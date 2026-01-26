# IMPLEMENTATION PLAN: Reestruturação do Módulo de Gestão de Pallets

**Spec**: `.claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md`
**Versão**: 1.2.4
**Data**: 25/01/2026
**Status**: EM PROGRESSO - Fase 6 Testes (96% Completo)
**Última Análise**: 25/01/2026 (Sessão 16 - Testes de auditoria de cancelamento implementados: 79 testes total, Critério 8 validado)

---

## RESUMO EXECUTIVO

Reestruturar o módulo de pallets em **dois domínios independentes**:
- **Domínio A**: Controle dos Pallets (créditos, vales, soluções)
- **Domínio B**: Tratativa das NFs (ciclo de vida documental)

### Estado Atual (Arquivos Existentes - VERIFICADO)

| Arquivo | Linhas | Descrição | Status |
|---------|--------|-----------|--------|
| `app/pallet/models.py` | 129 | Apenas `ValePallet` (será migrado para `PalletDocumento`) | ✅ Verificado |
| `app/pallet/routes.py` | ~1433 | Monolítico, mistura todos os conceitos | ⚠️ A deprecar |
| `app/pallet/__init__.py` | 7 | Inicialização básica (importa ValePallet) | ✅ Verificado |
| `app/pallet/utils.py` | ~50 | Funções auxiliares (CNPJ, prazos) | ✅ Manter |
| `app/pallet/services/emissao_nf_pallet.py` | - | Emissão de NF | ✅ Manter |
| `app/pallet/services/sync_odoo_service.py` | - | Sincronização Odoo | ⚠️ A modificar |

### Templates Existentes (13 arquivos)

| Template | Descrição | Ação |
|----------|-----------|------|
| `index.html` | Dashboard atual | Substituir por `dashboard_v2.html` |
| `vale_pallets.html` | Listagem vales | Migrar para `controle_pallets/vales.html` |
| `vale_pallet_form.html` | Formulário vale | Migrar para modal |
| `movimentos.html` | Movimentação estoque | Avaliar necessidade |
| `substituicao.html` | Substituição responsável | Migrar para modal |
| `substituicao_lista.html` | Lista substituições | Integrar em solucoes.html |
| `registrar_saida.html` | Saída de pallets | Migrar para modal |
| `registrar_retorno.html` | Retorno de pallets | Migrar para modal |
| `resolver_vale.html` | Resolução vale | Migrar para modal |
| `vincular_venda.html` | Vincular venda | Migrar para modal |
| `enviar_resolucao.html` | Enviar resolução | Migrar para modal |
| `baixar_movimento.html` | Baixar movimento | Migrar para modal |
| `sincronizar.html` | Sincronização Odoo | Manter/atualizar |

### Dependências Críticas

| Modelo | Tabela | Uso Atual | Verificado |
|--------|--------|-----------|------------|
| `ValePallet` | `vale_pallets` | Vales/canhotos (será migrado) | ✅ |
| `MovimentacaoEstoque` | `movimentacao_estoque` | Remessas/entradas (`local_movimentacao='PALLET'`), tem campos `tipo_destinatario`, `cnpj_destinatario`, `qtd_abatida` | ✅ Verificado (app/estoque/models.py:22-205) |
| `Embarque` | `embarques` | Campos `nf_pallet_*` (MANTER - Grupo 2) | ✅ Doc CLAUDE.md |
| `EmbarqueItem` | `embarque_itens` | Campos `nf_pallet_*` (MANTER - Grupo 2) | ✅ Doc CLAUDE.md |

---

## FASES DE IMPLEMENTAÇÃO

### FASE 1: INFRAESTRUTURA (Fundação)
**Prioridade**: ALTA | **Bloqueadora**: SIM

#### 1.1 Criar Novos Models

##### 1.1.1 Criar `app/pallet/models/nf_remessa.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Classe**: `PalletNFRemessa`
- **Campos obrigatórios**:
  - `numero_nf`, `serie`, `chave_nfe`, `data_emissao`
  - `odoo_account_move_id`, `odoo_picking_id`
  - `tipo_destinatario`, `cnpj_destinatario`, `nome_destinatario`
  - `status`: `ATIVA`, `RESOLVIDA`, `CANCELADA`
- **Relacionamentos**: `creditos`, `solucoes_nf`
- **Arquivo**: `app/pallet/models/nf_remessa.py` (~200 linhas)

##### 1.1.2 Criar `app/pallet/models/credito.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Classe**: `PalletCredito`
- **FK**: `nf_remessa_id`
- **Campos**: `qtd_original`, `qtd_saldo`, `tipo_responsavel`, `cnpj_responsavel`, `nome_responsavel`
- **Status**: `PENDENTE`, `PARCIAL`, `RESOLVIDO`
- **Arquivo**: `app/pallet/models/credito.py` (~230 linhas)

##### 1.1.3 Criar `app/pallet/models/documento.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Classe**: `PalletDocumento`
- **FK**: `credito_id`
- **Tipo**: `CANHOTO`, `VALE_PALLET`
- **Campos recebimento**: `recebido`, `recebido_em`, `recebido_por`
- **Nota**: Substitui parcialmente `ValePallet`
- **Arquivo**: `app/pallet/models/documento.py` (~200 linhas)

##### 1.1.4 Criar `app/pallet/models/solucao.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Classe**: `PalletSolucao`
- **FK**: `credito_id`
- **Tipo**: `BAIXA`, `VENDA`, `RECEBIMENTO`, `SUBSTITUICAO`
- **FK opcional**: `credito_destino_id` (para substituição)
- **Arquivo**: `app/pallet/models/solucao.py` (~350 linhas)

##### 1.1.5 Criar `app/pallet/models/nf_solucao.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Classe**: `PalletNFSolucao`
- **FK**: `nf_remessa_id`
- **Tipo**: `DEVOLUCAO`, `RETORNO`, `CANCELAMENTO`
- **Vinculação**: `AUTOMATICO`, `MANUAL`, `SUGESTAO`
- **Arquivo**: `app/pallet/models/nf_solucao.py` (~340 linhas)

##### 1.1.6 Criar `app/pallet/models/__init__.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Importar todos os novos models
- Manter import de `ValePallet` para compatibilidade transitória
- **Arquivo**: `app/pallet/models/__init__.py` (~45 linhas)
- **NOTA**: `ValePallet` movido para `app/pallet/models/vale_pallet.py`

#### 1.2 Criar Migrations

##### 1.2.1 Criar `scripts/pallet/001_criar_tabelas_pallet_v2.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Tabelas a criar**:
  - `pallet_nf_remessa`
  - `pallet_creditos`
  - `pallet_documentos`
  - `pallet_solucoes`
  - `pallet_nf_solucoes`
- **Índices**: `numero_nf`, `cnpj_destinatario`, `status`, `nf_remessa_id`
- **Arquivo**: `scripts/pallet/001_criar_tabelas_pallet_v2.py` (~470 linhas)

##### 1.2.2 Criar `scripts/pallet/001_criar_tabelas_pallet_v2.sql`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- SQL equivalente para Render Shell
- **Arquivo**: `scripts/pallet/001_criar_tabelas_pallet_v2.sql` (~330 linhas)

#### 1.3 Scripts de Migração de Dados

