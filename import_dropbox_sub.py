"""
Importa ricorsivamente U20-Federico-Brasile e Taglia A3 dal Dropbox di Ennio.
"""
import urllib.request, json, pathlib
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
from sqlalchemy import create_engine, text

TOKEN = 'sl.u.AGmBUyU9PGWfHT2UjrT1R9gR7511Vg2dGWLGsTiAeD7zazxnpoC579dkQVr_MbeP7d-8sqS9FCdMgUjQ_S0cGecaKVx_ReWeZ8gZEcOp2iLJFNav9hgOVNCYImGpvguuryeh_oxnOqX6vBF1dsb0zZQFCzPO3MXN-D_YroXFH4K8YTPO-KTh7vr5EJzgf9zJPYMXUHvgrnF-9KtVFGlc1a6Jb-rKKwH_ROqIgn6NXBYPqXsCuPSOsBdPM8qMV9-b-CiwD21h7GX-_6V-PaokK6M31s6YsRCwK4tPjl66Darun2tN1AaF9H0YzDD4FOdD4p4pt4-IdU9WaAD5UBE0-LncVO-oa1arU3F_qZOHxP31r2xnK9WVGbmt9DnfWJ_ZHyGf-xpeAB_PtwxPwGnFPIZNCCF34QoPXOiyU0Cpxc9EIZLBYG8bztpbzVNKJX5N0WTap-6ldX0uaOvzX89hL1jnq3vOV4R6_QTPdXEc3RriOpMmv00SGl9EACtvD7IeQ560TJJeRJPOEyqQr5ix67Fv1-T_jkH1TEFH4Y1LnHisBhKKTumVj5bdMnqtd6Y7_wHHKi1hQ-H4rNXxF1frAL5GmTrk-II00DPFtflmvgKPXusGq2Hfzu9tCZejQrDGOxUt2C6uPXufKbQbK1D0zcyd8fVTmWGvEZ3Xi_vm_MpuuDYhoQqPSZLjVGlVPrWahWKRg5ElVlShxiB0PVX7K7Mmbxw8R2MxWHsRNweXn6GDkj5PcoZ4f_sMO24uXgxyAQJuqyixJd4ELfdL811JAFeZuw4mXL4vwB3Lg1GcOHL2jVD4xezX41HFB79xbKJqfWhagOyva5E6ha1sS56079ipEng1kJGvlaBDqyyJ9HRhcA0cMPDBm__zBY2g0qdS2oI3d2sXebZOOwLzQlO-YNuZt4GgM93YagwZktQ6rwk8o1NUCYogrAVo8SjVofb3iFRDj2Tge2pdY9zVnycOEyTtpl9Z8N9iKNDHVNxpKNDzLqAFDslFtKlt2WEgnUXwDexNhkr7hHqVkvKVHKFCvR1Soa8UanWI-l4EXTOnBzs29r3R1RNtiuxFoTKI8cZDsn2MRLWuGUZnWBg-X53teEjkcEAAS6EUhMP-aqT2sVLewcQFHPILn0hZXPfDmwYnH3e-Ef3Yu0gTxveX8bEcoT75u_AonPnoXpBNWrmY44C7XisItvnkVOA2hC7iePFhtpODIYcrHN5-hQhVrfz33kcXKwgH2TTSP2Jh8f0rHjO0EZdi1GoU0fr6cm3Ab0ywCocW2VsClfMgRmK-MXqV7qlqGr5JKpJyV1IpIczlvbjqTA'

HEADERS = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
SKIP_EXT = {'jpg','jpeg','png','gif','bmp','tiff','heic','heif'}

def dbx_post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def list_recursive(path):
    r = dbx_post('https://api.dropboxapi.com/2/files/list_folder', {'path': path, 'recursive': True})
    entries = [e for e in r['entries'] if e['.tag'] == 'file']
    while r.get('has_more'):
        r = dbx_post('https://api.dropboxapi.com/2/files/list_folder/continue', {'cursor': r['cursor']})
        entries += [e for e in r['entries'] if e['.tag'] == 'file']
    return entries

