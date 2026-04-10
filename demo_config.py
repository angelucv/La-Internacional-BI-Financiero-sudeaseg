# Demo accionistas — La Internacional (datos SUDEASEG)
import base64
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
LOGO_PATH = ROOT / "Images" / "Logo horizontal.svg"

# Logos opcionales en Images/ (se prueba en orden; extensiones: .svg .png .webp .jpg .jpeg)
# Coloca aquí PNG/JPG reales para mejor resultado en el sidebar (los SVG solo con texto se ven «planos»).
SIDEBAR_LOGO_BASENAMES: tuple[str, ...] = (
    "Logo vertical",
    "483925234_1255226655991628_1456856016639894975_n",
    "La_Internacional_de_Seguros_Vertical_d8bff5a058",
    "Logo-Internacional-azul-amarillo",
    "Logo-Internacional-blanco-amarillo",
)

# Cabecera de página: ancho horizontal primero; respaldos con marca
HEADER_LOGO_BASENAMES: tuple[str, ...] = (
    "Logo horizontal",
    "Logo-Internacional-azul-amarillo",
    "La_Internacional_de_Seguros_Vertical_d8bff5a058",
)

# Título bajo el logo (cabecera principal)
APP_NAME = "Demo BI información financiera La Internacional"
# Texto corto para sidebar / pestañas del navegador
APP_NAME_SHORT = "La Internacional · mercado y sector"
COMPANY_FOCUS = "Internacional, C.A. de Seguros"
DATA_YEAR = 2023

COLOR_BRAND_NAVY = "#27306E"
COLOR_BRAND_GOLD = "#FFCB05"
COLOR_MUTED = "#4D4D4D"

# Colores de línea por peer_id (alto contraste; La Internacional siempre dorado)
PEER_LINE_COLORS: dict[str, str] = {
    "La Internacional": "#FFCB05",
    "mercantil": "#E63946",
    "caracas": "#1D3557",
    "oceanica": "#2A9D8F",
    "mapfre": "#7209B7",
    "piramide": "#F77F00",
    "hispana": "#06A77D",
    "constitucion": "#BC4749",
    "banesco": "#4361EE",
    "miranda": "#3A86FF",
    "real seguros": "#FB5607",
}


def plotly_brand_theme(
    *,
    height: int = 520,
    legend: dict | None = None,
    margin: dict | None = None,
) -> dict:
    """Estilo visual común para gráficos Plotly (marca La Internacional)."""
    leg = legend or dict(
        orientation="h",
        yanchor="top",
        y=-0.26,
        xanchor="center",
        x=0.5,
        font=dict(size=11, color=COLOR_BRAND_NAVY),
        bgcolor="rgba(255,255,255,0.7)",
        bordercolor="rgba(39,48,110,0.12)",
        borderwidth=1,
    )
    mar = margin or dict(t=96, b=168, l=56, r=40)
    return dict(
        template="plotly_white",
        font=dict(
            family="Segoe UI, system-ui, -apple-system, Roboto, sans-serif",
            size=13,
            color=COLOR_BRAND_NAVY,
        ),
        paper_bgcolor="#F0F4FB",
        plot_bgcolor="rgba(255,255,255,0.97)",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, sans-serif",
            bordercolor=COLOR_BRAND_NAVY,
        ),
        height=height,
        legend=leg,
        margin=mar,
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(39,48,110,0.06)",
            zeroline=False,
            showline=True,
            linewidth=1,
            linecolor="rgba(39,48,110,0.18)",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(39,48,110,0.08)",
            zeroline=False,
            showline=True,
            linewidth=1,
            linecolor="rgba(39,48,110,0.18)",
        ),
    )


def color_linea_peer(peer_id: str, fallback_index: int) -> str:
    """Color Plotly por compañía; si no hay clave, usa tonos bien separados."""
    if peer_id in PEER_LINE_COLORS:
        return PEER_LINE_COLORS[peer_id]
    fallbacks = [
        "#6C757D",
        "#0EAD69",
        "#EE6C4D",
        "#293241",
        "#98C1D9",
        "#9B5DE5",
        "#00BBF9",
    ]
    return fallbacks[fallback_index % len(fallbacks)]

FUENTE_DATOS = (
    "Cuadros oficiales del anuario «Seguro en Cifras» (SUDEASEG) y series mensuales descargables "
    "(primas netas por empresa), compilación para el demo."
)

# Sidebar: texto concreto (sin rótulos tipo «para la dirección») + autor (HTML)
SIDEBAR_RESUMEN_HTML = (
    "<p style='margin:0 0 0.7rem 0;line-height:1.52;font-size:0.98rem;color:#27306E;'>"
    "Ranking y participación de mercado; siniestralidad, comisiones y gastos "
    "frente al <strong>promedio del sector</strong> (boletín SUDEASEG); primas mensuales en "
    "<strong>USD</strong> al tipo oficial de cada mes.</p>"
    "<p style='margin:0;line-height:1.48;font-size:0.88rem;color:#4a4a4a;'>"
    "Todo proviene de información pública SUDEASEG: anuario <em>Seguro en Cifras</em>, boletines "
    "y series de primas. Los cierres contables oficiales son los de los estados financieros auditados.</p>"
)
SIDEBAR_AUTOR_HTML = (
    '<p style="margin:0.9rem 0 0 0;padding-top:0.75rem;border-top:1px solid rgba(39,48,110,0.18);'
    'font-size:0.88rem;line-height:1.5;color:#27306E;">'
    "<strong>Elaborado por:</strong> Angel Colmenares<br>"
    '<a href="mailto:angelc.ucv@gmail.com" style="color:#1D3557;text-decoration:underline;">'
    "angelc.ucv@gmail.com</a></p>"
)

