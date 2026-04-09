"""
Descarga (si aplica) y compila primas netas cobradas por empresa desde los Excel
oficiales de SUDEASEG (cifras mensuales) en un CSV largo: 2023 → último mes disponible 2026.

Uso: python scripts/build_primas_historico.py
"""
from __future__ import annotations

import calendar
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DOWNLOADS = ROOT / "data" / "raw" / "downloads"
PUBLIC = ROOT / "data" / "public"

BASE = "https://www.sudeaseg.gob.ve"

SOURCES: list[tuple[int, str]] = [
    (
        2023,
        "/Descargas/Estadisticas/Cifras%20Mensuales/"
        "5%20Primas%20Netas%20Cobradas%20por%20Empresa/"
        "primas-netas-cobradas-por-empresa-2023.xlsx",
    ),
    (
        2024,
        "/Descargas/Estadisticas/Cifras%20Mensuales/"
        "5%20Primas%20Netas%20Cobradas%20por%20Empresa/"
        "Dic%20primas-netas-cobradas-por-empresa-2024.xlsx",
    ),
    (
        2025,
        "/Descargas/Estadisticas/Cifras%20Mensuales/"
        "5%20Primas%20Netas%20Cobradas%20por%20Empresa/"
        "A%C3%B1o%202025/5_Primas_Dic.xlsx",
    ),
    (
        2026,
        "/Descargas/Estadisticas/Cifras%20Mensuales/"
        "5%20Primas%20Netas%20Cobradas%20por%20Empresa/"
        "A%C3%B1o%202026/5_Primas_Feb.xlsx",
    ),
]

MESES_ES = {
    "Enero": 1,
    "Febrero": 2,
    "Marzo": 3,
    "Abril": 4,
    "Mayo": 5,
    "Junio": 6,
    "Julio": 7,
    "Agosto": 8,
    "Septiembre": 9,
    "Octubre": 10,
    "Noviembre": 11,
    "Diciembre": 12,
}


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "la-internacional-demo/1.0"})
    with urlopen(req, timeout=120) as resp:
        data = resp.read()
    dest.write_bytes(data)


def _ensure_files() -> dict[int, Path]:
    """Devuelve año -> ruta local del Excel."""
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    out: dict[int, Path] = {}
    for year, rel in SOURCES:
        url = BASE + rel
        name = rel.split("/")[-1]
        path = DOWNLOADS / name
        if not path.exists():
            print(f"Descargando {year}: {url}")
            _download(url, path)
        else:
            print(f"Ya existe {year}: {path.name}")
        out[year] = path
    return out


_SKIP_PREFIXES = (
    "TOTAL PRIMERAS",
    "TOTAL SEGUNDAS",
    "TOTAL TERCERAS",
    "TOTAL CUARTAS",
    "TOTAL EMPRESAS RESTANTES",
)


def _sheet_skip_name(name: str) -> bool:
    n = name.strip().upper()
    return any(n.startswith(p) for p in _SKIP_PREFIXES)


def _sheet_stop_name(name: str) -> bool:
    """Fin de tabla de empresas (total mercado o bloque no empresa)."""
    n = name.strip().upper()
    if "VALOR DEL MERCADO" in n:
        return True
    if "TOTAL (EN MILES" in n or "TOTAL(EN MILES" in n.replace(" ", ""):
        return True
    return False


def _parse_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """Extrae ranking, empresa, primas, % participación desde una hoja cruda."""
    rows = []
    for i in range(12, len(df)):
        r = df.iloc[i]
        rank = r[1]
        name = r[2]
        primas = r[3]
        pct = r[4] if len(r) > 4 else None
        if pd.isna(name) or str(name).strip() == "":
            continue
        ns = str(name).strip()
        if _sheet_stop_name(ns):
            break
        if _sheet_skip_name(ns):
            continue
        try:
            rank_i = int(float(rank)) if pd.notna(rank) else None
        except (TypeError, ValueError):
            rank_i = None
        try:
            primas_f = float(primas) if pd.notna(primas) else None
        except (TypeError, ValueError):
            primas_f = None
        try:
            pct_f = float(pct) if pd.notna(pct) else None
        except (TypeError, ValueError):
            pct_f = None
        rows.append(
            {
                "ranking": rank_i,
                "empresa_raw": ns,
                "primas_miles_bs": primas_f,
                "pct_participacion": pct_f,
            }
        )
    return pd.DataFrame(rows)


def _normalize_empresa(name: str) -> str:
    s = " ".join(str(name).split())
    low = s.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    if "internacional" in low and "seguros" in low:
        return "La Internacional"
    return s


def build_long_table(paths: dict[int, Path]) -> pd.DataFrame:
    blocks = []
    for year, path in sorted(paths.items()):
        xl = pd.ExcelFile(path)
        for sheet in xl.sheet_names:
            mes = MESES_ES.get(sheet.strip())
            if mes is None:
                continue
            raw = pd.read_excel(path, sheet_name=sheet, header=None)
            part = _parse_sheet(raw)
            if part.empty:
                continue
            last = calendar.monthrange(year, mes)[1]
            fecha = f"{year:04d}-{mes:02d}-{last:02d}"
            part = part.assign(
                year=year,
                month=mes,
                fecha_periodo=fecha,
                archivo_fuente=path.name,
                hoja_mes=sheet,
            )
            part["empresa_norm"] = part["empresa_raw"].map(_normalize_empresa)
            blocks.append(part)
    if not blocks:
        raise RuntimeError("No se pudo leer ninguna hoja de primas.")
    return pd.concat(blocks, ignore_index=True)


def main() -> int:
    paths = _ensure_files()
    df = build_long_table(paths)
    out = PUBLIC / "primas_netas_mensual_largo.csv"
    PUBLIC.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, sep=";", index=False, encoding="utf-8")
    print(f"Escrito {out} ({len(df)} filas).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
