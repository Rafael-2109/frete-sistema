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


def test_render_admin_portal(db, client):
    with patch('flask_login.utils._get_user', return_value=_admin()):
        assert client.get('/carvia/portal-usuarios').status_code == 200
