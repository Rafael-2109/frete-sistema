# Modulo Devolucao — Guia para Claude Code

**Ultima Atualizacao**: 22/04/2026
**Stats**: ~13.9K LOC Python (17 arquivos) + 7 templates + 32 migrations
**Versao**: 3.0.0 (Fase 1-4.5 prod, Fase 5-6 pendentes)

> Este CLAUDE.md e o **ponto de entrada** para o modulo Devolucao.
> Detalhes profundos (APIs, modelos, fluxos) estao em sub-documentos.
> Para historico narrativo/changelog das fases, ler `README.md` (docstring de produto).

---

## Sub-documentacao

| Precisa de... | Documento |
|---------------|-----------|
| APIs completas (6 blueprints, ~80 endpoints) | [CLAUDE_APIS.md](CLAUDE_APIS.md) |
| Modelos, relacionamentos, gotchas de schema | [CLAUDE_MODELOS.md](CLAUDE_MODELOS.md) |
| Fluxos de dados (importacao Odoo, IA, reversao, sync monitoramento) | [CLAUDE_FLUXOS.md](CLAUDE_FLUXOS.md) |
| Historico do produto e fases de implementacao | [README.md](README.md) |
| Prompts/TODOs em aberto do usuario | [prompt.md](prompt.md) |

---

## O que este modulo faz

Gestao completa de devolucoes de mercadoria — desde o registro inicial no monitoramento ate autorizacao de descarte ou frete de retorno, com resolucao inteligente de De-Para de produto via Claude Haiku.

