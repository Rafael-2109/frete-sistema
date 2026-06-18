"""Testes do Portal do Cliente CarVia (stream 5) — FOCO EM SEGURANCA (isolamento de escopo).

Cobre: registro/aprovacao/autenticacao, os 2 modos de escopo (8A CNPJ direto, 8B cliente comercial),
o INVARIANTE DE SEGURANCA (um cliente so ve NFs do seu CNPJ, nunca de outro) e o pipeline de status.
"""
from unittest.mock import patch, MagicMock

import pytest

from app.carvia.services.documentos.portal_auth_service import CarviaPortalAuthService, PortalAuthError
from app.carvia.services.documentos.portal_status_service import CarviaPortalStatusService


def _nf(db, numero, cnpj_dest):
    from app.carvia.models.documentos import CarviaNf
    nf = CarviaNf(numero_nf=numero, cnpj_emitente='12345678000199', nome_emitente='EMIT',
                  cnpj_destinatario=cnpj_dest, nome_destinatario='CLIENTE', tipo_fonte='MANUAL',
                  status='ATIVA', criado_por='test@bot')
    db.session.add(nf); db.session.flush()
    return nf


# ----------------------------------------------------------- auth basico
def test_registro_e_aprovacao(db):
    u = CarviaPortalAuthService.registrar(nome='Cliente X', email='X@Mail.com', senha='segredo1')
    assert u.status == 'PENDENTE'
    assert u.email == 'x@mail.com'  # normalizado lower
    # email duplicado bloqueia
    with pytest.raises(PortalAuthError):
        CarviaPortalAuthService.registrar(nome='Outro', email='x@mail.com', senha='segredo2')
    # PENDENTE nao loga
    user, motivo = CarviaPortalAuthService.autenticar('x@mail.com', 'segredo1')
    assert user is None and 'aprovacao' in motivo.lower()
    # aprova com escopo CNPJ direto
    CarviaPortalAuthService.aprovar(u, operador='op@carvia', tipo_escopo='CNPJ_DIRETO',
                                    cnpjs=['11.222.333/0001-44'])
    assert u.status == 'ATIVO'
    assert u.cnpjs_permitidos() == {'11222333000144'}
    # agora loga
    user, motivo = CarviaPortalAuthService.autenticar('x@mail.com', 'segredo1')
    assert user is not None and motivo is None
    # senha errada nao loga
    user, _ = CarviaPortalAuthService.autenticar('x@mail.com', 'errada')
    assert user is None


def test_aprovar_escopo_vazio_bloqueia(db):
    u = CarviaPortalAuthService.registrar(nome='Y', email='y@mail.com', senha='segredo1')
    with pytest.raises(PortalAuthError):
        CarviaPortalAuthService.aprovar(u, operador='op', tipo_escopo='CNPJ_DIRETO', cnpjs=[])


def test_escopo_cliente_comercial(db):
    from app.carvia.models.clientes import CarviaCliente, CarviaClienteEndereco
    cli = CarviaCliente(nome_comercial='Grupo Z', ativo=True, criado_por='test@bot')
    db.session.add(cli); db.session.flush()
    db.session.add(CarviaClienteEndereco(cliente_id=cli.id, cnpj='55666777000188', tipo='DESTINO', ativo=True, criado_por='test@bot'))
    db.session.add(CarviaClienteEndereco(cliente_id=cli.id, cnpj='55666777000269', tipo='DESTINO', ativo=True, criado_por='test@bot'))
    db.session.flush()
    u = CarviaPortalAuthService.registrar(nome='Vend', email='v@mail.com', senha='segredo1')
    CarviaPortalAuthService.aprovar(u, operador='op', tipo_escopo='CLIENTE_COMERCIAL',
                                    cliente_comercial_id=cli.id)
    assert u.cnpjs_permitidos() == {'55666777000188', '55666777000269'}


# ----------------------------------------------- INVARIANTE DE SEGURANCA
def test_isolamento_de_escopo(db):
    """Cliente A (CNPJ AAA) NUNCA enxerga NF do cliente B (CNPJ BBB)."""
    nf_a = _nf(db, 'NFA', '11111111000111')
    nf_b = _nf(db, 'NFB', '22222222000222')
    a = CarviaPortalAuthService.registrar(nome='A', email='a@mail.com', senha='segredo1')
    CarviaPortalAuthService.aprovar(a, operador='op', tipo_escopo='CNPJ_DIRETO', cnpjs=['11111111000111'])

    vistos = CarviaPortalStatusService.listar_nfs(a)
    numeros = {v['nf'].numero_nf for v in vistos}
    assert 'NFA' in numeros
    assert 'NFB' not in numeros  # NAO ve a NF do outro CNPJ

    # acesso direto a NF fora do escopo retorna None (nao vaza por URL)
    assert CarviaPortalStatusService.get_nf_escopada(a, 'NFB') is None
    assert CarviaPortalStatusService.get_nf_escopada(a, 'NFA') is not None


