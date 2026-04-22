# CLAUDE_FLUXOS.md — Fluxos do modulo Devolucao

> Diagramas de fluxo para os 4 entrypoints de `NFDevolucao` + pipeline da IA + fluxos de Descarte/Frete.
> Ver `CLAUDE.md` para overview e `CLAUDE_MODELOS.md` para campos.

---

## Entrypoint 1: Registro Manual no Monitoramento

```
UI (monitoramento/visualizar_entrega.html)
  ↓ Click "Finalizar Entrega"
Modal "Houve devolucao?"
  ↓ Click "Sim, Registrar NFD"
Modal de registro NFD (numero_nfd, motivo, descricao, numero_nf_venda)
  ↓ POST /devolucao/registro/api/registrar
  │
  ├── Cria NFDevolucao:
  │     - entrega_monitorada_id = FK
  │     - origem_registro = 'MONITORAMENTO'
  │     - status = 'REGISTRADA'
  │     - tipo_documento = 'NFD'
  │     - criado_por = current_user.nome
  │
  ├── Cria OcorrenciaDevolucao:
  │     - numero_ocorrencia = '{NNNNN}/{AA}' (sequencial global >= 17500)
  │     - status = 'PENDENTE' (por default)
  │
  └── Marca EntregaMonitorada.teve_devolucao = True
```

**Arquivos**: `routes/registro_routes.py`, `monitoramento/routes.py:48`

---

## Entrypoint 2: Importacao DFe do Odoo (NFDService)

```
Scheduler (sincronizacao_incremental_definitiva.py:1025)
  ↓ NFDService.importar_nfds(minutos_janela=60)
  │
  ├── _buscar_nfds_odoo(data_inicio, limite, usar_write_date=True)
  │   XML-RPC: l10n_br_ciel_it_account.dfe
  │   Filtro: [('nfe_infnfe_ide_finnfe','=',4), ('write_date','>=',data_inicio)]
  │
  └── For each nfd_data in resultado:
      _processar_nfd(nfd_data):
        │
        ├── Check CNPJS_EXCLUIDOS (La Famiglia, Nacom Goya) → skip
        │
        ├── _tentar_vincular_por_numero_cnpj(numero_nfd, cnpj_emitente)
        │     Busca NFDevolucao existente com origem='MONITORAMENTO'
        │     │
        │     ├── Se achou: _atualizar_nfd_existente()
        │     │     - Preenche odoo_dfe_id, chave_nfd, valor_total, XML/PDF
        │     │     - status -> 'VINCULADA_DFE'
        │     │     - sincronizado_odoo = True
        │     │
        │     └── Se nao achou: _criar_nfd_orfa()
        │           - origem_registro = 'ODOO'
        │           - status = 'VINCULADA_DFE' direto
        │           - _criar_ocorrencia_automatica() → cria ocorrencia tambem
        │
        ├── _processar_nfs_referenciadas(nfd_id, xml_base64)
        │     Parse XML (tag <refNFe>)
        │     → popula NFDevolucaoNFReferenciada com origem='XML'
        │     → tenta vincular entrega_monitorada_id por numero_nf
        │
        ├── _processar_linhas_produto(nfd_id, xml_base64, prefixo_cnpj)
        │     Parse XML (tag <det>)
        │     → cria NFDevolucaoLinha
        │     → tenta resolver via DeParaProdutoCliente por prefixo_cnpj
        │     → _classificar_unidade(), _validar_tipo_por_preco()
        │     → _detectar_nfd_pallet() → marca e_pallet_devolucao se CFOPs match
        │
        ├── _extrair_info_complementar(nfd, xml_base64)
        │     Extrai tag <infCpl> → nfd.info_complementar (para IA processar depois)
        │
        ├── _extrair_endereco_emitente(nfd, xml_base64)
        │     Preenche UF, cidade, CEP, endereco do emitente
        │
        └── _salvar_arquivos_nfd(nfd, nfd_data)
              XML/PDF vindos do Odoo em base64
              → S3 via file_storage.save_bytes()
              → preenche nfd_xml_path, nfd_pdf_path
```

**Arquivo**: `services/nfd_service.py` (1589 LOC)

### Pontos de atencao
- **CFOPS_PALLET** (linha 57): NFDs com CFOPs de vasilhame sao marcadas `e_pallet_devolucao=True`. Modulo `app/pallet` deve trata-las.
- **CNPJS_EXCLUIDOS** (linha 51): `{'18467441', '61724241'}` — hardcoded, replicar em novos services.
- **CODIGO_PRODUTO_PALLET** (linha 60): `'208000012'` — codigo interno do pallet.

---

## Entrypoint 3: Reversao de NF de Venda (ReversaoService)

