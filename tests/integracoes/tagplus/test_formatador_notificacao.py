"""Testa a formatação WhatsApp de pedido/NF (sem DB, sem rede)."""
from app.integracoes.tagplus.services import formatador_notificacao as fmt

NFE = {
    "numero": 3706, "serie": 1, "valor_nota": 28594.78,
    "data_emissao": "2024-08-15T10:30:00Z",
    "destinatario": {"razao_social": "CESTA BASICA BRASIL COMERCIO"},
    "itens": [
        {"qtd": 44, "valor_unitario": 69.58,
         "produto": {"codigo": "4320147", "descricao": "AZEITONA VERDE FATIADA"}},
    ],
}
PEDIDO = {
    "numero": 555, "valor_total": 1200.50,
    "cliente": {"razao_social": "MERCADO X"},
    "vendedor": {"nome": "João Silva"},
    "data_entrega": "2024-08-20",
    "itens": [
        {"qtd": 2, "valor_unitario": 600.25,
         "produto_servico": {"codigo": "P1", "descricao": "PALMITO"}},
    ],
}


def test_formatar_nfe_contem_campos_principais():
    texto = fmt.formatar_nfe(NFE, vendedor_nome="João Silva")
    assert "3706" in texto
    assert "CESTA BASICA BRASIL" in texto
    assert "João Silva" in texto
    assert "28.594,78" in texto
    assert "4320147" in texto
    assert "|" not in texto


def test_formatar_nfe_omite_vendedor_quando_ausente():
    texto = fmt.formatar_nfe(NFE, vendedor_nome=None)
    assert "Vendedor" not in texto


def test_formatar_pedido_contem_vendedor():
    texto = fmt.formatar_pedido(PEDIDO)
    assert "555" in texto
    assert "MERCADO X" in texto
    assert "João Silva" in texto
    assert "1.200,50" in texto


def test_trunca_itens_acima_do_limite():
    nfe = dict(NFE)
    nfe["itens"] = [
        {"qtd": 1, "valor_unitario": 1.0, "produto": {"codigo": str(i), "descricao": f"P{i}"}}
        for i in range(40)
    ]
    texto = fmt.formatar_nfe(nfe, vendedor_nome=None)
    assert "(+10 itens)" in texto
