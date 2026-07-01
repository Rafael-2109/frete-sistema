<!-- doc:meta
tipo: reference
camada: L2
sot_de: app/pessoal/services/categorizacao_service.py, app/pessoal/services/aprendizado_service.py, app/pessoal/services/dashboard_service.py, app/pessoal/services/parsers/base_parser.py
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-07-01
-->
# Pessoal — Pipeline de Categorizacao e Particularidades

> **Papel:** particularidades do motor de categorizacao/exclusao do modulo `app/pessoal`
> (extratos Bradesco CSV, Nubank OFX, Pluggy). Serve para evitar falsos positivos/negativos
> ao mexer no modulo. Complemento: [PIX_CREDITO_E_REGRA_CONTA.md](PIX_CREDITO_E_REGRA_CONTA.md).

## Indice
- [Pipeline de categorizacao (ordem)](#pipeline-de-categorizacao-ordem)
- [Representacao canonica de "excluir do relatorio"](#representacao-canonica-de-excluir-do-relatorio)
- [Atribuicao de membro](#atribuicao-de-membro)
- [Deduplicacao na importacao](#deduplicacao-na-importacao)
- [Valor efetivo (competencia x caixa)](#valor-efetivo-competencia-x-caixa)
- [Auditoria 2026-07-01 (7 fixes + backfill)](#auditoria-2026-07-01-7-fixes--backfill)

---

## Pipeline de categorizacao (ordem)

`categorizacao_service.categorizar_transacao()` roda na importacao, na ordem:

| Camada | O que faz |
|--------|-----------|
| L0.5 parcela | herda categoria de outra parcela irma (mesmo `identificador_parcela`) |
| L0.6 funding Pix-Credito | texto "VALOR ADICIONADO NA CONTA POR CARTAO DE CREDITO" -> `excluir=True`, categoria NULL |
| L0.7 transf. entre contas proprias | `_memo_cita_conta_propria()`: memo cita nº de conta propria (regex, so digitos len>=6) -> `eh_transferencia_propria=True`, `excluir=True` **+ categoria "Transferencia entre contas"** |
| L1 F1 | match por `cpf_cnpj_parte == regra.cpf_cnpj_padrao` |
| L1 substring | `regra.padrao_historico` (normalizado) IN historico normalizado; ordena por len desc, `contas_ids != NULL` desc |
| L2 fuzzy | `rapidfuzz.token_set_ratio >= 85` |
| L3 RELATIVO | sugere categorias, NAO aplica (volta PENDENTE) |
| L4 heuristicas | PAGAMENTO_CARTAO (so debito) / PAGAMENTO_RECEBIDO_CARTAO (so credito) / TRANSFERENCIA_PROPRIA / INVESTIMENTO -> `excluir=True` |
| L5 | PENDENTE |

`_normalizar` = `unidecode(texto).upper()` + colapsa espacos (usado em TODO match e no aprendizado).

**Gotcha das origens:** cada parser monta `historico_completo` diferente — OFX Nubank = MEMO
inteiro (com CPF mascarado + nº de conta); Bradesco CSV = "HIST | DESCRICAO" (pipe); Pluggy =
"A | B | C". Regra aprendida do `historico_completo` inteiro fica **origin-locked** (nao porta
entre origens). Preferir editar o padrao para o nucleo do comerciante ao criar regra.

## Representacao canonica de "excluir do relatorio"

Exclusao tem **duas formas** que DEVEM convergir na UI:
1. **flag** — `eh_transferencia_propria` / `eh_pagamento_cartao` (setadas por L0.7/L4).
2. **categoria grupo `Desconsiderar`** — `eh_categoria_desconsiderar(categoria_id)`.

Uma transacao com `excluir_relatorio=True` mas `categoria_id=NULL` aparece **"A definir"** na
listagem apesar de excluida — foi a raiz da queixa de 2026-07-01 (73 transf. proprias). Por isso
L0.7 agora ATRIBUI a categoria "Transferencia entre contas" (nao so a flag). Ao criar novo caminho
de exclusao, **atribua a categoria Desconsiderar correspondente** em vez de deixar NULL.

Guard Pix-Credito: `deve_permanecer_excluida_pix_credito()` protege a compra-principal do split
em TODOS os writes de `excluir_relatorio` (ver [PIX_CREDITO_E_REGRA_CONTA.md](PIX_CREDITO_E_REGRA_CONTA.md)).

## Atribuicao de membro

`atribuir_membro()`: (1) titular do cartao (parser); (2) ultimos digitos -> conta; (2.5) **cartao =
dono da conta** (`conta.membro_id`), nunca deduz pelo nome do lojista; (3) CC: nome do membro no
historico por **palavra inteira** (`\b`, NAO substring — senao 'RAFAEL' casa 'RAFAELA'/'RAFAELCAM').

`membro_id` NAO entra em nenhum total do relatorio — so filtro/exibicao. Follow-up para terceiros
com mesmo primeiro nome de um familiar (ex.: 'RENATA LETICIA'): casar por CPF do membro (exige
cadastrar `cpf_cnpj` em `pessoal_membros`).

## Deduplicacao na importacao

Hash UNIQUE `gerar_hash_transacao`. Para **extrato Bradesco CC (CSV)** o Docto identifica a
transacao: `documento_autoritativo=True` -> hash IGNORA o historico (o banco reexporta a MESMA tx
com grafia diferente: "Transferencia Pix" vs "Transfe Pix"). OFX cartao mantem historico no hash
(FITID reusado). NUNCA deduplicar por `GROUP BY (conta,documento,data,valor,tipo)` generico —
documento NAO e unico (mapeia >1 evento); apagaria transacoes legitimas.

## Valor efetivo (competencia x caixa)

`valores_efetivos.EXPR_VALOR_EFETIVO` = `valor - COALESCE(valor_compensado, 0)` — fonte UNICA usada
por `dashboard_service` (competencia) E `fluxo_caixa_service` (caixa). Compensavel (compensavel_tipo
S/E) so sai do relatorio quando 100% compensada; o residual conta ao valor efetivo.

## Auditoria 2026-07-01 (7 fixes + backfill)

Auditoria multi-agente (32 agentes, achados verificados vs banco prod). Fixes de codigo (worktree
`pessoal-auditoria-fixes`, TDD): **A1** dashboard usa valor_efetivo (era nominal, ~R$1,4M fantasma);
**C1** dedup por documento autoritativo (R$30.265 dobrado); **B1/B2** guard eh_pix_credito
(R$2.660 double-count); **transf. canonica** L0.7 categoria; **D1/D2** membro word-boundary + cartao
dono; **P3** aprendizado rejeita padrao 'NULL'/'NONE'/'NAN'.

Backfill de dados (aplicado em prod 2026-07-01, idempotente):
`scripts/migrations/pessoal_auditoria_backfill.py` — A2 (4 tx Empresa-Entrada des-escondidas, R$182k),
B1 (6 compras re-excluidas), C1 (10 duplicatas removidas), TR (73 transf -> cat 138), R989
(regra 'NULL' desativada), REL (6 RELATIVO com cat orfas saneadas).
