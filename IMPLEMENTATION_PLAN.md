# IMPLEMENTATION PLAN: Reestruturação do Módulo de Gestão de Pallets

**Spec**: `.claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md`
**Versão**: 1.2.0
**Data**: 25/01/2026
**Status**: EM PROGRESSO - Fase 4 Frontend
**Última Análise**: 25/01/2026 12:40 (Sessão 3 - Templates solucoes.html e historico.html criados)

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
- [ ] **Status**: NÃO INICIADO
- Migrar `MovimentacaoEstoque` onde `local_movimentacao='PALLET'` e `tipo_movimentacao='REMESSA'`
- Para cada remessa: criar `PalletNFRemessa` + `PalletCredito`

##### 1.3.2 Criar `scripts/pallet/003_migrar_vale_pallet_para_documento.py`
- [ ] **Status**: NÃO INICIADO
- Migrar `ValePallet` para `PalletDocumento`
- Vincular a `PalletCredito` correto via `nf_pallet`
- Se vale resolvido, criar `PalletSolucao` correspondente

##### 1.3.3 Criar `scripts/pallet/004_validar_migracao.py`
- [ ] **Status**: NÃO INICIADO
- Verificar integridade referencial
- Comparar totais migrados
- Relatório de discrepâncias

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
  - Busca campos adicionais do Odoo: `company_id`, `l10n_br_chave_nfe`
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

##### 4.3.2 Criar `app/templates/pallet/tratativa_nfs/solucoes.html`
- [ ] **Status**: NÃO INICIADO
- Listagem de soluções de NF
- Devoluções e retornos registrados

##### 4.3.3 Modais/formulários:
- [x] `Modal Vincular Devolução (1:N)` - ✅ Integrado em direcionamento.html
- [x] `Modal Vincular Retorno (1:1)` - ✅ Integrado em direcionamento.html
- [ ] `Modal Confirmar Sugestão` - Pendente, será integrado em sugestoes.html

#### 4.4 Template de Detalhe

##### 4.4.1 Criar `app/templates/pallet/nf_remessa/detalhe.html`
- [ ] **Status**: NÃO INICIADO
- Dados da NF
- Status dos dois domínios lado a lado
- Histórico de documentos e soluções
- Ações contextuais

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
- [ ] **Status**: NÃO INICIADO
- **Arquivos a modificar**:
  - `app/devolucao/services/nfd_service.py` - Adicionar filtro na importação
  - `app/devolucao/routes/vinculacao_routes.py` - Filtrar na listagem de órfãs
- **Filtros a aplicar**:
  - Excluir CFOP 5920/6920 (remessa/devolução vasilhame)
  - Excluir CFOP 1920/2920 (entrada para devolução vasilhame)
  - Excluir produto código `208000012` (PALLET)

```python
# Arquivos: app/devolucao/services/nfd_service.py, app/devolucao/routes/vinculacao_routes.py
# Adicionar na query de importação/listagem:
CFOP_PALLET = ['5920', '6920', '1920', '2920']
CODIGO_PALLET = '208000012'

def filtrar_devolucoes_produto(query):
    """Exclui devoluções de pallet do módulo de devoluções de produtos."""
    return query.filter(
        ~DFe.cfop.in_(CFOP_PALLET),
        ~DFe.produto_codigo.contains(CODIGO_PALLET)
    )
```

#### 5.2 Consumir DFe para Match Automático

##### 5.2.1 Criar job/task para identificar NFs de pallet no DFe
- [ ] **Status**: NÃO INICIADO
- **Objetivo**: Buscar NFs de entrada com CFOP de devolução vasilhame e direcioná-las para o módulo de pallet
- **Lógica**:
  1. Consultar tabela `dfe` (sincronizada do Odoo) com filtro CFOP IN ('1920', '2920')
  2. Verificar se `produto_codigo` contém '208000012' (PALLET)
  3. Criar registro em `pallet_nf_solucoes` com tipo='DEVOLUCAO' e vinculacao='SUGESTAO'
  4. Usar `match_service.sugerir_vinculacao_devolucao()` para encontrar NF remessa original