```
Scheduler (sincronizacao_incremental_definitiva.py:1163)
  ↓ ReversaoService.importar_reversoes(dias=30)
  │
  ├── _buscar_notas_credito(data_corte, limite)
  │   XML-RPC: account.move
  │   Filtro: [('move_type','=','out_refund'),
  │            ('state','=','posted'),
  │            ('reversed_entry_id','!=',False),
  │            ('date','>=',data_corte)]
  │
  └── For each nc_data:
      _processar_nota_credito(nc_data):
        │
        ├── Extrair CNPJ do parceiro → skip se em CNPJS_EXCLUIDOS
        │
        ├── _buscar_nf_original(reversed_entry_id)
        │     → account.move original da venda
        │
        ├── Busca/cria NFDevolucao com:
        │     - numero_nfd = numero_nf (da NC)
        │     - numero_nf_venda = numero da NF original
        │     - tipo_documento = 'NF' (NAO 'NFD')
        │     - status_odoo = 'Revertida' ou 'Cancelada'
        │     - odoo_nf_venda_id = id da NF original
        │     - odoo_nota_credito_id = id da NC
        │     - numero_nota_credito = numero da NC
        │     - origem_registro = 'ODOO'
        │
        ├── _criar_linhas_reversao(nfd, itens_da_nf_original)
        │     → NFDevolucaoLinha com metodo_resolucao='ODOO'
        │     → produtos JA sao nossos codigos (sem De-Para necessario)
        │
        ├── _criar_nf_referenciada(nfd, nf_original)
        │     → NFDevolucaoNFReferenciada com origem='ODOO_REVERSAO'
        │     → tenta vincular entrega_monitorada_id
        │
        ├── Vincular a EntregaMonitorada se existir
        │     → NFDevolucao.entrega_monitorada_id
        │     → EntregaMonitorada.teve_devolucao = True
        │
        ├── _criar_ocorrencia_automatica() (se nao existir)
        │
        └── processar_reversao_estoque(nfd)
              → cria MovimentacaoEstoque (entrada negativa?)
              → marca FaturamentoProduto.status_nf (ou similar)
              → estatisticas: faturamento_marcados, movimentacoes_criadas
```

**Arquivo**: `services/reversao_service.py` (899 LOC)

### Diferenca chave NFD vs NF revertida

| Aspecto | `tipo_documento='NFD'` | `tipo_documento='NF'` |
|---------|------------------------|----------------------|
| Origem fiscal | Cliente emitiu nota de devolucao | Nos cancelamos/revertemos a venda |
| Movimento fisico | Houve retorno de mercadoria | **Nao houve movimento** (cancelamento administrativo) |
| Linhas vem de | XML da NFD (`<det>`) | Itens da NF original (`account.move.line`) |
| De-Para? | SIM (codigos do cliente) | NAO (ja nossos) |

---

## Entrypoint 4: Sync Monitoramento

```
Scheduler (sincronizacao_incremental_definitiva.py:1223)
  ↓ MonitoramentoSyncService.sincronizar_monitoramento()
  │
  ├── _buscar_entregas_sem_nfd()
  │     SELECT EntregaMonitorada WHERE
  │       status_finalizacao IN ('Cancelada','Devolvida','Troca de NF')
  │       AND NOT EXISTS (SELECT 1 FROM nf_devolucao WHERE entrega_monitorada_id = e.id)
  │
  └── For each entrega:
      _processar_entrega(entrega):
        │
        ├── Cria NFDevolucao:
        │     - numero_nfd = entrega.numero_nf
        │     - tipo_documento = 'NF'
        │     - status_monitoramento = entrega.status_finalizacao
        │     - status_odoo = NULL (pendente de enriquecimento futuro)
        │     - origem_registro = 'MONITORAMENTO'
        │
        ├── Cria OcorrenciaDevolucao automatica
        │
        └── Marca entrega.teve_devolucao = True
```

**Arquivo**: `services/monitoramento_sync_service.py` (371 LOC)

**Quando usar**: quando a operacao de entrega aponta problema **antes** do Odoo registrar reversao/NFD. Eventualmente o NFDService ou ReversaoService enriquecera com dados do Odoo.

---

## Pipeline de IA (AIResolverService)

```
                             AIResolverService
                                      │
      ┌───────────────────┬───────────┼───────────┬──────────────────┐
      ↓                   ↓           ↓           ↓                  ↓
 resolver_produto   resolver_      extrair_    normalizar_    classificar_
                    linhas_nfd   observacao     unidade     motivo_semantico
      │                   │           │           │                  │
  HAIKU/SONNET      Asyncio batch    HAIKU      HAIKU         Keyword fallback
                    paralelo                                  (sem LLM)
```

