import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from demo_boletin_tabla import render_cuadro_boletin_ranking
from demo_config import (
    APP_NAME_SHORT,
    COLOR_BRAND_GOLD,
    COLOR_BRAND_NAVY,
    DATA_YEAR,
    color_linea_peer,
    plotly_brand_theme,
    render_brand_header,
    render_demo_sidebar,
)
from demo_data import load_indicadores_29, load_indices_boletin, load_indices_historico
from demo_fx import (
    load_bcv_mensual,
    mercado_ytd_millones_usd_total,
    serie_mensual_millones_usd,
    ytd_millones_usd_desde_serie_mensual,
)
from demo_historico import (
    empresa_peer_id,
    etiqueta_display,
    load_primas_mensual_largo,
    tabla_ranking_en_fecha,
    ultimo_periodo_en_ano,
)

MESES_NOMBRE = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

INDICES_METRICAS: list[tuple[str, str]] = [
    ("SINI_PAG_VS_PRIM_PCT", "Siniestros pagados / primas netas (1)"),
    ("RESERVAS_VS_PRIM_PCT", "Reservas técnicas / primas netas (2)"),
    ("SINI_INC_VS_PRIM_DEV_PCT", "Siniestros incurridos / prima devengada (3)"),
    ("COMISION_VS_PRIM_PCT", "Comisiones / primas netas (4)"),
    ("GAST_ADQ_VS_PRIM_PCT", "Gastos adquisición / primas netas (5)"),
    ("GAST_ADM_VS_PRIM_PCT", "Gastos administración / primas netas (6)"),
    ("COSTO_REAS_VS_PRIM_DEV_PCT", "Costo reaseguro / prima devengada (7)"),
    ("TASA_COMBINADA_PCT", "Tasa combinada (8)"),
    ("INDICE_COB_RESERVAS", "Índice cobertura reservas (9)"),
]

# Títulos breves para rejillas (evitan solaparse)
INDICES_SUBPLOT_TITLES: list[str] = [
    "(1) Siniestros pag./primas",
    "(2) Reservas/primas",
    "(3) Siniestros inc./prima dev.",
    "(4) Comisiones/primas",
    "(5) Gastos adq./primas",
    "(6) Gastos adm./primas",
    "(7) Reaseguro/prima dev.",
    "(8) Tasa combinada",
    "(9) Cobertura reservas",
]


def _etiqueta_barra_corta(dfm: pd.DataFrame, peer_id: str) -> str:
    """Etiqueta corta para eje X (legible en móvil y pantalla ancha)."""
    if peer_id == "La Internacional":
        return "La Internacional"
    if peer_id == "mercantil":
        return "Mercantil"
    if peer_id == "caracas":
        return "Caracas"
    s = etiqueta_display(dfm, peer_id)
    s = " ".join(s.split())
    return s[:18] + "…" if len(s) > 18 else s


