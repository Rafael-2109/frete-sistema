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


def test_nf_nao_vincula_a_duas_coletas(db):
    """Bug 🔴: uma CarviaNf pertence a no maximo 1 coleta (UNIQUE uq_carvia_coleta_nf)."""
    nf = _criar_nf(db, numero='999')
    c1 = CarviaColetaService.criar_coleta(usuario='test@bot')
    l1 = CarviaColetaService.adicionar_linha(c1, numero_nf='999')
    CarviaColetaService.vincular_nf(l1, nf.id)

    c2 = CarviaColetaService.criar_coleta(usuario='test@bot')
    l2 = CarviaColetaService.adicionar_linha(c2, numero_nf='999')
    with pytest.raises(ColetaError):
        CarviaColetaService.vincular_nf(l2, nf.id)


def test_sugerir_nf_exclui_ja_vinculada(db):
    """Bug 🔴: NF ja vinculada a qualquer coleta nao deve ser sugerida de novo."""
    nf = _criar_nf(db, numero='123')
    c1 = CarviaColetaService.criar_coleta(usuario='test@bot')
    l1 = CarviaColetaService.adicionar_linha(c1, numero_nf='123')
    assert nf.id in [s.id for s in CarviaColetaService.sugerir_nf(l1)]  # antes de vincular: sugere

    CarviaColetaService.vincular_nf(l1, nf.id)
    c2 = CarviaColetaService.criar_coleta(usuario='test@bot')
    l2 = CarviaColetaService.adicionar_linha(c2, numero_nf='123')
    assert nf.id not in [s.id for s in CarviaColetaService.sugerir_nf(l2)]  # depois: excluida


def test_editar_coleta_repropaga_local_cd(db):
    """Bug 🔴: mudar o destino da coleta re-propaga para as NFs ja vinculadas."""
    coleta = CarviaColetaService.criar_coleta(local_cd='VICTORIO_MARCHEZINE', usuario='test@bot')
    nf = _criar_nf(db, numero='321', local_cd='VICTORIO_MARCHEZINE')
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='321')
    CarviaColetaService.vincular_nf(linha, nf.id)
    assert nf.local_cd == 'VICTORIO_MARCHEZINE'

    CarviaColetaService.editar_coleta(coleta, local_cd='TENENTE_MARQUES')
    assert coleta.local_cd == 'TENENTE_MARQUES'
    assert nf.local_cd == 'TENENTE_MARQUES'  # re-propagado


def test_marcar_coletada_cancelada_bloqueia(db):
    """Edge 🟠: coleta CANCELADA nao pode ser marcada como coletada (bypass via POST)."""
    coleta = CarviaColetaService.criar_coleta(valor_coleta=Decimal('10'), usuario='test@bot')
    CarviaColetaService.cancelar_coleta(coleta)
    with pytest.raises(ColetaError):
        CarviaColetaService.marcar_coletada(coleta, usuario='test@bot')


def test_parse_decimal_br():
    """Edge 🟠: entrada BR de milhar sem centavos nao vira 1,5."""
    from app.carvia.routes.coleta_routes import _parse_decimal
    assert _parse_decimal('1.500,00') == 1500.0
    assert _parse_decimal('1.500') == 1500.0       # milhar BR (era 1.5 antes do fix)
    assert _parse_decimal('1.234.567') == 1234567.0
    assert _parse_decimal('10.50') == 10.5         # decimal real (2 casas)
    assert _parse_decimal('1234,56') == 1234.56
    assert _parse_decimal('500') == 500.0
    assert _parse_decimal('') is None
