"""IDs fixos diversos do Odoo NACOM (sem lar mais especifico).

Centraliza valores de dominio que estavam hardcoded como atributos de classe
em services (`stock_picking_service.py`, `inventario_pipeline_service.py`).
Para IDs de empresa/local/fiscal use `locations.py` / `operacoes_fiscais.py`.
"""

# account.incoterms code=CIF. G004: NACOM exige incoterm nos pickings inter-company.
INCOTERM_CIF = 6

# delivery.carrier "(61.724.241/0001-78) NACOM GOYA ..." — transportadora propria.
CARRIER_NACOM = 996

# payment.provider 'SEM PAGAMENTO' — usado em invoices inter-company de inventario
# (movimentacao sem financeiro). Setado em account.move.payment_provider_id.
PAYMENT_PROVIDER_SEM_PAGAMENTO = 38