def _fig_indicador_top3(
    col_code: str,
    title_short: str,
    idx: pd.DataFrame,
    top3: pd.DataFrame,
    dfm: pd.DataFrame,
    iy: int,
    im: int,
) -> go.Figure:
    """Barras verticales por indicador; borde más marcado en La Internacional."""
    names: list[str] = []
    pids: list[str] = []
    vals: list[float] = []
    colors: list[str] = []
    for j, (_, r) in enumerate(top3.iterrows()):
        pid = str(r["peer_id"])
        sub = idx[(idx["peer_id"] == pid) & (idx["year"] == iy) & (idx["month"] == im)]
        if sub.empty:
            continue
        row = sub.iloc[0]
        v = row[col_code] if col_code in row.index else float("nan")
        v = float(v) if pd.notna(v) else 0.0
        names.append(_etiqueta_barra_corta(dfm, pid))
        pids.append(pid)
        vals.append(v)
        colors.append(color_linea_peer(pid, j))
    line_w = [3.2 if p == "La Internacional" else 1.2 for p in pids]
    line_c = ["#B8860B" if p == "La Internacional" else "white" for p in pids]
    fig = go.Figure(
        go.Bar(
            x=names,
            y=vals,
            marker=dict(
                color=colors,
                line=dict(width=line_w, color=line_c),
                opacity=0.94,
            ),
            text=[f"{v:,.2f}" for v in vals],
            textposition="outside",
            textfont=dict(size=10, color=COLOR_BRAND_NAVY),
            cliponaxis=False,
            hovertemplate="%{x}<br>%{y:,.4f}<extra></extra>",
        )
    )
    fig.update_layout(
        **plotly_brand_theme(height=300, margin=dict(t=52, b=72, l=44, r=20)),
        title=dict(
            text=f"<b>{title_short}</b>",
            x=0.5,
            xanchor="center",
            font=dict(size=12),
        ),
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
        bargap=0.28,
    )
    fig.update_xaxes(tickangle=-28, automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def _fig_pie_participacion(
    dfm: pd.DataFrame,
    top3: pd.DataFrame,
    fech26: pd.Timestamp,
    total_mercado_usd: float,
    anio_curso: int,
    tc_df: pd.DataFrame,
    *,
    chart_height: int = 460,
) -> go.Figure:
    """Donut Top 3 + resto; resalta La Internacional."""
    pie_labels: list[str] = []
    pie_vals: list[float] = []
    pie_colors: list[str] = []
    pie_pids: list[str] = []
    sum_top3 = 0.0
    for i, (_, r) in enumerate(top3.iterrows()):
        pid = str(r["peer_id"])
        usd = ytd_millones_usd_desde_serie_mensual(dfm, tc_df, pid, pd.Timestamp(fech26))
        if usd != usd:
            usd = 0.0
        sum_top3 += usd
        short = etiqueta_display(dfm, pid)
        pie_labels.append(short if len(short) <= 40 else short[:37] + "…")
        pie_vals.append(usd)
        pie_colors.append(color_linea_peer(pid, i))
        pie_pids.append(pid)
    resto_usd = (
        max(0.0, float(total_mercado_usd) - sum_top3) if total_mercado_usd == total_mercado_usd else 0.0
    )
    pie_labels.append("Resto del mercado")
    pie_vals.append(resto_usd)
    pie_colors.append("#B8BCC8")
    pie_pids.append("_resto")

    n_slices = len(pie_vals)
    pull_list = [
        (0.16 if pie_pids[i] == "La Internacional" else 0.0) for i in range(n_slices)
    ]
    line_widths = [
        (4.0 if pie_pids[i] == "La Internacional" else 1.5) for i in range(n_slices)
    ]
    line_colors = [
        (
            "#C9A000"
            if pie_pids[i] == "La Internacional"
            else ("#E2E6EE" if pie_pids[i] == "_resto" else "white")
        )
        for i in range(n_slices)
    ]

    fig_pie = go.Figure(
        go.Pie(
            labels=pie_labels,
            values=pie_vals,
            hole=0.52,
            pull=pull_list,
            sort=False,
            rotation=32,
            domain=dict(x=[0.02, 0.98], y=[0.06, 0.98]),
            marker=dict(
                colors=pie_colors,
                line=dict(width=line_widths, color=line_colors),
            ),
            textinfo="label+percent",
            textposition="outside",
            textfont=dict(size=11, color=COLOR_BRAND_NAVY),
            hovertemplate="%{label}<br>%{value:,.2f} M USD<br>%{percent}<extra></extra>",
            insidetextorientation="radial",
        )
    )
    fig_pie.update_layout(
        **plotly_brand_theme(
            height=chart_height,
            margin=dict(t=48, b=72, l=8, r=8),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.02,
                x=0.5,
                xanchor="center",
            ),
        ),
        title=dict(
            text=f"<b>Participación YTD {anio_curso}</b> · millones USD<br>"
            f"<sup>Cierre {fech26.strftime('%Y-%m')}</sup>",
            x=0.5,
            xanchor="center",
        ),
        showlegend=False,
    )
    if "La Internacional" in pie_pids:
        fig_pie.add_annotation(
            text=f"<span style='color:{COLOR_BRAND_GOLD}'>★</span> "
            "<b>La Internacional</b> — resaltada",
            xref="paper",
            yref="paper",
            x=0.5,
            y=-0.05,
            showarrow=False,
            font=dict(size=11, color=COLOR_BRAND_NAVY),
        )
    return fig_pie


