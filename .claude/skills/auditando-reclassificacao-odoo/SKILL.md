---
name: auditando-reclassificacao-odoo
description: >-
  Skill READ-only para AUDITAR reclassificacao contabil em lote no Odoo
  (account.move.line). 3 modos: medir-saldos (conta/empresa/periodo),
  validar-lote (arquivo-alvo vs Odoo: divergencias/ausentes/duplicados) e
  monitorar-andamento (% migrado). Usar p/ "mede CPV/VarNeg em setembro",
  "valida o lote", "quanto ja migrou pra CPV". So mede/compara/monitora — NAO
  escreve/reclassifica; razao geral completo -> razao-geral-odoo. Matriz no corpo.
allowed-tools: Read, Bash, Glob, Grep
---

# auditando-reclassificacao-odoo (READ-only — 3 modos de auditoria)

## Indice

- [Quando usar / Quando NAO usar](#quando-usar--quando-nao-usar)
- [Modos READ-only (3)](#modos-read-only-3)
- [Constantes reais](#constantes-reais)
- [Estrutura do arquivo-alvo](#estrutura-do-arquivo-alvo)
- [Exemplos](#exemplos)
- [Formato de saida](#formato-de-saida)
- [Armadilhas](#armadilhas)
- [Validacao](#validacao)

Skill de auditoria de **reclassificacao contabil em lotes** no Odoo. Mede saldos,
valida a integridade de um lote-alvo contra o estado real e monitora o andamento
de uma execucao em curso. **ESTRITAMENTE READ-only**: usa apenas `search_read`
sobre `account.move.line` e `account.move` — nunca `button_draft` / `write
account_id` / `action_post`.

> **Origem:** 17 scripts distintos do cluster 4 (sessao `4ce68a88`, Marcus
> user 18), reclassificacao CPV/VarNeg/FFF mes a mes (ago/2025 → jan/2026) na
> empresa CD. Aprovada na decisao 4-maos `#164` (2026-06-12). A sugestao irma de
> **write em massa (#163) foi REJEITADA** — por isso esta skill NAO escreve.

Service: `scripts/auditar_reclassificacao.py` — detalhes de parametros e
retornos em [SCRIPTS.md](./SCRIPTS.md).
Boilerplate Odoo: `.claude/references/odoo/AGENT_BOILERPLATE.md`

## Quando usar / Quando NAO usar

**USAR QUANDO** o pedido e:
- "mede os saldos de CPV/VarNeg/FFF em setembro/2025" (n_linhas + total_debito)
- "qual o saldo da conta X no periodo Y?" (debit>0, posted, por empresa/journal)
- "valida o lote de reclassificacao" / "confere o arquivo-alvo contra o Odoo"
- "tem divergencia / linha ausente / duplicado no lote?"
- "como esta o andamento da reclassificacao?" / "quanto ja migrou pra CPV?"
- "ja finalizou a reclassificacao de novembro?"

**NAO USAR PARA:**
- **EXECUTAR a reclassificacao** (button_draft → write account_id → action_post):
  esta skill e READ-only por design (C4). O write e' operacao pontual/finita,
  feita por script dedicado fora de skill — NAO foi promovido a skill (#163
  rejeitada: acerto retroativo finito, sem recorrencia permanente).
- rastrear UMA NF/PO/SO/pagamento -> `rastreando-odoo`
- razao geral / balancete completo (saldo acumulado por conta) -> `razao-geral-odoo`
- extratos bancarios pendentes de conciliacao -> `gerando-baseline-conciliacao`
- saldo de ESTOQUE (stock.quant) -> `consultando-quant-odoo`
- explorar modelo Odoo desconhecido -> `descobrindo-odoo-estrutura`
- auditoria SPED ECD -> subagente `auditor-sped-ecd`

## Modos READ-only (3)

### a) `medir-saldos` — saldo por conta no periodo

```
objeto:        account.move.line (READ-only)
input:         --contas <id:rotulo,...> --data-inicio --data-fim
                 [--company-id 4] [--journal-id 845] [--state posted] [--json]
filtro:        debit>0 AND parent_state=<state> (default posted; --state draft|both
               para contar o que falta postar pos-reclassificacao; both omite o filtro)
output (JSON): {modo, company_id, journal_id, periodo:{inicio,fim},
                saldos:[{conta_id, rotulo, n_linhas, total_debito}]}
pre-condicoes: contas nao-vazio; datas YYYY-MM-DD
pos-condicoes: nenhuma (read-only)
```

### b) `validar-lote` — arquivo-alvo vs estado real (integridade)

```
objeto:        account.move.line + account.move (READ-only)
input:         --arquivo <json> [--chave venda_NF]
                 --conta-destino <id> --conta-origem <id> [--json]
output (JSON): {modo, conta_destino, conta_origem, total_alvo, linhas_unicas,
                duplicados:[lid], processadas, pendentes,
                divergentes:[{lid,account_id}], ausentes:[lid],
                moves_draft, integro:bool}
classificacao: processada = lid em conta_destino; pendente = em conta_origem;
                divergente = em outra conta; ausente = lid sumiu do Odoo.
integro:       sem anomalias estruturais (duplicados/ausentes/divergentes).
pre-condicoes: arquivo existe; chave presente no JSON
pos-condicoes: nenhuma (read-only)
```

### c) `monitorar-andamento` — progresso de execucao em curso

```
objeto:        account.move.line + account.move (READ-only)
input:         --arquivo <json> [--chave venda_NF]
                 --conta-destino <id> --conta-origem <id> [--json]
output (JSON): {modo, total, processadas, pendentes, pct_concluido,
                moves_draft, concluido:bool}
concluido:     processadas==total AND moves_draft==0
pre-condicoes: arquivo existe; chave presente no JSON
pos-condicoes: nenhuma (read-only)
```

## Constantes reais

Defaults extraidos dos scripts originais (sempre overridaveis por flag).

| Simbolo | Valor | Significado |
|---|---|---|
| company_id | `4` | CD (default) |
| journal_id | `845` | journal das vendas reclassificadas |
| CPV | `25091` | Custo Produto Vendido (conta destino) |
| VARNEG | `26785` | Variacao Negativa (conta origem) |
| FFF | `26854` | conta auxiliar do mutirao |
| chave | `venda_NF` | chave da lista no arquivo-alvo JSON |

## Estrutura do arquivo-alvo

```json
{"venda_NF": [{"line": <move_id>, "lid": <move_line_id>, "debit": <valor>}, ...]}
```
`line` = id do `account.move`; `lid` = id do `account.move.line`; `debit` = valor.

## Exemplos

```bash
SK=.claude/skills/auditando-reclassificacao-odoo/scripts/auditar_reclassificacao.py

# a) Medir CPV/VarNeg/FFF em setembro/2025 (baseline antes do mutirao)
python "$SK" medir-saldos --contas 25091:CPV,26785:VARNEG,26854:FFF \
    --data-inicio 2025-09-01 --data-fim 2025-09-30 --json

# b) Validar o lote-alvo de setembro vs Odoo (integridade)
python "$SK" validar-lote --arquivo /tmp/reclass/setembro_alvo.json \
    --conta-destino 25091 --conta-origem 26785 --json

# c) Acompanhar o andamento (durante a execucao)
python "$SK" monitorar-andamento --arquivo /tmp/reclass/setembro_alvo.json \
    --conta-destino 25091 --conta-origem 26785
```

## Formato de saida

Default = **tabela** (legivel). Com `--json` retorna o dict estruturado descrito
em cada modo (`json.dumps`, `indent=2`). Convencao majoritaria dos scripts de
skill.

## Armadilhas

- **READ-only inviolavel**: se o pedido for EXECUTAR a reclassificacao (mover
  linhas para CPV), esta skill NAO faz — ela so audita. O write e' script
  dedicado fora de skill (#163 rejeitada).
- **`debit>0` no medir-saldos**: mede apenas linhas a debito efetivas (espelha os
  scripts originais). Lancamentos a credito (debit=0) sao ignorados de proposito.
- **`account_id` vem como `[id, nome]`** (many2one via XML-RPC): o classificador
  extrai `[0]` automaticamente. Nao comparar a tupla crua.
- **`parent_state` na move.line**: filtra `posted` pela move pai; linhas de moves
  em draft nao entram no medir-saldos (mas aparecem em `moves_draft` no
  validar/monitorar).
- **Nao confundir com `razao-geral-odoo`**: aquela exporta o razao/balancete
  completo com saldo acumulado; esta foca em UM par origem→destino de
  reclassificacao com classificacao por lid.

## Validacao

Construida via TDD (2026-06-13) — 16 testes deterministicos em
`tests/skills/auditando_reclassificacao_odoo/` (FakeOdoo avaliando domain Odoo;
sem rede/LLM/PROD). Smoke real em PROD: `medir-saldos` set/2025 retornou
CPV 7591 linhas / R$ 5.924.701,64; VarNeg 404 / R$ 1.497.850,89; FFF 0.
