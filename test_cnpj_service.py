from unittest.mock import Mock

import pytest

from cnpj_service import BrasilAPIClient, CNPJError, format_cnpj, normalize_cnpj


def test_normalize_and_format_cnpj():
    assert normalize_cnpj("04.252.011/0001-10") == "04252011000110"
    assert format_cnpj("04252011000110") == "04.252.011/0001-10"


def test_invalid_cnpj_is_rejected():
    with pytest.raises(CNPJError, match="14 digitos"):
        normalize_cnpj("123")


def test_lookup_maps_company_fields():
    response = Mock(status_code=200)
    response.json.return_value = {
        "razao_social": "Empresa Exemplo LTDA",
        "nome_fantasia": "Exemplo",
        "descricao_situacao_cadastral": "ATIVA",
        "municipio": "Sao Paulo",
        "uf": "SP",
    }
    session = Mock()
    session.get.return_value = response

    result = BrasilAPIClient(session=session).lookup("04.252.011/0001-10")

    assert result.razao_social == "Empresa Exemplo LTDA"
    assert result.status == "Encontrado"
    session.get.assert_called_once()


def test_lookup_handles_not_found():
    response = Mock(status_code=404)
    session = Mock()
    session.get.return_value = response

    with pytest.raises(CNPJError, match="nao encontrado"):
        BrasilAPIClient(session=session).lookup("04.252.011/0001-10")
