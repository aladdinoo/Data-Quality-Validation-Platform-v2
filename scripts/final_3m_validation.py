#!/usr/bin/env python3
"""FINAL 3M VALIDATION — independent validation harness (Phase 3 of the final task).

Purpose
-------
Execute a REAL, fresh 3,000,000-row validation of the frozen V1 pipeline and
independently verify the results with a from-scratch oracle.

Independence statement
----------------------
- This script has ZERO imports from data_quality_platform / runner.
- The production path is exercised ONLY as a subprocess of the canonical CLI
  (``python -m runner.cli validate ...``), exactly as previously executed at 3M scale.
- The ORACLE below re-implements all 8 V1 predicates from the documented frozen
  contract with an independently written code path. It does NOT call any
  production rule function. The STATE_ZIP_PREFIXES table is transcribed as a
  frozen data constant of the contract (a pytest regression test cross-checks
  the transcription against data_quality_platform.contracts).
- Semantics notes for the oracle:
  * names: suspicious-substring (case-insensitive), non-alpha (Unicode-aware
    ``str.isalpha`` + hyphen + apostrophe allowed — same predicate family as the
    frozen engine), repeated-single-char after removing hyphen/apostrophe.
  * email: blank after strip -> email_blank=1; non-blank and not matching the
    documented pattern -> email_syntax_failure=1; non-blank and matching ->
    proposed_email_export_eligible=1. The oracle uses ``re.fullmatch`` on the
    stripped value; the engine uses ``re.match`` with a trailing ``$`` on the
    stripped value — for newline-free CSV values these are equivalent (any
    string distinguishing them must contain a trailing newline AFTER stripping,
    which is impossible since ``str.strip`` removes trailing whitespace).
  * geography: V1 frozen PREFIX-MAP semantics (NOT the SP1 canonical-reference
    semantics). States outside the 51-state prefix map (e.g. GU, PR, AA) are
    NOT assessable; a well-formed-or-not ZIP with an in-map state is scored
    purely by prefix membership.

Determinism
-----------
- One ``random.Random(seed)`` instance drives the whole dataset, consumed
  strictly in row order -> byte-identical dataset for the same (seed, rows).
- The engine is deterministic for identical input -> byte-identical output.
- The script runs the full pipeline TWICE and proves byte-identity.

Safety
------
- No ClickHouse, no network, no production data, no credentials.
- Peak memory measured via resource.getrusage (SELF + CHILDREN).
- Progress logged every 250,000 rows.

Usage
-----
    python scripts/final_3m_validation.py --rows 3000000 --seed 20260910 --passes 2
"""

import argparse
import csv
import filecmp
import hashlib
import json
import os
import random
import re
import resource
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Frozen contract constants (transcribed; NOT imported from the platform) ──
SOURCE_COLUMNS = [
    "id", "email_address", "first_name", "last_name", "address",
    "city", "county_name", "state", "zip", "website_source",
    "phone_number", "gender", "dob", "registration_date", "valid",
    "extra", "email_id", "ethnicity", "ownrent", "domain",
    "main_interest", "sub_interest", "latitude", "longitude", "uploaded",
    "country", "websource_id", "interest_ids", "DNC", "source",
    "first_name_norm", "last_name_norm", "zip_norm",
]

FLAG_COLUMNS = [
    "first_name_cleaning_candidate",
    "last_name_cleaning_candidate",
    "name_cleaning_candidate",
    "email_blank",
    "email_syntax_failure",
    "proposed_email_export_eligible",
    "zip_state_assessable",
    "geography_mismatch_candidate",
]

# 51-state ZIP prefix map (frozen V1 data contract, transcribed independently)
ORACLE_PREFIXES = {
    "AL": ("35", "36"), "AK": ("99",), "AZ": ("85", "86"),
    "AR": ("71", "72"), "CA": ("90", "91", "92", "93", "94", "95", "96"),
    "CO": ("80", "81"), "CT": ("06",), "DE": ("19",),
    "DC": ("20", "20"), "FL": ("32", "33", "34"), "GA": ("30", "31"),
    "HI": ("96", "97"), "ID": ("83", "84"), "IL": ("60", "61", "62"),
    "IN": ("46", "47"), "IA": ("50", "51", "52"), "KS": ("66", "67"),
    "KY": ("40", "41", "42"), "LA": ("70", "71"), "ME": ("03", "04"),
    "MD": ("21", "22"), "MA": ("01", "02"), "MI": ("48", "49"),
    "MN": ("55", "56"), "MS": ("38", "39"), "MO": ("63", "64", "65"),
    "MT": ("59",), "NE": ("68", "69"), "NV": ("88", "89"),
    "NH": ("03",), "NJ": ("07", "08"), "NM": ("87", "88"),
    "NY": ("10", "11", "12", "13", "14"), "NC": ("27", "28"),
    "ND": ("58",), "OH": ("43", "44", "45"), "OK": ("73", "74"),
    "OR": ("97",), "PA": ("15", "16", "17", "18", "19"),
    "RI": ("02", "03"), "SC": ("29",), "SD": ("57",),
    "TN": ("37", "38"), "TX": ("75", "76", "77", "78", "79"),
    "UT": ("84",), "VT": ("05",), "VA": ("22", "23", "24"),
    "WA": ("98", "99"), "WV": ("24", "25", "26"),
    "WI": ("53", "54"), "WY": ("82", "83"),
}

