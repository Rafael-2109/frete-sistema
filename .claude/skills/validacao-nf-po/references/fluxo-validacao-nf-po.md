# Fluxo Completo: Validacao NF x PO

## Arquivo Principal
`app/recebimento/services/validacao_nf_po_service.py`

---

## ETAPA 1: Entrada - validar_dfe() (linha 75)

```python
def validar_dfe(self, odoo_dfe_id: int, usar_dados_locais: bool = True) -> Dict[str, Any]:
```

1. Cria/atualiza registro em `ValidacaoNfPoDfe` (get_or_create)
2. Reseta contadores: itens_sem_depara, itens_sem_po, itens_preco_diverge, etc.
3. Limpa matches/divergencias anteriores (DELETE CASCADE)

---

## ETAPA 2: Buscar DFE no Odoo - _buscar_dfe() (linha 406)

```python
def _buscar_dfe(self, odoo_dfe_id: int) -> Optional[Dict[str, Any]]:
    odoo = get_odoo_connection()
    dfes = odoo.read('l10n_br_ciel_it_account.dfe', [odoo_dfe_id], [...])
    return dfes[0] if dfes else None
```

**Campos Odoo lidos**:
```python
[
    'id', 'name', 'l10n_br_status',
    'nfe_infnfe_emit_cnpj',         # CNPJ fornecedor
    'nfe_infnfe_emit_xnome',        # Razao social fornecedor
    'nfe_infnfe_dest_cnpj',         # CNPJ empresa compradora (destinatario)
    # ATENCAO: 'nfe_infnfe_dest_xnome' NAO EXISTE no Odoo!
    'nfe_infnfe_ide_nnf',           # Numero NF
    'nfe_infnfe_ide_serie',         # Serie
    'protnfe_infnfe_chnfe',         # Chave NF-e (44 digitos)
    'nfe_infnfe_ide_dhemi',         # Data/hora emissao (ISO)
    'nfe_infnfe_total_icmstot_vnf', # Valor total NF
    'l10n_br_tipo_pedido',          # Tipo pedido
    'purchase_id',                  # PO vinculado (many2one: [id, name])
    'purchase_fiscal_id'            # PO fiscal (many2one: [id, name])
]
```

**Dados salvos localmente em ValidacaoNfPoDfe**:
```python
validacao.numero_nf = dfe_data.get('nfe_infnfe_ide_nnf')
validacao.serie_nf = dfe_data.get('nfe_infnfe_ide_serie')
validacao.cnpj_fornecedor = limpar_cnpj(dfe_data.get('nfe_infnfe_emit_cnpj'))
validacao.razao_fornecedor = dfe_data.get('nfe_infnfe_emit_xnome')
validacao.cnpj_empresa_compradora = limpar_cnpj(dfe_data.get('nfe_infnfe_dest_cnpj'))
# razao_empresa_compradora: Buscado via res.partner pelo CNPJ (nfe_infnfe_dest_xnome NAO existe)
validacao.data_nf = parse_date(dfe_data.get('nfe_infnfe_ide_dhemi'))
validacao.valor_total_nf = dfe_data.get('nfe_infnfe_total_icmstot_vnf')
```

---

## ETAPA 3: Buscar Linhas DFE - _buscar_dfe_lines() (linha 479)

```python
def _buscar_dfe_lines(self, odoo_dfe_id: int) -> List[Dict[str, Any]]:
    odoo = get_odoo_connection()
    line_ids = odoo.search('l10n_br_ciel_it_account.dfe.line', [('dfe_id', '=', odoo_dfe_id)])
    lines = odoo.read('l10n_br_ciel_it_account.dfe.line', line_ids, [...])
    return lines
```

**ATENCAO**: Assinatura aceita APENAS 1 argumento (odoo_dfe_id). NAO passar line_ids como segundo argumento.

