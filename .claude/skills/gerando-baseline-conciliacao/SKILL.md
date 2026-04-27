---
name: gerando-baseline-conciliacao
description: >-
  Esta skill deve ser usada quando o usuario Marcus (user_id=18, Controller
  Financeiro) ou outro usuario financeiro pedir "atualizar baseline", "baseline
  de conciliacao", "foto das conciliacoes", "foto atual das conciliacoes",
  "extratos pendentes por mes", "gerar baseline" ou "relatorio de extratos
  pendentes". Gera Excel com 4 abas canonicas (Pendentes Mes x Journal,
  Pendentes, Conciliacoes Dia Anterior, Resumo) usando dados diretos do Odoo
  account.bank.statement.line com is_reconciled=False.

  NAO USAR QUANDO:
  - Conciliacao de linhas individuais no Odoo, usar **executando-odoo-financeiro**
  - Transferencias internas entre bancos NACOM GOYA, usar **conciliando-transferencias-internas**
  - Rastrear extrato ou pagamento individual, usar **rastreando-odoo**
  - Exportar razao geral contabil, usar **razao-geral-odoo**
  - Baseline de CarVia (frete), usar **gerindo-carvia**
  - Cotacao de frete, usar **cotando-frete**
allowed-tools: Read, Bash, Glob, Grep
---

## Quando NAO Usar Esta Skill

| Situacao | Skill Correta | Por que? |
|----------|--------------|----------|
| Conciliar extrato individual | **executando-odoo-financeiro** | Esta skill APENAS gera relatorio, nao executa conciliacao |
| Transferencia interna entre bancos NACOM GOYA | **conciliando-transferencias-internas** | Fluxo especifico de is_internal_transfer |
| Rastrear pagamento ou NF | **rastreando-odoo** | Pipeline documental, nao relatorio agregado |
| Exportar balancete/razao | **razao-geral-odoo** | Contabilidade geral, nao extratos |

---

# Gerando Baseline de Conciliacao

Skill para gerar o **baseline canonico de extratos pendentes de conciliacao** no formato travado pelo Marcus (user_id=18, Controller Financeiro Nacom Goya).

## REGRAS ANTI-ALUCINACAO

```
NUNCA FAZER:
- NUNCA usar tabela local extrato_item como fonte (acumula linhas ja conciliadas)
- NUNCA calcular PGTOS/RECEB usando payment_id IS NOT NULL (retorna zero)
- NUNCA gerar layout com colunas ou abas diferentes do canonico sem autorizacao
- NUNCA usar SYNC_ODOO_WRITE_DATE como nome de usuario em D-1
- NUNCA inventar SQL — usar apenas queries documentadas em references/SQL_ODOO.md
- NUNCA omitir a aba "Conciliacoes Dia Anterior" ou a secao "Evolucao Baseline"

SEMPRE FAZER:
- SEMPRE consultar Odoo account.bank.statement.line com is_reconciled=False
- SEMPRE usar sinal do amount: PGTOS=count(amount<0), RECEB=count(amount>0)
- SEMPRE usar nomes reais via write_uid para aba D-1
- SEMPRE gerar exatamente 4 abas nos nomes canonicos
- SEMPRE validar os 5 checkpoints antes de entregar (ver Checkpoints)
```

## Formato Canonico (travado em preferences.xml do Marcus)

Nome do arquivo: `extratos_pendentes_mes_journal_<DDmmmYYYY>.xlsx`

### 4 Abas obrigatorias

1. **Pendentes Mes x Journal** (posicao 1)
2. **Pendentes** (posicao 2)
3. **Conciliacoes Dia Anterior** (posicao 3)
4. **Resumo** (posicao 4)

Detalhes por aba: `references/FORMATO_ABAS.md`.

## Fontes de Dados

| Aba | Fonte Primaria | Complementos |
|-----|---------------|--------------|
| 1 (Mes x Journal) | Odoo `account.bank.statement.line` WHERE `is_reconciled=False` | — |
| 2 (Pendentes) | Mesma da 1, mas por linha individual | — |
| 3 (Conciliacoes D-1) | Odoo `account.bank.statement.line` conciliadas em D-1 | UNIAO com `lancamento_comprovante`. NAO incluir `carvia_conciliacoes` — baseline e exclusiva Nacom Goya |
| 4 (Resumo) | Pivot sobre aba 1 | — |

