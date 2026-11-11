PRAGMA foreign_keys = ON;

-- Table 1: raw data exactly as received from the machine (serial or printer)
-- Table 1: raw data exactly as received from the machine (serial or printer)
CREATE TABLE IF NOT EXISTS raw_captures (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    source       TEXT    NOT NULL CHECK (source IN ('serial', 'printer')),
    settings     TEXT,
    content      BLOB    NOT NULL,
    processed    INTEGER NOT NULL DEFAULT 0 CHECK (processed IN (0, 1))
);

-- Table 2: one row per compaction test
CREATE TABLE IF NOT EXISTS runs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_capture_id     INTEGER NOT NULL REFERENCES raw_captures(id),
    run_number         INTEGER,
    tested_at          TEXT    NOT NULL,
    target_gyrations   INTEGER,
    target_height_mm   REAL,
    stress_kpa         REAL,
    angle_deg          REAL,
    gyrations_per_min  REAL,
    mould_diameter_mm  REAL,
    firmware_version   TEXT,
    UNIQUE (run_number, tested_at)
);

-- Readable version of runs (a view: no data stored, just a friendly query)
CREATE VIEW IF NOT EXISTS readable_runs AS
SELECT
    id                 AS "Database ID",
    raw_capture_id     AS "Raw Data Link",
    run_number         AS "Batch/Run Number",
    tested_at          AS "Date and Time Tested",
    target_gyrations   AS "Target Gyrations",
    target_height_mm   AS "Target Height (mm)",
    stress_kpa         AS "Applied Pressure (kPa)",
    angle_deg          AS "Machine Angle (Degrees)",
    gyrations_per_min  AS "Gyrations per Minute",
    mould_diameter_mm  AS "Mould Size (mm)",
    firmware_version   AS "Firmware Version"
FROM runs;

-- Table 3: specimen height at the end of each gyration
CREATE TABLE IF NOT EXISTS gyrations (
    run_id           INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    gyration_number  INTEGER NOT NULL,
    height_mm        REAL    NOT NULL,
    PRIMARY KEY (run_id, gyration_number)
) WITHOUT ROWID;