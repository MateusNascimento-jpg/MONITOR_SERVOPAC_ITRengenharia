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
REPLY_SECONDS = 1.5


def open_port(port, baud, framing):
    """Open the serial port with one setting, e.g. 9600 and '8N1'."""
    return serial.serial_for_url(
        port,
        baudrate=baud,
        bytesize=int(framing[0]),
        parity=framing[1],
        stopbits=int(framing[2]),
        timeout=0.5,
    )


def read_for(ser, seconds):
    """Collect everything that arrives during a number of seconds."""
    received = bytearray()
    end = time.time() + seconds
    while time.time() < end:
        chunk = ser.read(256)
        if chunk:
            received += chunk
    return bytes(received)


def listen(port, baud, framing, seconds):
    """Open the port, read for a few seconds, close it."""
    ser = open_port(port, baud, framing)
    if port == "loop://":
        ser.write(b"IPC Servopac TEST 123\r\n")  # loopback: what we send comes back
    data = read_for(ser, seconds)
    ser.close()
    return data


def text_score(data):
    """Share of bytes that are readable text (0.0 to 1.0)."""
    if not data:
        return 0.0
    readable = sum(1 for b in data if 32 <= b <= 126 or b in (9, 10, 13))
    return readable / len(data)

def show(data):
    print("  HEX :", data.hex(" "))
    text = "".join(chr(b) if 32 <= b <= 126 else "." for b in data)
    print("  TEXT:", text)


def save_capture(data, settings, sent=None):
    """Store the raw bytes in raw_captures and return the new id."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.execute(
        "INSERT INTO raw_captures (source, settings, sent, content) VALUES (?, ?, ?, ?)",
        ("serial", settings, sent, data),
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


def parse_input(text):
    """Turn what was typed into bytes.

    'hex: 05 1b'  -> the bytes 05 1B
    'STATUS\\r'    -> the text STATUS followed by a carriage return
    """
    if text.lower().startswith("hex:"):
        return bytes.fromhex(text[4:])
    return text.encode("latin-1").decode("unicode_escape").encode("latin-1")


def command_mode(port, baud, framing="8N1"):
    """Type commands, send them, show and save the replies."""
    settings = f"{baud} {framing}"
    ser = open_port(port, baud, framing)
    print(f"Command mode on {port} at {settings}.")
    print(r"Type text (use \r for Enter, \x05 for a byte) or 'hex: 05 1b'.")
    print("Type 'quit' to exit.")
    try:
        while True:
            try:
                text = input("> ")
            except EOFError:
                break
            if text.strip().lower() == "quit":
                break
            if not text:
                continue
            try:
                to_send = parse_input(text)
            except ValueError as e:
                print(f"  Could not read that input: {e}")
                continue

            ser.reset_input_buffer()  # drop anything old before sending
            ser.write(to_send)
            print("  SENT:", to_send.hex(" "))

            reply = read_for(ser, REPLY_SECONDS)
            if reply:
                show(reply)
                capture_id = save_capture(reply, settings, sent=to_send)
                print(f"  Saved to raw_captures with id {capture_id}.")
            else:
                print("  No reply.")
    finally:
        ser.close()
        print("Port closed.")


# Usage:
#   python discover.py                       -> virtual loopback port, 9600 8N1
#   python discover.py COM3 9600             -> real port, one setting
#   python discover.py COM3 9600 8N2         -> real port, one setting with framing
#   python discover.py COM3 scan             -> real port, try every setting
#   python discover.py COM3 cmd 9600 8N1     -> real port, type commands
port = sys.argv[1] if len(sys.argv) > 1 else "loop://"
mode = sys.argv[2] if len(sys.argv) > 2 else "9600"

if mode == "scan":
    scan(port)
elif mode == "cmd":
    baud = int(sys.argv[3]) if len(sys.argv) > 3 else 9600
    framing = sys.argv[4] if len(sys.argv) > 4 else "8N1"
    command_mode(port, baud, framing)
else:
    framing = sys.argv[3] if len(sys.argv) > 3 else "8N1"
    single(port, int(mode), framing)