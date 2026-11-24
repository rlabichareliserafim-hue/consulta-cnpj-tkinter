# CNPJ Radar

Automação de dados com Python para importar uma lista de CNPJs, consultar informações cadastrais pela BrasilAPI e exportar os resultados em Excel.

Projeto de portfólio de Rafael Augusto Labichareli Serafim — Dados, BI e Automação de Processos.

## Problema e solução

Enriquecer uma base de empresas manualmente exige repetir consultas e copiar informações. O CNPJ Radar organiza esse processo em importação, normalização dos identificadores, remoção de duplicatas, consulta HTTP e exportação para análise posterior.

A interface permite acompanhar o progresso e pausar as consultas. Erros individuais são registrados sem interromper o restante do lote. Não foram medidos ganhos de produtividade em produção.

## Dados exportados

- `cnpj`: identificador formatado.
- `razao` e `fantasia`: razão social e nome fantasia.
- `situacao`: situação cadastral informada pela API.
- `local`: município e UF.
- `status`: resultado da consulta, como Encontrado ou Erro.
- `detalhe`: mensagem associada a uma falha.

Situação cadastral e status da consulta são campos distintos. A fonte utilizada é a BrasilAPI; o aplicativo não consulta diretamente uma API oficial da Receita Federal e não é um produto oficial desse órgão.

## Competências demonstradas

Python, pandas, integração REST com requests, tratamento de dados tabulares, exportação com openpyxl e testes com respostas HTTP simuladas. CustomTkinter fornece a interface de operação.

## Organização

- `app.py`: interface e processamento das consultas em segundo plano.
- `cnpj_service.py`: normalização, formatação e acesso à API.
- `spreadsheet.py`: leitura, remoção de duplicatas e exportação.
- `test_cnpj_service.py`: testes unitários sem consultas reais.

## Limitações e privacidade

- A normalização aceita apenas CNPJs numéricos de 14 dígitos e não verifica seus dígitos verificadores. Formatos alfanuméricos não são suportados.
- CSV utiliza vírgula como separador nesta versão; preserve a coluna CNPJ como texto para manter zeros à esquerda.
- A leitura de XLS exige instalar `xlrd` adicionalmente. XLSX e CSV usam os requisitos fornecidos.
- Disponibilidade, atualização dos dados e limites de consulta dependem da BrasilAPI. Erros de limite são registrados, sem nova tentativa automática.
- Os testes atuais cobrem o serviço de consulta, não toda a interface.
- As consultas enviam os CNPJs importados à BrasilAPI. O código não exige token; planilhas e resultados locais não são incluídos no repositório.

## Requisitos

- Python 3.11 ou superior
- Internet para realizar as consultas

## Instalação

No PowerShell, a partir desta pasta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Execução

```powershell
python app.py
```

A planilha deve ser CSV, XLS ou XLSX e conter uma coluna chamada `CNPJ`. Linhas inválidas são ignoradas e CNPJs repetidos são consultados apenas uma vez. O resultado pode ser exportado para XLSX.

A consulta usa a BrasilAPI, que disponibiliza dados públicos de CNPJ. O serviço pode impor limites de uso; o aplicativo informa erros individuais sem interromper o lote inteiro.

## Testes

```powershell
pytest -q
```
