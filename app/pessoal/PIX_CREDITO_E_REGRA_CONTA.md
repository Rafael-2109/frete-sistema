<!-- doc:meta
tipo: reference
camada: L2
sot_de: app/pessoal/services/pix_credito_service.py, app/pessoal/services/aportes_dono_service.py
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-30
-->
# Pessoal — "Pix no Credito" (Caso 1) e Regra por Conta (Caso 2)

> **Papel:** reference dos dois tratamentos adicionados ao modulo `app/pessoal` para refletir
> no relatorio a realidade economica de (1) operacoes "Pix no Credito" do Nubank e (2) aportes
> do dono em contas diferentes. NAO documenta o modulo inteiro — so estes dois fluxos.

## Indice
- [Caso 1 — Pix no Credito do Nubank](#caso-1--pix-no-credito-do-nubank)
- [Caso 2 — Regra de categorizacao por conta](#caso-2--regra-de-categorizacao-por-conta)
- [Migration e scripts de reprocessamento](#migration-e-scripts-de-reprocessamento)

---

## Caso 1 — Pix no Credito do Nubank

Uma operacao "Pix no Credito" gera um **trio** espalhado em 2 contas Nubank:

| Perna | Conta | Lancamento | Valor |
|-------|-------|------------|-------|
| A funding | NuConta | "Valor adicionado na conta por cartao de credito - …Pix no Credito" (credito) | +V |
| B pix-saida | NuConta | "Transferencia enviada pelo Pix - \<BENEF\>" (debito) | −V |
| C compra | Cartao Nubank | "\<BENEF\>" (debito) | −(V+juros) |

**Distorcao sem tratamento:** A entra como receita falsa, B e C contam a despesa do beneficiario
em duplicidade, e o juros nao aparece separado.

**Tratamento (queremos ver `BENEF V` + `Juros (V+j − V)`):**
1. **A funding → excluido.** Heuristica de prioridade `PADROES_FUNDING_PIX_CREDITO` no Layer 0.6 de
   `categorizacao_service.categorizar_transacao` (roda na importacao, texto univoco).
2. **B pix-saida → despesa PRINCIPAL** na data da operacao (mantem categoria do beneficiario).
3. **C compra → split** em principal (=V, `excluir_relatorio=True`, pois o principal ja esta em B)
   + nova linha de **juros** (=j, visivel, categoria *Juros & Multa*). A soma principal+juros == valor
   original ⇒ a fatura do cartao continua fechando (`fatura_service` soma por `importacao_id` sem
   filtrar `excluir_relatorio`).

**Por que o principal fica em B e nao em C:** B sempre existe na data certa; C (fatura) chega atrasada
ou pode faltar. Sem C, o trio nao fecha — A fica excluido e B fica como despesa; o juros entra quando a
fatura e importada e a deteccao seguinte fecha o trio.

**Onde:** `pix_credito_service.detectar_e_processar()` (pos-importacao, analogo a `transferencia_service`),
disparado automaticamente no fim de `routes/importacao.py` e `services/pluggy_merge_service.merge_item`.
Idempotente via `eh_pix_credito` / `pix_credito_grupo` (campos em `PessoalTransacao`). Reversao manual:
`pix_credito_service.reverter_grupo(grupo)`.

---

## Caso 2 — Regra de categorizacao por conta

`PessoalRegraCategorizacao.contas_ids` (JSON array de `PessoalConta.id`, NULL = qualquer conta) restringe
a regra a contas de DESTINO. Permite duas regras com o mesmo padrao textual e contas diferentes.

**Motor** (`categorizacao_service`): `_conta_no_filtro(conta_id, regra.get_contas_ids())` guarda os 3
layers (F1/substring/fuzzy). Ordenacao: padrao mais longo primeiro; entre iguais, regra **com** conta
vence a generica (`contas_ids IS NOT NULL` desc). Propagado em `aprendizado_service` (`_mesmo_escopo_regra`,
`aprender_de_categorizacao`, `propagar_regra_para_pendentes`, `simular_propagacao`, `contar_matches_por_regra`),
nas rotas (`configuracao.salvar_regra`/`_regra_payload`/`regras_aplicaveis_transacao`,
`transacoes.categorizar`/`categorizar_lote`) e na UI (`templates/pessoal/configuracao.html`, select "Contas").

**Aplicacao ao dono (Rafael):** `aportes_dono_service` cria 4 regras conta-especificas
(`RAFAEL DE CARVALHO` / `RAFAEL NASCIMENTO` × Bradesco→*Salario* / Nubank→*Transferencia entre contas*) e
**desativa a generica** concorrente (sem conta). Como sao Layer 1 (substring), ganham do padrao heuristico
`TED-T ELET DISP` (Layer 4) — resolvendo tambem os aportes que caiam errado em transferencia propria.

---

## Migration e scripts de reprocessamento

Ordem de deploy (producao):
1. **Migration** (par DDL+Python): `scripts/migrations/pessoal_pix_credito_e_regra_conta.{sql,py}`
   — adiciona `contas_ids`, `eh_pix_credito`, `pix_credito_grupo`.
2. **Reprocessar historico** (idempotentes; `--dry-run` por padrao, `--apply` grava):
   - `scripts/migrations/pessoal_reprocessar_pix_credito.py` — fecha os trios ja importados.
   - `scripts/migrations/pessoal_seed_aportes_dono.py` — cria regras do dono + recategoriza entradas.

Testes: `tests/pessoal/test_pix_credito.py`, `tests/pessoal/test_regra_por_conta.py`.