### Fluxo de `resolver_produto(codigo_cliente, descricao, prefixo_cnpj, unidade, qtd)`

```
1. _buscar_depara_grupo_empresarial(codigo_cliente, prefixo_cnpj)
   Se prefixo_cnpj pertence a grupo (Atacadao/Assai):
     → Busca tabela especializada do grupo
     → Retorna match deterministico
     → EXIT (sem chamar LLM)

2. _buscar_depara_lote(prefixo_cnpj, codigo_cliente)
   → DeParaProdutoCliente match exato por (prefixo_cnpj, codigo_cliente)
   → Se encontrou: EXIT (sem LLM)

3. _extrair_termos_busca(descricao_cliente) [Haiku, constrained via TermosBuscaResponse]
   Extrai termos-chave e materia_prima

4. _buscar_produtos_prefiltrados(termos, materia_prima, ...)
   → Smart filter com historico de faturamento do CNPJ
   → Retorna candidatos (max limite_candidatos=20)

5. Se nenhum candidato: retorna requer_confirmacao=True, BAIXA confianca

6. _buscar_produtos_semantico(descricao, candidatos) [Sonnet, constrained via DeParaResponse]
   → Envia glossario + candidatos + descricao
   → Haiku/Sonnet devolve codigo_interno + confianca + justificativa
   → Structured Output garante JSON valido

7. _converter_depara_response() → ResultadoResolucaoProduto

8. Se confianca > 0.9:
   _gravar_depara() → auto-insert em DeParaProdutoCliente (cache)

9. Retorna ResultadoResolucaoProduto:
   - sucesso: bool
   - confianca: float
   - sugestao_principal: ProdutoSugestao
   - outras_sugestoes: List[ProdutoSugestao]
   - requer_confirmacao: bool
   - metodo_resolucao: 'DEPARA' | 'SMART_FILTER' | 'DEPARA_GRUPO'
```

### Fluxo de `extrair_observacao(texto)`

```
Input: "DEVOLUCAO REF NF 123456 E NF 789012 - AVARIA NO TRANSPORTE"

1. Chama Haiku com Pydantic ObservacaoResponse como output_format:
   {
     "numeros_nf_venda": ["123456", "789012"],
     "motivo_sugerido": "AVARIA",
     "descricao_motivo": "Avaria no transporte",
     "confianca": 0.95
   }

2. Retorna ResultadoExtracaoObservacao:
   - numero_nf_venda (str, compat): "123456" (primeira)
   - numeros_nf_venda (list[str]): todas
   - motivo_sugerido, descricao_motivo, confianca
```

### Quando `extrair_observacao` e chamado

Em `ocorrencia_routes.py:409` (rota `detalhe`), se `nfd.info_complementar` existe e `nfd.confianca_motivo is None` (nao foi processado), a IA roda **automaticamente** no primeiro acesso.

---

## Fluxo Frete Retorno

```
Logistica decide RETORNO (OcorrenciaDevolucao.destino='RETORNO')
  ↓
POST /devolucao/frete/api/<oc_id>/fretes (criar_frete)
  → FreteDevolucao(status='COTADO')
  ↓ PUT .../frete/<id>/status
COTADO → APROVADO
  ↓
Transportadora coleta mercadoria
  ↓ PUT .../frete/<id>/status
APROVADO → COLETADO
  ↓ OcorrenciaDevolucao.localizacao_atual = 'EM_TRANSITO'
  ↓
Chegada no CD
  ↓ PUT .../frete/<id>/status
COLETADO → ENTREGUE
  ↓ OcorrenciaDevolucao.localizacao_atual = 'CD'
  ↓ OcorrenciaDevolucao.data_chegada_cd = now
  ↓
Faturamento da transportadora
  ↓ Vincula FreteDevolucao.despesa_extra_id
  → DespesaExtra com tipo_despesa='DEVOLUCAO'

(Para NFs de venda SEM Frete original, usa frete_placeholder_service:
  - Busca Embarque(numero=0) + Transportadora(cnpj='00000000000000')
  - Cria Frete fantasma com valores zerados
  - Cria DespesaExtra(tipo_documento='PENDENTE_DOCUMENTO', numero_documento='PENDENTE_FATURA'))
```

---

## Fluxo Descarte

