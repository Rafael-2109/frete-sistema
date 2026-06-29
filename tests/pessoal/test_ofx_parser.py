"""Tests do parser OFX do modulo Pessoal (extrato NuConta + fatura cartao Nubank).

Parser e logica pura (sem DB) — os OFX abaixo sao trechos fieis dos arquivos reais
do Nubank (cartao em USASCII/CHARSET 1252; extrato em UTF-8 com acentos).
"""
from datetime import date
from decimal import Decimal

from app.pessoal.services.parsers.ofx_parser import (
    detectar_ofx, parsear_ofx_pessoal,
)


# Fatura de cartao (CREDITCARDMSGSRSV1 / CCSTMTRS) — USASCII
OFX_CARTAO = (
    b"OFXHEADER:100\r\nDATA:OFXSGML\r\nVERSION:102\r\nENCODING:USASCII\r\n"
    b"CHARSET:1252\r\n<OFX>\r\n<CREDITCARDMSGSRSV1>\r\n<CCSTMTTRNRS>\r\n"
    b"<CCSTMTRS>\r\n<CURDEF>BRL\r\n<CCACCTFROM>\r\n"
    b"<ACCTID>5f00ffaf-315a-4466-aa0f-6ef2b15baa39\r\n</CCACCTFROM>\r\n"
    b"<BANKTRANLIST>\r\n<DTSTART>20260509000000[-3:BRT]\r\n"
    b"<DTEND>20260609000000[-3:BRT]\r\n"
    b"<STMTTRN>\r\n<TRNTYPE>DEBIT\r\n<DTPOSTED>20260608000000[-3:BRT]\r\n"
    b"<TRNAMT>-10.00\r\n<FITID>6a251c6c\r\n<MEMO>Amazon Ad Free For Pri\r\n</STMTTRN>\r\n"
    b"<STMTTRN>\r\n<TRNTYPE>CREDIT\r\n<DTPOSTED>20260529000000[-3:BRT]\r\n"
    b"<TRNAMT>5000.00\r\n<FITID>6a19f752\r\n<MEMO>Pagamento recebido\r\n</STMTTRN>\r\n"
    b"<STMTTRN>\r\n<TRNTYPE>CREDIT\r\n<DTPOSTED>20260606000000[-3:BRT]\r\n"
    b"<TRNAMT>0.00\r\n<FITID>6a0e2ccf\r\n<MEMO>Juros de pagamento parcial da fatura (rotativo)\r\n</STMTTRN>\r\n"
    b"</BANKTRANLIST>\r\n</CCSTMTRS>\r\n</CCSTMTTRNRS>\r\n</CREDITCARDMSGSRSV1>\r\n</OFX>\r\n"
)

# Extrato NuConta (BANKMSGSRSV1 / STMTRS) — UTF-8 com acentos
OFX_EXTRATO = (
    "OFXHEADER:100\r\nDATA:OFXSGML\r\nVERSION:102\r\nENCODING:UTF-8\r\n"
    "CHARSET:NONE\r\n<OFX>\r\n<BANKMSGSRSV1>\r\n<STMTTRNRS>\r\n<STMTRS>\r\n"
    "<CURDEF>BRL\r\n<BANKACCTFROM>\r\n<BANKID>0260\r\n<BRANCHID>1\r\n"
    "<ACCTID>63685323-8\r\n<ACCTTYPE>CHECKING\r\n</BANKACCTFROM>\r\n"
    "<BANKTRANLIST>\r\n<DTSTART>20250801000000[-3:BRT]\r\n"
    "<DTEND>20250831000000[-3:BRT]\r\n"
    "<STMTTRN>\r\n<TRNTYPE>CREDIT\r\n<DTPOSTED>20250801000000[-3:BRT]\r\n"
    "<TRNAMT>3000.00\r\n<FITID>688cbdac\r\n"
    "<MEMO>Transferência recebida pelo Pix - RENATA GALAFASSI DE QUEIROZ - "
    "•••.529.541-•• - BCO BRADESCO S.A. (0237) Agência: 111 Conta: 128948-9\r\n</STMTTRN>\r\n"
    "<STMTTRN>\r\n<TRNTYPE>DEBIT\r\n<DTPOSTED>20250813000000[-3:BRT]\r\n"
    "<TRNAMT>-22.00\r\n<FITID>689d2e3f\r\n"
    "<MEMO>Transferência enviada pelo Pix - Uyara Queiroz Costa\r\n</STMTTRN>\r\n"
    "</BANKTRANLIST>\r\n</STMTRS>\r\n</STMTTRNRS>\r\n</BANKMSGSRSV1>\r\n</OFX>\r\n"
).encode('utf-8')


def test_detectar_ofx_positivo():
    assert detectar_ofx(OFX_CARTAO) is True
    assert detectar_ofx(OFX_EXTRATO) is True


def test_detectar_ofx_negativo():
    assert detectar_ofx(b"Data;Historico;Valor\r\n01/01;COMPRA;-10,00") is False
    assert detectar_ofx("qualquer csv;a;b") is False


def test_parse_cartao_tipo_e_acctid():
    res = parsear_ofx_pessoal(OFX_CARTAO)
    assert res.tipo == 'cartao'
    assert res.acctid == '5f00ffaf-315a-4466-aa0f-6ef2b15baa39'
    assert res.periodo_inicio == date(2026, 5, 9)
    assert res.periodo_fim == date(2026, 6, 9)


def test_parse_cartao_ignora_valor_zero():
    res = parsear_ofx_pessoal(OFX_CARTAO)
    # 3 STMTTRN, mas a de TRNAMT=0.00 (juros) e ignorada
    assert len(res.transacoes) == 2
    memos = [t.historico for t in res.transacoes]
    assert 'Amazon Ad Free For Pri' in memos
    assert 'Pagamento recebido' in memos


def test_parse_cartao_valores_e_tipos():
    res = parsear_ofx_pessoal(OFX_CARTAO)
    compra = next(t for t in res.transacoes if t.historico == 'Amazon Ad Free For Pri')
    assert compra.tipo == 'debito'
    assert compra.valor == Decimal('10.00')  # sempre positivo
    assert compra.documento == '6a251c6c'

    pgto = next(t for t in res.transacoes if t.historico == 'Pagamento recebido')
    assert pgto.tipo == 'credito'
    assert pgto.valor == Decimal('5000.00')


def test_parse_extrato_tipo_acctid_e_utf8():
    res = parsear_ofx_pessoal(OFX_EXTRATO)
    assert res.tipo == 'extrato'
    assert res.acctid == '63685323-8'
    assert len(res.transacoes) == 2

    dep = next(t for t in res.transacoes if t.tipo == 'credito')
    assert dep.valor == Decimal('3000.00')
    # acentos preservados (UTF-8) e numero da conta de origem no memo
    assert 'Transferência recebida' in dep.historico
    assert 'Conta: 128948-9' in dep.historico


def test_parse_extrato_debito_negativo_vira_positivo():
    res = parsear_ofx_pessoal(OFX_EXTRATO)
    saida = next(t for t in res.transacoes if t.tipo == 'debito')
    assert saida.valor == Decimal('22.00')
    assert 'Uyara' in saida.historico
