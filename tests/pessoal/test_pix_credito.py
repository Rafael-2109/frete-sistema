"""Tests do tratamento "Pix no Credito" do Nubank (Caso 1).

Mecanica de uma operacao Pix no Credito:
- NuConta credito  "Valor adicionado na conta por cartao de credito - ...Pix no Credito" (+V) = funding (liquidez)
- NuConta debito   "Transferencia enviada pelo Pix - <BENEF>" (-V)                            = despesa principal
- Cartao Nubank    "<BENEF>" (-(V+juros))                                                     = compra (principal + juros)

Tratamento desejado no relatorio de competencia:
- funding excluido
- principal (do Pix-saida) como despesa
- compra do cartao -> split: principal excluido + juros visivel (Juros & Multa)
"""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app import db as _db
from app.pessoal.models import (
    PessoalConta, PessoalCategoria, PessoalImportacao, PessoalTransacao,
)
from app.pessoal.services.categorizacao_service import categorizar_transacao


# ---------------------------------------------------------------------------
# Heuristica do funding (rode na importacao, independe do casamento do trio)
# ---------------------------------------------------------------------------
def test_funding_pix_no_credito_e_excluido(make_transacao):
    """O credito 'Valor adicionado...Pix no Credito' e perna de liquidez, nao receita."""
    t = make_transacao(
        tipo='credito',
        valor=Decimal('1500.00'),
        hash_transacao='funding_pix_cred',
        historico=(
            'Valor adicionado na conta por cartão de crédito - '
            'Valor adicionado para Pix no Crédito'
        ),
    )
    r = categorizar_transacao(t)
    assert r.excluir_relatorio is True
    assert r.status == 'CATEGORIZADO'
    assert r.eh_transferencia_propria is False
    assert r.eh_pagamento_cartao is False


def test_funding_tem_prioridade_sobre_regra_existente(make_transacao):
    """A exclusao do funding roda ANTES das regras PADRAO/heuristicas."""
    t = make_transacao(
        tipo='credito',
        valor=Decimal('320.00'),
        hash_transacao='funding_pix_cred2',
        historico=(
            'Valor adicionado na conta por cartão de crédito - '
            'Valor adicionado para Pix no Crédito'
        ),
    )
    r = categorizar_transacao(t)
    assert r.excluir_relatorio is True


# ---------------------------------------------------------------------------
# Deteccao do trio + split (pix_credito_service)
# ---------------------------------------------------------------------------
def _conta(ctx, membro, nome, tipo, numero=None):
    c = PessoalConta(
        nome=f'{nome} {uuid4().hex[:6]}', tipo=tipo, banco='nubank',
        numero_conta=numero, membro_id=membro.id, ativa=True,
    )
    _db.session.add(c)
    _db.session.commit()
    ctx['contas'].append(c.id)
    return c


def _imp(ctx, conta):
    imp = PessoalImportacao(
        conta_id=conta.id, nome_arquivo=f'{uuid4().hex[:6]}.ofx',
        tipo_arquivo='extrato_cc', total_linhas=0, linhas_importadas=0, status='IMPORTADO',
    )
    _db.session.add(imp)
    _db.session.commit()
    ctx['importacoes'].append(imp.id)
    return imp


def _tx(ctx, imp, conta, historico, valor, tipo, data, categoria_id=None):
    t = PessoalTransacao(
        importacao_id=imp.id, conta_id=conta.id, data=data,
        historico=historico, historico_completo=historico, valor=Decimal(str(valor)),
        tipo=tipo, status='PENDENTE', excluir_relatorio=False, categoria_id=categoria_id,
        hash_transacao=f'h{uuid4().hex[:16]}',
    )
    _db.session.add(t)
    _db.session.commit()
    ctx['transacoes'].append(t.id)
    return t


def _cat(ctx, nome, grupo):
    c = PessoalCategoria(nome=f'{nome}_{uuid4().hex[:5]}', grupo=grupo, ativa=True)
    _db.session.add(c)
    _db.session.commit()
    ctx['categorias'].append(c.id)
    return c


@pytest.fixture
def cat_juros(pessoal_ctx):
    """Categoria de juros (grupo Financeiro, nome com 'Juros')."""
    existente = PessoalCategoria.query.filter(
        PessoalCategoria.grupo == 'Financeiro',
        PessoalCategoria.nome.ilike('%juros%'),
        PessoalCategoria.ativa.is_(True),
    ).first()
    if existente:
        return existente
    c = PessoalCategoria(nome='Juros & Multa', grupo='Financeiro', ativa=True)
    _db.session.add(c)
    _db.session.commit()
    pessoal_ctx['categorias'].append(c.id)
    return c


