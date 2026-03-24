---
name: operando-portal-atacadao
description: >-
  Automacao do PORTAL WEB Atacadao (Hodie Booking, hodiebooking.com.br) via
  Playwright. Use apenas quando o usuario mencionar explicitamente o portal,
  site, ou Hodie Booking do Atacadao. A solicitacao precisa conter "Atacadao"
  combinado com "portal", "site", "Hodie", "hodiebooking", ou verbo que
  implique navegacao web ("abrir", "navegar", "acessar", "entrar no").
  Exemplos que trigam: "imprimir protocolo no portal Atacadao",
  "ver agendamentos no site do Atacadao", "agendar entrega no portal
  Atacadao", "abrir portal do Atacadao", "navegar no Hodie Booking",
  "entrar no site Atacadao e ver pedidos", "acessar o portal pra imprimir".
  Exemplos que nao trigam (sem mencao ao portal): "consultar saldo
  Atacadao", "verificar agendamento Atacadao", "pedidos do Atacadao" —
  resolvidas localmente por gerindo-expedicao, monitorando-entregas ou
  consultando-sql. NAO USAR para CarVia (gerindo-carvia), SSW
  (operando-ssw), ou dados locais sem portal.
allowed-tools: Read, Bash, Glob, Grep
---

# operando-portal-atacadao

Executa operacoes no **portal Atacadao** (Hodie Booking) via scripts Playwright standalone.
Portal: `https://atacadao.hodiebooking.com.br`

---

## WORKFLOW OBRIGATORIO (seguir SEMPRE, nesta ordem)

```
PASSO 1 — VERIFICAR SESSAO (ANTES de qualquer script)
  Executar: ls -la app/portal/atacadao/storage_state_atacadao.json
  Se NAO existe ou tamanho 0 → PARAR. Informar:
    "Sessao expirada. Execute: python -m app.portal.atacadao.login_interativo"
  Se existe → prosseguir

PASSO 2 — EXECUTAR SCRIPT
  Rodar o script com argumentos corretos (ver Decision Tree)
  Para agendar_lote.py: SEMPRE --dry-run primeiro, MESMO que usuario peca "direto"

PASSO 3 — REPORTAR OUTPUT (campos obrigatorios por script)
  Apresentar ao usuario os campos-chave do JSON de saida (ver REGRAS DE REPORT)
  NUNCA parafrasear, inventar ou omitir campos do JSON
```

**VIOLAR ESTA ORDEM = EVAL FAIL**

## REGRAS CRITICAS

1. Sessao **OBRIGATORIA** — verificar `storage_state_atacadao.json` ANTES de executar qualquer script (Passo 1)
2. Se sessao expirada, **PARAR IMEDIATAMENTE** e informar o comando exato:
   `python -m app.portal.atacadao.login_interativo`
   NAO tentar executar scripts com sessao expirada. NAO tentar automatizar login (CAPTCHA).
3. `--dry-run` e **OBRIGATORIO** na primeira execucao de `agendar_lote.py` — MESMO que usuario peca "direto"
4. Screenshot capturado **ANTES** de qualquer submit destrutivo — evidencia do formulario
5. Agente DEVE usar AskUserQuestion para confirmar antes de agendar sem --dry-run
6. NUNCA inventar protocolos, pedidos ou dados — usar EXATAMENTE o que o portal retorna
7. De-Para de produtos (`ProdutoDeParaAtacadao`) deve estar completo ANTES de agendar

## REGRAS DE REPORT (Passo 3 — campos obrigatorios)

Ao apresentar resultados, CITAR estes campos do JSON de saida de cada script:

### imprimir_pedidos.py
- `modo`: "detalhe" ou "listagem" — informar qual modo foi usado
- `pdf_path`: caminho completo do PDF gerado em `/tmp/pedidos_atacadao/`
- `pdf_size_kb`: tamanho do arquivo
- Se `sucesso=false`: citar o campo `erro` e NAO inventar dados

### impressao_protocolo.py (GeradorPDFProtocoloAtacadao)
- `pdf_path`: caminho completo do PDF em `/tmp/protocolos_atacadao/`
- Gerar um PDF por protocolo (iterar se multiplos)