**Campos Odoo lidos**:
```python
[
    'id',                   # ID da linha
    'dfe_id',               # Referencia ao DFE
    'product_id',           # Produto Odoo (many2one)
    'det_prod_cprod',       # Codigo do produto DO FORNECEDOR (chave De-Para!)
    'det_prod_xprod',       # Descricao/nome do produto
    'det_prod_qcom',        # Quantidade (UM do fornecedor)
    'det_prod_ucom',        # Unidade de medida (fornecedor)
    'det_prod_vuncom',      # Preco unitario (UM do fornecedor)
    'det_prod_vprod'        # Valor total do item
]
```

---

## ETAPA 4: Conversao De-Para BATCH - _converter_itens_dfe_batch() (linha 513)

**Logica**:
1. Extrair todos `det_prod_cprod` das linhas
2. Query BATCH em `produto_fornecedor_depara` por (cnpj_fornecedor, cod_produto_fornecedor)
3. Para cada item:
   - Se tem De-Para: converter quantidade e preco pelo fator
   - Se nao tem: marcar como `itens_sem_depara` (bloqueio)

**Formulas de conversao**:
```python
# Fornecedor envia em ML (mililitro), interno em UNITS
# fator_conversao = 1000

# Quantidade: qtd_nf * fator
qtd_convertida = qtd_original * fator  # 60 ML * 1000 = 60000 UNITS

# Preco: preco_nf / fator
preco_convertido = preco_original / fator  # R$ 41/ML / 1000 = R$ 0.041/UNIT
```

**Estrutura de retorno (itens_convertidos)**:
```python
{
    'tem_depara': True,
    'dfe_line_id': int,             # ID linha Odoo
    'cod_produto_fornecedor': str,  # Codigo do fornecedor
    'cod_produto_interno': str,     # Codigo interno (resultado De-Para)
    'odoo_product_id': int,         # ID produto no Odoo
    'nome_produto': str,
    'qtd_original': Decimal,        # UM fornecedor
    'qtd_convertida': Decimal,      # UM interna
    'um_nf': str,                   # Ex: 'ML', 'MI', 'MIL'
    'um_interna': str,              # Ex: 'UNITS'
    'preco_original': Decimal,      # Por UM fornecedor
    'preco_convertido': Decimal,    # Por UM interna
    'fator_conversao': Decimal
}
```

---

## ETAPA 5: Buscar POs LOCAL - _buscar_pos_fornecedor_local() (linha 755)

**Criterios de filtro**:
```python
PedidoCompras.query.filter(
    cnpj_fornecedor == cnpj_limpo,         # Mesmo fornecedor
    status_odoo IN ('purchase', 'done'),    # Confirmados
    (dfe_id IS NULL OR dfe_id = ''),        # Sem NF vinculada
    (qtd_produto_pedido - qtd_recebida) > 0 # Com saldo
)
```

**Agrupamento**: Por `num_pedido` (cada PO pode ter N linhas/produtos)

**Campo critico `_cod_produto_interno`**: Vem de `PedidoCompras.cod_produto` - este e o codigo interno usado para match.

---

## ETAPA 6: Match com Split - _fazer_match_com_split() (linha ~1707)

Para cada produto unico da NF:
1. Filtrar POs candidatos por preco (0%) e data (±dias uteis)
2. Ordenar por data ASC (PO mais antigo primeiro)
3. Alocar: `min(qtd_pendente, saldo_real_po)`
4. Registrar `MatchAlocacao` para cada alocacao
5. Repetir ate qtd_pendente = 0 ou esgotar POs

**Tolerancia de quantidade**: Se `qtd_nf <= saldo_total * 1.10` → aceita

---

## ETAPA 7: Registro de Resultados

Para cada item da NF, cria `MatchNfPoItem` com:
- `status_match`: 'match', 'sem_depara', 'sem_po', 'preco_diverge', 'data_diverge', 'qtd_diverge'
- `qtd_nf`, `preco_nf`: Valores JA CONVERTIDOS (apos De-Para)
- `qtd_po`, `preco_po`: Valores do PO candidato
- Alocacoes (se split): via `MatchAlocacao`

