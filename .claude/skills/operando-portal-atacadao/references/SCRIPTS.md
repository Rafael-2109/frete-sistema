# Scripts — Portal Atacadao

**Caminho**: `.claude/skills/operando-portal-atacadao/scripts/`
**Invocacao**: `source .venv/bin/activate && python .claude/skills/operando-portal-atacadao/scripts/<script>.py [args]`

Os scripts ficam no diretorio da skill. Eles IMPORTAM de `app.portal.atacadao.*` (infraestrutura Flask) mas NAO vivem la.

---

## 0. atacadao_common.py — Biblioteca Compartilhada

**NAO executavel** — importado pelos demais scripts via `from atacadao_common import ...`

| Funcao | Descricao |
|--------|-----------|
| `verificar_credenciais_atacadao()` | Valida `ATACADAO_USUARIO` e `ATACADAO_SENHA` no `.env` |
| `carregar_defaults(path)` | Carrega `atacadao_defaults.json` |
| `criar_client_com_sessao(headless)` | Cria `AtacadaoPlaywrightClient` com storage_state |
| `criar_sessao_download(headless)` | Sessao Playwright com `accept_downloads=True` |
| `verificar_sessao_sync(page)` | Navega `/pedidos`, verifica se nao redirecionou para login |
| `capturar_screenshot(page, nome, dir)` | Screenshot em `/tmp/atacadao_operacoes/` |
| `gerar_saida(sucesso, **kwargs)` | JSON padronizado em stdout |
| `extrair_tabela(page, selector)` | Extrai tabela Vue do portal via JS eval |
| `extrair_tabela_com_paginacao(page, selector, max)` | Idem com paginacao |

**Storage state buscado em**: `{PROJECT_ROOT}/storage_state_atacadao.json` (raiz do projeto)

---

## 1. imprimir_pedidos.py

Imprime pedidos do portal como PDF — modo detalhe (um pedido) ou listagem (todos de um CNPJ).

### Parametros

| Argumento | Tipo | Obrigatorio | Descricao |
|-----------|------|-------------|-----------|
| `--pedido` | str | Pelo menos um dos dois | Nr. do pedido (1-8 digitos). Ex: `457652` |
| `--cnpj` | str | Pelo menos um dos dois | CNPJ da unidade (14 digitos). Ex: `75315333003043` |
| `--dry-run` | flag | Nao | Preview sem gerar PDF |

### Invocacao

```bash
# Detalhe de um pedido
python .claude/skills/operando-portal-atacadao/scripts/imprimir_pedidos.py --pedido 457652

# Listagem de um CNPJ
python .claude/skills/operando-portal-atacadao/scripts/imprimir_pedidos.py --cnpj 75315333003043

# Dry-run
python .claude/skills/operando-portal-atacadao/scripts/imprimir_pedidos.py --pedido 457652 --dry-run
```

### Output

```json
{"sucesso": true, "modo": "detalhe", "pdf_path": "/tmp/pedidos_atacadao/pedido_457652_20260323.pdf", "pdf_size_kb": 123.45}
```

### Dependencias

- `atacadao_common` (sessao, screenshot, saida JSON)
- **NAO** usa `create_app()` — sem acesso ao banco

---

## 2. consultar_agendamentos.py

Exporta CSV de agendamentos futuros por CNPJ. Opcionalmente cruza com sistema local.

### Parametros

| Argumento | Tipo | Obrigatorio | Descricao |
|-----------|------|-------------|-----------|
| `--cnpj` | str | **SIM** | CNPJ da unidade (14 digitos) |
| `--dias` | int | Nao (default: 45) | Nr. de dias futuros |
| `--dry-run` | flag | Nao | Preview sem acessar portal |
| `--cruzar-local` | flag | Nao | Cruza com Separacao + EntregaMonitorada locais |

### Invocacao

