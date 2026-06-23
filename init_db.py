"""Crea le tabelle su Neon (esegui una volta sola)."""
import sys, pathlib
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
from sqlalchemy import create_engine, text

cfg = tomllib.loads(pathlib.Path(".streamlit/secrets.toml").read_text())
url = cfg["connections"]["neon"]["url"]
engine = create_engine(url)
with engine.connect() as c:
    c.execute(text(pathlib.Path("schema.sql").read_text()))
    c.commit()
print("✅ Schema FedeLab caricato su Neon.")
