# CLAUDE_APIS.md — APIs do modulo Devolucao

> Lista completa das ~80 rotas em 6 blueprints sob `devolucao_bp` (prefixo `/devolucao`).
> Ver `CLAUDE.md` para arquitetura e `CLAUDE_MODELOS.md` para schemas.

---

## Blueprint Registry

```python
# app/devolucao/__init__.py
devolucao_bp = Blueprint('devolucao', __name__, url_prefix='/devolucao')

# Sub-blueprints (url_for names):
registro_bp       # 'devolucao.devolucao_registro.*'       /registro
ocorrencia_bp     # 'devolucao.devolucao_ocorrencia.*'     /ocorrencias
vinculacao_bp     # 'devolucao.devolucao_vinculacao.*'     /vinculacao
ai_bp             # 'devolucao.devolucao_ai.*'             /ai
frete_bp          # 'devolucao.devolucao_frete.*'          /frete
cadastro_bp       # 'devolucao.devolucao_cadastro.*'       /cadastros
```

**Menu**: `app/templates/base.html:257` → `url_for('devolucao.devolucao_ocorrencia.index')`

**Todas as rotas requerem `@login_required`** (exceto se documentado).

---

## registro_bp — `/devolucao/registro` (Fase 1)

Registro manual de NFD a partir do monitoramento.

| Metodo | Endpoint | Funcao | Descricao |
|--------|----------|--------|-----------|
| POST | `/api/registrar` | `api_registrar_nfd` | Cria NFDevolucao + OcorrenciaDevolucao + marca `teve_devolucao=True` |
| GET | `/api/listar/<int:entrega_id>` | `api_listar_nfds` | Lista NFDs de uma entrega |
| GET | `/api/<int:nfd_id>` | `api_obter_nfd` | Detalhes de uma NFD |
| PUT | `/api/<int:nfd_id>` | `api_atualizar_nfd` | Atualiza NFD manual |
| DELETE | `/api/<int:nfd_id>` | `api_excluir_nfd` | Soft delete (`ativo=False`) |
| GET | `/api/motivos` | `api_listar_motivos` | Lista `MOTIVOS_DEVOLUCAO` |
| GET | `/modal/<int:entrega_id>` | `modal_registro` | HTML do modal de registro |

### Exemplo payload

```json
POST /devolucao/registro/api/registrar
{
  "entrega_id": 123,
  "numero_nfd": "12345",
  "motivo": "AVARIA",
  "descricao_motivo": "Produto chegou danificado",
  "numero_nf_venda": "654321"
}
→ {
  "success": true,
  "nfd_id": 1,
  "numero_nfd": "12345",
  "ocorrencia_id": 1,
  "numero_ocorrencia": "17500/26"
}
```

---

## ocorrencia_bp — `/devolucao/ocorrencias` (Fase 2 + dashboard)

Dashboard + detalhe + APIs de ocorrencia. **Maior arquivo do modulo (1757 LOC)**.

### Paginas HTML

| Metodo | Endpoint | Funcao | Descricao |
|--------|----------|--------|-----------|
| GET | `/` | `index` | Dashboard com filtros + paginacao (default 150/pag). Enriquece com `raz_social_red`, vendedor/equipe, NFs referenciadas, frete retorno, descarte |
| GET | `/<int:ocorrencia_id>` | `detalhe` | Detalhe (template ~105KB, 3500+ linhas). Chama `get_ai_resolver` se `info_complementar` nao foi processado |

### APIs de Ocorrencia

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/api/<int:ocorrencia_id>` | `api_obter_ocorrencia` |
| PUT | `/api/<int:ocorrencia_id>/logistica` | `api_atualizar_logistica` |
| PUT | `/api/<int:ocorrencia_id>/comercial` | `api_atualizar_comercial` |
| GET | `/api/stats` | `api_stats` |

### APIs de Anexos

| Metodo | Endpoint | Funcao | Descricao |
|--------|----------|--------|-----------|
| POST | `/api/<int:ocorrencia_id>/anexos` | `api_upload_anexo` | Upload multipart — detecta tipo EMAIL/FOTO/DOCUMENTO |
| GET | `/api/<int:ocorrencia_id>/anexos` | `api_listar_anexos` | Lista todos |
| GET | `/api/<int:ocorrencia_id>/anexos/<int:anexo_id>/download` | `api_download_anexo` | Download individual |
| GET | `/api/<int:ocorrencia_id>/anexos/download-all` | `api_download_all_anexos` | ZIP com todos |
| DELETE | `/api/<int:ocorrencia_id>/anexos/<int:anexo_id>` | `api_excluir_anexo` | Soft delete |

### APIs de Download NFD

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/nfd/<int:nfd_id>/xml` | `download_xml` |
| GET | `/nfd/<int:nfd_id>/pdf` | `download_pdf` |

### APIs Cross-referencia

