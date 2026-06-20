"""Fluxo da Cotacao Comercial CarVia (CotacaoV2) — 3 mudancas (2026-06-20):

1. Tipo de carga OPCIONAL na criacao (antes obrigava DIRETA/FRACIONADA).
2. Aproveitamento AUTOMATICO do valor do CTe quando a NF da cotacao ja tem
   CTe CarVia (CarviaOperacao.cte_valor) — sem depender de flag criacao_tardia.
3. "Gravar" pula a etapa de aprovacao do cliente: marcar_enviado vai direto
   para APROVADO.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock


def _user():
    u = MagicMock()
    u.is_authenticated = True
    u.sistema_carvia = True
    u.perfil = 'administrador'
    u.email = 'tester@carvia'
    return u


def _cliente_enderecos(db):
    """Cria cliente + origem global (SP) + destino (RJ). Retorna (cli, origem, destino)."""
    from app.carvia.models import CarviaCliente, CarviaClienteEndereco
    cli = CarviaCliente(nome_comercial='Cliente Cotacao Teste', criado_por='test')
    db.session.add(cli)
    db.session.flush()
    origem = CarviaClienteEndereco(
        cliente_id=None, cnpj='11111111000111', tipo='ORIGEM', ativo=True,
        razao_social='Origem Global', fisico_uf='SP', fisico_cidade='SAO PAULO',
        criado_por='test',
    )
    destino = CarviaClienteEndereco(
        cliente_id=cli.id, cnpj='22222222000122', tipo='DESTINO', ativo=True,
        razao_social='Destino Cliente', fisico_uf='RJ', fisico_cidade='RIO DE JANEIRO',
        criado_por='test',
    )
    db.session.add_all([origem, destino])
    db.session.flush()
    return cli, origem, destino


def _cotacao_minima(db, valor_final=None):
    """Cria cotacao via service em RASCUNHO, opcionalmente com valor + data_expedicao."""
    from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service
    cli, origem, destino = _cliente_enderecos(db)
    cot, erro = CotacaoV2Service.criar_cotacao(
        cliente_id=cli.id,
        endereco_origem_id=origem.id,
        endereco_destino_id=destino.id,
        tipo_material='CARGA_GERAL',
        criado_por='tester@carvia',
        peso=100.0,
        data_expedicao=date(2026, 7, 1),
    )
    assert erro is None, erro
    if valor_final is not None:
        cot.valor_final_aprovado = Decimal(str(valor_final))
    db.session.flush()
    return cot


def _nf_com_cte(db, numero_nf, cte_valor):
    """Cria CarviaNf ATIVA + CarviaOperacao(cte_valor) vinculadas via CarviaOperacaoNf."""
    from app.carvia.models import CarviaNf, CarviaOperacao, CarviaOperacaoNf
    nf = CarviaNf(
        numero_nf=numero_nf, cnpj_emitente='11111111000111', nome_emitente='E',
        cnpj_destinatario='22222222000122', nome_destinatario='D',
        data_emissao=date(2026, 1, 5), valor_total=Decimal('500'),
        status='ATIVA', tipo_fonte='MANUAL', criado_por='test',
    )
    db.session.add(nf)
    db.session.flush()
    op = CarviaOperacao(
        cte_numero=f'CTe-{numero_nf}', cte_valor=Decimal(str(cte_valor)),
        cte_data_emissao=date(2026, 1, 5),
        cnpj_cliente='22222222000122', nome_cliente='D',
        uf_origem='SP', cidade_origem='SAO PAULO',
        uf_destino='RJ', cidade_destino='RIO DE JANEIRO',
        status='RASCUNHO', tipo_entrada='IMPORTADO', criado_por='test',
    )
    db.session.add(op)
    db.session.flush()
    db.session.add(CarviaOperacaoNf(operacao_id=op.id, nf_id=nf.id))
    db.session.flush()
    return nf, op


def _vincular_nf_na_cotacao(db, cotacao, numero_nf):
    """Cria pedido + item com numero_nf, espelhando o que o wizard faz."""
    from app.carvia.models import CarviaPedido, CarviaPedidoItem
    ped = CarviaPedido(
        numero_pedido=CarviaPedido.gerar_numero_pedido(cotacao.id),
        cotacao_id=cotacao.id, filial='SP', tipo_separacao='ESTOQUE',
        criado_por='test',
    )
    db.session.add(ped)
    db.session.flush()
    db.session.add(CarviaPedidoItem(
        pedido_id=ped.id, descricao='Produto', quantidade=1,
        valor_total=Decimal('500'), numero_nf=numero_nf,
    ))
    db.session.flush()
    return ped


# ==================== Demanda 3: pular aprovacao do cliente ====================

def test_marcar_enviado_vai_direto_para_aprovado(db):
    from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service
    cot = _cotacao_minima(db, valor_final=1000)

    ok, erro = CotacaoV2Service.marcar_enviado(cot.id, 'tester@carvia')

    assert ok, erro
    assert cot.status == 'APROVADO'
    assert cot.aprovado_por == 'tester@carvia'
    assert cot.aprovado_em is not None


def test_marcar_enviado_sem_valor_bloqueia(db):
    from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service
    cot = _cotacao_minima(db, valor_final=None)

    ok, erro = CotacaoV2Service.marcar_enviado(cot.id, 'tester@carvia')

    assert not ok
    assert 'valor' in (erro or '').lower()
    assert cot.status == 'RASCUNHO'


# ==================== Demanda 2: aproveitar CTe automaticamente ====================

def test_aproveitar_cte_usa_soma_dos_ctes(db):
    from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service
    cot = _cotacao_minima(db)
    _nf_com_cte(db, '90001', 1200.0)
    _vincular_nf_na_cotacao(db, cot, '90001')

    aproveitou, total = CotacaoV2Service.aproveitar_cte_se_houver(cot.id)

    assert aproveitou is True
    assert float(total) == 1200.0
    assert float(cot.valor_final_aprovado) == 1200.0
    assert float(cot.valor_tabela) == 1200.0
    assert cot.criacao_tardia is True


def test_aproveitar_cte_soma_operacoes_distintas(db):
    from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service
    cot = _cotacao_minima(db)
    _nf_com_cte(db, '90010', 300.0)
    _nf_com_cte(db, '90011', 700.0)
    _vincular_nf_na_cotacao(db, cot, '90010')
    _vincular_nf_na_cotacao(db, cot, '90011')

    aproveitou, total = CotacaoV2Service.aproveitar_cte_se_houver(cot.id)

    assert aproveitou is True
    assert float(total) == 1000.0


def test_aproveitar_cte_nao_duplica_operacao_compartilhada(db):
    """1 CTe vinculado a 2 NFs da cotacao deve ser contado UMA vez."""
    from app.carvia.models import CarviaNf, CarviaOperacao, CarviaOperacaoNf
    from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service
    cot = _cotacao_minima(db)
    nfs = []
    for num in ('90030', '90031'):
        nf = CarviaNf(
            numero_nf=num, cnpj_emitente='11111111000111', nome_emitente='E',
            cnpj_destinatario='22222222000122', nome_destinatario='D',
            data_emissao=date(2026, 1, 5), valor_total=Decimal('500'),
            status='ATIVA', tipo_fonte='MANUAL', criado_por='test',
        )
        db.session.add(nf)
        db.session.flush()
        nfs.append(nf)
    op = CarviaOperacao(
        cte_numero='CTe-SHARED', cte_valor=Decimal('1000'),
        cte_data_emissao=date(2026, 1, 5),
        cnpj_cliente='22222222000122', nome_cliente='D',
        uf_origem='SP', cidade_origem='SAO PAULO',
        uf_destino='RJ', cidade_destino='RIO DE JANEIRO',
        status='RASCUNHO', tipo_entrada='IMPORTADO', criado_por='test',
    )
    db.session.add(op)
    db.session.flush()
    db.session.add(CarviaOperacaoNf(operacao_id=op.id, nf_id=nfs[0].id))
    db.session.add(CarviaOperacaoNf(operacao_id=op.id, nf_id=nfs[1].id))
    db.session.flush()
    _vincular_nf_na_cotacao(db, cot, '90030')
    _vincular_nf_na_cotacao(db, cot, '90031')

    aproveitou, total = CotacaoV2Service.aproveitar_cte_se_houver(cot.id)

    assert aproveitou is True
    assert float(total) == 1000.0  # 1 vez, nao 2000


def test_aproveitar_cte_sem_cte_retorna_false(db):
    from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service
    cot = _cotacao_minima(db)
    # NF sem operacao/CTe
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf='90020', cnpj_emitente='11111111000111', nome_emitente='E',
        cnpj_destinatario='22222222000122', nome_destinatario='D',
        data_emissao=date(2026, 1, 5), valor_total=Decimal('500'),
        status='ATIVA', tipo_fonte='MANUAL', criado_por='test',
    )
    db.session.add(nf)
    db.session.flush()
    _vincular_nf_na_cotacao(db, cot, '90020')

    aproveitou, total = CotacaoV2Service.aproveitar_cte_se_houver(cot.id)

    assert aproveitou is False
    assert float(total) == 0.0
    assert cot.criacao_tardia is False


# ==================== Demanda 1: tipo de carga opcional ====================

def test_criar_cotacao_sem_tipo_carga_grava_none(db, client):
    from app.carvia.models import CarviaCotacao
    cli, origem, destino = _cliente_enderecos(db)
    db.session.commit()

    with patch('flask_login.utils._get_user', return_value=_user()):
        resp = client.post('/carvia/cotacoes/nova', data={
            'cliente_id': cli.id,
            'tipo_material': 'CARGA_GERAL',
            'endereco_origem_id': origem.id,
            'endereco_destino_id': destino.id,
            'peso': '100',
            'data_expedicao': '2026-07-01',
            # tipo_carga AUSENTE de proposito
        })

    assert resp.status_code in (302, 200)
    cot = CarviaCotacao.query.filter_by(cliente_id=cli.id).order_by(
        CarviaCotacao.id.desc()
    ).first()
    assert cot is not None
    assert cot.tipo_carga is None


# ==================== Smoke de render (templates editados) ====================

def test_render_criar_e_detalhe(db, client):
    from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service
    cot = _cotacao_minima(db, valor_final=1000)
    ok, erro = CotacaoV2Service.marcar_enviado(cot.id, 'tester@carvia')
    assert ok, erro
    db.session.commit()

    with patch('flask_login.utils._get_user', return_value=_user()):
        assert client.get('/carvia/cotacoes/nova').status_code == 200
        # detalhe de cotacao ja APROVADA (estado novo do fluxo) renderiza
        assert client.get(f'/carvia/cotacoes/{cot.id}').status_code == 200
