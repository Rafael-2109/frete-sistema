---
name: gerando-baseline-conciliacao
description: >-
  Gera Excel com 4 abas de extratos pendentes (baseline de conciliacao Nacom).
  Gatilhos: "gerar/atualizar baseline", "foto das conciliacoes", "extratos
  pendentes por mes" (Marcus user_id=18 ou financeiro). Anti: conciliar linha ->
  executando-odoo-financeiro; transferencia interna ->
  conciliando-transferencias-internas; rastrear pagamento -> rastreando-odoo.
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
   - Se usuario disser "do dia DD/MM" / "08/05" / "ontem" -> data passada -> PASSAR --data-referencia
   - Sem mencao de data -> hoje.
3. Rodar scripts/gerar_baseline.py com a data.
4. Script:
   a. Executa 4 queries contra Odoo (ver SQL_ODOO.md).
      - Quando data_ref < hoje: reconstroi estado historico via UNIAO
        (create_date<=ref AND is_reconciled=False) OR (write_date>ref AND is_reconciled=True)
      - Quando data_ref = hoje: filtra apenas is_reconciled=False (estado atual).
   b. Monta Excel openpyxl seguindo FORMATO_ABAS.md.
   c. Salva em /tmp/ e retorna URL de download.
   d. Emite [WARNING] no stdout se o total bater EXATO com algum baseline historico
      conhecido (sinal de cache, filtro errado, ou skill nao aplicou data passada).
5. Validar 5 checkpoints antes de responder (ver Checkpoints).
6. VALIDACAO HISTORICA OBRIGATORIA quando data_ref < hoje (ver secao abaixo).
7. POS-EXECUCAO OBRIGATORIA (ver "Apresentacao Pos-Geracao Obrigatoria" abaixo).
8. Se usuario pedir variacao: RECUSAR e pedir autorizacao explicita.
```

## Validacao Historica Obrigatoria (data_ref < hoje)

**Trigger**: usuario pediu "baseline do dia DD/MM" para data anterior a hoje.

ANTES de entregar o resultado, comparar o total obtido com:

1. **Baseline anterior em memoria/historico** (tabela `## Historico de baseline` deste SKILL.md
   ou ultimo Excel gerado).
2. **Output do script**: se aparecer linha `[WARNING] BASELINE HISTORICO COM TOTAL IDENTICO`,
   tratar como bloqueador.

**Acao por cenario**:

| Cenario | Acao |
|---------|------|
| Total IDENTICO ao baseline anterior (delta=0) | ALERTAR usuario explicitamente: "O total obtido para DD/MM e identico ao baseline anterior (NNN). Possivelmente a skill nao recalculou o estado historico. Quer forcar recalculo ou revisar o filtro?" — NAO entregar como correto. |
| Total muito proximo (ex: delta < 10 em base de milhares) | Reportar delta no chat: "Delta vs baseline anterior: -3 linhas. Verifique se faz sentido para a janela de tempo." |
| Total significativamente diferente | Entregar normalmente com delta explicito. |
| Script emitiu [WARNING] | SEMPRE alertar usuario antes de entregar. |

**Anti-padrao proibido** (sessao `5ffdeace-6f95-4413-ab96-ed553d3b2d92`, 11/05/2026):
agente entregou baseline de 08/05 com total 3.287 IDENTICO ao baseline atual de 11/05,
adicionando apenas uma nota de rodape "O total e identico ao baseline de hoje" — sem
alertar que o resultado pode estar errado nem perguntar se deve recalcular.

**Padrao correto**: se delta=0 inesperado em data passada, PARAR e perguntar ao usuario
antes de gerar o link/tabelas.

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

## Revalidacao em Solicitacoes Repetidas (IMP-2026-05-13-001)

Quando o usuario solicitar "atualizar baseline" / "foto das conciliacoes" pela SEGUNDA ou
TERCEIRA vez no MESMO dia, o agente DEVE **revalidar** os dados no Odoo em vez de devolver
cache da execucao anterior. Dados de conciliacao mudam em tempo real (Marcus + analistas
conciliando enquanto a conversa acontece) e responder "essa solicitacao foi processada ha N
minutos" e ANTI-PADRAO documentado.

**Regra**:

| Tempo desde a ultima execucao | Acao |
|-------------------------------|------|
| < 60 segundos | Reaproveitar resposta anterior (defesa contra duplo-clique) |
| >= 60 segundos | **Reexecutar** `gerar_baseline.py`, comparar com baseline anterior, reportar delta |

**Output obrigatorio quando revalida**: incluir no inicio da resposta a linha:

```
Revalidado as HH:MM — delta vs execucao anterior: <DELTA> linhas
```

Onde:
- `HH:MM` = hora atual (timezone Brasilia, formato 24h)
- `DELTA` = diferenca em valor absoluto vs total da ultima execucao do dia
- Se DELTA=0: exibir `delta = 0 (estado nao mudou — confirmacao via Odoo direto)`

**Anti-padrao proibido** (sessao `227aecd0-fce7-49aa-9f44-7efbe8af0295`, 13/05/2026): agente
respondeu "Essa solicitacao foi processada ha 2 min" e truncou a resposta. Resultado: usuario
ficou sem saber se o dado estava atualizado e teve que repetir a pergunta.

