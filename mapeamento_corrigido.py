# Mapeamento corrigido baseado em verificação real
# Gerado automaticamente em 2025-07-15

CAMPOS_VALIDOS = {
    "sale.order.line": {
        "obrigatorios": ['id', 'product_id', 'order_id'],
        "opcionais": ['name', 'product_uom_qty', 'price_unit', 'state']
    },
    "product.product": {
        "obrigatorios": ['id', 'name'],
        "opcionais": ['default_code', 'list_price', 'standard_price', 'categ_id', 'type', 'uom_id', 'description', 'active']
    },
    "res.partner": {
        "obrigatorios": ['id', 'name'],
        "opcionais": ['vat', 'street', 'city', 'state_id', 'country_id', 'phone', 'email', 'customer_rank', 'supplier_rank']
    },
    "delivery.carrier": {
        "obrigatorios": ['id', 'name'],
        "opcionais": ['product_id', 'delivery_type', 'fixed_price', 'active']
    },
}
