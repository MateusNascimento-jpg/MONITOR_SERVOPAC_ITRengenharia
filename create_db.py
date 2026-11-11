import sqlite3 
from pathlib import Path 

#Conect to the database  
FOLDER = Path(__file__).parent
DB_FILE = FOLDER / "servopac.db"
SCHEMA_FILE = FOLDER / "schema.sql"     

schema = SCHEMA_FILE.read_text(encoding="utf-8") 

conn = sqlite3.connect(DB_FILE) 
conn.executescript(schema)
tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()
conn.close()

print(f"Database is ready: {DB_FILE}" ) 
print("Tables", [t[0] for t in tables]) 