```bash
python .claude/skills/operando-portal-atacadao/scripts/consultar_agendamentos.py --cnpj 75315333003043
python .claude/skills/operando-portal-atacadao/scripts/consultar_agendamentos.py --cnpj 75315333003043 --dias 30 --cruzar-local
```

### Output

```json
{
  "sucesso": true,
  "total_registros": 42,
  "csv_path": "/tmp/agendamentos_atacadao/agendamentos_75315333003043_20260323.csv",
  "resumo": {"total": 42, "por_status": {"Aguardando check-in": 10}},
  "resumo_cruzamento": {"agendamento_disponivel": 5, "agenda_perdida": 2, "em_dia": 3, "entregue": 1, "sem_cruzamento": 0}
}
```

### Dependencias

- `atacadao_common` (sessao download, screenshot)
- `create_app()` — **apenas com `--cruzar-local`** (Separacao, EntregaMonitorada)
- URL: `/relatorio/itens`

---

## 3. consultar_saldo.py

Exporta CSV de saldo disponivel para agendamento. Opcionalmente cruza EAN com cadastro local.

### Parametros

| Argumento | Tipo | Obrigatorio | Descricao |
|-----------|------|-------------|-----------|
| `--cnpj` | str | Nao | Filtra por CNPJ. Sem ele = TODAS as filiais |
| `--filial` | str | Nao | Filtra por codigo de filial. Ex: `183` |
| `--cruzar-local` | flag | Nao | Cruza EAN com `CadastroPalletizacao.codigo_ean` |

### Invocacao

```bash
# Saldo de TODAS as filiais
python .claude/skills/operando-portal-atacadao/scripts/consultar_saldo.py

# Saldo de uma filial especifica
python .claude/skills/operando-portal-atacadao/scripts/consultar_saldo.py --filial 183

# Com cruzamento local (identifica produtos Nacom)
python .claude/skills/operando-portal-atacadao/scripts/consultar_saldo.py --cruzar-local
```

### Output

```json
{
  "sucesso": true,
  "total_registros": 15,
  "csv_path": "/tmp/saldo_atacadao/saldo_20260323.csv",
  "resumo": {"total_saldo": 1250, "total_produtos_distintos": 8, "por_filial": {"183": 850}},
  "cruzamento": {"com_match": 6, "sem_match": 2, "produtos_identificados": [{"ean": "17898...", "cod_produto": 12345}]}
}
```

### GOTCHAs

- `SALDO_MINIMO_VALIDO = 2`: saldo=1 sao pedidos fantasmas, filtrados automaticamente
- `PREFIXOS_EAN_INVALIDOS = ("000", "037", "37", "57")`: codigos internos do portal, nao EAN reais

### Dependencias

- `atacadao_common` (sessao download, screenshot)
- `create_app()` — **apenas com `--cruzar-local`** (CadastroPalletizacao)
- URL: `/relatorio/planilhaPedidos`

---

## 4. agendar_lote.py

Agendamento em lote via upload de planilha XLSX em `/cargas-planilha`. `--dry-run` OBRIGATORIO na primeira execucao.

### Parametros

**Modo 1 — A partir do CSV de saldo:**

| Argumento | Tipo | Obrigatorio | Descricao |
|-----------|------|-------------|-----------|
| `--saldo-csv` | str | Sim (modo 1) | CSV de saldo (output de `consultar_saldo.py`) |
| `--data` | str | Sim (modo 1) | Data(s) DD/MM/YYYY, multiplas separadas por virgula |
| `--veiculo` | str | Sim (modo 1) | Codigo do veiculo (ver tabela abaixo) |

**Modo 2 — Planilha pronta:**

| Argumento | Tipo | Obrigatorio | Descricao |
|-----------|------|-------------|-----------|
| `--planilha` | str | Sim (modo 2) | XLSX para upload direto |

**Filtros:**

| Argumento | Tipo | Default | Descricao |
|-----------|------|---------|-----------|
| `--ean` | str | None | Filtra saldo por EAN especifico |
| `--filial` | str | None | Filtra saldo por filial |