##### 1.3.1 Criar `scripts/pallet/002_migrar_movimentacao_para_nf_remessa.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Migrar `MovimentacaoEstoque` onde `local_movimentacao='PALLET'` e `tipo_movimentacao='REMESSA'`
- Para cada remessa: criar `PalletNFRemessa` + `PalletCredito`
- **Arquivos criados**:
  - `scripts/pallet/002_migrar_movimentacao_para_nf_remessa.py` (~430 linhas) - Script Python com --dry-run e --force
  - `scripts/pallet/002_migrar_movimentacao_para_nf_remessa.sql` (~150 linhas) - SQL para Render Shell
- **Funcionalidades**:
  - Verifica pré-requisitos (tabelas de destino existem)
  - Evita duplicatas via movimentacao_estoque_id
  - Calcula qtd_saldo baseado em qtd_abatida
  - Determina status baseado em baixado e saldo
  - Modo dry-run para teste
  - Modo --force para remigração
  - Relatório final de contagens

##### 1.3.2 Criar `scripts/pallet/003_migrar_vale_pallet_para_documento.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Migrar `ValePallet` para `PalletDocumento`
- Vincular a `PalletCredito` correto via `nf_pallet`
- Se vale resolvido, criar `PalletSolucao` correspondente
- **Arquivos criados**:
  - `scripts/pallet/003_migrar_vale_pallet_para_documento.py` (~560 linhas) - Script Python com --dry-run, --force, --verbose
  - `scripts/pallet/003_migrar_vale_pallet_para_documento.sql` (~220 linhas) - SQL para Render Shell
- **Funcionalidades**:
  - Busca PalletCredito via nf_pallet → PalletNFRemessa.numero_nf
  - Mapeia tipo_vale (CANHOTO_ASSINADO → CANHOTO, VALE_PALLET → VALE_PALLET)
  - Se resolvido=True, cria PalletSolucao (VENDA ou RECEBIMENTO/COLETA)
  - Evita duplicatas via vale_pallet_id
  - Relatório de vales sem crédito correspondente
  - Modo dry-run para teste
  - Modo --force para remigração

##### 1.3.3 Criar `scripts/pallet/004_validar_migracao.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Arquivos criados**:
  - `scripts/pallet/004_validar_migracao.py` (~913 linhas) - Script Python com --verbose e --output
  - `scripts/pallet/004_validar_migracao.sql` (~427 linhas) - SQL para Render Shell
- **14 Verificações implementadas**:
  1. Tabelas V2 existem (contagem de registros)
  2. Tabelas legado existem (fonte de migração)
  3. FK Créditos → NF Remessa
  4. FK Documentos → Créditos
  5. FK Soluções → Créditos
  6. FK Soluções NF → NF Remessa
  7. Saldo <= Original (créditos)
  8. Status vs Saldo (consistência)
  9. Soma Soluções <= Original
  10. Migração MovimentacaoEstoque (comparação fonte/destino)
  11. Migração ValePallet (comparação fonte/destino)
  12. Totais de Quantidades (consistência matemática)
  13. NFs Duplicadas
  14. Formato de CNPJs (11 ou 14 dígitos)
- **Funcionalidades**:
  - Modo --verbose para detalhes de cada problema
  - Modo --output para salvar relatório em arquivo
  - Resumo final com contagem de OK/AVISO/ERRO
  - Categorização de problemas (erro crítico vs aviso)

---

### FASE 2: BACKEND (Lógica de Negócio)
**Prioridade**: ALTA | **Depende de**: Fase 1

#### 2.1 Services Domínio A (Controle de Pallets)

##### 2.1.1 Criar `app/pallet/services/credito_service.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026) - 797 linhas
- **Métodos implementados**:
  - `criar_credito_ao_importar_nf(nf_remessa_id, usuario)` ✅
  - `criar_credito_manual(nf_remessa_id, quantidade, ...)` ✅
  - `registrar_documento(credito_id, tipo, ...)` ✅
  - `registrar_recebimento_documento(documento_id, usuario, ...)` ✅
  - `registrar_solucao(credito_id, tipo_solucao, quantidade, usuario)` ✅
  - `registrar_baixa(credito_id, quantidade, motivo, ...)` ✅
  - `registrar_venda(creditos_quantidades, nf_venda, ...)` ✅
  - `registrar_recebimento(credito_id, quantidade, ...)` ✅
  - `registrar_substituicao(credito_origem_id, credito_destino_id, ...)` ✅
  - `calcular_saldo_credito(credito_id)` ✅
  - `atualizar_status_credito(credito_id)` ✅
  - `listar_creditos_pendentes(...)` ✅
  - `obter_resumo_por_responsavel(cnpj)` ✅
  - `listar_vencimentos_proximos(dias)` ✅
- **Arquivo**: `app/pallet/services/credito_service.py`

##### 2.1.2 Criar `app/pallet/services/solucao_pallet_service.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026) - 642 linhas
- **Métodos implementados**:
  - `registrar_baixa(credito_id, quantidade, motivo, usuario, ...)` ✅
  - `validar_baixa_massiva(creditos_ids, motivo)` ✅
  - `registrar_venda(nf_venda, creditos_quantidades, ...)` ✅
  - `listar_vendas_por_nf(nf_venda)` ✅
  - `registrar_recebimento(credito_id, quantidade, ...)` ✅
  - `registrar_recebimento_lote(creditos_quantidades, ...)` ✅
  - `registrar_substituicao(credito_origem_id, credito_destino_id, ...)` ✅
  - `criar_credito_para_substituicao(nf_remessa_id, ...)` ✅
  - `obter_historico_solucoes(...)` ✅
  - `obter_totais_por_tipo(cnpj_responsavel, ...)` ✅
- **Arquivo**: `app/pallet/services/solucao_pallet_service.py`

#### 2.2 Services Domínio B (Tratativa NFs)

##### 2.2.1 Criar `app/pallet/services/nf_service.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026) - 896 linhas
- **Métodos implementados**:
  - `importar_nf_remessa_odoo(dados_odoo, usuario)` ✅
  - `obter_nf_por_id(nf_id)` ✅
  - `obter_nf_por_numero(numero_nf, serie)` ✅
  - `obter_nf_por_chave(chave_nfe)` ✅
  - `listar_nfs_ativas(cnpj_destinatario, tipo_destinatario, empresa, limite)` ✅
  - `listar_nfs_pendentes_vinculacao()` ✅
  - `cancelar_nf(nf_remessa_id, motivo, usuario)` ✅
  - `atualizar_status_nf(nf_remessa_id)` ✅
  - `registrar_solucao_nf(nf_remessa_id, tipo, quantidade, dados, usuario)` ✅
  - `confirmar_sugestao(nf_solucao_id, usuario)` ✅
  - `rejeitar_sugestao(nf_solucao_id, motivo, usuario)` ✅
  - `obter_resumo_nf(nf_remessa_id)` ✅
- **Arquivo**: `app/pallet/services/nf_service.py`