```
Logistica decide DESCARTE (OcorrenciaDevolucao.destino='DESCARTE')
  Motivo: CUSTO_ALTO / PERECIVEIS / AVARIA_TOTAL / CONTAMINACAO / CLIENTE_SOLICITOU
  ↓
POST /devolucao/frete/api/<oc_id>/descartes (criar_descarte)
  → DescarteDevolucao(status='AUTORIZADO')
  → numero_termo = 'TD-YYYYMM-XXXX' (sequencial mensal)
  → empresa_autorizada = transportador OU cliente (tipo)
  ↓
Gerar termo (PDF) via template devolucao/termo_descarte.html
  ↓ GET .../descarte/<id>/termo/imprimir ou /download
  → Registra termo_impresso_em, termo_salvo_em
  ↓
Upload termo (termo_path)
  ↓ POST .../descarte/<id>/upload/termo
  → termo_enviado_em, termo_enviado_para
  ↓ PUT .../descarte/<id>/status
AUTORIZADO → TERMO_ENVIADO
  ↓
Cliente retorna termo assinado
  ↓ POST .../descarte/<id>/upload/termo_assinado
  → termo_retornado_em
  ↓ PUT .../descarte/<id>/status
TERMO_ENVIADO → TERMO_RETORNADO
  ↓
Descarte fisico efetuado
  ↓ POST .../descarte/<id>/upload/comprovante
  → data_descarte preenchida
  ↓ PUT .../descarte/<id>/status
TERMO_RETORNADO → DESCARTADO
  ↓ OcorrenciaDevolucao.localizacao_atual = 'DESCARTADO'
  ↓
Se tem_custo=True (empresa de destruicao paga):
  → DescarteDevolucao.despesa_extra_id preenchido
  → DespesaExtra(tipo_despesa='DESCARTE', ...) criada separadamente

Descarte parcial? Criar DescarteItem(nfd_linha_id, quantidade_descarte, ...)
```

---

## Fluxo de Status da Ocorrencia (auto-computed)

```python
def calcular_status(self) -> str:
    # Os "7 campos comerciais obrigatorios":
    # 1. categorias (N:M, >=1)
    # 2. subcategorias (N:M, >=1)
    # 3. responsavel_id (FK)
    # 4. origem_id (FK)
    # 5. autorizado_por_id (FK)
    # 6. momento_devolucao (!= None, != 'INDEFINIDO')
    # 7. desfecho (!= None, strip != '')

    if not self._campos_comerciais_preenchidos():
        return 'PENDENTE'

    # NFD com entrada fisica no Odoo = status_codigo '06' (Concluido)
    nfd = self.nf_devolucao
    if nfd and nfd.odoo_status_codigo == '06':
        return 'RESOLVIDO'

    return 'EM_ANDAMENTO'
```

**Importante**: sempre chamar `calcular_status()` e persistir apos atualizar campos comerciais. Nunca setar `status` diretamente na API.

**Trigger**: `api_atualizar_comercial` em `ocorrencia_routes.py:664` recalcula e persiste.

---

## Fluxo Scheduler (orquestracao)

```
sincronizacao_incremental_definitiva.py (cron)
  ↓
Para CADA modulo habilitado (sucesso_X flags):
  1. Faturamento, Carteira, ...
  2. NFDs (linha 1025-1062):
     ↓ NFDService.importar_nfds(minutos_janela=60)
     → Log estatisticas
  3. Reversoes (linha 1163-1171):
     ↓ ReversaoService.importar_reversoes(dias=N)
  4. Monitoramento (linha 1223-1248):
     ↓ MonitoramentoSyncService.sincronizar_monitoramento()
  5. Pallets, Validacao recebimento, IBS/CBS, Pickings, ...

Ao final (linha 1863):
  modulos_sync = [sucesso_faturamento, sucesso_carteira, ..., sucesso_nfds, ..., sucesso_reversoes, sucesso_monitoramento, ...]
  if not all(modulos_sync):
      → Alerta / retry
```

---

## Debugging: Fluxo de processo de NFD orfao

Quando uma NFD e importada do Odoo mas nao tem match com registro manual:

```
1. NFDService._criar_nfd_orfa(nfd_data) cria registro com:
   origem_registro='ODOO', entrega_monitorada_id=None

2. NFDService._criar_ocorrencia_automatica() cria OcorrenciaDevolucao
   com numero_ocorrencia e status='PENDENTE'

3. Dashboard `/devolucao/ocorrencias/` mostra orfao (sem vinculo com entrega)

4. Operador acessa `/devolucao/vinculacao` (ui nao pronta — usar API):
   GET /api/<nfd_id>/candidatos
   → Lista EntregasMonitoradas com match por numero_nf_venda ou CNPJ
   POST /api/<nfd_id>/vincular {"entrega_id": N}
   → Atualiza NFDevolucao.entrega_monitorada_id
   → Marca EntregaMonitorada.teve_devolucao = True

5. Proxima sincronizacao encontra o match estabelecido.
```

**Razao para orfaos**: monitoramento nao registrou devolucao manualmente, mas Odoo gerou DFe. Operacional prefere vincular depois.
