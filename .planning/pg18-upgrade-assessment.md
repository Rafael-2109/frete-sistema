# Avaliacao de Riscos — Upgrade PostgreSQL 16 → 18

**Data**: 2026-02-12
**Status**: APROVADO — Risco geral BAIXO
**Banco**: `dpg-d13m38vfte5s738t6p50-a` (Render, Oregon, basic_4gb)

---

## Dados Reais do Cluster (coletados 2026-02-12)

| Item | Valor |
|------|-------|
| Versao | PostgreSQL 16.11 (Debian) |
| Tamanho do banco | 1.170 MB (~1.2 GB) |
| Total de indexes | 1.187 |
| Partial indexes | 36 |
| GIN indexes | 0 |
| Triggers | 7 (5 BEFORE, 2 AFTER) |
| Extensions instaladas | pg_stat_statements 1.10, plpgsql 1.0, unaccent 1.1 |
| Data checksums | **ON** |
| Password encryption | **md5** |
| Collation | en_US.UTF8 |
| Encoding | UTF8 |

---

## Matriz de Risco Consolidada (com dados reais)

| # | Risco | Severidade | Probabilidade | Impacto Final | Verificacao |
|---|-------|-----------|---------------|--------------|-------------|
| 1 | Data checksums mismatch | Critico | **NULA** (ambos ON) | **NENHUM** | `SHOW data_checksums` = on |
| 2 | AFTER trigger role change | Medio | Nula (role unica) | **NENHUM** | 2 AFTER triggers, mesma role |
| 3 | VACUUM partition children | Baixo | Nula (sem partitions) | **NENHUM** | N/A |
| 4 | Timezone abbreviation | Medio | Nula (usa nome) | **NENHUM** | `timezone=America/Sao_Paulo` |
| 5 | COPY CSV marker | Baixo | Nula (nao usa COPY) | **NENHUM** | N/A |
| 6 | Unlogged partitions | Baixo | Nula | **NENHUM** | N/A |
| 7 | Rule privileges | Baixo | Nula | **NENHUM** | N/A |
| 8 | MD5 deprecation warnings | Baixo | **ALTA** | **BAIXO** | `password_encryption = md5` |
| 9 | Reindex necessario | Medio | Alta | **MEDIO** | 1.187 indexes, ~1.2 GB |

---

## Detalhamento dos Riscos Relevantes

### RISCO 1: Data Checksums — ELIMINADO

O cluster PG 16 ja tem `data_checksums = on`. PG 18 tambem habilita por default.
Nao ha mismatch — `pg_upgrade` procedera sem problemas neste aspecto.

### RISCO 2: AFTER Triggers — NENHUM

Apenas 2 AFTER triggers no sistema:
- `trigger_atualizar_totais_embarque` (tabela `embarque_itens`) — funcao `atualizar_totais_embarque`
- `trigger_atualizar_ordens_filhas` (tabela `ordem_producao`) — funcao `atualizar_ordens_filhas`

Ambos executam com a mesma role de aplicacao. Sem `SET ROLE` ou `SET SESSION AUTHORIZATION` em nenhum ponto. Mudanca de PG 18 no contexto de role de AFTER triggers nao tem impacto.

Os outros 5 triggers sao BEFORE (update_updated_at_column e similares) — nao afetados.

### RISCO 8: MD5 Password Warnings — BAIXO

`password_encryption = md5` confirmado. PG 18 emitira warnings nos logs quando senhas MD5 forem usadas. Sem impacto funcional, mas recomenda-se migrar para SCRAM-SHA-256.

**Acao**: Apos upgrade, solicitar ao Render suporte a migracao para SCRAM via painel.

### RISCO 9: Reindex — MEDIO (unico ponto de atencao)

- **1.187 indexes** em 1.2 GB de banco
- **36 partial indexes** (maioria em `separacao` e `carteira_principal`)
- **0 GIN indexes** (plano original estimava 1 — nao confirmado)
- **Tempo estimado**: Para 1.2 GB com 1.187 indexes, ~2-5 minutos
- **Extension `unaccent`**: Usada em indexes de busca textual — REINDEX obrigatorio

---

## Compatibilidade de Extensions