### consultar_agendamentos.py
- `total_registros`: numero total de registros
- `csv_path`: caminho do CSV exportado
- `resumo.por_status`: apresentar contadores EXATAMENTE como retornados (NAO inventar status)
- `periodo.de` e `periodo.ate`: periodo consultado
- Se `--cruzar-local`: citar `resumo_cruzamento` com TODOS os contadores:
  `agendamento_disponivel`, `agenda_perdida`, `em_dia`, `entregue`, `sem_cruzamento`
- Se `--cruzar-local`: citar `total_separacoes_local` e `total_entregas_local`

### consultar_saldo.py
- `total_registros`: numero total de linhas do CSV
- `csv_path`: caminho do CSV exportado em `/tmp/saldo_atacadao/`
- `resumo.total_produtos_distintos`: quantos EANs unicos
- `resumo.total_saldo`: soma de todo saldo disponivel
- `resumo.por_filial`: saldo agrupado por filial
- Se `--cruzar-local`: citar `cruzamento.com_match`, `cruzamento.sem_match`
- Se `--cruzar-local`: listar `cruzamento.produtos_identificados` (EAN → cod_produto)

### agendar_lote.py
- Se `modo=preview`: informar `planilha_path` e instrucao para proximo passo
- Se `modo=dry-run`: citar `validacao.validas`, `validacao.inconsistentes`
  - Se inconsistentes > 0: listar `validacao.detalhes_inconsistencias` (linha, motivo, dados)
  - Cada inconsistencia inclui `saldo_portal` (qtd real no portal) e `saldo_parcial` (bool)
  - Se `saldo_parcial=True`: informar ao usuario que existe saldo parcial (ex: "EAN X tem saldo de 200, voce solicitou 700. Quer agendar com 200?")
  - Se `saldo_portal=0` para todos: informar "nenhum item tem saldo disponivel no portal"
  - Se tudo valido: informar comando para confirmar
- Se `modo=confirmado`: citar `resultado.status`, `resultado.link_cargas`, `resultado.controle`
- **SEMPRE** executar --dry-run primeiro, MESMO que usuario peca "direto"
- AskUserQuestion antes de --confirmar

## ANTI-ALUCINACAO

- **Protocolos**: Sempre numeros inteiros capturados do portal. NAO inventar.
- **Produtos**: Codigos do Atacadao != nossos codigos. Sempre usar De-Para.
- **Status**: EXATAMENTE o texto do portal (ex: "Aguardando aprovacao"). NAO traduzir.
- **Resultados do script**: Apresentar EXATAMENTE o que o JSON de saida retorna (ver REGRAS DE REPORT).
- **Sessao**: Portal tem CAPTCHA. Re-login NAO pode ser automatizado. Comando: `python -m app.portal.atacadao.login_interativo`
- **CSV do portal**: Colunas do CSV podem mudar. NAO assumir nomes de colunas — usar os que o script retorna em `registros[0].keys()`.
- **Fidelidade ao output**: Ao reportar resultados, citar valores EXATAMENTE do JSON de saida. NAO parafrasear status, NAO inventar contadores, NAO arredondar valores.
- **Sessao expirada**: Se script falha ou retorna erro de sessao, NAO tentar novamente. PARAR e pedir re-login.

## GLOSSARIO

| Termo | Significado |
|-------|-------------|
| **protocolo** | Numero inteiro = senha de agendamento no portal. NAO confundir com pedido. |
| **agenda_perdida** | Agendamento cuja `data_agendamento < hoje` E sem NF emitida. Indica entrega que perdeu a janela. |
| **agendamento_disponivel** | Agendamento com data futura E com separacao local associada. |
| **em_dia** | Agendamento com data futura mas sem separacao local (ok, ainda ha tempo). |
| **entregue** | Agendamento que ja tem NF/entrega confirmada no sistema local. |
| **sem_cruzamento** | Agendamento do portal sem correspondencia no sistema local. |
| **De-Para** | `ProdutoDeParaAtacadao` — mapeia codigo Atacadao → codigo interno. OBRIGATORIO antes de agendar. |
| **storage_state** | `storage_state_atacadao.json` — cookies/sessao do Playwright. Requer re-login quando expira. |

### Mapeamento CSV do Relatorio → Sistema Local

O CSV exportado de `/relatorio/itens` tem colunas com nomes diferentes do nosso sistema:

