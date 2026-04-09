import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from demo_config import (
    APP_NAME_SHORT,
    COLOR_BRAND_GOLD,
    COLOR_MUTED,
    FUENTE_DATOS,
    color_linea_peer,
    plotly_brand_theme,
    render_brand_header,
    render_demo_sidebar,
)
from demo_fx import (
    agregar_usd_mensual,
    load_bcv_mensual,
    merge_tipo_cambio,
    ytd_millones_usd_desde_serie_mensual,
)
from demo_historico import (
    acumulado_a_primas_mensuales,
    conjunto_analisis,
    etiqueta_display,
    load_primas_mensual_largo,
    serie_peers,
    variacion_interanual_diciembre,
)

st.set_page_config(
    page_title=f"Serie histórica | {APP_NAME_SHORT}",
    page_icon="📈",
    layout="wide",
)

st.markdown(
    f"""
<style>
    .page-h1 {{
        font-size: 1.4rem;
        font-weight: 600;
        color: #27306E;
        margin: 0.35rem 0 0.45rem 0;
        line-height: 1.25;
    }}
    .block-note {{
        border-left: 4px solid {COLOR_BRAND_GOLD};
        padding-left: 1rem;
        color: {COLOR_MUTED};
        font-size: 0.9rem;
    }}
</style>
""",
    unsafe_allow_html=True,
)

render_demo_sidebar()

render_brand_header("Primas mensuales · USD (BCV) · participación · Top del mercado vs La Internacional")
st.markdown('<p class="page-h1">Serie histórica</p>', unsafe_allow_html=True)

try:
    df = load_primas_mensual_largo()
    tc = load_bcv_mensual()
except Exception as e:
    st.error(str(e))
    st.stop()

ult, peer_ids = conjunto_analisis(df, n=5)
sub = serie_peers(df, peer_ids)
sub_m = acumulado_a_primas_mensuales(sub)
sub_m = merge_tipo_cambio(sub_m, tc)
sub_m = agregar_usd_mensual(sub_m)

ult_row = df[df["fecha_periodo"] == ult]
intl = ult_row[ult_row["peer_id"] == "La Internacional"]
rank_i = int(intl["ranking"].iloc[0]) if not intl.empty else None
primas_i_bs = float(intl["primas_miles_bs"].iloc[0]) if not intl.empty else None
part_i = float(intl["pct_participacion"].iloc[0]) if not intl.empty and intl["pct_participacion"].notna().any() else None
top1 = ult_row[ult_row["ranking"] == 1]
p1_bs = float(top1["primas_miles_bs"].iloc[0]) if not top1.empty else None

ytd_usd_intl = ytd_millones_usd_desde_serie_mensual(df, tc, "La Internacional", pd.Timestamp(ult))
ytd_usd_lider = (
    ytd_millones_usd_desde_serie_mensual(df, tc, str(top1.iloc[0]["peer_id"]), pd.Timestamp(ult))
    if not top1.empty
    else float("nan")
)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Último cierre", pd.Timestamp(ult).strftime("%Y-%m-%d"))
with m2:
    st.metric("Ranking La Int.", f"#{rank_i}" if rank_i else "—")
with m3:
    st.metric(
        "YTD La Int. (M USD)",
        f"{ytd_usd_intl:,.2f}" if ytd_usd_intl == ytd_usd_intl else "—",
    )
with m4:
    st.metric("Participación", f"{part_i:.2f} %" if part_i is not None else "—")

st.caption(
    f"USD: flujos mensuales al tipo BCV de cada mes · Cierre SUDEASEG **{pd.Timestamp(ult).strftime('%Y-%m-%d')}**."
)

if (
    primas_i_bs
    and p1_bs
    and math.isfinite(ytd_usd_lider)
    and math.isfinite(ytd_usd_intl)
    and ytd_usd_lider > 0
):
    pct_usd = 100.0 * ytd_usd_intl / ytd_usd_lider
    lr = ult_row[ult_row["ranking"] == 1]
    leader_lbl = (
        etiqueta_display(df, str(lr.iloc[0]["peer_id"]))
        if not lr.empty
        else "el líder"
    )
    st.markdown(
        f'<p class="block-note">vs <strong>{leader_lbl}</strong> (#1): YTD USD La Internacional = '
        f"<strong>{pct_usd:.1f}%</strong> del líder.</p>",
        unsafe_allow_html=True,
    )

with st.expander("Metodología (flujo mensual y USD)", expanded=False):
    st.markdown(
        "**Flujo mensual:** acumulado del mes menos acumulado del mes anterior (por año). "
        "**USD:** cada mes al tipo BCV de ese mes (`bcv_ves_por_usd_mensual.csv`)."
    )

unidad = st.radio(
    "Unidad del gráfico de flujo",
    ["Millones USD (tipo BCV por mes)", "Miles de Bs. nominales (sin conversión)"],
    horizontal=True,
    index=0,
)

use_usd = unidad.startswith("Millones")

# Gráfico primas MENSUALES
fig = go.Figure()
legend_bottom = dict(
    orientation="h",
    yanchor="top",
    y=-0.28,
    xanchor="center",
    x=0.5,
    font=dict(size=11),
)

