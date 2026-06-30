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
# Extracao do beneficiario (historico_completo e UPPERCASE em producao)
# ---------------------------------------------------------------------------
def test_beneficiario_extrai_de_historico_completo_uppercase():
    """Em producao historico_completo vem normalizado (MAIUSCULO). O extrator
    precisa casar 'PIX' independente de caixa (regressao do dry-run de prod)."""
    from app.pessoal.services.pix_credito_service import _beneficiario
    h = ('TRANSFERENCIA ENVIADA PELO PIX - ESTHERCITA A C B PIOVACCARI - '
         '***.871.568-** - ITAU UNIBANCO S.A. (0341) AGENCIA: 9635 CONTA: 910-4')
    assert _beneficiario(h) == 'ESTHERCITA A C B PIOVACCARI'


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


def _tx(ctx, imp, conta, historico, valor, tipo, data, categoria_id=None, historico_completo=None):
    t = PessoalTransacao(
        importacao_id=imp.id, conta_id=conta.id, data=data,
        historico=historico, historico_completo=historico_completo or historico,
        valor=Decimal(str(valor)),
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
        # historico_completo em MAIUSCULO, como o normalizador grava em producao
        historico_completo=f'TRANSFERENCIA ENVIADA PELO PIX - {benef} - ***.871.568-** - ITAU UNIBANCO',
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


def test_split_rejeita_compra_com_juros_absurdo(pessoal_ctx, membro):
    """Nome repetido (ex.: RENATA recebe varios Pix) pode casar a compra errada, com
    juros desproporcional. Compra com juros > 50% do principal NAO splita (parcial)."""
    from app.pessoal.services import pix_credito_service as pcs

    nuconta = _conta(pessoal_ctx, membro, 'NuConta', 'conta_corrente', '63685323-8')
    cartao = _conta(pessoal_ctx, membro, 'Nubank Cartao', 'cartao_credito')
    imp_n = _imp(pessoal_ctx, nuconta)
    imp_c = _imp(pessoal_ctx, cartao)
    D = date(2099, 3, 1)
    benef = 'FULANO REPETIDO DE TAL'
    _tx(pessoal_ctx, imp_n, nuconta,
        'Valor adicionado na conta por cartão de crédito - Valor adicionado para Pix no Crédito',
        1000.00, 'credito', D)
    _tx(pessoal_ctx, imp_n, nuconta,
        f'Transferência enviada pelo Pix - {benef} - ITAÚ', 1000.00, 'debito', D,
        historico_completo=f'TRANSFERENCIA ENVIADA PELO PIX - {benef} - ITAU')
    compra = _tx(pessoal_ctx, imp_c, cartao, benef, 1700.00, 'debito', D)  # juros 700 = 70%

    pcs.detectar_e_processar(janela_dias=10)
    c = _db.session.get(PessoalTransacao, compra.id)
    # registrar eventuais marcacoes para cleanup
    for f in PessoalTransacao.query.filter(PessoalTransacao.conta_id.in_([nuconta.id, cartao.id])).all():
        if f.pix_credito_grupo and f.id not in pessoal_ctx['transacoes']:
            pessoal_ctx['transacoes'].append(f.id)
    # compra NAO foi splitada (juros desproporcional)
    assert c.eh_pix_credito is False
    assert float(c.valor) == 1700.00


def test_parcial_fecha_quando_compra_chega(pessoal_ctx, membro, cat_juros):
    """Parcial (sem compra) NAO forma grupo e fica reprocessavel: quando a compra do
    cartao e importada depois, a deteccao seguinte fecha o trio (split)."""
    from app.pessoal.services import pix_credito_service as pcs

    nuconta = _conta(pessoal_ctx, membro, 'NuConta', 'conta_corrente', '63685323-8')
    cartao = _conta(pessoal_ctx, membro, 'Nubank Cartao', 'cartao_credito')
    imp_n = _imp(pessoal_ctx, nuconta)
    imp_c = _imp(pessoal_ctx, cartao)
    D = date(2099, 4, 1)
    benef = 'BENEFICIARIO PARCIAL UNICO'
    funding = _tx(pessoal_ctx, imp_n, nuconta,
                  'Valor adicionado na conta por cartão de crédito - Valor adicionado para Pix no Crédito',
                  800.00, 'credito', D)
    _tx(pessoal_ctx, imp_n, nuconta,
        f'Transferência enviada pelo Pix - {benef} - ITAÚ', 800.00, 'debito', D,
        historico_completo=f'TRANSFERENCIA ENVIADA PELO PIX - {benef} - ITAU')

    # 1a deteccao: sem compra -> parcial (funding excluido, SEM grupo)
    pcs.detectar_e_processar(janela_dias=10)
    f1 = _db.session.get(PessoalTransacao, funding.id)
    assert f1.pix_credito_grupo is None
    assert f1.excluir_relatorio is True

    # A fatura do cartao chega depois
    compra = _tx(pessoal_ctx, imp_c, cartao, benef, 880.00, 'debito', D)  # juros 80 = 10%

    # 2a deteccao: agora fecha o trio
    pcs.detectar_e_processar(janela_dias=10)
    f2 = _db.session.get(PessoalTransacao, funding.id)
    assert f2.pix_credito_grupo is not None
    _registrar_grupo(pessoal_ctx, f2.pix_credito_grupo)
    c2 = _db.session.get(PessoalTransacao, compra.id)
    assert c2.eh_pix_credito is True
    assert float(c2.valor) == 800.00
    juros = PessoalTransacao.query.filter(
        PessoalTransacao.pix_credito_grupo == f2.pix_credito_grupo,
        PessoalTransacao.excluir_relatorio.is_(False),
        PessoalTransacao.conta_id == cartao.id,
    ).first()
    assert juros is not None and float(juros.valor) == 80.00


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
