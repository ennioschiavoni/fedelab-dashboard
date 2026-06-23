"""Inserisce le 7 cartelle Drive nel DB FedeLab."""
import pathlib, sys
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
from sqlalchemy import create_engine, text

cfg = tomllib.loads(pathlib.Path(".streamlit/secrets.toml").read_text())
url = cfg["connections"]["neon"]["url"]
engine = create_engine(url)

contenuti = [
    {
        "data": "2026-04-22",
        "titolo": "FEDE – Video 22 Apr",
        "tipo": "video",
        "categoria": "Vari",
        "drive_id": "1rNrgAY6-MVRVpjMGZYbmsxqqSTJOq8Tu",
        "drive_type": "folder",
        "nota": "Sessione del 22 aprile: ricezione (Fede Rice 1-2-3), spin (Fede Spin 1-2-3), modelli.",
        "gara": None, "giornata": None,
    },
    {
        "data": "2026-04-27",
        "titolo": "Fede Spin – Adriano",
        "tipo": "video",
        "categoria": "Attacco",
        "drive_id": "1QDVIFk0rFN8qoRjwV-CmtXds9uai8UeP",
        "drive_type": "folder",
        "nota": "Spin con Adriano: gioco, rallenty frontale, mix. Lavoro sulla rotazione del polso.",
        "gara": None, "giornata": None,
    },
    {
        "data": "2026-06-01",
        "titolo": "Set ricezione",
        "tipo": "video",
        "categoria": "Ricezione",
        "drive_id": "1HYJRiiPamIXM5rzqRNx-iLIkqISkms4K",
        "drive_type": "folder",
        "nota": "Affondi, spin addosso, float con pallone. Focus posizione base e lettura traiettoria.",
        "gara": None, "giornata": None,
    },
    {
        "data": "2026-04-17",
        "titolo": "Video Allenamento 1",
        "tipo": "video",
        "categoria": "Vari",
        "drive_id": "1hPqIR0rou-xyh2LeHnc6uARmhsPhM_On",
        "drive_type": "folder",
        "nota": "Prima sessione completa: divaricata e angoli, ricezione, spin, SN in 4.",
        "gara": None, "giornata": None,
    },
    {
        "data": "2026-04-14",
        "titolo": "Programma Pesi – Estate 2026",
        "tipo": "pdf",
        "categoria": "Fisico",
        "drive_id": "1qCJuDiQfc4MjGw4VTEGnYwTOp7zKuzMp",
        "drive_type": "folder",
        "nota": "Scheda pesi estiva preparata con Ale. Contiene PDF + video dimostrativi.",
        "gara": None, "giornata": None,
    },
    {
        "data": "2026-04-19",
        "titolo": "Tagli A2 – Ricezione e Servizio",
        "tipo": "clip_partita",
        "categoria": "Partita",
        "drive_id": "1cU5KAtaTEGXnyih3zmnfbcA5jPrd2ihh",
        "drive_type": "folder",
        "nota": "Ultimi 4 turni A2: ricezione (301 MB) e servizio (84 MB). Analisi da fare insieme.",
        "gara": "Last 4 A2", "giornata": None,
    },
    {
        "data": "2026-04-19",
        "titolo": "Video Vari – Spin e Attacchi Lagonegro",
        "tipo": "video",
        "categoria": "Vari",
        "drive_id": "1Joa_EXT8PfybVWdi0ezlpRivBvq9LNB0",
        "drive_type": "folder",
        "nota": "Spin rallenty (due versioni qualità), attacchi vs Lagonegro in alta risoluzione.",
        "gara": "vs Lagonegro", "giornata": None,
    },
]

sql = text("""
    INSERT INTO contenuti (data, titolo, tipo, categoria, drive_id, drive_type, nota, gara, giornata)
    VALUES (:data, :titolo, :tipo, :categoria, :drive_id, :drive_type, :nota, :gara, :giornata)
""")

with engine.begin() as c:
    for r in contenuti:
        c.execute(sql, r)

print(f"✅ {len(contenuti)} cartelle inserite nel DB FedeLab.")
