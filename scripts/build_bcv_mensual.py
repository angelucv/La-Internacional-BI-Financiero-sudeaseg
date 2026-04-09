"""
Construye `data/public/bcv_ves_por_usd_mensual.csv`: bolívares nominales por 1 USD (oficial BCV).

- Donde hay serie diaria pública (API de consulta no oficial que replica la tasa BCV), se usa el
  **último valor del mes**.
- Los meses sin API se rellenan por **interpolación log-lineal** entre **anclas mensuales** tomadas
  de referencias públicas (prensa / resúmenes de tasa BCV). Revise y sustituya por series propias
  si necesita precisión contable.

Ejecutar: python scripts/build_bcv_mensual.py
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "public" / "bcv_ves_por_usd_mensual.csv"

# Anclas (fecha fin de mes, VES por 1 USD). Ajuste según sus fuentes BCV.
ANCHORS: list[tuple[str, float]] = [
    ("2023-01-31", 20.5),
    ("2023-07-31", 28.0),
    ("2024-01-31", 36.0),
    ("2024-07-31", 44.0),
    ("2025-01-31", 52.0),
    ("2025-07-31", 95.0),
    ("2025-08-31", 148.444),
    ("2026-01-31", 295.0),
    ("2026-04-30", 475.0),
]


def _fetch_api_daily(start: str, end: str) -> pd.DataFrame:
    url = f"https://bcv-api.rafnixg.dev/rates/history?start_date={start}&end_date={end}"
    req = urllib.request.Request(url, headers={"User-Agent": "la-internacional-demo/1.1"})
    raw = urllib.request.urlopen(req, timeout=90).read()
    payload = json.loads(raw.decode())
    rows = payload.get("rates") or []
    if not rows:
        return pd.DataFrame(columns=["date", "ves_por_usd"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.rename(columns={"dollar": "ves_por_usd"})
    return df.sort_values("date")


def _month_end_last_rate(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame(columns=["year", "month", "fecha", "ves_por_usd", "fuente"])
    daily = daily.copy()
    daily["year"] = daily["date"].dt.year
    daily["month"] = daily["date"].dt.month
    out = (
        daily.groupby(["year", "month"], as_index=False)
        .agg(fecha=("date", "max"), ves_por_usd=("ves_por_usd", "last"))
    )
    out["fuente"] = "api_diaria_agrupada_mes"
    return out


def main() -> int:
    import numpy as np

    # Rango mensual alineado a primas (2023-01 … 2026-12)
    month_starts = pd.date_range("2023-01-01", "2026-12-01", freq="MS")
    month_ends = month_starts + pd.offsets.MonthEnd(0)

    ax_num = np.array([np.datetime64(pd.Timestamp(a[0]).to_datetime64()) for a in ANCHORS], dtype="datetime64[ns]")
    ay = np.array([math.log(a[1]) for a in ANCHORS], dtype=float)
    ts = month_ends.to_numpy(dtype="datetime64[ns]")
    y_log = np.interp(ts.astype("int64"), ax_num.astype("int64"), ay)
    series_interp = pd.Series(np.exp(y_log), index=month_starts)

    # API: ventana amplia (puede fallar en entornos sin red)
    api_daily = pd.DataFrame()
    try:
        api_daily = _fetch_api_daily(
            "2025-08-24",
            datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        )
    except Exception:
        pass
    api_m = _month_end_last_rate(api_daily)

    rows = []
    for ms, me in zip(month_starts, month_ends, strict=False):
        y, m = int(ms.year), int(ms.month)
        hit = api_m[(api_m["year"] == y) & (api_m["month"] == m)]
        if not hit.empty:
            ves = float(hit["ves_por_usd"].iloc[0])
            fuente = "bcv_api_diaria_ultimo_dia_mes"
        else:
            ves = float(series_interp.loc[ms])
            fuente = "interpolacion_log_anclas_publicas"
        rows.append(
            {
                "year": y,
                "month": m,
                "fecha_cierre_mes": me.strftime("%Y-%m-%d"),
                "ves_por_usd": ves,
                "fuente": fuente,
            }
        )

    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, sep=";", index=False, encoding="utf-8")
    print(f"Escrito {OUT} ({len(df)} filas).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