| Coluna CSV Portal | Equivalente no Sistema | CUIDADO |
|-------------------|----------------------|---------|
| `Agendamento` (col ~16) | protocolo (separacao.protocolo) | NAO usar coluna "Protocolo" do CSV — pode ser outro campo |
| `Data Agendamento` (col ~15) | data agendada (agendamentos_entrega.data_agendada) | NAO usar "Data Desejada" |
| `Status` | status do agendamento | Valores EXATOS do portal, ex: "Aguardando check-in" = valido/nao recebido |
| `Codigo` | PODE ser duplicado por item | NAO usar como chave unica |
| `Embarque` | mascarado pelo portal | NAO confundir com embarque.id do sistema |

## TRATAMENTO DE ERROS

| Erro | Causa | Acao |
|------|-------|------|
| `RuntimeError: sessao expirada` | Storage state invalido | Pedir re-login interativo |
| Redirecionamento para /login | Sessao expirou | Idem |
| Timeout ao carregar tabela | Portal lento | Aumentar timeout, tentar novamente |
| `Produto sem De-Para` | Mapeamento incompleto | Listar produtos faltantes, NAO agendar |
| `Botao nao encontrado` | Seletores mudaram | Verificar `PORTAL_NAVEGACAO.md`, atualizar config |
| Timeout no download CSV | Portal lento ou sem dados | Reportar erro, sugerir reduzir --dias |
| CSV vazio (0 registros) | Sem agendamentos no periodo | Reportar claramente "0 registros", NAO inventar dados |
| Erro no cruzamento local | Tabela/coluna ausente | Reportar cruzamento_erro, manter dados do portal |

---

## Decision Tree

**Todos os scripts ficam em `.claude/skills/operando-portal-atacadao/scripts/`.**
**Invocacao**: `source .venv/bin/activate && python .claude/skills/operando-portal-atacadao/scripts/<script>.py [args]`

