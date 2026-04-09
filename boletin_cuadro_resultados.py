"""
Cuadro 1 — Resultado técnico / Saldo de operaciones (Boletín en cifras SUDEASEG).

Los PDF recientes del boletín suelen llevar las tablas como gráficos sin capa de texto;
el mismo cuadro se publica como Excel «1 Cuadro de Resultados» en la misma sección de
Cifras mensuales. Este módulo parsea ese Excel oficial y expone el CSV en `data/public/`.
"""
from __future__ import annotations

import calendar
import re
from pathlib import Path

import pandas as pd

from demo_historico import empresa_peer_id

ROOT = Path(__file__).resolve().parent
DATA_PUBLIC = ROOT / "data" / "public"
CSV_NAME = "resultado_tecnico_saldo_mensual.csv"

MESES_ES = {
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


def _infer_year_month_from_banner(df: pd.DataFrame) -> tuple[int, int] | None:
    """Lee «ACUMULADA AL 31 DE ENERO DE 2026» en las primeras filas."""
    for i in range(min(12, len(df))):
        for j in range(min(6, df.shape[1])):
            cell = df.iloc[i, j]
            if cell is None or (isinstance(cell, float) and pd.isna(cell)):
                continue
            s = str(cell).strip()
            m = re.search(
                r"ACUMULADA\s+AL\s+(\d{1,2})\s+DE\s+(\w+)\s+DE\s+(\d{4})",
                s,
                re.I,
            )
            if m:
                _dia, mes_txt, year_s = m.group(1), m.group(2).lower(), m.group(3)
                mes = MESES_ES.get(mes_txt)
                if mes:
                    return int(year_s), mes
    return None


def parse_cuadro1_excel(path: Path, sheet: str | int = 0) -> pd.DataFrame:
    """
    Extrae filas de empresa del libro «1 Cuadro de Resultados» (hoja mensual).
    Columnas: PNC (primas netas cobradas), resultado técnico bruto, reaseguro, RT neto,
    gestión general, saldo de operaciones (miles de Bs.).
    """
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    ym = _infer_year_month_from_banner(raw)
    if ym is None:
        raise ValueError(
            f"No se encontró la leyenda «ACUMULADA AL … DE …» en {path.name}. "
            "Compruebe que sea el archivo oficial del boletín."
        )
    year, month = ym
    last = calendar.monthrange(year, month)[1]
    fecha = f"{year:04d}-{month:02d}-{last:02d}"

    rows: list[dict] = []
    for i in range(12, len(raw)):
        r = raw.iloc[i]
        rank = r.iloc[1] if len(r) > 1 else None
        name = r.iloc[2] if len(r) > 2 else None
        if name is None or (isinstance(name, float) and pd.isna(name)):
            continue
        ns = str(name).strip()
        if not ns or ns.upper().startswith("TOTAL"):
            break
        if "consignado" in ns.lower() and "empresas" in ns.lower():
            break
        try:
            rank_i = int(float(rank)) if rank is not None and not pd.isna(rank) else None
        except (TypeError, ValueError):
            rank_i = None
        if rank_i is None:
            continue

        def num(k: int) -> float | None:
            if len(r) <= k:
                return None
            v = r.iloc[k]
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        pnc = num(3)
        rt_b = num(4)
        reas = num(5)
        rt_n = num(6)
        gest = num(7)
        saldo = num(8)

        pct = None
        if pnc is not None and abs(pnc) > 1e-12 and saldo is not None:
            pct = 100.0 * saldo / pnc

        rows.append(
            {
                "ranking": rank_i,
                "empresa_raw": ns,
                "peer_id": empresa_peer_id(ns),
                "pnc_miles_bs": pnc,
                "rt_bruto_miles_bs": rt_b,
                "reaseguro_cedido_miles_bs": reas,
                "rt_neto_miles_bs": rt_n,
                "gestion_general_miles_bs": gest,
                "saldo_operaciones_miles_bs": saldo,
                "pct_saldo_sobre_pnc": pct,
                "year": year,
                "month": month,
                "fecha_periodo": fecha,
                "archivo_fuente": path.name,
            }
        )

    if not rows:
        raise ValueError(f"No se leyeron filas de empresas en {path} (hoja {sheet}).")
    return pd.DataFrame(rows)


def load_resultado_tecnico_saldo() -> pd.DataFrame | None:
    path = DATA_PUBLIC / CSV_NAME
    if not path.exists():
        return None
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    df["fecha_periodo"] = pd.to_datetime(df["fecha_periodo"])
    return df


def top_n_para_infografia(sub: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return sub.head(n).copy()