**Quatro entrypoints de criacao de `NFDevolucao`**:
1. **Manual (monitoramento)** — usuario finaliza entrega e registra NFD (`origem_registro='MONITORAMENTO'`)
2. **Automatico (NFDService)** — importa DFe com `finnfe=4` do Odoo (`origem_registro='ODOO'`) — ver [CLAUDE_FLUXOS.md#importacao-nfd-do-odoo](CLAUDE_FLUXOS.md)
3. **Reversao (ReversaoService)** — NF de venda revertida via `out_refund` no Odoo cria `NFDevolucao` com `tipo_documento='NF'`
4. **Sync Monitoramento (MonitoramentoSyncService)** — entrega com `status_finalizacao in ('Cancelada','Devolvida','Troca de NF')` sem NFD vinculada

Todos os entrypoints **criam `OcorrenciaDevolucao` automaticamente** (1:1 com NFDevolucao).

---

## Arquitetura em uma tela

```
app/devolucao/
  __init__.py                           # Blueprint principal (devolucao_bp, /devolucao)
  models.py                             # 18 modelos SQLAlchemy — ver CLAUDE_MODELOS.md
  routes/
    registro_routes.py                  # /devolucao/registro/* — Fase 1 (manual)
    ocorrencia_routes.py                # /devolucao/ocorrencias/* — Dashboard + detalhe (maior arquivo, 1757 LOC)
    vinculacao_routes.py                # /devolucao/vinculacao/* — Import Odoo + orfaos
    ai_routes.py                        # /devolucao/ai/* — Claude Haiku De-Para
    frete_routes.py                     # /devolucao/frete/* — Frete retorno + descarte
    cadastro_routes.py                  # /devolucao/cadastros/* — CRUD lookup tables + permissoes
  services/
    nfd_service.py                      # Import DFe finnfe=4 do Odoo (1589 LOC)
    reversao_service.py                 # Import NF revertida (out_refund)
    monitoramento_sync_service.py       # Cria NFD de entregas Cancelada/Devolvida/Troca de NF
    nfd_xml_parser.py                   # Parse XML NFD (extrai refNFe, itens, infCpl)
    ai_resolver_service.py              # Claude Haiku 4.5 + Sonnet 4.6 (2578 LOC)
    frete_placeholder_service.py        # Cria Frete fantasma para devolucoes sem frete original

app/templates/devolucao/
  registro/modal_nfd.html               # Modal Fase 1
  ocorrencias/index.html                # Dashboard (~50KB)
  ocorrencias/detalhe.html              # Detalhe (~105KB - GRANDE)
  ocorrencias/_modal_cadastros.html     # Modal CRUD lookups
  ocorrencias/_modal_permissoes.html    # Modal permissoes
  depara/index.html                     # Tela gerenciamento De-Para
  depara/resolver_nfd.html              # Resolver produtos de NFD (via Haiku)
  termo_descarte.html                   # PDF do termo de descarte
```

**Menu**: `base.html:257` — `url_for('devolucao.devolucao_ocorrencia.index')`

---

## Gotchas Criticos

### 1. Nomenclatura confusa: NFD pode ser **NF de venda revertida**
- `NFDevolucao.tipo_documento='NFD'` → Nota Fiscal de Devolucao emitida pelo cliente (ingresso real de mercadoria)
- `NFDevolucao.tipo_documento='NF'` → NF de venda que foi revertida/cancelada (sem movimento fisico)
- Sempre filtrar por `tipo_documento` ao escrever queries especificas.

### 2. CNPJs excluidos globalmente
```python
CNPJS_EXCLUIDOS = {'18467441', '61724241'}  # La Famiglia e Nacom Goya (empresas internas)
```
Definido em **3 lugares** (`nfd_service.py:51`, `reversao_service.py:44`, `ocorrencia_routes.py:36`). Sempre replicar ao adicionar novo callsite.

### 3. Pallets NAO sao devolucoes de produto
`NFDevolucao.e_pallet_devolucao=True` quando CFOPs estao em `CFOPS_PALLET = {'1920','2920','5920','6920','5917','6917','1917','2917'}`. Detectado automaticamente em `NFDService._detectar_nfd_pallet()`. Deve ser tratado no modulo `app/pallet/`, NAO aqui.

**TODA query de listagem/relatorio/agregacao DEVE adicionar `NFDevolucao.e_pallet_devolucao.is_(False)`**. Callsites atuais: `ocorrencia_routes.index`, `api_stats`, `exportar_relatorio` (dashboard stats tambem). Ao criar nova rota que lista/agrega ocorrencias, replicar o filtro.

### 4. Status da ocorrencia e **auto-computado**
`OcorrenciaDevolucao.calcular_status()` (models.py:1048) retorna:
- `PENDENTE` se campos comerciais incompletos
- `EM_ANDAMENTO` se campos completos mas NFD sem entrada (`odoo_status_codigo != '06'`)
- `RESOLVIDO` se campos completos E NFD com entrada (`odoo_status_codigo == '06'`)

**Nunca setar `status` manualmente** — usar o metodo. Os "7 campos comerciais obrigatorios" sao: categorias (N:M ≥1), subcategorias (N:M ≥1), responsavel_id, origem_id, autorizado_por_id, momento_devolucao (!= INDEFINIDO), desfecho.

### 5. Numero de ocorrencia: formato global sequencial
`OcorrenciaDevolucao.gerar_numero_ocorrencia()` retorna `{NNNNN}/{AA}` com sequencia GLOBAL comecando em 17500 (NAO reinicia por mes/ano). Exemplo: `17500/26`, `17501/26`.

### 6. CNPJ vem em dois formatos
- `NFDevolucao.cnpj_emitente` = **raw** (sem mascara, ex: `12345678000190`)
- `FaturamentoProduto.cnpj_cliente` = **formatado** (`12.345.678/0001-90`)
- Para cruzar, usar `app.utils.cnpj_utils.formatar_cnpj()` antes do JOIN. Exemplo em `ocorrencia_routes.py:263`.

### 7. Lookup tables com FK + legado varchar (cache denormalizado)
`OcorrenciaDevolucao` tem **ambos**: campos varchar (`categoria`, `responsavel`, etc.) E FKs (`responsavel_id`, `origem_id`, `autorizado_por_id`). Relacionamentos N:M para `categorias` e `subcategorias` via tabelas de juncao (`ocorrencia_devolucao_categoria`, `ocorrencia_devolucao_subcategoria`). Ao atualizar, **gravar em ambos** (ver `api_atualizar_comercial` em `ocorrencia_routes.py:664`).

### 8. Permissoes granulares para CRUD de lookups
`cadastro_routes.py:43` (`_verificar_permissao_cadastro`):
- Perfis `administrador` e `gerente_comercial` → acesso total automatico
- Outros perfis → precisam de registro em `PermissaoCadastroDevolucao` com flags `pode_criar`/`pode_editar`/`pode_excluir`

### 9. Data de resolucao ≠ data de entrada
Mencionado em `prompt.md` como pendencia. NFDs podem ter `data_resolucao` (ocorrencia) diferente de `data_entrada` (NFD no Odoo). Investigar caso `/devolucao/ocorrencias/5004`.

### 10. `abort(4xx)` NAO funciona
Global exception handler faz re-raise. **SEMPRE** usar `return jsonify({'erro': '...'}), N`. Regra global — ver `memory/app_abort_4xx_gotcha.md`.

### 11. CNPJ_EXCLUIDOS em filtros do dashboard
`ocorrencia_routes.py:83-89` filtra por `NOT LIKE '{prefixo}%'` no `cnpj_emitente`. Ao adicionar filtros/agregacoes, **sempre replicar** o filtro de exclusao.

---

## Integracao com outros modulos

| Modulo | Ponto de integracao |
|--------|---------------------|
| `app/monitoramento` | `EntregaMonitorada.teve_devolucao` (bool) + `EntregaMonitorada.nfs_devolucao` (1:N via `entrega_monitorada_id`). Import em `monitoramento/routes.py:48` |
| `app/fretes` | `Frete.nfd_id` + `Frete.numero_nfd` (FK opcional para NFD). `DespesaExtra` vinculada a `FreteDevolucao.despesa_extra_id` E `DescarteDevolucao.despesa_extra_id`. Ver `frete_placeholder_service.py` |
| `app/faturamento` | Enriquece vendedor/equipe via `FaturamentoProduto.vendedor` + `FaturamentoProduto.equipe_vendas` por NF referenciada (fallback por CNPJ) |
| `app/carteira` | `CarteiraPrincipal.raz_social_red` para exibir razao social reduzida na listagem |
| `app/transportadoras` | FK `transportadora_retorno_id` em `OcorrenciaDevolucao` |
| `app/estoque` | `ReversaoService.processar_reversao_estoque()` cria `MovimentacaoEstoque` quando NF revertida |
| `app/scheduler` | `sincronizacao_incremental_definitiva.py` chama `NFDService`, `ReversaoService`, `MonitoramentoSyncService` (executado por cron) |
| `app/odoo` | `odoo/utils/connection.get_odoo_connection()` — modelo `l10n_br_ciel_it_account.dfe` (finnfe=4) e `account.move` (move_type=out_refund) |
| `app/rastreamento` | `rastreamento/services/odoo_integration_service.py:46` importa `NFDevolucao` para exibicao no app mobile |
| `app/pallet` | NFDs com CFOPs de vasilhame (1920/2920/5920/6920/*) sao marcadas `e_pallet_devolucao=True` — **NAO tratar aqui** |

---

## Storage S3

| Campo | Conteudo | Origem |
|-------|----------|--------|
| `NFDevolucao.nfd_xml_path` | XML da NFD (base64 decoded do Odoo) | `NFDService._salvar_arquivos_nfd()` |
| `NFDevolucao.nfd_pdf_path` | PDF/DANFE da NFD | idem |
| `AnexoOcorrencia.caminho_s3` | Emails (.msg), fotos, documentos | `ocorrencia_routes.api_upload_anexo` |
| `DescarteDevolucao.termo_path` | Termo de autorizacao de descarte | `frete_routes.upload_documento_descarte` |
| `DescarteDevolucao.termo_assinado_path` | Termo assinado pelo cliente | idem |
| `DescarteDevolucao.comprovante_path` | Foto/doc do descarte efetivo | idem |

Acesso via `app.utils.file_storage.get_file_storage()` (lazy — requer app context).

---

## Scheduler (cron job)

`app/scheduler/sincronizacao_incremental_definitiva.py` roda sincronizacoes incrementais:
- **NFDs** (linha 1025-1062): `NFDService.importar_nfds(minutos_janela=N)`
- **Reversoes** (linha 1163-1171): `ReversaoService.importar_reversoes(dias=N)`
- **Monitoramento** (linha 1223-1248): `MonitoramentoSyncService.sincronizar_monitoramento()`

Ao adicionar nova sync, seguir padrao: lazy import + try/except per-module + log `sucesso_X = True/False`.

---

## Servicos — funcao-por-funcao

Ver [CLAUDE_FLUXOS.md](CLAUDE_FLUXOS.md) para diagramas e [CLAUDE_APIS.md](CLAUDE_APIS.md) para enderecos.

### NFDService (nfd_service.py)
- `importar_nfds(dias_retroativos|minutos_janela|data_inicio,data_fim, limite)` — entrypoint publico
- `_buscar_nfds_odoo()` — XML-RPC ao Odoo
- `_processar_nfd()` — tenta vincular por `numero_nfd+cnpj_emitente`; fallback cria orfao
- `_tentar_vincular_por_numero_cnpj()` — matching manual vs orfao
- `_criar_ocorrencia_automatica()` — 1:1 com NFD nova
- `_processar_nfs_referenciadas()` — extrai `<refNFe>` do XML
- `_processar_linhas_produto()` — extrai itens + detecta pallet
- `_detectar_nfd_pallet()` — seta `e_pallet_devolucao=True`
- `_extrair_info_complementar()` — copia tag `<infCpl>` para `info_complementar`
- `_extrair_endereco_emitente()` — enriquece UF/municipio/CEP/endereco
- `_salvar_arquivos_nfd()` — persiste XML/PDF no S3
- `vincular_nfd_manual()` — operacao manual via UI
- `listar_nfds_orfas()`, `listar_candidatos_vinculacao()` — helpers UI

### ReversaoService (reversao_service.py)
- `importar_reversoes(dias, limite)` — busca `out_refund` postadas com `reversed_entry_id`
- `_processar_nota_credito()` — cria/atualiza `NFDevolucao` com `tipo_documento='NF'` e `status_odoo='Revertida'`
- `_buscar_nf_original()`, `_buscar_itens_nf_original()` — XML-RPC ao Odoo
- `_criar_linhas_reversao()`, `_criar_nf_referenciada()`
- `processar_reversao_estoque()` — cria `MovimentacaoEstoque` + marca `FaturamentoProduto`

### MonitoramentoSyncService (monitoramento_sync_service.py)
- `sincronizar_monitoramento()` — unico entrypoint
- `_buscar_entregas_sem_nfd()`, `_processar_entrega()`

### AIResolverService (ai_resolver_service.py)
- Modelos: **Haiku 4.5** (micro-tarefas), **Sonnet 4.6** (resolucao semantica complexa)
- `resolver_produto(codigo_cliente, descricao_cliente, prefixo_cnpj, unidade_cliente, quantidade, ...)` → `ResultadoResolucaoProduto`
- `resolver_linhas_nfd(nfd_id, ...)` — batch paralelo (asyncio) para todas as linhas de uma NFD
- `extrair_observacao(texto)` — extrai numero_nf_venda + motivo + confianca (Pydantic `ObservacaoResponse`)
- `normalizar_unidade(unidade)` — CXA1 → CAIXA, etc.
- `classificar_motivo_semantico(texto)` — fallback sem LLM (keyword-based)
- **Estrategia De-Para (ordem de tentativa)**:
  1. De-Para grupo empresarial (Atacadao/Assai) — deterministico
  2. De-Para generico (`DeParaProdutoCliente` por `prefixo_cnpj`)
  3. Smart filter: busca candidatos via `resolver_entidades` + historico
  4. Haiku com constrained decoding (Pydantic `DeParaResponse`)
- **Grava automatico** em `DeParaProdutoCliente` se confianca > 0.9 (em `_gravar_depara()`)

### FretePlaceholderService (frete_placeholder_service.py)
Para devolucoes cuja NF de venda nao tem `Frete` no sistema (ex: pre-julho/2024):
- `buscar_embarque_devolucao()` — retorna `Embarque(numero=0)` (deve existir — ver `scripts/migrations/criar_embarque_devolucao.py`)
- `buscar_transportadora_devolucao()` — retorna `Transportadora(cnpj='00000000000000')` (migration `criar_transportadora_devolucao.py`)
- `criar_frete_placeholder(nfd, numero_nf_venda)` — cria Frete fantasma com valores zerados
- `obter_ou_criar_frete_para_devolucao()` — busca ou cria
- `criar_despesa_devolucao()` — `DespesaExtra` com `tipo_despesa='DEVOLUCAO'`, `tipo_documento='PENDENTE_DOCUMENTO'`, `numero_documento='PENDENTE_FATURA'`, `setor_responsavel='LOGISTICA'`

---

## Migrations relevantes

Todas em `scripts/migrations/` (regra CLAUDE.md: DDL precisa de 2 artefatos `.py` + `.sql`):

**Essenciais** (rodar em ordem):
1. `criar_transportadora_devolucao.py` — `Transportadora(cnpj='00000000000000')`
2. `criar_embarque_devolucao.py` — `Embarque(numero=0)` (dependencia da primeira)
3. `criar_tabelas_devolucao_fase1.py` / `.sql` — tabelas base Fase 1

**Evolucao**:
- `add_descarte_devolucao.py` — tabela `descarte_devolucao` (Fase 3)
- `add_descarte_itens.py` — tabela `descarte_item`
- `criar_tabela_nf_referenciada_fase4.py` / `.sql` — `nf_devolucao_nf_referenciada` (Fase 4)
- `add_confianca_resolucao_nfd_linha.py` — IA (Fase 4.5)
- `add_info_complementar_nf_devolucao.py` — tag infCpl
- `add_tipo_documento_nfd.py` + `backfill_tipo_documento_nfd.py` — suporte a NF revertida
- `add_momento_devolucao_ocorrencia.py`, `migrar_status_ocorrencia_devolucao.py`
- `criar_tabela_permissao_cadastro_devolucao.py` / `.sql` — permissoes CRUD
- `add_empresa_autorizada_descarte.py` / `.sql`, `add_local_coleta_frete_devolucao.py`
- `add_nfd_despesa_extra.py` — FK `DespesaExtra.nfd_id`
- `add_quantidade_convertida_nfd_linha.py` / `.sql`, `fix_nfd_linha_caixa_preco_unidade.py`
- `backfill_conversao_devolucao.py` — preenche `quantidade_convertida`/`qtd_por_caixa`
- `popular_endereco_emitente_nfd.py`, `add_endereco_emitente_nfd.py`
- `sync_data_entrada_nfd.py`, `hora_08_devolucao_fornecedor.py` / `.sql`

**Interna ao modulo**:
- `app/devolucao/scripts/migrations/add_confianca_motivo_nf_devolucao.py`

---

## Fase 5 e Fase 6 (NAO implementadas)

**Fase 5 — Contagem/Inspecao**:
- Model `ContagemDevolucao` (tabela `contagem_devolucao`) **ja existe** mas **sem UI**
- Pendentes: tela de contagem fisica, upload de fotos via `AnexoOcorrencia.contagem_devolucao_id`
- Campos ja mapeados: `caixas_conforme`, `caixas_nao_conforme`, `caixas_faltantes`, `status_qualidade`, `destino_produto`, `conferente`

**Fase 6 — Lancamento no Odoo**:
- Processo de 16 etapas (ver `.claude/references/odoo/PIPELINE_RECEBIMENTO.md`)
- NENHUM service de lancamento existe — build from scratch quando implementar

---

## TODOs abertos (`prompt.md`)

Leitura obrigatoria antes de mexer em templates ou dashboard. Entre os pedidos:
- Exibir `raz_social_red` com evidencia acima da razao social
- Aba descarte: nosso codigo + descricao, conversao UN/CX dinamica JS, botao importar quebrado
- Anexos: multi-upload com descricao replicada, "Baixar Todos" (ZIP), tipo auto-detectado
- Reversao: exibir NC em vez de NF na listagem
- **Inconsistencia de data de resolucao** (investigar caso `/devolucao/ocorrencias/5004` vs DFe Odoo 38076)
- Listagem: vendedor + equipe via NF referenciada ou CNPJ, badge com data de entrada ocupando 2 linhas sem empurrar tabela
- Permissoes: botao "Autorizacao" na aba comercial (so admin/gerente comercial)
- Log de quem anexou; campo financeiro de pagamento/baixa; exportacao

---

## Quick References

- Rotas: `app/__init__.py:822` (import) e `:884` (register)
- Link no menu: `app/templates/base.html:257`
- Agent SDK: **nao ha skill dedicada** — usar `especialista-odoo` ou `raio-x-pedido` para fluxos que cruzam com Odoo
- Scheduler: `app/scheduler/sincronizacao_incremental_definitiva.py` linhas 1025, 1163, 1223