**Padrao correto**: SEMPRE reexecutar quando delta >= 60s, com a linha "Revalidado as..."
no topo do output, mesmo que delta seja zero.

## Aba/Tabela D-0 — Conciliacoes do Dia Atual (IMP-2026-05-13-002)

Quando a `data_referencia` for **HOJE** (D-0), o agente DEVE incluir AUTOMATICAMENTE no chat
e no Excel uma tabela adicional com as conciliacoes ja realizadas no dia, alem da tabela D-1.

**Comportamento**:
- Sempre que data_ref == hoje: gerar tabela D-0 (conciliacoes ja realizadas no dia, por usuario).
- Se nao houver conciliacoes em D-0: exibir explicitamente "Nenhuma conciliacao registrada hoje
  ate <HH:MM>" — NAO omitir a secao.
- Aplicar a mesma estrutura `Usuario | Linhas | Pgtos | Rec` ordenado por linhas DESC.
- No Excel, a aba "Conciliacoes Dia Anterior" passa a renomear-se contextualmente conforme
  data_referencia: para D-0 incluir tambem subsecao "Hoje (D-0)" abaixo da subsecao "Ontem (D-1)".

**Anti-padrao** (sessao `227aecd0-fce7-49aa-9f44-7efbe8af0295`, 13/05/2026): baseline gerado
sem tabela D-0, usuario teve que perguntar separadamente "QUAL FOI AS Conciliacoes em D-0".

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

**REGRA CRITICA — ENTREGA ATOMICA (I7 do system_prompt)**: A confirmacao de geracao,
o link de download, o resumo (total + delta) e as duas tabelas DEVEM aparecer TODOS
na MESMA mensagem. NUNCA emitir mensagens intermediarias do tipo "Script rodando…",
"Script OK", "Extraindo dados…", "Gerando link…" sem o link real anexo. Aguarde o
script terminar e retornar `arquivo.url_completa` antes de responder.

**ANTI-PADRAO PROIBIDO** (sessoes 4cc8c1f6 e ed2fa68c, 07/05/2026):
- Turno 1 do agente: "Script OK, extraindo tabelas..."
- Turno 2 do usuario: "gerou?"
- Turno 3 do agente: "Gerando link de download..."
- Turno 4 do usuario: "gerou?"
- ...repete 12 vezes...
- Turno final: link postado.

**PADRAO CORRETO** — UMA UNICA mensagem contendo: link + total + delta + Tabela 1 + Tabela 2.

**SINAL DE FRICCAO**: Se o usuario perguntar "gerou?", "e as tabelas?", "envia o link"
ou "verificar a solicitacao anterior" apos voce ter dito que o script terminou, isso
indica que esta secao foi pulada — registrar como pitfall via `log_system_pitfall`
e como `register_improvement` (category=`gotcha_report`).

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
| 11/05/2026 | (1) `query_odoo_pendentes()` agora recebe `data_ref` e aplica filtro historico quando `data_ref < hoje`: `(create_date <= ref) AND (is_reconciled=False OR (is_reconciled=True AND write_date > ref))`. (2) Adicionado `_emitir_warning_se_total_identico_a_baselines_historicos()` que detecta IMP-2026-05-11-001 (data passada retornando estado atual). (3) Nova armadilha #9 + secao "Validacao Historica Obrigatoria" em SKILL.md. | Sessao `5ffdeace-6f95-4413-ab96-ed553d3b2d92` (Marcus, 11/05) — IMP-2026-05-11-001, -003 |
| 06/06/2026 | **Refator retrocompativel (CLI identico)** para reuso pelo fast-path deterministico do agente (FASE 1 reducao de custo): (1) extraida `gerar_baseline_arquivo(data_ref, output_dir, ordem_meses)` — NAO cria app_context (chamador cria), retorna `{output_file, agg, pendentes, d1, d0, total, ...}`; `main()` passa a chama-la. (2) corpo de `query_conciliacoes_d1` extraido para `_query_conciliacoes_dia(odoo_conn, dia)`; `query_conciliacoes_d1`/novo `query_conciliacoes_d0` delegam (D-0 = dia atual, IMP-2026-05-13-002, so na apresentacao de chat — Excel canonico inalterado). Quando "atualizar baseline" e' trivial, `app/agente/sdk/baseline_fastpath.py` roda este script SEM LLM. Variacao/falha -> cai no agente (skill normal). Plano: `docs/superpowers/plans/2026-06-06-reducao-custo-agente-fast-path.md`. Spot-check PROD OK (62 pendentes, D-1 271). | Plano reducao de custo (fast-path), 06/06 |
| 15/06/2026 | **Botao "Gerar Baseline" na Central Financeira** (3o disparo, alem de chat e fast-path): rota `POST /financeiro/baseline/gerar` (`login_required` + `requires_financeiro`) chama `executar_baseline_fastpath` e devolve `{ok,url,total}` para download inline no dashboard. Tira a tarefa recorrente do fluxo conversacional (REC-2026-05-05-001, 7a semana). Smoke local OK (67 pendentes). | Followup avaliacao manutencao semanal 15/06 |
