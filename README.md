# MONITOR_SERVOPAC_ITRengenharia
 
Tools to read compaction data from ITR Engenharia's **ELE-SERVOPAC gyratory compactor** (made by Industrial Process Controls Ltd, Melbourne) and store it in a local SQLite database.
 
**Status:** the database and the serial discovery tool are ready and tested on a virtual port. They have not been connected to the machine yet.
 
---
 
## What we know about the machine
 
From the IPC Servopac operating manual (firmware 2.04, 2005) and the IPC Global brochure:
 
- **Rear ports:** `SERIAL I/O` (DB-9, RS-232), `PRINTER` (DB-25, parallel), `PENDANT` (DB-25, may be missing on our unit).
- **Serial port:** a "coded data interface" for monitoring and control. The machine most likely waits for commands instead of sending data on its own.
- **Original PC software:** "PC-Based Servopac Monitor" (Windows 98/XP). It saves test data as readable ASCII text files. We don't have it; it has been requested from Controls Group.
- **Stored data:** the last 12 tests in non-volatile memory, with the specimen height at the end of every gyration.
- **Test parameters:** date/time, number of gyrations, target height, vertical stress (kPa), angle (degrees), gyrations per minute, mould diameter (100 or 150 mm). Each test gets a run number.
- **Pendant:** optional if a PC is permanently assigned to the machine. Printing is started from the pendant (hold ENTER until a double beep).
---
 
## Files
 
| File | What it does |
|---|---|
| `schema.sql` | Database structure (tables and view) |
| `create_db.py` | Creates `servopac.db` from `schema.sql` |
| `test_db.py` | Tests the structure in a temporary in-memory database |
| `show_db.py` | Shows the tables, columns and row counts of `servopac.db` |
| `discover.py` | Serial discovery tool: listen, scan and command modes |
 
`servopac.db` is not stored on GitHub (see `.gitignore`). Recreate it with `python create_db.py`.
 
---
 
## Setup
 
Requires Python 3.
 
```
pip install pyserial
python create_db.py
python test_db.py
```
 
If `schema.sql` changes, delete `servopac.db` and run `python create_db.py` again.
 
---
 
## Database
 
| Table | Content |
|---|---|
| `raw_captures` | Everything received, exactly as it arrived: source, serial settings, bytes sent, bytes received |
| `runs` | One row per compaction test (parameters and run number) |
| `gyrations` | One row per gyration: specimen height in mm |
| `readable_runs` (view) | `runs` with friendly column names |
 
`runs` and `gyrations` will be filled by a parser, written once we see real data from the machine.
 
---
 
## discover.py
 
```
python discover.py                       # virtual loopback port, 9600 8N1
python discover.py COM3 9600             # listen on a real port, one setting
python discover.py COM3 9600 8N2         # same, with a different framing
python discover.py COM3 scan             # try 18 settings, 3 s each (about 1 minute)
python discover.py COM3 cmd 9600 8N1     # type commands and see the replies
```
 
In command mode:
 
- Text with escapes: `\r` = Enter (0D), `\n` = line feed (0A), `\x05` = any byte by hex code. Nothing is added automatically.
- Raw bytes: `hex: 05 1b`
- `quit` to exit.
Every non-empty reply is saved in `raw_captures`, with the settings used and the bytes sent.
 
---
 
## Test-day guide
 
### Bring
 
- [ ] PC with this project, Python and pyserial installed
- [ ] USB-to-RS232 adapter (FTDI chipset)
- [ ] Null-modem adapter (DB-9)
- [ ] DB-9 extension cable
- [ ] A paperclip or jumper wire (for the adapter loopback test)
- [ ] Phone camera
### Safety rules
 
- The machine is operated only by lab staff who normally run it.
- Do not open the machine or remove covers.
- Do not enter calibration mode or change any machine setting.
- Send commands only with the machine idle, no mould loaded, and someone next to the emergency stop.
### Step 1: Record the machine
 
- [ ] Photograph the rear panel and the nameplate.
- [ ] Check whether there is a `PENDANT` port and a pendant (keypad with display).
- [ ] If there is a pendant: note the firmware version shown at power-up ("IPC Servopac" followed by the version).
- [ ] Note how the machine is operated today: pendant, PC, or both.
### Step 2: Start with a clean database
 
```
Remove-Item servopac.db
python create_db.py
```
 
### Step 3: Check the adapter alone
 
1. Plug the adapter into the PC and find its port:
```
   python -m serial.tools.list_ports -v
```
   Note the `COMx` name and confirm the description mentions FTDI.
2. Short pins 2 and 3 on the adapter's DB-9 connector with the paperclip.
3. Send a test:
```
   python discover.py COM3 cmd 9600 8N1
```
   Type `HELLO\r\n`. The same bytes must come back. If they do, the adapter works.
4. Remove the paperclip. Delete and recreate the database (Step 2) to remove the test rows.
 
### Step 4: Listen to the machine
 
1. Connect the adapter to `SERIAL I/O` with the straight cable.
2. With the machine powered on and idle:
```
   python discover.py COM3 scan
```
3. Run the scan again while lab staff run a normal compaction test.
4. If nothing arrives on any setting: add the null-modem adapter and repeat 2 and 3.
### Step 5: Try a few commands (only if Step 4 received nothing)
 
Machine idle, no mould, someone at the emergency stop. Use the setting with the best result from the scan, or 9600 8N1:
 
```
python discover.py COM3 cmd 9600 8N1
```
 
Try, one at a time: `\r`, `hex: 05`, `?\r`. These are guesses; the real commands are not published. Try both cable types.
 
### Step 6: Save the results
 
- [ ] Copy `servopac.db` to a safe place (USB drive or cloud).
- [ ] Write down which cable (straight or null-modem) and which setting gave results.
### Reading the results
 
| What you see | What it means | Next step |
|---|---|---|
| Readable text at one setting | Found the right speed and framing | Capture full tests with that setting; write the parser |
| Data at every setting, all garbage | Binary protocol, or a framing not in the list | Keep the raw captures and analyze the HEX |
| Nothing at any setting, both cables | The machine waits for a command | Command mode, the original software, or the printer route |
| Commands get replies | The machine is answering | Save everything; map commands to replies |
 
---
 
## Open items
 
- Get the "PC-Based Servopac Monitor" software and its reference manual (requested from Controls Group).
- Confirm whether our unit has a pendant.
- Write the parser once real data is captured.
- Printer route (ESP32 capture of the `PRINTER` port) as a backup, only if there is a pendant to start printing.
