# 📋 MAPEAMENTO DE CAMPOS: Odoo → CarteiraPrincipal

## 🔍 QUERIES DO ODOO (5 queries em lote)

1. **sale.order** - Dados do pedido
2. **res.partner** - Dados do cliente e endereço
3. **product.product** - Dados do produto
4. **product.category** - Categorias do produto
5. **sale.order.line** - Linhas do pedido (dados base)

---

## 📊 MAPEAMENTO CAMPO A CAMPO

| **Campo CarteiraPrincipal** | **Origem Odoo** | **Modelo/Campo Odoo** | **Processamento** |
|---------------------------|----------------|-------------------|-----------------|
| **IDENTIFICAÇÃO** |
| `num_pedido` | sale.order | `name` | Direto |
| `cod_produto` | sale.order.line | `product_id[0]` | ID do produto |
| `status_pedido` | sale.order | `state` | Mapeado: draft→Cotação, sale→Pedido de venda |
| `pedido_cliente` | sale.order | `l10n_br_pedido_compra` | Direto |
| **DATAS** |
| `data_pedido` | sale.order | `create_date` | Convertido para date |
| `data_entrega_pedido` | sale.order | `commitment_date` | Convertido para date |
| `expedicao` | - | - | NULL (calculado depois) |
| `agendamento` | - | - | NULL (preservado se existir) |
| `protocolo` | - | - | '' (preservado se existir) |
| **QUANTIDADES** |
| `qtd_produto_pedido` | sale.order.line | `product_uom_qty` | Float direto |
| `qtd_cancelada_produto_pedido` | sale.order.line | `qty_cancelado` | Float direto |
| `qtd_saldo_produto_pedido` | CALCULADO | - | `qtd_produto - qtd_cancelada - qtd_faturada` |
| `preco_produto_pedido` | sale.order.line | `price_unit` | Float direto |
| **CLIENTE** |
| `cnpj_cpf` | res.partner | `l10n_br_cnpj` ou `l10n_br_cpf` | CNPJ prioritário |
| `raz_social` | res.partner | `name` | String direto |
| `raz_social_red` | res.partner | `trade_name` ou `name[:100]` | Fallback para name |
| `municipio` | res.partner | `l10n_br_municipio_id[1]` | Extrai nome da cidade (BR) |
| `estado` | res.partner | `state_id[1]` | Extrai UF |
| `vendedor` | sale.order | `user_id[1]` | Nome do usuário |
| `equipe_vendas` | sale.order | `team_id[1]` | Nome da equipe |
| **PRODUTO** |
| `nome_produto` | product.product | `name` | String direto |
| `unid_medida_produto` | sale.order.line | `product_uom[1]` | Nome da unidade |
| `categoria_produto` | product.category | Hierarquia 3 níveis | Categoria avô |
| `materia_prima_produto` | product.category | Hierarquia 2 níveis | Categoria pai |
| `embalagem_produto` | product.category | `name` | Categoria direta |
| **COMERCIAL** |
| `cond_pgto_pedido` | sale.order | `payment_term_id[1]` | Nome do termo |
| `forma_pgto_pedido` | sale.order | `payment_provider_id[1]` | Nome do provedor |
| `incoterm` | sale.order | `incoterm` | Extrai código antes do ']' |
| `metodo_entrega_pedido` | sale.order | `carrier_id[1]` | Nome transportadora |
| `cliente_nec_agendamento` | res.partner | `agendamento` | Campo customizado |
| `observ_ped_1` | sale.order | `picking_note` | String até 700 chars |
| **ENDEREÇO ENTREGA** |
| `empresa_endereco_ent` | res.partner (shipping) | `name` | Nome do endereço |
| `cnpj_endereco_ent` | res.partner (shipping) | `l10n_br_cnpj` | CNPJ entrega |
| `nome_cidade` | res.partner (shipping) | `l10n_br_municipio_id[1]` | Cidade entrega (BR) |
| `cod_uf` | res.partner (shipping) | `state_id[1]` | UF entrega (2 chars) |
| `cep_endereco_ent` | res.partner (shipping) | `zip` | CEP |
| `bairro_endereco_ent` | res.partner (shipping) | `l10n_br_endereco_bairro` | Bairro |
| `rua_endereco_ent` | res.partner (shipping) | `street` | Rua |
| `endereco_ent` | res.partner (shipping) | `l10n_br_endereco_numero` | Número |
| `telefone_endereco_ent` | res.partner (shipping) | `phone` | Telefone |
| **AUDITORIA** |
| `ativo` | - | - | True (sempre) |
| `created_at` | - | - | datetime.now() |
| `updated_at` | - | - | datetime.now() |
| `created_by` | - | - | 'Sistema Odoo' |
| `updated_by` | - | - | 'Sistema Odoo' |

---

## ⚙️ PROCESSAMENTO ESPECIAL

### Cálculo de `qtd_saldo_produto_pedido`:
```python
# Busca em FaturamentoProduto
qtd_faturada = SELECT SUM(qtd_produto_faturado)
                FROM faturamento_produto
                WHERE origem = num_pedido
                AND cod_produto = cod_produto
                AND status_nf != 'Cancelado'

# Cálculo final
qtd_saldo = qtd_produto_pedido - qtd_cancelada_produto_pedido - qtd_faturada
```

### Campos NÃO atualizados (preservados se existirem):
- `separacao_lote_id`
- `qtd_saldo`, `valor_saldo`, `peso`, `pallet` (campos de separação)
- `roteirizacao`
- Campos de estoque (`estoque_d0` até `estoque_d28`)

---

## 📍 LOCALIZAÇÃO NO CÓDIGO

### Arquivo Principal:
`app/odoo/services/carteira_service.py`

### Métodos Relevantes:
- `obter_carteira_pendente()` - Busca dados do Odoo (linha 65)
- `_processar_dados_carteira_com_multiplas_queries()` - Processamento em lote (linha 156)
- `_mapear_item_carteira_otimizado()` - Mapeamento campo a campo (linha 366)
- `_sanitizar_dados_carteira()` - Sanitização antes de salvar (linha 597)

### Sincronização Incremental (Proposta):
- Adicionar campo `odoo_write_date` em CarteiraPrincipal
- Filtrar por `write_date >= (now - 40 minutos)`
- Atualizar TODOS os campos exceto `qtd_saldo_produto_pedido` que é calculado