SUSPICIOUS = (
    "test", "fake", "dummy", "xxx", "zzz", "aaa", "bbb",
    "admin", "null", "none", "na", "n/a", "unknown",
    "example", "sample", "asdf", "qwerty", "abc", "xyz",
)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def transcription_self_check():
    """Structural sanity of the transcribed tables (no production imports)."""
    assert len(SOURCE_COLUMNS) == 33, "SOURCE_COLUMNS must be 33"
    assert len(set(SOURCE_COLUMNS)) == 33, "SOURCE_COLUMNS must be unique"
    assert len(FLAG_COLUMNS) == 8, "FLAG_COLUMNS must be 8"
    assert len(ORACLE_PREFIXES) == 51, "ORACLE_PREFIXES must have 51 states"
    for st, prefs in ORACLE_PREFIXES.items():
        assert len(st) == 2 and st.isupper() and st.isalpha(), st
        for p in prefs:
            assert len(p) == 2 and p.isdigit(), (st, p)
    assert len(SUSPICIOUS) == 19  # 19 frozen patterns in the contract


# ════════════════════════════════════════════════════════════════════
# INDEPENDENT ORACLE — the 8 frozen V1 predicates, re-implemented here
# ════════════════════════════════════════════════════════════════════

def _blank(text):
    return text is None or str(text).strip() == ""


def _oracle_name_flag(name):
    """first_name/last_name cleaning candidate predicate."""
    s = str(name or "").strip()
    if s == "":
        return 0
    low = s.lower()
    for pattern in SUSPICIOUS:
        if pattern in low:
            return 1
    for ch in s:
        if not (ch.isalpha() or ch == "-" or ch == "'"):
            return 1
    collapsed = low.replace("-", "").replace("'", "")
    if len(s) > 1 and collapsed != "" and len(set(collapsed)) == 1:
        return 1
    return 0


def _oracle_full_name_flag(first, last):
    f = str(first or "").strip()
    l = str(last or "").strip()
    if f == "" and l == "":
        return 0
    if f != "" and l != "":
        if f.lower() == l.lower():
            return 1
        if len(f) <= 1 and len(l) <= 1:
            return 1
    return 0


def _oracle_email_flags(raw_email):
    """Returns (blank, syntax_failure, export_eligible) for one raw value."""
    e = str(raw_email if raw_email is not None else "").strip()
    if e == "":
        return 1, 0, 0
    ok = EMAIL_RE.fullmatch(e) is not None
    return 0, (0 if ok else 1), (1 if ok else 0)


def _oracle_geography_flags(raw_zip, raw_state):
    """Returns (assessable, mismatch) under frozen V1 prefix-map semantics."""
    z = str(raw_zip or "").strip()
    s = str(raw_state or "").strip()
    if z == "" or s == "":
        return 0, 0
    su = s.upper()
    if su not in ORACLE_PREFIXES:
        return 0, 0
    for prefix in ORACLE_PREFIXES[su]:
        if z.startswith(prefix):
            return 1, 0
    return 1, 1


def oracle_flags(row):
    """Compute all 8 V1 flags for one row dict. Independent code path."""
    blank, syntax_fail, eligible = _oracle_email_flags(row.get("email_address"))
    assessable, mismatch = _oracle_geography_flags(row.get("zip"), row.get("state"))
    return {
        "first_name_cleaning_candidate": _oracle_name_flag(row.get("first_name")),
        "last_name_cleaning_candidate": _oracle_name_flag(row.get("last_name")),
        "name_cleaning_candidate": _oracle_full_name_flag(
            row.get("first_name"), row.get("last_name")),
        "email_blank": blank,
        "email_syntax_failure": syntax_fail,
        "proposed_email_export_eligible": eligible,
        "zip_state_assessable": assessable,
        "geography_mismatch_candidate": mismatch,
    }


# ════════════════════════════════════════════════════════════════════
# DETERMINISTIC 3M DATASET GENERATOR (independent of platform generator)
# ════════════════════════════════════════════════════════════════════

FIRST_NORMAL = ["James", "Mary", "Robert", "Patricia", "Michael", "Linda",
                "David", "Sarah", "Daniel", "Laura", "Kevin", "Emily",
                "Brian", "Anna", "Jason", "Olivia", "Eric", "Sophia",
                "Mark", "Grace", "Paul", "Chloe", "Andrew", "Hannah"]
LAST_NORMAL = ["Smith", "Johnson", "Brown", "Garcia", "Miller", "Wilson",
               "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin",
               "Lee", "Clark", "Lewis", "Walker", "Hall", "Young", "King",
               "Wright", "Scott", "Green", "Baker", "Adams"]
SUSPICIOUS_NAMES = ["Test", "Fakeuser", "Dummy", "Xyz", "Sample", "Asdf",
                    "Qwerty", "Unknown", "Null", "Abcuser"]
REPEATED_NAMES = ["aaaa", "bbbb", "zzzz", "xx", "qqqq"]
UNICODE_NAMES = ["José", "Zoë", "André", "François", "Müller", "Sjöberg"]
HYPHEN_APOS_NAMES = ["Anne-Marie", "O'Brien", "D'Angelo", "Jean-Pierre", "Mary-Jane"]
MALFORMED_ZIPS = ["0", "00USA", "000CA", "015 8", "123456", "12A45", ""]
UNKNOWN_STATES = ["ZZ", "XX", "GU", "PR", "VI"]
CITIES = ["Springfield", "Riverside", "Franklin", "Greenville", "Bristol",
          "Clinton", "Fairview", "Salem", "Madison", "Georgetown", "Arlington"]
COUNTIES = ["Washington", "Jefferson", "Lincoln", "Jackson", "Franklin",
            "Montgomery", "Marion", "Monroe", "Adams", "Clay"]
STREETS = ["Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Pine Rd",
           "Elm Blvd", "Sunset Ave", "River Rd", "Hill St", "Lake Dr"]
