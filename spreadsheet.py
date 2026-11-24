from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from cnpj_service import CNPJError, normalize_cnpj


CNPJ_ALIASES = {"cnpj", "documento", "document", "cnpj_raiz"}


def extract_cnpjs(path: str | Path) -> list[str]:
    file_path = Path(path)
    if file_path.suffix.lower() not in {".xlsx", ".xls", ".csv"}:
        raise ValueError("Selecione um arquivo CSV ou Excel.")

    if file_path.suffix.lower() == ".csv":
        frame = pd.read_csv(file_path, dtype=str)
    else:
        frame = pd.read_excel(file_path, dtype=str)

    column = next(
        (name for name in frame.columns if str(name).strip().lower() in CNPJ_ALIASES),
        None,
    )
    if column is None:
        raise ValueError("A planilha precisa ter uma coluna chamada CNPJ.")

    cnpjs: list[str] = []
    invalid = 0
    for value in frame[column].dropna().tolist():
        try:
            normalized = normalize_cnpj(value)
        except CNPJError:
            invalid += 1
            continue
        if normalized not in cnpjs:
            cnpjs.append(normalized)

    if not cnpjs:
        detail = "Nenhum CNPJ valido foi encontrado"
        if invalid:
            detail += f" ({invalid} linha(s) ignorada(s))"
        raise ValueError(detail + ".")
    return cnpjs


def export_results(path: str | Path, rows: list[dict[str, Any]]) -> None:
    pd.DataFrame(rows).to_excel(path, index=False)