```
Imprimir PEDIDO(s) do portal? (detalhe ou listagem)
  -> Resolver filial para CNPJ: resolvendo-entidades (se usuario passou nome/numero de filial)
  -> Modo detalhe:
     python .claude/skills/operando-portal-atacadao/scripts/imprimir_pedidos.py --pedido 457652 [--cnpj 75315333003043] [--dry-run]
  -> Modo listagem:
     python .claude/skills/operando-portal-atacadao/scripts/imprimir_pedidos.py --cnpj 75315333003043 [--dry-run]
  -> Gera PDF em /tmp/pedidos_atacadao/
  -> Output: {"sucesso": true, "modo": "detalhe"|"listagem", "pdf_path": "...", "pdf_size_kb": N}

Imprimir PROTOCOLO(s) de agendamento? (senha de entrega)
  -> NAO usar imprimir_pedidos.py — usar impressao_protocolo.py diretamente
  -> from app.portal.atacadao.impressao_protocolo import gerar_pdf_protocolo_atacadao
  -> gerar_pdf_protocolo_atacadao(protocolo="12345")
  -> Gera PDF em /tmp/protocolos_atacadao/
  -> DISTINCAO: protocolo = senha de agendamento (numero inteiro). Pedido = numero do pedido no portal.

Consultar agendamentos futuros de um CNPJ?
  -> python .claude/skills/operando-portal-atacadao/scripts/consultar_agendamentos.py --cnpj 12345678000190 [--dias 30] [--cruzar-local]
  -> Sem --cruzar-local: exporta CSV + retorna registros e resumo por_status
  -> Com --cruzar-local: adiciona resumo_cruzamento com contadores:
     agendamento_disponivel, agenda_perdida, em_dia, entregue, sem_cruzamento
  -> Output: {"sucesso": true, "total_registros": N, "csv_path": "...",
              "resumo": {"total": N, "por_status": {...}},
              "resumo_cruzamento": {...} (se --cruzar-local)}

Consultar saldo disponivel para agendamento?
  -> python .claude/skills/operando-portal-atacadao/scripts/consultar_saldo.py [--cnpj 75315333003043] [--filial 183] [--cruzar-local]
  -> Sem --cnpj: exporta saldo de TODAS as filiais
  -> Com --cnpj: filtra resultados por CNPJ do fornecedor
  -> Com --filial: filtra resultados por codigo de filial (loja Atacadao)
  -> Com --cruzar-local: cruza EAN do CSV com CadastroPalletizacao.codigo_ean
     para identificar cod_produto Nacom → util antes de agendar
  -> Output: {"sucesso": true, "total_registros": N, "csv_path": "...",
              "resumo": {"total_saldo": N, "por_filial": {...}},
              "cruzamento": {"com_match": N, "sem_match": N} (se --cruzar-local)}

Agendar entrega em lote (TODOS os produtos/filiais)?
  -> PASSO 1:
     python .claude/skills/operando-portal-atacadao/scripts/consultar_saldo.py --cruzar-local
  -> PASSO 2:
     python .claude/skills/operando-portal-atacadao/scripts/agendar_lote.py \
       --saldo-csv /tmp/saldo_atacadao/saldo.csv --data DD/MM/YYYY --veiculo 7 --dry-run
     Parametros opcionais: --multiplicar N, --dividir-por N, --cnpj-cd CNPJ
  -> PASSO 3: Reportar validacao (validas/inconsistentes)
  -> PASSO 4: AskUserQuestion: "Confirmar agendamento de N linhas para DD/MM/YYYY?"
  -> PASSO 5:
     python .claude/skills/operando-portal-atacadao/scripts/agendar_lote.py \
       --planilha /tmp/agendamento_atacadao/agendamento.xlsx --confirmar
  -> OU: usuario pode preparar planilha manualmente e usar --planilha diretamente

Agendar produto ESPECIFICO? (ex: "10 pallets de palmito pro Atacadao de Jacarei dia 24/3")
  -> PRE-PASSO: Resolver entidades (se usuario informou nome de produto, nao EAN)
     a) resolvendo-entidades: nome do produto → cod_produto + EAN
        Ex: "AZ VI 500 campo belo" → cod_produto=12345, EAN=17898075642344
     b) Se filial informada por nome de cidade:
        consultar_saldo.py --cruzar-local → verificar quais filiais tem o EAN
        e identificar o codigo de filial correspondente a cidade (ex: Jacarei=filial 183)
        NOTA: o portal so tem codigos de filial (numeros), nao nomes de cidade.
        Se nao conseguir resolver, AskUserQuestion com as filiais disponiveis.
  -> PASSO 1:
     python .claude/skills/operando-portal-atacadao/scripts/consultar_saldo.py --filial <CODIGO> --cruzar-local
  -> PASSO 2:
     python .claude/skills/operando-portal-atacadao/scripts/agendar_lote.py \
       --saldo-csv /tmp/saldo_atacadao/saldo.csv \
       --ean <EAN> --filial <CODIGO> --pallets 10 \
       --data 24/03/2026,25/03/2026,26/03/2026 --veiculo 7 --dry-run
     Notas:
       --ean: filtra saldo para um EAN especifico
       --filial: filtra saldo para uma filial especifica
       --pallets N: converte N pallets → unidades via cadastro_palletizacao
       --qtd N: alternativa em unidades (sem conversao)
       --data: aceita virgula para multiplas datas (uma planilha com varias linhas)
       --veiculo: codigo do veiculo na planilha (7=Carreta-Bau padrao)
  -> PASSO 3: Reportar validacao (validas/inconsistentes) + qtd convertida em unidades
  -> PASSO 4: AskUserQuestion: "Confirmar agendamento?"
  -> PASSO 5:
     python .claude/skills/operando-portal-atacadao/scripts/agendar_lote.py \
       --planilha /tmp/agendamento_atacadao/agendamento.xlsx --confirmar

Sessao expirada? (detectada no Passo 1 ou por erro do script)
  -> PARAR IMEDIATAMENTE. NAO tentar executar mais scripts.
  -> Informar ao usuario: "Sessao expirada. Execute no terminal:
     python -m app.portal.atacadao.login_interativo
     Depois repita a solicitacao."
  -> NAO tentar automatizar login (portal tem CAPTCHA)

Consultar dados de agendamento SEM acessar portal?
  -> NAO usar esta skill. Usar consultando-sql ou gerindo-expedicao
```

---

## Arquitetura

### Onde ficam os scripts

```
.claude/skills/operando-portal-atacadao/scripts/   ← SCRIPTS EXECUTAVEIS (5 arquivos)
app/portal/atacadao/                                ← INFRAESTRUTURA Flask (reutilizada pelos scripts)
```

