"""OCR local (EasyOCR) sobre páginas rasterizadas de PDF del Boletín en cifras."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None  # type: ignore[misc, assignment]


@dataclass
class OcrLine:
    texto: str
    confianza: float
    y_centro: float
    x_centro: float


def pdf_page_to_rgb(path: Path, page_index: int, zoom: float = 2.5) -> np.ndarray:
    """Rasteriza una página del PDF a RGB uint8 (H, W, 3)."""
    if fitz is None:
        raise RuntimeError("Instale pymupdf: pip install pymupdf")
    doc = fitz.open(path)
    if page_index < 0 or page_index >= len(doc):
        doc.close()
        raise IndexError(f"Página {page_index} fuera de rango (0–{len(doc)-1})")
    page = doc[page_index]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    doc.close()
    if arr.shape[2] == 4:
        arr = arr[:, :, :3]
    return arr


def easyocr_detections_to_lines(detections: list[Any]) -> list[OcrLine]:
    """Convierte salida de easyocr.readtext en líneas ordenables."""
    out: list[OcrLine] = []
    for det in detections:
        bbox, text, conf = det[0], det[1], float(det[2])
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        yc = (min(ys) + max(ys)) / 2.0
        xc = (min(xs) + max(xs)) / 2.0
        out.append(OcrLine(texto=str(text).strip(), confianza=conf, y_centro=yc, x_centro=xc))
    return out


def agrupar_en_filas(lines: list[OcrLine], y_tol: float = 18.0) -> list[list[OcrLine]]:
    """Agrupa cajas OCR en filas por proximidad vertical (píxeles)."""
    if not lines:
        return []
    sorted_l = sorted(lines, key=lambda r: (r.y_centro, r.x_centro))
    filas: list[list[OcrLine]] = []
    cur: list[OcrLine] = [sorted_l[0]]
    y0 = sorted_l[0].y_centro
    for r in sorted_l[1:]:
        if abs(r.y_centro - y0) <= y_tol:
            cur.append(r)
        else:
            cur.sort(key=lambda x: x.x_centro)
            filas.append(cur)
            cur = [r]
            y0 = r.y_centro
    cur.sort(key=lambda x: x.x_centro)
    filas.append(cur)
    return filas


def filas_a_texto_tabla(filas: list[list[OcrLine]]) -> list[dict[str, Any]]:
    """Una fila legible: texto unido con separador y confianza mínima."""
    rows = []
    for i, fila in enumerate(filas):
        if not fila:
            continue
        texto = "  |  ".join(t.texto for t in fila)
        conf_min = min(t.confianza for t in fila)
        conf_avg = sum(t.confianza for t in fila) / len(fila)
        rows.append(
            {
                "fila_ocr": i + 1,
                "texto_unido": texto,
                "conf_min": round(conf_min, 4),
                "conf_prom": round(conf_avg, 4),
            }
        )
    return rows


def resolver_pdf_boletin_dic_2025() -> Path | None:
    """Localiza el PDF del boletín n.º 50 Diciembre 2025 en data/raw/pdf/."""
    root = Path(__file__).resolve().parent / "data" / "raw" / "pdf"
    if not root.is_dir():
        return None
    for pat in ("*50*Diciembre*.pdf", "*Cifras*Nro*50*Diciembre*.pdf"):
        hits = list(root.glob(pat))
        if hits:
            return hits[0]
    return None
