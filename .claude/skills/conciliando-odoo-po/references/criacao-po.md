# Criacao de PO Conciliador no Odoo

## Metodo Correto: `copy()` do Odoo

O metodo `copy()` e um metodo nativo do ORM do Odoo que duplica um registro completo,
permitindo sobrescrever campos especificos via parametro `default`.

### Por que copy() e nao create()

| Aspecto | create() (ERRADO) | copy() (CORRETO) |
|---------|-------------------|-------------------|
| Campos copiados | Apenas os especificados | TODOS do registro original |
| Chamadas RPC | 2 (read + create) | 1 (copy) |
| Campos obrigatorios | Pode esquecer | Automatico |
| Campos fiscais BR | Manual (l10n_br_*) | Automatico |
| Condicao pagamento | Manual | Automatico |
| Empresa (company_id) | Manual | Automatico |
| Posicao fiscal | Manual | Automatico |
| Tipo de operacao | Manual | Automatico |
| Manutencao futura | Fragi: novo campo = esquecido | Robusto |

## Codigo Validado: Criar PO Conciliador

```python
def _criar_po_conciliador(self, odoo, fornecedor_id, validacao, po_referencia_id):
    """
    Cria PO Conciliador duplicando o PO de referencia via copy() do Odoo.

    IMPORTANTE:
    - Usa copy() nativo que duplica TODOS os campos
    - Sobrescreve apenas: partner_id, date_order, origin, state, order_line
    - Herda automaticamente: empresa, condicao pgto, fiscal, picking_type, etc.
    """
    try:
        # =====================================================
        # PASSO 1: Duplicar PO via copy()
        # =====================================================
        novo_po_id = odoo.execute_kw(
            'purchase.order',
            'copy',
            [po_referencia_id],
            {
                'default': {
                    'partner_id': fornecedor_id,
                    'date_order': validacao.data_nf.isoformat() if validacao.data_nf else datetime.utcnow().isoformat(),
                    'origin': f'Conciliacao NF {validacao.numero_nf or validacao.odoo_dfe_id}',
                    'state': 'draft',
                    'order_line': False,  # Tenta nao copiar linhas
                }
            }
        )

        if not novo_po_id:
            logger.error("Falha ao duplicar PO via copy()")
            return None

        # =====================================================
        # PASSO 2: FALLBACK - Remover linhas se copy() as criou
        # Em algumas versoes do Odoo, order_line=False nao funciona
        # =====================================================
        linhas_existentes = odoo.search(
            'purchase.order.line',
            [[('order_id', '=', novo_po_id)]]
        )
        if linhas_existentes:
            logger.warning(
                f"copy() criou {len(linhas_existentes)} linhas indesejadas, removendo..."
            )
            try:
                odoo.execute_kw(
                    'purchase.order.line',
                    'unlink',
                    [linhas_existentes]
                )
            except Exception as e_del:
                logger.warning(f"Nao foi possivel remover linhas: {e_del}")

        # =====================================================
        # PASSO 3: Buscar nome do novo PO
        # =====================================================
        novo_po = odoo.read('purchase.order', [novo_po_id], ['name'])
        novo_po_name = novo_po[0]['name'] if novo_po else str(novo_po_id)

        logger.info(
            f"PO Conciliador {novo_po_name} criado via copy() "
            f"(baseado em PO {po_referencia_id}) para NF {validacao.numero_nf}"
        )

        return {
            'po_id': novo_po_id,
            'po_name': novo_po_name
        }

    except Exception as e:
        logger.error(f"Erro ao criar PO Conciliador via copy(): {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
```

## Codigo Validado: Criar Linha do PO Conciliador

```python
def _criar_linha_po_conciliador(self, odoo, po_conciliador_id, produto_id,
                                 quantidade, preco_unitario, linha_referencia_id):
    """
    Cria linha no PO Conciliador duplicando a linha de referencia via copy().

    IMPORTANTE:
    - linha_referencia_id = ID da linha ORIGINAL de cada PO
    - NAO e a linha do PO de referencia do cabecalho
    - Cada linha copia CFOP, impostos, UOM da sua propria origem
    - Sobrescreve apenas: order_id, product_id, product_qty, price_unit
    """
    try:
        nova_linha_id = odoo.execute_kw(
            'purchase.order.line',
            'copy',
            [linha_referencia_id],
            {
                'default': {
                    'order_id': po_conciliador_id,
                    'product_id': produto_id,
                    'product_qty': quantidade,      # QTD DA NF (conciliada)
                    'price_unit': preco_unitario,    # PRECO DA NF
                }
            }
        )

        if nova_linha_id:
            logger.debug(
                f"Linha criada no PO Conciliador via copy(): "
                f"produto {produto_id}, qtd {quantidade}, preco {preco_unitario}"
            )

        return nova_linha_id

    except Exception as e:
        logger.error(f"Erro ao criar linha via copy(): {e}")
        return None
```