##### 2.2.2 Criar `app/pallet/services/match_service.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026) - ~750 linhas
- **Métodos implementados**:
  - `buscar_nfs_devolucao_pallet_dfe(data_de, data_ate, apenas_nao_processadas)` ✅
  - `sugerir_vinculacao_devolucao(nf_devolucao, criar_sugestao)` ✅
  - `sugerir_vinculacao_retorno(nf_retorno, criar_sugestao)` ✅
  - `confirmar_vinculacao(nf_solucao_id, usuario)` ✅
  - `rejeitar_sugestao(nf_solucao_id, motivo, usuario)` ✅
  - `vincular_devolucao_manual(nf_remessa_ids, nf_devolucao, quantidades, usuario)` ✅
  - `vincular_retorno_manual(nf_remessa_id, nf_retorno, quantidade, usuario)` ✅
  - `processar_devolucoes_pendentes(data_de, data_ate, criar_sugestoes)` ✅
- **Helpers internos**:
  - `_eh_nf_devolucao_pallet(document_id)` ✅
  - `_obter_cfop_code(cfop_id)` ✅
  - `_eh_produto_pallet(product_id)` ✅
  - `_obter_quantidade_pallets_linhas(document_id)` ✅
  - `_limpar_cnpj(cnpj)` ✅
  - `_eh_intercompany(cnpj)` ✅
  - `_nf_ja_processada(chave_nfe)` ✅
  - `_extrair_nf_referencia(info_complementar)` ✅
  - `_calcular_score_match(nf_remessa, nf_devolucao, nf_referenciada)` ✅
  - `_criar_sugestao_vinculacao(nf_remessa, nf_devolucao, quantidade_sugerida)` ✅
- **Arquivo**: `app/pallet/services/match_service.py`

#### 2.3 Atualizar Service Existente

##### 2.3.1 Modificar `app/pallet/services/sync_odoo_service.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Integrar com novos models
- Ao sincronizar remessa: criar `PalletNFRemessa` + `PalletCredito`
- Manter compatibilidade com `MovimentacaoEstoque` (período de transição)
- **Implementação**:
  - Adicionado mapeamento `COMPANY_ID_TO_EMPRESA` (4=CD, 1=FB, 3=SC)
  - No método `sincronizar_remessas`: após criar `MovimentacaoEstoque`, chama `NFService.importar_nf_remessa_odoo()`
  - Busca campos adicionais do Odoo: `company_id`, `l10n_br_chave_nf`
  - Tratamento de erro isolado: falha no v2 não bloqueia sistema legado
  - Log detalhado mostrando empresa e criação de PalletNFRemessa

---

### FASE 3: ROUTES (API e Views)
**Prioridade**: MÉDIA | **Depende de**: Fase 2

#### 3.1 Estrutura de Routes

##### 3.1.1 Criar `app/pallet/routes/__init__.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Blueprint principal `pallet_v2_bp` com url_prefix `/pallet/v2`
- Função `init_routes()` para registrar sub-blueprints
- Função `register_blueprints(app)` para uso externo
- **Arquivo**: `app/pallet/routes/__init__.py` (~55 linhas)

##### 3.1.2 Criar `app/pallet/routes/dashboard.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- `GET /pallet/v2/` - Dashboard principal (3 tabs)
- `GET /pallet/v2/api/stats` - API de estatísticas
- `GET /pallet/v2/api/creditos-vencendo` - API créditos próximos do vencimento
- Cards de resumo por domínio (total em terceiros, créditos, NFs, sugestões)
- Stats para Tab 1 (NF Remessa), Tab 2 (Controle Pallets), Tab 3 (Tratativa NFs)
- **Arquivo**: `app/pallet/routes/dashboard.py` (~270 linhas)

##### 3.1.3 Criar `app/pallet/routes/nf_remessa.py`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- `GET /pallet/v2/nf-remessa/` - Listagem com filtros
- `GET /pallet/v2/nf-remessa/<id>` - Detalhe da NF
- `POST /pallet/v2/nf-remessa/<id>/cancelar` - Cancelar NF
- `GET /pallet/v2/nf-remessa/api/buscar` - API de busca
- `GET /pallet/v2/nf-remessa/api/<id>` - API detalhe NF
- `GET /pallet/v2/nf-remessa/api/por-numero` - API busca por número
- `GET /pallet/v2/nf-remessa/api/pendentes-vinculacao` - API NFs pendentes
- **Arquivo**: `app/pallet/routes/nf_remessa.py` (~320 linhas)

##### 3.1.4 Criar `app/pallet/routes/controle_pallets.py` (Domínio A)
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Listagens**:
  - `GET /pallet/v2/controle/vales` - Listagem de documentos (canhotos/vales)
  - `GET /pallet/v2/controle/solucoes` - Listagem de créditos pendentes
  - `GET /pallet/v2/controle/historico` - Histórico de soluções
- **Ações de Documentos**:
  - `POST /pallet/v2/controle/documento` - Registrar documento
  - `POST /pallet/v2/controle/documento/<id>/receber` - Receber documento
- **Ações de Soluções**:
  - `POST /pallet/v2/controle/baixa` - Registrar baixa
  - `POST /pallet/v2/controle/venda` - Registrar venda (N:1)
  - `POST /pallet/v2/controle/recebimento` - Registrar recebimento
  - `POST /pallet/v2/controle/substituicao` - Registrar substituição
- **APIs**:
  - `GET /pallet/v2/controle/api/creditos` - Listar créditos pendentes
  - `GET /pallet/v2/controle/api/credito/<id>` - Detalhe do crédito
  - `GET /pallet/v2/controle/api/resumo-responsavel/<cnpj>` - Resumo por responsável
- **Arquivo**: `app/pallet/routes/controle_pallets.py` (~640 linhas)

##### 3.1.5 Criar `app/pallet/routes/tratativa_nfs.py` (Domínio B)
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Listagens**:
  - `GET /pallet/v2/tratativa/direcionamento` - NFs aguardando vinculação
  - `GET /pallet/v2/tratativa/sugestoes` - Sugestões automáticas
  - `GET /pallet/v2/tratativa/solucoes` - Histórico de soluções de NF
  - `GET /pallet/v2/tratativa/canceladas` - NFs canceladas (histórico)
- **Ações de Vinculação**:
  - `POST /pallet/v2/tratativa/vincular-devolucao` - Vincular devolução (1:N)
  - `POST /pallet/v2/tratativa/vincular-retorno` - Vincular retorno (1:1)
  - `POST /pallet/v2/tratativa/confirmar-sugestao/<id>` - Confirmar sugestão
  - `POST /pallet/v2/tratativa/rejeitar-sugestao/<id>` - Rejeitar sugestão
  - `POST /pallet/v2/tratativa/processar-devolucoes` - Buscar no DFe e criar sugestões
- **APIs**:
  - `GET /pallet/v2/tratativa/api/sugestoes` - Listar sugestões pendentes
  - `GET /pallet/v2/tratativa/api/buscar-devolucoes` - Buscar devoluções no DFe
  - `GET /pallet/v2/tratativa/api/sugerir-vinculacao` - Sugerir vinculação
  - `GET /pallet/v2/tratativa/api/nf-solucao/<id>` - Detalhe de solução NF
- **Arquivo**: `app/pallet/routes/tratativa_nfs.py` (~550 linhas)

#### 3.2 Deprecar Routes Antigos