| Metodo | Endpoint | Funcao | Descricao |
|--------|----------|--------|-----------|
| GET | `/api/<int:ocorrencia_id>/comparar-nf-venda` | `api_comparar_nf_venda` | Compara produtos da NFD vs NFs de venda referenciadas (`FaturamentoProduto`) — `qtd_vendida` vs `qtd_devolvida`, preco venda vs devolvido. Produtos nao encontrados retornam em `nfs_nao_encontradas` |
| GET | `/api/exportar` | `exportar_relatorio` | Excel com filtros (equipe, vendedor, mes, ano, cnpj, cliente). Cada linha = 1 NFD expandida por NF referenciada |

---

## vinculacao_bp — `/devolucao/vinculacao` (Fase 4)

Importacao do Odoo e vinculacao manual.

### Sincronizacao

| Metodo | Endpoint | Funcao | Descricao |
|--------|----------|--------|-----------|
| POST | `/api/sincronizar` | `api_sincronizar_nfds` | Import inicial (ex: `dias_retroativos=30`) |
| POST | `/api/sincronizar/incremental` | `api_sincronizar_incremental` | `minutos_janela=60` (usado pelo scheduler) |
| POST | `/api/sincronizar-reversoes` | `api_sincronizar_reversoes` | `ReversaoService.importar_reversoes` (out_refund) |
| POST | `/api/sincronizar-monitoramento` | `api_sincronizar_monitoramento` | `MonitoramentoSyncService.sincronizar_monitoramento` |
| POST | `/api/sincronizar-completo` | `api_sincronizar_completo` | Executa os 3 acima em sequencia |

### Vinculacao manual

| Metodo | Endpoint | Funcao | Descricao |
|--------|----------|--------|-----------|
| GET | `/api/orfas` | `api_listar_orfas` | NFDs `origem_registro='ODOO'` sem vinculo com entrega |
| GET | `/api/<int:nfd_id>` | `api_obter_nfd` | Detalhes da NFD |
| GET | `/api/<int:nfd_id>/candidatos` | `api_listar_candidatos` | Lista candidatas a vincular (match por NF venda + CNPJ) |
| POST | `/api/<int:nfd_id>/vincular` | `api_vincular_manual` | Vincula NFD orfa a uma `EntregaMonitorada` |

### NFs Referenciadas

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/api/<int:nfd_id>/nfs-referenciadas` | `api_listar_nfs_referenciadas` |
| POST | `/api/<int:nfd_id>/nfs-referenciadas` | `api_adicionar_nf_referenciada` |
| DELETE | `/api/<int:nfd_id>/nfs-referenciadas/<int:ref_id>` | `api_remover_nf_referenciada` |

### Estatisticas

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/api/estatisticas` | `api_estatisticas` |

---

## ai_bp — `/devolucao/ai` (Fase 4.5 — Claude Haiku 4.5 + Sonnet 4.6)

### Paginas HTML

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/depara` | `pagina_depara` (tela gerenciamento De-Para) |

### APIs de resolucao

| Metodo | Endpoint | Funcao | Descricao |
|--------|----------|--------|-----------|
| POST | `/api/resolver-produto` | `api_resolver_produto` | Input: `codigo_cliente`, `descricao_cliente`, `prefixo_cnpj`, `unidade_cliente`, `quantidade` |
| POST | `/api/extrair-observacao` | `api_extrair_observacao` | Extrai `numeros_nf_venda[]`, `motivo_sugerido`, `descricao_motivo`, `confianca` de texto livre |
| POST | `/api/normalizar-unidade` | `api_normalizar_unidade` | `CXA1` → `CAIXA`, etc. |
| POST | `/api/nfd/<int:nfd_id>/resolver-linhas` | `api_resolver_linhas_nfd` | Batch paralelo (asyncio) — resolve todas as linhas |
| POST | `/api/nfd/<int:nfd_id>/atualizar-motivo` | `api_atualizar_motivo_nfd` | Aplica motivo extraido pela IA |
| GET | `/api/nfd/<int:nfd_id>/linhas` | `api_listar_linhas_nfd` | Lista linhas com status de resolucao |
| POST | `/api/linha/<int:linha_id>/confirmar` | `api_confirmar_resolucao` | Confirma resolucao manual/IA — grava De-Para |

### APIs De-Para CRUD

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/api/depara` | `api_listar_depara` |
| POST | `/api/depara` | `api_criar_depara` |
| PUT | `/api/depara/<int:depara_id>` | `api_atualizar_depara` |
| DELETE | `/api/depara/<int:depara_id>` | `api_excluir_depara` |
| POST | `/api/depara/importar` | `api_importar_depara` (XLSX/CSV) |
| GET | `/api/depara/exportar` | `api_exportar_depara` (Excel) |

### APIs de Produtos (para resolucao manual)

| Metodo | Endpoint | Funcao | Descricao |
|--------|----------|--------|-----------|
| GET | `/api/produtos/buscar?q=...` | `api_buscar_produtos` | Autocomplete de produtos internos |
| GET | `/api/produtos/<codigo>` | `api_obter_produto` | Detalhes de um produto |