for i, pid in enumerate(peer_ids):
    s = sub_m[sub_m["peer_id"] == pid]
    if s.empty:
        continue
    label = etiqueta_display(df, pid)
    color = color_linea_peer(pid, i)
    width = 3.6 if pid == "La Internacional" else 2.2
    if use_usd:
        yv = s["primas_mes_millones_usd"]
        ht = "%{x|%Y-%m}<br>%{y:,.3f} M USD<extra></extra>"
        y_title = "Millones USD (nominal, al tipo del mes)"
    else:
        yv = s["primas_mes_miles"]
        ht = "%{x|%Y-%m}<br>%{y:,.0f} miles Bs.<extra></extra>"
        y_title = "Miles de Bs. (flujo mensual nominal)"
    extra = {}
    if pid == "La Internacional" and use_usd:
        extra = dict(
            fill="tozeroy",
            fillcolor="rgba(255, 203, 5, 0.22)",
            line=dict(color=color, width=width, shape="spline", smoothing=0.35),
        )
    else:
        extra = dict(line=dict(color=color, width=width, shape="spline", smoothing=0.35))
    fig.add_trace(
        go.Scatter(
            x=s["fecha_periodo"],
            y=yv,
            mode="lines",
            name=label,
            hovertemplate=ht,
            **extra,
        )
    )

title_main = (
    "Primas netas del mes — en millones de dólares (tipo de cambio oficial BCV, cada mes)"
    if use_usd
    else "Primas netas del mes — miles de bolívares nominales (sin conversión)"
)
subtitle = (
    "Cada punto usa el tipo VES/USD del cierre de mes correspondiente · Fuente primas: SUDEASEG"
    if use_usd
    else "Estimado como diferencia de acumulados YTD publicados por SUDEASEG"
)

fig.update_layout(
    **plotly_brand_theme(height=580, legend=legend_bottom, margin=dict(t=110, b=170, l=56, r=40)),
    title=dict(
        text=f"<b>{title_main}</b><br><sup>{subtitle}</sup>",
        x=0.5,
        xanchor="center",
        y=0.97,
    ),
    xaxis_title="Mes",
    yaxis_title=y_title,
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": "hover"})

st.subheader("Participación en el mercado (%)")
fig2 = go.Figure()
for i, pid in enumerate(peer_ids):
    s = sub[sub["peer_id"] == pid]
    if s.empty or s["pct_participacion"].isna().all():
        continue
    label = etiqueta_display(df, pid)
    color = color_linea_peer(pid, i)
    fig2.add_trace(
        go.Scatter(
            x=s["fecha_periodo"],
            y=s["pct_participacion"],
            mode="lines",
            name=label,
            line=dict(
                color=color,
                width=3.0 if pid == "La Internacional" else 2.2,
                shape="spline",
                smoothing=0.35,
            ),
            hovertemplate="%{x|%Y-%m}<br>%{y:.2f}%<extra></extra>",
        )
    )
fig2.update_layout(
    **plotly_brand_theme(height=500, legend=legend_bottom, margin=dict(t=100, b=170, l=56, r=40)),
    title=dict(
        text="<b>Participación de mercado</b><br><sup>% sobre el universo del cuadro (SUDEASEG)</sup>",
        x=0.5,
        xanchor="center",
    ),
    xaxis_title="Cierre de mes",
    yaxis_title="% participación",
)
st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": "hover"})

st.subheader("Variación interanual (diciembre vs diciembre, miles Bs. nominales)")
var_df = variacion_interanual_diciembre(df, peer_ids)
if var_df.empty:
    st.info("No hay pares completos de cierres de diciembre para calcular variación YoY.")
else:
    pivot = var_df.pivot(index="peer_id", columns="periodo", values="variacion_pct")
    pivot = pivot.reindex([p for p in peer_ids if p in pivot.index])
    pivot_display = pivot.round(1)
    pivot_display.index = [etiqueta_display(df, str(i)) for i in pivot_display.index]
    st.dataframe(pivot_display, use_container_width=True)

with st.expander("Fuente de los datos", expanded=False):
    st.markdown(FUENTE_DATOS)

with st.expander("Lectura comparativa (guía para la reunión)", expanded=False):
    st.markdown(
        """
**Primas en bolívares vs USD**

- SUDEASEG publica primas en **bolívares nominales** (miles de Bs.). La inflación puede inflar la serie nominal.
- Aquí, la vista en **USD** usa el tipo de cambio **oficial BCV** (bolívares por dólar) **de cada mes**, 
  construido con `scripts/build_bcv_mensual.py`: donde hay cotización diaria replicada vía API pública se toma el **último día del mes**; 
  el resto se interpola entre **anclas** de referencia. **Valide** las cifras contra el BCV para trabajo fino.

**YTD en USD**

- Es la **suma** de los flujos mensuales ya convertidos; no es el acumulado en Bs. dividido por un solo tipo.

**Participación %**

- No depende del tipo de cambio: compara posiciones dentro del mismo universo del cuadro.

**Limitaciones**

- 2026: solo meses publicados en la descarga de SUDEASEG.
"""
    )

st.caption(
    "Fuentes: SUDEASEG (`python scripts/build_primas_historico.py`) · "
    "Tipo cambio BCV (`python scripts/build_bcv_mensual.py`)."
)