def _sector_promedio_boletin(
    idx: pd.DataFrame, iy: int, im: int, col: str
) -> float | None:
    """Media simple del indicador en el corte (todas las empresas con dato)."""
    sub = idx[(idx["year"] == iy) & (idx["month"] == im)]
    if col not in sub.columns:
        return None
    s = pd.to_numeric(sub[col], errors="coerce").dropna()
    if s.empty:
        return None
    return float(s.mean())


def _tacometro_axis_max(
    valor_empresa: float, promedio_sector: float | None, piso: float
) -> float:
    cand = max(piso, valor_empresa * 1.22)
    if promedio_sector is not None and promedio_sector == promedio_sector:
        cand = max(cand, float(promedio_sector) * 1.22)
    step = 5 if cand <= 45 else 10 if cand <= 120 else 15
    return float(math.ceil(max(cand, 8.0) / step) * step)


def _titulo_tacometro_multilinea(titulo: str) -> tuple[str, int]:
    """
    Títulos en 2 líneas (<br>) y tamaño acorde para que no se recorten en columnas estrechas.
    Plotly admite <br> en el texto del indicador.
    """
    t = titulo.strip()
    if t == "Siniestralidad (pag./primas)":
        return "Siniestralidad<br>(pag. / primas)", 17
    if t == "Gastos administración":
        return "Gastos<br>administración", 17
    if t == "Gastos de adquisición":
        return "Gastos de<br>adquisición", 17
    if t == "Comisiones":
        return "Comisiones", 18
    if len(t) > 16 and " " in t:
        i = t.rfind(" ", 0, min(len(t), 18))
        if i > 0:
            return f"{t[:i]}<br>{t[i + 1 :]}", 16
    return t, 17


def _fig_tacometro_vs_sector(
    titulo: str,
    valor_empresa: float | None,
    promedio_sector: float | None,
    *,
    piso_escala: float,
    color_aguja: str,
) -> go.Figure:
    """
    Tacómetro: aguja = La Internacional; banda gruesa en el arco = promedio del sector.
    Fondo del arco en un solo tono neutro (sin franjas multicolor).
    """
    ve = (
        float(valor_empresa)
        if valor_empresa is not None
        and not (isinstance(valor_empresa, float) and valor_empresa != valor_empresa)
        else 0.0
    )
    vs = (
        float(promedio_sector)
        if promedio_sector is not None
        and not (isinstance(promedio_sector, float) and promedio_sector != promedio_sector)
        else None
    )

    mx = _tacometro_axis_max(ve, vs, piso_escala)
    titulo_plot, titulo_fs = _titulo_tacometro_multilinea(titulo)
    # Una sola franja neutra (sin tricolor); el foco va a la aguja y al umbral del sector
    steps = [{"range": [0, mx], "color": "rgba(218, 226, 239, 0.55)"}]
    gauge: dict = {
        "axis": {
            "range": [0, mx],
            "tickwidth": 2,
            "tickcolor": COLOR_BRAND_NAVY,
            "tickfont": {"size": 13, "color": COLOR_BRAND_NAVY, "family": "Segoe UI, sans-serif"},
        },
        "bar": {"color": color_aguja, "thickness": 0.82},
        "bgcolor": "rgba(255,255,255,0.6)",
        "borderwidth": 2,
        "bordercolor": "rgba(39,48,110,0.22)",
        "steps": steps,
    }
    if vs is not None and 0 <= vs <= mx:
        gauge["threshold"] = {
            "line": {"color": "#087F5B", "width": 5},
            "thickness": 1.0,
            "value": vs,
        }

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=ve,
            number={
                "suffix": " %",
                "font": {
                    "size": 26,
                    "color": COLOR_BRAND_NAVY,
                    "family": "Segoe UI, sans-serif",
                },
            },
            title={
                "text": titulo_plot,
                "font": {
                    "size": titulo_fs,
                    "color": COLOR_BRAND_NAVY,
                    "family": "Segoe UI, sans-serif",
                },
            },
            domain={"x": [0.06, 0.94], "y": [0.08, 0.92]},
            gauge=gauge,
        )
    )
    # Leyenda en dos líneas para pantallas estrechas (móvil)
    if vs is not None:
        ann = (
            f"<b style='color:#087F5B;font-size:15px'>Promedio sector</b> "
            f"<span style='color:#087F5B;font-size:15px;font-weight:700'>{vs:.1f} %</span><br>"
            f"<b style='color:#27306E;font-size:15px'>La Internacional</b> "
            f"<span style='color:#27306E;font-size:15px;font-weight:700'>{ve:.1f} %</span>"
        )
    else:
        ann = (
            f"<b style='color:#27306E;font-size:15px'>La Internacional</b> "
            f"<span style='font-size:15px;font-weight:700'>{ve:.1f} %</span>"
        )
    fig.add_annotation(
        x=0.5,
        y=-0.08,
        xref="paper",
        yref="paper",
        text=ann,
        showarrow=False,
        align="center",
        font=dict(size=14, color="#343A40", family="Segoe UI, sans-serif"),
    )
    fig.update_layout(
        height=360,
        margin=dict(t=64, b=90, l=8, r=8, pad=0),
        paper_bgcolor="#F0F4FB",
        font=dict(color=COLOR_BRAND_NAVY, family="Segoe UI, sans-serif"),
    )
    return fig


