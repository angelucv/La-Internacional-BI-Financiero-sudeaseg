# Demo BI financiero — La Internacional

Panel en [Streamlit](https://streamlit.io) con ranking Top 3, participación de mercado, indicadores del boletín SUDEASEG y series de primas (datos de demo en `data/public/`).

**Repositorio:** [github.com/angelucv/La-Internacional-BI-Financiero-sudeaseg](https://github.com/angelucv/La-Internacional-BI-Financiero-sudeaseg)

## Ejecución local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Despliegue en la nube (Streamlit Community Cloud)

1. Sube el proyecto a GitHub (por ejemplo el repo enlazado arriba).
2. Entra en [share.streamlit.io](https://share.streamlit.io) e inicia sesión con GitHub.
3. **New app** → selecciona el repositorio, rama y archivo principal **`app.py`**.
4. **Deploy**. Streamlit instalará dependencias desde `requirements.txt`.
5. Asegúrate de que la carpeta **`data/public/`** con los CSV esté versionada en el repo (o configura secretos / almacenamiento si más adelante mueves los datos).

La carpeta **`data/raw/`** (PDF y Excel de SUDEASEG) **no se sube a GitHub** por tamaño; queda en local para regenerar CSV con `scripts/`. Los logos van en **`Images/`** (ver `demo_config.py`).

## Requisitos

- Python 3.10+
- Ver `requirements.txt` (Streamlit ≥ 1.33 por la opción de sidebar en `.streamlit/config.toml`).
