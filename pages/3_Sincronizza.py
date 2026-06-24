"""Pagina admin – sincronizzazione automatica Dropbox + Google Drive."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import streamlit as st
import urllib.request, json
from sqlalchemy import text
from auth import require_admin, logout_button

st.set_page_config(page_title="Sincronizza – FedeLab", layout="wide")
require_admin()
logout_button()

st.title("🔄 Sincronizza contenuti")
st.caption("Scansiona Dropbox e Google Drive e importa i nuovi file nel database, senza duplicati.")

conn = st.connection("neon", type="sql")

# ── Helpers Dropbox ───────────────────────────────────────────────────────────
DBX_TOKEN  = st.secrets.get("dropbox", {}).get("token", "")
DBX_ROOT   = st.secrets.get("dropbox", {}).get("root_path", "/__Personale2025/Federico_Volley")
DBX_HEADERS = {"Authorization": f"Bearer {DBX_TOKEN}", "Content-Type": "application/json"}

SKIP_EXT = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "heic", "heif"}

def dbx_post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), DBX_HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def dbx_list_recursive(path):
    r = dbx_post("https://api.dropboxapi.com/2/files/list_folder",
                 {"path": path, "recursive": True})
    entries = [e for e in r["entries"] if e[".tag"] == "file"]
    while r.get("has_more"):
        r = dbx_post("https://api.dropboxapi.com/2/files/list_folder/continue",
                     {"cursor": r["cursor"]})
        entries += [e for e in r["entries"] if e[".tag"] == "file"]
    return entries

def dbx_share_link(path):
    try:
        r = dbx_post(
            "https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings",
            {"path": path, "settings": {"requested_visibility": "public"}},
        )
        return r["url"].replace("?dl=0", "?raw=1")
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        if "shared_link_already_exists" in str(body):
            r = dbx_post("https://api.dropboxapi.com/2/sharing/list_shared_links",
                         {"path": path})
            return r["links"][0]["url"].replace("?dl=0", "?raw=1")
        raise

# ── Helpers Google Drive ──────────────────────────────────────────────────────
def drive_list_folder(folder_id: str, api_key: str):
    """Lista ricorsiva di una cartella Drive pubblica tramite API key."""
    results = []
    page_token = None
    while True:
        url = (
            f"https://www.googleapis.com/drive/v3/files"
            f"?q=%27{folder_id}%27+in+parents+and+trashed%3Dfalse"
            f"&fields=nextPageToken,files(id,name,mimeType,createdTime,parents)"
            f"&key={api_key}"
            + (f"&pageToken={page_token}" if page_token else "")
        )
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
        for f in data.get("files", []):
            if f["mimeType"] == "application/vnd.google-apps.folder":
                results += drive_list_folder(f["id"], api_key)
            else:
                results.append(f)
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return results

# ── Classificatori ────────────────────────────────────────────────────────────
def guess_tipo(name):
    n = name.lower()
    if n.endswith((".mp4", ".mov", ".avi", ".mkv")):
        if any(k in n for k in ["partita","gara","bologna","lagonegro","a2","orioli",
                                  "nazionale","u20","brasile","pineto","brugherio",
                                  "macerata","belluno","garlasco"]):
            return "clip_partita"
        return "video"
    if n.endswith(".pdf"):
        return "pdf"
    if n.endswith((".docx", ".doc", ".pptx")):
        return "doc"
    return "doc"

def guess_categoria(path, name):
    p = (path + name).lower()
    if any(k in p for k in ["ricezione", "rice"]):       return "Ricezione"
    if any(k in p for k in ["attacco", "spin", "taglia", "lateral", "alzata"]): return "Attacco"
    if any(k in p for k in ["battuta"]):                 return "Battuta"
    if any(k in p for k in ["fisico", "pesi", "palestra", "casa", "attrezzatura"]): return "Fisico"
    if any(k in p for k in ["partita", "gara", "bologna", "lagonegro", "orioli",
                              "nazionale", "u20", "brasile", "pineto", "brugherio",
                              "macerata", "belluno", "garlasco"]):
        return "Partita"
    return "Vari"

def folder_label(path):
    parts = path.rstrip("/").split("/")
    return parts[-2] if len(parts) >= 2 else ""

# ── UI ────────────────────────────────────────────────────────────────────────
tab_dbx, tab_drive = st.tabs(["📦 Dropbox", "📂 Google Drive"])

# ────────────────────────────────────── DROPBOX ───────────────────────────────
with tab_dbx:
    st.markdown(f"**Cartella radice:** `{DBX_ROOT}` (sottocartelle incluse)")

    if not DBX_TOKEN:
        st.warning("⚠ Token Dropbox non configurato. Aggiungilo nei Secrets di Streamlit Cloud sotto `[dropbox] token`.")
        st.stop()

    if st.button("🔄 Sincronizza Dropbox", type="primary"):
        with st.spinner("Scansione Dropbox in corso…"):
            try:
                all_entries = dbx_list_recursive(DBX_ROOT)
            except Exception as e:
                st.error(f"Errore Dropbox: {e}")
                st.stop()

        all_entries = [
            e for e in all_entries
            if e["name"].rsplit(".", 1)[-1].lower() not in SKIP_EXT
        ]
        st.info(f"Trovati **{len(all_entries)}** file in Dropbox.")

        # Carica URL già nel DB per dedup
        existing = conn.query(
            "SELECT drive_id FROM contenuti WHERE drive_type = 'dropbox'"
        )
        existing_urls = set(existing["drive_id"].tolist())

        sql = text("""
            INSERT INTO contenuti
              (data, titolo, tipo, categoria, drive_id, drive_type, nota, gara, giornata)
            VALUES
              (:data, :titolo, :tipo, :categoria, :drive_id, :drive_type, :nota, :gara, :giornata)
        """)

        salvati, saltati, errori = 0, 0, []
        prog = st.progress(0)
        log  = st.empty()

        with conn.session as s:
            for i, e in enumerate(all_entries):
                prog.progress((i + 1) / len(all_entries))
                name = e["name"]
                path = e["path_display"]
                data_str = e.get("server_modified", "2023-01-01")[:10]

                try:
                    url = dbx_share_link(path)
                except Exception as ex:
                    errori.append(f"{name}: {ex}")
                    continue

                if url in existing_urls:
                    saltati += 1
                    continue

                tipo      = guess_tipo(name)
                categoria = guess_categoria(path, name)
                fl        = folder_label(path)
                base      = name.rsplit(".", 1)[0]
                titolo    = f"{fl} – {base}" if fl and fl not in base else base

                gara = None
                for city in ["Pineto","Brugherio","Bologna","Macerata","Belluno","Garlasco"]:
                    if city.lower() in path.lower():
                        gara = city
                        break

                s.execute(sql, {
                    "data": data_str, "titolo": titolo, "tipo": tipo,
                    "categoria": categoria, "drive_id": url,
                    "drive_type": "dropbox", "nota": None,
                    "gara": gara, "giornata": None,
                })
                existing_urls.add(url)
                salvati += 1
                log.caption(f"✓ {titolo}")

            s.commit()

        prog.empty()
        log.empty()
        st.cache_data.clear()
        st.success(f"✅ **{salvati}** nuovi file importati · {saltati} già presenti · {len(errori)} errori")
        if errori:
            with st.expander("Errori"):
                for err in errori:
                    st.text(err)

# ────────────────────────────────────── GOOGLE DRIVE ─────────────────────────
with tab_drive:
    st.markdown("Inserisci l'**ID cartella** Google Drive e una **API Key** pubblica per scansionare.")

    drive_folder_id = st.text_input(
        "ID cartella Google Drive",
        help="Dall'URL: drive.google.com/drive/folders/**QUESTO_ID**"
    )
    drive_api_key = st.text_input(
        "API Key Google (con Drive API abilitata)",
        type="password",
        help="Crea una API key in console.cloud.google.com → API e servizi → Credenziali"
    )

    if st.button("🔄 Sincronizza Google Drive", type="primary",
                 disabled=not (drive_folder_id and drive_api_key)):
        with st.spinner("Scansione Google Drive in corso…"):
            try:
                files = drive_list_folder(drive_folder_id.strip(), drive_api_key.strip())
            except Exception as e:
                st.error(f"Errore Drive: {e}")
                st.stop()

        st.info(f"Trovati **{len(files)}** file in Drive.")

        existing = conn.query(
            "SELECT drive_id FROM contenuti WHERE drive_type IN ('file','folder')"
        )
        existing_ids = set(existing["drive_id"].tolist())

        sql = text("""
            INSERT INTO contenuti
              (data, titolo, tipo, categoria, drive_id, drive_type, nota, gara, giornata)
            VALUES
              (:data, :titolo, :tipo, :categoria, :drive_id, :drive_type, :nota, :gara, :giornata)
        """)

        salvati, saltati, errori = 0, 0, []
        prog = st.progress(0)
        log  = st.empty()

        with conn.session as s:
            for i, f in enumerate(files):
                prog.progress((i + 1) / len(files))
                fid   = f["id"]
                name  = f["name"]
                data_str = f.get("createdTime", "2023-01-01T00:00:00Z")[:10]

                if fid in existing_ids:
                    saltati += 1
                    continue

                tipo      = guess_tipo(name)
                categoria = guess_categoria("", name)
                titolo    = name.rsplit(".", 1)[0]

                s.execute(sql, {
                    "data": data_str, "titolo": titolo, "tipo": tipo,
                    "categoria": categoria, "drive_id": fid,
                    "drive_type": "file", "nota": None,
                    "gara": None, "giornata": None,
                })
                existing_ids.add(fid)
                salvati += 1
                log.caption(f"✓ {titolo}")

            s.commit()

        prog.empty()
        log.empty()
        st.cache_data.clear()
        st.success(f"✅ **{salvati}** nuovi file importati · {saltati} già presenti · {len(errori)} errori")
