"""Visualización: Resultado técnico / Saldo de operaciones + PNC (Boletín en cifras)."""
from __future__ import annotations

import math
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from boletin_cuadro_resultados import top_n_para_infografia
from demo_boletin_tabla import fmt_miles_bs_es, fmt_pct_es
from demo_config import COLOR_BRAND_NAVY, color_linea_peer, plotly_brand_theme
from demo_historico import etiqueta_display, tabla_ranking_en_fecha


def pick_corte_resultado(df_in: pd.DataFrame, fech_objetivo: pd.Timestamp) -> tuple[pd.DataFrame, str]:
    """
    Selecciona el corte mensual más cercano al de primas: mismo año/mes si existe;
    si no, el último corte con fecha_periodo <= objetivo; si no, el más reciente en la serie.
    """
    df = df_in.copy()
    y, m = int(fech_objetivo.year), int(fech_objetivo.month)
    sub = df[(df["year"] == y) & (df["month"] == m)].copy()
    if not sub.empty:
        lab = f"{y}-{m:02d} (cuadro 1 boletín)"
        return sub.sort_values("ranking"), lab
    fo = pd.Timestamp(fech_objetivo).normalize()
    cand = df[df["fecha_periodo"] <= fo]
    if not cand.empty:
        last = cand["fecha_periodo"].max()
        sub = df[df["fecha_periodo"] == last].sort_values("ranking")
        lab = f"{pd.Timestamp(last).strftime('%Y-%m')} (último corte ≤ fecha primas)"
        return sub, lab
    last = df["fecha_periodo"].max()
    sub = df[df["fecha_periodo"] == last].sort_values("ranking")
    lab = f"{pd.Timestamp(last).strftime('%Y-%m')} (más reciente en datos)"
    return sub, lab


def _etiqueta_corta(name: str) -> str:
    s = " ".join(str(name).split())
    return s[:28] + "…" if len(s) > 28 else s


_MESES_ABR = (
    None,
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
)


def _label_opcion_corte(ts) -> str:
    t = pd.Timestamp(ts)
    return f"{_MESES_ABR[t.month]} {t.year} · {t.strftime('%Y-%m-%d')}"


DASHBOARD_RESULTADO_TOP_N = 5


def _ranking_pnc_boletin_en_fecha(df_primas: pd.DataFrame, fecha: pd.Timestamp) -> pd.DataFrame:
    """
    Ranking por primas netas cobradas (PNC) como en la infografía del boletín (~pág. 10):
    mismo criterio que `tabla_ranking_en_fecha`. Si no hay fila exacta, última fecha ≤ corte.
    """
    ft = pd.Timestamp(fecha).normalize()
    rank = tabla_ranking_en_fecha(df_primas, ft)
    if not rank.empty:
        return rank
    le = df_primas[df_primas["fecha_periodo"].notna()]
    le = le[le["fecha_periodo"] <= ft]
    if le.empty:
        return pd.DataFrame()
    ft2 = le["fecha_periodo"].max()
    return tabla_ranking_en_fecha(df_primas, ft2)


def _cuadro_top_n_por_ranking_pnc_boletin(
    sub_cuadro: pd.DataFrame,
    df_primas: pd.DataFrame,
    fecha_corte: pd.Timestamp,
    n: int,
) -> tuple[pd.DataFrame, str]:
    """
    De las ~10 primeras empresas por PNC del boletín, toma las n primeras posiciones (1..n)
    y devuelve las filas del cuadro de resultados en ese orden (no el orden del Excel del cuadro 1).
    """
    rank = _ranking_pnc_boletin_en_fecha(df_primas, fecha_corte)
    if rank.empty:
        s = sub_cuadro[sub_cuadro["pnc_miles_bs"].notna()].copy()
        s = s.sort_values("pnc_miles_bs", ascending=False).head(n)
        s = s.copy()
        s["ranking_boletin"] = range(1, len(s) + 1)
        return s, (
            "No hay serie de primas en esa fecha: se ordenó por **PNC del cuadro 1** (descendente)."
        )

    cols_r = ["ranking", "peer_id", "empresa_raw", "primas_miles_bs"]
    rtop = rank.sort_values("ranking").head(n)[cols_r].rename(
        columns={
            "ranking": "ranking_boletin",
            "empresa_raw": "_nom_primas",
            "primas_miles_bs": "_pnc_ranking_prim",
        }
    )
    disp = rtop.merge(sub_cuadro, on="peer_id", how="left")
    disp["empresa_raw"] = disp["empresa_raw"].fillna(disp["_nom_primas"])
    # Sin fila del cuadro 1: PNC = primas del ranking (~pág. 10); si hay cuadro, prevalece (tras corrección en carga).
    if "pnc_miles_bs" in disp.columns:
        disp["pnc_miles_bs"] = disp["pnc_miles_bs"].fillna(disp["_pnc_ranking_prim"])
    else:
        disp["pnc_miles_bs"] = disp["_pnc_ranking_prim"]
    disp = disp.drop(columns=["_nom_primas", "_pnc_ranking_prim"], errors="ignore")
    fcuadro = pd.Timestamp(fecha_corte).normalize()
    fprim = pd.Timestamp(rank["fecha_periodo"].iloc[0]).normalize()
    note = (
        f"Orden **#1–#{n}** = las **{n} primeras posiciones del ranking por PNC** del boletín (infografía ~pág. 10). "
        f"Serie de primas: **{fprim.strftime('%Y-%m-%d')}**."
    )
    if fprim != fcuadro:
        note += f" *(fecha de primas distinta al corte del cuadro {fcuadro.strftime('%Y-%m-%d')}; se usa la última serie ≤ corte.)*"
    return disp, note


