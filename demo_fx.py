"""Tipo de cambio oficial BCV (serie mensual) y conversión a USD para series de primas SUDEASEG."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "public"


def load_bcv_mensual() -> pd.DataFrame:
    path = DATA / "bcv_ves_por_usd_mensual.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Falta {path}. Ejecute: python scripts/build_bcv_mensual.py"
        )
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    return df


def merge_tipo_cambio(df: pd.DataFrame, tc: pd.DataFrame | None = None) -> pd.DataFrame:
    """Une `ves_por_usd` (Bs. nominales por 1 USD) por año-mes."""
    if tc is None:
        tc = load_bcv_mensual()
    out = df.merge(
        tc[["year", "month", "ves_por_usd", "fuente"]],
        on=["year", "month"],
        how="left",
    )
    return out


def primas_miles_bs_a_usd_millones(primas_miles_bs: pd.Series, ves: pd.Series) -> pd.Series:
    """
    SUDEASEG expresa cifras en «miles de Bs.» → Bs nominales = miles * 1000.
    Millones USD = Bs / VES_per_USD / 1e6.
    """
    bs = pd.to_numeric(primas_miles_bs, errors="coerce") * 1000.0
    v = pd.to_numeric(ves, errors="coerce")
    return bs / v / 1_000_000.0


def agregar_usd_mensual(df_mensual: pd.DataFrame) -> pd.DataFrame:
    """Espera columnas primas_mes_miles (o primas_miles_bs mensual) y ves_por_usd."""
    d = df_mensual.copy()
    if "primas_mes_miles" in d.columns:
        d["primas_mes_millones_usd"] = primas_miles_bs_a_usd_millones(d["primas_mes_miles"], d["ves_por_usd"])
    return d


def ytd_usd_suma_mensual(
    df_mensual_usd: pd.DataFrame,
    peer_id: str,
    ult_fecha: pd.Timestamp,
) -> float:
    """Suma de flujos mensuales en millones USD desde enero hasta ult_fecha (mismo año)."""
    y = ult_fecha.year
    sub = df_mensual_usd[
        (df_mensual_usd["peer_id"] == peer_id)
        & (df_mensual_usd["year"] == y)
        & (df_mensual_usd["fecha_periodo"] <= ult_fecha)
    ]
    if sub.empty or "primas_mes_millones_usd" not in sub.columns:
        return float("nan")
    return float(sub["primas_mes_millones_usd"].sum())


def mercado_ytd_millones_usd_total(
    df_largo: pd.DataFrame,
    tc: pd.DataFrame,
    ult_fecha: pd.Timestamp,
) -> float:
    """Suma del YTD en millones USD de todas las empresas del cuadro en el cierre (suma de partes)."""
    import math

    ult_fecha = pd.Timestamp(ult_fecha)
    row = df_largo[df_largo["fecha_periodo"] == ult_fecha]
    if row.empty:
        return float("nan")
    total = 0.0
    for pid in row["peer_id"].unique():
        v = ytd_millones_usd_desde_serie_mensual(df_largo, tc, str(pid), ult_fecha)
        if isinstance(v, (int, float)) and math.isfinite(v):
            total += float(v)
    return total


def serie_mensual_millones_usd(
    df_largo: pd.DataFrame,
    tc: pd.DataFrame,
    peer_id: str,
    year: int,
) -> pd.DataFrame:
    """Flujo mensual en millones USD (tipo BCV de cada mes) para un peer y un año."""
    from demo_historico import acumulado_a_primas_mensuales, serie_peers

    s = serie_peers(df_largo, [peer_id])
    if s.empty:
        return pd.DataFrame()
    sm = acumulado_a_primas_mensuales(s)
    sm = merge_tipo_cambio(sm, tc)
    sm = agregar_usd_mensual(sm)
    sub = sm[(sm["year"] == year) & (sm["peer_id"] == peer_id)].sort_values("month")
    if sub.empty or "primas_mes_millones_usd" not in sub.columns:
        return pd.DataFrame()
    return sub[
        ["year", "month", "fecha_periodo", "peer_id", "primas_mes_millones_usd"]
    ].copy()


def ytd_millones_usd_desde_serie_mensual(
    df_largo: pd.DataFrame,
    tc: pd.DataFrame,
    peer_id: str,
    ult_fecha: pd.Timestamp,
) -> float:
    """YTD en millones USD (suma de flujos mensuales al tipo de cada mes) a partir de la serie larga."""
    from demo_historico import acumulado_a_primas_mensuales, serie_peers

    s = serie_peers(df_largo, [peer_id])
    if s.empty:
        return float("nan")
    sm = acumulado_a_primas_mensuales(s)
    sm = merge_tipo_cambio(sm, tc)
    sm = agregar_usd_mensual(sm)
    return ytd_usd_suma_mensual(sm, peer_id, ult_fecha)
