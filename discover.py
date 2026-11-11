import sqlite3
import sys
import time
from pathlib import Path

import serial

DB_FILE = Path(__file__).parent / "servopac.db"

# Settings tried in scan mode
BAUD_RATES = [1200, 2400, 4800, 9600, 19200, 38400]
FRAMINGS = ["8N1", "8N2", "7E1"]
SCAN_SECONDS = 3


def listen(port, baud, framing, seconds):
    """Read everything that arrives on the port for a few seconds."""
    ser = serial.serial_for_url(
        port,
        baudrate=baud,
        bytesize=int(framing[0]),
        parity=framing[1],
        stopbits=int(framing[2]),
        timeout=0.5,
    )
    if port == "loop://":
        ser.write(b"IPC Servopac TEST 123\r\n")  # loopback: what we send comes back

    received = bytearray()
    end = time.time() + seconds
    while time.time() < end:
        chunk = ser.read(256)
        if chunk:
            received += chunk
    ser.close()
    return bytes(received)


def text_score(data):
    """Share of bytes that are readable text (0.0 to 1.0)."""
    if not data:
        return 0.0
    readable = sum(1 for b in data if 32 <= b <= 126 or b in (9, 10, 13))
    return readable / len(data)


def show(data):
    print("  HEX :", data.hex(" "))
    print("  TEXT:", data.decode("ascii", errors="replace"))


def save_capture(data, settings):
    """Store the raw bytes in raw_captures and return the new id."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.execute(
        "INSERT INTO raw_captures (source, settings, content) VALUES (?, ?, ?)",
        ("serial", settings, data),
    )
    conn.commit()
    capture_id = cur.lastrowid
    conn.close()
    return capture_id


def single(port, baud, framing="8N1", seconds=5):
    """Listen once with one setting."""
    settings = f"{baud} {framing}"
    print(f"Listening on {port} at {settings} for {seconds} s...")
    data = listen(port, baud, framing, seconds)
    print(f"Done. {len(data)} bytes received.")
    if data:
        show(data)
        capture_id = save_capture(data, settings)
        print(f"Saved to raw_captures with id {capture_id}.")
    else:
        print("Nothing received, nothing saved.")


def scan(port):
    """Try every baud rate and framing, save what arrives, rank the results."""
    total = len(BAUD_RATES) * len(FRAMINGS)
    print(f"Scanning {port}: {total} settings, {SCAN_SECONDS} s each...")
    results = []
    for baud in BAUD_RATES:
        for framing in FRAMINGS:
            settings = f"{baud} {framing}"
            data = listen(port, baud, framing, SCAN_SECONDS)
            score = text_score(data)
            line = f"  {settings:<11} {len(data):>5} bytes   text {score:>4.0%}"
            if data:
                capture_id = save_capture(data, settings)
                line += f"   saved id {capture_id}"
            print(line)
            results.append((score, len(data), settings, data))

    best = max(results)
    if best[1] == 0:
        print("\nNothing received on any setting.")
    else:
        print(f"\nBest guess: {best[2]} ({best[0]:.0%} readable text)")
        show(best[3])


# Usage:
#   python discover.py                 -> virtual loopback port, 9600 8N1
#   python discover.py COM3 9600       -> real port, one setting
#   python discover.py COM3 9600 8N2   -> real port, one setting with framing
#   python discover.py COM3 scan       -> real port, try every setting
port = sys.argv[1] if len(sys.argv) > 1 else "loop://"
mode = sys.argv[2] if len(sys.argv) > 2 else "9600"

if mode == "scan":
    scan(port)
else:
    framing = sys.argv[3] if len(sys.argv) > 3 else "8N1"
    single(port, int(mode), framing)