import sqlite3
import sys
import time
from pathlib import Path

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "loop://"
BAUD = int(sys.argv[2]) if len(sys.argv) > 2 else 9600
SECONDS = 5
DB_FILE = Path(__file__).parent / "servopac.db"


def listen(port, baud, seconds):
    """Read everything that arrives on the port for a few seconds."""
    ser = serial.serial_for_url(
        port, baudrate=baud, bytesize=8, parity="N", stopbits=1, timeout=0.5
    )
    if port == "loop://":
        ser.write(b"IPC Servopac TEST 123\r\n")  # loopback: what we send comes back

    print(f"Listening on {port} at {baud} baud for {seconds} s...")
    received = bytearray()
    end = time.time() + seconds
    while time.time() < end:
        chunk = ser.read(256)
        if chunk:
            received += chunk
            print("  HEX :", chunk.hex(" "))
            print("  TEXT:", chunk.decode("ascii", errors="replace"))
    ser.close()
    return bytes(received)


def save_capture(data):
    """Store the raw bytes in raw_captures and return the new id."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.execute(
        "INSERT INTO raw_captures (source, content) VALUES (?, ?)",
        ("serial", data),
    )
    conn.commit()
    capture_id = cur.lastrowid
    conn.close()
    return capture_id


data = listen(PORT, BAUD, SECONDS)
print(f"Done. {len(data)} bytes received.")

if data:
    capture_id = save_capture(data)
    print(f"Saved to raw_captures with id {capture_id}.")
else:
    print("Nothing received, nothing saved.")