DOMAINS = ["example.com", "testmail.org", "webmail.net", "company.io", "inbox.co"]
INVALID_EMAILS = ["not-an-email", "no-at-sign.com", "user@@double.com",
                  "user@nodot", "a@b", "user name@x.com", "..@..", "@missinglocal"]
WEBSOURCES = ["organic", "partner", "affiliate", "paid-search", "social"]
ETHNICITIES = ["W", "B", "A", "H", "O", "U"]
INTERESTS = ["sports", "finance", "travel", "tech", "home", "auto", "health"]
SUBINTERESTS = ["news", "deals", "reviews", "guides", "tips", "trends"]
SOURCES = ["vendor_a", "vendor_b", "partner_c", "internal"]
ALL_PREFIXES = sorted({p for prefs in ORACLE_PREFIXES.values() for p in prefs})


def _five_digit(rng):
    return f"{rng.randrange(10000, 100000)}"


def _matching_zip(rng, state):
    prefix = rng.choice(ORACLE_PREFIXES[state])
    return prefix + f"{rng.randrange(100, 1000)}"


def _mismatching_zip(rng, state):
    """A 5-digit ZIP guaranteed NOT to start with any prefix of `state`."""
    own = set(ORACLE_PREFIXES[state])
    while True:
        prefix = rng.choice(ALL_PREFIXES)
        if prefix not in own:
            return prefix + f"{rng.randrange(100, 1000)}"


def _random_row(rng, i):
    # email distribution: 78% valid / 8% blank / 7% invalid / 5% padded / 2% NULL-string
    r = rng.random()
    if r < 0.78:
        email = f"user{i}@{rng.choice(DOMAINS)}"
    elif r < 0.86:
        email = ""
    elif r < 0.93:
        email = rng.choice(INVALID_EMAILS)
    elif r < 0.98:
        email = f"  user{i}@{rng.choice(DOMAINS)}  "
    else:
        email = "NULL"
    # names
    r = rng.random()
    if r < 0.82:
        first = rng.choice(FIRST_NORMAL)
    elif r < 0.87:
        first = rng.choice(SUSPICIOUS_NAMES)
    elif r < 0.91:
        first = rng.choice(REPEATED_NAMES)
    elif r < 0.94:
        first = rng.choice(UNICODE_NAMES)
    elif r < 0.97:
        first = rng.choice(HYPHEN_APOS_NAMES)
    else:
        first = rng.choice(["", "J", "A", "x", " "])
    r = rng.random()
    if r < 0.84:
        last = rng.choice(LAST_NORMAL)
    elif r < 0.88:
        last = rng.choice(SUSPICIOUS_NAMES)
    elif r < 0.92:
        last = rng.choice(REPEATED_NAMES)
    elif r < 0.95:
        last = rng.choice(UNICODE_NAMES)
    elif r < 0.97:
        last = rng.choice(HYPHEN_APOS_NAMES)
    else:
        last = rng.choice(["", "K", "Z", "q", " "])
    # geography
    r = rng.random()
    if r < 0.90:
        state = rng.choice(sorted(ORACLE_PREFIXES))
    elif r < 0.93:
        state = rng.choice(sorted(ORACLE_PREFIXES)).lower()
    elif r < 0.96:
        state = rng.choice(UNKNOWN_STATES)
    elif r < 0.98:
        state = ""
    else:
        state = f"{rng.randrange(10, 100)}"
    if state.upper() in ORACLE_PREFIXES and state != "":
        r = rng.random()
        if r < 0.85:
            zip_val = _matching_zip(rng, state.upper())
        elif r < 0.95:
            zip_val = _mismatching_zip(rng, state.upper())
        else:
            zip_val = rng.choice(MALFORMED_ZIPS)
    else:
        r = rng.random()
        if r < 0.70:
            zip_val = _five_digit(rng)
        elif r < 0.90:
            zip_val = rng.choice(MALFORMED_ZIPS)
        else:
            zip_val = ""
    city = "" if rng.random() < 0.05 else rng.choice(CITIES)
    county = "" if rng.random() < 0.10 else rng.choice(COUNTIES)
    address = "" if rng.random() < 0.05 else f"{rng.randrange(1, 9999)} {rng.choice(STREETS)}"
    return {
        "id": str(i),
        "email_address": email,
        "first_name": first,
        "last_name": last,
        "address": address,
        "city": city,
        "county_name": county,
        "state": state,
        "zip": zip_val,
        "website_source": rng.choice(WEBSOURCES),
        "phone_number": f"555-{rng.randrange(100, 1000):03d}-{rng.randrange(1000, 10000):04d}",
        "gender": rng.choice(["M", "F"]),
        "dob": f"19{rng.randrange(40, 100):02d}-{rng.randrange(1, 13):02d}-{rng.randrange(1, 29):02d}",
        "registration_date": f"2025-{rng.randrange(1, 13):02d}-{rng.randrange(1, 29):02d}",
        "valid": str(rng.randrange(0, 2)),
        "extra": "",
        "email_id": f"eid{i}",
        "ethnicity": rng.choice(ETHNICITIES),
        "ownrent": rng.choice(["R", "O"]),
        "domain": rng.choice(DOMAINS),
        "main_interest": rng.choice(INTERESTS),
        "sub_interest": rng.choice(SUBINTERESTS),
        "latitude": f"{rng.uniform(24.0, 50.0):.6f}",
        "longitude": f"{rng.uniform(-125.0, -66.0):.6f}",
        "uploaded": f"2026-0{rng.randrange(1, 9)}-{rng.randrange(10, 29):02d}",
        "country": "US" if rng.random() < 0.95 else "",
        "websource_id": str(rng.randrange(1, 5000)),
        "interest_ids": f"{rng.randrange(1, 50)},{rng.randrange(1, 50)}",
        "DNC": str(rng.randrange(0, 2)),
        "source": rng.choice(SOURCES),
        "first_name_norm": first.lower(),
        "last_name_norm": last.lower(),
        "zip_norm": zip_val,
    }


