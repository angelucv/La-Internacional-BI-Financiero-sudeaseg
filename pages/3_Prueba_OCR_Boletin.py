"""
Prueba OCR local (EasyOCR) sobre 2 páginas del Boletín en cifras — Diciembre 2025.

Requiere: pip install easyocr pymupdf
La primera ejecución descarga modelos (~100MB+).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demo_config import APP_NAME_SHORT, render_brand_header, render_demo_sidebar
from demo_ocr_boletin import (
    agrupar_en_filas,
    easyocr_detections_to_lines,
    filas_a_texto_tabla,
    pdf_page_to_rgb,
    resolver_pdf_boletin_dic_2025,
)

st.set_page_config(
    page_title=f"Prueba OCR boletín | {APP_NAME_SHORT}",
    page_icon="🔍",
    layout="wide",
)

render_demo_sidebar()
render_brand_header("Prueba OCR — Boletín en cifras (local · EasyOCR)")

st.markdown(
    "### Diciembre 2025 — dos páginas de ejemplo\n"
    "- **Página 8** (índice 7): cuadro *Resultado técnico / Saldo de operaciones*.\n"
    "- **Página 10** (índice 9): infografía *Primas netas cobradas (PNC)* y participación Top 10.\n\n"
    "Los números en tablas complejas pueden salir fragmentados; esto es una **prueba inicial** para validar el OCR."
)

pdf_path = resolver_pdf_boletin_dic_2025()
if pdf_path is None:
    st.error(
        "No se encontró el PDF del boletín (p. ej. `Boletín Cifras Nro 50 Diciembre.pdf`) "
        "en `data/raw/pdf/`. Colóquelo ahí y recargue."
    )
    st.stop()

st.caption(f"Archivo: `{pdf_path.name}`")

# Páginas 1-based → índice 0-based
P_DEFAULT = (8, 10)
zoom = st.slider("Zoom render (calidad OCR)", 1.5, 3.5, 2.5, 0.1)
y_tol = st.slider("Tolerancia agrupación vertical (px)", 8.0, 40.0, 18.0, 1.0)


@st.cache_resource(show_spinner="Cargando modelos EasyOCR (solo la primera vez puede tardar)…")
def _reader():
    import easyocr

    return easyocr.Reader(["es", "en"], gpu=False, verbose=False)


if st.button("Ejecutar OCR en páginas 8 y 10", type="primary"):
    reader = _reader()
    prog = st.progress(0.0, text="Procesando…")
    for idx, p1 in enumerate(P_DEFAULT):
        p0 = p1 - 1
        prog.progress((idx) / 2.0, text=f"Página {p1}…")
        try:
            img = pdf_page_to_rgb(pdf_path, p0, zoom=zoom)
        except Exception as e:
            st.error(f"Página {p1}: {e}")
            continue

        dets = reader.readtext(img)
        lines = easyocr_detections_to_lines(dets)
        filas = agrupar_en_filas(lines, y_tol=y_tol)
        tabla = filas_a_texto_tabla(filas)

        st.subheader(f"Página {p1}")
        c1, c2 = st.columns((1, 1))
        with c1:
            st.image(img, caption=f"Raster {img.shape[1]}×{img.shape[0]} px", use_container_width=True)
        with c2:
            st.metric("Cajas OCR detectadas", len(dets))
            st.metric("Filas agrupadas (heurística)", len(tabla))

        df = pd.DataFrame(tabla)
        st.dataframe(df, use_container_width=True, height=min(600, 28 * (len(df) + 3)))

        with st.expander(f"Texto crudo línea a línea (página {p1})"):
            raw_lines = sorted(lines, key=lambda r: (r.y_centro, r.x_centro))
            st.text_area(
                "detalle",
                "\n".join(f"[{x.confianza:.2f}] {x.texto}" for x in raw_lines),
                height=240,
                label_visibility="collapsed",
            )

    prog.progress(1.0, text="Listo")
    st.success("OCR completado. Revise filas con baja confianza y números partidos.")
else:
    st.info('Pulse **Ejecutar OCR en páginas 8 y 10** para generar la vista. Primera vez: descarga de modelos.')

st.caption(
    "Motor: **EasyOCR** (local). Para más meses: duplique esta página o parametrizaremos PDF y rango de páginas."
)