SQL completo: `references/SQL_ODOO.md`.

## Armadilhas documentadas

Ver `references/ARMADILHAS.md` — 8 armadilhas ja cometidas pelo agente em sessoes anteriores.

## Fluxo de Execucao

```
1. Detectar gatilho: "atualizar baseline" / "baseline de conciliacao" / etc.
2. Confirmar data de referencia (default: hoje).
3. Rodar scripts/gerar_baseline.py com a data.
4. Script:
   a. Executa 4 queries contra Odoo (ver SQL_ODOO.md).
   b. Monta Excel openpyxl seguindo FORMATO_ABAS.md.
   c. Salva em /tmp/ e retorna URL de download.
5. Validar 5 checkpoints antes de responder (ver Checkpoints).
6. POS-EXECUCAO OBRIGATORIA (ver "Apresentacao Pos-Geracao Obrigatoria" abaixo).
7. Se usuario pedir variacao: RECUSAR e pedir autorizacao explicita.
```

## Pre-Execucao Obrigatoria

ANTES de invocar `gerar_baseline.py`, o agente DEVE consultar a memoria persistente para
garantir consistencia com o formato/historico ja acordado com o usuario:

| # | Acao | Tool / Path | Por que |
|---|------|-------------|---------|
| 1 | Ler preferencia de formato do Marcus | `view_memories(path="/memories/preferences.xml")` (user_id=18) — secao `<preference name="baseline_conciliacoes">` | Confirma 4 abas canonicas, colunas, ordenacao, rodapes; evita gerar layout divergente |
| 2 | Ler heuristica empresa nivel 5 | `view_memories(path="/memories/empresa/heuristicas/financeiro/baseline-de-extratos-formato-fixo.xml")` | Reforca regras anti-alucinacao (sinal do amount, NAO usar tabela local, etc.) |
| 3 | Ler historico acumulado de evolucao | Tabela `## Historico de baseline` no fim deste SKILL.md + secao "Evolucao Baseline" do ultimo Excel | Garante que a nova linha de evolucao (`<data> | <total> | delta=<delta>`) seja appendada ao historico cumulativo, NAO substitua |
| 4 | Verificar preferencias de apresentacao | `view_memories(path="/memories/preferences.xml")` — campos `apresentacao_chat`, `formato_combinado` se existirem | Captura ajustes recentes (ex.: ordem das tabelas, colunas adicionais) feitos em sessoes anteriores |

**REGRA**: Se a memoria (1) ou (2) NAO existir ou estiver incompleta, REPORTAR ao usuario
antes de gerar — NAO seguir adiante com defaults. Memorias quebradas indicam desalinhamento
de contrato.

**SINAL DE FRICCAO**: Se o usuario disser "atualizar com base no formato que haviamos
combinado" ou "verificar a solicitacao anterior" APOS o baseline ja ter sido entregue, isso
indica que esta secao foi pulada — registrar como pitfall via `log_system_pitfall`.

## Apresentacao Pos-Geracao Obrigatoria

APOS gerar o Excel e ANTES de encerrar a resposta, o agente DEVE apresentar AUTOMATICAMENTE
no chat (sem aguardar segunda solicitacao do usuario):

### Tabela 1 — Pendentes Mes x Journal (resumo da Aba 1)

Markdown table com as colunas: `Mes | Journal | Linhas | PGTOS | RECEB.` para todas as
combinacoes mes+journal (mesma fonte que alimenta a Aba 1 do Excel). Linha TOTAL no fim.

```
| Mes      | Journal         | Linhas | PGTOS | RECEB. |
|----------|-----------------|--------|-------|--------|
| 04/2026  | SICOOB          | 200    | 150   | 50     |
| ...      | ...             | ...    | ...   | ...    |
| **TOTAL**|                 | 6.350  | 4.800 | 1.550  |
```

### Tabela 2 — Conciliacoes D-1 por usuario (resumo da Aba 3)

Markdown table com as colunas: `Usuario | Linhas | Pgtos | Rec` ordenado por linhas DESC.
Linha TOTAL no fim. Se nenhuma conciliacao em D-1, exibir explicitamente: "Nenhuma
conciliacao registrada em <data>".