- **Campos do DFe úteis** (modelo em `app/recebimento/models.py:304-394` - ValidacaoFiscalDfe):
  - `odoo_dfe_id`, `numero_nf`, `chave_nfe`
  - `cnpj_fornecedor`, `razao_fornecedor`
  - Para CFOP: consultar Odoo via `l10n_br_fiscal.document.line`
  - Para produto: consultar Odoo via `l10n_br_fiscal.document.line.product_id`
- **Nota**: O modelo local não tem campo CFOP. Será necessário consultar Odoo diretamente ou adicionar campo ao modelo.

#### 5.3 Listagem de Movimentações (Requisito do Usuário)

##### 5.3.1 Criar tela de listagem consolidada
- [ ] **Status**: NÃO INICIADO
- **Filtros obrigatórios** (conforme resposta do usuário):
  - NF de venda (via Embarque → EmbarqueItem → NF)
  - NF de remessa (PalletNFRemessa)
  - Cliente (cnpj_destinatario quando tipo_destinatario='CLIENTE')
  - Transportadora (cnpj_destinatario quando tipo_destinatario='TRANSPORTADORA', ou via Embarque.transportadora)
  - Data
  - UF
  - Cidade
- **Campos a exibir**: Todos os campos relevantes + saldo atual de crédito

---

### FASE 6: TESTES E VALIDAÇÃO
**Prioridade**: ALTA | **Após**: Fase 4

#### 6.1 Testes de Migração
- [ ] **6.1.1** Validar migração de dados existentes
- [ ] **6.1.2** Comparar totais antes/depois
- [ ] **6.1.3** Verificar integridade referencial

#### 6.2 Testes Funcionais
- [ ] **6.2.1** Testar fluxo completo: NF remessa → Crédito → Solução
- [ ] **6.2.2** Testar fluxo completo: NF remessa → Devolução → Vinculação
- [ ] **6.2.3** Testar independência dos domínios
- [ ] **6.2.4** Testar match automático

#### 6.3 Validação de Negócio
- [ ] **6.3.1** Validar com usuário: Dashboard
- [ ] **6.3.2** Validar com usuário: Fluxo Domínio A
- [ ] **6.3.3** Validar com usuário: Fluxo Domínio B

---

## CRITÉRIOS DE ACEITE (da spec)

| # | Critério | Status |
|---|----------|--------|
| 1 | NF de remessa cria automaticamente registro de crédito | ⬜ |
| 2 | Crédito pode ser resolvido independente da NF | ⬜ |
| 3 | NF pode ser resolvida independente do crédito | ⬜ |
| 4 | Venda de pallets permite N NFs remessa → 1 NF venda | ⬜ |
| 5 | Substituição transfere responsabilidade com rastreabilidade | ⬜ |
| 6 | Devolução permite 1 NF → N NFs remessa com confirmação | ⬜ |
| 7 | Retorno vincula automaticamente 1:1 por informações complementares | ⬜ |
| 8 | Cancelamento mantém registro para auditoria | ⬜ |
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

## RESUMO DE PROGRESSO (Atualizado 25/01/2026 - Sessão 4)

### Status por Fase

| Fase | Tarefas | Concluídas | Pendentes | Status |
|------|---------|------------|-----------|--------|
| 1. Infraestrutura | 8 | 8 | 0 | ✅ **CONCLUÍDO** |
| 2. Backend | 5 | 5 | 0 | ✅ **CONCLUÍDO** |
| 3. Routes | 6 | 6 | 0 | ✅ **CONCLUÍDO** |
| 4. Frontend | 14 | 9 | 5 | 🟡 EM PROGRESSO |
| 5. Integração | 4 | 1 (análise) | 3 | ⏳ Aguardando |
| 6. Testes | 9 | 0 | 9 | ⏳ Aguardando |
| **TOTAL** | **46** | **29** | **17** | 🟢 **63% Completo** |

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
├── routes/              ✅ CRIADO (Fase 3) - Blueprint v2
│   ├── __init__.py      ✅ Criado (~55 linhas) - Hub de registro
│   ├── dashboard.py     ✅ Criado (~270 linhas) - Dashboard 3 tabs
│   ├── nf_remessa.py    ✅ Criado (~320 linhas) - CRUD NF Remessa
│   ├── controle_pallets.py ✅ Criado (~640 linhas) - Domínio A
│   └── tratativa_nfs.py ✅ Criado (~550 linhas) - Domínio B
└── services/            ✅ CRIADO (Fase 2)
    ├── __init__.py           ✅ Atualizado (exporta todos os services)
    ├── emissao_nf_pallet.py  ✅ Existe (manter)
    ├── sync_odoo_service.py  ✅ MODIFICADO (integrado com novos models v2)
    ├── credito_service.py    ✅ CRIADO (797 linhas)
    ├── solucao_pallet_service.py ✅ CRIADO (642 linhas)
    ├── nf_service.py         ✅ CRIADO (896 linhas)
    └── match_service.py      ✅ CRIADO (~750 linhas)