##### 3.2.1 Marcar routes em `app/pallet/routes.py` como deprecated
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Ações realizadas**:
  - Renomeado `app/pallet/routes.py` → `app/pallet/routes_legacy.py`
  - Adicionado decorator `@deprecated_route()` nas principais rotas v1
  - Cada acesso a rota deprecada gera WARNING no log com alternativa v2
  - Atualizado `app/__init__.py` para registrar ambos blueprints (v1 e v2)
- **Rotas deprecadas** (22 rotas, todas funcionando):
  - `GET /pallet/` → `pallet_v2.dashboard.index`
  - `GET /pallet/movimentos` → `pallet_v2.controle_pallets.listar_vales`
  - `GET /pallet/vales` → `pallet_v2.controle_pallets.listar_vales`
  - `POST /pallet/registrar-saida` → `pallet_v2.controle_pallets.registrar_documento`
  - `POST /pallet/registrar-retorno` → `pallet_v2.controle_pallets.registrar_recebimento`
  - `GET /pallet/substituicao` → `pallet_v2.controle_pallets.registrar_substituicao`
  - `POST /pallet/vales/novo` → `pallet_v2.controle_pallets.registrar_documento`
  - `POST /pallet/vales/<id>/receber` → `pallet_v2.controle_pallets.receber_documento`
  - `POST /pallet/vales/<id>/resolver` → `pallet_v2.controle_pallets.registrar_baixa`
  - `GET /pallet/api/saldo/<cnpj>` → `pallet_v2.controle_pallets.api_resumo_responsavel`
  - `GET /pallet/api/dashboard` → `pallet_v2.dashboard.api_stats`
- **Arquivo**: `app/pallet/routes_legacy.py` (~1550 linhas)

---

### FASE 4: FRONTEND (UI)
**Prioridade**: MÉDIA | **Depende de**: Fase 3

#### 4.1 Dashboard Principal

##### 4.1.1 Criar `app/templates/pallet/v2/dashboard.html`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Layout com 3 tabs principais (NFs Remessa, Controle Pallets, Tratativa NFs)
- Cards de resumo (4 cards: Pallets em Terceiros, Créditos Pendentes, NFs Pendentes, Próximos Vencimento)
- Ações rápidas (Registrar Documento, Sincronizar Odoo)
- Modal para registrar documento integrado
- Alerta de créditos próximos do vencimento
- CSS customizado com design system
- **Arquivo**: `app/templates/pallet/v2/dashboard.html` (~945 linhas)

#### 4.2 Templates Domínio A (Controle Pallets)

##### 4.2.1 Criar `app/templates/pallet/v2/controle_pallets/vales.html`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Listagem de documentos (canhotos e vales)
- Filtros: tipo, status, CNPJ/nome do emissor
- Ações: registrar documento (modal), marcar como recebido, ver detalhes
- Stats cards: total, canhotos pendentes, vales pendentes, recebidos
- Paginação completa com filtros preservados
- Modal de detalhes por documento
- **Arquivo**: `app/templates/pallet/v2/controle_pallets/vales.html` (~1031 linhas)

##### 4.2.2 Criar `app/templates/pallet/v2/controle_pallets/solucoes.html`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Listagem de créditos pendentes com filtros (status, tipo_responsavel, cnpj)
- Stats cards: pendentes, parciais, resolvidos, total saldo
- Tabela com seleção em lote para ações de venda
- 4 modais de ação integrados: baixa, venda, recebimento, substituição
- Modal de detalhes do crédito via API
- Indicadores visuais de vencimento (vencido, prestes a vencer)
- **Arquivo**: `app/templates/pallet/v2/controle_pallets/solucoes.html` (~1100 linhas)

##### 4.2.3 Criar `app/templates/pallet/v2/controle_pallets/historico.html`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Histórico de soluções registradas
- Filtros por tipo, período, CNPJ
- Stats por tipo de solução (baixa, venda, recebimento, substituição)
- Tabela com detalhes específicos por tipo de solução
- **Arquivo**: `app/templates/pallet/v2/controle_pallets/historico.html` (~400 linhas)

##### 4.2.4 Modais de ação (Controle de Pallets)
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026) - Integrados em solucoes.html
- ✅ Modal Baixa: quantidade, motivo, observação
- ✅ Modal Venda: seleção de créditos (N:1), NF venda, valor unitário
- ✅ Modal Recebimento: quantidade, referência (vale/canhoto), observação
- ✅ Modal Substituição: novo responsável (tipo, CNPJ, nome), quantidade, motivo

#### 4.3 Templates Domínio B (Tratativa NFs)

##### 4.3.1 Criar `app/templates/pallet/v2/tratativa_nfs/direcionamento.html`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- NFs aguardando vinculação (listagem com filtros)
- Modais integrados: Vincular Devolução (1:N), Vincular Retorno (1:1)
- Stats cards: total ativas, transportadoras, clientes
- Paginação completa com filtros preservados
- **Arquivo**: `app/templates/pallet/v2/tratativa_nfs/direcionamento.html` (~700 linhas)

##### 4.3.2 Criar `app/templates/pallet/v2/tratativa_nfs/sugestoes.html`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Listagem de sugestões automáticas de vinculação
- Stats cards: pendentes, devoluções, retornos
- Filtro por tipo de sugestão
- Modais integrados: Confirmar Sugestão, Rejeitar Sugestão, Detalhes
- Ação de buscar devoluções no DFe (processar pendentes)
- Score de match visual (high/medium/low)
- **Arquivo**: `app/templates/pallet/v2/tratativa_nfs/sugestoes.html` (~700 linhas)
- **NOTA**: Adicionado campo `score_match` ao modelo `PalletNFSolucao` e migrações

##### 4.3.3 Criar `app/templates/pallet/v2/tratativa_nfs/solucoes.html`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Listagem de soluções de NF confirmadas (histórico)
- Devoluções, retornos e cancelamentos registrados
- Filtros por tipo, vinculação, data_de, data_ate
- Stats cards: total, devoluções, retornos, cancelamentos (com contagem de pallets)
- Modal de detalhes completo com informações de confirmação/rejeição
- Paginação com preservação de filtros
- **Arquivo**: `app/templates/pallet/v2/tratativa_nfs/solucoes.html` (~700 linhas)

##### 4.3.4 Criar `app/templates/pallet/v2/tratativa_nfs/canceladas.html`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- NFs canceladas (histórico para auditoria)
- Stats cards: total canceladas, transportadoras, clientes (com contagem de pallets)
- Filtros por data de cancelamento (data_de, data_ate)
- Tabela com: NF, tipo destinatário, destinatário, quantidade, emissão, cancelamento, motivo
- Modal de detalhes reutilizando API de nf_remessa
- Paginação completa com filtros preservados
- **Arquivo**: `app/templates/pallet/v2/tratativa_nfs/canceladas.html` (~600 linhas)

##### 4.3.5 Modais/formulários:
- [x] `Modal Vincular Devolução (1:N)` - ✅ Integrado em direcionamento.html
- [x] `Modal Vincular Retorno (1:1)` - ✅ Integrado em direcionamento.html
- [x] `Modal Confirmar Sugestão` - ✅ Integrado em sugestoes.html
- [x] `Modal Rejeitar Sugestão` - ✅ Integrado em sugestoes.html
- [x] `Modal Detalhes Sugestão` - ✅ Integrado em sugestoes.html

