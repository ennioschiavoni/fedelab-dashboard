"""Pagina admin — note tecniche standalone."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
import streamlit as st
from sqlalchemy import text
from auth import require_admin, logout_button

st.set_page_config(page_title="Note Coach – FedeLab", layout="centered")
require_admin()
logout_button()
st.title("📝 Note Allenatore")

conn = st.connection("neon", type="sql")

col1, col2 = st.columns(2)
data      = col1.date_input("Data")
categoria = col2.selectbox("Categoria", ["Ricezione","Attacco","Battuta","Fisico","Partita","Vari"])
testo     = st.text_area("Nota", height=150)

if st.button("💾 Salva nota", type="primary", disabled=not testo.strip()):
    with conn.session as s:
        s.execute(text(
            "INSERT INTO note_coach (data, categoria, testo) VALUES (:d,:c,:t)"
        ), {"d": data, "c": categoria, "t": testo.strip()})
        s.commit()
    st.cache_data.clear()
    st.success("Nota salvata.")
    st.rerun()

st.divider()
df = conn.query("SELECT * FROM note_coach ORDER BY data DESC")
if df.empty:
    st.info("Nessuna nota ancora.")
    st.stop()

for _, r in df.iterrows():
    with st.expander(f"📝 {r['categoria']}  ·  {r['data']}"):
        st.markdown(r["testo"])
        if st.button("🗑 Elimina", key=f"del_{r['id']}"):
            with conn.session as s:
                s.execute(text("DELETE FROM note_coach WHERE id = :id"), {"id": int(r["id"])})
                s.commit()
            st.cache_data.clear()
            st.rerun()
