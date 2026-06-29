"""Tests do roteamento de importacao OFX (resolucao de conta + fluxo fim-a-fim).

Os ACCTIDs sao gerados por teste (uuid) para nao colidir com contas Nubank reais
ja semeadas no banco (dev/prod).
"""
from uuid import uuid4

import pytest

from app import db as _db
from app.pessoal.models import PessoalConta, PessoalTransacao, PessoalImportacao
from app.pessoal.services.parsers.ofx_parser import resolver_conta_ofx
from app.pessoal.routes import importacao as importacao_mod


def _ofx_cartao(acctid: str) -> bytes:
    return (
        "OFXHEADER:100\r\nDATA:OFXSGML\r\nVERSION:102\r\nENCODING:USASCII\r\nCHARSET:1252\r\n"
        "<OFX>\r\n<CREDITCARDMSGSRSV1>\r\n<CCSTMTTRNRS>\r\n<CCSTMTRS>\r\n<CURDEF>BRL\r\n"
        "<CCACCTFROM>\r\n<ACCTID>" + acctid + "\r\n</CCACCTFROM>\r\n<BANKTRANLIST>\r\n"
        "<DTSTART>20260509000000[-3:BRT]\r\n<DTEND>20260609000000[-3:BRT]\r\n"
        "<STMTTRN>\r\n<TRNTYPE>DEBIT\r\n<DTPOSTED>20260607000000[-3:BRT]\r\n"
        "<TRNAMT>-40.90\r\n<FITID>aa01\r\n<MEMO>Dm*Spotify\r\n</STMTTRN>\r\n"
        "<STMTTRN>\r\n<TRNTYPE>CREDIT\r\n<DTPOSTED>20260529000000[-3:BRT]\r\n"
        "<TRNAMT>5000.00\r\n<FITID>aa02\r\n<MEMO>Pagamento recebido\r\n</STMTTRN>\r\n"
        "</BANKTRANLIST>\r\n</CCSTMTRS>\r\n</CCSTMTTRNRS>\r\n</CREDITCARDMSGSRSV1>\r\n</OFX>\r\n"
    ).encode('latin-1')


class _FakeUser:
    id = 1
    nome = 'Teste'


@pytest.fixture
def conta_cartao_nubank(pessoal_ctx, membro):
    acctid = str(uuid4())  # unico -> nao colide com contas Nubank ja semeadas
    c = PessoalConta(
        nome=f'Nubank Cartão {uuid4().hex[:6]}',
        tipo='cartao_credito',
        banco='nubank',
        numero_conta=acctid,
        membro_id=membro.id,
        ativa=True,
    )
    _db.session.add(c)
    _db.session.commit()
    pessoal_ctx['contas'].append(c.id)
    c._acctid_teste = acctid
    return c


def test_resolver_conta_ofx_por_acctid(conta_cartao_nubank):
    acctid = conta_cartao_nubank._acctid_teste
    assert resolver_conta_ofx(acctid, 'cartao') == conta_cartao_nubank.id


def test_resolver_conta_ofx_fallback_unica_nubank(conta_cartao_nubank):
    """ACCTID desconhecido: fallback resolve SE houver exatamente 1 cartao Nubank."""
    n = PessoalConta.query.filter_by(
        banco='nubank', tipo='cartao_credito', ativa=True,
    ).count()
    res = resolver_conta_ofx('uuid-inexistente-xyz', 'cartao')
    if n == 1:
        assert res == conta_cartao_nubank.id
    else:
        assert res is None  # ambiguo -> fallback nao resolve


def test_resolver_conta_ofx_acctid_de_cartao_nao_vira_conta_corrente(conta_cartao_nubank):
    """ACCTID de cartao + tipo extrato nunca resolve para a conta de cartao."""
    acctid = conta_cartao_nubank._acctid_teste
    assert resolver_conta_ofx(acctid, 'extrato') != conta_cartao_nubank.id


def test_processar_ofx_cartao_fim_a_fim(pessoal_ctx, conta_cartao_nubank, monkeypatch):
    monkeypatch.setattr(importacao_mod, 'current_user', _FakeUser())

    res = importacao_mod._processar_ofx(
        'nu_cartao.ofx', _ofx_cartao(conta_cartao_nubank._acctid_teste),
    )
    assert res['sucesso'] is True, res.get('erro')
    imp_id = res['importacao_id']
    pessoal_ctx['importacoes'].append(imp_id)

    txs = PessoalTransacao.query.filter_by(importacao_id=imp_id).all()
    for t in txs:
        pessoal_ctx['transacoes'].append(t.id)

    imp = _db.session.get(PessoalImportacao, imp_id)
    assert imp.tipo_arquivo == 'fatura_cartao'
    assert imp.conta_id == conta_cartao_nubank.id
    assert len(txs) == 2
    assert all(t.origem_import == 'ofx' for t in txs)

    # "Pagamento recebido" (credito no cartao) deve estar excluido do relatorio
    pgto = next(t for t in txs if t.historico == 'Pagamento recebido')
    assert pgto.tipo == 'credito'
    assert pgto.excluir_relatorio is True

    # Compra (Spotify) entra normal (nao excluida)
    compra = next(t for t in txs if t.historico == 'Dm*Spotify')
    assert compra.tipo == 'debito'
    assert compra.excluir_relatorio is False