def test_usuario_sem_escopo_nao_ve_nada(db):
    _nf(db, 'NFX', '33333333000333')
    u = CarviaPortalAuthService.registrar(nome='SemEscopo', email='s@mail.com', senha='segredo1')
    # nao aprovado / sem CNPJ -> nada
    assert CarviaPortalStatusService.listar_nfs(u) == []


# --------------------------------------------------- pipeline de status
def test_pipeline_status(db):
    from app.carvia.services.documentos.coleta_service import CarviaColetaService
    from app.carvia.services.documentos.coleta_recebimento_service import CarviaColetaRecebimentoService
    from app.carvia.models.documentos import CarviaNfVeiculo
    from app.monitoramento.models import EntregaMonitorada

    nf = _nf(db, 'NFP', '44444444000444')
    db.session.add(CarviaNfVeiculo(nf_id=nf.id, chassi='CHP1', modelo='POP')); db.session.flush()

    # ainda nada -> Aguardando
    st = CarviaPortalStatusService.status_nf(nf)
    assert st['atual_key'] is None

    # coleta + vincula + coletada -> COLETADO
    coleta = CarviaColetaService.criar_coleta(valor_coleta=10, local_cd='TENENTE_MARQUES', usuario='op')
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='NFP')
    CarviaColetaService.vincular_nf(linha, nf.id)
    CarviaColetaService.marcar_coletada(coleta, usuario='op')
    assert CarviaPortalStatusService.status_nf(nf)['atual_key'] == 'COLETADO'

    # confere o chassi -> RECEBIDO_MATRIZ
    CarviaColetaRecebimentoService.conferir_chassi(coleta, 'CHP1', usuario='conf')
    assert CarviaPortalStatusService.status_nf(nf)['atual_key'] == 'RECEBIDO_MATRIZ'

    # EntregaMonitorada CARVIA com data_embarque + chegada_filial + entregue
    em = EntregaMonitorada(numero_nf='NFP', origem='CARVIA', cliente='CLIENTE',
                           data_embarque=None, entregue=False)
    db.session.add(em); db.session.flush()
    import datetime
    em.data_embarque = datetime.date(2026, 6, 1)
    assert CarviaPortalStatusService.status_nf(nf)['atual_key'] == 'EMBARCADO'
    em.chegada_filial = True
    assert CarviaPortalStatusService.status_nf(nf)['atual_key'] == 'RECEBIDO_FILIAL'
    em.entregue = True
    assert CarviaPortalStatusService.status_nf(nf)['atual_key'] == 'ENTREGUE'


def test_dados_detalhe_agrupa_motos_e_lista_4_documentos(db):
    """Enriquecimento: motos agrupadas por modelo (expansiveis) + os 4 documentos SEMPRE
    listados (com flag disponivel) — independente de haver arquivo."""
    from app.carvia.models.documentos import CarviaNfVeiculo
    nf = _nf(db, 'NFD', '66666666000166')
    for ch in ('C1', 'C2'):
        db.session.add(CarviaNfVeiculo(nf_id=nf.id, chassi=ch, modelo='POP 110'))
    db.session.add(CarviaNfVeiculo(nf_id=nf.id, chassi='C3', modelo='BIZ 125'))
    db.session.flush()

    dados = CarviaPortalStatusService.dados_detalhe(nf)
    assert dados['qtd_motos'] == 3
    grupos = {g['modelo']: g for g in dados['motos_por_modelo']}
    assert grupos['POP 110']['qtd'] == 2
    assert set(grupos['POP 110']['chassis']) == {'C1', 'C2'}
    assert grupos['BIZ 125']['qtd'] == 1
    # os 4 documentos sempre presentes; sem arquivo cadastrado -> todos indisponiveis
    tipos = {a['tipo'] for a in dados['arquivos']}
    assert tipos == {'nf_pdf', 'dacte', 'fatura', 'canhoto'}
    assert all(a['disponivel'] is False for a in dados['arquivos'])


def _modelo(db, nome):
    """get-or-create: `nome` e UNIQUE e o catalogo real ja pode te-lo cadastrado."""
    from app.carvia.models.config_moto import CarviaModeloMoto
    m = CarviaModeloMoto.query.filter_by(nome=nome).first()
    if m:
        return m
    m = CarviaModeloMoto(nome=nome, comprimento=1.8, largura=0.7, altura=1.1,
                         peso_medio=90, ativo=True, criado_por='test@bot')
    db.session.add(m); db.session.flush()
    return m


def _item(db, nf, modelo, qtd):
    from app.carvia.models.documentos import CarviaNfItem
    it = CarviaNfItem(nf_id=nf.id, descricao=modelo.nome, quantidade=qtd,
                      modelo_moto_id=modelo.id)
    db.session.add(it); db.session.flush()
    return it


