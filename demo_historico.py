"""Series históricas de primas (SUDEASEG) y utilidades de comparación Top N vs La Internacional."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "public"


def empresa_peer_id(name: str) -> str:
    """Clave estable para enlazar la misma aseguradora entre años (nombres varían levemente)."""
    n = str(name).lower()
    n = re.sub(r"[,.]", " ", n)
    n = " ".join(n.split())
    n = n.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    if "internacional" in n and "seguros" in n:
        return "La Internacional"
    for brand in (
        "mercantil",
        "caracas",
        "piramide",
        "mapfre",
        "oceanica",
        "oceánica",
        "hispana",
        "constitucion",
        "banesco",
    ):
        if brand in n:
            return brand
    if "real" in n and "seguros" in n:
        return "real seguros"
    if "miranda" in n:
        return "miranda"
    if "piramide" in n or "pirámide" in name.lower():
        return "piramide"
    return n[:36]


def load_primas_mensual_largo() -> pd.DataFrame:
    path = DATA / "primas_netas_mensual_largo.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Falta {path}. Ejecute: python scripts/build_primas_historico.py"
        )
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    df["fecha_periodo"] = pd.to_datetime(df["fecha_periodo"])
    df["peer_id"] = df["empresa_raw"].map(empresa_peer_id)
    return df


def ultimo_periodo(df: pd.DataFrame) -> pd.Timestamp:
    return df["fecha_periodo"].max()


def top_peers_en_fecha(df: pd.DataFrame, fecha: pd.Timestamp, n: int = 5) -> list[str]:
    """IDs peer_id del top n por ranking en una fecha (solo empresas con ranking numérico)."""
    sub = df[df["fecha_periodo"] == fecha].copy()
    sub = sub[sub["ranking"].notna()].sort_values("ranking")
    seen: set[str] = set()
    out: list[str] = []
    for _, row in sub.iterrows():
        pid = row["peer_id"]
        if pid in seen:
            continue
        seen.add(pid)
        out.append(pid)
        if len(out) >= n:
            break
    return out


def conjunto_analisis(df: pd.DataFrame, n: int = 5) -> tuple[pd.Timestamp, list[str]]:
    """Fecha más reciente y lista de peer_id: top n en esa fecha, asegurando La Internacional."""
    ult = ultimo_periodo(df)
    top = top_peers_en_fecha(df, ult, n=n)
    if "La Internacional" not in top:
        top = top + ["La Internacional"]
    rank_map = (
        df[df["fecha_periodo"] == ult]
        .drop_duplicates("peer_id")
        .set_index("peer_id")["ranking"]
        .to_dict()
    )

    def sort_key(pid: str):
        r = rank_map.get(pid)
        return (r if r is not None else 999, pid)

    top_sorted = sorted(set(top), key=sort_key)
    return ult, top_sorted


def serie_peers(df: pd.DataFrame, peer_ids: list[str]) -> pd.DataFrame:
    """Serie larga filtrada a los peer_id indicados."""
    sub = df[df["peer_id"].isin(peer_ids)].copy()
    return sub.sort_values(["fecha_periodo", "peer_id"])


def acumulado_a_primas_mensuales(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte primas **acumuladas YTD** por año (como publica SUDEASEG) en **flujo mensual**:
    mes_n = acum_n - acum_{n-1}; enero = acum_enero.
    Así la serie no “cae” artificialmente cada enero al reiniciar el acumulado.
    """
    df = df.sort_values(["peer_id", "year", "month"]).copy()
    out: list[dict] = []
    for pid, g in df.groupby("peer_id", sort=False):
        for _y, gy in g.groupby("year", sort=True):
            gy = gy.sort_values("month")
            prev_acum = None
            for _, row in gy.iterrows():
                ac = row["primas_miles_bs"]
                if pd.isna(ac):
                    continue
                if prev_acum is None:
                    mes = float(ac)
                else:
                    mes = float(ac) - float(prev_acum)
                prev_acum = ac
                d = row.to_dict()
                d["primas_mes_miles"] = mes
                out.append(d)
    return pd.DataFrame(out)