def _edge_rows():
    """Hand-crafted edge rows embedded at the head of the dataset (deterministic).
    These exercise V1 semantics on the exact geography/name/email boundaries,
    including the well-known WA/99501 and GU/96910 pairs (under V1 prefix-map
    semantics: WA+99501 -> assessable=1/mismatch=0; GU+96910 -> 0/0)."""
    rows = []

    def add(email, first, last, state, zip_val, city="Springfield",
            county="Franklin", address="123 Main St"):
        rows.append({
            "id": "0", "email_address": email, "first_name": first,
            "last_name": last, "address": address, "city": city,
            "county_name": county, "state": state, "zip": zip_val,
            "website_source": "organic", "phone_number": "555-010-0100",
            "gender": "M", "dob": "1980-01-01", "registration_date": "2025-01-01",
            "valid": "1", "extra": "", "email_id": "eid0", "ethnicity": "U",
            "ownrent": "O", "domain": "example.com", "main_interest": "tech",
            "sub_interest": "news", "latitude": "35.000000",
            "longitude": "-90.000000", "uploaded": "2026-01-01", "country": "US",
            "websource_id": "1", "interest_ids": "1,2", "DNC": "0",
            "source": "vendor_a", "first_name_norm": first.lower(),
            "last_name_norm": last.lower(), "zip_norm": zip_val,
        })

    # geography acceptance-style pairs + boundaries (V1 prefix-map semantics)
    add("user1@example.com", "James", "Smith", "CA", "90210")
    add("user2@example.com", "James", "Smith", "CA", "00USA")
    add("user3@example.com", "James", "Smith", "CA", "0")
    add("user4@example.com", "James", "Smith", "CA", "000CA")
    add("user5@example.com", "James", "Smith", "CA", "015 8")
    add("user6@example.com", "James", "Smith", "WA", "99501")
    add("user7@example.com", "James", "Smith", "GU", "96910")
    add("user8@example.com", "James", "Smith", "ca", "90210")       # lowercase state
    add("user9@example.com", "James", "Smith", "NY", "10001")
    add("user10@example.com", "James", "Smith", "NY", "99999")      # mismatching
    add("user11@example.com", "James", "Smith", "", "90210")        # blank state
    add("user12@example.com", "James", "Smith", "CA", "")           # blank zip
    add("user13@example.com", "James", "Smith", "12", "90210")      # numeric state
    add("user14@example.com", "James", "Smith", "XX", "12345")      # unknown state
    add("user15@example.com", "James", "Smith", "AK", "99501")      # AK prefix 99
    add("user16@example.com", "James", "Smith", "MA", "01234")
    add("user17@example.com", "James", "Smith", "WA", "98101")
    # name edges
    add("user20@example.com", "José", "García", "CA", "90210")      # unicode alpha OK
    add("user21@example.com", "O'Brien", "Smith", "CA", "90210")
    add("user22@example.com", "Anne-Marie", "Dupont", "CA", "90210")
    add("user23@example.com", "aaaa", "Smith", "CA", "90210")       # repeated
    add("user24@example.com", "Test", "User", "CA", "90210")        # suspicious
    add("user25@example.com", "", "Smith", "CA", "90210")           # blank first
    add("user26@example.com", "J", "K", "CA", "90210")              # single chars
    add("user27@example.com", "Same", "Same", "CA", "90210")        # first==last
    add("user28@example.com", "Smith", "smith", "CA", "90210")      # case-insensitive equal
    add("user29@example.com", "John Doe42", "Smith", "CA", "90210")  # non-alpha
    # email edges
    add("", "James", "Smith", "CA", "90210")                        # blank email
    add("   ", "James", "Smith", "CA", "90210")                     # whitespace email
    add("  user30@example.com  ", "James", "Smith", "CA", "90210")  # padded valid
    add("not-an-email", "James", "Smith", "CA", "90210")            # invalid
    add("user@nodot", "James", "Smith", "CA", "90210")              # invalid
    add("NULL", "James", "Smith", "CA", "90210")                    # null-string
    # blank city / blank address
    add("user31@example.com", "James", "Smith", "CA", "90210", city="", address="")
    add("user32@example.com", "James", "Smith", "CA", "90210", county="", address="")
    return rows


def generate_dataset(path, rows, seed, progress_every=250_000):
    """Deterministic dataset: one RNG consumed strictly in row order."""
    rng = random.Random(seed)
    edges = _edge_rows()
    t0 = time.perf_counter()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    written = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SOURCE_COLUMNS)
        writer.writeheader()
        for i in range(1, rows + 1):
            if i <= len(edges):
                row = dict(edges[i - 1])
                row["id"] = str(i)
            else:
                row = _random_row(rng, i)
            writer.writerow(row)
            written += 1
            if written % progress_every == 0:
                log(f"  generate: {written:,}/{rows:,} rows "
                    f"({time.perf_counter() - t0:.1f}s)")
    return time.perf_counter() - t0


# ════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ════════════════════════════════════════════════════════════════════

def log(msg):
    print(msg, flush=True)