def get_share_link(path):
    try:
        r = dbx_post(
            'https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings',
            {'path': path, 'settings': {'requested_visibility': 'public'}}
        )
        return r['url'].replace('?dl=0', '?raw=1')
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        if 'shared_link_already_exists' in str(body):
            r = dbx_post('https://api.dropboxapi.com/2/sharing/list_shared_links', {'path': path})
            return r['links'][0]['url'].replace('?dl=0', '?raw=1')
        raise

def guess_tipo(name):
    n = name.lower()
    if n.endswith(('.mp4', '.mov')):
        return 'clip_partita'
    if n.endswith('.pdf'):
        return 'pdf'
    if n.endswith(('.docx', '.doc', '.pptx')):
        return 'doc'
    return 'video'

def guess_categoria_from_path(path, name):
    p = path.lower()
    n = name.lower()
    if 'alzata' in p:         return 'Attacco'
    if 'attacco' in p:        return 'Attacco'
    if 'battuta' in p:        return 'Battuta'
    if 'difesa' in p:         return 'Vari'
    if 'muro' in p:           return 'Vari'
    if 'ricezione' in p:      return 'Ricezione'
    if 'taglia' in p:         return 'Partita'
    if 'gara' in p:           return 'Partita'
    if any(k in n for k in ['pineto','brugherio','bologna','macerata','belluno','garlasco']):
        return 'Partita'
    if any(k in n for k in ['rice']):
        return 'Ricezione'
    if any(k in n for k in ['spin','attacc','taglia']):
        return 'Attacco'
    return 'Partita'   # U20 Brasile default = Partita

def subfolder_label(path):
    """Estrae il nome della sottocartella come prefisso del titolo."""
    parts = path.split('/')
    # es. /.../U20-Federico-Brasile/Ricezione/file.mp4 -> "Ricezione"
    if len(parts) >= 2:
        return parts[-2]
    return ''

# --- main ---
SCAN_PATHS = [
    '/__Personale2025/Federico_Volley/U20-Federico-Brasile',
    '/__Personale2025/Federico_Volley/Taglia A3',
]

all_entries = []
for sp in SCAN_PATHS:
    entries = list_recursive(sp)
    entries = [e for e in entries if e['name'].rsplit('.',1)[-1].lower() not in SKIP_EXT]
    all_entries += entries

print(f"File da importare: {len(all_entries)}")

cfg = tomllib.loads(pathlib.Path('.streamlit/secrets.toml').read_text())
engine = create_engine(cfg['connections']['neon']['url'])
sql = text("""
    INSERT INTO contenuti (data, titolo, tipo, categoria, drive_id, drive_type, nota, gara, giornata)
    VALUES (:data, :titolo, :tipo, :categoria, :drive_id, :drive_type, :nota, :gara, :giornata)
""")

salvati = 0
errori = []
with engine.begin() as conn:
    for e in all_entries:
        name = e['name']
        path = e['path_display']
        data_str = e.get('server_modified', '2023-01-01')[:10]
        ext = name.rsplit('.',1)[-1].lower() if '.' in name else ''

        try:
            url = get_share_link(path)
        except Exception as ex:
            errori.append(f"{name}: {ex}")
            continue

        tipo = guess_tipo(name)
        categoria = guess_categoria_from_path(path, name)
        folder_label = subfolder_label(path)
        base_name = name.rsplit('.', 1)[0]
        titolo = f"{folder_label} – {base_name}" if folder_label and folder_label not in base_name else base_name

        # gara dal nome cartella Taglia A3
        gara = None
        for city in ['Pineto','Brugherio','Bologna','Macerata','Belluno','Garlasco']:
            if city.lower() in path.lower():
                gara = city
                break

        conn.execute(sql, {
            'data': data_str,
            'titolo': titolo,
            'tipo': tipo,
            'categoria': categoria,
            'drive_id': url,
            'drive_type': 'dropbox',
            'nota': None,
            'gara': gara,
            'giornata': None,
        })
        salvati += 1
        print(f"  ✓ [{categoria}] {titolo}")

print(f"\n✅ Importati {salvati}. Errori: {len(errori)}")
for err in errori:
    print(f"  ✗ {err}")
