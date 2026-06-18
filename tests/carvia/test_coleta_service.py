"""Testes do CarviaColetaService — Coletas CarVia ("papel de pao", stream 3).

Cobre: criacao + linhas, vinculo a NF real com propagacao de local_cd (Stream 1),
marcar coletada (cria CarviaDespesa tipo COLETA a conciliar), congelamento pos-coletada
e sugestao de NF por numero normalizado. Service e flush-only (compativel com fixture `db`).
"""
from decimal import Decimal

import pytest

from app.carvia.services.documentos.coleta_service import CarviaColetaService, ColetaError


def _criar_nf(db, numero='000123', local_cd='VICTORIO_MARCHEZINE'):
    from app.carvia.models.documentos import CarviaNf
    nf = CarviaNf(
        numero_nf=numero,
        cnpj_emitente='12345678000199',
        nome_emitente='EMITENTE TESTE',
        cnpj_destinatario='98765432000155',
        nome_destinatario='CLIENTE REAL LTDA',
        tipo_fonte='MANUAL',
        status='ATIVA',
        local_cd=local_cd,
        criado_por='test@bot',
    )
    db.session.add(nf)
    db.session.flush()
    return nf


def test_criar_e_adicionar_linha(db):
    coleta = CarviaColetaService.criar_coleta(
        contratado_nome='Ze Fretes', placa='ABC1D23',
        valor_coleta=Decimal('500.00'), local_cd='TENENTE_MARQUES', usuario='test@bot',
    )
    assert coleta.numero_coleta == f'COL-{coleta.id:03d}'
    assert coleta.status == 'RASCUNHO'
    assert coleta.local_cd == 'TENENTE_MARQUES'

    CarviaColetaService.adicionar_linha(
        coleta, numero_nf='123', nome_cliente_rascunho='Loja do Ze',
        cidade_destino='Curitiba', qtd_motos=4, valor_frete=Decimal('80.00'), vendedor='Fulano',
    )
    assert coleta.total_nfs == 1
    assert coleta.total_motos == 4


def test_vincular_propaga_local_cd(db):
    # Coleta TM; NF nasce VM -> ao vincular, NF assume TM (Stream 1)
    coleta = CarviaColetaService.criar_coleta(local_cd='TENENTE_MARQUES', usuario='test@bot')
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='000123', nome_cliente_rascunho='Rascunho LTDA')
    nf = _criar_nf(db, numero='123', local_cd='VICTORIO_MARCHEZINE')

    CarviaColetaService.vincular_nf(linha, nf.id)
    assert linha.carvia_nf_id == nf.id
    assert linha.vinculada is True
    assert nf.local_cd == 'TENENTE_MARQUES'  # propagado da coleta
    # nome efetivo passa a ser o REAL da NF (consolidacao rascunho -> real)
    assert linha.nome_cliente_efetivo == 'CLIENTE REAL LTDA'


def test_marcar_coletada_cria_despesa(db):
    coleta = CarviaColetaService.criar_coleta(
        contratado_nome='Ze Fretes', placa='ABC1D23',
        valor_coleta=Decimal('500.00'), local_cd='TENENTE_MARQUES', usuario='test@bot',
    )
    nf = _criar_nf(db, numero='555')
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='555')
    CarviaColetaService.vincular_nf(linha, nf.id)

    CarviaColetaService.marcar_coletada(coleta, usuario='test@bot')
    assert coleta.status == 'COLETADA'
    assert coleta.data_coletada is True
    assert coleta.data_coletada_em is not None
    assert coleta.despesa_id is not None

    from app.carvia.models.financeiro import CarviaDespesa
    desp = db.session.get(CarviaDespesa, coleta.despesa_id)
    assert desp is not None
    assert desp.tipo_despesa == 'COLETA'
    assert desp.valor == Decimal('500.00')
    assert desp.status == 'PENDENTE'
    # NF vinculada manteve o local_cd da coleta
    assert nf.local_cd == 'TENENTE_MARQUES'


def test_marcar_coletada_idempotente_sem_valor_nao_cria_despesa(db):
    coleta = CarviaColetaService.criar_coleta(usuario='test@bot')  # sem valor_coleta
    CarviaColetaService.marcar_coletada(coleta, usuario='test@bot')
    assert coleta.status == 'COLETADA'
    assert coleta.despesa_id is None  # sem valor -> sem despesa
    # idempotente: chamar de novo nao quebra
    CarviaColetaService.marcar_coletada(coleta, usuario='test@bot')
    assert coleta.status == 'COLETADA'


def test_congelamento_apos_coletada(db):
    coleta = CarviaColetaService.criar_coleta(valor_coleta=Decimal('10'), usuario='test@bot')
    CarviaColetaService.marcar_coletada(coleta, usuario='test@bot')
    assert coleta.pode_editar() is False
    with pytest.raises(ColetaError):
        CarviaColetaService.adicionar_linha(coleta, numero_nf='999')


def test_sugerir_nf_normaliza_numero(db):
    coleta = CarviaColetaService.criar_coleta(usuario='test@bot')
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='000123')  # zeros a esquerda
    nf = _criar_nf(db, numero='123')
    sugestoes = CarviaColetaService.sugerir_nf(linha)
    assert nf.id in [s.id for s in sugestoes]