#### 4.4 Template de Detalhe

##### 4.4.1 Criar `app/templates/pallet/v2/nf_remessa/detalhe.html`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Dados completos da NF (número, série, chave, data emissão, empresa, quantidade, valores)
- Status dos dois domínios lado a lado:
  - Domínio A: Controle de Pallets (créditos com progress bar, lista de créditos, stats)
  - Domínio B: Tratativa de NFs (soluções documentais com progress bar, lista de soluções)
- Histórico de soluções em timeline (baixa, venda, recebimento, substituição)
- Ações contextuais: Cancelar NF (modal), Vincular NF, Gerenciar Créditos
- Informações de auditoria (criação, atualização, IDs Odoo)
- **Arquivo**: `app/templates/pallet/v2/nf_remessa/detalhe.html` (~700 linhas)

##### 4.4.2 Criar `app/templates/pallet/v2/nf_remessa/listagem.html`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Listagem completa de NFs de remessa com filtros
- Stats cards: total, ativas, resolvidas, canceladas
- Filtros: status, empresa, tipo destinatário, CNPJ/nome, data inicial/final
- Tabela com: NF, emissão, empresa, destinatário, quantidade, resolvido, status
- Paginação completa com filtros preservados
- **Arquivo**: `app/templates/pallet/v2/nf_remessa/listagem.html` (~400 linhas)

#### 4.5 Atualizar Menu

##### 4.5.1 Modificar `app/templates/base.html`
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- Adicionado link para nova Gestão de Pallets
- Local: Financeiro > (após Central Fiscal)
- Rota: `pallet_v2.dashboard.index`
- Ícone: `fas fa-pallet text-warning`

---

### FASE 5: INTEGRAÇÃO E FILTROS
**Prioridade**: ALTA | **Depende de**: Fase 2

#### 5.1 Filtrar Devoluções de Pallet no Módulo de Devolução

##### 5.1.1 Identificar arquivo de devoluções ✅ JÁ IDENTIFICADO
- [x] **Status**: ANÁLISE CONCLUÍDA
- **Arquivos do módulo de devolução** (16 arquivos em `app/devolucao/`):
  - `app/devolucao/services/nfd_service.py` - Importação de NFDs do Odoo (finnfe=4)
  - `app/devolucao/routes/vinculacao_routes.py` - APIs de sincronização e vinculação
  - `app/devolucao/models.py` - Modelo NFDevolucao com campo `origem_registro`
- **Fluxo atual**: NFDs são importadas do Odoo via DFe (finnfe=4 = NF entrada)
- **Problema**: CFOP 5920/6920 (pallet) está entrando junto com devoluções de produto

##### 5.1.2 Adicionar filtro para excluir devoluções de pallet
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Arquivos modificados**:
  - `app/devolucao/models.py` - Adicionado campo `e_pallet_devolucao` (Boolean)
  - `app/devolucao/services/nfd_service.py`:
    - Adicionadas constantes `CFOPS_PALLET` e `CODIGO_PRODUTO_PALLET`
    - Criado método `_detectar_nfd_pallet()` para detectar NFDs de pallet por CFOP/código
    - Chamada automática após `_processar_linhas_produto()` no fluxo de importação
    - Atualizado `listar_nfds_orfas()` para excluir NFDs de pallet por padrão
  - `scripts/devolucao/001_adicionar_campo_pallet.py` - Migration Python
  - `scripts/devolucao/001_adicionar_campo_pallet.sql` - Migration SQL
  - `scripts/devolucao/002_detectar_nfds_pallet_existentes.py` - Script para marcar NFDs existentes
- **Implementação**:
  - Campo `e_pallet_devolucao` adicionado à tabela `nf_devolucao`
  - Detecção automática por CFOP (1920, 2920, 5920, 6920, 5917, 6917, 1917, 2917)
  - Detecção automática por código produto (208000012)
  - Filtro aplicado na listagem de órfãs (parâmetro `incluir_pallets=False` por padrão)

#### 5.2 Consumir DFe para Match Automático

##### 5.2.1 Criar job/task para identificar NFs de pallet no DFe
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Objetivo**: Buscar NFs de entrada com CFOP de devolução vasilhame e direcioná-las para o módulo de pallet
- **Implementação**:
  - `MatchService.buscar_nfs_devolucao_pallet_dfe()` - Busca NFs de pallet diretamente no Odoo
  - `MatchService.processar_devolucoes_pendentes()` - Processa e cria sugestões de vinculação
  - `POST /pallet/v2/tratativa/processar-devolucoes` - Rota para processamento manual
  - `POST /pallet/v2/tratativa/api/processar-devolucoes` - API JSON para jobs/integrações
- **Funcionalidades**:
  - Busca NFs no modelo `l10n_br_fiscal.document` do Odoo
  - Filtra por CFOP de devolução vasilhame (5920/6920/1920/2920)
  - Filtra por código produto PALLET (208000012)
  - Cria sugestões de vinculação (`vinculacao='SUGESTAO'`)
  - Retornos com NF referenciada são vinculados automaticamente (`vinculacao='AUTOMATICO'`)
  - Exclui CNPJs intercompany (Nacom/La Famiglia)
- **Arquivos**:
  - `app/pallet/services/match_service.py` (~986 linhas)
  - `app/pallet/routes/tratativa_nfs.py` (rotas adicionadas/corrigidas)

#### 5.3 Listagem de Movimentações (Requisito do Usuário)

##### 5.3.1 Criar tela de listagem consolidada
- [x] **Status**: ✅ CONCLUÍDO (25/01/2026)
- **Filtros implementados** (conforme resposta do usuário):
  - NF de venda (via Embarque → EmbarqueItem → NF) ✅
  - NF de remessa (PalletNFRemessa) ✅
  - Cliente (cnpj_destinatario quando tipo_destinatario='CLIENTE') ✅
  - Transportadora (cnpj_destinatario quando tipo_destinatario='TRANSPORTADORA', ou via Embarque.transportadora) ✅
  - Data (data_de, data_ate) ✅
  - UF (PalletCredito.uf_responsavel) ✅
  - Cidade (PalletCredito.cidade_responsavel) ✅
  - Status (ATIVA, RESOLVIDA, CANCELADA) ✅
  - Tipo Destinatário (TRANSPORTADORA, CLIENTE) ✅
- **Campos exibidos**: NF Remessa, Emissão, Tipo, Destinatário, Transportadora, NF Venda, UF, Cidade, Qtd, Saldo, Status
- **Funcionalidades extras**:
  - Exportação para CSV via API
  - Paginação com filtros preservados
  - Stats cards (total registros, total pallets, saldo pendente, ativas, resolvidas, canceladas)
- **Arquivos criados/modificados**:
  - `app/pallet/routes/movimentacoes.py` (~450 linhas) - Rota e API de exportação
  - `app/templates/pallet/v2/movimentacoes/listagem.html` (~350 linhas) - Template
  - `app/pallet/routes/__init__.py` - Registro do blueprint
  - `app/templates/pallet/v2/dashboard.html` - Link de acesso rápido
- **Acesso**: Dashboard Gestão de Pallets > Botão "Movimentações" ou /pallet/v2/movimentacoes/

