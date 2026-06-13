<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/skills/auditando-reclassificacao-odoo/SKILL.md
superseded_by: —
atualizado: 2026-06-13
-->
# Scripts — Auditando Reclassificacao Odoo (Detalhes)

> **Papel:** referencia detalhada de parametros, retornos e exemplos do unico
> script desta skill. Visao geral e roteamento: [SKILL.md](./SKILL.md).

## Indice

- [auditar_reclassificacao.py](#auditar_reclassificacaopy)
  - [Modo medir-saldos](#modo-medir-saldos)
  - [Modo validar-lote](#modo-validar-lote)
  - [Modo monitorar-andamento](#modo-monitorar-andamento)
- [Helpers puros (testaveis)](#helpers-puros-testaveis)
- [Fronteira de I/O](#fronteira-de-io)
- [Testes](#testes)

---

## auditar_reclassificacao.py

Script unico, 3 sub-comandos (modos). **READ-only** — so `search_read` sobre
`account.move.line` e `account.move`. Sem `--dry-run`/`--confirmar` (read nao
muta nada).

```bash
source .venv/bin/activate
SK=.claude/skills/auditando-reclassificacao-odoo/scripts/auditar_reclassificacao.py
python "$SK" <modo> [opcoes]
```

### Modo medir-saldos

Mede `n_linhas` + `total_debito` por conta no periodo, com o filtro fixo
`debit>0 AND parent_state=posted` (linhas a debito efetivas, posted).

| Param | Obrig | Default | Descricao |
|-------|-------|---------|-----------|
| `--contas` | sim | — | `id:rotulo` separados por virgula (ex: `25091:CPV,26785:VARNEG`). Sem rotulo usa o id. |
| `--data-inicio` | sim | — | `YYYY-MM-DD` |
| `--data-fim` | sim | — | `YYYY-MM-DD` |
| `--company-id` | nao | `4` (CD) | company_id Odoo |
| `--journal-id` | nao | `845` | journal_id Odoo |
| `--json` | nao | tabela | saida JSON |

**Retorno (JSON):**
```json
{"modo": "medir-saldos", "company_id": 4, "journal_id": 845,
 "periodo": {"inicio": "2025-09-01", "fim": "2025-09-30"},
 "saldos": [{"conta_id": 25091, "rotulo": "CPV", "n_linhas": 7591,
             "total_debito": 5924701.64}]}
```

### Modo validar-lote

Compara o arquivo-alvo JSON contra o estado real no Odoo. Classifica cada `lid`
unico e detecta anomalias estruturais.

| Param | Obrig | Default | Descricao |
|-------|-------|---------|-----------|
| `--arquivo` | sim | — | caminho do JSON-alvo |
| `--chave` | nao | `venda_NF` | chave da lista no JSON |
| `--conta-destino` | sim | — | conta para onde as linhas devem migrar (ex: 25091) |
| `--conta-origem` | sim | — | conta de origem (ex: 26785) |
| `--json` | nao | tabela | saida JSON |

**Classificacao por `lid`:** `processada` = em conta_destino; `pendente` = em
conta_origem; `divergente` = em qualquer outra conta; `ausente` = `lid` nao
existe mais no Odoo. `duplicados` = `lid` repetido no arquivo. `moves_draft` =
quantos `account.move` (campo `line`) estao em `state=draft`. `integro` = sem
duplicados, ausentes nem divergentes.

**Retorno (JSON):**
```json
{"modo": "validar-lote", "conta_destino": 25091, "conta_origem": 26785,
 "total_alvo": 6, "linhas_unicas": 5, "duplicados": [5],
 "processadas": 2, "pendentes": 1,
 "divergentes": [{"lid": 3, "account_id": 99999}], "ausentes": [4],
 "moves_draft": 1, "integro": false}
```

### Modo monitorar-andamento

Subconjunto focado em progresso de uma execucao em curso.

| Param | Obrig | Default | Descricao |
|-------|-------|---------|-----------|
| `--arquivo` | sim | — | caminho do JSON-alvo |
| `--chave` | nao | `venda_NF` | chave da lista no JSON |
| `--conta-destino` | sim | — | conta destino |
| `--conta-origem` | sim | — | conta origem |
| `--json` | nao | tabela | saida JSON |

**Retorno (JSON):**
```json
{"modo": "monitorar-andamento", "total": 3, "processadas": 2, "pendentes": 1,
 "pct_concluido": 66.7, "moves_draft": 0, "concluido": false}
```
`concluido` = `processadas == total AND moves_draft == 0`.

## Helpers puros (testaveis)

A logica vive em funcoes que recebem a conexao Odoo `c` injetada (sem I/O
proprio), o que permite teste deterministico com um FakeOdoo:

| Funcao | Responsabilidade |
|--------|------------------|
| `parse_contas(s)` | `'25091:CPV,26785:VARNEG'` -> `[(25091,'CPV'),(26785,'VARNEG')]` |
| `carregar_alvo(path, chave)` | le o JSON-alvo; `KeyError` claro se a chave faltar |
| `detectar_duplicados(registros)` | `lid` repetidos (ordem de 1a ocorrencia) |
| `medir_saldos(c, contas, ini, fim, company_id, journal_id)` | n_linhas + total_debito por conta |
| `validar_lote(c, registros, conta_destino, conta_origem)` | integridade do lote |
| `monitorar_andamento(c, registros, conta_destino, conta_origem)` | progresso |

## Fronteira de I/O

`_conectar()` faz o import lazy de `app.odoo.utils.connection.get_odoo_connection`
(via `sys.path.insert`) e autentica — chamado so dentro de `main()`. Os helpers
puros nao importam `app`, garantindo testes isolados sem rede/PROD.

## Testes

`tests/skills/auditando_reclassificacao_odoo/test_logica_auditoria_reclassificacao.py`
— 16 testes deterministicos (FakeOdoo avalia o domain Odoo: `=`, `!=`, `in`,
`>`, `>=`, `<`, `<=`). Cobrem cada filtro do `medir-saldos` (conta, company,
journal, periodo, `debit>0`, `parent_state=posted`), a classificacao completa do
`validar-lote` e o progresso do `monitorar-andamento`.

## Fontes

- FONTE (codigo): `.claude/skills/auditando-reclassificacao-odoo/scripts/auditar_reclassificacao.py`
- FONTE (origem do design): 17 scripts distintos do cluster 4 (`agent_adhoc_script`, sessao `4ce68a88`), decisao 4-maos `#164`/`#166` (`agent_improvement_dialogue`).
- FONTE (modelos/campos): `.claude/references/odoo/MODELOS_CAMPOS.md` (account.move.line) + `.claude/references/odoo/AGENT_BOILERPLATE.md` (conexao).
