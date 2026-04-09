# Demo reunión accionistas — La Internacional (datos SUDEASEG / Seguro en Cifras)
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from demo_config import APP_NAME_SHORT, DATA_YEAR, render_brand_header, render_demo_sidebar

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
    f"- **Sector e Internacional**: ranking, primas en USD (tipo de cambio del mes) e **indicadores financieros anuales** "
    f"por empresa (referencia anuario {DATA_YEAR}).\n"
    "- **Serie histórica**: evolución del flujo mensual y participación; comparativa con el líder del mercado "
    "y La Internacional.\n"
    "- Los importes siguen las **unidades y definiciones** de los cuadros oficiales (anuario y series mensuales SUDEASEG)."
)

with st.expander("Glosario de terminología", expanded=False):
    st.markdown(
        """
**Marco**

- **SUDEASEG**: superintendencia del sector asegurador en Venezuela; publica estadísticas y boletines con **definiciones propias** para cada ratio.
- **Primas netas**: ingresos por pólizas según el criterio del cuadro (frente a otras nociones contables de ingreso).
- **Prima devengada**: prima reconocida por el periodo (distinta de «cobrada»); algunos índices del boletín la usan como denominador.
- **Acumulado del año**: suma de primas desde enero hasta la **fecha de corte** del cuadro (lo que en fuentes suele etiquetarse como YTD).
- **Primas del mes / flujo mensual**: aquí se obtiene por **diferencia entre acumulados** consecutivos; aproxima el volumen del mes, no un asiento de caja.
- **PNC (primas netas cobradas)**: base en bolívares que el boletín usa para ciertos porcentajes (p. ej. saldos relativos a primas cobradas).
- **Reservas técnicas**: provisiones para obligaciones de seguro futuras; su peso frente a primas indica **carga de reserva** en la estructura del negocio.
- **Siniestros pagados**: desembolsos ya realizados por siniestros.
- **Siniestros incurridos**: obligación reconocida por siniestros ocurridos (devengo), aunque aún no esté todo pagado.

**Índices habituales en el boletín (misma numeración que en los cuadros)**

1. **Siniestros pagados / primas netas** — presión del **pagado** sobre el volumen de primas.
2. **Reservas técnicas / primas netas** — magnitud de reservas en relación con primas.
3. **Siniestros incurridos / prima devengada** — carga de siniestralidad devengada frente a prima devengada.
4. **Comisiones / primas netas** — costo de intermediación respecto de primas netas.
5. **Gastos de adquisición / primas netas** — gasto de colocación frente a primas netas.
6. **Gastos de administración / primas netas** — gasto de estructura frente a primas netas.
7. **Costo de reaseguro / prima devengada** — carga del reaseguro admitido frente a prima devengada.
8. **Tasa combinada** — indicador sintético de **siniestralidad más gastos de adquisición** frente a primas (lectura tipo «combined ratio»; la fórmula exacta es la del boletín).
9. **Índice de cobertura de reservas** — relación entre reservas y magnitudes de siniestralidad según la definición del cuadro (mide **colchón** frente a desembolsos incurridos en los términos del indicador).

**Cuenta de resultados técnica (orden típico en estados del ramo)**

- **Resultado técnico bruto**: resultado de la actividad aseguradora antes de ciertos ajustes de gestión.
- **Reaseguro cedido**: parte del riesgo transferida a reaseguradores; reduce la exposición neta de la compañía.
- **Resultado técnico neto**: resultado técnico después del efecto del reaseguro cedido.
- **Gestión general**: gastos de administración central y similares atribuibles en el cuadro.
- **Saldo de operaciones**: resultado que cierra la cadena mostrada; en el panel puede verse también como **porcentaje sobre PNC** para comparar entre empresas.

**Fuentes distintas**

- **Boletín periódico**: ratios e indicadores con **corte mensual** y metodología del boletín.
- **Anuario estadístico**: **cifras anuales** por empresa (siniestralidad, comisiones, gastos, etc.); no tiene por qué coincidir en tiempo con una serie mensual de primas.

_Las definiciones contables y regulatorias finales están en la normativa y en los documentos fuente de SUDEASEG._
"""
    )