def test_motos_sem_chassi_contam_pelo_item(db):
    """NF por PDF_DANFE (sem chassi) — a moto so existe no item. Deve contar TODAS
    (nao 0, como antes) e exibir chassi vazio, agrupadas pelo modelo do item."""
    nf = _nf(db, 'NFSC', '88888888000188')
    _item(db, nf, _modelo(db, 'X12'), 3)

    dados = CarviaPortalStatusService.dados_detalhe(nf)
    assert dados['qtd_motos'] == 3  # antes: 0 (so contava chassi)
    grp = {g['modelo']: g for g in dados['motos_por_modelo']}
    assert grp['X12']['qtd'] == 3
    assert grp['X12']['chassis'] == ['', '', '']  # 3 motos, chassi vazio
    # a listagem usa a MESMA fonte de contagem
    assert CarviaPortalStatusService._qtd_motos_por_nf([nf.id])[nf.id] == 3


def test_motos_chassi_parcial_completa_com_vazio(db):
    """NF com chassi PARCIAL (menos chassis lidos que motos no DANFE): exibe os
    chassis reais + as faltantes como vazio; qtd = total real, nao subconta."""
    from app.carvia.models.documentos import CarviaNfVeiculo
    nf = _nf(db, 'NFPC', '99999999000199')
    _item(db, nf, _modelo(db, 'X11 MINI'), 5)  # DANFE: 5 motos
    for ch in ('A1', 'A2', 'A3', 'A4'):        # so 4 chassis lidos
        db.session.add(CarviaNfVeiculo(nf_id=nf.id, chassi=ch,
                                       modelo='MINI SCOOTER ELETR. X11 MINI'))
    db.session.flush()

    dados = CarviaPortalStatusService.dados_detalhe(nf)
    assert dados['qtd_motos'] == 5  # max(4 chassi, 5 item) — NAO 4
    grupos = {g['modelo']: g for g in dados['motos_por_modelo']}
    assert grupos['MINI SCOOTER ELETR. X11 MINI']['qtd'] == 4
    assert grupos['Sem chassi informado']['qtd'] == 1
    assert grupos['Sem chassi informado']['chassis'] == ['']


def test_motos_chassi_maior_que_item_usa_chassi(db):
    """Item subconta (1) vs 3 chassis fisicos: a contagem fisica manda; sem vazios."""
    from app.carvia.models.documentos import CarviaNfVeiculo
    nf = _nf(db, 'NFCM', '10101010000110')
    _item(db, nf, _modelo(db, 'BIG TRI'), 1)
    for ch in ('B1', 'B2', 'B3'):
        db.session.add(CarviaNfVeiculo(nf_id=nf.id, chassi=ch,
                                       modelo='TRI MOTO ELETRICA BIG-TRI'))
    db.session.flush()

    dados = CarviaPortalStatusService.dados_detalhe(nf)
    assert dados['qtd_motos'] == 3  # max(3 chassi, 1 item)
    grupos = {g['modelo']: g for g in dados['motos_por_modelo']}
    assert grupos['TRI MOTO ELETRICA BIG-TRI']['qtd'] == 3
    assert 'Sem chassi informado' not in grupos  # sem deficit


# ------------------------------------------------------------ render smoke
def _admin():
    u = MagicMock(); u.is_authenticated = True; u.sistema_carvia = True
    u.perfil = 'administrador'; u.email = 'op@carvia'
    return u


def test_render_portal_publico(db, client):
    # paginas publicas do portal (usuario externo anonimo) renderizam
    assert client.get('/portal-cliente/login').status_code == 200
    assert client.get('/portal-cliente/registrar').status_code == 200
    # area logada sem sessao -> redireciona para login
    assert client.get('/portal-cliente/').status_code in (301, 302)


def test_registrar_com_grupo_empresa(db):
    u = CarviaPortalAuthService.registrar(nome='Cli', email='g@mail.com', senha='segredo1',
                                          grupo_empresa='Grupo Atacado Norte')
    assert u.grupo_empresa == 'Grupo Atacado Norte'


def test_render_admin_portal(db, client):
    with patch('flask_login.utils._get_user', return_value=_admin()):
        assert client.get('/carvia/portal-usuarios').status_code == 200


def test_ver_portal_interno_renderiza(db, client):
    """Usuario CarVia (interno) ve a MESMA tela do cliente (read-only), escopada ao usuario."""
    nf = _nf(db, 'NFI', '77777777000177')
    u = CarviaPortalAuthService.registrar(nome='ClienteVis', email='vis@mail.com', senha='segredo1',
                                          grupo_empresa='Grupo Vis')
    CarviaPortalAuthService.aprovar(u, operador='op', tipo_escopo='CNPJ_DIRETO', cnpjs=['77777777000177'])
    db.session.commit()
    with patch('flask_login.utils._get_user', return_value=_admin()):
        r = client.get(f'/carvia/portal-usuarios/{u.id}/ver')
        assert r.status_code == 200
        assert b'NFI' in r.data  # ve a NF do escopo do cliente
        r2 = client.get(f'/carvia/portal-usuarios/{u.id}/nf/NFI')
        assert r2.status_code == 200
