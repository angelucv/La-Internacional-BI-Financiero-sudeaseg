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

from demo_historico import empresa_peer_id, load_primas_mensual_largo

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


def _norm_header_cell(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip().upper()
    for a, b in (
        ("Á", "A"),
        ("É", "E"),
        ("Í", "I"),
        ("Ó", "O"),
        ("Ú", "U"),
        ("Ñ", "N"),
    ):
        s = s.replace(a, b)
    return " ".join(s.split())


def _detect_cuadro1_column_indices(raw: pd.DataFrame) -> dict[str, int | None]:
    """
    Localiza columnas por textos del boletín. Si no hay fila de encabezados clara,
    devuelve None en todas (se usará heurística en parse_cuadro1_excel).
    """
    found: dict[str, int | None] = {
        "pnc": None,
        "rt_bruto": None,
        "reaseguro": None,
        "rt_neto": None,
        "gestion": None,
        "saldo": None,
    }
    for i in range(min(22, len(raw))):
        for j in range(min(16, raw.shape[1])):
            t = _norm_header_cell(raw.iloc[i, j])
            if len(t) < 6:
                continue
            if "PRIMAS" in t and "NETAS" in t and ("COBRAD" in t or "COBRADA" in t):
                found["pnc"] = j
            elif "RESULTADO" in t and "TECNICO" in t and "BRUTO" in t:
                found["rt_bruto"] = j
            elif "REASEGURO" in t and "CEDID" in t:
                found["reaseguro"] = j
            elif "RESULTADO" in t and "TECNICO" in t and "NETO" in t:
                found["rt_neto"] = j
            elif "GESTION" in t and "GENERAL" in t:
                found["gestion"] = j
            elif "SALDO" in t and "OPERACION" in t:
                found["saldo"] = j
    return found


def _resolve_cuadro1_layout(raw: pd.DataFrame) -> str:
    """
    «pnc_first»: columnas como PNC, RT bruto, reaseguro… (p. ej. plantilla ene-2026).
    «rt_first»: resultado técnico bruto en la primera columna numérica (p. ej. dic-2025 / PDF pág. 24);
    PNC suele ir al final o solo en otro cuadro — se rellena luego con la serie de primas.
    """
    h = _detect_cuadro1_column_indices(raw)
    if h["pnc"] == 3 and h["rt_bruto"] == 4:
        return "pnc_first"
    if h["rt_bruto"] == 3 and h["saldo"] == 7 and (h["pnc"] is None or h["pnc"] >= 8):
        return "rt_first"
    if h["rt_bruto"] == 3 and h["pnc"] is None and h["reaseguro"] == 4:
        return "rt_first"
    # Sonda primera fila con ranking numérico
    for i in range(11, min(24, len(raw))):
        r = raw.iloc[i]
        try:
            rk = r.iloc[1]
            if rk is None or (isinstance(rk, float) and pd.isna(rk)):
                continue
            int(float(rk))
        except (TypeError, ValueError):
            continue
        v3 = r.iloc[3] if len(r) > 3 else None
        if v3 is None or (isinstance(v3, float) and pd.isna(v3)):
            continue
        try:
            f3 = float(v3)
        except (TypeError, ValueError):
            continue
        v8 = float(r.iloc[8]) if len(r) > 8 and not pd.isna(r.iloc[8]) else None
        if f3 < -400_000:
            return "rt_first"
        if f3 > 2_000_000 and v8 is not None and abs(v8) < abs(f3) * 0.05:
            return "pnc_first"
    return "rt_first"


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

    El orden de columnas en el Excel **no es fijo**: unas plantillas ponen **PNC** al inicio
    y otras el bloque **Resultado técnico bruto … Saldo** en las primeras columnas (como el PDF
    pág. ~24), dejando **PNC** al final o solo en el cuadro de primas. Se detecta el orden por
    encabezados y, si hace falta, por heurística sobre la primera fila de datos.
    Unidades: miles de Bs.
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

    layout = _resolve_cuadro1_layout(raw)

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

        if layout == "pnc_first":
            pnc = num(3)
            rt_b = num(4)
            reas = num(5)
            rt_n = num(6)
            gest = num(7)
            saldo = num(8)
        else:
            # Resultado técnico bruto… saldo en D–H; PNC en I si existe (misma hoja boletín).
            rt_b = num(3)
            reas = num(4)
            rt_n = num(5)
            gest = num(6)
            saldo = num(7)
            pnc = num(8)

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


def _alinear_pnc_y_corregir_columnas_mal_parseadas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza con la serie de **primas netas cobradas** (mismo criterio que el ranking ~pág. 10).

    El parse antiguo asumía «PNC en la primera columna numérica»; en muchas plantillas la primera
    columna es **resultado técnico bruto** y la PNC va al final o solo en el cuadro de primas.
    Si `pnc_miles_bs` del CSV no coincide con la serie de primas pero encaja ese desfase,
    reasigna RT bruto… saldo y fija PNC = primas del boletín.
    """
    try:
        prim = load_primas_mensual_largo()
    except FileNotFoundError:
        return df

    ref = prim[["fecha_periodo", "peer_id", "primas_miles_bs"]].rename(
        columns={"primas_miles_bs": "_pnc_boletin_primas"}
    )
    out = df.merge(ref, on=["fecha_periodo", "peer_id"], how="left")
    pr = out["_pnc_boletin_primas"]
    ps = out["pnc_miles_bs"]
    both = pr.notna() & ps.notna()
    den = pr.abs().replace(0, pd.NA)
    diff_rel = (ps - pr).abs() / den
    rel = both & (diff_rel <= 0.02).fillna(False)
    rel = rel | (both & (pr.abs() < 1e-9) & (ps.abs() < 1e-9))
    out.loc[rel, "pnc_miles_bs"] = out.loc[rel, "_pnc_boletin_primas"]

    need_fix = pr.notna() & ps.notna() & ~rel

    # Copias: las columnas de `out` son vistas; si no, al escribir rt_bruto se corrompen los valores
    # siguientes tomados del mismo bloque (mismo error que el parse antiguo).
    new_rt = ps.copy()
    new_re = out["rt_bruto_miles_bs"].copy()
    new_rn = out["reaseguro_cedido_miles_bs"].copy()
    new_g = out["rt_neto_miles_bs"].copy()
    new_sd = out["saldo_operaciones_miles_bs"].where(
        out["saldo_operaciones_miles_bs"].notna(),
        out["gestion_general_miles_bs"],
    ).copy()

    m = need_fix
    out.loc[m, "rt_bruto_miles_bs"] = new_rt[m]
    out.loc[m, "reaseguro_cedido_miles_bs"] = new_re[m]
    out.loc[m, "rt_neto_miles_bs"] = new_rn[m]
    out.loc[m, "gestion_general_miles_bs"] = new_g[m]
    out.loc[m, "saldo_operaciones_miles_bs"] = new_sd[m]
    out.loc[m, "pnc_miles_bs"] = pr[m]

    ok_pct = (
        out["pnc_miles_bs"].notna()
        & (out["pnc_miles_bs"].abs() > 1e-12)
        & out["saldo_operaciones_miles_bs"].notna()
    )
    out.loc[ok_pct, "pct_saldo_sobre_pnc"] = (
        100.0 * out.loc[ok_pct, "saldo_operaciones_miles_bs"] / out.loc[ok_pct, "pnc_miles_bs"]
    )

    return out.drop(columns=["_pnc_boletin_primas"], errors="ignore")


def load_resultado_tecnico_saldo() -> pd.DataFrame | None:
    path = DATA_PUBLIC / CSV_NAME
    if not path.exists():
        return None
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    df["fecha_periodo"] = pd.to_datetime(df["fecha_periodo"])
    return _alinear_pnc_y_corregir_columnas_mal_parseadas(df)


def top_n_para_infografia(sub: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return sub.head(n).copy()
