import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent / "servopac.db"

# Columns of the runs table that decode() is allowed to fill
RUN_FIELDS = (
    "run_number",
    "tested_at",
    "target_gyrations",
    "target_height_mm",
    "stress_kpa",
    "angle_deg",
    "gyrations_per_min",
    "mould_diameter_mm",
    "firmware_version",
)


def decode(content):
    """Turn the raw bytes of one capture into a list of tests.

    Each test is a dict:
        {"run": {"run_number": 7, "tested_at": "2026-11-10 17:30", ...},
         "gyrations": [(1, 120.50), (2, 118.20), ...]}

    Return an empty list if the bytes are not in a known format.

    *** THIS IS THE ONLY PART TO REWRITE WHEN WE SEE REAL MACHINE DATA. ***
    For now it only understands an INVENTED example format:

        RUN 7
        DATE 2026-11-10 17:30
        STRESS 600
        ANGLE 1.25
        GYR 1 120.50
        GYR 2 118.20
        END
    """
    text = content.decode("ascii", errors="replace")
    if not text.startswith("RUN "):
        return []

    tests = []
    run, gyrations = {}, []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        key = parts[0]
        if key == "RUN":
            run, gyrations = {"run_number": int(parts[1])}, []
        elif key == "DATE":
            run["tested_at"] = f"{parts[1]} {parts[2]}"
        elif key == "STRESS":
            run["stress_kpa"] = float(parts[1])
        elif key == "ANGLE":
            run["angle_deg"] = float(parts[1])
        elif key == "GYR":
            gyrations.append((int(parts[1]), float(parts[2])))
        elif key == "END":
            tests.append({"run": run, "gyrations": gyrations})
    return tests


def save_test(conn, capture_id, test):
    """Insert one test and its gyrations. Return False if it already exists."""
    run = {k: v for k, v in test["run"].items() if k in RUN_FIELDS}

    existing = conn.execute(
        "SELECT id FROM runs WHERE run_number = ? AND tested_at = ?",
        (run.get("run_number"), run.get("tested_at")),
    ).fetchone()
    if existing:
        return False

    columns = ["raw_capture_id"] + list(run)
    values = [capture_id] + list(run.values())
    placeholders = ", ".join("?" for _ in columns)
    cur = conn.execute(
        f"INSERT INTO runs ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )
    run_id = cur.lastrowid

    conn.executemany(
        "INSERT INTO gyrations (run_id, gyration_number, height_mm) VALUES (?, ?, ?)",
        [(run_id, n, h) for n, h in test["gyrations"]],
    )
    return True


def process_all(conn):
    """Decode every unprocessed capture and save what is recognized."""
    captures = conn.execute(
        "SELECT id, content FROM raw_captures WHERE processed = 0 ORDER BY id"
    ).fetchall()
    summary = {"captures": len(captures), "saved": 0, "duplicates": 0,
               "not_recognized": 0, "errors": 0}

    for capture_id, content in captures:
        try:
            tests = decode(content)
        except (ValueError, IndexError) as e:
            print(f"  capture {capture_id}: error while decoding: {e}")
            summary["errors"] += 1
            continue

        if not tests:
            print(f"  capture {capture_id}: format not recognized, left unprocessed")
            summary["not_recognized"] += 1
            continue

        try:
            with conn:  # one transaction: all of this capture is saved, or nothing
                for test in tests:
                    if save_test(conn, capture_id, test):
                        summary["saved"] += 1
                    else:
                        summary["duplicates"] += 1
                conn.execute(
                    "UPDATE raw_captures SET processed = 1 WHERE id = ?",
                    (capture_id,),
                )
            print(f"  capture {capture_id}: {len(tests)} test(s) processed")
        except sqlite3.Error as e:
            print(f"  capture {capture_id}: database error: {e}")
            summary["errors"] += 1

    return summary


if __name__ == "__main__":
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    print("Processing raw captures...")
    result = process_all(conn)
    conn.close()
    print(
        f"Done. {result['captures']} capture(s) checked: "
        f"{result['saved']} test(s) saved, {result['duplicates']} duplicate(s), "
        f"{result['not_recognized']} not recognized, {result['errors']} error(s)."
    )