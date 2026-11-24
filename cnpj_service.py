from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import requests


CNPJ_LENGTH = 14
BRASIL_API_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"


class CNPJError(Exception):
    """Erro esperado ao consultar ou validar um CNPJ."""


@dataclass(frozen=True)
class CompanyResult:
    cnpj: str
    razao_social: str = ""
    nome_fantasia: str = ""
    situacao: str = ""
    municipio: str = ""
    uf: str = ""
    status: str = "Pendente"
    detalhe: str = ""


def normalize_cnpj(value: Any) -> str:
    """Retorna somente os 14 digitos do CNPJ ou falha com mensagem clara."""
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != CNPJ_LENGTH:
        raise CNPJError("CNPJ deve conter 14 digitos.")
    return digits


def format_cnpj(cnpj: str) -> str:
    digits = normalize_cnpj(cnpj)
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


class BrasilAPIClient:
    def __init__(self, timeout: int = 15, session: requests.Session | None = None) -> None:
        self.timeout = timeout
        self.session = session or requests.Session()

    def lookup(self, cnpj: str) -> CompanyResult:
        normalized = normalize_cnpj(cnpj)
        try:
            response = self.session.get(
                BRASIL_API_URL.format(cnpj=normalized),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise CNPJError(f"Falha de conexao: {exc}") from exc

        if response.status_code == 404:
            raise CNPJError("CNPJ nao encontrado.")
        if response.status_code == 429:
            raise CNPJError("Limite da API atingido. Tente novamente em instantes.")
        if response.status_code >= 400:
            raise CNPJError(f"API retornou HTTP {response.status_code}.")

        try:
            data: dict[str, Any] = response.json()
        except ValueError as exc:
            raise CNPJError("A API retornou uma resposta invalida.") from exc

        return CompanyResult(
            cnpj=format_cnpj(normalized),
            razao_social=str(data.get("razao_social") or ""),
            nome_fantasia=str(data.get("nome_fantasia") or ""),
            situacao=str(data.get("descricao_situacao_cadastral") or ""),
            municipio=str(data.get("municipio") or ""),
            uf=str(data.get("uf") or ""),
            status="Encontrado",
        )
