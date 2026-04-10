"""Temporal: lista archivos en directorio SUDEASEG Año 2026."""
from __future__ import annotations

import re
from urllib.request import Request, urlopen

url = (
    "https://www.sudeaseg.gob.ve/Descargas/Estadisticas/Cifras%20Mensuales/"
    "1%20Cuadro%20de%20Resultados/A%C3%B1o%202026/"
)
req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urlopen(req, timeout=60) as r:
    html = r.read().decode("utf-8", "replace")
for m in re.findall(r'href="([^"]+\.xlsx)"', html, re.I):
    print(m)