## Campos que copy() Herda Automaticamente

### No Cabecalho (purchase.order)

| Campo | Descricao | Importancia |
|-------|-----------|-------------|
| `company_id` | Empresa | Obrigatorio |
| `currency_id` | Moeda | Obrigatorio |
| `picking_type_id` | Tipo de operacao de estoque | Obrigatorio |
| `fiscal_position_id` | Posicao fiscal | Fiscal BR |
| `payment_term_id` | Condicao de pagamento | Financeiro |
| `user_id` | Responsavel | Organizacional |
| `l10n_br_*` | Campos fiscais brasileiros | Fiscal BR |
| `incoterm_id` | Incoterm | Comercial |
| `notes` | Notas | Informativo |

### Na Linha (purchase.order.line)

| Campo | Descricao | Importancia |
|-------|-----------|-------------|
| `product_uom` | Unidade de medida | Obrigatorio |
| `name` | Descricao do produto | Informativo |
| `date_planned` | Data planejada | Logistico |
| `taxes_id` | Impostos vinculados | Fiscal |
| `fiscal_operation_id` | Operacao fiscal | Fiscal BR |
| `fiscal_operation_line_id` | Linha operacao fiscal | Fiscal BR |
| `cfop_id` | CFOP | Fiscal BR |
| `ncm_id` | NCM do produto | Fiscal BR |
| `icms_*` | Campos ICMS | Fiscal BR |
| `ipi_*` | Campos IPI | Fiscal BR |
| `pis_*` | Campos PIS | Fiscal BR |
| `cofins_*` | Campos COFINS | Fiscal BR |

## Parametro `default` do copy()

O parametro `default` e um dicionario que sobrescreve campos no registro duplicado:

```python
# Sintaxe:
novo_id = odoo.execute_kw(
    'modelo.odoo',
    'copy',
    [id_original],
    {
        'default': {
            'campo1': valor1,      # Sobrescreve
            'campo2': valor2,      # Sobrescreve
            'campo_o2m': False,    # Limpa campo One2many
            # Campos NAO listados = copiados do original
        }
    }
)
```

### Valores especiais em `default`:
- `False` em campo One2many (ex: `order_line`) → tenta nao copiar os registros filhos
- `False` em campo Many2one → limpa a referencia
- String/int/float → sobrescreve com valor fornecido

## Ajuste de Quantidade no PO Original

```python
def _ajustar_quantidade_linha(self, odoo, linha_id, nova_quantidade):
    """
    Reduz a quantidade de uma linha de PO (saldo apos conciliacao).
    """
    odoo.write(
        'purchase.order.line',
        linha_id,
        {'product_qty': nova_quantidade}
    )
```

## Confirmar PO Conciliador

```python
# Apos criar todas as linhas, confirmar o PO:
odoo.execute_kw(
    'purchase.order',
    'button_confirm',
    [po_conciliador_id]
)
# Muda state: draft → purchase
# Cria stock.picking associado
```

## Cancelar PO Vazio

```python
# Se PO original ficou com saldo 0 em TODAS as linhas:
odoo.execute_kw(
    'purchase.order',
    'button_cancel',
    [po_id]
)
# Muda state: purchase → cancel

# FALLBACK se button_cancel falhar (PO com recebimento parcial):
odoo.write('purchase.order', po_id, {'state': 'cancel'})
```

## Vincular DFe ao PO

```python
# Campo customizado no Odoo (pode variar por instalacao):
odoo.write(
    'purchase.order',
    po_conciliador_id,
    {'dfe_id': validacao.odoo_dfe_id}
)
```

## Teste Isolado de copy()

```bash
source .venv/bin/activate && python -c "
from app.odoo.utils.connection import get_odoo_connection

odoo = get_odoo_connection()
odoo.authenticate()

# Substituir por ID real de PO existente
po_id = 12345

# Testar copy() do PO
novo_id = odoo.execute_kw('purchase.order', 'copy', [po_id], {
    'default': {
        'state': 'draft',
        'origin': 'TESTE copy()',
        'order_line': False
    }
})
print(f'PO criado: {novo_id}')

# Verificar campos herdados
novo_po = odoo.read('purchase.order', [novo_id], [
    'name', 'partner_id', 'payment_term_id', 'fiscal_position_id',
    'company_id', 'currency_id', 'state', 'order_line'
])
print(f'Dados: {novo_po[0]}')

# Verificar se linhas foram copiadas (nao deviam)
linhas = odoo.search('purchase.order.line', [[('order_id', '=', novo_id)]])
print(f'Linhas criadas (deveria ser 0): {len(linhas)}')

# LIMPAR: Cancelar PO de teste
odoo.execute_kw('purchase.order', 'button_cancel', [novo_id])
print('PO de teste cancelado')
"
```