### Estatisticas

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/api/estatisticas` | `api_estatisticas_resolucao` |

---

## frete_bp — `/devolucao/frete` (Fase 3)

### Fretes de retorno

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/api/<int:ocorrencia_id>/fretes` | `listar_fretes` |
| POST | `/api/<int:ocorrencia_id>/fretes` | `criar_frete` |
| GET | `/api/frete/<int:frete_id>` | `obter_frete` |
| PUT | `/api/frete/<int:frete_id>` | `atualizar_frete` |
| PUT | `/api/frete/<int:frete_id>/status` | `atualizar_status_frete` |
| DELETE | `/api/frete/<int:frete_id>` | `excluir_frete` |

### Descartes

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/api/<int:ocorrencia_id>/descartes` | `listar_descartes` |
| POST | `/api/<int:ocorrencia_id>/descartes` | `criar_descarte` |
| GET | `/api/descarte/<int:descarte_id>` | `obter_descarte` |
| PUT | `/api/descarte/<int:descarte_id>/status` | `atualizar_status_descarte` |
| DELETE | `/api/descarte/<int:descarte_id>` | `excluir_descarte` |

### Upload de documentos (descarte)

| Metodo | Endpoint | Funcao | Tipos validos |
|--------|----------|--------|---------------|
| POST | `/api/descarte/<int:descarte_id>/upload/<tipo>` | `upload_documento_descarte` | `termo` / `termo_assinado` / `comprovante` |
| GET | `/api/descarte/<int:descarte_id>/termo/download` | `download_termo_descarte` | PDF |
| GET | `/api/descarte/<int:descarte_id>/termo/imprimir` | `imprimir_termo_descarte` | HTML preview |

### Helpers de cotacao

| Metodo | Endpoint | Funcao | Descricao |
|--------|----------|--------|-----------|
| GET | `/api/<int:ocorrencia_id>/calcular-peso` | `calcular_peso_devolucao` | Soma pesos das linhas convertidas |
| POST | `/api/<int:ocorrencia_id>/estimar-retorno` | `estimar_frete_retorno` | Usa calculadora de frete interno |

### Lookups

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/api/transportadoras` | `listar_transportadoras` |
| GET | `/api/motivos-descarte` | `listar_motivos_descarte` |
| GET | `/api/ufs` | `listar_ufs` |
| GET | `/api/cidades/<uf>` | `listar_cidades_por_uf` |

---

## cadastro_bp — `/devolucao/cadastros`

CRUD dinamico de lookup tables (`tipo` = `categorias`, `subcategorias`, `responsaveis`, `origens`, `autorizados`).

### CRUD generico

| Metodo | Endpoint | Funcao | Observacao |
|--------|----------|--------|------------|
| GET | `/api/<tipo>` | `listar_ativos` | Filtro `?categoria_ids=1,2,3` disponivel para `subcategorias` e `responsaveis` |
| GET | `/api/<tipo>/todos` | `listar_todos` | Inclui inativos |
| POST | `/api/<tipo>` | `criar` | **Verifica permissao** |
| PUT | `/api/<tipo>/<int:item_id>` | `editar` | **Verifica permissao** |
| PATCH | `/api/<tipo>/<int:item_id>/toggle` | `toggle_ativo` | **Verifica permissao (excluir)** |

### Gestao de permissoes

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/api/permissoes` | `listar_permissoes` |
| POST | `/api/permissoes` | `conceder_permissao` |
| PUT | `/api/permissoes/<int:perm_id>` | `atualizar_permissao` |
| DELETE | `/api/permissoes/<int:perm_id>` | `revogar_permissao` |

### Permissao (`_verificar_permissao_cadastro`)

```python
if current_user.perfil in ('administrador', 'gerente_comercial'):
    return True  # bypass
perm = PermissaoCadastroDevolucao.query.filter_by(
    usuario_id=current_user.id, tipo_cadastro=tipo, ativo=True
).first()
# acao in ('criar','editar','excluir')
return perm.pode_<acao> if perm else False
```

---

## Padroes de resposta

### Sucesso
```json
{"sucesso": true, ...}
// ou
{"success": true, ...}
```

### Erro (usar SEMPRE `jsonify`, NAO `abort`)
```python
return jsonify({'sucesso': False, 'erro': 'Mensagem'}), 400
return jsonify({'sucesso': False, 'erro': 'Nao encontrado'}), 404
return jsonify({'sucesso': False, 'erro': str(e)}), 500
```

**Gotcha**: exception handler global re-raise `HTTPException` — `abort(4xx)` **nao funciona** aqui.

---

## Decorators comuns

- `@login_required` — todas as rotas (exceto dumps publicos, que nao existem)
- **Autor** de mudancas: `current_user.nome` (ou `username` como fallback)
- **Timezone**: criar com `agora_utc_naive()` de `app.utils.timezone` — NAO usar `datetime.now()`
