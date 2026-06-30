"""Testes Task 8: tratativas com movimento de estoque.

Cenarios:
  1. USAR_ESTOQUE -> consumir baixa o saldo (delta -qtd)
  2. USAR_OUTRA_MOTO -> canibalizar delta 0 + abre FALTA_PECA no doador
  3. VENDA grava receita_* na linha de consumo
  4. solicitar_compra cria compra e seta fase=AGUARDANDO_PECA SEM resolver
  5. guard chassi_origem != chassi_destino em canibalizar
"""

import uuid
from decimal import Decimal
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPeca, AssaiPendencia, AssaiEstoqueMovimento,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE,
    MOVIMENTO_CONSUMO, MOVIMENTO_CANIBALIZACAO,
    PENDENCIA_CATEGORIA_FALTA_PECA, PENDENCIA_CATEGORIA_VENDA,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_POS_VENDA_LOJA,
    PENDENCIA_FASE_AGUARDANDO_PECA, COMPRA_PECA_TIPO_COMPRA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.movimento_service import (
    registrar_entrada, consumir, canibalizar, saldo, EstoqueError,
)
from app.motos_assai.services.pendencia_service import abrir_pendencia, solicitar_compra


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto(chassi, admin_user, estado=EVENTO_MONTADA):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(moto)
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    if estado != EVENTO_ESTOQUE:
        emitir_evento(chassi, estado, admin_user.id)
    db.session.flush()
    return moto


def _peca(admin_user, nome='Bateria 60V'):
    p = AssaiPeca(nome=nome, ativo=True, criado_por_id=admin_user.id)
    db.session.add(p)
    db.session.flush()
    return p


def test_usar_estoque_consumo_baixa_saldo(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        peca = _peca(admin_user)
        registrar_entrada(
            peca_id=peca.id, quantidade=5, custo_unitario=100,
            operador_id=admin_user.id,
        )
        assert saldo(peca.id) == Decimal('5')
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta bateria',
            operador_id=admin_user.id, peca_id=peca.id,
        )
        mov = consumir(
            peca_id=peca.id, quantidade=1, pendencia_id=ficha.id,
            chassi_destino=chassi, operador_id=admin_user.id,
        )
        assert mov.tipo == MOVIMENTO_CONSUMO
        assert mov.delta_almoxarifado == Decimal('-1')
        assert mov.custo_unitario == Decimal('100.0000')
        assert mov.receita_unitaria is None
        assert saldo(peca.id) == Decimal('4')
        db.session.rollback()


def test_usar_outra_moto_canibalizacao_delta0_abre_falta_no_doador(app, admin_user):
    with app.app_context():
        receptor = f'TST_R{_uid()}'
        doador = f'TST_D{_uid()}'
        _moto(receptor, admin_user)
        _moto(doador, admin_user)
        peca = _peca(admin_user)
        registrar_entrada(
            peca_id=peca.id, quantidade=3, custo_unitario=100,
            operador_id=admin_user.id,
        )
        saldo_antes = saldo(peca.id)
        ficha_r = abrir_pendencia(
            chassi=receptor, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta peca receptor',
            operador_id=admin_user.id, peca_id=peca.id,
        )
        mov = canibalizar(
            peca_id=peca.id, quantidade=1, chassi_origem=doador,
            chassi_destino=receptor, pendencia_id=ficha_r.id,
            operador_id=admin_user.id,
        )
        assert mov.tipo == MOVIMENTO_CANIBALIZACAO
        assert mov.delta_almoxarifado == Decimal('0')
        assert mov.custo_unitario == Decimal('0.0000')
        assert saldo(peca.id) == saldo_antes  # canibalizacao nao mexe no saldo
        # Doador ganhou uma FALTA_PECA root e virou PENDENTE
        falta_doador = (
            AssaiPendencia.query
            .filter_by(chassi=doador, categoria=PENDENCIA_CATEGORIA_FALTA_PECA)
            .first()
        )
        assert falta_doador is not None
        assert falta_doador.pendencia_pai_id is None
        assert falta_doador.detalhes.get('canibalizado_para') == receptor
        assert status_efetivo(doador) == EVENTO_PENDENTE
        db.session.rollback()


def test_venda_grava_receita_no_consumo(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        peca = _peca(admin_user, nome='Carregador')
        registrar_entrada(
            peca_id=peca.id, quantidade=2, custo_unitario=80,
            operador_id=admin_user.id,
        )
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_VENDA,
            origem=PENDENCIA_ORIGEM_POS_VENDA_LOJA, descricao='Venda de peca avulsa',
            operador_id=admin_user.id, peca_id=peca.id, retorno_fisico=False,
        )
        mov = consumir(
            peca_id=peca.id, quantidade=1, pendencia_id=ficha.id,
            chassi_destino=chassi, operador_id=admin_user.id,
            receita_unitaria=150,
        )
        assert mov.receita_unitaria == Decimal('150.0000')
        assert mov.receita_total == Decimal('150.00')
        db.session.rollback()


def test_solicitar_compra_seta_aguardando_peca_sem_resolver(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        peca = _peca(admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Sem estoque, pedir compra',
            operador_id=admin_user.id, peca_id=peca.id,
        )
        compra = solicitar_compra(
            pendencia_id=ficha.id, tipo=COMPRA_PECA_TIPO_COMPRA,
            itens=[{'peca_id': peca.id, 'quantidade': 2}],
            operador_id=admin_user.id,
        )
        assert compra.tipo == COMPRA_PECA_TIPO_COMPRA
        assert compra.itens[0].pendencia_id == ficha.id
        assert ficha.fase == PENDENCIA_FASE_AGUARDANDO_PECA
        assert ficha.resolvida_em is None  # provisao nao resolve
        db.session.rollback()


def test_canibalizar_guard_doador_igual_receptor(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        peca = _peca(admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta peca',
            operador_id=admin_user.id, peca_id=peca.id,
        )
        with pytest.raises(EstoqueError, match='doador'):
            canibalizar(
                peca_id=peca.id, quantidade=1, chassi_origem=chassi,
                chassi_destino=chassi, pendencia_id=ficha.id,
                operador_id=admin_user.id,
            )
        db.session.rollback()
