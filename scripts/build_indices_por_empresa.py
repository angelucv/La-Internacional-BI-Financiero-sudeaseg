"""
Descarga el Excel «Índice por empresa» (Boletín en cifras) y genera:
- `data/public/indices_por_empresa_historico_largo.csv` — todas las hojas mensuales del libro
  (p. ej. Enero + Febrero en el archivo de febrero).
- `data/public/indices_por_empresa_mes_actual.csv` — último mes disponible (mismo criterio que antes).

Uso: python scripts/build_indices_por_empresa.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DOWNLOADS = ROOT / "data" / "raw" / "downloads"
PUBLIC = ROOT / "data" / "public"

BASE = "https://www.sudeaseg.gob.ve"

# Ajustar cuando publiquen un archivo con mes más reciente (p. ej. Mar.xlsx).
SOURCES: list[tuple[int, str]] = [
    (
        2026,
        "/Descargas/Estadisticas/Cifras%20Mensuales/"
        "3%20Indice%20por%20Empresa/"
        "A%C3%B1o%202026/3_Indice_por_Empresa_Feb.xlsx",
    ),
]

SHEET_TO_MONTH: dict[str, int] = {
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


def _parse_indices_sheet(raw: pd.DataFrame, year: int, month: int) -> list[dict]:
    rows: list[dict] = []
    for i in range(12, len(raw)):
        row = raw.iloc[i]
        rank = row.iloc[1]
        name = row.iloc[2]
        if pd.isna(name) or str(name).strip() == "":
            break
        sname = str(name).strip()
        if sname.upper() == "TOTAL" or sname.upper().startswith("TOTAL "):
            break
        if isinstance(rank, str) and "TOTAL" in str(rank).upper():
            break
        vals = [row.iloc[j] for j in range(3, 12)]
        if len(vals) < 9:
            vals = vals + [None] * (9 - len(vals))
        rows.append(
            {
                "NOMBRE_EMPRESA": sname,
                "year": year,
                "month": month,
                "SINI_PAG_VS_PRIM_PCT": vals[0],
                "RESERVAS_VS_PRIM_PCT": vals[1],
                "SINI_INC_VS_PRIM_DEV_PCT": vals[2],
                "COMISION_VS_PRIM_PCT": vals[3],
                "GAST_ADQ_VS_PRIM_PCT": vals[4],
                "GAST_ADM_VS_PRIM_PCT": vals[5],
                "COSTO_REAS_VS_PRIM_DEV_PCT": vals[6],
                "TASA_COMBINADA_PCT": vals[7],
                "INDICE_COB_RESERVAS": vals[8],
            }
        )
    return rows


def parse_indices_workbook(path: Path, year: int, archivo_fuente: str) -> pd.DataFrame:
    """Todas las hojas mensuales reconocidas (Enero, Febrero, …) en un solo libro."""
    xl = pd.ExcelFile(path)
    parts: list[pd.DataFrame] = []
    for sheet in xl.sheet_names:
        if sheet not in SHEET_TO_MONTH:
            continue
        month = SHEET_TO_MONTH[sheet]
        raw = pd.read_excel(path, sheet_name=sheet, header=None)
        recs = _parse_indices_sheet(raw, year, month)
        if not recs:
            continue
        df = pd.DataFrame(recs)
        df["archivo_fuente"] = archivo_fuente
        df["hoja"] = sheet
        parts.append(df)
    if not parts:
        raise ValueError(f"No se encontraron hojas mensuales en {path.name}: {xl.sheet_names}")
    return pd.concat(parts, ignore_index=True)


def main() -> int:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    all_hist: list[pd.DataFrame] = []
    for year, rel in SOURCES:
        url = BASE + rel
        name = rel.split("/")[-1]
        local = DOWNLOADS / name
        print(f"Descargando {url} -> {local.name}")
        try:
            _download(url, local)
        except Exception as e:
            print(f"AVISO: no se pudo descargar ({e}). Si ya existe {local}, se usará local.")
            if not local.exists():
                return 1
        df = parse_indices_workbook(local, year, name)
        all_hist.append(df)

    historico = pd.concat(all_hist, ignore_index=True)
    dest_hist = PUBLIC / "indices_por_empresa_historico_largo.csv"
    historico.to_csv(dest_hist, sep=";", index=False, encoding="utf-8")
    print(f"Escrito {dest_hist} ({len(historico)} filas)")

    # Último año-mes global
    historico["_k"] = historico["year"] * 100 + historico["month"]
    kmax = int(historico["_k"].max())
    actual = historico[historico["_k"] == kmax].drop(columns=["_k"])
    dest_act = PUBLIC / "indices_por_empresa_mes_actual.csv"
    actual.to_csv(dest_act, sep=";", index=False, encoding="utf-8")
    print(f"Escrito {dest_act} ({len(actual)} filas, corte año-mes {kmax})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