```
| Usuario          | Linhas | Pgtos | Rec |
|------------------|--------|-------|-----|
| Marcus Lima      | 80     | 60    | 20  |
| Joao Silva       | 30     | 25    | 5   |
| **TOTAL**        | 134    | 100   | 34  |
```

### Mensagem-template para o chat

```
Baseline canonico gerado: <URL_DOWNLOAD_EXCEL>
Total de extratos pendentes: <N> (delta vs baseline anterior: <DELTA>)

Pendentes por Mes x Journal:
<TABELA_1_MARKDOWN>

Conciliacoes em D-1 (<DATA_REFERENCIA - 1>) por usuario:
<TABELA_2_MARKDOWN>

Arquivo Excel completo (4 abas) disponivel para download no link acima.
```

**REGRA**: NUNCA entregar APENAS o link do Excel sem essas duas tabelas inline. O usuario
ja sinalizou (sessao `feda2aa9-5623-4977-9a19-fa070bbaab2c`, 26/04/2026) que omitir as
tabelas forca uma segunda rodada de pergunta — fluxo redundante deve ser eliminado.

**SINAL DE FRICCAO**: Se o usuario perguntar "e as tabelas?" ou "verificar a solicitacao
anterior" apos o link do Excel ter sido enviado, isso indica que esta secao foi pulada —
registrar como pitfall via `log_system_pitfall`.

## 5 Checkpoints de validacao

ANTES de entregar o arquivo ao usuario, confirmar mentalmente:

| # | Checkpoint | Como verificar |
|---|------------|----------------|
| 1 | Fonte = Odoo `is_reconciled=False` (NAO tabela local) | Linha do SQL tem `is_reconciled=False` |
| 2 | Valor Debitos = negativo (nao abs) | Formula do Excel mantem sinal |
| 3 | Aba 3 usa write_uid real (NAO SYNC_*) | SELECT join com res_users.name |
| 4 | 4 abas nos nomes EXATOS | `wb.sheetnames == ["Pendentes Mes x Journal", "Pendentes", "Conciliacoes Dia Anterior", "Resumo"]` |
| 5 | PGTOS/RECEB via sinal do amount, nao payment_id | SQL usa `COUNT(*) FILTER (WHERE amount < 0)` |

## Uso

```bash
# Dentro do container (Render Shell ou dev local)
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python .claude/skills/gerando-baseline-conciliacao/scripts/gerar_baseline.py \
  --output-dir /tmp \
  --data-referencia 2026-04-17
```

Saida:
```
[OK] Baseline gerado: /tmp/extratos_pendentes_mes_journal_17Abr2026.xlsx
     Aba 1 (Pendentes Mes x Journal): 24 linhas
     Aba 2 (Pendentes): 500 linhas
     Aba 3 (Conciliacoes D-1): 8 usuarios
     Aba 4 (Resumo): 24 linhas + Total Geral
     Total extratos pendentes: 6.985
```

## Referencias

- `references/FORMATO_ABAS.md` — especificacao detalhada das 4 abas
- `references/SQL_ODOO.md` — queries exatas para cada aba
- `references/ARMADILHAS.md` — 8 armadilhas ja cometidas pelo agente
- `/memories/preferences.xml` (user_id=18) — fonte unica da verdade
- `/memories/empresa/heuristicas/financeiro/baseline-de-extratos-formato-fixo.xml` — heuristica nivel 5 que entra em operational_directives

## Historico de baseline

| Data | Total | Delta |
|------|-------|-------|
| 09/04/2026 | 8.684 | — |
| 16/04/2026 | 6.985 | -1.699 |
| 17/04/2026 | 6.694 | -291 |
| 18/04/2026 | 6.350 | -344 |
| 22/04/2026 | 6.162 | -188 |

Tabela local no mesmo dia: 18.158 — NAO usar (acumula ja conciliados).

## Historico de fixes do script

| Data | Fix | Sessao trigger |
|------|-----|----------------|
| 22/04/2026 | (1) API OdooConnection (search_read em vez de dict-subscript). (2) Campos reais lancamento_comprovante (lancado_por/valor_alocado/lancado_em + status='LANCADO'). (3) _ROOT resiliente a /tmp. (4) **Removida Fonte 3 carvia_conciliacoes** — baseline e exclusiva Nacom Goya, CarVia e empresa separada. Smoke test: 6.162 pendentes OK. | Sessao 459 (Marcus, 22/04) — IMP-2026-04-22-001 |
