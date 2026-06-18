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
- `add_fatura_transportadora_id_custo_entrega.py` + `.sql` — ADD COLUMN `fatura_transportadora_id` em `carvia_custos_entrega` (FK nullable ON DELETE SET NULL) + indice + backfill via `subcontrato_id -> sub.fatura_transportadora_id` + backfill status `PENDENTE -> VINCULADO_FT` para CEs com FK. Padrao DespesaExtra.fatura_frete_id do Nacom. NAO remove `subcontrato_id` (migration destructive separada). Relatorio de CEs orfaos ao final.
- `remove_subcontrato_id_custo_entrega.py` + `.sql` — **DESTRUCTIVE (pos-deploy)**: DROP COLUMN `subcontrato_id` de `carvia_custos_entrega` apos validar que todo o codigo ja migrou para `fatura_transportadora_id`. Executar apenas apos Fase 1-6 em producao estavel. NAO CRIADA AINDA — sera Fase 7.
- `add_previnculos_extrato_cotacao.py` + `.sql` — Tabela `carvia_previnculos_extrato_cotacao` (feature frete pre-pago — regra R16). 15 colunas, 2 CHECK constraints (`ck_previnculo_valor_positivo`, `ck_previnculo_status`), 5 indices + UNIQUE PARCIAL `(extrato_linha_id, cotacao_id) WHERE status='ATIVO'`. FKs: `extrato_linha_id` (CASCADE), `cotacao_id` (CASCADE), `conciliacao_id` (SET NULL), `fatura_cliente_id` (SET NULL). Idempotente via `IF NOT EXISTS` + DO blocks para check constraints.
- `carvia_comissao_ajustes.py` + `.sql` — Consistencia de comissoes (R21). (1) ADD COLUMN `vendedor_usuario_id` (FK `usuarios`, indexed) + `total_ajustes` NUMERIC(15,2) em `carvia_comissao_fechamentos`; (2) tabela `carvia_comissao_ajustes` (delta debito/credito por CTe alterado/cancelado: 4 indices, 2 CHECK constraints `status`/`motivo`, FKs `operacao_id`, `fechamento_origem_id`, `vendedor_usuario_id`, `fechamento_aplicado_id` SET NULL); (3) backfill `vendedor_usuario_id` por lower(email). Idempotente (DO blocks + `IF NOT EXISTS`). A tabela tambem nasce via `create_all` no boot — o `.sql` cobre PROD.

### Redesign CarVia 2026-06 (coletas papel-de-pao / recebimento por chassi / portal cliente / flag local_cd)

> Aplicadas no PROD via `SKIP_DB_CREATE=true DATABASE_URL=$DATABASE_URL_PROD python <mig>.py`.
> GOTCHA: `create_all` cria tabela nova no boot mas NAO altera tabela existente nem cria VIEW —
> ALTER/VIEW exigem a migration ANTES do push (model carregado em toda request; deploy falha sem a coluna).
> mig CREATE TABLE muitas vezes ja existem via `create_all` (indices `ix_*` SQLAlchemy, NAO `idx_*` do .sql) — NAO re-rodar o .sql.

- `2026_06_17_local_cd_e_chegada_filial.py` + `.sql` — flag `local_cd` VARCHAR(20) NOT NULL DEFAULT 'VICTORIO_MARCHEZINE' em `separacao`, `embarque_itens`, `controle_portaria`, `carvia_nfs`, `entregas_monitoradas` + `chegada_filial` (bool) + `chegada_filial_em` em `entregas_monitoradas` + 6 indices parciais. Backfill VM automatico.
- `2026_06_17_carvia_coletas.py` + `.sql` — tabelas `carvia_coletas` (cabecalho coleta "papel de pao") + `carvia_coleta_nfs` (linhas NF rascunho).
- `2026_06_17_carvia_coleta_recebimento.py` + `.sql` — tabelas `carvia_coleta_recebimentos` (1:1 coleta) + `carvia_coleta_recebimento_chassis` (1 linha/moto) — recebimento por chassi.
- `2026_06_17_carvia_portal_cliente.py` + `.sql` — tabelas `carvia_portal_usuarios` (usuario EXTERNO isolado) + `carvia_portal_usuario_cnpjs` (escopo CNPJ_DIRETO).
- `alterar_view_pedidos_v10_local_cd.py` + `.sql` — VIEW `pedidos` + MV `mv_pedidos` v10 = v9 + coluna `local_cd` (Nacom `min(s.local_cd)`; CarVia NULL) + indice `idx_mv_pedidos_local_cd`. DROP+CREATE atomico; REFRESH CONCURRENTLY preservado.
- `alterar_view_pedidos_v11_carvia_local_cd.py` + `.sql` — v11 = v10 com CarVia `local_cd` = default 'VICTORIO_MARCHEZINE' (4B). (v12 — derivar TM da Coleta — implementado abaixo: Frente A 2026-06-18.)
- `2026_06_18_carvia_pedido_cotacao_local_cd.py` + `.sql` (**Frente A**) — coluna `local_cd` VARCHAR(20) NOT NULL DEFAULT 'VICTORIO_MARCHEZINE' em `carvia_cotacoes` + `carvia_pedidos` + 2 indices parciais (TM) + backfill TM retroativo a partir de `carvia_nfs` via `numero_nf` normalizado. Alimentada por `coleta_service._propagar_local_cd_para_documentos` (Coleta -> NF -> Pedido/Cotacao). Idempotente.
- `alterar_view_pedidos_v12_carvia_local_cd_da_coleta.py` + `.sql` (**Frente A**) — v12 = v11 com Partes 2A/2B lendo `COALESCE(cot.local_cd / ped.local_cd, 'VICTORIO_MARCHEZINE')` em vez do literal fixo. **DEADLOCK-RESILIENTE** (2026-06-18): recria a VIEW `pedidos` e a MV `mv_pedidos` (independentes) em **TRANSACOES SEPARADAS** + `SET lock_timeout='10s'` — recriar as duas na MESMA transacao com o app lendo ambas formava ciclo de locks (deadlock real no PROD na 1a tentativa). O runner `.py` executa em AUTOCOMMIT (psycopg2) deixando os BEGIN/COMMIT do .sql controlarem; `psql -f` tambem serve. PRE-REQUISITO: a migration de colunas acima.
- `2026_06_18_carvia_coleta_nf_unique.py` + `.sql` — UNIQUE(`carvia_nf_id`) em `carvia_coleta_nfs` (uma NF pertence a no max 1 coleta; fix de status ambiguo no portal). DO block idempotente.
- `2026_06_18_carvia_recebimento_flag_e_chegada.py` + `.sql` — `usuarios.acesso_recebimento_carvia` (BOOL — operador so-recebimento, sem valores) + `carvia_coletas.data_prevista_chegada` (DATE).
- `2026_06_18_carvia_portal_grupo_empresa.py` + `.sql` — `carvia_portal_usuarios.grupo_empresa` (VARCHAR — grupo/empresa que o cliente declara no cadastro; hint de vinculo).
- `2026_06_18_carvia_coleta_nf_uf.py` + `.sql` — `carvia_coleta_nfs.uf` (VARCHAR(2) — UF do destino, rascunho que se consolida com a NF real ao vincular). `ADD COLUMN IF NOT EXISTS` + backfill de `uf`/`cidade_destino` das linhas ja vinculadas a partir de `carvia_nfs.uf_destinatario`/`cidade_destinatario`. Idempotente.
