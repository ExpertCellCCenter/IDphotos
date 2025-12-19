# app.py
import re
import io
import hashlib
from pathlib import Path
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
import requests
from PIL import Image, ImageOps

import numpy as np  # ✅ for mobile orientation heuristic

# PDF
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import letter, landscape, portrait
from reportlab.lib.units import mm

# Optional HEIC/HEIF support
try:
    import pillow_heif  # type: ignore
    pillow_heif.register_heif_opener()
    HEIF_OK = True
except Exception:
    HEIF_OK = False

# ----------------------------------------------------
# STREAMLIT CONFIG
# ----------------------------------------------------
st.set_page_config(page_title="Documentos complementarios", page_icon="📷", layout="centered")

# ----------------------------------------------------
# STYLE
# ----------------------------------------------------
st.markdown(
    """
<style>
/* --- Hide Streamlit chrome (top bar / menu / footer) --- */
header[data-testid="stHeader"] {display:none !important;}
#MainMenu {visibility: hidden !important;}
footer {visibility: hidden !important;}
div[data-testid="stAppViewContainer"] {padding-top: 0rem !important;}

/* Force a light-looking app */
.stApp { background: #ffffff !important; color: #0B0F14 !important; }
[data-testid="stAppViewContainer"]{ background: #ffffff !important; }
section[data-testid="stSidebar"]{ background: #F5F7FA !important; }

/* Text */
h1, h2, h3, h4, h5, h6, p, li, label, span, div { color: #0B0F14 !important; }

/* Inputs */
input, textarea {
  background: #FFFFFF !important;
  color: #0B0F14 !important;
  border: 1px solid rgba(0,0,0,0.15) !important;
  border-radius: 10px !important;
}

/* FILE UPLOADER */
[data-testid="stFileUploaderDropzone"]{
  background: #F7FAFC !important;
  border: 1px dashed rgba(0,0,0,0.25) !important;
  border-radius: 14px !important;
}
[data-testid="stFileUploaderDropzone"] *{ color: #0B0F14 !important; }
[data-testid="stFileUploaderDropzone"] button{
  background: #00A8E0 !important;
  color: #FFFFFF !important;
  border: 0 !important;
  border-radius: 12px !important;
  font-weight: 800 !important;
}
[data-testid="stFileUploaderDropzone"] button *{ color: #FFFFFF !important; }
[data-testid="stFileUploaderDropzone"] button:hover{ filter: brightness(0.95) !important; }
[data-testid="stFileUploaderDropzone"] small{ color: rgba(11,15,20,0.70) !important; }
[data-testid="stFileUploaderDropzone"][data-active="true"]{
  background: rgba(0,168,224,0.08) !important;
  border-color: rgba(0,168,224,0.45) !important;
}

/* CAMERA INPUT STYLING */
[data-testid="stCameraInput"]{
  background: #F7FAFC !important;
  border: 1px dashed rgba(0,0,0,0.20) !important;
  border-radius: 14px !important;
}
[data-testid="stCameraInput"] *{ color: #0B0F14 !important; }
[data-testid="stCameraInput"] button{
  background: #00A8E0 !important;
  color: #FFFFFF !important;
  border: 0 !important;
  border-radius: 12px !important;
  font-weight: 800 !important;
}
[data-testid="stCameraInput"] button *{ color: #FFFFFF !important; }
[data-testid="stCameraInput"] button:hover{ filter: brightness(0.95) !important; }

/* --- DEFAULT (PORTRAIT) BEHAVIOR --- */
div[data-testid="stCameraInput"] video,
div[data-testid="stCameraInput"] img{
  width: 100% !important;
  height: auto !important;
  object-fit: contain !important;
}

/* --- MOBILE LANDSCAPE FIX --- */
/* Only applies when screen is landscape and height is small (like a phone) */
@media only screen and (orientation: landscape) and (max-height: 500px) {
  
  /* 1. Force the container to not be 100% wide. 
     We limit width to 60vh (60% of viewport height) so the resulting height stays small. */
  div[data-testid="stCameraInput"] {
    width: auto !important;
    max-width: 60vh !important; 
    margin: 0 auto !important; /* Center it */
  }

  /* 2. Force the video to fit within that smaller container */
  div[data-testid="stCameraInput"] video,
  div[data-testid="stCameraInput"] img {
    max-height: 60vh !important;
    width: 100% !important; 
    object-fit: contain !important;
  }
}

/* Buttons */
.stButton > button {
  background: #00A8E0 !important;
  color: #FFFFFF !important;
  border: 0 !important;
  border-radius: 12px !important;
  padding: 0.55rem 1rem !important;
  font-weight: 800 !important;
}
.stButton > button:hover{ filter: brightness(0.95); }

/* Alerts */
[data-testid="stAlert"]{
  background: #F5F7FA !important;
  border: 1px solid rgba(0,0,0,0.08) !important;
  color: #0B0F14 !important;
}

/* EXPANDERS: blue header like buttons */
div[data-testid="stExpander"] details{
  background: #FFFFFF !important;
  border: 1px solid rgba(0,0,0,0.08) !important;
  border-radius: 14px !important;
  padding: 0 !important;
  overflow: hidden !important;
}
div[data-testid="stExpander"] details > summary{
  background: #00A8E0 !important;
  color: #FFFFFF !important;
  padding: 10px 14px !important;
  font-weight: 800 !important;
  border-radius: 14px !important;
  margin: 0 !important;
}
div[data-testid="stExpander"] details > summary *{ color: #FFFFFF !important; }
div[data-testid="stExpander"] details[open] > summary{
  border-bottom-left-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
  border-bottom: 1px solid rgba(0,0,0,0.08) !important;
}
div[data-testid="stExpander"] details > div{ padding: 10px 12px !important; }

/* Header */
.brand-header{ display:flex; align-items:center; gap:14px; padding: 6px 0 12px 0; }
.brand-title{ font-size: 1.6rem; font-weight: 900; line-height: 1.15; margin: 0; }
.brand-subtitle{ margin: 4px 0 0 0; opacity: 0.85; font-size: 0.95rem; }
.hr-soft{ border: none; height: 1px; background: rgba(0,0,0,0.08); margin: 10px 0 16px 0; }

/* Cards */
.success-wrap{
  border: 1px solid rgba(0,0,0,0.08);
  background: #FFFFFF;
  border-radius: 18px;
  padding: 22px 20px;
  box-shadow: 0 10px 26px rgba(0,0,0,0.08);
}
.success-title{ font-size: 1.6rem; font-weight: 800; line-height: 1.2; margin: 0 0 10px 0; }
.success-sub{ font-size: 1rem; opacity: 0.92; margin: 0 0 14px 0; }
.success-chip{
  display: inline-block;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(0,168,224,0.10);
  border: 1px solid rgba(0,168,224,0.25);
  font-weight: 700;
  margin-right: 10px;
}
.success-meta{
  margin-top: 16px;
  border-top: 1px solid rgba(0,0,0,0.08);
  padding-top: 14px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.success-box{
  flex: 1;
  min-width: 180px;
  border: 1px solid rgba(0,0,0,0.08);
  background: #F7FAFC;
  border-radius: 14px;
  padding: 12px 14px;
}
.success-k{ font-size: 0.85rem; opacity: 0.85; margin: 0; }
.success-v{ font-size: 1.15rem; font-weight: 800; margin: 2px 0 0 0; }
.preview-wrap{ margin-top: 14px; border-top: 1px solid rgba(0,0,0,0.08); padding-top: 14px; }
.preview-title{ font-weight: 800; margin-bottom: 10px; opacity: 0.95; }
</style>
""",
    unsafe_allow_html=True,
)

