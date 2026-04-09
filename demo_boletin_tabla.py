"""Cuadro tipo boletín SUDEASEG: ranking con PNC al inicio del mes + YTD + participación."""
from __future__ import annotations

import html
import math
import textwrap
from typing import Any

import pandas as pd

from demo_config import COLOR_BRAND_GOLD, COLOR_BRAND_NAVY
from demo_historico import primas_acumuladas_al_inicio_mes

# Fondo por fila (degradado aproximado al boletín — contraste con texto blanco)
BOLETIN_FILA_BG: list[str] = [
    "#1e3a5f",
    "#2563eb",
    "#0d9488",
    "#059669",
    "#65a30d",
    "#7f1d1d",
    "#dc2626",
    "#ca8a04",
    "#9ca3af",
    "#6b7280",
]


def fmt_miles_bs_es(val: float | None) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—"
    neg = val < 0
    v = abs(val)
    s = f"{v:,.2f}"
    intp, frac = s.split(".", 1)
    intp = intp.replace(",", ".")
    body = f"{intp},{frac}"
    return ("-" if neg else "") + body


def fmt_pct_es(val: float | None) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—"
    s = f"{val:.2f}"
    return s.replace(".", ",")


def _row_cells(
    pnc0: float | None,
    nombre: str,
    ytd: float,
    pct: float | None,
    bg: str,
    *,
    es_total: bool = False,
    peer_id: str = "",
) -> str:
    fw = "700" if es_total else "500"
    pnc_s = fmt_miles_bs_es(pnc0)
    ytd_s = fmt_miles_bs_es(ytd)
    pct_s = fmt_pct_es(pct)
    pnc_style = "color:#fecaca;" if pnc0 is not None and pnc0 < 0 else "color:#fff;"
    ytd_style = "color:#fecaca;" if ytd < 0 else "color:#fff;"
    pill = ""
    if not es_total:
        esc = html.escape(nombre)
        ring = (
            f"box-shadow:0 0 0 2px {COLOR_BRAND_GOLD};"
            if peer_id == "La Internacional"
            else ""
        )
        pill = (
            '<span style="display:inline-block;padding:0.35rem 0.75rem;border-radius:999px;'
            f"background:rgba(255,255,255,0.14);{ring}\">{esc}</span>"
        )
    else:
        pill = f'<span style="font-weight:700">{html.escape(nombre)}</span>'

    return (
        f'<tr style="background:{bg};color:#fff;">'
        f'<td style="text-align:right;padding:10px 12px;{pnc_style}font-weight:{fw};">{pnc_s}</td>'
        f'<td style="text-align:left;padding:10px 12px;font-weight:{fw};">{pill}</td>'
        f'<td style="text-align:right;padding:10px 12px;{ytd_style}font-weight:{fw};">{ytd_s}</td>'
        f'<td style="text-align:right;padding:10px 12px;color:#fff;font-weight:{fw};">{pct_s}</td>'
        "</tr>"
    )


def render_cuadro_boletin_ranking(
    st_module: Any,
    ranked: pd.DataFrame,
    dfm: pd.DataFrame,
    fecha: pd.Timestamp,
    *,
    top_n: int = 10,
    titulo: str = "Primas netas cobradas — cuadro tipo boletín (Top 10)",
    descripcion: str | None = None,
) -> None:
    """
    Tabla HTML estilo boletín: PNC acumulada al inicio del mes, empresa, YTD miles Bs., % participación.
    `ranked`: salida de `tabla_ranking_en_fecha` ordenada por ranking.
    """
    sub = ranked.head(top_n).copy()
    if sub.empty:
        st_module.warning("No hay filas de ranking para armar el cuadro.")
        return

    rows_html: list[str] = []
    sum_p0 = 0.0
    sum_ytd = 0.0
    sum_pct = 0.0
    n_pct = 0

    for i, (_, r) in enumerate(sub.iterrows()):
        pid = str(r["peer_id"])
        pnc0 = primas_acumuladas_al_inicio_mes(dfm, pid, fecha)
        ytd = float(r["primas_miles_bs"])
        pct = float(r["pct_participacion"]) if pd.notna(r["pct_participacion"]) else None
        bg = BOLETIN_FILA_BG[i % len(BOLETIN_FILA_BG)]
        rows_html.append(
            _row_cells(
                pnc0,
                str(r["empresa_raw"]),
                ytd,
                pct,
                bg,
                peer_id=pid,
            )
        )
        if pnc0 is not None and not math.isnan(pnc0):
            sum_p0 += pnc0
        sum_ytd += ytd
        if pct is not None:
            sum_pct += pct
            n_pct += 1

    rows_html.append(
        _row_cells(
            sum_p0,
            "TOTAL",
            sum_ytd,
            sum_pct if n_pct else None,
            "#374151",
            es_total=True,
        )
    )

    mes = fecha.strftime("%Y-%m")
    subhdr_bg = "#64748b"
    # Sin sangría de 4+ espacios antes de las etiquetas: en Markdown eso se renderiza como bloque de código.
    thead = textwrap.dedent(
        f"""
<thead>
<tr style="background:{COLOR_BRAND_NAVY};color:#fff;">
<th style="padding:12px 10px;text-align:center;font-weight:700;">PNC al inicio</th>
<th style="padding:12px 10px;text-align:center;font-weight:700;">Empresa</th>
<th style="padding:12px 10px;text-align:center;font-weight:700;">Primas YTD</th>
<th style="padding:12px 10px;text-align:center;font-weight:700;">% participación<br/>en el mercado</th>
</tr>
<tr style="background:{subhdr_bg};color:#fff;font-size:0.82rem;">
<th style="padding:6px 10px;text-align:center;font-weight:600;">Miles de Bs.</th>
<th style="padding:6px 10px;text-align:center;font-weight:600;"></th>
<th style="padding:6px 10px;text-align:center;font-weight:600;">Miles de Bs.</th>
<th style="padding:6px 10px;text-align:center;font-weight:600;"></th>
</tr>
</thead>
"""
    ).strip()

    st_module.markdown(f"#### {titulo}")
    st_module.markdown(
        f"<p style='margin:0.15rem 0 0.5rem 0;font-size:0.95rem;color:#495057;'>"
        f"Cierre SUDEASEG <strong>{html.escape(mes)}</strong>. "
        f"<strong>PNC al inicio</strong>: acumulado en miles Bs. al cierre del mes anterior "
        f"(o diciembre del año previo si el corte es enero).</p>",
        unsafe_allow_html=True,
    )
    if descripcion:
        st_module.markdown(descripcion)

    table = (
        '<div class="boletin-cuadro-wrap" style="margin:0.5rem 0 1.25rem 0;overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;font-family:Segoe UI,system-ui,sans-serif;'
        "font-size:0.92rem;box-shadow:0 2px 12px rgba(39,48,110,0.12);border-radius:8px;overflow:hidden;\">"
        f"{thead}<tbody>{''.join(rows_html)}</tbody></table></div>"
    )
    st_module.markdown(table, unsafe_allow_html=True)
