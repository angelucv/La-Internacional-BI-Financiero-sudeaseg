"""
Extracción de tablas de primas netas cobradas por empresa desde PDF del boletín
«Cifras mensuales» / Boletín en cifras (SUDEASEG).

Los PDF no están versionados en el repo: colóquelos en data/raw/boletin_pdf/ (local).
"""
from __future__ import annotations

import calendar
import re
from pathlib import Path

import pandas as pd

try:
    import pdfplumber
except ImportError as e:
    pdfplumber = None  # type: ignore[misc, assignment]
    _IMPORT_ERR = e
else:
    _IMPORT_ERR = None

MESES_TEXTO: dict[str, int] = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

MESES_CORTO: dict[str, int] = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


def _ensure_pdfplumber() -> None:
    if pdfplumber is None:
        raise RuntimeError(
            "Falta pdfplumber. Instale dependencias: pip install pdfplumber"
        ) from _IMPORT_ERR


def parse_numero_ve(s: str | None) -> float | None:
    """
    Convierte cifras estilo VE en float: miles con punto, decimales con coma (p. ej. 39.620.347,68).
    También acepta porcentajes 25,74.
    """
    if s is None:
        return None
    t = str(s).strip().replace("\xa0", " ").replace(" ", "")
    if not t or t in ("—", "-", "–", "…"):
        return None
    neg = t.startswith("-")
    if neg:
        t = t[1:].strip()
    if t.startswith("(") and t.endswith(")"):
        neg = True
        t = t[1:-1].strip()
    if not t:
        return None
    if "," in t:
        left, right = t.rsplit(",", 1)
        if re.fullmatch(r"\d{1,4}", right):
            intpart = left.replace(".", "")
            try:
                val = float(f"{intpart}.{right}")
            except ValueError:
                return None
        else:
            return None
    elif "." in t:
        parts = t.split(".")
        if len(parts[-1]) == 3 and len(parts) >= 2:
            val = float("".join(parts))
        elif len(parts) == 2 and len(parts[1]) <= 2:
            try:
                val = float(f"{parts[0]}.{parts[1]}")
            except ValueError:
                return None
        else:
            try:
                val = float(t.replace(".", "").replace(",", "."))
            except ValueError:
                return None
    else:
        try:
            val = float(t)
        except ValueError:
            return None
    return -val if neg else val


def _cell_str(c: object | None) -> str:
    if c is None:
        return ""
    return " ".join(str(c).split())


def _is_stop_name(name: str) -> bool:
    u = name.strip().upper()
    if "VALOR DEL MERCADO" in u:
        return True
    if u == "TOTAL" or u.startswith("TOTAL "):
        return True
    if "TOTAL (EN MILES" in u.replace(" ", ""):
        return True
    return False


def _parse_ranking_row(cells: list[str]) -> dict | None:
    if len(cells) < 4:
        return None
    # Unir celdas intermedias como nombre si la tabla está troceada
    rank_s = cells[0]
    try:
        r0 = float(str(rank_s).replace(",", ".").strip())
        rank_i = int(r0)
    except (TypeError, ValueError):
        return None
    if rank_i < 1 or rank_i > 500:
        return None
    # últimas dos cifras: primas y % (o % y primas — probar ambos órdenes)
    last = parse_numero_ve(cells[-1])
    prev = parse_numero_ve(cells[-2])
    name_parts = cells[1:-2]
    name = " ".join(x for x in name_parts if x).strip()
    if len(name) < 4 or _is_stop_name(name):
        return None
    primas: float | None
    pct: float | None
    if prev is not None and last is not None:
        # Participación suele estar entre ~0 y 100; primas en miles de Bs. son órdenes mayores
        a_small = abs(prev) <= 150.0
        b_small = abs(last) <= 150.0
        if a_small and not b_small:
            pct, primas = prev, last
        elif b_small and not a_small:
            pct, primas = last, prev
        elif abs(prev) >= abs(last):
            primas, pct = prev, last
        else:
            primas, pct = last, prev
    else:
        primas, pct = prev, last
    if primas is None:
        return None
    return {
        "ranking": rank_i,
        "empresa_raw": name,
        "primas_miles_bs": primas,
        "pct_participacion": pct,
    }


def _rows_from_table(table: list[list[str | None]]) -> list[dict]:
    rows: list[dict] = []
    for raw in table:
        cells = [_cell_str(c) for c in raw if c is not None]
        if not any(cells):
            continue
        # Saltar cabeceras
        joined = " ".join(cells).upper()
        if "PARTICIPACI" in joined and "MERCADO" in joined and "EMPRESA" in joined:
            continue
        if "RANKING" in joined or joined.strip().startswith("#"):
            continue
        rec = _parse_ranking_row(cells)
        if rec:
            rows.append(rec)
        elif len(cells) >= 2 and _is_stop_name(cells[1] if len(cells) > 1 else cells[0]):
            break
    return rows


def infer_year_month_from_text(text: str) -> tuple[int, int] | None:
    """Busca «Febrero 2026» o «Febrero de 2026» en el texto del boletín."""
    t = text.lower()
    m = re.search(
        r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)"
        r"\s*(?:de\s*)?(\d{4})\b",
        t,
        re.I,
    )
    if m:
        mes = MESES_TEXTO.get(m.group(1).lower())
        year = int(m.group(2))
        if mes and 2000 <= year <= 2100:
            return year, mes
    return None


def infer_year_month_from_filename(name: str) -> tuple[int, int] | None:
    base = Path(name).stem.lower()
    m = re.search(r"(20\d{2})[-_](\d{1,2})\b", base)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return y, mo
    m = re.search(
        r"\b(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)[a-z]*[-_]?(\d{4})\b",
        base,
        re.I,
    )
    if m:
        mo = MESES_CORTO.get(m.group(1).lower()[:3])
        y = int(m.group(2))
        if mo and 2000 <= y <= 2100:
            return y, mo
    m = re.search(r"(\d{4})[-_]?(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)", base, re.I)
    if m:
        y = int(m.group(1))
        mo = MESES_CORTO.get(m.group(2).lower()[:3])
        if mo and 2000 <= y <= 2100:
            return y, mo
    return None


def extract_text_first_pages(path: Path, max_pages: int = 3) -> str:
    _ensure_pdfplumber()
    chunks: list[str] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages[:max_pages]):
            tx = page.extract_text() or ""
            chunks.append(tx)
    return "\n".join(chunks)


def extract_primas_ranking_from_pdf(path: Path) -> pd.DataFrame:
    """
    Lee todas las tablas del PDF y devuelve el bloque que parece ranking de primas + participación.
    """
    _ensure_pdfplumber()
    best: list[dict] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                continue
            for table in tables:
                if not table:
                    continue
                cand = _rows_from_table(table)
                if len(cand) > len(best):
                    best = cand
    if not best:
        raise ValueError(
            f"No se detectó la tabla de ranking en {path.name}. "
            "Compruebe que el PDF sea el cuadro de primas netas por empresa del boletín SUDEASEG."
        )
    return pd.DataFrame(best)


def assign_periodo(
    df: pd.DataFrame, year: int, month: int, archivo: str
) -> pd.DataFrame:
    last = calendar.monthrange(year, month)[1]
    fecha = f"{year:04d}-{month:02d}-{last:02d}"
    out = df.copy()
    out["year"] = year
    out["month"] = month
    out["fecha_periodo"] = fecha
    out["archivo_fuente"] = archivo
    out["hoja_mes"] = f"PDF_{month:02d}"
    return out
