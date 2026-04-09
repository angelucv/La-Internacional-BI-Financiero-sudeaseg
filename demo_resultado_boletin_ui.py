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
from demo_historico import etiqueta_display


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


def fig_infografia_top10_saldo_pnc(
    sub: pd.DataFrame,
    df_etiquetas: pd.DataFrame,
    *,
    height: int = 520,
) -> go.Figure:
    """Barras horizontales tipo boletín: % saldo sobre PNC (Top 10 por ranking)."""
    t10 = top_n_para_infografia(sub, 10)
    t10 = t10.iloc[::-1].reset_index(drop=True)
    labels = [
        f"{int(r['ranking'])} · {_etiqueta_corta(etiqueta_display(df_etiquetas, r['peer_id']))}"
        for _, r in t10.iterrows()
    ]
    xs = []
    for _, r in t10.iterrows():
        v = r["pct_saldo_sobre_pnc"]
        xs.append(float(v) if v is not None and not (isinstance(v, float) and math.isnan(v)) else 0.0)
    colors = []
    for i, (_, r) in enumerate(t10.iterrows()):
        pid = str(r["peer_id"])
        j = int(r["ranking"]) - 1 if pd.notna(r["ranking"]) else i
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
            text="<b>Top 10 — % Saldo de operaciones sobre PNC</b><br>"
            "<sup>PNC = Primas netas cobradas (miles Bs.) · Mismo cuadro oficial del boletín</sup>",
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
) -> None:
    sub, etiqueta_corte = pick_corte_resultado(df_res, pd.Timestamp(fech_ref))
    st_module.markdown("#### Resultado técnico / Saldo de operaciones (Boletín en cifras)")
    st_module.caption(
        f"Corte mostrado: **{etiqueta_corte}**. "
        "PNC = primas netas cobradas (miles Bs.). "
        "% = 100 × Saldo de operaciones / PNC. "
        "Fuente: cuadro 1 oficial (misma información que el PDF del boletín mensual)."
    )
    fig = fig_infografia_top10_saldo_pnc(sub, df_primas_largo)
    st_module.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    disp = sub.head(15).copy()
    disp["Empresa"] = disp["empresa_raw"]
    disp["PNC (miles Bs.)"] = disp["pnc_miles_bs"]
    disp["RT bruto"] = disp["rt_bruto_miles_bs"]
    disp["Reaseguro cedido"] = disp["reaseguro_cedido_miles_bs"]
    disp["RT neto"] = disp["rt_neto_miles_bs"]
    disp["Gestión gral."] = disp["gestion_general_miles_bs"]
    disp["Saldo operaciones"] = disp["saldo_operaciones_miles_bs"]
    disp["% Saldo / PNC"] = disp["pct_saldo_sobre_pnc"]
    show_cols = [
        "ranking",
        "Empresa",
        "PNC (miles Bs.)",
        "RT bruto",
        "Reaseguro cedido",
        "RT neto",
        "Gestión gral.",
        "Saldo operaciones",
        "% Saldo / PNC",
    ]
    tab = disp[show_cols].copy()
    for col in (
        "PNC (miles Bs.)",
        "RT bruto",
        "Reaseguro cedido",
        "RT neto",
        "Gestión gral.",
        "Saldo operaciones",
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
