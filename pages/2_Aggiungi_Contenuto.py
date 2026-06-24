"""Pagina admin — aggiunge video, PDF, doc, clip, report DV."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
import streamlit as st
from sqlalchemy import text
from auth import require_admin, logout_button
import re

st.set_page_config(page_title="Aggiungi Contenuto – FedeLab", layout="centered")
require_admin()
logout_button()
st.title("➕ Aggiungi contenuto")

conn = st.connection("neon", type="sql")

def extract_drive_id(url_or_id: str) -> tuple[str, str]:
    """
    Estrae (drive_id, drive_type) da un URL Google Drive o da un ID grezzo.
    drive_type = 'folder' | 'file'
    """
    s = url_or_id.strip()
    # Cartella
    m = re.search(r"drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)", s)
    if m:
        return m.group(1), "folder"
    # File /file/d/ID
    m = re.search(r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)", s)
    if m:
        return m.group(1), "file"
    # open?id=ID
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", s)
    if m:
        return m.group(1), "file"
    # ID grezzo (solo alfanumerico + trattini/underscore, >10 chars)
    if re.match(r"^[a-zA-Z0-9_-]{10,}$", s):
        return s, "file"
    return "", "file"

st.subheader("Dati del contenuto")

col1, col2 = st.columns(2)
data    = col1.date_input("Data")
categoria = col2.selectbox("Categoria", ["Ricezione","Attacco","Battuta","Fisico","Partita","Vari"])

titolo  = st.text_input("Titolo (es. 'Trave 22 Apr – Attacco in diagonale')")
tipo    = st.selectbox("Tipo", ["video","clip_partita","pdf","doc","report_dv"],
                       format_func=lambda x: {
                           "video":"🎥 Video allenamento",
                           "clip_partita":"📹 Clip partita",
                           "pdf":"📄 PDF",
                           "doc":"📝 Documento",
                           "report_dv":"📊 Report DataVolley",
                       }[x])

drive_url = st.text_input(
    "Link o ID Google Drive",
    help="Incolla il link di condivisione del file o della cartella Drive"
)

gara     = st.text_input("Gara (es. 'vs Macerata')  — solo per clip/report", "")
giornata = st.number_input("Giornata", 0, 30, 0)

nota = st.text_area("Nota allenatore (visibile a Federico)", height=100)

# Anteprima embed
if drive_url:
    did, dtype = extract_drive_id(drive_url)
    if did:
        st.caption(f"ID estratto: `{did}` · tipo: `{dtype}`")
        preview_url = (
            f"https://drive.google.com/embeddedfolderview?id={did}#list"
            if dtype == "folder"
            else f"https://drive.google.com/file/d/{did}/preview"
        )
        with st.expander("Anteprima embed"):
            st.components.v1.iframe(preview_url, height=380, scrolling=True)
    else:
        st.warning("URL non riconosciuto. Verifica il link Drive.")
        did, dtype = "", "file"
else:
    did, dtype = "", "file"

st.divider()
if st.button("💾 Salva", type="primary", disabled=not (titolo and did)):
    with conn.session as s:
        s.execute(text("""
            INSERT INTO contenuti (data, titolo, tipo, categoria, drive_id, drive_type, nota, gara, giornata)
            VALUES (:data, :titolo, :tipo, :cat, :did, :dtype, :nota, :gara, :giornata)
        """), {
            "data": data, "titolo": titolo.strip(), "tipo": tipo,
            "cat": categoria, "did": did, "dtype": dtype,
            "nota": nota.strip() or None,
            "gara": gara.strip() or None,
            "giornata": int(giornata) if giornata else None,
        })
        s.commit()
    st.cache_data.clear()
    st.success(f"✅ '{titolo}' aggiunto.")
    st.rerun()

# ── Lista esistenti ───────────────────────────────────────────────────────────
st.divider()
st.subheader("Contenuti inseriti")
df = conn.query("SELECT id, data, titolo, tipo, categoria, gara FROM contenuti ORDER BY data DESC")
if df.empty:
    st.info("Nessun contenuto ancora.")
else:
    st.dataframe(df, hide_index=True, width="stretch")

    st.subheader("Elimina contenuto")
    del_id = st.selectbox("ID da eliminare", df["id"].tolist(),
                          format_func=lambda i: f"ID {i} — {df.set_index('id').loc[i,'titolo']}")
    if st.button("🗑 Elimina", type="secondary"):
        with conn.session as s:
            s.execute(text("DELETE FROM contenuti WHERE id = :id"), {"id": int(del_id)})
            s.commit()
        st.cache_data.clear()
        st.success("Eliminato.")
        st.rerun()
