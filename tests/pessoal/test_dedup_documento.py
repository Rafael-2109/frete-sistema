"""C1 — Dedup por documento autoritativo (nao pelo historico volatil).

Bug auditado: gerar_hash_transacao inclui normalizar_historico(historico) no hash.
O Bradesco reexporta a MESMA transacao (mesmo Docto) com grafia diferente do historico
('Transferencia Pix' vs 'Transfe Pix'), mudando o hash -> a dedup escapa e a tx entra 2x
(R$30.265 dobrados em producao). Quando o documento identifica unicamente a transacao,
o hash NAO deve depender do historico. OFX cartao (FITID reusado) mantem o historico.
"""
from datetime import date
from decimal import Decimal

from app.pessoal.services.parsers.base_parser import gerar_hash_transacao


def test_documento_autoritativo_ignora_historico_no_hash():
    # Bradesco CC: mesmo Docto/data/valor/tipo, grafia do historico diferente -> MESMO hash
    h1 = gerar_hash_transacao(
        1, date(2026, 4, 17), 'Transferencia Pix', Decimal('25000.00'), 'credito',
        documento='1554213', sequencia=0, documento_autoritativo=True,
    )
    h2 = gerar_hash_transacao(
        1, date(2026, 4, 17), 'Transfe Pix', Decimal('25000.00'), 'credito',
        documento='1554213', sequencia=0, documento_autoritativo=True,
    )
    assert h1 == h2


def test_sem_autoritativo_historico_diferencia_hash():
    # OFX cartao (default): FITID reusado; o historico distingue -> hashes DIFERENTES
    h1 = gerar_hash_transacao(
        7, date(2025, 12, 19), 'COMPRA A', Decimal('100.00'), 'debito',
        documento='FIT1', sequencia=0,
    )
    h2 = gerar_hash_transacao(
        7, date(2025, 12, 19), 'COMPRA B', Decimal('100.00'), 'debito',
        documento='FIT1', sequencia=0,
    )
    assert h1 != h2


def test_autoritativo_sem_documento_cai_no_historico():
    # doc vazio: nao ha o que confiar; o historico volta a diferenciar (nao colapsar tx distintas)
    h1 = gerar_hash_transacao(
        1, date(2026, 4, 17), 'PIX PARA A', Decimal('50.00'), 'debito',
        documento='', sequencia=0, documento_autoritativo=True,
    )
    h2 = gerar_hash_transacao(
        1, date(2026, 4, 17), 'PIX PARA B', Decimal('50.00'), 'debito',
        documento='', sequencia=0, documento_autoritativo=True,
    )
    assert h1 != h2


def test_documento_zero_tratado_como_ausente():
    # Docto '0' normaliza para '' -> nao autoritativo, usa historico
    h1 = gerar_hash_transacao(
        1, date(2026, 4, 17), 'PIX PARA A', Decimal('50.00'), 'debito',
        documento='0', sequencia=0, documento_autoritativo=True,
    )
    h2 = gerar_hash_transacao(
        1, date(2026, 4, 17), 'PIX PARA B', Decimal('50.00'), 'debito',
        documento='0', sequencia=0, documento_autoritativo=True,
    )
    assert h1 != h2
