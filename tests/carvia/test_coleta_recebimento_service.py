"""Testes do recebimento por chassi da coleta (stream 4).

Foco no INVARIANTE do usuario: recebimento e por MOTO e o BACKFILL faz a ordem NF<->chassi
nao impactar a vinculacao (conferir chassi antes da NF vinculada -> reconcilia ao vincular).
"""
import pytest

from app.carvia.services.documentos.coleta_service import CarviaColetaService
from app.carvia.services.documentos.coleta_recebimento_service import (
    CarviaColetaRecebimentoService, RecebimentoError)


def _nf_com_chassis(db, numero, chassis):
    from app.carvia.models.documentos import CarviaNf, CarviaNfVeiculo
    nf = CarviaNf(numero_nf=numero, cnpj_emitente='12345678000199', nome_emitente='EMIT',
                  nome_destinatario='CLIENTE REAL', tipo_fonte='MANUAL', status='ATIVA',
                  criado_por='test@bot')
    db.session.add(nf); db.session.flush()
    for ch in chassis:
        db.session.add(CarviaNfVeiculo(nf_id=nf.id, chassi=ch, modelo='POP 110'))
    db.session.flush()
    return nf


def test_conferir_vinculado_e_alerta(db):
    coleta = CarviaColetaService.criar_coleta(usuario='test@bot')
    nf = _nf_com_chassis(db, '100', ['9C2AAAA00AA000001'])
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='100')
    CarviaColetaService.vincular_nf(linha, nf.id)

    # chassi da NF vinculada -> VINCULADO
    l1 = CarviaColetaRecebimentoService.conferir_chassi(coleta, '9C2AAAA00AA000001', qr_code_lido=True, usuario='conf')
    assert l1.status == 'VINCULADO'
    assert l1.carvia_nf_veiculo_id is not None
    # chassi desconhecido -> ALERTA (escaneio livre)
    l2 = CarviaColetaRecebimentoService.conferir_chassi(coleta, 'CHASSI_FANTASMA_X', usuario='conf')
    assert l2.status == 'ALERTA'
    assert l2.carvia_nf_veiculo_id is None


def test_backfill_chassi_antes_da_nf(db):
    """O INVARIANTE: conferir chassi ANTES de vincular a NF -> ALERTA; ao vincular a NF
    (que contem o chassi), a reconciliacao retro-vincula -> VINCULADO."""
    coleta = CarviaColetaService.criar_coleta(usuario='test@bot')
    # NF existe no sistema com o chassi, mas a linha da coleta ainda NAO esta vinculada
    nf = _nf_com_chassis(db, '200', ['9C2BBBB00BB000002'])
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='200')  # so rascunho, sem vinculo

    # confere o chassi ANTES de vincular -> ALERTA (NF nao pertence a coleta ainda)
    l = CarviaColetaRecebimentoService.conferir_chassi(coleta, '9C2BBBB00BB000002', usuario='conf')
    assert l.status == 'ALERTA'

    # vincula a NF -> dispara reconciliacao (backfill)
    CarviaColetaService.vincular_nf(linha, nf.id)
    db.session.refresh(l)
    assert l.status == 'VINCULADO'
    assert l.carvia_nf_veiculo_id is not None


def test_nf_recebida_quando_todos_chassis(db):
    coleta = CarviaColetaService.criar_coleta(usuario='test@bot')
    nf = _nf_com_chassis(db, '300', ['CH1', 'CH2'])
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='300')
    CarviaColetaService.vincular_nf(linha, nf.id)

    CarviaColetaRecebimentoService.conferir_chassi(coleta, 'CH1', usuario='conf')
    assert CarviaColetaRecebimentoService.nf_recebida(coleta, nf.id) is False  # falta CH2
    CarviaColetaRecebimentoService.conferir_chassi(coleta, 'CH2', usuario='conf')
    assert CarviaColetaRecebimentoService.nf_recebida(coleta, nf.id) is True


def test_chassi_duplicado_bloqueia(db):
    coleta = CarviaColetaService.criar_coleta(usuario='test@bot')
    CarviaColetaRecebimentoService.conferir_chassi(coleta, 'DUP1', usuario='conf')
    with pytest.raises(RecebimentoError):
        CarviaColetaRecebimentoService.conferir_chassi(coleta, 'dup1', usuario='conf')  # normaliza p/ maiusc


def test_chassis_esperados_autocomplete(db):
    coleta = CarviaColetaService.criar_coleta(usuario='test@bot')
    nf = _nf_com_chassis(db, '700', ['9C2AAA00', '9C2BBB00'])
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='700')
    CarviaColetaService.vincular_nf(linha, nf.id)

    esperados = CarviaColetaRecebimentoService.chassis_esperados(coleta)
    chassis = {e['chassi'] for e in esperados}
    assert chassis == {'9C2AAA00', '9C2BBB00'}

    # confere um -> sai do esperado
    CarviaColetaRecebimentoService.conferir_chassi(coleta, '9C2AAA00', usuario='conf')
    esperados = CarviaColetaRecebimentoService.chassis_esperados(coleta)
    assert {e['chassi'] for e in esperados} == {'9C2BBB00'}
    # filtro por q
    assert CarviaColetaRecebimentoService.chassis_esperados(coleta, q='BBB')[0]['chassi'] == '9C2BBB00'
    assert CarviaColetaRecebimentoService.chassis_esperados(coleta, q='ZZZ') == []


def test_finalizar_status(db):
    coleta = CarviaColetaService.criar_coleta(usuario='test@bot')
    nf = _nf_com_chassis(db, '400', ['OK1'])
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='400')
    CarviaColetaService.vincular_nf(linha, nf.id)
    CarviaColetaRecebimentoService.conferir_chassi(coleta, 'OK1', usuario='conf')
    CarviaColetaRecebimentoService.conferir_chassi(coleta, 'EXTRA_ALERTA', usuario='conf')
    receb = CarviaColetaRecebimentoService.finalizar(coleta, usuario='conf')
    assert receb.status == 'COM_DIVERGENCIA'  # tem ALERTA

    # remove o alerta e re-finaliza -> CONCLUIDO
    alerta = receb.chassis.filter_by(status='ALERTA').first()
    CarviaColetaRecebimentoService.remover_chassi(alerta)
    receb = CarviaColetaRecebimentoService.finalizar(coleta, usuario='conf')
    assert receb.status == 'CONCLUIDO'
