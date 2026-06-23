-- Contenuti multimediali (video, PDF, doc) linkati da Google Drive
CREATE TABLE IF NOT EXISTS contenuti (
    id          SERIAL PRIMARY KEY,
    data        DATE NOT NULL,
    titolo      TEXT NOT NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('video','pdf','doc','clip_partita','report_dv')),
    categoria   TEXT NOT NULL CHECK (categoria IN ('Ricezione','Attacco','Battuta','Fisico','Partita','Vari')),
    drive_id    TEXT NOT NULL,          -- ID file/cartella Google Drive
    drive_type  TEXT NOT NULL DEFAULT 'file' CHECK (drive_type IN ('file','folder')),
    nota        TEXT,                   -- nota dell'allenatore
    gara        TEXT,                   -- es. "vs Macerata" (solo per clip/report)
    giornata    INTEGER
);

-- Note tecniche standalone dell'allenatore (non legate a un file)
CREATE TABLE IF NOT EXISTS note_coach (
    id        SERIAL PRIMARY KEY,
    data      DATE NOT NULL,
    categoria TEXT NOT NULL,
    testo     TEXT NOT NULL
);