def ultimo_periodo_en_ano(df: pd.DataFrame, year: int) -> pd.Timestamp | None:
    sub = df[df["year"] == year]
    if sub.empty:
        return None
    return pd.Timestamp(sub["fecha_periodo"].max())


def tabla_ranking_en_fecha(df: pd.DataFrame, fecha: pd.Timestamp) -> pd.DataFrame:
    """Ranking completo en una fecha (para armar Top 3, totales, etc.)."""
    sub = df[df["fecha_periodo"] == fecha].copy()
    sub = sub[sub["ranking"].notna()].sort_values("ranking")
    return sub


def primas_acumuladas_al_inicio_mes(
    df: pd.DataFrame, peer_id: str, fecha: pd.Timestamp
) -> float | None:
    """
    Acumulado de primas netas cobradas (miles Bs.) al inicio del mes de `fecha`:
    cierre del mes anterior en el mismo año; en enero, cierre de diciembre del año previo.
    Si no hay dato previo, 0.0 (inicio de serie).
    """
    y, m = int(fecha.year), int(fecha.month)
    g = df[df["peer_id"] == peer_id]
    if g.empty:
        return None
    if m > 1:
        prev = g[(g["year"] == y) & (g["month"] == m - 1)]
        if not prev.empty:
            return float(prev["primas_miles_bs"].iloc[0])
        return None
    prev_dec = g[(g["year"] == y - 1) & (g["month"] == 12)]
    if not prev_dec.empty:
        return float(prev_dec["primas_miles_bs"].iloc[0])
    return 0.0


def primas_acumuladas_al_inicio_mes(
    df: pd.DataFrame, peer_id: str, fecha: pd.Timestamp
) -> float | None:
    """
    Acumulado de primas netas cobradas (miles Bs.) **al inicio** del mes de corte:
    mismo valor que el acumulado YTD publicado al **cierre del mes anterior**.
    Enero → cierre de diciembre del año anterior (si existe en la serie); si no, 0.0.
    """
    y, m = int(fecha.year), int(fecha.month)
    g = df[df["peer_id"] == peer_id]
    if g.empty:
        return None
    if m > 1:
        prev = g[(g["year"] == y) & (g["month"] == m - 1)]
        if not prev.empty:
            return float(prev["primas_miles_bs"].iloc[0])
        return None
    prev_dec = g[(g["year"] == y - 1) & (g["month"] == 12)]
    if not prev_dec.empty:
        return float(prev_dec["primas_miles_bs"].iloc[0])
    return 0.0


def variacion_interanual_diciembre(df: pd.DataFrame, peer_ids: list[str]) -> pd.DataFrame:
    """Variación % Dic vs Dic para cada año disponible (requiere mes 12 en ambos años)."""
    d = df[df["month"] == 12].copy()
    if d.empty:
        return pd.DataFrame()
    piv = d.pivot_table(
        index="peer_id",
        columns="year",
        values="primas_miles_bs",
        aggfunc="first",
    )
    years = sorted(piv.columns)
    rows = []
    for a, b in zip(years, years[1:]):
        col = f"{a}->{b}"
        for pid in peer_ids:
            if pid not in piv.index:
                continue
            va, vb = piv.loc[pid, a], piv.loc[pid, b]
            if pd.isna(va) or pd.isna(vb) or va == 0:
                continue
            pct = 100.0 * (vb - va) / va
            rows.append(
                {
                    "peer_id": pid,
                    "periodo": col,
                    "variacion_pct": pct,
                    "primas_desde": va,
                    "primas_hasta": vb,
                }
            )
    return pd.DataFrame(rows)


def etiqueta_display(df: pd.DataFrame, peer_id: str) -> str:
    """Nombre corto legible (última aparición)."""
    sub = df[df["peer_id"] == peer_id].sort_values("fecha_periodo")
    if sub.empty:
        return peer_id
    raw = str(sub.iloc[-1]["empresa_raw"])
    raw = " ".join(raw.split())
    if peer_id == "La Internacional":
        return "La Internacional"
    if len(raw) > 42:
        return raw[:39] + "…"
    return raw
