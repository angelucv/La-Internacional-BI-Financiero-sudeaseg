"""Carga CSV locales del demo (sin Supabase)."""
from pathlib import Path

import pandas as pd

from demo_historico import empresa_peer_id

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "public"


def _read_csv(name: str) -> pd.DataFrame:
    path = DATA / name
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, sep=";", encoding="utf-8")


def load_primas_31a() -> pd.DataFrame:
    df = _read_csv("cuadro_31A_primas_netas_cobradas_2023_vs_2022.csv")
    for c in ("PRIMAS_2022", "PRIMAS_2023", "CRECIMIENTO_PORC"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["NOMBRE_EMPRESA"].astype(str).str.upper() != "TOTAL"].copy()
    return df


def load_indicadores_29() -> pd.DataFrame:
    df = _read_csv("cuadro_29_indicadores_financieros_2023_por_empresa.csv")
    skip = df["NOMBRE_EMPRESA"].astype(str).str.contains(
        "Valor del Mercado", case=False, na=False
    )
    df = df[~skip].copy()
    num_cols = [c for c in df.columns if c != "NOMBRE_EMPRESA"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def load_indices_boletin() -> pd.DataFrame:
    """Índices mensuales tipo Boletín en cifras (SUDEASEG). Ver `scripts/build_indices_por_empresa.py`."""
    path = DATA / "indices_por_empresa_mes_actual.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Falta {path}. Ejecute: python scripts/build_indices_por_empresa.py"
        )
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    num_cols = [
        c
        for c in df.columns
        if c not in ("NOMBRE_EMPRESA", "year", "month", "archivo_fuente")
    ]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["peer_id"] = df["NOMBRE_EMPRESA"].map(empresa_peer_id)
    return df


def load_indices_historico() -> pd.DataFrame:
    """Serie larga de índices por empresa y mes (varias hojas del mismo Excel SUDEASEG)."""
    path = DATA / "indices_por_empresa_historico_largo.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Falta {path}. Ejecute: python scripts/build_indices_por_empresa.py"
        )
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    num_cols = [
        c
        for c in df.columns
        if c not in ("NOMBRE_EMPRESA", "year", "month", "archivo_fuente", "hoja")
    ]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["peer_id"] = df["NOMBRE_EMPRESA"].map(empresa_peer_id)
    return df