def fig_infografia_top_saldo_pnc(
    disp_top: pd.DataFrame,
    df_etiquetas: pd.DataFrame,
    *,
    n: int = DASHBOARD_RESULTADO_TOP_N,
    height: int = 420,
) -> go.Figure:
    """Barras horizontales: % saldo sobre PNC (filas ya en orden boletín PNC)."""
    t10 = top_n_para_infografia(disp_top, min(n, len(disp_top)))
    t10 = t10.iloc[::-1].reset_index(drop=True)
    labels = []
    for _, r in t10.iterrows():
        rb = r.get("ranking_boletin", r.get("ranking"))
        rk = int(rb) if pd.notna(rb) else 0
        pid = str(r["peer_id"]) if pd.notna(r.get("peer_id")) else ""
        labels.append(f"{rk} · {_etiqueta_corta(etiqueta_display(df_etiquetas, pid))}")
    xs = []
    for _, r in t10.iterrows():
        v = r["pct_saldo_sobre_pnc"]
        xs.append(float(v) if v is not None and not (isinstance(v, float) and math.isnan(v)) else 0.0)
    colors = []
    for i, (_, r) in enumerate(t10.iterrows()):
        pid = str(r["peer_id"])
        rb = r.get("ranking_boletin", r.get("ranking"))
        j = int(rb) - 1 if pd.notna(rb) else i
        colors.append(color_linea_peer(pid, j % 8))
    fig = go.Figure(
        go.Bar(
            x=xs,
            y=labels,
            orientation="h",
            marker=dict(color=colors, line=dict(width=[3.0 if str(r["peer_id"]) == "La Internacional" else 1.0 for _, r in t10.iterrows()], color=COLOR_BRAND_NAVY)),
            text=[fmt_pct_es(x) + " %" for x in xs],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>% saldo / PNC: %{x:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        **plotly_brand_theme(height=height, margin=dict(t=56, b=48, l=8, r=120)),
        title=dict(
            text=f"<b>Top {n} — % Saldo de operaciones sobre PNC</b><br>"
            "<sup>Mismo Top 5 por PNC que la infografía del boletín (~pág. 10); importes del cuadro 1 (~pág. 24)</sup>",
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="% (Saldo de operaciones / PNC)",
        yaxis_title="",
        showlegend=False,
    )
    fig.update_xaxes(zeroline=True, zerolinewidth=1, zerolinecolor="rgba(39,48,110,0.35)")
    return fig


def render_seccion_resultado_tecnico_saldo(
    st_module: Any,
    df_res: pd.DataFrame,
    df_primas_largo: pd.DataFrame,
    fech_ref: pd.Timestamp,
    *,
    selectbox_key: str = "corte_cuadro_resultado_boletin",
    show_inner_heading: bool = True,
) -> None:
    sub_sugerido, etiqueta_sugerida = pick_corte_resultado(df_res, pd.Timestamp(fech_ref))
    fechas_cuadro = set(pd.to_datetime(df_res["fecha_periodo"]).drop_duplicates().unique())
    fechas_primas = set(pd.to_datetime(df_primas_largo["fecha_periodo"]).drop_duplicates().unique())
    fechas_unicas = sorted(fechas_cuadro | fechas_primas, reverse=True)
    default_ts = (
        pd.Timestamp(sub_sugerido["fecha_periodo"].iloc[0])
        if not sub_sugerido.empty
        else pd.Timestamp(fechas_unicas[0])
    )
    opciones_map = {_label_opcion_corte(f): f for f in fechas_unicas}
    labels = list(opciones_map.keys())
    default_lbl = _label_opcion_corte(default_ts)
    idx0 = labels.index(default_lbl) if default_lbl in labels else 0
    elegido = st_module.selectbox(
        "Corte del cuadro de resultados (1 Cuadro de Resultados)",
        options=labels,
        index=idx0,
        help=(
            "Por defecto se alinea al último cierre de primas de la página. "
            "Elija otro mes para comparar (p. ej. dic. 2025)."
        ),
        key=selectbox_key,
    )
    ts_elegido = pd.Timestamp(opciones_map[elegido])
    sub = df_res[df_res["fecha_periodo"] == ts_elegido]
    etiqueta_corte = f"{ts_elegido.strftime('%Y-%m')} (cuadro 1 boletín)"
    if default_lbl != elegido:
        etiqueta_corte += f" · sugerido según primas: {etiqueta_sugerida}"

    disp, nota_rank = _cuadro_top_n_por_ranking_pnc_boletin(
        sub,
        df_primas_largo,
        ts_elegido,
        DASHBOARD_RESULTADO_TOP_N,
    )
    _m_pct = (
        disp["saldo_operaciones_miles_bs"].notna()
        & disp["pnc_miles_bs"].notna()
        & (disp["pnc_miles_bs"].abs() > 1e-12)
    )
    disp.loc[_m_pct, "pct_saldo_sobre_pnc"] = (
        100.0
        * disp.loc[_m_pct, "saldo_operaciones_miles_bs"]
        / disp.loc[_m_pct, "pnc_miles_bs"]
    )

    if show_inner_heading:
        st_module.markdown("#### Resultado técnico / Saldo de operaciones (Boletín en cifras)")
    st_module.caption(
        f"Corte cuadro: **{etiqueta_corte}**. "
        f"{nota_rank} "
        "Columnas del PDF (~pág. 24): resultado técnico bruto, reaseguro cedido, RT neto, gestión general, saldo de operaciones; "
        "más **PNC** y **% Saldo / PNC** (dos decimales; **% = 100 × Saldo / PNC**). "
        f"Solo **Top {DASHBOARD_RESULTADO_TOP_N}** por PNC (~pág. 10). "
        "Si aún no hay Excel del cuadro 1 para ese mes, el ranking y la PNC salen de primas; el resto de columnas queda vacío hasta importar el archivo."
    )
    fig = fig_infografia_top_saldo_pnc(disp, df_primas_largo, n=DASHBOARD_RESULTADO_TOP_N)
    st_module.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    disp = disp.copy()
    disp["Empresa"] = disp["empresa_raw"]
    disp["Resultado técnico bruto"] = disp["rt_bruto_miles_bs"]
    disp["Resultado reaseguro cedido"] = disp["reaseguro_cedido_miles_bs"]
    disp["Resultado técnico neto"] = disp["rt_neto_miles_bs"]
    disp["Resultado gestión gral."] = disp["gestion_general_miles_bs"]
    disp["Saldo de operaciones"] = disp["saldo_operaciones_miles_bs"]
    disp["PNC (miles Bs.)"] = disp["pnc_miles_bs"]
    disp["% Saldo / PNC"] = disp["pct_saldo_sobre_pnc"]
    show_cols = [
        "ranking_boletin",
        "Empresa",
        "Resultado técnico bruto",
        "Resultado reaseguro cedido",
        "Resultado técnico neto",
        "Resultado gestión gral.",
        "Saldo de operaciones",
        "PNC (miles Bs.)",
        "% Saldo / PNC",
    ]
    if "ranking_boletin" not in disp.columns:
        disp["ranking_boletin"] = range(1, len(disp) + 1)
    tab = disp[show_cols].copy()
    tab = tab.rename(columns={"ranking_boletin": "# PNC boletín"})
    if disp["saldo_operaciones_miles_bs"].isna().all() and not disp.empty:
        st_module.warning(
            "No hay filas del **1 Cuadro de Resultados** para esta fecha en los datos cargados. "
            "Se muestra el Top 5 por **PNC** (primas) y columnas de resultado técnico vacías. "
            "Coloque el Excel oficial en `data/raw/xlsx/` y ejecute `python scripts/build_resultado_cuadro_boletin.py --merge`."
        )
    for col in (
        "Resultado técnico bruto",
        "Resultado reaseguro cedido",
        "Resultado técnico neto",
        "Resultado gestión gral.",
        "Saldo de operaciones",
        "PNC (miles Bs.)",
    ):
        tab[col] = tab[col].map(lambda x: fmt_miles_bs_es(float(x)) if pd.notna(x) else "—")
    tab["% Saldo / PNC"] = tab["% Saldo / PNC"].map(
        lambda x: fmt_pct_es(float(x)) if pd.notna(x) else "—"
    )
    st_module.dataframe(
        tab,
        use_container_width=True,
        hide_index=True,
        height=min(520, 42 * (len(tab) + 2)),
    )


def render_sin_datos_resultado(st_module: Any) -> None:
    st_module.info(
        "No hay datos del cuadro «Resultado técnico / Saldo de operaciones». "
        "Coloque los Excel **1 Cuadro de Resultados** del boletín en `data/raw/xlsx/` y ejecute: "
        "`python scripts/build_resultado_cuadro_boletin.py`"
    )