scripts/pallet/          ✅ CRIADO
├── 001_criar_tabelas_pallet_v2.py   ✅ Criado
└── 001_criar_tabelas_pallet_v2.sql  ✅ Criado

app/templates/pallet/
├── 13 arquivos          ✅ Existem (migrar/deprecar na Fase 4)
├── v2/                  ✅ CRIADO (Fase 4 - Em Progresso)
│   ├── dashboard.html   ✅ CRIADO (~945 linhas)
│   ├── controle_pallets/
│   │   ├── vales.html   ✅ CRIADO (~1031 linhas)
│   │   ├── solucoes.html ✅ CRIADO (~1100 linhas) - Com modais integrados
│   │   └── historico.html ✅ CRIADO (~400 linhas)
│   ├── tratativa_nfs/
│   │   └── direcionamento.html ✅ CRIADO (~700 linhas) - Com modais devolução/retorno
│   └── nf_remessa/      ❌ VAZIO (Fase 4)
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

### Próximo Passo: Fase 4 (Criar Templates/UI)

**Fase 3 - Routes concluídos** (35 rotas v2 + 22 rotas v1 deprecated):
1. ✅ `app/pallet/routes/__init__.py` - Blueprint principal
2. ✅ `app/pallet/routes/dashboard.py` - Dashboard 3 tabs
3. ✅ `app/pallet/routes/nf_remessa.py` - CRUD NF Remessa
4. ✅ `app/pallet/routes/controle_pallets.py` - Domínio A (créditos, documentos, soluções)
5. ✅ `app/pallet/routes/tratativa_nfs.py` - Domínio B (vinculação, sugestões)
6. ✅ `app/pallet/routes_legacy.py` - Routes v1 com warnings de deprecação

**Pendente - Fase 4** (5 tarefas restantes):
- ✅ 4.1.1 Criar `app/templates/pallet/v2/dashboard.html` - Dashboard principal ✅ CONCLUÍDO
- ✅ 4.2.1 Criar `app/templates/pallet/v2/controle_pallets/vales.html` - Listagem documentos ✅ CONCLUÍDO
- ✅ 4.2.2 Criar `app/templates/pallet/v2/controle_pallets/solucoes.html` - Listagem créditos ✅ CONCLUÍDO
- ✅ 4.2.3 Criar `app/templates/pallet/v2/controle_pallets/historico.html` - Histórico soluções ✅ CONCLUÍDO
- ✅ 4.2.4 Criar modais: baixa, venda, recebimento, substituição (integrados em solucoes.html) ✅ CONCLUÍDO
- ✅ 4.5.1 Modificar `app/templates/base.html` - Link no menu ✅ CONCLUÍDO
- ✅ 4.3.1 Criar `app/templates/pallet/v2/tratativa_nfs/direcionamento.html` ✅ CONCLUÍDO (Com modais devolução/retorno)
- 4.3.2 Criar `app/templates/pallet/v2/tratativa_nfs/sugestoes.html`
- 4.3.3 Criar `app/templates/pallet/v2/tratativa_nfs/solucoes.html`
- 4.3.4 Criar `app/templates/pallet/v2/tratativa_nfs/canceladas.html`
- 4.4.1 Criar `app/templates/pallet/v2/nf_remessa/detalhe.html`

**Comando para continuar**:
```bash
./ralph-loop.sh 10  # Executa 10 iterações do Ralph Loop
```

**Ordem de implementação restante**:
1. ~~**Fase 1** (BLOQUEADORA) → Criar models e migrations~~ ✅
2. ~~**Fase 2** → Implementar services~~ ✅
3. ~~**Fase 3** → Criar routes/APIs~~ ✅
4. **Fase 4** → Criar templates/UI (PRÓXIMO)
5. **Fase 5** → Integração com devolução e DFe
6. **Fase 6** → Testes e validação
