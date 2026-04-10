"""
Compila `data/public/resultado_tecnico_saldo_mensual.csv` desde los Excel oficiales
«1 Cuadro de Resultados» del Boletín en cifras (misma sección que el PDF mensual).

Uso típico (archivos en data/raw/xlsx/):
  python scripts/build_resultado_cuadro_boletin.py

O una carpeta concreta:
  python scripts/build_resultado_cuadro_boletin.py --carpeta data/raw/xlsx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from boletin_cuadro_resultados import (  # noqa: E402
    CSV_NAME,
    DATA_PUBLIC,
    parse_cuadro1_excel,
)


def _collect_xlsx(carpeta: Path) -> list[Path]:
    out: list[Path] = []
    for pat in ("1_Cuadro_de_Resultados*.xlsx", "1 Cuadro*.xlsx", "cuadro-de-resultados*.xlsx"):
        out.extend(carpeta.glob(pat))
        out.extend(carpeta.glob(pat.upper()))
    # únicos, ordenados
    return sorted({p.resolve() for p in out if p.is_file()})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--carpeta",
        type=Path,
        default=ROOT / "data" / "raw" / "xlsx",
        help="Carpeta con Excel «1 Cuadro de Resultados»",
    )
    ap.add_argument(
        "--merge",
        action="store_true",
        help="Fusionar con CSV existente (reemplaza mismo año/mes)",
    )
    args = ap.parse_args()

    if not args.carpeta.is_dir():
        print(f"No existe la carpeta: {args.carpeta}", file=sys.stderr)
        return 1

    paths = _collect_xlsx(args.carpeta)
    if not paths:
        print(
            f"No se encontró ningún «1_Cuadro_de_Resultados*.xlsx» en {args.carpeta}.",
            file=sys.stderr,
        )
        return 1

    bloques: list[pd.DataFrame] = []
    for path in paths:
        try:
            xl = pd.ExcelFile(path)
        except Exception as e:
            print(f"Omitiendo {path.name}: {e}", file=sys.stderr)
            continue
        for sheet in xl.sheet_names:
            if str(sheet).strip().lower() in ("portada", "índice", "indice"):
                continue
            try:
                df = parse_cuadro1_excel(path, sheet=sheet)
                bloques.append(df)
                print(f"OK {path.name} :: {sheet} → {len(df)} filas · {df['year'].iloc[0]}-{df['month'].iloc[0]:02d}")
            except Exception as e:
                msg = str(e).encode("ascii", "replace").decode("ascii")
                print(f"  skip hoja «{sheet}» en {path.name}: {msg}", file=sys.stderr)

    if not bloques:
        print("No se pudo leer ningún cuadro válido.", file=sys.stderr)
        return 1

    nuevo = pd.concat(bloques, ignore_index=True)
    cols = [
        "ranking",
        "empresa_raw",
        "peer_id",
        "pnc_miles_bs",
        "rt_bruto_miles_bs",
        "reaseguro_cedido_miles_bs",
        "rt_neto_miles_bs",
        "gestion_general_miles_bs",
        "saldo_operaciones_miles_bs",
        "pct_saldo_sobre_pnc",
        "year",
        "month",
        "fecha_periodo",
        "archivo_fuente",
    ]
    nuevo = nuevo[cols]
    out = DATA_PUBLIC / CSV_NAME
    DATA_PUBLIC.mkdir(parents=True, exist_ok=True)

    if args.merge and out.exists():
        prev = pd.read_csv(out, sep=";", encoding="utf-8")
        prev["fecha_periodo"] = pd.to_datetime(prev["fecha_periodo"])
        claves = {(int(r["year"]), int(r["month"])) for _, r in nuevo.iterrows()}
        mask = prev.apply(lambda r: (int(r["year"]), int(r["month"])) not in claves, axis=1)
        comb = pd.concat([prev[mask], nuevo], ignore_index=True)
        comb["fecha_periodo"] = pd.to_datetime(comb["fecha_periodo"], errors="coerce")
        comb = comb.sort_values(["fecha_periodo", "ranking"]).reset_index(drop=True)
        comb["fecha_periodo"] = comb["fecha_periodo"].dt.strftime("%Y-%m-%d")
        comb.to_csv(out, sep=";", index=False, encoding="utf-8")
        print(f"Fusionado → {out} ({len(comb)} filas).")
    else:
        nuevo = nuevo.sort_values(["fecha_periodo", "ranking"]).reset_index(drop=True)
        nuevo.to_csv(out, sep=";", index=False, encoding="utf-8")
        print(f"Escrito {out} ({len(nuevo)} filas).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
