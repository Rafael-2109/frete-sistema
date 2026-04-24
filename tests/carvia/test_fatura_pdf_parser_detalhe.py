"""Regression test do _regex_detalhe_ctes (fatura_pdf_parser.py).

Bug: o regex primario exigia `\\s+` obrigatorio entre NOME e NF_FLAG, mas em
PDFs SSW com nome de destinatario longo o texto extraido cola NOME+FLAG sem
espaco (ex: "SUPERMERCADOPONTONOVOGUAC1"). Resultado: de 5 linhas no PDF, apenas
1 casava e a fatura vinculava so 1 CTe.

Fix: `(.+?)\\s+(\\d+)` -> `(.+?)\\s*([01])` (espaco opcional + flag restrito a 0/1).
"""

from __future__ import annotations

from app.carvia.services.parsers.fatura_pdf_parser import FaturaPDFParser


def _parser_stub(texto: str):
    """Cria parser sem abrir PDF real — chama _regex_detalhe_ctes diretamente."""
    # pdf_bytes minimo so para satisfazer o __init__; nao e usado pelo metodo.
    parser = FaturaPDFParser.__new__(FaturaPDFParser)
    return parser._regex_detalhe_ctes(texto)


def test_detalhe_ssw_nome_grudado_com_flag():
    """PDF SSW com nome destinatario longo cola NOME+FLAG sem espaco (caso BoletoCV1[1]170545).

    As 5 linhas correspondem as NFs 49611-49615 da fatura 131-7 do cliente NOTCO BRASIL.
    """
    texto = "\n".join([
        "1 00000199 23/04/26 71782163000200 SUPERMERCADOPONTONOVOGUAC1 000049612 1.152,24 89 125,06 15,01 0,00 0,00 125,06",
        "1 00000200 23/04/26 71782163000626 SUPERMERCADOPONTONOVOLTDA1 000049615 1.393,81 105 148,01 17,76 0,00 0,00 148,01",
        "1 00000201 23/04/26 71782163000464 SUPERMERCADOPONTONOVOGUAC1 000049614 3.262,02 243 343,06 41,17 0,00 0,00 343,06",
        "1 00000202 23/04/26 71782163000111 SUPERMERCADO PONTO NOVOGU 1 000049611 4.177,49 331 467,91 56,15 0,00 0,00 467,91",
        "1 00000203 23/04/26 71782163000545 SUPERMERCADOPONTONOVOGUAC1 000049613 5.455,63 471 665,97 79,92 0,00 0,00 665,97",
    ])
    itens = _parser_stub(texto)
    assert len(itens) == 5, f"Esperado 5 itens, obtido {len(itens)}"

    ctes = [it['cte_numero'] for it in itens]
    nfs = [it['nf_numero'] for it in itens]
    assert ctes == ['199', '200', '201', '202', '203']
    assert nfs == ['49612', '49615', '49614', '49611', '49613']

    # Soma dos fretes deve bater com total da fatura (R$ 1.750,01)
    total_frete = sum(it['frete'] for it in itens)
    assert abs(total_frete - 1750.01) < 0.01


def test_detalhe_ssw_nome_com_espaco_antes_flag():
    """Formato classico com espaco entre NOME e FLAG (ja funcionava antes do fix).

    Cobre regressao: o fix nao deve quebrar o caso com espaco.
    """
    texto = "1 00000001 09/01/26 09089839000112 LAIOUNS IMP. E EXPORTACAO 0 000033268 23.206,00 514 1.250,00 150,00 0,00 0,00 1.250,00"
    itens = _parser_stub(texto)
    assert len(itens) == 1
    assert itens[0]['cte_numero'] == '1'
    assert itens[0]['nf_numero'] == '33268'
    assert itens[0]['contraparte_cnpj'] == '09089839000112'
    assert itens[0]['contraparte_nome'] == 'LAIOUNS IMP. E EXPORTACAO'
    assert itens[0]['frete'] == 1250.0


def test_detalhe_nome_com_digitos_nao_confunde_com_flag():
    """Nome terminando em digito (ex: "LOJA 5", "LOJA 10") nao pode ser confundido com flag.

    O fix restringe flag a [01]. Non-greedy expande o nome ate encontrar
    `[01]\\s+\\d{6,12}`, evitando colisao com digitos intermediarios do nome.
    """
    texto_loja5 = "1 00000100 01/04/26 12345678000199 LOJA 5 CENTRO 1 000012345 500,00 10 50,00 6,00 0,00 0,00 50,00"
    texto_loja10 = "1 00000101 01/04/26 12345678000199 LOJA 10 CENTRO 1 000012346 500,00 10 50,00 6,00 0,00 0,00 50,00"
    itens5 = _parser_stub(texto_loja5)
    itens10 = _parser_stub(texto_loja10)
    assert len(itens5) == 1
    assert len(itens10) == 1
    assert itens5[0]['contraparte_nome'] == 'LOJA 5 CENTRO'
    assert itens10[0]['contraparte_nome'] == 'LOJA 10 CENTRO'
    assert itens5[0]['nf_numero'] == '12345'
    assert itens10[0]['nf_numero'] == '12346'


def test_detalhe_cpf_raw_11_digitos():
    """Contraparte pessoa fisica (CPF 11 digitos) tambem deve funcionar."""
    texto = "1 00000050 15/03/26 12345678901 JOAO DA SILVA 1 000099999 500,00 20 50,00 6,00 0,00 0,00 50,00"
    itens = _parser_stub(texto)
    assert len(itens) == 1
    assert itens[0]['contraparte_cnpj'] == '12345678901'
    assert itens[0]['contraparte_nome'] == 'JOAO DA SILVA'
