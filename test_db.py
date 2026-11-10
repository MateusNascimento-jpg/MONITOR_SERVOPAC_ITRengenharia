import sqlite3
from pathlib import Path

FOLDER = Path(__file__).parent
schema = (FOLDER / "schema.sql").read_text(encoding="utf-8")

# Temporary database in memory: the real servopac.db is not touched
conn = sqlite3.connect(":memory:")
conn.executescript(schema)
conn.execute("PRAGMA foreign_keys = ON")

# 1. A fake raw capture
cur = conn.execute(
    "INSERT INTO raw_captures (source, content) VALUES (?, ?)",
    ("serial", b"FAKE DATA"),
)
capture_id = cur.lastrowid

# 2. A fake test
cur = conn.execute(
    """INSERT INTO runs (raw_capture_id, run_number, tested_at, target_gyrations,
                         stress_kpa, angle_deg, gyrations_per_min, mould_diameter_mm)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
    (capture_id, 7, "2026-11-10 17:30", 5, 600, 1.25, 30, 150),
)
run_id = cur.lastrowid

# 3. Five fake gyrations
heights = [(1, 120.50), (2, 118.20), (3, 116.90), (4, 116.10), (5, 115.60)]
conn.executemany(
    "INSERT INTO gyrations (run_id, gyration_number, height_mm) VALUES (?, ?, ?)",
    [(run_id, n, h) for n, h in heights],
)
conn.commit()

print("Test 1 - read the data back:")
rows = conn.execute(
    """SELECT r.run_number, r.tested_at, g.gyration_number, g.height_mm
       FROM runs r JOIN gyrations g ON g.run_id = r.id
       ORDER BY g.gyration_number"""
).fetchall()
for row in rows:
    print("  ", row)

print("Test 2 - duplicate test is blocked:")
try:
    conn.execute(
        "INSERT INTO runs (raw_capture_id, run_number, tested_at) VALUES (?, ?, ?)",
        (capture_id, 7, "2026-11-10 17:30"),
    )
    print("   FAIL: duplicate was accepted")
except sqlite3.IntegrityError as e:
    print("   OK:", e)

print("Test 3 - gyration pointing to a test that does not exist is blocked:")
try:
    conn.execute("INSERT INTO gyrations VALUES (999, 1, 100.0)")
    print("   FAIL: orphan gyration was accepted")
except sqlite3.IntegrityError as e:
    print("   OK:", e)

print("Test 4 - deleting the test also deletes its gyrations:")
conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
left = conn.execute("SELECT COUNT(*) FROM gyrations").fetchone()[0]
print("   OK" if left == 0 else "   FAIL", f"- gyrations left: {left}")

conn.close()