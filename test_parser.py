import sqlite3
from pathlib import Path

from parser import process_all

FOLDER = Path(__file__).parent
schema = (FOLDER / "schema.sql").read_text(encoding="utf-8")

# Temporary database in memory: the real servopac.db is not touched
conn = sqlite3.connect(":memory:")
conn.executescript(schema)
conn.execute("PRAGMA foreign_keys = ON")

EXAMPLE = (
    b"RUN 7\r\n"
    b"DATE 2026-11-10 17:30\r\n"
    b"STRESS 600\r\n"
    b"ANGLE 1.25\r\n"
    b"GYR 1 120.50\r\n"
    b"GYR 2 118.20\r\n"
    b"GYR 3 116.90\r\n"
    b"END\r\n"
)


def add_capture(content):
    conn.execute(
        "INSERT INTO raw_captures (source, content) VALUES (?, ?)",
        ("serial", content),
    )
    conn.commit()


def check(name, condition):
    print(f"{'OK  ' if condition else 'FAIL'} {name}")


add_capture(EXAMPLE)            # capture 1: valid test
add_capture(EXAMPLE)            # capture 2: the same test again
add_capture(b"garbage")         # capture 3: unknown format
add_capture(b"RUN x\r\nEND\r\n")  # capture 4: right format, broken value

print("Running the parser:")
result = process_all(conn)
print()

runs = conn.execute("SELECT run_number, tested_at, stress_kpa, angle_deg FROM runs").fetchall()
heights = conn.execute("SELECT gyration_number, height_mm FROM gyrations ORDER BY 1").fetchall()
processed = dict(conn.execute("SELECT id, processed FROM raw_captures").fetchall())

check("Test 1 - one test saved with the right values",
      runs == [(7, "2026-11-10 17:30", 600.0, 1.25)])
check("Test 2 - its 3 gyrations saved in order",
      heights == [(1, 120.5), (2, 118.2), (3, 116.9)])
check("Test 3 - the repeated test was skipped as a duplicate",
      result["duplicates"] == 1)
check("Test 4 - valid captures marked as processed",
      processed[1] == 1 and processed[2] == 1)
check("Test 5 - unknown and broken captures left unprocessed",
      processed[3] == 0 and processed[4] == 0)

second = process_all(conn)
check("Test 6 - running again does not save anything twice",
      second["saved"] == 0 and conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1)

conn.close()