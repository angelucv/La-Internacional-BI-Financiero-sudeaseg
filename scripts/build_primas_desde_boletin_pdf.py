"""
Genera `data/public/primas_netas_mensual_largo.csv` a partir de PDF del Boletín en cifras /
Cifras mensuales SUDEASEG (cuadro de primas netas cobradas por empresa).

Coloque los PDF en local, por ejemplo: data/raw/boletin_pdf/

Ejemplos:
  python scripts/build_primas_desde_boletin_pdf.py --pdf data/raw/boletin_pdf/feb2026.pdf --year 2026 --month 2
  python scripts/build_primas_desde_boletin_pdf.py --carpeta data/raw/boletin_pdf/ --merge

Si omite --year/--month, se intenta inferir del texto del PDF o del nombre del archivo.
Con --merge se conservan otros meses ya presentes en el CSV de salida.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
for p in (ROOT, SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from boletin_pdf import (  # noqa: E402
    assign_periodo,
    extract_primas_ranking_from_pdf,
    extract_text_first_pages,
    infer_year_month_from_filename,
    infer_year_month_from_text,
)
PUBLIC = ROOT / "data" / "public"
DEFAULT_OUT = PUBLIC / "primas_netas_mensual_largo.csv"


def _normalize_empresa(name: str) -> str:
    """Misma lógica que `scripts/build_primas_historico.py` para `empresa_norm`."""
    s = " ".join(str(name).split())
    low = (
        s.lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    if "internacional" in low and "seguros" in low:
        return "La Internacional"
    return s


def _periodo_para_pdf(
    path: Path, year: int | None, month: int | None
) -> tuple[int, int]:
    if year is not None and month is not None:
        return year, month
    text = extract_text_first_pages(path, max_pages=4)
    ym = infer_year_month_from_text(text)
    if ym:
        return ym
    ym = infer_year_month_from_filename(path.name)
    if ym:
        return ym
    raise ValueError(
        f"No se pudo determinar año/mes para {path}. "
        "Use --year y --month o renombre el archivo (p. ej. 2026_02_boletin.pdf)."
    )


def _normalizar_df(df: pd.DataFrame, archivo: str, year: int, month: int) -> pd.DataFrame:
    out = assign_periodo(df, year, month, archivo)
    out["empresa_norm"] = out["empresa_raw"].map(_normalize_empresa)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="CSV de primas desde PDF boletín SUDEASEG")
    ap.add_argument(
        "--pdf",
        action="append",
        default=[],
        help="Ruta a un PDF (repita para varios archivos)",
    )
    ap.add_argument(
        "--carpeta",
        type=Path,
        default=None,
        help="Directorio con archivos .pdf",
    )
    ap.add_argument(
        "--salida",
        type=Path,
        default=DEFAULT_OUT,
        help=f"CSV de salida (default: {DEFAULT_OUT})",
    )
    ap.add_argument(
        "--year",
        type=int,
        default=None,
        help="Año del corte (si un solo PDF y no se infiere)",
    )
    ap.add_argument(
        "--month",
        type=int,
        default=None,
        help="Mes del corte (1-12)",
    )
    ap.add_argument(
        "--merge",
        action="store_true",
        help="Unir con el CSV existente reemplazando solo los meses extraídos",
    )
    args = ap.parse_args()

    paths: list[Path] = []
    for p in args.pdf:
        paths.append(Path(p))
    if args.carpeta:
        carp = args.carpeta
        if not carp.is_dir():
            print(f"No existe la carpeta: {carp}", file=sys.stderr)
            return 1
        paths.extend(sorted(carp.glob("*.pdf")))
        paths.extend(sorted(carp.glob("*.PDF")))

    if not paths:
        print(
            "Indique --pdf archivo.pdf y/o --carpeta con PDF del boletín SUDEASEG.",
            file=sys.stderr,
        )
        return 1

    bloques: list[pd.DataFrame] = []
    for path in paths:
        if not path.exists():
            print(f"No existe: {path}", file=sys.stderr)
            return 1
        print(f"Leyendo {path.name} …")
        try:
            raw = extract_primas_ranking_from_pdf(path)
            if len(paths) == 1:
                y, m = _periodo_para_pdf(path, args.year, args.month)
            else:
                y, m = _periodo_para_pdf(path, None, None)
            df = _normalizar_df(raw, path.name, y, m)
            bloques.append(df)
            print(f"  → {len(df)} empresas · {y}-{m:02d}")
        except Exception as e:
            print(f"Error en {path}: {e}", file=sys.stderr)
            return 1

    nuevo = pd.concat(bloques, ignore_index=True)
    columnas = [
        "ranking",
        "empresa_raw",
        "primas_miles_bs",
        "pct_participacion",
        "year",
        "month",
        "fecha_periodo",
        "archivo_fuente",
        "hoja_mes",
        "empresa_norm",
    ]
    for c in columnas:
        if c not in nuevo.columns:
            nuevo[c] = None
    nuevo = nuevo[columnas]

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    if args.merge and args.salida.exists():
        prev = pd.read_csv(args.salida, sep=";", encoding="utf-8")
        prev["fecha_periodo"] = pd.to_datetime(prev["fecha_periodo"])
        claves = {(int(r["year"]), int(r["month"])) for _, r in nuevo.iterrows()}
        mask = prev.apply(
            lambda r: (int(r["year"]), int(r["month"])) not in claves, axis=1
        )
        prev_kept = prev[mask]
        comb = pd.concat([prev_kept, nuevo], ignore_index=True)
        comb = comb.sort_values(["fecha_periodo", "ranking"]).reset_index(drop=True)
        comb["fecha_periodo"] = comb["fecha_periodo"].dt.strftime("%Y-%m-%d")
        comb.to_csv(args.salida, sep=";", index=False, encoding="utf-8")
        print(f"Fusionado → {args.salida} ({len(comb)} filas).")
    else:
        nuevo = nuevo.sort_values(["fecha_periodo", "ranking"]).reset_index(drop=True)
        nuevo.to_csv(args.salida, sep=";", index=False, encoding="utf-8")
        print(f"Escrito {args.salida} ({len(nuevo)} filas).")

    print(
        "\nNota: la app (`load_primas_mensual_largo`) lee este CSV. "
        "Si usaba el script Excel, este archivo queda sustituido o ampliado según --merge."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