def _first_existing_logo(basenames: tuple[str, ...]) -> Path | None:
    img_dir = ROOT / "Images"
    if not img_dir.is_dir():
        return None
    exts = (".svg", ".png", ".webp", ".jpg", ".jpeg", ".JPG", ".JPEG", ".PNG", ".WEBP")
    allowed = {".svg", ".png", ".webp", ".jpg", ".jpeg"}
    for base in basenames:
        for ext in exts:
            p = img_dir / f"{base}{ext}"
            if p.is_file():
                return p
        for p in sorted(img_dir.glob(f"{base}.*")):
            if p.is_file() and p.suffix.lower() in allowed:
                return p
    return None


def sidebar_logo_path() -> Path | None:
    """Primera coincidencia: logo para sidebar claro."""
    return _first_existing_logo(SIDEBAR_LOGO_BASENAMES)


def header_logo_path() -> Path | None:
    """Logo ancho para cabecera principal (data-URI; más fiable que st.image con algunos SVG)."""
    return _first_existing_logo(HEADER_LOGO_BASENAMES)


def _mime_sidebar_logo(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".webp": "image/webp",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(ext, "application/octet-stream")


def render_sidebar_logo_block(path: Path) -> None:
    """
    Logo compacto arriba del sidebar: limita altura para recortar márgenes en blanco del archivo
    y evita cajas con mucho padding.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return
    b64 = base64.b64encode(raw).decode("ascii")
    mime = _mime_sidebar_logo(path)
    st.sidebar.markdown(
        f'<div style="margin:0 0 0.5rem 0;padding:4px 2px;line-height:0;text-align:center;">'
        f'<img src="data:{mime};base64,{b64}" alt="La Internacional" '
        f'style="width:100%;max-width:240px;max-height:220px;height:auto;object-fit:contain;'
        f'object-position:center;display:block;margin:0 auto;"/></div>',
        unsafe_allow_html=True,
    )


def render_brand_header(
    subtitle: str | None = None,
    *,
    logo_width_px: int = 720,
):
    """
    Cabecera de marca: logo centrado (data-URI), título del demo y subtítulo opcional.
    """
    h_logo = header_logo_path()
    _, cx, _ = st.columns([0.05, 0.90, 0.05])
    with cx:
        if h_logo is not None:
            try:
                raw = h_logo.read_bytes()
                b64 = base64.b64encode(raw).decode("ascii")
                mime = _mime_sidebar_logo(h_logo)
                st.markdown(
                    f'<div style="text-align:center;margin:0.35rem 0 0.5rem 0;">'
                    f'<img src="data:{mime};base64,{b64}" alt="La Internacional" '
                    f'style="width:100%;max-width:{logo_width_px}px;height:auto;display:inline-block;"/>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
            except OSError:
                pass
        st.markdown(
            f'<p style="text-align:center;color:{COLOR_BRAND_NAVY};font-size:1.12rem;font-weight:600;'
            f'margin:0.55rem 0 0.2rem 0;line-height:1.35;">{APP_NAME}</p>',
            unsafe_allow_html=True,
        )
        if subtitle:
            st.markdown(
                f'<p style="text-align:center;color:{COLOR_MUTED};font-size:0.88rem;'
                f"line-height:1.45;margin:0.15rem 0 0.5rem 0;max-width:42rem;margin-left:auto;margin-right:auto;"
                f'">{subtitle}</p>',
                unsafe_allow_html=True,
            )


def render_demo_sidebar():
    """
    Sidebar: primero el logo (arriba del todo), luego enlaces (navegación nativa oculta en config).
    """
    s_logo = sidebar_logo_path()
    if s_logo is not None:
        render_sidebar_logo_block(s_logo)
    st.sidebar.markdown("---")
    st.sidebar.page_link("app.py", label="Inicio", icon="🏠")
    st.sidebar.page_link(
        "pages/1_Sector_Top3_y_Internacional.py",
        label="Sector Top3 y Internacional",
        icon="🏆",
    )
    st.sidebar.page_link(
        "pages/2_Serie_historica_Top5.py",
        label="Serie histórica Top5",
        icon="📈",
    )
    st.sidebar.caption(
        "En **Sector** y **Serie histórica** hay una sección común: "
        "tabla y gráfico **Resultado técnico / Top 5 por PNC** (cuadro 1 del boletín)."
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f'<p style="font-size:1.12rem;font-weight:700;color:#27306E;line-height:1.3;margin:0 0 0.45rem 0;">'
        f"{APP_NAME_SHORT}</p>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f'<div style="font-size:0.98rem;line-height:1.52;color:#27306E;margin:0;">'
        f"{SIDEBAR_RESUMEN_HTML}</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(SIDEBAR_AUTOR_HTML, unsafe_allow_html=True)