def _build_fig_primas_mensuales_top3(
    dfm: pd.DataFrame,
    tc_df: pd.DataFrame,
    top3: pd.DataFrame,
    anio_curso: int,
) -> go.Figure:
    meses_labels: list[str] = []
    for _, r in top3.iterrows():
        ser0 = serie_mensual_millones_usd(dfm, tc_df, str(r["peer_id"]), anio_curso)
        if not ser0.empty:
            meses_labels = [
                f"{int(row.year)}-{int(row.month):02d}" for _, row in ser0.iterrows()
            ]
            break
    if not meses_labels:
        for m in sorted(dfm[dfm["year"] == anio_curso]["month"].dropna().unique()):
            meses_labels.append(f"{anio_curso}-{int(m):02d}")

    fig_pr = go.Figure()
    for j, (_, r) in enumerate(top3.iterrows()):
        pid = str(r["peer_id"])
        ser = serie_mensual_millones_usd(dfm, tc_df, pid, anio_curso)
        if ser.empty:
            continue
        by_m = {
            int(row.month): float(row["primas_mes_millones_usd"]) for _, row in ser.iterrows()
        }
        ys = []
        for lab in meses_labels:
            mo = int(lab.split("-")[1])
            ys.append(by_m.get(mo, 0.0))
        nm = _etiqueta_barra_corta(dfm, pid)
        lw = 2.8 if pid == "La Internacional" else 1.2
        lc = "#B8860B" if pid == "La Internacional" else "white"
        fig_pr.add_trace(
            go.Bar(
                x=meses_labels,
                y=ys,
                name=nm,
                marker=dict(
                    color=color_linea_peer(pid, j),
                    line=dict(color=lc, width=lw),
                    opacity=0.92,
                ),
                hovertemplate=f"{nm}<br>%{{x}}<br>%{{y:,.2f}} M USD<extra></extra>",
            )
        )
    fig_pr.update_layout(
        **plotly_brand_theme(
            height=460,
            margin=dict(t=72, b=56, l=52, r=24),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                x=0.5,
                xanchor="center",
            ),
        ),
        title=dict(
            text=f"<b>Primas mensuales · {anio_curso}</b> · millones USD (barras verticales)",
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="Mes",
        yaxis_title="Millones USD",
        barmode="group",
        bargap=0.18,
        bargroupgap=0.06,
    )
    return fig_pr


st.set_page_config(
    page_title=f"Top 3 empresas | {APP_NAME_SHORT}",
    page_icon="🏆",
    layout="wide",
)