---

### FASE 6: TESTES E VALIDAÇÃO
**Prioridade**: ALTA | **Após**: Fase 4

#### 6.1 Testes de Migração
- [x] **6.1.1** Validar migração de dados existentes ✅ (25/01/2026 - 28 testes)
- [x] **6.1.2** Comparar totais antes/depois ✅ (25/01/2026 - 28 testes)
- [x] **6.1.3** Verificar integridade referencial ✅ (25/01/2026 - 28 testes)

#### 6.2 Testes Funcionais
- [x] **6.2.1** Testar fluxo completo: NF remessa → Crédito → Solução ✅ (25/01/2026)
- [x] **6.2.2** Testar fluxo completo: NF remessa → Devolução → Vinculação ✅ (25/01/2026)
- [x] **6.2.3** Testar independência dos domínios ✅ (25/01/2026) - Coberto em 6.2.2
- [x] **6.2.4** Testar match automático ✅ (25/01/2026) - Coberto em 6.2.2

#### 6.3 Validação de Negócio
- [ ] **6.3.1** Validar com usuário: Dashboard
- [ ] **6.3.2** Validar com usuário: Fluxo Domínio A
- [ ] **6.3.3** Validar com usuário: Fluxo Domínio B

---

## CRITÉRIOS DE ACEITE (da spec)

| # | Critério | Status |
|---|----------|--------|
| 1 | NF de remessa cria automaticamente registro de crédito | ✅ (testado) |
| 2 | Crédito pode ser resolvido independente da NF | ✅ (testado) |
| 3 | NF pode ser resolvida independente do crédito | ✅ (testado em 6.2.2) |
| 4 | Venda de pallets permite N NFs remessa → 1 NF venda | ✅ (testado) |
| 5 | Substituição transfere responsabilidade com rastreabilidade | ✅ (testado) |
| 6 | Devolução permite 1 NF → N NFs remessa com confirmação | ✅ (testado em 6.2.2) |
| 7 | Retorno vincula automaticamente 1:1 por informações complementares | ✅ (testado em 6.2.2) |
| 8 | Cancelamento mantém registro para auditoria | ✅ (testado - 13 testes em test_cancelamento_auditoria.py) |
| 9 | UI separa claramente os dois domínios | ⬜ |
| 10 | Dados históricos migrados corretamente | ⬜ |

---

## QUESTÕES EM ABERTO (da spec)

1. **Prazos de cobrança**: Manter lógica atual (7 dias SP/RED, 30 dias demais) ou parametrizar?
Sim, manter
2. **Relatórios**: Quais relatórios são necessários para cada domínio?
Relatórios ainda não implementaremos, mas é necessario uma listagem com todas as movimentações podendo filtrar por
- NF de venda (relacionada à NF de remessa através de Embarque / EmbarqueItem)
- NF de remessa
- Cliente (Quando houver)
- Transportadora (Seja como destinatario da NF ou transportadora da NF de um cliente, relacionado por Embarque.transportadora)
- Data
- UF
- Cidade
3. **Notificações**: Alertas automáticos para vales próximos do vencimento?
Não é necessario nesse momento.
---

## NOTAS DE IMPLEMENTAÇÃO

### Compatibilidade com Sistema Atual

Durante a transição, manter:
- `MovimentacaoEstoque` com `local_movimentacao='PALLET'` funcionando
- `ValePallet` acessível (read-only após migração)
- Routes antigos redirecionando para novos

### Campos do Embarque (Manter - Grupo 2)

Os campos de pallet físico em `Embarque`/`EmbarqueItem` continuam existindo:
- `Embarque.nf_pallet_transportadora`
- `Embarque.qtd_pallet_transportadora`
- `Embarque.qtd_pallets_separados`
- `Embarque.qtd_pallets_trazidos`
- `EmbarqueItem.nf_pallet_cliente`
- `EmbarqueItem.qtd_pallet_cliente`

Estes campos são do **Grupo 2 (Pallets Físicos)** e NÃO serão afetados pela reestruturação.

### Integração Futura

Ao preencher `nf_pallet_*` no Embarque/EmbarqueItem:
- Sistema PODE criar `PalletNFRemessa` automaticamente
- OU usuário vincula manualmente a uma existente
- Decisão: implementar na Fase 5 ou posterior

---

## RESUMO DE PROGRESSO (Atualizado 25/01/2026 - Sessão 12)

### Status por Fase

| Fase | Tarefas | Concluídas | Pendentes | Status |
|------|---------|------------|-----------|--------|
| 1. Infraestrutura | 11 | 11 | 0 | ✅ **CONCLUÍDO** |
| 2. Backend | 5 | 5 | 0 | ✅ **CONCLUÍDO** |
| 3. Routes | 6 | 6 | 0 | ✅ **CONCLUÍDO** |
| 4. Frontend | 15 | 15 | 0 | ✅ **CONCLUÍDO** |
| 5. Integração | 4 | 4 | 0 | ✅ **CONCLUÍDO** |
| 6. Testes | 9 | 7 | 2 | ⏳ EM PROGRESSO (apenas validação com usuário restante) |
| **TOTAL** | **50** | **48** | **2** | 🟢 **96% Completo** |

### Fase 6 - Testes (⏳ EM PROGRESSO)

| Item | Status | Arquivo | Testes |
|------|--------|---------|--------|
| 6.1.1-3 Testes de migração | ✅ | `tests/pallet/test_migracao.py` | 28 |
| 6.2.1 Fluxo NF→Crédito→Solução | ✅ | `tests/pallet/test_fluxo_nf_credito_solucao.py` | 14 |
| 6.2.2 Fluxo NF→Devolução→Vinculação | ✅ | `tests/pallet/test_fluxo_nf_devolucao_vinculacao.py` | 24 |
| 6.2.3 Independência dos domínios | ✅ | Coberto em 6.2.2 (TestIndependenciaDominios) | 2 |
| 6.2.4 Match automático | ✅ | Coberto em 6.2.2 (TestMatchAutomatico) | 6 |
| 6.2.5 Auditoria de cancelamento | ✅ | `tests/pallet/test_cancelamento_auditoria.py` | 13 |
| 6.3.1-3 Validação com usuário | ⬜ | Pendente (requer interação) | - |

**Total de testes implementados**: 79 testes passando
- `tests/pallet/test_migracao.py`: 28 testes
- `tests/pallet/test_fluxo_nf_credito_solucao.py`: 14 testes
- `tests/pallet/test_fluxo_nf_devolucao_vinculacao.py`: 24 testes
- `tests/pallet/test_cancelamento_auditoria.py`: 13 testes

**Classes de teste (migração)**:
- `TestTabelasExistem`: Verificar existência de tabelas V2
- `TestCriacaoDadosMigracao`: Validar criação de dados após migração
- `TestConsistenciaQuantidades`: Saldo <= Original, soma soluções
- `TestConsistenciaStatus`: Status consistente com saldo
- `TestIntegridadeReferencialCreditoNF`: FK crédito → NF remessa
- `TestIntegridadeReferencialDocumentoCredito`: FK documento → crédito
- `TestIntegridadeReferencialSolucaoCredito`: FK solução → crédito
- `TestIntegridadeReferencialNFSolucaoNFRemessa`: FK NF solução → NF remessa
- `TestUnicidade`: Chaves únicas (numero_nf+serie, chave_nfe)
- `TestFormatoDados`: Formato CNPJ (11/14 dígitos)
- `TestFuncoesValidacao`: Funções auxiliares de validação
- `TestRelacionamentosBidirecionais`: Backrefs funcionando