Scripts ficam no diretorio da skill, NAO em `app/portal/atacadao/`.
Eles IMPORTAM de `app.portal.atacadao.*` mas NAO vivem la.

### Invocacao

```bash
# Todos os scripts sao invocados assim (da raiz do projeto):
source .venv/bin/activate && python .claude/skills/operando-portal-atacadao/scripts/<script>.py [args]

# Exemplo:
python .claude/skills/operando-portal-atacadao/scripts/consultar_saldo.py --cruzar-local
```

### Workflow

```
Agente Web — SEGUIR EXATAMENTE ESTA ORDEM:
  1. VERIFICAR SESSAO: ls -la storage_state_atacadao.json
     Se nao existe → PARAR, pedir: python -m app.portal.atacadao.login_interativo
  2. Resolver parametros (CNPJ, pedido) — usar resolvendo-entidades se necessario
  3. Executar script com argumentos corretos (ver Decision Tree)
     Se agendar_lote.py → SEMPRE --dry-run primeiro
  4. REPORTAR campos-chave do JSON de saida (ver REGRAS DE REPORT)
     NUNCA omitir pdf_path, modo, total_registros, csv_path, etc.
  5. Se destrutivo: AskUserQuestion ("Confirmar execucao?") + mostrar preview
  6. Se confirmado: executar sem --dry-run
```

Scripts sao standalone (Playwright sync), importam de `app.portal.atacadao.*`.
Requerem `create_app()` + `app.app_context()` quando acessam banco (--cruzar-local, --pallets).
Ref completa de parametros: `references/SCRIPTS.md`

---

## Scripts

**Caminho**: `.claude/skills/operando-portal-atacadao/scripts/`
**Ref completa** (parametros, output, dependencias): `references/SCRIPTS.md`

| # | Script | Proposito | Status |
|---|--------|-----------|--------|
| 0 | `atacadao_common.py` | Biblioteca compartilhada (sessao, download, screenshot, saida JSON) — NAO executavel | IMPLEMENTADO |
| 1 | `imprimir_pedidos.py` | Imprimir pedidos como PDF — detalhe (--pedido) ou listagem (--cnpj) | IMPLEMENTADO |
| 2 | `consultar_agendamentos.py` | Export CSV de agendamentos futuros por CNPJ, cruzamento local opcional | IMPLEMENTADO |
| 3 | `consultar_saldo.py` | Export CSV de saldo disponivel de /relatorio/planilhaPedidos, cruzamento com EAN local opcional | IMPLEMENTADO |
| 4 | `agendar_lote.py` | Agendamento em lote via upload de planilha XLSX em /cargas-planilha (--dry-run obrigatorio) | IMPLEMENTADO |

---

## Infraestrutura Existente (reutilizada)

| Arquivo | Papel | Usado por |
|---------|-------|-----------|
| `app/portal/atacadao/config.py` | URLs, seletores, veiculos, timeouts | Todos |
| `app/portal/atacadao/playwright_client.py` | AtacadaoPlaywrightClient (sync, ~700 LOC) | Todos |
| `app/portal/atacadao/login_interativo.py` | Login com CAPTCHA, re-login | Sessao |
| `app/portal/atacadao/impressao_protocolo.py` | GeradorPDFProtocoloAtacadao (protocolos, NAO pedidos) | Impressao de protocolos |
| `app/portal/atacadao/verificacao_protocolo.py` | VerificadorProtocoloAtacadao | Script 2 |
| `app/portal/atacadao/models.py` | ProdutoDeParaAtacadao | Scripts 3, 4 |
| `app/portal/atacadao/routes_agendamento.py` | Rotas Flask (preparar, gravar, confirmar) | Script 4 |

---

## MCP Tool

| Tool | Proposito |
|------|-----------|
| `browser_atacadao_login` (C5) | Carrega sessao Atacadao no browser MCP, verifica validade |

---

## References (carregar sob demanda)

| Quando o agente precisa de... | Ler |
|-------------------------------|-----|
| **Parametros, invocacao e output dos scripts** | [SCRIPTS.md](references/SCRIPTS.md) |
| Seletores e caminhos do portal | [PORTAL_NAVEGACAO.md](references/PORTAL_NAVEGACAO.md) |
| URLs, veiculos, timeouts padrao | `atacadao_defaults.json` |
| Config existente (seletores) | `app/portal/atacadao/config.py` |