@pytest.fixture
def trio(pessoal_ctx, membro, cat_juros):
    """Operacao Pix no Credito completa: funding + pix-saida + compra cartao."""
    nuconta = _conta(pessoal_ctx, membro, 'NuConta', 'conta_corrente', '63685323-8')
    cartao = _conta(pessoal_ctx, membro, 'Nubank Cartao', 'cartao_credito')
    cat_benef = _cat(pessoal_ctx, 'Consultas', 'Saude')
    imp_n = _imp(pessoal_ctx, nuconta)
    imp_c = _imp(pessoal_ctx, cartao)

    D = date(2099, 2, 19)
    benef = 'ESTHERCITA A C B PIOVACCARI'
    funding = _tx(
        pessoal_ctx, imp_n, nuconta,
        'Valor adicionado na conta por cartão de crédito - Valor adicionado para Pix no Crédito',
        1500.00, 'credito', D,
    )
    pix = _tx(
        pessoal_ctx, imp_n, nuconta,
        f'Transferência enviada pelo Pix - {benef} - •••.871.568-•• - ITAÚ UNIBANCO',
        1500.00, 'debito', D, categoria_id=cat_benef.id,
    )
    compra = _tx(
        pessoal_ctx, imp_c, cartao, benef, 1642.71, 'debito', D, categoria_id=cat_benef.id,
    )
    return {
        'nuconta': nuconta, 'cartao': cartao, 'imp_c': imp_c,
        'funding': funding, 'pix': pix, 'compra': compra,
        'cat_juros': cat_juros, 'cat_benef': cat_benef,
    }


def _registrar_grupo(ctx, grupo):
    """Registra no cleanup as transacoes (incl. juros sintetico) criadas no grupo."""
    for t in PessoalTransacao.query.filter_by(pix_credito_grupo=grupo).all():
        if t.id not in ctx['transacoes']:
            ctx['transacoes'].append(t.id)


def test_detecta_trio_e_faz_split(trio, pessoal_ctx):
    from app.pessoal.services import pix_credito_service as pcs

    res = pcs.detectar_e_processar(janela_dias=5)
    assert res['trios_processados'] >= 1
    _registrar_grupo(pessoal_ctx, _db.session.get(PessoalTransacao, trio['funding'].id).pix_credito_grupo)

    funding = _db.session.get(PessoalTransacao, trio['funding'].id)
    pix = _db.session.get(PessoalTransacao, trio['pix'].id)
    compra = _db.session.get(PessoalTransacao, trio['compra'].id)

    grupo = funding.pix_credito_grupo
    assert grupo

    # Funding: excluido + marcado + agrupado
    assert funding.eh_pix_credito is True
    assert funding.excluir_relatorio is True
    assert funding.pix_credito_grupo == grupo

    # Pix-saida: despesa principal (mantida visivel), marcada e agrupada
    assert pix.eh_pix_credito is True
    assert pix.excluir_relatorio is False
    assert float(pix.valor) == 1500.00
    assert pix.pix_credito_grupo == grupo

    # Compra do cartao: split -> vira o principal (excluido)
    assert compra.eh_pix_credito is True
    assert compra.excluir_relatorio is True
    assert float(compra.valor) == 1500.00
    assert compra.pix_credito_grupo == grupo

    # Linha de juros criada: visivel, categoria de juros, mesma fatura
    juros = PessoalTransacao.query.filter(
        PessoalTransacao.pix_credito_grupo == grupo,
        PessoalTransacao.conta_id == trio['cartao'].id,
        PessoalTransacao.excluir_relatorio.is_(False),
        PessoalTransacao.eh_pix_credito.is_(True),
    ).first()
    assert juros is not None
    assert float(juros.valor) == 142.71
    assert juros.categoria_id == trio['cat_juros'].id
    assert juros.importacao_id == trio['imp_c'].id  # mesma fatura -> soma fecha

    # Soma da fatura preservada (principal + juros == valor original da compra)
    assert float(compra.valor) + float(juros.valor) == 1642.71


def test_deteccao_idempotente(trio, pessoal_ctx):
    """Rodar duas vezes nao duplica a linha de juros nem re-splita."""
    from app.pessoal.services import pix_credito_service as pcs

    pcs.detectar_e_processar(janela_dias=5)
    grupo = _db.session.get(PessoalTransacao, trio['funding'].id).pix_credito_grupo
    _registrar_grupo(pessoal_ctx, grupo)
    n1 = PessoalTransacao.query.filter_by(pix_credito_grupo=grupo).count()

    pcs.detectar_e_processar(janela_dias=5)
    _registrar_grupo(pessoal_ctx, grupo)
    n2 = PessoalTransacao.query.filter_by(pix_credito_grupo=grupo).count()
    assert n1 == n2 == 4  # funding + pix + compra(principal) + juros