**Classes de teste (fluxo devolução/vinculação)**:
- `TestVinculacaoManualDevolucao`: Vinculação manual 1:N
- `TestVinculacaoManualRetorno`: Vinculação manual 1:1
- `TestSugestaoVinculacao`: Criar, confirmar e rejeitar sugestões
- `TestMatchAutomatico`: Extração de NF referenciada, score de match
- `TestCalculoScore`: Algoritmo de pontuação de candidatas
- `TestHelpersCNPJ`: Limpeza e validação de CNPJs
- `TestValidacoesSolucaoNF`: Validações de regras de negócio
- `TestIndependenciaDominios`: Separação Domínio A × Domínio B

**Classes de teste (auditoria de cancelamento)**:
- `TestCamposAuditoriaCancelamento`: Campos de auditoria preenchidos corretamente
- `TestValidacoesCancelamento`: Validações (motivo obrigatório, usuário obrigatório, NF inexistente)
- `TestSoftDeleteCancelamento`: Soft delete (registro não é deletado, relacionamentos mantidos)
- `TestMetodoCancelarModelo`: Método cancelar() do modelo PalletNFRemessa
- `TestSerializacaoCancelamento`: to_dict() inclui campos de cancelamento

### Fase 1.3 - Scripts de Migração de Dados (✅ CONCLUÍDA)

| Item | Status | Arquivo | Linhas |
|------|--------|---------|--------|
| 1.3.1 Migrar MovimentacaoEstoque | ✅ | `scripts/pallet/002_migrar_movimentacao_para_nf_remessa.py` | ~430 |
| 1.3.2 Migrar ValePallet | ✅ | `scripts/pallet/003_migrar_vale_pallet_para_documento.py` | ~560 |
| 1.3.3 Validar migração | ✅ | `scripts/pallet/004_validar_migracao.py` | ~913 |

### Fase 5 - Detalhamento (✅ CONCLUÍDA)

| Item | Status | Arquivo | Linhas |
|------|--------|---------|--------|
| 5.1.1 Identificar arquivo devoluções | ✅ | Análise app/devolucao/ | - |
| 5.1.2 Adicionar filtro pallet | ✅ | `app/devolucao/services/nfd_service.py` | ~50 |
| 5.2.1 Job DFe para pallets | ✅ | `app/pallet/services/match_service.py` | ~986 |
| 5.3.1 Listagem Movimentações | ✅ | `app/pallet/routes/movimentacoes.py` | ~450 |

**Novas rotas v2**:
- `GET /pallet/v2/movimentacoes/` - Listagem consolidada com filtros
- `GET /pallet/v2/movimentacoes/api/exportar` - API de exportação JSON
- `GET /pallet/v2/movimentacoes/api/cidades` - API de cidades por UF

### Fase 3 - Detalhamento (✅ CONCLUÍDA)

| Item | Status | Arquivo | Linhas |
|------|--------|---------|--------|
| 3.1.1 Blueprint principal | ✅ | `app/pallet/routes/__init__.py` | ~55 |
| 3.1.2 Dashboard | ✅ | `app/pallet/routes/dashboard.py` | ~270 |
| 3.1.3 NF Remessa | ✅ | `app/pallet/routes/nf_remessa.py` | ~320 |
| 3.1.4 Controle Pallets | ✅ | `app/pallet/routes/controle_pallets.py` | ~640 |
| 3.1.5 Tratativa NFs | ✅ | `app/pallet/routes/tratativa_nfs.py` | ~550 |
| 3.2.1 Deprecar routes | ✅ | `app/pallet/routes_legacy.py` | ~1550 |

**Rotas registradas**:
- v1 (legacy): 22 rotas em `/pallet/...` com warnings de deprecação
- v2 (novo): 35 rotas em `/pallet/v2/...`

### Fase 2 - Detalhamento (✅ CONCLUÍDA)

| Item | Status | Arquivo | Linhas |
|------|--------|---------|--------|
| 2.1.1 CreditoService | ✅ | `app/pallet/services/credito_service.py` | 797 |
| 2.1.2 SolucaoPalletService | ✅ | `app/pallet/services/solucao_pallet_service.py` | 642 |
| 2.2.1 NFService | ✅ | `app/pallet/services/nf_service.py` | 896 |
| 2.2.2 MatchService | ✅ | `app/pallet/services/match_service.py` | ~750 |
| 2.3.1 sync_odoo_service | ✅ | `app/pallet/services/sync_odoo_service.py` | ~850 |

### Fase 1 - Detalhamento (✅ CONCLUÍDA)

| Item | Status | Arquivo |
|------|--------|---------|
| 1.1.1 PalletNFRemessa | ✅ | `app/pallet/models/nf_remessa.py` |
| 1.1.2 PalletCredito | ✅ | `app/pallet/models/credito.py` |
| 1.1.3 PalletDocumento | ✅ | `app/pallet/models/documento.py` |
| 1.1.4 PalletSolucao | ✅ | `app/pallet/models/solucao.py` |
| 1.1.5 PalletNFSolucao | ✅ | `app/pallet/models/nf_solucao.py` |
| 1.1.6 models/__init__.py | ✅ | `app/pallet/models/__init__.py` |
| 1.2.1 Migration Python | ✅ | `scripts/pallet/001_criar_tabelas_pallet_v2.py` |
| 1.2.2 Migration SQL | ✅ | `scripts/pallet/001_criar_tabelas_pallet_v2.sql` |

### Estrutura Atual (Pós Fase 3)