# Anchor always present
st.markdown('<div id="top-anchor"></div>', unsafe_allow_html=True)

# ----------------------------------------------------
# SCROLL TO TOP
# ----------------------------------------------------
def scroll_to_top():
    components.html(
        """
        <script>
          (function () {
            function doScroll(doc) {
              try { doc.getElementById("top-anchor")?.scrollIntoView({block:"start"}); } catch(e) {}
              try { doc.documentElement.scrollTop = 0; } catch(e) {}
              try { doc.body.scrollTop = 0; } catch(e) {}
              try { doc.querySelector('[data-testid="stAppViewContainer"]')?.scrollTo(0,0); } catch(e) {}
              try { doc.querySelector('[data-testid="stAppViewContainer"]')?.scrollTop = 0; } catch(e) {}
              try { doc.querySelector('section.main')?.scrollTo(0,0); } catch(e) {}
              try { doc.querySelector('section.main')?.scrollTop = 0; } catch(e) {}
              try { doc.querySelector('div[data-testid="stMainBlockContainer"]')?.scrollTo(0,0); } catch(e) {}
              try { doc.querySelector('div[data-testid="stMainBlockContainer"]')?.scrollTop = 0; } catch(e) {}
            }

            function run() {
              try { window.scrollTo(0,0); } catch(e) {}
              try { doScroll(document); } catch(e) {}
              try { doScroll(window.parent.document); } catch(e) {}
              try { window.parent.scrollTo(0,0); } catch(e) {}
            }

            run();
            setTimeout(run, 50);
            setTimeout(run, 250);
            setTimeout(run, 800);
          })();
        </script>
        """,
        height=0,
    )