**Quantidade (override do saldo):**

| Argumento | Tipo | Default | Descricao |
|-----------|------|---------|-----------|
| `--qtd` | int | None | Qtd fixa em UNIDADES (mutuamente exclusivo com --pallets) |
| `--pallets` | int | None | Qtd em PALLETS → converte via CadastroPalletizacao (requer --ean) |

**Negocio:**

| Argumento | Tipo | Default | Descricao |
|-----------|------|---------|-----------|
| `--cnpj-cd` | str | `61724241000330` | CNPJ do CD (coluna B da planilha) |
| `--multiplicar` | int | 1 | Repetir agendamento N vezes (nr_carga incrementa) |
| `--dividir-por` | int | 1 | Dividir saldo por N |
| `--qtd-min-pallets` | int | None | Qtd minima de pallets (aceito mas NAO implementado — gap G1) |

**Execucao:**

| Argumento | Tipo | Default | Descricao |
|-----------|------|---------|-----------|
| `--dry-run` | flag | — | Validar no portal sem salvar (mutuamente exclusivo com --confirmar) |
| `--confirmar` | flag | — | Salvar agendamento (mutuamente exclusivo com --dry-run) |

### Invocacao

```bash
# Passo 1: gerar planilha + dry-run
python .claude/skills/operando-portal-atacadao/scripts/agendar_lote.py \
  --saldo-csv /tmp/saldo_atacadao/saldo.csv --data 31/03/2026 --veiculo 7 --dry-run

# Passo 2: confirmar
python .claude/skills/operando-portal-atacadao/scripts/agendar_lote.py \
  --planilha /tmp/agendamento_atacadao/agendamento.xlsx --confirmar

# Produto especifico: 10 pallets de um EAN para filial 183
python .claude/skills/operando-portal-atacadao/scripts/agendar_lote.py \
  --saldo-csv /tmp/saldo_atacadao/saldo.csv \
  --ean 17898075642344 --filial 183 --pallets 10 \
  --data 31/03/2026 --veiculo 7 --dry-run
```

### Output (dry-run)

```json
{
  "sucesso": true,
  "modo": "dry-run",
  "planilha_path": "/tmp/agendamento_atacadao/agendamento.xlsx",
  "validacao": {"validas": 15, "inconsistentes": 2, "detalhes_inconsistencias": [
    {"linha": 3, "motivo": "saldo insuficiente", "saldo_portal": 200, "saldo_parcial": true}
  ]}
}
```

### Output (confirmado)

```json
{
  "sucesso": true,
  "modo": "confirmado",
  "resultado": {"status": "agendado", "link_cargas": "https://atacadao.hodiebooking.com.br/cargas?controle=abc123", "controle": "abc123"}
}
```

### Dependencias

- `atacadao_common` (sessao download, screenshot)
- `create_app()` — **apenas com `--pallets`** (CadastroPalletizacao)
- URL: `/cargas-planilha`

---

## Tabela de Veiculos

| Cod. planilha | Veiculo | Max Pallets |
|---------------|---------|-------------|
| 1 | Kombi/Van | 5 |
| 3 | F4000-3/4 Bau | 10 |
| 4 | Toco-Bau | 24 |
| 5 | Truck-Bau | 75 |
| 6 | Truck-Sider | 75 |
| 7 | Carreta-Bau | 80 |
| 8 | Carreta-Sider | 80 |
| 9 | Carreta-Container | 56 |
| 2 | Carreta-Graneleira | 60 |
| 10 | Bitrem-Graneleiro | 56 |
| 11 | Rodotrem-Bau | 100 |
| 12 | Truck-Graneleiro | 32 |

**ATENCAO**: Max Pallets acima sao do PORTAL (capacidade fisica). O limite OPERACIONAL da Nacom e 30 pallets por carreta (regra de negocio em `REGRAS_P1_P7.md`).
