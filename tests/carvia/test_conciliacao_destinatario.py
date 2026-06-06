"""Testes do fix I5 — destinatario como sinal adicional no match de conciliacao.

REVISAO_ARQUITETURA_2026 I5: o motor de conciliacao ignorava o destinatario da
NF. Em frete (CIF/FOB) o pagador bancario real pode ser o destinatario, nao o
pagador cadastrado na fatura. O fix adiciona destinatario/remetente como sinal
"+" (CNPJ deterministico um degrau abaixo do pagador + nome no jaccard).

pontuar_documentos e funcao PURA (sem DB) — testavel com objetos simples.
"""
from datetime import date
from types import SimpleNamespace

from app.carvia.services.financeiro.carvia_sugestao_service import (
    pontuar_documentos,
)


def _linha(descricao, valor=1000.0, razao_social=None):
    return SimpleNamespace(
        valor=valor,
        data=date(2026, 6, 6),
        razao_social=razao_social,
        descricao=descricao,
        memo='',
    )


def test_destinatario_cnpj_na_descricao_recebe_boost():
    # A descricao traz o CNPJ do DESTINATARIO, nao o do pagador cadastrado.
    linha = _linha('Pix recebido 12345678000199 referente frete')
    doc = {
        'tipo_documento': 'fatura_cliente',
        'id': 1,
        'saldo': 1000.0,
        'nome': 'CLIENTE PAGADOR LTDA',
        'cnpj_cliente': '99999999000100',          # pagador != descricao
        'remetente_cnpj': '99999999000100',
        'destinatarios': [{'cnpj': '12345678000199', 'nome': 'DESTINO SA'}],
        'vencimento': '06/06/2026',
        'data': '06/06/2026',
    }

    docs = pontuar_documentos(linha, [doc])

    assert docs[0]['score_cnpj_direto'] is True
    assert docs[0]['score_cnpj_direto_tipo'] == 'CNPJ_DESTINATARIO'
    assert docs[0]['score'] >= 0.85


def test_pagador_direto_tem_prioridade_sobre_destinatario():
    # Quando o proprio pagador casa, mantem CNPJ_COMPLETO (0.95), nao secundario.
    linha = _linha('Pix recebido 99999999000100 frete')
    doc = {
        'tipo_documento': 'fatura_cliente',
        'id': 1,
        'saldo': 1000.0,
        'nome': 'CLIENTE PAGADOR LTDA',
        'cnpj_cliente': '99999999000100',
        'destinatarios': [{'cnpj': '12345678000199', 'nome': 'DESTINO SA'}],
        'vencimento': '06/06/2026',
        'data': '06/06/2026',
    }

    docs = pontuar_documentos(linha, [doc])

    assert docs[0]['score_cnpj_direto_tipo'] == 'CNPJ_COMPLETO'
    assert docs[0]['score'] >= 0.95


def test_doc_sem_destinatarios_nao_quebra():
    # fatura_transportadora nao tem enrichment de destinatarios — no-op seguro.
    linha = _linha('TED transportadora x', valor=500.0, razao_social='TRANSP X')
    doc = {
        'tipo_documento': 'fatura_transportadora',
        'id': 2,
        'saldo': 500.0,
        'nome': 'TRANSP X',
        'cnpj_transportadora': '11111111000111',
        'vencimento': '',
        'data': '',
    }

    docs = pontuar_documentos(linha, [doc])

    assert 'score' in docs[0]
    assert docs[0]['score_cnpj_direto'] is False
