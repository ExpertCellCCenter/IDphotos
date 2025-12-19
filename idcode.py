import re
import io
import hashlib
from pathlib import Path
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
import requests
from PIL import Image, ImageOps

import numpy as np

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
# STYLE (Original "Perfect" CSS + Progress Bar Tweaks)
# ----------------------------------------------------
st.markdown(
    """
<style>
/* --- Hide Streamlit chrome --- */
header[data-testid="stHeader"] {display:none !important;}
#MainMenu {visibility: hidden !important;}
footer {visibility: hidden !important;}
div[data-testid="stAppViewContainer"] {padding-top: 0rem !important;}

/* Force a light-looking app */
.stApp { background: #ffffff !important; color: #0B0F14 !important; }
[data-testid="stAppViewContainer"]{ background: #ffffff !important; }
section[data-testid="stSidebar"]{ background: #F5F7FA !important; }

/* Text & Inputs */
h1, h2, h3, h4, h5, h6, p, li, label, span, div { color: #0B0F14 !important; }
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
[data-testid="stFileUploaderDropzone"][data-active="true"]{
  background: rgba(0,168,224,0.08) !important;
  border-color: rgba(0,168,224,0.45) !important;
}

/* ==================================================
   CAMERA STYLING
   ================================================== */

/* 1. Main Camera Container */
[data-testid="stCameraInput"] {
  width: 100% !important;
  background: #000000 !important; 
  border-radius: 14px !important;
  position: relative !important;
  overflow: hidden !important;
}

/* 2. REMOVE FORCED ASPECT RATIO */
[data-testid="stCameraInput"] > div {
    aspect-ratio: unset !important;
    height: auto !important;
}

/* 3. VIDEO & IMAGE PREVIEW (NO CROP) */
[data-testid="stCameraInput"] video,
[data-testid="stCameraInput"] img {
  width: 100% !important;
  height: auto !important;
  min-height: 300px !important; 
  max-height: 80vh !important;  
  object-fit: contain !important; /* Shows full sensor view */
}

/* 4. BUTTONS (Blue) */
[data-testid="stCameraInput"] button {
  background: #00A8E0 !important;
  color: #FFFFFF !important;
  border: 0 !important;
  border-radius: 8px !important;
  font-weight: 800 !important;
  z-index: 9999 !important;
}
[data-testid="stCameraInput"] button:hover {
  filter: brightness(0.95) !important;
}
[data-testid="stCameraInput"] button svg {
  fill: white !important;
  stroke: white !important;
}

/* 5. Take Photo Button Position */
[data-testid="stCameraInput"] button:not(:has(svg)) {
  padding: 0.55rem 1rem !important;
  margin: 10px auto !important; 
}

/* 6. Icon Buttons Position */
[data-testid="stCameraInput"] button:has(svg) {
  padding: 8px 12px !important;
  border: 1px solid rgba(255,255,255,0.2) !important;
}

/* --- MOBILE LANDSCAPE SPECIFIC --- */
@media only screen and (orientation: landscape) and (max-height: 500px) {
  div[data-testid="stCameraInput"],
  div[data-testid="stCameraInput"] > div {
    height: 90vh !important; 
    width: 100% !important;
    background: #000000 !important;
    border: none !important;
    display: flex !important;
    flex-direction: column;
    justify-content: center;
    align-items: center;
  }

  div[data-testid="stCameraInput"] video,
  div[data-testid="stCameraInput"] img {
    height: 100% !important;
    width: 100% !important;
    object-fit: contain !important;
    max-height: unset !important;
  }

  div[data-testid="stCameraInput"] button:not(:has(svg)) {
    position: absolute !important;
    bottom: 20px !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    width: auto !important;
    min-width: 150px !important;
    white-space: nowrap !important;
  }

  div[data-testid="stCameraInput"] button:has(svg) {
    position: absolute !important;
    top: 15px !important;
    right: 15px !important;
    left: auto !important;
    bottom: auto !important;
    transform: none !important;
  }
}

/* Standard Buttons */
.stButton > button {
  background: #00A8E0 !important;
  color: #FFFFFF !important;
  border: 0 !important;
  border-radius: 12px !important;
  padding: 0.55rem 1rem !important;
  font-weight: 800 !important;
}

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
            }
            function run() {
              try { window.scrollTo(0,0); } catch(e) {}
              try { doScroll(document); } catch(e) {}
            }
            run();
            setTimeout(run, 50);
            setTimeout(run, 250);
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
2) Sube fotos desde tu galería **y/o** toma fotos con la cámara  
3) Presiona **Subir fotos** → se subirán al sistema   
"""
    )

# ----------------------------------------------------
# LOGIC / HELPERS
# ----------------------------------------------------
FOLIO_PATTERN = re.compile(r"^\d{6}-[A-Z0-9]{6}$")

