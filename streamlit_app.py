import streamlit as st
import pandas as pd
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from auth import require_login, logout_button, is_admin

st.set_page_config(page_title="Federico Roberti – Lab 2026", layout="wide")
require_login()
logout_button()

conn = st.connection("neon", type="sql")

@st.cache_data(ttl=60)
def load_contenuti() -> pd.DataFrame:
    return conn.query("SELECT * FROM contenuti ORDER BY data DESC")

@st.cache_data(ttl=60)
def load_note() -> pd.DataFrame:
    return conn.query("SELECT * FROM note_coach ORDER BY data DESC")

ICONS = {
    "video": "🎥", "clip_partita": "📹", "pdf": "📄",
    "doc": "📝", "report_dv": "📊",
}
CAT_ICONS = {
    "Ricezione": "🤲", "Attacco": "💥", "Battuta": "🏐",
    "Fisico": "💪", "Partita": "🏟", "Vari": "📁",
}

def drive_embed(drive_id: str, drive_type: str) -> str:
    if drive_type == "folder":
        return f"https://drive.google.com/embeddedfolderview?id={drive_id}#list"
    return f"https://drive.google.com/file/d/{drive_id}/preview"

# ── Home ──────────────────────────────────────────────────────────────────────
st.title("🏐 Federico Roberti — Lab 2026")

df_c = load_contenuti()
df_n = load_note()

if df_c.empty and df_n.empty:
    st.info("Nessun contenuto ancora caricato. L'allenatore aggiungerà presto materiale.")
    st.stop()

# ── KPI rapidi ────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Video / Clip", len(df_c[df_c["tipo"].isin(["video","clip_partita"])]))
c2.metric("Documenti",    len(df_c[df_c["tipo"].isin(["pdf","doc","report_dv"])]))
c3.metric("Note coach",   len(df_n))
c4.metric("Categorie",    df_c["categoria"].nunique() if not df_c.empty else 0)

st.divider()

# ── Timeline ──────────────────────────────────────────────────────────────────
st.subheader("📅 Ultimi contenuti")

# Mostra gli ultimi 10 elementi (video + note) ordinati per data
items = []
for _, r in df_c.head(10).iterrows():
    items.append({
        "data": r["data"], "titolo": r["titolo"],
        "tipo": r["tipo"], "categoria": r["categoria"],
        "drive_id": r["drive_id"], "drive_type": r["drive_type"],
        "nota": r.get("nota",""), "kind": "contenuto",
    })
for _, r in df_n.head(5).iterrows():
    items.append({
        "data": r["data"], "titolo": "📝 Nota coach",
        "tipo": "doc", "categoria": r["categoria"],
        "drive_id": None, "nota": r["testo"], "kind": "nota",
    })

items = sorted(items, key=lambda x: str(x["data"]), reverse=True)[:10]

for item in items:
    icon = ICONS.get(item["tipo"], "📁")
    cat_icon = CAT_ICONS.get(item["categoria"], "📁")
    with st.expander(f"{icon} {item['titolo']}  ·  {cat_icon} {item['categoria']}  ·  {item['data']}"):
        if item["kind"] == "nota":
            st.markdown(item["nota"])
        else:
            if item["nota"]:
                st.info(f"💬 **Nota allenatore:** {item['nota']}")
            if item["drive_id"]:
                url = drive_embed(item["drive_id"], item.get("drive_type","file"))
                st.components.v1.iframe(url, height=420, scrolling=True)
                st.caption(f"[Apri in Google Drive ↗](https://drive.google.com/{'drive/folders' if item.get('drive_type')=='folder' else 'file/d'}/{item['drive_id']})")

# ── Per categoria ─────────────────────────────────────────────────────────────
if not df_c.empty:
    st.divider()
    st.subheader("📂 Per fondamentale")
    cats = sorted(df_c["categoria"].unique())
    tabs = st.tabs([f"{CAT_ICONS.get(c,'📁')} {c}" for c in cats])
    for tab, cat in zip(tabs, cats):
        with tab:
            sub = df_c[df_c["categoria"] == cat]
            for _, r in sub.iterrows():
                icon = ICONS.get(r["tipo"], "📁")
                with st.expander(f"{icon} {r['titolo']}  ·  {r['data']}"):
                    if r.get("nota"):
                        st.info(f"💬 **Nota allenatore:** {r['nota']}")
                    url = drive_embed(r["drive_id"], r.get("drive_type","file"))
                    st.components.v1.iframe(url, height=420, scrolling=True)
                    st.caption(f"[Apri in Google Drive ↗](https://drive.google.com/{'drive/folders' if r.get('drive_type')=='folder' else 'file/d'}/{r['drive_id']})")