---

## PREVIEW: buscar_preview_pos_candidatos() (linha 2104)

**REGRA**: Este metodo NUNCA chama Odoo. 100% dados locais.

```python
def buscar_preview_pos_candidatos(self, odoo_dfe_id: int) -> Dict[str, Any]:
    # 1. ValidacaoNfPoDfe.query (LOCAL)
    validacao = ValidacaoNfPoDfe.query.filter_by(odoo_dfe_id=odoo_dfe_id).first()

    # 2. MatchNfPoItem.query (LOCAL - itens JA convertidos)
    itens_match = MatchNfPoItem.query.filter_by(validacao_id=validacao.id).all()

    # 3. PedidoCompras.query (LOCAL)
    pos_local = self._buscar_pos_fornecedor_local(cnpj_fornecedor)

    # 4. Calcular matches (calculo puro, sem I/O)
    pos_candidatos = self._calcular_preview_matches(...)

    # 5. Retornar JSON formatado
    return {'sucesso': True, 'dfe': {...}, 'itens_nf': [...], ...}
```

**Por que local**: Os dados ja foram importados pela validacao (`validar_dfe()`). O preview apenas exibe o que ja existe no banco local.

---

## Mapeamento Odoo → Local

### Cabecalho DFE:
| Campo Odoo | Campo Local (ValidacaoNfPoDfe) |
|---|---|
| `nfe_infnfe_emit_cnpj` | `cnpj_fornecedor` |
| `nfe_infnfe_emit_xnome` | `razao_fornecedor` |
| `nfe_infnfe_dest_cnpj` | `cnpj_empresa_compradora` |
| (buscado via res.partner) | `razao_empresa_compradora` |
| `nfe_infnfe_ide_nnf` | `numero_nf` |
| `nfe_infnfe_ide_serie` | `serie_nf` |
| `protnfe_infnfe_chnfe` | `chave_nfe` |
| `nfe_infnfe_ide_dhemi` | `data_nf` |
| `nfe_infnfe_total_icmstot_vnf` | `valor_total_nf` |
| `purchase_id` | `odoo_po_vinculado_id` + `name` |
| `purchase_fiscal_id` | `odoo_po_fiscal_id` + `name` |

### Linhas DFE:
| Campo Odoo (dfe.line) | Campo Local (MatchNfPoItem) |
|---|---|
| `id` | `odoo_dfe_line_id` |
| `det_prod_cprod` | `cod_produto_fornecedor` |
| `det_prod_xprod` | `nome_produto` |
| `det_prod_ucom` | `um_nf` |
| `det_prod_qcom` * fator | `qtd_nf` (CONVERTIDA!) |
| `det_prod_vuncom` / fator | `preco_nf` (CONVERTIDO!) |
| (via De-Para) | `cod_produto_interno` |
| (via De-Para) | `fator_conversao` |

---

## Status Possiveis (ValidacaoNfPoDfe.status)

| Status | Significado | Proximo Passo |
|---|---|---|
| `pendente` | Nunca processado | Executar validar_dfe() |
| `validando` | Em processamento | Aguardar |
| `aprovado` | 100% match | Pode consolidar |
| `bloqueado` | <100% match | Resolver divergencias |
| `consolidado` | POs ajustados | Finalizado |
| `finalizado_odoo` | DFE ja tem PO no Odoo | Nada a fazer |
| `erro` | Falha no processamento | Verificar logs |

---

## Regra Critica: 100% Match Obrigatorio

```python
pode_consolidar = (status == 'aprovado' AND itens_match == total_itens)
```

Se UM UNICO item falhar, TODO o fluxo bloqueia. Consolidacao (criacao de PO no Odoo) so executa com 100%.