| Extension | Versao Atual | Compativel PG 18? | Notas |
|-----------|-------------|-------------------|-------|
| pg_stat_statements | 1.10 | **SIM** | Atualiza automaticamente |
| plpgsql | 1.0 | **SIM** | Built-in |
| unaccent | 1.1 | **SIM** | Estavel |

---

## Compatibilidade de Stack Python

| Componente | Versao | Compativel PG 18? |
|------------|--------|-------------------|
| psycopg2-binary | 2.9.10 | **SIM** |
| Flask-SQLAlchemy | 3.1.1 | **SIM** |
| Flask-Migrate | 4.1.0 | **SIM** |
| SQLAlchemy dialect | postgresql | **SIM** |

---

## Triggers Completos no Sistema

| Trigger | Tabela | Timing | Funcao |
|---------|--------|--------|--------|
| update_ai_sessions_updated_at | ai_advanced_sessions | BEFORE | update_updated_at_column |
| update_ai_config_updated_at | ai_system_config | BEFORE | update_updated_at_column |
| update_alertas_separacao_updated_at | alertas_separacao_cotada | BEFORE | update_updated_at_column |
| trigger_atualizar_totais_embarque | embarque_itens | **AFTER** | atualizar_totais_embarque |
| trg_atualizar_qtd_mto | ordem_producao | BEFORE | atualizar_qtd_pedido_mto |
| trigger_atualizar_ordens_filhas | ordem_producao | **AFTER** | atualizar_ordens_filhas |
| update_saldo_estoque_cache_atualizado_em | saldo_estoque_cache | BEFORE | update_atualizado_em_column |

---

## Partial Indexes (36 total)

### carteira_principal (6)
- idx_carteira_cnpj_partial
- idx_carteira_raz_social_red_unaccent
- idx_carteira_num_pedido_partial
- idx_carteira_vendedor_cnpj
- idx_carteira_pedido_saldo
- idx_carteira_equipe_vendedor

### separacao (16)
- idx_sep_falta_item_sync, idx_sep_pedido_sync, idx_sep_lote_status
- idx_sep_nf, idx_separacao_lote_pedido_sync, idx_separacao_numero_nf_status
- idx_separacao_sync_lote, idx_sep_cotacao_id, idx_sep_pedido_produto_sync
- idx_sep_produto_qtd_sync, idx_sep_lote_pedido_produto, idx_separacao_cobertura
- idx_separacao_sync_only, idx_sep_falta_pgto_sync, idx_sep_nf_cd
- idx_sep_lote_sync

### Outras tabelas (14)
- cnab_retorno_lote, empresa_venda_moto, entregas_monitoradas (2)
- entregas_rastreadas, faturamento_produto, lancamento_comprovante
- moto (2), movimentacao_estoque (2), usuarios (2), validacao_nf_po_dfe

---

## Plano de Execucao Final

### Pre-Upgrade (scripts: `pg18_pre_upgrade_check.py` / `.sql`)
1. Executar script de verificacao pre-upgrade (automatizado)
2. Fazer backup via Render Dashboard
3. Comunicar janela de manutencao (~15-20 min)

### Upgrade
4. Iniciar upgrade via Render Dashboard → PG 18
5. Render executa pg_upgrade internamente

### Pos-Upgrade (scripts: `pg18_post_upgrade.py` / `.sql`)
6. Executar `REINDEX DATABASE` (~2-5 min)
7. Executar `ANALYZE` em todas as tabelas
8. Verificar extensions (pg_stat_statements, unaccent)
9. Testar triggers: embarque_itens INSERT, ordem_producao UPDATE
10. Verificar logs para MD5 warnings
11. Monitorar metricas de performance por 24h

### Pos-Estabilizacao
12. Solicitar migracao de md5 → scram-sha-256 ao Render suporte

---

## Conclusao

**Risco geral: BAIXO**

Dados reais confirmam compatibilidade excelente:
- Checksums ja habilitados (risco #1 ELIMINADO)
- Apenas 2 AFTER triggers com role unica (risco #2 NENHUM)
- Sem particionamento, COPY, rules (riscos #3-7 NENHUM)
- Banco de 1.2 GB com REINDEX rapido (~2-5 min)
- Stack Python totalmente compativel
- Extensions estaveis e compativeis

Unico trabalho operacional: REINDEX + ANALYZE pos-upgrade + planejar migracao SCRAM.
