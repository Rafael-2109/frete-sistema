# CarVia — Historico de Migrations

**Referenciado por**: `app/carvia/CLAUDE.md`

Todas em `scripts/migrations/`. Regra CLAUDE.md: DDL requer `.py` + `.sql` (exceto data fixes).

---

- `criar_tabelas_carvia.py` + `.sql` — 6 tabelas base, 18 indices
- `adicionar_sistema_carvia_usuarios.py` + `.sql` — Campo no Usuario
- `adicionar_seq_subcontrato.py` + `.sql` — `numero_sequencial_transportadora` + unique index parcial + backfill
- `adicionar_campos_fatura_cliente_v2.py` + `.sql` — 14 novos campos em `carvia_faturas_cliente` + tabela `carvia_fatura_cliente_itens`
- `carvia_linking_v1_schema.py` + `.sql` — FK `operacao_id`/`nf_id` em `carvia_fatura_cliente_itens` + tabela `carvia_fatura_transportadora_itens` (15 cols, 4 indices)
- `carvia_linking_v2_backfill.py` — Backfill de FKs em itens existentes (requer v1 antes)
- `backfill_carvia_nf_linking.py` + `.sql` — Cria CarviaNf stubs (FATURA_REFERENCIA) para NFs referenciadas em faturas que nunca foram importadas, vincula nf_id e cria junctions
- `adicionar_status_pagamento_fatura_transportadora.py` + `.sql` — 3 novos campos (`status_pagamento`, `pago_por`, `pago_em`) + indice
- `add_nfs_referenciadas_json_operacoes.py` + `.sql` — Campo JSONB `nfs_referenciadas_json` em carvia_operacoes (refs NF do CTe XML)
- `backfill_nfs_referenciadas_json.py` + `.sql` — Backfill: popula JSON a partir de junctions existentes
- `criar_tabela_carvia_conta_movimentacoes.py` + `.sql` — Tabela `carvia_conta_movimentacoes` (saldo por SUM, UNIQUE tipo_doc+doc_id)
- `adicionar_pago_em_por_carvia.py` + `.sql` — `pago_em`/`pago_por` em `carvia_faturas_cliente` e `carvia_despesas`
- `backfill_carvia_fatura_operacao_binding.py` + `.sql` — Backfill: seta `fatura_cliente_id` e `status=FATURADO` em operacoes via itens de fatura existentes
- `fix_carvia_faturas_duplicadas.py` + `.sql` — Fix: remover 21 faturas cliente duplicadas (importacao 2x do mesmo PDF)
- `add_unique_faturas_carvia.py` + `.sql` — UNIQUE(numero_fatura, cnpj_cliente) em faturas_cliente + UNIQUE(numero_fatura, transportadora_id) em faturas_transportadora
- `adicionar_status_carvia_nfs.py` + `.sql` — Campo `status` VARCHAR(20) DEFAULT 'ATIVA' + `cancelado_em`, `cancelado_por`, `motivo_cancelamento` + indice
- `backfill_numeracao_sequencial_carvia.py` — Backfill: preenche `cte_numero` NULL com CTe-### (operacoes) e Sub-### (subcontratos). Sem DDL
- `criar_tabelas_sessao_cotacao_carvia.py` + `.sql` — 2 tabelas (`carvia_sessoes_cotacao` + `carvia_sessao_demandas`), 5 indices, 2 constraints
- `adicionar_contato_sessao_cotacao_carvia.py` + `.sql` — 4 campos contato cliente (cliente_nome, cliente_email, cliente_telefone, cliente_responsavel)
- `backfill_prefixo_cotacao_carvia.py` + `.sql` — DML: renomeia SC-### → COTACAO-### em numero_sessao
- `criar_tabelas_custo_entrega_cte_complementar.py` + `.sql` — 3 tabelas (`carvia_cte_complementares`, `carvia_custos_entrega`, `carvia_custo_entrega_anexos`), 13 indices
- `adicionar_conferencia_subcontrato.py` + `.sql` — 5 campos conferencia em `carvia_subcontratos` (`valor_considerado`, `status_conferencia`, `conferido_por`, `conferido_em`, `detalhes_conferencia`) + indice
- `criar_tabelas_categoria_moto.py` + `.sql` — 2 tabelas (`carvia_categorias_moto`, `carvia_precos_categoria_moto`) + FK `categoria_moto_id` em `carvia_modelos_moto` + 3 indices
- `criar_tabela_carvia_admin_audit.py` + `.sql` — Tabela `carvia_admin_audit` (auditoria admin: snapshot JSONB, 4 indices, check constraint acoes)
