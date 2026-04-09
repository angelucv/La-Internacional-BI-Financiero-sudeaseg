# Demo reunión accionistas — La Internacional (datos SUDEASEG / Seguro en Cifras)
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from demo_config import (
    APP_NAME_SHORT,
    COMPANY_FOCUS,
    DATA_YEAR,
    FUENTE_DATOS,
    render_brand_header,
    render_demo_sidebar,
)

st.set_page_config(
    page_title=f"Inicio | {APP_NAME_SHORT}",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_demo_sidebar()

render_brand_header("Panel para reunión de accionistas — datos oficiales SUDEASEG")

st.markdown(
    "Este panel es una **vista rápida** para la conversación con accionistas: "
    "**ranking y participación** con las primas **más recientes** publicadas por SUDEASEG "
    "(acumulado del año hasta el último mes disponible en la descarga), "
    "más **indicadores** del anuario de referencia y una **serie histórica** con primas **mensuales** "
    "(diferencia de acumulados) para ver el ritmo sin el efecto de cierre de año."
)

st.subheader("Cómo usarlo")
st.markdown(
    f"- **Sector e Internacional**: ranking, primas en USD (tipo de cambio del mes) e indicadores del "
    f"**cuadro 29** (referencia anuario {DATA_YEAR}).\n"
    "- **Serie histórica**: evolución del flujo mensual y participación; comparativa con el top del mercado "
    "y La Internacional.\n"
    "- Los importes siguen las **unidades de los cuadros fuente** (anuario y series mensuales SUDEASEG)."
)

st.success(
    "Ejecutar en local: `streamlit run app.py` — No requiere Supabase; los CSV están en `data/public/`."
)