```
app/pallet/
├── __init__.py          ✅ Existe (7 linhas)
├── routes_legacy.py     ✅ Renomeado (~1550 linhas) - Routes v1 DEPRECATED
├── utils.py             ✅ Existe (~50 linhas)
├── cli.py               ✅ Existe
├── models/              ✅ CRIADO (Fase 1)
│   ├── __init__.py      ✅ Criado (exporta todos os modelos)
│   ├── vale_pallet.py   ✅ Criado (modelo legado)
│   ├── nf_remessa.py    ✅ Criado (PalletNFRemessa)
│   ├── credito.py       ✅ Criado (PalletCredito)
│   ├── documento.py     ✅ Criado (PalletDocumento)
│   ├── solucao.py       ✅ Criado (PalletSolucao)
│   └── nf_solucao.py    ✅ Criado (PalletNFSolucao)
├── routes/              ✅ CRIADO (Fase 3 + Fase 5) - Blueprint v2
│   ├── __init__.py      ✅ Criado (~60 linhas) - Hub de registro
│   ├── dashboard.py     ✅ Criado (~270 linhas) - Dashboard 3 tabs
│   ├── nf_remessa.py    ✅ Criado (~320 linhas) - CRUD NF Remessa
│   ├── controle_pallets.py ✅ Criado (~640 linhas) - Domínio A
│   ├── tratativa_nfs.py ✅ Criado (~550 linhas) - Domínio B
│   └── movimentacoes.py ✅ CRIADO (~450 linhas) - Listagem consolidada (Fase 5)
└── services/            ✅ CRIADO (Fase 2)
    ├── __init__.py           ✅ Atualizado (exporta todos os services)
    ├── emissao_nf_pallet.py  ✅ Existe (manter)
    ├── sync_odoo_service.py  ✅ MODIFICADO (integrado com novos models v2)
    ├── credito_service.py    ✅ CRIADO (797 linhas)
    ├── solucao_pallet_service.py ✅ CRIADO (642 linhas)
    ├── nf_service.py         ✅ CRIADO (896 linhas)
    └── match_service.py      ✅ CRIADO (~750 linhas)

scripts/pallet/          ✅ COMPLETO
├── 001_criar_tabelas_pallet_v2.py   ✅ Criado
├── 001_criar_tabelas_pallet_v2.sql  ✅ Criado
├── 002_migrar_movimentacao_para_nf_remessa.py  ✅ Criado (~430 linhas)
├── 002_migrar_movimentacao_para_nf_remessa.sql ✅ Criado (~150 linhas)
├── 003_migrar_vale_pallet_para_documento.py    ✅ Criado (~560 linhas)
├── 003_migrar_vale_pallet_para_documento.sql   ✅ Criado (~220 linhas)
├── 004_validar_migracao.py    ✅ CRIADO (Sessão 12, ~913 linhas) - 14 verificações
└── 004_validar_migracao.sql   ✅ CRIADO (Sessão 12, ~427 linhas) - SQL para Render Shell

app/templates/pallet/
├── 13 arquivos          ✅ Existem (migrar/deprecar na Fase 4)
├── v2/                  ✅ CRIADO (Fase 4 + Fase 5)
│   ├── dashboard.html   ✅ CRIADO (~950 linhas) - Atualizado com link Movimentações
│   ├── controle_pallets/
│   │   ├── vales.html   ✅ CRIADO (~1031 linhas)
│   │   ├── solucoes.html ✅ CRIADO (~1100 linhas) - Com modais integrados
│   │   └── historico.html ✅ CRIADO (~400 linhas)
│   ├── tratativa_nfs/
│   │   ├── direcionamento.html ✅ CRIADO (~700 linhas) - Com modais devolução/retorno
│   │   ├── sugestoes.html ✅ CRIADO (~700 linhas) - Com modais confirmar/rejeitar/detalhes
│   │   ├── solucoes.html ✅ CRIADO (~700 linhas) - Histórico com modal detalhes
│   │   └── canceladas.html ✅ CRIADO (~600 linhas) - NFs canceladas para auditoria
│   ├── nf_remessa/
│   │   ├── detalhe.html  ✅ CRIADO (~700 linhas) - Detalhe NF com 2 domínios
│   │   └── listagem.html ✅ CRIADO (~400 linhas) - Listagem com filtros
│   └── movimentacoes/   ✅ CRIADO (Fase 5)
│       └── listagem.html ✅ CRIADO (~350 linhas) - Listagem consolidada com filtros
```

### Dependências Confirmadas

| Dependência | Status | Localização |
|-------------|--------|-------------|
| MovimentacaoEstoque | ✅ Verificado | app/estoque/models.py:22-205 |
| ValePallet | ✅ Migrado | app/pallet/models/vale_pallet.py |
| Embarque (Grupo 2) | ✅ Documentado | CLAUDE.md (não modificar) |
| Módulo Devolução | ✅ Identificado | app/devolucao/ (16 arquivos) |
| DFe/Validação | ✅ Verificado | app/recebimento/models.py:304+ |

---

## PRÓXIMA AÇÃO

### ✅ Fase 1 e 2 Concluídas

**Para criar as tabelas no banco de dados** (se ainda não executado):
```bash
# Opção 1: Script Python (local)
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python scripts/pallet/001_criar_tabelas_pallet_v2.py

# Opção 2: SQL direto no Render Shell
psql $DATABASE_URL < scripts/pallet/001_criar_tabelas_pallet_v2.sql
```

### ✅ Fase 4 Concluída (Frontend/UI)

**Todos os templates v2 criados** (15 arquivos, ~8000 linhas):

| Arquivo | Descrição | Linhas |
|---------|-----------|--------|
| `dashboard.html` | Dashboard com 3 tabs | ~945 |
| `controle_pallets/vales.html` | Listagem de documentos | ~1031 |
| `controle_pallets/solucoes.html` | Créditos com 4 modais | ~1100 |
| `controle_pallets/historico.html` | Histórico soluções | ~400 |
| `tratativa_nfs/direcionamento.html` | NFs aguardando | ~700 |
| `tratativa_nfs/sugestoes.html` | Sugestões automáticas | ~700 |
| `tratativa_nfs/solucoes.html` | Soluções confirmadas | ~700 |
| `tratativa_nfs/canceladas.html` | NFs canceladas | ~600 |
| `nf_remessa/detalhe.html` | Detalhe com 2 domínios | ~700 |
| `nf_remessa/listagem.html` | Listagem com filtros | ~400 |

### ✅ Fase 5 Concluída (Integração) - 100%

**Todas as tarefas da Fase 5 concluídas**:
- [x] 5.1.1 Identificar arquivo de devoluções ✅
- [x] 5.1.2 Adicionar filtro para excluir devoluções de pallet do módulo de devolução ✅
- [x] 5.2.1 Criar job/task para identificar NFs de pallet no DFe ✅ (Sessão 9)
- [x] 5.3.1 Criar tela de listagem consolidada de movimentações ✅ (Sessão 10)

**APIs disponíveis**:
- `GET /pallet/v2/movimentacoes/` - Listagem consolidada com filtros
- `GET /pallet/v2/movimentacoes/api/exportar` - API de exportação JSON/CSV
- `GET /pallet/v2/movimentacoes/api/cidades` - API de cidades por UF
- `POST /pallet/v2/tratativa/processar-devolucoes` - Processamento manual
- `POST /pallet/v2/tratativa/api/processar-devolucoes` - API JSON para jobs

**⚠️ Antes de testar, executar migrations**:
```bash
# Opção 1: Script Python (local)
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python scripts/pallet/001_criar_tabelas_pallet_v2.py
python scripts/devolucao/001_adicionar_campo_pallet.py
python scripts/devolucao/002_detectar_nfds_pallet_existentes.py

# Opção 2: SQL direto no Render Shell
psql $DATABASE_URL < scripts/pallet/001_criar_tabelas_pallet_v2.sql
psql $DATABASE_URL < scripts/devolucao/001_adicionar_campo_pallet.sql
```

**Comando para continuar Ralph Loop**:
```bash
./ralph-loop.sh 10  # Executa 10 iterações do Ralph Loop
```

**Ordem de implementação restante**:
1. ~~**Fase 1** (BLOQUEADORA) → Criar models e migrations~~ ✅
2. ~~**Fase 2** → Implementar services~~ ✅
3. ~~**Fase 3** → Criar routes/APIs~~ ✅
4. ~~**Fase 4** → Criar templates/UI~~ ✅
5. **Fase 5** → Integração com devolução e DFe (EM PROGRESSO - 75%)
6. **Fase 6** → Testes e validação