# ----------------------------------------------------
# BRAND HEADER
# ----------------------------------------------------
def render_header():
    logo_path = Path(__file__).parent / "att_logo.png"

    c1, c2 = st.columns([1, 5], vertical_alignment="center")
    with c1:
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)

    with c2:
        st.markdown(
            """
<div class="brand-header">
  <div>
    <p class="brand-title">Documentos complementarios</p>
    <p class="brand-subtitle">para continuar la cotización</p>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="hr-soft"></div>', unsafe_allow_html=True)

    st.markdown(
        """
1) Escribe el **folio** de tu cotización (formato: `251215-0FF480`)  
2) Sube fotos desde tu galería **y/o** toma fotos con la cámara (puedes tomar varias)  
3) Presiona **Subir fotos** → se subirán al sistema   
"""
    )

# ----------------------------------------------------
# FOLIO FORMAT
# ----------------------------------------------------
FOLIO_PATTERN = re.compile(r"^\d{6}-[A-Z0-9]{6}$")

def normalize_folio(raw: str) -> str:
    s = (raw or "").strip().upper()
    s = s.replace("–", "-").replace("—", "-")
    return s

def is_valid_folio(folio: str) -> bool:
    return bool(FOLIO_PATTERN.match(folio))

# ----------------------------------------------------
# DEVICE DETECTION (best-effort)
# ----------------------------------------------------
def _user_agent_lower() -> str:
    try:
        # Newer Streamlit
        ua = st.context.headers.get("User-Agent", "")
        return (ua or "").lower()
    except Exception:
        return ""

def is_mobile_device() -> bool:
    ua = _user_agent_lower()
    if not ua:
        return False
    keys = ["iphone", "ipad", "ipod", "android", "mobile", "windows phone"]
    return any(k in ua for k in keys)

IS_MOBILE = is_mobile_device()

# ----------------------------------------------------
# HELPERS
# ----------------------------------------------------
def _guess_suffix(mime: str | None, fallback_name: str | None = None) -> str:
    if fallback_name:
        s = Path(fallback_name).suffix
        if s:
            return s.lower()

    if not mime:
        return ".jpg"
    m = mime.lower()
    if "png" in m:
        return ".png"
    if "heic" in m or "heif" in m:
        return ".heic"
    if "jpeg" in m or "jpg" in m:
        return ".jpg"
    return ".jpg"

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _open_img_safe(b: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(b))
    # ✅ EXIF transpose (when EXIF exists)
    img = ImageOps.exif_transpose(img)
    return img

def _to_png_bytes(img: Image.Image) -> bytes:
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)  # lossless
    buf.seek(0)
    return buf.read()

def _projection_score(img: Image.Image) -> float:
    """
    Heuristic for documents: upright orientation tends to have more variation across rows (text lines)
    than across columns. We compare row-variance vs col-variance on a downscaled grayscale copy.
    """
    g = img.convert("L")
    w, h = g.size
    max_side = 480
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        g = g.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BILINEAR)

    arr = np.asarray(g, dtype=np.float32) / 255.0
    row = arr.mean(axis=1)
    col = arr.mean(axis=0)
    return float(row.var() - col.var())

def normalize_camera_orientation_mobile(img: Image.Image) -> Image.Image:
    """
    ✅ Mobile fix: choose 0° vs 90° (CW) based on document-like projection score.
    Only used for camera photos on mobile.
    """
    try:
        score0 = _projection_score(img)
        img90 = img.rotate(270, expand=True)  # 90° CW
        score90 = _projection_score(img90)

        # Rotate only if it improves the score (more "horizontal text lines" feel)
        if score90 > score0:
            return img90
        return img
    except Exception:
        return img

def prepare_for_storage(b: bytes, mime: str | None, source: str) -> tuple[bytes, str | None, str]:
    """
    - Opens image
    - EXIF transpose
    - ✅ If source is camera AND device is mobile -> apply robust 0/90 auto-rotation
    - Saves as lossless PNG (keeps quality, removes EXIF confusion)
    """
    try:
        img = _open_img_safe(b)

        if source == "camera" and IS_MOBILE:
            img = normalize_camera_orientation_mobile(img)

        png_bytes = _to_png_bytes(img)
        return png_bytes, "image/png", ".png"
    except Exception:
        return b, mime, _guess_suffix(mime)

def normalize_for_preview(b: bytes, source: str) -> Image.Image | None:
    """
    For UI previews: show corrected orientation (same logic), without changing storage bytes here.
    """
    try:
        img = _open_img_safe(b)
        if source == "camera" and IS_MOBILE:
            img = normalize_camera_orientation_mobile(img)
        return img
    except Exception:
        return None

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
    r = requests.put(url, headers=graph_headers_binary(mime_type), data=file_bytes, timeout=180)
    r.raise_for_status()

def list_existing_hashes(folder_item_id: str, max_pages: int = 10) -> set[str]:
    hashes = set()
    url = f"{drive_base_url()}/items/{folder_item_id}/children?$select=name&$top=200"
    for _ in range(max_pages):
        r = requests.get(url, headers=graph_headers_json(), timeout=30)
        r.raise_for_status()
        data = r.json()
        for it in data.get("value", []):
            name = it.get("name", "")
            m = re.search(r"__sha256_([0-9a-f]{12})", name)
            if m:
                hashes.add(m.group(1))
        nxt = data.get("@odata.nextLink")
        if not nxt:
            break
        url = nxt
    return hashes

# ----------------------------------------------------
# PDF BUILDER (LETTER + no-upscale for quality)
# ----------------------------------------------------
def build_pdf_from_images_high_quality(image_bytes_list: list[bytes]) -> bytes:
    if not image_bytes_list:
        raise ValueError("No hay imágenes para generar el PDF.")

    out = io.BytesIO()
    c = canvas.Canvas(out, pageCompression=0)

    margin = 10 * mm

    for b in image_bytes_list:
        img = _open_img_safe(b)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        w_px, h_px = img.size

        # ✅ Always LETTER (portrait/landscape depending on image)
        if w_px >= h_px:
            page_w, page_h = landscape(letter)
        else:
            page_w, page_h = portrait(letter)

        png_buf = io.BytesIO()
        img.save(png_buf, format="PNG", optimize=False)
        png_buf.seek(0)

        max_w = page_w - 2 * margin
        max_h = page_h - 2 * margin

        # ✅ IMPORTANT: never upscale -> avoids "horrible" pixelated look
        scale = min(max_w / w_px, max_h / h_px, 1.0)

        draw_w = w_px * scale
        draw_h = h_px * scale

        x = (page_w - draw_w) / 2
        y = (page_h - draw_h) / 2

        c.setPageSize((page_w, page_h))
        c.drawImage(ImageReader(png_buf), x, y, width=draw_w, height=draw_h, mask="auto")
        c.showPage()

    c.save()
    out.seek(0)
    return out.read()

# ----------------------------------------------------
# SESSION STATE
# ----------------------------------------------------
if "camera_photos" not in st.session_state:
    st.session_state.camera_photos = []
if "gallery_photos" not in st.session_state:
    st.session_state.gallery_photos = []
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
if "last_screen" not in st.session_state:
    st.session_state.last_screen = ""

def reset_flow():
    st.session_state.camera_photos = []
    st.session_state.gallery_photos = []
    st.session_state.uploaded_ok = False
    st.session_state.uploaded_folio = ""
    st.session_state.uploaded_total = 0
    st.session_state.uploaded_previews = []
    st.session_state.final_screen = False

def _current_screen() -> str:
    if st.session_state.final_screen:
        return "final"
    if st.session_state.uploaded_ok:
        return "success"
    return "main"

# ----------------------------------------------------
# FINAL SCREEN
# ----------------------------------------------------
if st.session_state.final_screen:
    scroll_to_top()
    st.session_state.last_screen = _current_screen()

    render_header()
    scroll_to_top()

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
    if st.session_state.last_screen != _current_screen():
        scroll_to_top()
        st.session_state.last_screen = _current_screen()

    folio = st.session_state.uploaded_folio
    total = st.session_state.uploaded_total
    previews = st.session_state.uploaded_previews or []

    render_header()
    scroll_to_top()

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

    with st.expander("📷 Ver fotos subidas", expanded=True):
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
if st.session_state.last_screen != _current_screen():
    scroll_to_top()
    st.session_state.last_screen = _current_screen()

render_header()
scroll_to_top()

folio_input = st.text_input("Folio de la cotización", placeholder="Ej. 251215-0FF480")
folio = normalize_folio(folio_input)

if not folio:
    st.info("Escribe el folio para continuar.")
    st.stop()

if not is_valid_folio(folio):
    st.error("Formato de folio inválido. Debe ser: **251215-0FF480** (6 dígitos, guion, 6 alfanuméricos).")
    st.stop()

st.success(f"Folio válido: **{folio}**")

# INE guide
instrucciones_path = Path(__file__).parent / "ineCorrecto.jpeg"
if not instrucciones_path.exists():
    instrucciones_path = Path("/mnt/data/ineCorrecto.jpeg")

with st.expander("🪪 Guía: cómo tomar correctamente la foto (INE)", expanded=True):
    if instrucciones_path.exists():
        st.image(str(instrucciones_path), use_container_width=True)
    else:
        st.warning("No se encontró la imagen de instrucciones (ineCorrecto.jpeg).")

base_folder = st.secrets["azure_app"].get("onedrive_base_folder", "fotos_cotizaciones")

# --------------------
# GALLERY UPLOADS
# --------------------
st.subheader("📁 Subir desde galería / archivos")
uploaded_files = st.file_uploader(
    "Puedes subir varias fotos",
    type=["jpg", "jpeg", "png", "heic", "heif"],
    accept_multiple_files=True,
    key="gallery_uploader",
)

# Only overwrite if there are actual files
if uploaded_files is not None and len(uploaded_files) > 0:
    new_list = []
    for f in uploaded_files:
        b = f.getvalue()
        new_list.append({"bytes": b, "mime": f.type, "suffix": _guess_suffix(f.type, f.name), "name": f.name})
    st.session_state.gallery_photos = new_list

if st.session_state.gallery_photos:
    with st.expander("Ver vista previa de fotos seleccionadas"):
        cols = st.columns(3)
        for idx, item in enumerate(st.session_state.gallery_photos):
            cols[idx % 3].image(item["bytes"], caption=f"Foto #{idx+1}", use_container_width=True)

st.markdown("---")

# --------------------
# CAMERA (MULTI)
# --------------------
st.subheader("📸 Tomar fotos con la cámara (puedes tomar varias)")
camera_photo = st.camera_input("Toma una foto y luego pulsa **Agregar foto tomada**", key="camera_input")

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

if st.session_state.camera_photos:
    with st.expander("Ver vista previa de fotos tomadas"):
        cols = st.columns(3)
        for i, p in enumerate(st.session_state.camera_photos, start=1):
            img_prev = normalize_for_preview(p["bytes"], source="camera")
            if img_prev is not None:
                cols[(i - 1) % 3].image(img_prev, caption=f"Foto tomada #{i}", use_container_width=True)
            else:
                cols[(i - 1) % 3].image(p["bytes"], caption=f"Foto tomada #{i}", use_container_width=True)

st.markdown("---")

# --------------------
# UPLOAD BUTTON (ONLY bar + % + legend)
# --------------------
if st.button("💾 Subir fotos", type="primary"):
    if (not st.session_state.gallery_photos) and (not st.session_state.camera_photos):
        st.warning("No seleccionaste fotos de galería ni agregaste fotos tomadas.")
        st.stop()

    gallery_items = st.session_state.gallery_photos
    camera_items = st.session_state.camera_photos

    total_selected = len(gallery_items) + len(camera_items)
    total_steps = max(1, total_selected) + 2
    done_steps = 0

    legend = st.empty()
    progress_bar = st.progress(0)
    pct_line = st.empty()

    def _set_progress():
        pct = int(min(100, (done_steps / total_steps) * 100))
        progress_bar.progress(pct)
        pct_line.markdown(f"{pct}%")
        legend.markdown("**Finalizado**" if pct >= 100 else "**Subiendo**")

    try:
        legend.markdown("**Subiendo**")
        pct_line.markdown("0%")

        target_folder_id = ensure_path([base_folder, folio])
        done_steps += 1
        _set_progress()

        existing_hash_prefixes = list_existing_hashes(target_folder_id)
        seen_this_run: set[str] = set()

        # PDF uses normalized bytes (correct orientation + lossless)
        pdf_images_bytes: list[bytes] = []
        counter = {"n": 0}
        flags = {"new_anything": False}

        def maybe_upload_image(original_bytes: bytes, store_bytes: bytes, store_mime: str | None, source: str, store_suffix: str) -> bool:
            h12 = sha256_bytes(original_bytes)[:12]
            if h12 in existing_hash_prefixes or h12 in seen_this_run:
                return False

            seen_this_run.add(h12)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{folio}_{source}_{ts}__sha256_{h12}{store_suffix}"
            upload_small_file_to_folder(target_folder_id, filename, store_bytes, store_mime)

            existing_hash_prefixes.add(h12)
            counter["n"] += 1
            flags["new_anything"] = True
            return True

        # Upload gallery
        for g in gallery_items:
            store_b, store_m, store_s = prepare_for_storage(g["bytes"], g.get("mime"), "upload")
            pdf_images_bytes.append(store_b)
            maybe_upload_image(g["bytes"], store_b, store_m, "upload", store_s)
            done_steps += 1
            _set_progress()

        # Upload camera (mobile fix applied here)
        for p in camera_items:
            store_b, store_m, store_s = prepare_for_storage(p["bytes"], p.get("mime"), "camera")
            pdf_images_bytes.append(store_b)
            maybe_upload_image(p["bytes"], store_b, store_m, "camera", store_s)
            done_steps += 1
            _set_progress()

        # PDF step
        done_steps += 1
        _set_progress()

        if flags["new_anything"]:
            try:
                pdf_bytes = build_pdf_from_images_high_quality(pdf_images_bytes)
                ts_pdf = datetime.now().strftime("%Y%m%d_%H%M%S")
                pdf_name = f"{folio}_fotos_{ts_pdf}.pdf"
                upload_small_file_to_folder(target_folder_id, pdf_name, pdf_bytes, "application/pdf")
            except Exception as pdf_err:
                st.warning(
                    "⚠️ Las fotos se subieron correctamente, pero no se pudo generar el PDF. "
                    "Si subiste HEIC/HEIF, instala `pillow-heif`."
                )
                st.caption(f"Detalle: {pdf_err}")
        else:
            st.info("No se subió nada nuevo (todas las fotos ya existían en el sistema).")

        progress_bar.progress(100)
        pct_line.markdown("100%")
        legend.markdown("**Finalizado**")

        # Clear stacks
        st.session_state.camera_photos = []
        st.session_state.gallery_photos = []

        # Success screen (show normalized previews)
        st.session_state.uploaded_ok = True
        st.session_state.uploaded_folio = folio
        st.session_state.uploaded_total = counter["n"]
        st.session_state.uploaded_previews = pdf_images_bytes
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
