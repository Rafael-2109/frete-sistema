# Campos do Modelo delivery.carrier

**Modelo Odoo:** `delivery.carrier`
**Descricao:** Metodos de entrega / Transportadoras
**Total de Campos:** 34

---

## Campos Principais

| Campo | Tipo | Descricao | Obrigatorio |
|-------|------|-----------|-------------|
| `id` | integer | ID interno | Auto |
| `name` | char | Nome do metodo de entrega | Sim |
| `display_name` | char | Nome de exibicao | Auto |
| `active` | boolean | Ativo | Nao (padrao True) |
| `sequence` | integer | Sequencia de ordenacao | Nao |

---

## Campos de Configuracao

| Campo | Tipo | Valores/Descricao |
|-------|------|-------------------|
| `delivery_type` | selection | fixed, base_on_rule, etc |
| `integration_level` | selection | rate, rate_and_ship |
| `invoice_policy` | selection | estimated, real |
| `prod_environment` | boolean | Ambiente de producao |
| `debug_logging` | boolean | Log de debug |

---

## Campos de Preco

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `fixed_price` | float | Preco fixo | 50.00 |
| `margin` | float | Margem percentual | 10.0 |
| `fixed_margin` | float | Margem fixa | 5.00 |
| `free_over` | boolean | Frete gratis acima de valor | True |
| `amount` | float | Valor minimo para frete gratis | 500.00 |
| `shipping_insurance` | integer | Percentual de seguro | 1 |

---

## Campos de Relacionamento

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_partner_id` | many2one | **Parceiro (res.partner) vinculado** |
| `product_id` | many2one | Produto de frete |
| `company_id` | many2one | Empresa |
| `price_rule_ids` | one2many | Regras de preco |

> **IMPORTANTE:** `l10n_br_partner_id` vincula a transportadora a um parceiro (res.partner).
> Isso permite buscar dados do parceiro (CNPJ, endereco, etc) atraves deste relacionamento.

---

## Campos de Abrangencia

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `country_ids` | many2many | Paises atendidos |
| `state_ids` | many2many | Estados atendidos |
| `zip_prefix_ids` | many2many | Prefixos de CEP atendidos |
| `route_ids` | many2many | Rotas |

---

## Campos de Devolucao

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `can_generate_return` | boolean | Pode gerar etiqueta de devolucao |
| `return_label_on_delivery` | boolean | Gerar etiqueta de devolucao na entrega |
| `get_return_label_from_portal` | boolean | Etiqueta disponivel no portal |

---

## Campos de Descricao

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `carrier_description` | text | Descricao do metodo de entrega |

---

## Campos de Data

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `create_date` | datetime | Data de criacao |
| `create_uid` | many2one | Criado por |
| `write_date` | datetime | Ultima atualizacao |
| `write_uid` | many2one | Atualizado por |

---

## Valores de delivery_type

| Valor | Descricao |
|-------|-----------|
| `fixed` | Preco fixo |
| `base_on_rule` | Baseado em regras |
| ... | (outros dependem de modulos instalados) |

---

## Filtros Uteis

```python
# Transportadoras ativas
[('active', '=', True)]

# Por nome
[('name', 'ilike', 'correios')]

# Com preco fixo definido
[('fixed_price', '>', 0)]

# Que atendem SP
[('state_ids.code', '=', 'SP')]

# Com frete gratis acima de valor
[('free_over', '=', True)]

# Incluir inativas
['|', ('active', '=', True), ('active', '=', False)]
```

---

## Como Buscar Dados do Parceiro da Transportadora

A transportadora esta vinculada a um parceiro atraves de `l10n_br_partner_id`.
Para obter dados completos (CNPJ, endereco, etc):

```python
# 1. Buscar transportadora
transportadora = odoo.search_read(
    'delivery.carrier',
    [('name', 'ilike', 'correios')],
    fields=['id', 'name', 'l10n_br_partner_id']
)

# 2. Se tiver parceiro vinculado, buscar dados
if transportadora and transportadora[0].get('l10n_br_partner_id'):
    partner_id = transportadora[0]['l10n_br_partner_id'][0]
    parceiro = odoo.search_read(
        'res.partner',
        [('id', '=', partner_id)],
        fields=['name', 'vat', 'l10n_br_cnpj', 'street', 'city']
    )
```

---

## Relacionamento com Outros Modelos

```
delivery.carrier
    │
    ├── res.partner (l10n_br_partner_id)
    │   └── Dados cadastrais da transportadora
    │
    ├── product.product (product_id)
    │   └── Produto de frete para faturamento
    │
    ├── stock.picking
    │   └── Entregas usando esta transportadora
    │
    └── sale.order
        └── Pedidos com esta transportadora
```

---

## Atualizacoes

| Data | Alteracao |
|------|-----------|
| 02/12/2025 | Documento criado com mapeamento completo |
