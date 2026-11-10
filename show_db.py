import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent / "servopac.db"

conn = sqlite3.connect(DB_FILE)

objects = conn.execute(
    """SELECT type, name FROM sqlite_master
       WHERE name NOT LIKE 'sqlite_%'
       ORDER BY type, name"""
).fetchall()

for obj_type, name in objects:
    count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
    print(f"\n[{obj_type.upper()}] {name}  ({count} rows)")
    for col in conn.execute(f'PRAGMA table_info("{name}")'):
        cid, col_name, col_type, notnull, default, pk = col
        flags = []
        if pk:
            flags.append("PK")
        if notnull:
            flags.append("NOT NULL")
        print(f"   - {col_name:<25} {col_type:<8} {' '.join(flags)}")

conn.close()