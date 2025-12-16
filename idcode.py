# app.py
import re
from pathlib import Path
from datetime import datetime

import streamlit as st
import requests

# ----------------------------------------------------
# STREAMLIT CONFIG
# ----------------------------------------------------
st.set_page_config(page_title="Documentos complementarios", page_icon="📷", layout="centered")

# ----------------------------------------------------
# STYLE (Fancy screens)
# ----------------------------------------------------
st.markdown(
    """
<style>
.success-wrap{
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.04);
  border-radius: 18px;
  padding: 22px 20px;
  box-shadow: 0 12px 34px rgba(0,0,0,0.22);
}
.success-title{
  font-size: 1.6rem;
  font-weight: 800;
  line-height: 1.2;
  margin: 0 0 10px 0;
}
.success-sub{
  font-size: 1rem;
  opacity: 0.92;
  margin: 0 0 14px 0;
}
.success-chip{
  display: inline-block;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(34,197,94,0.18);
  border: 1px solid rgba(34,197,94,0.35);
  font-weight: 700;
  margin-right: 10px;
}
.success-meta{
  margin-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.10);
  padding-top: 14px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.success-box{
  flex: 1;
  min-width: 180px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.03);
  border-radius: 14px;
  padding: 12px 14px;
}
.success-k{
  font-size: 0.85rem;
  opacity: 0.85;
  margin: 0;
}
.success-v{
  font-size: 1.15rem;
  font-weight: 800;
  margin: 2px 0 0 0;
}
.preview-wrap{
  margin-top: 14px;
  border-top: 1px solid rgba(255,255,255,0.10);
  padding-top: 14px;
}
.preview-title{
  font-weight: 800;
  margin-bottom: 10px;
  opacity: 0.95;
}
</style>
""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------
# FOLIO FORMAT (STRICT)
# Example: 251215-0FF480
# ----------------------------------------------------
FOLIO_PATTERN = re.compile(r"^\d{6}-[A-Z0-9]{6}$")


def normalize_folio(raw: str) -> str:
    return (raw or "").strip().upper()


def is_valid_folio(folio: str) -> bool:
    return bool(FOLIO_PATTERN.match(folio))


# ----------------------------------------------------
# ONEDRIVE / GRAPH HELPERS
# ----------------------------------------------------
def graph_token() -> str:
    tenant_id = st.secrets["azure_app"]["tenant_id"]
    client_id = st.secrets["azure_app"]["client_id"]
    client_secret = st.secrets["azure_app"]["client_secret"]

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    r = requests.post(token_url, data=data, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def drive_base_url() -> str:
    user = st.secrets["azure_app"]["onedrive_user"]
    return f"https://graph.microsoft.com/v1.0/users/{user}/drive"


def graph_headers_json() -> dict:
    return {"Authorization": f"Bearer {graph_token()}", "Content-Type": "application/json"}


def graph_headers_binary(mime: str | None) -> dict:
    return {"Authorization": f"Bearer {graph_token()}", "Content-Type": mime or "application/octet-stream"}


@st.cache_resource
def root_id() -> str:
    url = f"{drive_base_url()}/root?$select=id"
    r = requests.get(url, headers=graph_headers_json(), timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def ensure_folder(parent_item_id: str, folder_name: str) -> str:
    list_url = f"{drive_base_url()}/items/{parent_item_id}/children?$select=id,name,folder"
    r = requests.get(list_url, headers=graph_headers_json(), timeout=30)
    r.raise_for_status()

    for item in r.json().get("value", []):
        if item.get("name") == folder_name and item.get("folder") is not None:
            return item["id"]

    create_url = f"{drive_base_url()}/items/{parent_item_id}/children"
    payload = {"name": folder_name, "folder": {}, "@microsoft.graph.conflictBehavior": "rename"}
    r = requests.post(create_url, headers=graph_headers_json(), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def ensure_path(folder_parts: list[str]) -> str:
    current = root_id()
    for name in folder_parts:
        current = ensure_folder(current, name)
    return current


def upload_small_file_to_folder(folder_item_id: str, filename: str, file_bytes: bytes, mime_type: str | None) -> None:
    url = f"{drive_base_url()}/items/{folder_item_id}:/{filename}:/content"
    r = requests.put(url, headers=graph_headers_binary(mime_type), data=file_bytes, timeout=120)
    r.raise_for_status()


# ----------------------------------------------------
# SESSION STATE
# ----------------------------------------------------
if "camera_photos" not in st.session_state:
    st.session_state.camera_photos = []

if "uploaded_ok" not in st.session_state:
    st.session_state.uploaded_ok = False

if "uploaded_folio" not in st.session_state:
    st.session_state.uploaded_folio = ""

if "uploaded_total" not in st.session_state:
    st.session_state.uploaded_total = 0

if "uploaded_previews" not in st.session_state:
    st.session_state.uploaded_previews = []

if "final_screen" not in st.session_state:
    st.session_state.final_screen = False


def _guess_suffix(mime: str | None) -> str:
    if not mime:
        return ".jpg"
    m = mime.lower()
    if "png" in m:
        return ".png"
    if "heic" in m or "heif" in m:
        return ".heic"
    return ".jpg"


def reset_flow():
    st.session_state.camera_photos = []
    st.session_state.uploaded_ok = False
    st.session_state.uploaded_folio = ""
    st.session_state.uploaded_total = 0
    st.session_state.uploaded_previews = []
    st.session_state.final_screen = False


# ----------------------------------------------------
# FINAL SCREEN
# ----------------------------------------------------
if st.session_state.final_screen:
    st.title("📷 Documentos complementarios para continuar la cotización")

    st.markdown(
        """
<div class="success-wrap">
  <div class="success-title">✅ Proceso finalizado</div>
  <div class="success-sub">
    Gracias. Tus documentos fueron registrados correctamente.<br/>
    Ya puedes cerrar esta página con seguridad.
  </div>
  <span class="success-chip">Listo</span>
  <div class="success-meta">
    <div class="success-box">
      <p class="success-k">Siguiente paso</p>
      <p class="success-v">Continuar con la cotización (contacta a tu agente)</p>
    </div>
    <div class="success-box">
      <p class="success-k">Acción</p>
      <p class="success-v">Puedes cerrar esta pantalla</p>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button("🔁 Subir documentos de otra cotización", type="primary", use_container_width=True):
        reset_flow()
        st.rerun()

    st.stop()

# ----------------------------------------------------
# SUCCESS SCREEN
# ----------------------------------------------------
if st.session_state.uploaded_ok:
    folio = st.session_state.uploaded_folio
    total = st.session_state.uploaded_total
    previews = st.session_state.uploaded_previews or []

    st.title("📷 Documentos complementarios para continuar la cotización")

    st.markdown(
        f"""
<div class="success-wrap">
  <div class="success-title">✅ Carga completada</div>
  <div class="success-sub">
    Las fotos correspondientes a la cotización <b>{folio}</b> se subieron al sistema de manera satisfactoria.
  </div>

  <span class="success-chip">Subida exitosa</span>

  <div class="success-meta">
    <div class="success-box">
      <p class="success-k">Folio</p>
      <p class="success-v">{folio}</p>
    </div>
    <div class="success-box">
      <p class="success-k">Total de fotos subidas</p>
      <p class="success-v">{total}</p>
    </div>
  </div>

  <div class="preview-wrap">
    <div class="preview-title">Vista previa de fotos subidas</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if previews:
        cols = st.columns(4)
        for i, b in enumerate(previews, start=1):
            cols[(i - 1) % 4].image(b, caption=f"Foto #{i}", use_container_width=True)
    else:
        st.info("No hay vista previa disponible.")

    st.write("")

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("📤 Subir más fotos (otro folio)", type="primary", use_container_width=True):
            reset_flow()
            st.rerun()
    with colB:
        if st.button("✅ Finalizar", use_container_width=True):
            st.session_state.final_screen = True
            st.rerun()

    st.stop()

# ----------------------------------------------------
# MAIN SCREEN
# ----------------------------------------------------
st.title("📷 Documentos complementarios para continuar la cotización")

st.markdown(
    """
1) Escribe el **folio** de tu cotización (formato: `251215-0FF480`)  
2) Sube fotos desde tu galería **y/o** toma fotos con la cámara (puedes tomar varias)  
3) Presiona **Subir fotos** → se subirán al sistema  
"""
)

folio_input = st.text_input("Folio de la cotización", placeholder="Ej. 251215-0FF480")
folio = normalize_folio(folio_input)

if not folio:
    st.info("Escribe el folio para continuar.")
    st.stop()

if not is_valid_folio(folio):
    st.error("Formato de folio inválido. Debe ser: **251215-0FF480** (6 dígitos, guion, 6 alfanuméricos).")
    st.stop()

st.success(f"Folio válido: **{folio}**")

base_folder = st.secrets["azure_app"].get("onedrive_base_folder", "fotos_cotizaciones")

st.subheader("📁 Subir desde galería / archivos")
uploaded_files = st.file_uploader(
    "Puedes subir varias fotos",
    type=["jpg", "jpeg", "png", "heic", "heif"],
    accept_multiple_files=True,
)

if uploaded_files:
    with st.expander("Ver vista previa de fotos seleccionadas"):
        cols = st.columns(3)
        for idx, f in enumerate(uploaded_files):
            cols[idx % 3].image(f.getvalue(), caption=f"Foto #{idx+1}", use_container_width=True)

st.markdown("---")

st.subheader("📸 Tomar fotos con la cámara (puedes tomar varias)")
camera_photo = st.camera_input("Toma una foto y luego pulsa **Agregar foto tomada**")

c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    add_cam = st.button("➕ Agregar foto tomada", use_container_width=True)
with c2:
    clear_cam = st.button("🗑️ Quitar fotos tomadas", use_container_width=True)
with c3:
    st.metric("Fotos tomadas", len(st.session_state.camera_photos))

if clear_cam:
    st.session_state.camera_photos = []
    st.success("Se quitaron las fotos tomadas.")
    st.rerun()

if add_cam:
    if camera_photo is None:
        st.warning("Primero toma una foto con la cámara.")
    else:
        b = camera_photo.getvalue()
        mime = camera_photo.type
        st.session_state.camera_photos.append({"bytes": b, "mime": mime, "suffix": _guess_suffix(mime)})
        st.success(f"✅ Foto agregada. Ya tienes {len(st.session_state.camera_photos)} foto(s) tomada(s).")
        st.rerun()

if len(st.session_state.camera_photos) > 0:
    with st.expander("Ver vista previa de fotos tomadas"):
        cols = st.columns(3)
        for i, p in enumerate(st.session_state.camera_photos, start=1):
            cols[(i - 1) % 3].image(p["bytes"], caption=f"Foto tomada #{i}", use_container_width=True)

st.markdown("---")

if st.button("💾 Subir fotos", type="primary"):
    if (not uploaded_files) and (len(st.session_state.camera_photos) == 0):
        st.warning("No seleccionaste fotos de galería ni agregaste fotos tomadas.")
        st.stop()

    try:
        target_folder_id = ensure_path([base_folder, folio])

        total = 0
        previews: list[bytes] = []

        if uploaded_files:
            for f in uploaded_files:
                b = f.getvalue()
                previews.append(b)
                suffix = Path(f.name).suffix or ".jpg"
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"{folio}_upload_{ts}{suffix}"
                upload_small_file_to_folder(target_folder_id, filename, b, f.type)
                total += 1

        for p in st.session_state.camera_photos:
            previews.append(p["bytes"])
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{folio}_camera_{ts}{p['suffix']}"
            upload_small_file_to_folder(target_folder_id, filename, p["bytes"], p["mime"])
            total += 1

        st.session_state.camera_photos = []

        st.session_state.uploaded_ok = True
        st.session_state.uploaded_folio = folio
        st.session_state.uploaded_total = total
        st.session_state.uploaded_previews = previews
        st.rerun()

    except requests.HTTPError as e:
        st.error("❌ Error subiendo fotos (Microsoft Graph).")
        st.code(str(e))
        try:
            st.code(e.response.text)
        except Exception:
            pass
    except Exception as e:
        st.error("❌ Error inesperado.")
        st.code(str(e))