def normalize_folio(raw: str) -> str:
    s = (raw or "").strip().upper()
    s = s.replace("–", "-").replace("—", "-")
    return s

def is_valid_folio(folio: str) -> bool:
    return bool(FOLIO_PATTERN.match(folio))

def _user_agent_lower() -> str:
    try:
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

def _guess_suffix(mime: str | None, fallback_name: str | None = None) -> str:
    if fallback_name:
        s = Path(fallback_name).suffix
        if s: return s.lower()
    if not mime: return ".jpg"
    m = mime.lower()
    if "png" in m: return ".png"
    if "heic" in m: return ".heic"
    return ".jpg"

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _open_img_safe(b: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(b))
    img = ImageOps.exif_transpose(img)
    return img

def _to_png_bytes(img: Image.Image) -> bytes:
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    buf.seek(0)
    return buf.read()

def _projection_score(img: Image.Image) -> float:
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
    try:
        score0 = _projection_score(img)
        img90 = img.rotate(270, expand=True)
        score90 = _projection_score(img90)
        if score90 > score0:
            return img90
        return img
    except Exception:
        return img

def prepare_for_storage(b: bytes, mime: str | None, source: str) -> tuple[bytes, str | None, str]:
    try:
        img = _open_img_safe(b)
        if source == "camera" and IS_MOBILE:
            img = normalize_camera_orientation_mobile(img)
        png_bytes = _to_png_bytes(img)
        return png_bytes, "image/png", ".png"
    except Exception:
        return b, mime, _guess_suffix(mime)

def normalize_for_preview(b: bytes, source: str) -> Image.Image | None:
    try:
        img = _open_img_safe(b)
        if source == "camera" and IS_MOBILE:
            img = normalize_camera_orientation_mobile(img)
        return img
    except Exception:
        return None

# ----------------------------------------------------
# ONEDRIVE
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

def graph_headers_binary(mime: str | None) -> dict:
    return {"Authorization": f"Bearer {graph_token()}", "Content-Type": mime or "application/octet-stream"}

@st.cache_resource
def root_id() -> str:
    url = f"{drive_base_url()}/root?$select=id"
    r = requests.get(url, headers={"Authorization": f"Bearer {graph_token()}"}, timeout=30)
    r.raise_for_status()
    return r.json()["id"]

def ensure_folder(parent_item_id: str, folder_name: str) -> str:
    headers = {"Authorization": f"Bearer {graph_token()}", "Content-Type": "application/json"}
    list_url = f"{drive_base_url()}/items/{parent_item_id}/children?$select=id,name,folder"
    r = requests.get(list_url, headers=headers, timeout=30)
    for item in r.json().get("value", []):
        if item.get("name") == folder_name and item.get("folder") is not None:
            return item["id"]
    create_url = f"{drive_base_url()}/items/{parent_item_id}/children"
    payload = {"name": folder_name, "folder": {}, "@microsoft.graph.conflictBehavior": "rename"}
    r = requests.post(create_url, headers=headers, json=payload, timeout=30)
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

def list_existing_hashes(folder_item_id: str) -> set[str]:
    hashes = set()
    headers = {"Authorization": f"Bearer {graph_token()}"}
    url = f"{drive_base_url()}/items/{folder_item_id}/children?$select=name&$top=200"
    for _ in range(10):
        r = requests.get(url, headers=headers, timeout=30)
        data = r.json()
        for it in data.get("value", []):
            name = it.get("name", "")
            m = re.search(r"__sha256_([0-9a-f]{12})", name)
            if m: hashes.add(m.group(1))
        if not data.get("@odata.nextLink"): break
        url = data["@odata.nextLink"]
    return hashes

# ----------------------------------------------------
# PDF BUILDER
# ----------------------------------------------------
def build_pdf_from_images_high_quality(image_bytes_list: list[bytes]) -> bytes:
    if not image_bytes_list: raise ValueError("No hay imágenes.")
    out = io.BytesIO()
    c = canvas.Canvas(out, pageCompression=0)
    margin = 10 * mm
    for b in image_bytes_list:
        img = _open_img_safe(b)
        if img.mode != "RGB": img = img.convert("RGB")
        w_px, h_px = img.size
        if w_px >= h_px: page_w, page_h = landscape(letter)
        else: page_w, page_h = portrait(letter)
        
        png_buf = io.BytesIO()
        img.save(png_buf, format="PNG", optimize=False)
        png_buf.seek(0)
        
        max_w = page_w - 2 * margin
        max_h = page_h - 2 * margin
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
# STATE & FLOW
# ----------------------------------------------------
if "camera_photos" not in st.session_state: st.session_state.camera_photos = []
if "gallery_photos" not in st.session_state: st.session_state.gallery_photos = []
if "uploaded_ok" not in st.session_state: st.session_state.uploaded_ok = False
if "uploaded_folio" not in st.session_state: st.session_state.uploaded_folio = ""
if "final_screen" not in st.session_state: st.session_state.final_screen = False