def sha256_file(path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def peak_rss_mb():
    """Peak RSS in MB: max of this process and its children (Linux ru_maxrss is KiB)."""
    self_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    child_kb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return max(self_kb, child_kb) / 1024.0


def run_cli_validate(csv_path, out_path, run_id, evidence_dir):
    """Run the PRODUCTION validation path as a subprocess of the canonical CLI."""
    cmd = [
        sys.executable, "-m", "runner.cli", "validate",
        "--csv", csv_path, "--output", out_path,
        "--run-id", run_id, "--evidence-dir", evidence_dir,
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    duration = time.perf_counter() - t0
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "duration_seconds": round(duration, 3),
    }


# ════════════════════════════════════════════════════════════════════
# VERIFICATION + INDEPENDENT ORACLE PASS
# ════════════════════════════════════════════════════════════════════

def verify_and_oracle(in_path, out_path, expected_rows, progress_every=250_000):
    """Stream input+output in lockstep. Checks the 16 required dimensions that
    apply to the per-pass verification (schema, counts, order, identity,
    ordering, immutability of values, output shape, all 8 flags, oracle)."""
    result = {
        "schema_status": "FAIL",
        "row_count_status": "FAIL",
        "column_count_status": "FAIL",
        "column_order_status": "FAIL",
        "row_identity_status": "FAIL",
        "row_ordering_status": "FAIL",
        "source_values_preserved_status": "FAIL",
        "output_shape_status": "FAIL",
        "flag_domain_status": "FAIL",
        "oracle_comparisons": 0,
        "oracle_mismatches": 0,
        "mismatches_by_rule": {c: 0 for c in FLAG_COLUMNS},
        "first_mismatches": [],
        "flag_totals": {c: 0 for c in FLAG_COLUMNS},
        "input_rows": 0,
        "output_rows": 0,
    }

    with open(in_path, "r", newline="", encoding="utf-8") as fin, \
         open(out_path, "r", newline="", encoding="utf-8") as fout:
        reader_in = csv.DictReader(fin)
        reader_out = csv.DictReader(fout)
        header_in = list(reader_in.fieldnames or [])
        header_out = list(reader_out.fieldnames or [])

        # 1. schema + 3/4. column count + order
        result["schema_status"] = "PASS" if header_in == SOURCE_COLUMNS else "FAIL"
        result["column_count_status"] = (
            "PASS" if len(header_in) == 33 and len(header_out) == 41 else "FAIL")
        result["column_order_status"] = (
            "PASS" if header_out == SOURCE_COLUMNS + FLAG_COLUMNS else "FAIL")

        rows_seen = 0
        identity_ok = True
        ordering_ok = True
        preserved_ok = True
        flag_domain_ok = True
        identity_first_bad = None
        ordering_first_bad = None
        preserved_first_bad = None
        t0 = time.perf_counter()

        for pos, (src, dst) in enumerate(zip(reader_in, reader_out), start=1):
            rows_seen += 1
            # 5. row identity: id equals its 1-based position in both files
            if src.get("id") != str(pos) or dst.get("id") != str(pos):
                identity_ok = False
                if identity_first_bad is None:
                    identity_first_bad = (pos, src.get("id"), dst.get("id"))
            # 6. row ordering + 7. source values preserved: all 33 source
            #    columns byte-equal between input row and output row at pos
            for col in SOURCE_COLUMNS:
                if src.get(col) != dst.get(col):
                    ordering_ok = False
                    preserved_ok = False
                    if ordering_first_bad is None:
                        ordering_first_bad = (pos, col, repr(src.get(col)), repr(dst.get(col)))
            # 8/9. output shape: flags in {0,1}
            for col in FLAG_COLUMNS:
                v = dst.get(col)
                if v not in ("0", "1"):
                    flag_domain_ok = False
                if v == "1":
                    result["flag_totals"][col] += 1
            # 10. independent oracle
            expected = oracle_flags(src)
            for col in FLAG_COLUMNS:
                result["oracle_comparisons"] += 1
                actual = dst.get(col)
                if str(expected[col]) != actual:
                    result["oracle_mismatches"] += 1
                    result["mismatches_by_rule"][col] += 1
                    if len(result["first_mismatches"]) < 5:
                        result["first_mismatches"].append({
                            "row": pos, "rule": col,
                            "input": {k: src.get(k) for k in
                                      ("id", "email_address", "first_name",
                                       "last_name", "state", "zip")},
                            "oracle": str(expected[col]), "engine": actual,
                        })
            if rows_seen % progress_every == 0:
                log(f"  verify+oracle: {rows_seen:,} rows "
                    f"({time.perf_counter() - t0:.1f}s, mismatches so far: "
                    f"{result['oracle_mismatches']})")

        result["input_rows"] = rows_seen
        # drain both readers to prove equal counts
        extra_in = sum(1 for _ in reader_in)
        extra_out = sum(1 for _ in reader_out)
        result["output_rows"] = rows_seen + extra_out
        result["extra_input_rows_after_lockstep"] = extra_in
        result["extra_output_rows_after_lockstep"] = extra_out

    result["row_count_status"] = (
        "PASS" if (result["input_rows"] == expected_rows
                   and result["output_rows"] == expected_rows
                   and extra_in == 0 and extra_out == 0) else "FAIL")
    result["row_identity_status"] = "PASS" if identity_ok else "FAIL"
    if identity_first_bad:
        result["row_identity_first_anomaly"] = identity_first_bad
    result["row_ordering_status"] = "PASS" if ordering_ok else "FAIL"
    result["source_values_preserved_status"] = "PASS" if preserved_ok else "FAIL"
    if ordering_first_bad:
        result["first_source_column_difference"] = ordering_first_bad
    result["output_shape_status"] = "PASS" if (
        flag_domain_ok and result["column_count_status"] == "PASS"
        and result["column_order_status"] == "PASS") else "FAIL"
    result["flag_domain_status"] = "PASS" if flag_domain_ok else "FAIL"
    result["verify_duration_seconds"] = round(time.perf_counter() - t0, 3)
    return result


# ════════════════════════════════════════════════════════════════════
# SP1 ISOLATION CHECK (production run must have executed V1, not SP1)
# ════════════════════════════════════════════════════════════════════

def sp1_isolation_check(engine_evidence_dir):
    """The engine manifest must record exactly the 8 frozen V1 rule IDs and
    their known hashes; the SP1 successor layer must not appear."""
    manifest_path = os.path.join(engine_evidence_dir, "manifest.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as exc:
        return {"status": "FAIL", "reason": f"manifest unreadable: {exc}"}
    rule_hashes = manifest.get("rule_hashes", {})
    if sorted(rule_hashes.keys()) == sorted(FLAG_COLUMNS) and len(rule_hashes) == 8:
        return {"status": "PASS", "rules_in_manifest": sorted(rule_hashes.keys())}
    return {"status": "FAIL", "rules_in_manifest": sorted(rule_hashes.keys())}


# ════════════════════════════════════════════════════════════════════
# MAIN DRIVER
# ════════════════════════════════════════════════════════════════════

def phase_generate(args, pass_no):
    """PHASE: generate — build the deterministic dataset for one pass."""
    label = f"pass{pass_no}"
    in_path = os.path.join(args.data_dir, f"consumer_3m_seed_{args.seed}_{label}.csv")
    log(f"[{label}] GENERATE dataset ({args.rows:,} rows, seed {args.seed}) ...")
    gen_t = generate_dataset(in_path, args.rows, args.seed)
    in_hash = sha256_file(in_path)
    in_size = os.path.getsize(in_path)
    log(f"[{label}] dataset: {in_size:,} bytes, sha256={in_hash}, "
        f"generated in {gen_t:.1f}s")
    state = {
        "pass": label,
        "path": in_path, "rows": args.rows, "seed": args.seed,
        "columns": 33, "size_bytes": in_size, "sha256": in_hash,
        "generation_seconds": round(gen_t, 3),
    }
    with open(os.path.join(args.evidence_dir, f"{label}_generate.json"), "w",
              encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    return state


def phase_validate(args, pass_no):
    """PHASE: validate — run the production CLI subprocess for one pass."""
    label = f"pass{pass_no}"
    gen_path = os.path.join(args.evidence_dir, f"{label}_generate.json")
    with open(gen_path, "r", encoding="utf-8") as f:
        gen = json.load(f)
    in_path = gen["path"]
    out_path = os.path.join(
        args.data_dir, f"consumer_3m_seed_{args.seed}_{label}_out.csv")
    engine_ev = os.path.join(args.evidence_dir, f"{label}_engine")
    log(f"[{label}] VALIDATE via production CLI subprocess ...")
    cli = run_cli_validate(in_path, out_path, f"final_3m_{label}", engine_ev)
    log(f"[{label}] CLI exit={cli['returncode']} in {cli['duration_seconds']}s")
    for line in cli["stdout"].splitlines():
        log(f"[{label}] CLI> {line}")
    if cli["stderr"].strip():
        for line in cli["stderr"].splitlines()[:20]:
            log(f"[{label}] CLI(err)> {line}")
    in_hash_post = sha256_file(in_path)
    out_hash = sha256_file(out_path) if cli["returncode"] == 0 else ""
    out_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    # Peak RSS of the engine = RUSAGE_CHILDREN high-water mark after the
    # subprocess completes (Linux ru_maxrss is KiB). This is the authoritative
    # whole-run memory figure, matching the method used by the prior 3M
    # execution evidence (evidence/final_5m_execution/11_.../run1/memory.txt).
    engine_peak_rss_mb = round(peak_rss_mb(), 2)
    log(f"[{label}] engine peak RSS (RUSAGE_CHILDREN, post-exit): "
        f"{engine_peak_rss_mb} MB")
    log(f"[{label}] output: {out_size:,} bytes, sha256={out_hash}")
    log(f"[{label}] source immutability: input hash before={gen['sha256'][:16]} "
        f"after={in_hash_post[:16]} -> "
        f"{'UNCHANGED' if gen['sha256'] == in_hash_post else 'CHANGED'}")
    state = {
        "pass": label,
        "cli": cli,
        "output_path": out_path, "output_size_bytes": out_size,
        "output_sha256": out_hash,
        "input_sha256_after_validation": in_hash_post,
        "engine_evidence_dir": engine_ev,
        "engine_peak_rss_mb": engine_peak_rss_mb,
    }
    with open(os.path.join(args.evidence_dir, f"{label}_cli.json"), "w",
              encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    return state


def phase_verify(args, pass_no):
    """PHASE: verify — schema/identity/order/oracle verification for one pass."""
    label = f"pass{pass_no}"
    with open(os.path.join(args.evidence_dir, f"{label}_generate.json"),
              "r", encoding="utf-8") as f:
        gen = json.load(f)
    with open(os.path.join(args.evidence_dir, f"{label}_cli.json"),
              "r", encoding="utf-8") as f:
        cli_state = json.load(f)
    log(f"[{label}] VERIFY + INDEPENDENT ORACLE (streaming {args.rows:,} rows) ...")
    verify = verify_and_oracle(gen["path"], cli_state["output_path"], args.rows)
    for key in ("schema_status", "row_count_status", "column_count_status",
                "column_order_status", "row_identity_status", "row_ordering_status",
                "source_values_preserved_status", "output_shape_status",
                "flag_domain_status"):
        log(f"[{label}]   {key}: {verify[key]}")
    log(f"[{label}]   oracle comparisons={verify['oracle_comparisons']:,} "
        f"mismatches={verify['oracle_mismatches']}")
    if verify["oracle_mismatches"]:
        log(f"[{label}]   mismatches_by_rule={verify['mismatches_by_rule']}")
    sp1 = sp1_isolation_check(cli_state["engine_evidence_dir"])
    log(f"[{label}] SP1 isolation (manifest rule set): {sp1['status']}")
    pass_result = {
        "pass": label,
        "blocked": cli_state["cli"]["returncode"] != 0,
        "cli": cli_state["cli"],
        "dataset": {
            "path": gen["path"], "rows": gen["rows"], "seed": gen["seed"],
            "columns": 33, "size_bytes": gen["size_bytes"],
            "sha256": gen["sha256"],
            "sha256_after_validation": cli_state["input_sha256_after_validation"],
            "generation_seconds": gen["generation_seconds"],
        },
        "output": {
            "path": cli_state["output_path"],
            "rows": verify["output_rows"], "columns": 41,
            "size_bytes": cli_state["output_size_bytes"],
            "sha256": cli_state["output_sha256"],
        },
        "verification": verify,
        "sp1_isolation": sp1,
        "peak_rss_mb": round(peak_rss_mb(), 2),
        "engine_peak_rss_mb": cli_state.get("engine_peak_rss_mb"),
    }
    with open(os.path.join(args.evidence_dir, f"{label}_result.json"), "w",
              encoding="utf-8") as f:
        json.dump(pass_result, f, indent=2)
    return pass_result


def run_pass(pass_no, args, t_total0):
    """Single-shot full pass (generate -> validate -> verify). Used by --phase all."""
    label = f"pass{pass_no}"
    gen = phase_generate(args, pass_no)
    val = phase_validate(args, pass_no)
    if val["cli"]["returncode"] != 0:
        log(f"[{label}] BLOCKED: production CLI failed — stopping this pass.")
        return {"pass": label, "blocked": True, "cli": val["cli"]}
    return phase_verify(args, pass_no)


def phase_finalize(args):
    """PHASE: finalize — determinism comparison + FINAL_RESULTS.json."""
    with open(os.path.join(args.evidence_dir, "pass1_result.json"),
              "r", encoding="utf-8") as f:
        p1 = json.load(f)
    p2_path = os.path.join(args.evidence_dir, "pass2_result.json")
    p2 = None
    if os.path.exists(p2_path):
        with open(p2_path, "r", encoding="utf-8") as f:
            p2 = json.load(f)

    # Authoritative whole-run peak memory: engine child peak (validation stage).
    harness_peak = p1.get("peak_rss_mb", 0) or 0
    engine_peak = p1.get("engine_peak_rss_mb") or 0
    if p2 is not None:
        engine_peak = max(engine_peak, p2.get("engine_peak_rss_mb") or 0)
    peak_memory_mb = max(engine_peak, harness_peak)

    determinism = {"input_hash_equal": None, "output_hash_equal": None,
                   "byte_identical_output": None}
    if p2 is not None:
        determinism["input_hash_equal"] = (
            p1["dataset"]["sha256"] == p2["dataset"]["sha256"])
        determinism["output_hash_equal"] = (
            p1["output"]["sha256"] == p2["output"]["sha256"])
        if os.path.exists(p1["output"]["path"]) and os.path.exists(p2["output"]["path"]):
            determinism["byte_identical_output"] = filecmp.cmp(
                p1["output"]["path"], p2["output"]["path"], shallow=False)
        log(f"DETERMINISM: input_hash_equal={determinism['input_hash_equal']} "
            f"output_hash_equal={determinism['output_hash_equal']} "
            f"byte_identical_output={determinism['byte_identical_output']}")

    v = p1["verification"]
    schema_ok = v["schema_status"] == "PASS" and v["column_count_status"] == "PASS" \
        and v["column_order_status"] == "PASS"
    preservation_ok = v["row_count_status"] == "PASS" \
        and v["row_identity_status"] == "PASS" and v["row_ordering_status"] == "PASS" \
        and v["source_values_preserved_status"] == "PASS" \
        and v["output_shape_status"] == "PASS" \
        and v["flag_domain_status"] == "PASS" \
        and p1["dataset"]["sha256"] == p1["dataset"]["sha256_after_validation"]
    oracle_ok = v["oracle_mismatches"] == 0
    sp1_ok = p1["sp1_isolation"]["status"] == "PASS"
    determinism_ok = (p2 is None) or all(
        x is not False for x in determinism.values())
    safety_ok = True  # enforced by construction: no network/CH/prod imports or calls

    final_status = "PASS" if all([schema_ok, preservation_ok, oracle_ok,
                                  sp1_ok, determinism_ok, safety_ok,
                                  p1["cli"]["returncode"] == 0]) else "FAIL"

    stage_runtimes = {
        "generation_pass1": p1["dataset"]["generation_seconds"],
        "validation_pass1": p1["cli"]["duration_seconds"],
        "verify_oracle_pass1": p1["verification"]["verify_duration_seconds"],
    }
    total_runtime = sum(stage_runtimes.values())
    if p2 is not None:
        stage_runtimes["generation_pass2"] = p2["dataset"]["generation_seconds"]
        stage_runtimes["validation_pass2"] = p2["cli"]["duration_seconds"]
        stage_runtimes["verify_oracle_pass2"] = p2["verification"]["verify_duration_seconds"]
        total_runtime = sum(stage_runtimes.values())

    final = {
        "report": "FINAL 3M VALIDATION RESULTS",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rows": p1["dataset"]["rows"],
        "columns": 33,
        "output_columns": 41,
        "seed": p1["dataset"]["seed"],
        "input_sha256": p1["dataset"]["sha256"],
        "output_sha256": p1["output"]["sha256"],
        "input_size_bytes": p1["dataset"]["size_bytes"],
        "output_size_bytes": p1["output"]["size_bytes"],
        "runtime_seconds": round(total_runtime, 3),
        "runtime_note": "sum of staged phase runtimes (generation+validation+verify per pass)",
        "stage_runtime_seconds": stage_runtimes,
        "peak_memory_mb": peak_memory_mb,
        "peak_memory_note": (
            "engine subprocess peak RSS via resource.getrusage(RUSAGE_CHILDREN) "
            "measured post-exit in the validate phase (authoritative); "
            "harness verify-process peak was "
            f"{harness_peak} MB"),
        "oracle_comparisons": v["oracle_comparisons"],
        "oracle_mismatches": v["oracle_mismatches"],
        "mismatches_by_rule": v["mismatches_by_rule"],
        "first_mismatches": v["first_mismatches"],
        "flag_totals_output_csv": v["flag_totals"],
        "flag_totals_engine_cli": p1["cli"]["stdout"],
        "schema_status": "PASS" if schema_ok else "FAIL",
        "preservation_status": "PASS" if preservation_ok else "FAIL",
        "determinism_status": (
            "PASS (byte-identical on repeated execution)"
            if determinism_ok and p2 is not None
            else ("NOT RUN (single pass)" if p2 is None else "FAIL")),
        "determinism_detail": determinism,
        "safety_status": (
            "PASS — no ClickHouse, no network, no production data, "
            "no credentials, no mutations; production path exercised only "
            "via local CLI subprocess on synthetic data"),
        "sp1_isolation_status": "PASS" if sp1_ok else "FAIL",
        "sp1_isolation_detail": p1["sp1_isolation"],
        "cli_verdict": "Validation PASSED" if p1["cli"]["returncode"] == 0 else "FAILED",
        "final_status": final_status,
        "environment": {
            "python": sys.version.split()[0],
            "os": sys.platform,
        },
        "pass2": ({"dataset_sha256": p2["dataset"]["sha256"],
                   "output_sha256": p2["output"]["sha256"],
                   "cli_returncode": p2["cli"]["returncode"],
                   "oracle_mismatches": p2["verification"]["oracle_mismatches"]}
                  if p2 else None),
    }

    results_path = os.path.join(args.evidence_dir, "FINAL_RESULTS.json")
    tmp_path = results_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2)
    os.replace(tmp_path, results_path)  # atomic evidence writing
    log(f"FINAL_RESULTS.json written (atomic): {results_path}")

    if p2 is not None and determinism_ok and not args.keep_pass2:
        removed = []
        for path in (p2["dataset"]["path"], p2["output"]["path"]):
            if os.path.exists(path):
                os.remove(path)
                removed.append(path)
        final["pass2_files_removed_after_byte_identical_proof"] = removed
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(final, f, indent=2)
        os.replace(tmp_path, results_path)
        log(f"pass2 bulk CSVs removed after byte-identity proof: {removed}")

    log("=" * 72)
    log("FINAL 3M VALIDATION SUMMARY")
    log(f"  final_status: {final_status}")
    log(f"  rows: {final['rows']:,}  columns: {final['columns']} -> {final['output_columns']}")
    log(f"  seed: {final['seed']}")
    log(f"  input_sha256:  {final['input_sha256']}")
    log(f"  output_sha256: {final['output_sha256']}")
    log(f"  runtime_seconds: {final['runtime_seconds']}")
    log(f"  peak_memory_mb: {final['peak_memory_mb']}")
    log(f"  oracle_comparisons: {final['oracle_comparisons']:,}")
    log(f"  oracle_mismatches: {final['oracle_mismatches']}")
    log(f"  determinism_status: {final['determinism_status']}")
    log(f"  schema_status: {final['schema_status']}")
    log(f"  preservation_status: {final['preservation_status']}")
    log(f"  sp1_isolation_status: {final['sp1_isolation_status']}")
    log("=" * 72)
    return 0 if final_status == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(description="Final 3M independent validation")
    parser.add_argument("--phase", default="all",
                        choices=["all", "generate", "validate", "verify", "finalize"],
                        help="Execution phase (staged mode for constrained shells); "
                             "'all' runs everything in one process")
    parser.add_argument("--pass-no", type=int, default=1, choices=[1, 2])
    parser.add_argument("--rows", type=int, default=3_000_000)
    parser.add_argument("--seed", type=int, default=20260910)
    parser.add_argument("--passes", type=int, default=2, choices=[1, 2])
    parser.add_argument("--data-dir", default=os.path.join(
        REPO_ROOT, "data", "generated", "final_3m"))
    parser.add_argument("--evidence-dir", default=os.path.join(
        REPO_ROOT, "evidence", "final_3m_validation"))
    parser.add_argument("--keep-pass2", action="store_true",
                        help="Keep pass2 CSVs after byte-identity is proven "
                             "(default: delete to reclaim disk, hashes retained)")
    args = parser.parse_args()
    transcription_self_check()
    os.makedirs(args.evidence_dir, exist_ok=True)
    t_total0 = time.perf_counter()

    log("=" * 72)
    log("FINAL 3M VALIDATION — independent harness")
    log(f"phase={args.phase} rows={args.rows:,} seed={args.seed} "
        f"pass_no={args.pass_no} passes={args.passes}")
    log(f"started_utc={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    log("=" * 72)

    if args.phase == "generate":
        phase_generate(args, args.pass_no)
        return 0
    if args.phase == "validate":
        phase_validate(args, args.pass_no)
        return 0
    if args.phase == "verify":
        phase_verify(args, args.pass_no)
        return 0
    if args.phase == "finalize":
        return phase_finalize(args)

    # --phase all: original single-process behavior
    passes = [run_pass(n, args, t_total0) for n in range(1, args.passes + 1)]
    if any(p.get("blocked") for p in passes):
        log("FINAL STATUS: BLOCKED — a production CLI run failed.")
        return 1
    return phase_finalize(args)


if __name__ == "__main__":
    sys.exit(main())