st.markdown(
    """
<style>
    .page-h1 {
        font-size: 1.4rem;
        font-weight: 600;
        color: #27306E;
        margin: 0.35rem 0 0.45rem 0;
        line-height: 1.25;
    }
    .gauge-section-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #27306E;
        margin: 0.55rem 0 0.4rem 0;
        line-height: 1.3;
    }
    .gauge-section-hint {
        font-size: 1rem;
        line-height: 1.55;
        color: #495057;
        margin: 0 0 0.85rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

render_demo_sidebar()

render_brand_header(f"Top 3 YTD · USD (BCV) · Anuario {DATA_YEAR}")
st.markdown('<p class="page-h1">Top 3 empresas — año en curso</p>', unsafe_allow_html=True)

try:
    dfm = load_primas_mensual_largo()
    ind = load_indicadores_29()
    tc = load_bcv_mensual()
except Exception as e:
    st.error(f"No se pudieron cargar los datos: {e}")
    st.stop()

idx_loaded: pd.DataFrame | None = None
idx_h: pd.DataFrame | None = None
try:
    idx_loaded = load_indices_boletin()
except FileNotFoundError:
    idx_loaded = None
try:
    idx_h = load_indices_historico()
except FileNotFoundError:
    idx_h = None

anio_curso = int(dfm["year"].max())
fech26 = ultimo_periodo_en_ano(dfm, anio_curso)
if fech26 is None:
    st.error(
        f"No hay datos para el último año en la serie ({anio_curso}). "
        "Ejecute `python scripts/build_primas_historico.py`."
    )
    st.stop()

rank_full = tabla_ranking_en_fecha(dfm, fech26)
total_mercado_usd = mercado_ytd_millones_usd_total(dfm, tc, pd.Timestamp(fech26))

ranked = rank_full.copy().reset_index(drop=True)
ranked["Ranking"] = ranked["ranking"].astype(int)

focus_rows = ranked[ranked["peer_id"] == "La Internacional"]
if focus_rows.empty:
    st.warning(
        "No se encontró «La Internacional» en el ranking. "
        "Revise `demo_historico.empresa_peer_id`."
    )
    rango = None
    focus_row = pd.DataFrame()
else:
    focus_row = focus_rows.iloc[[0]]
    rango = int(focus_row["Ranking"].iloc[0])

top3 = ranked.head(3)

render_cuadro_boletin_ranking(
    st,
    ranked,
    dfm,
    pd.Timestamp(fech26),
    top_n=10,
    titulo="Ranking de primas (estilo boletín SUDEASEG)",
    descripcion="Incluye la columna **PNC al inicio** (acumulado previo al mes de corte). "
    "La fila TOTAL suma miles Bs. y los puntos de participación de las filas visibles (subconjunto Top 10).",
)

st.markdown(
    '<p class="gauge-section-title">Indicadores — La Internacional vs sector (boletín SUDEASEG)</p>',
    unsafe_allow_html=True,
)
if idx_loaded is None or idx_loaded.empty:
    st.info(
        "No hay índices del boletín para tacómetros. Ejecute `python scripts/build_indices_por_empresa.py`."
    )
else:
    iy_idx = int(idx_loaded["year"].max())
    im_idx = int(idx_loaded.loc[idx_loaded["year"] == iy_idx, "month"].max())
    sub_li = idx_loaded[
        (idx_loaded["peer_id"] == "La Internacional")
        & (idx_loaded["year"] == iy_idx)
        & (idx_loaded["month"] == im_idx)
    ]
    if sub_li.empty:
        st.warning(
            f"No hay fila de índices para La Internacional en el corte "
            f"{MESES_NOMBRE.get(im_idx, str(im_idx))} {iy_idx}."
        )
    else:
        rr = sub_li.iloc[0]
        tac_specs: list[tuple[str, str, float, str]] = [
            ("SINI_PAG_VS_PRIM_PCT", "Siniestralidad (pag./primas)", 85.0, "#E63946"),
            ("GAST_ADM_VS_PRIM_PCT", "Gastos administración", 35.0, "#1D3557"),
            ("COMISION_VS_PRIM_PCT", "Comisiones", 18.0, "#7209B7"),
            ("GAST_ADQ_VS_PRIM_PCT", "Gastos de adquisición", 14.0, "#F77F00"),
        ]
        st.markdown(
            f'<p class="gauge-section-hint">Corte índices: <strong>{MESES_NOMBRE.get(im_idx, str(im_idx))} {iy_idx}</strong>. '
            "Cada tacómetro tiene <strong>escala propia</strong>. "
            "<strong>Arco de color</strong> = La Internacional; "
            "<strong style=\'color:#087F5B\'>Marca verde</strong> en el arco = promedio del sector "
            "(mismo mes del boletín).</p>",
            unsafe_allow_html=True,
        )
        for row_specs in (tac_specs[:2], tac_specs[2:]):
            c_left, c_right = st.columns(2, gap="medium")
            for col_g, (col_code, titulo, piso, c_aguja) in zip(
                (c_left, c_right), row_specs
            ):
                v_emp = rr[col_code] if col_code in rr.index else None
                v_emp = float(v_emp) if v_emp is not None and pd.notna(v_emp) else None
                v_sec = _sector_promedio_boletin(idx_loaded, iy_idx, im_idx, col_code)
                with col_g:
                    st.plotly_chart(
                        _fig_tacometro_vs_sector(
                            titulo,
                            v_emp,
                            v_sec,
                            piso_escala=piso,
                            color_aguja=c_aguja,
                        ),
                        use_container_width=True,
                        config={"displayModeBar": False},
                        key=f"gauge_main_{col_code}",
                    )

st.markdown("### Participación en el mercado (YTD)")
st.caption(
    "Top 3 y **resto del mercado** · millones USD (tipo BCV) · "
    "**La Internacional** resaltada si está en el Top 3."
)
fig_pie_hero = _fig_pie_participacion(
    dfm,
    top3,
    fech26,
    total_mercado_usd,
    anio_curso,
    tc,
    chart_height=580,
)
st.plotly_chart(
    fig_pie_hero,
    use_container_width=True,
    config={"displayModeBar": "hover"},
    key="main_pie_participacion",
)

st.markdown("### Primas mensuales (Top 3)")
st.caption(
    f"Barras verticales agrupadas por mes · millones USD · **{anio_curso}**."
)
fig_primas_main = _build_fig_primas_mensuales_top3(dfm, tc, top3, anio_curso)
st.plotly_chart(
    fig_primas_main,
    use_container_width=True,
    config={"displayModeBar": "hover"},
    key="main_primas_mensuales",
)

if rango is not None:
    st.success(
        f"**La Internacional** — **#{rango}** en el ranking YTD {anio_curso} "
        f"({len(ranked)} empresas en el cuadro)."
    )

tab_vol, tab_ind, tab_evo = st.tabs(
    ["Volumen y participación", "Indicadores — Boletín en cifras", "Evolución mensual"]
)

with tab_vol:
    st.subheader(f"Detalle volumen — {fech26.strftime('%Y-%m')} · USD")
    st.caption(
        "Resumen principal arriba: **tacómetros**, **participación** y **primas mensuales**. "
        "Aquí: tabla con **miles de bolívares** (cuadro fuente)."
    )

    rows_tab = []
    for _, r in top3.iterrows():
        pid = str(r["peer_id"])
        usd = ytd_millones_usd_desde_serie_mensual(dfm, tc, pid, pd.Timestamp(fech26))
        rows_tab.append(
            {
                "Ranking": int(r["Ranking"]),
                "Empresa": r["empresa_raw"],
                "YTD (M USD)": usd,
                "% participación": float(r["pct_participacion"])
                if pd.notna(r["pct_participacion"])
                else None,
                "YTD (miles Bs.)": float(r["primas_miles_bs"]),
            }
        )
    show_tab = pd.DataFrame(rows_tab)
    st.dataframe(
        show_tab.style.format(
            {
                "YTD (M USD)": "{:,.2f}",
                "% participación": "{:.2f}",
                "YTD (miles Bs.)": "{:,.0f}",
            },
            na_rep="—",
        ),
        use_container_width=True,
        hide_index=True,
    )

with tab_ind:
    st.subheader("Índices por empresa (Boletín en cifras, SUDEASEG)")
    st.markdown(
        "Cada ratio en su propia escala (**barras verticales**). Definiciones alineadas al boletín SUDEASEG."
    )

    if idx_loaded is None or idx_loaded.empty:
        st.warning(
            "No hay archivo de índices. Ejecute `python scripts/build_indices_por_empresa.py`."
        )
    else:
        iy = int(idx_loaded["year"].max())
        im = int(idx_loaded.loc[idx_loaded["year"] == iy, "month"].max())
        arch = str(idx_loaded.iloc[0].get("archivo_fuente", ""))
        st.caption(
            f"**Corte índices:** {MESES_NOMBRE.get(im, str(im))} **{iy}** · "
            f"archivo origen: `{arch or '—'}`"
        )

        filas_ind: list[dict] = []
        faltan: list[str] = []
        for _, r in top3.iterrows():
            pid = str(r["peer_id"])
            sub = idx_loaded[idx_loaded["peer_id"] == pid]
            if sub.empty:
                faltan.append(str(r["empresa_raw"]))
                continue
            row = sub.loc[sub["year"] == iy]
            row = row[row["month"] == im]
            if row.empty:
                faltan.append(str(r["empresa_raw"]))
                continue
            rr = row.iloc[0]
            d: dict = {"Empresa": str(r["empresa_raw"]), "peer_id": pid}
            for col, lab in INDICES_METRICAS:
                d[lab] = rr[col] if col in rr.index else None
            filas_ind.append(d)

        if faltan:
            st.warning(
                "No hay fila de índices para: "
                + ", ".join(faltan)
                + ". Revise nombres en el Excel o amplíe `empresa_peer_id`."
            )

        if filas_ind:
            df_show = pd.DataFrame(filas_ind)
            lab_cols = [lab for _, lab in INDICES_METRICAS]
            st.dataframe(
                df_show[["Empresa"] + lab_cols].style.format(
                    {c: "{:,.2f}" for c in lab_cols},
                    na_rep="—",
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("Gráficos por indicador (Top 3)")
            for row_i in range(0, len(INDICES_METRICAS), 2):
                c_left, c_right = st.columns(2)
                for ci, col_idx in enumerate((row_i, row_i + 1)):
                    if col_idx >= len(INDICES_METRICAS):
                        break
                    col_code, title = INDICES_METRICAS[col_idx]
                    fig_i = _fig_indicador_top3(
                        col_code, title, idx_loaded, top3, dfm, iy, im
                    )
                    target = c_left if ci == 0 else c_right
                    with target:
                        st.plotly_chart(
                            fig_i,
                            use_container_width=True,
                            config={"displayModeBar": "hover"},
                            key=f"tab_ind_bar_{col_code}_{col_idx}",
                        )

    st.subheader(f"Indicadores financieros — anuario {DATA_YEAR} (cuadro 29)")
    st.caption(
        "Referencia anual publicada en el anuario; no coincide en el tiempo con el YTD de primas "
        "ni con el boletín mensual de índices."
    )
    ind_df = ind.copy()
    ind_df["peer_id"] = ind_df["NOMBRE_EMPRESA"].map(empresa_peer_id)
    peer_need = list(top3["peer_id"].unique())
    if "La Internacional" not in peer_need:
        peer_need.append("La Internacional")

    ind_sub = ind_df[ind_df["peer_id"].isin(peer_need)].drop_duplicates("peer_id")
    orden = {p: i for i, p in enumerate(peer_need)}
    ind_sub["_ord"] = ind_sub["peer_id"].map(lambda x: orden.get(x, 99))
    ind_sub = ind_sub.sort_values("_ord").drop(columns=["_ord"])

    rename = {
        "NOMBRE_EMPRESA": "Empresa",
        "PCT_SINIESTRALIDAD_PAGADA": "Siniestralidad pagada %",
        "PCT_COMISION_GASTOS_ADQUISICION": "Comisión y gastos adquisición %",
        "PCT_GASTOS_ADMINISTRACION": "Gastos administración %",
        "GASTOS_COBERTURA_RESERVAS": "Gastos cobertura reservas",
        "INDICE_UTILIDAD_PATRIMONIO": "Índice utilidad / patrimonio",
    }
    cols_show = [c for c in rename if c in ind_sub.columns]
    ind_show = ind_sub[cols_show].rename(columns=rename)
    st.dataframe(ind_show, use_container_width=True, hide_index=True)

    st.markdown(
        f"_Primas (pestaña «Volumen»): YTD **{anio_curso}** en USD según SUDEASEG + BCV._"
    )

with tab_evo:
    st.subheader("Evolución mes a mes — primas (Top 3)")
    st.caption(
        f"Mismo gráfico que arriba · **Barras verticales** por mes · millones USD · **{anio_curso}**."
    )
    fig_pr_tab = _build_fig_primas_mensuales_top3(dfm, tc, top3, anio_curso)
    st.plotly_chart(
        fig_pr_tab,
        use_container_width=True,
        config={"displayModeBar": "hover"},
        key="tab_evo_primas_mensuales",
    )

    st.subheader("Evolución mes a mes — índices del boletín (Top 3)")
    if idx_h is None or idx_h.empty:
        st.info(
            "No hay histórico de índices. Ejecute `python scripts/build_indices_por_empresa.py` "
            "(el Excel debe incluir varias hojas mensuales, p. ej. Enero y Febrero)."
        )
    else:
        peer_ids_t3 = [str(x) for x in top3["peer_id"].tolist()]
        sub_h = idx_h[idx_h["peer_id"].isin(peer_ids_t3)].copy()
        sub_h["periodo"] = pd.to_datetime(
            sub_h["year"].astype(str)
            + "-"
            + sub_h["month"].astype(int).astype(str).str.zfill(2)
            + "-01",
            errors="coerce",
        )
        meses_idx = sorted(sub_h["periodo"].unique())
        st.caption(
            f"**{len(meses_idx)}** mes(es) en el archivo · **Barras verticales** agrupadas por mes; "
            "cada panel con escala propia."
        )
        if len(meses_idx) < 2:
            st.warning(
                "Con un solo mes en el histórico solo verá un grupo de barras; "
                "añada hojas al Excel o un archivo con más meses y vuelva a generar el CSV."
            )

        x_labels = [pd.Timestamp(t).strftime("%Y-%m") for t in meses_idx]

        def _vals_metric(pid: str, col_code: str) -> list[float]:
            g = sub_h[sub_h["peer_id"] == pid].sort_values(["year", "month"])
            by_k: dict[str, float] = {}
            for _, row in g.iterrows():
                k = pd.Timestamp(row["periodo"]).strftime("%Y-%m")
                v = row[col_code]
                by_k[k] = float(v) if pd.notna(v) else 0.0
            return [by_k.get(xl, 0.0) for xl in x_labels]

        fig_m = make_subplots(
            rows=3,
            cols=3,
            subplot_titles=INDICES_SUBPLOT_TITLES,
            vertical_spacing=0.14,
            horizontal_spacing=0.07,
            specs=[[{"type": "bar"} for _ in range(3)] for _ in range(3)],
        )
        for i, (col_code, _lab) in enumerate(INDICES_METRICAS):
            rr, cc = i // 3 + 1, i % 3 + 1
            for j, pid in enumerate(peer_ids_t3):
                ys = _vals_metric(pid, col_code)
                nm = _etiqueta_barra_corta(dfm, pid)
                col = color_linea_peer(pid, j)
                lw = 2.6 if pid == "La Internacional" else 1.0
                lc = "#B8860B" if pid == "La Internacional" else "white"
                fig_m.add_trace(
                    go.Bar(
                        x=x_labels,
                        y=ys,
                        name=nm,
                        legendgroup=pid,
                        showlegend=(i == 0),
                        marker=dict(color=col, line=dict(width=lw, color=lc), opacity=0.9),
                        hovertemplate=f"{nm}<br>%{{x}}<br>%{{y:,.2f}}<extra></extra>",
                    ),
                    row=rr,
                    col=cc,
                )
        fig_m.for_each_annotation(lambda a: a.update(font=dict(size=10, color=COLOR_BRAND_NAVY)))
        fig_m.update_layout(
            **plotly_brand_theme(
                height=1000,
                margin=dict(t=40, b=52, l=44, r=28),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.01,
                    x=0.5,
                    xanchor="center",
                ),
            ),
            barmode="group",
            bargap=0.15,
            bargroupgap=0.05,
        )
        fig_m.update_xaxes(tickangle=-35, automargin=True)
        fig_m.update_yaxes(automargin=True)
        st.plotly_chart(
            fig_m,
            use_container_width=True,
            config={"displayModeBar": "hover"},
            key="tab_evo_indices_subplots",
        )