def reset_flow():
    st.session_state.camera_photos = []
    st.session_state.gallery_photos = []
    st.session_state.uploaded_ok = False
    st.session_state.final_screen = False

# ----------------------------------------------------
# SCREENS
# ----------------------------------------------------
if st.session_state.final_screen:
    render_header()
    scroll_to_top()
    st.markdown("""
<div class="success-wrap">
  <div class="success-title">✅ Proceso finalizado</div>
  <div class="success-sub">Gracias. Tus documentos fueron registrados correctamente.</div>
</div>
""", unsafe_allow_html=True)
    if st.button("🔁 Subir otra cotización", type="primary"):
        reset_flow()
        st.rerun()
    st.stop()

if st.session_state.uploaded_ok:
    render_header()
    scroll_to_top()
    st.markdown(f"""
<div class="success-wrap">
  <div class="success-title">✅ Carga completada</div>
  <div class="success-sub">Folio <b>{st.session_state.uploaded_folio}</b></div>
</div>
""", unsafe_allow_html=True)
    if st.button("📤 Subir más fotos", type="primary"):
        reset_flow()
        st.rerun()
    if st.button("✅ Finalizar"):
        st.session_state.final_screen = True
        st.rerun()
    st.stop()

# MAIN
render_header()
scroll_to_top()

folio_input = st.text_input("Folio de la cotización", placeholder="Ej. 251215-0FF480")
folio = normalize_folio(folio_input)

if not folio:
    st.info("Escribe el folio para continuar.")
    st.stop()
if not is_valid_folio(folio):
    st.error("Formato inválido.")
    st.stop()

st.success(f"Folio válido: **{folio}**")

base_folder = st.secrets["azure_app"].get("onedrive_base_folder", "fotos_cotizaciones")

st.subheader("📁 Galería")
uploaded_files = st.file_uploader("Sube fotos", type=["jpg","png","heic"], accept_multiple_files=True)
if uploaded_files:
    st.session_state.gallery_photos = [{"bytes": f.getvalue(), "mime": f.type, "name": f.name} for f in uploaded_files]

st.markdown("---")
st.subheader("📸 Cámara")
camera_photo = st.camera_input("Toma foto", key="camera_input")

c1, c2, c3 = st.columns(3)
if c1.button("➕ Agregar foto"):
    if camera_photo:
        st.session_state.camera_photos.append({"bytes": camera_photo.getvalue(), "mime": camera_photo.type})
        st.success("Foto agregada")
        st.rerun()
if c2.button("🗑️ Borrar fotos"):
    st.session_state.camera_photos = []
    st.rerun()
c3.metric("Tomadas", len(st.session_state.camera_photos))

if st.session_state.camera_photos:
    with st.expander("Ver fotos tomadas"):
        cols = st.columns(3)
        for i, p in enumerate(st.session_state.camera_photos):
            img = normalize_for_preview(p["bytes"], "camera")
            if img: cols[i%3].image(img, use_container_width=True)

st.markdown("---")
if st.button("💾 Subir fotos", type="primary"):
    if not st.session_state.gallery_photos and not st.session_state.camera_photos:
        st.error("No hay fotos.")
        st.stop()
    
    # NEW PROGRESS LOGIC
    status_text = st.empty()
    bar = st.progress(0)
    status_text.markdown("⏳ **Subiendo...**")
    
    try:
        target_id = ensure_path([base_folder, folio])
        exist_hashes = list_existing_hashes(target_id)
        
        items = st.session_state.gallery_photos + st.session_state.camera_photos
        pdf_imgs = []
        
        for i, item in enumerate(items):
            src_type = "camera" if item in st.session_state.camera_photos else "upload"
            sb, sm, ss = prepare_for_storage(item["bytes"], item.get("mime"), src_type)
            pdf_imgs.append(sb)
            
            h = sha256_bytes(item["bytes"])[:12]
            if h not in exist_hashes:
                fname = f"{folio}_{src_type}_{datetime.now().strftime('%H%M%S')}__{h}{ss}"
                upload_small_file_to_folder(target_id, fname, sb, sm)
            
            # Update bar
            bar.progress((i+1)/len(items))
            
        # PDF
        try:
            pdf_b = build_pdf_from_images_high_quality(pdf_imgs)
            pdf_n = f"{folio}_fotos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            upload_small_file_to_folder(target_id, pdf_n, pdf_b, "application/pdf")
        except Exception: pass
        
        bar.progress(100)
        status_text.markdown("✅ **Finalizado**")
        
        st.session_state.uploaded_ok = True
        st.session_state.uploaded_folio = folio
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")
