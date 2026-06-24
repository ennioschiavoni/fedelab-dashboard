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
    if drive_type == "dropbox":
        return None  # Dropbox non supporta embed — usiamo link diretto
    if drive_type == "folder":
        return f"https://drive.google.com/embeddedfolderview?id={drive_id}#list"
    return f"https://drive.google.com/file/d/{drive_id}/preview"

def render_content(drive_id, drive_type, titolo):
    if drive_type == "dropbox":
        # Dropbox: mostra link diretto
        url = drive_id  # per dropbox salviamo l'URL direttamente
        st.markdown(f"[📥 Apri / Scarica: {titolo}]({url})")
    else:
        url = drive_embed(drive_id, drive_type)
        if url:
            st.components.v1.iframe(url, height=420, scrolling=True)
            base = "https://drive.google.com/drive/folders" if drive_type == "folder" else "https://drive.google.com/file/d"
            st.caption(f"[Apri in Google Drive ↗]({base}/{drive_id})")

# ── Home ──────────────────────────────────────────────────────────────────────
st.title("🏐 Federico Roberti — Lab 2026")

df_c = load_contenuti()
df_n = load_note()

if df_c.empty and df_n.empty:
    st.info("Nessun contenuto ancora caricato. L'allenatore aggiungerà presto materiale.")
    st.stop()

# ── Sidebar – filtri ──────────────────────────────────────────────────────────
TYPE_MAP = {
    "Video": ["video", "clip_partita"],
    "PDF":   ["pdf", "report_dv"],
    "Word":  ["doc"],
}

with st.sidebar:
    st.markdown("### 🔍 Filtri")

    st.markdown("**Tipologia**")
    tipi_sel = [t for t in TYPE_MAP if st.checkbox(t, value=True, key=f"tipo_{t}")]

    st.markdown("**Anno**")
    anni_db = sorted(
        df_c["data"].apply(lambda d: pd.to_datetime(d).year).unique().tolist()
    ) if not df_c.empty else []
    anni_range = list(range(2020, 2027))
    anni_sel = [a for a in anni_range if st.checkbox(str(a), value=(a in anni_db), key=f"anno_{a}")]

# ── Applica filtri a df_c ─────────────────────────────────────────────────────
tipi_interni = [t for label in tipi_sel for t in TYPE_MAP[label]]
if not df_c.empty:
    if tipi_sel:
        df_c = df_c[df_c["tipo"].isin(tipi_interni)]
    if anni_sel:
        df_c = df_c[df_c["data"].apply(lambda d: pd.to_datetime(d).year).isin(anni_sel)]

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
            if item["nota"] and str(item["nota"]) not in ("", "nan", "None"):
                st.info(f"💬 **Nota allenatore:** {item['nota']}")
            if item["drive_id"]:
                render_content(item["drive_id"], item.get("drive_type","file"), item["titolo"])

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
                    if r.get("nota") and str(r["nota"]) not in ("", "nan", "None"):
                        st.info(f"💬 **Nota allenatore:** {r['nota']}")
                    render_content(r["drive_id"], r.get("drive_type","file"), r["titolo"])
