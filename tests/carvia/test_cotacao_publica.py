"""Cotacao Rapida PUBLICA (tela sem login): modelo, service, rotas, rate-limit."""
from decimal import Decimal
from unittest.mock import MagicMock, patch


def test_modelo_persiste_e_le(db):
    from app.carvia.models import CarviaCotacaoRapidaPublica
    reg = CarviaCotacaoRapidaPublica(
        solicitante_nome='Fulano',
        uf_destino='RJ',
        cidade_destino='Rio de Janeiro',
        itens=[{'modelo_id': 1, 'quantidade': 2}],
        opcoes=[{'tabela_nome': 'T1', 'valor_total': 100.0}],
        valor_total_min=Decimal('100.00'),
        qtd_total_motos=2,
    )
    db.session.add(reg)
    db.session.commit()
    lido = CarviaCotacaoRapidaPublica.query.get(reg.id)
    assert lido.solicitante_nome == 'Fulano'
    assert lido.itens[0]['quantidade'] == 2
    assert lido.criado_em is not None


def _resultado_fake():
    return {
        'ok': True,
        'opcoes': [
            {'tabela_nome': 'T1', 'valor_total': 250.0, 'modelos': [], 'lead_time': 3},
            {'tabela_nome': 'T2', 'valor_total': 180.0, 'modelos': [], 'lead_time': 5},
        ],
        'itens': [
            {'modelo_id': 1, 'modelo_nome': 'POP', 'categoria_nome': 'A', 'quantidade': 2},
            {'modelo_id': 2, 'modelo_nome': 'JET', 'categoria_nome': 'B', 'quantidade': 1},
        ],
        'regiao': {'uf_destino': 'RJ', 'cidade_destino': 'Rio de Janeiro'},
    }


def test_registrar_cotacao_publica_deriva_campos(db):
    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    reg = CotacaoRapidaService().registrar_cotacao_publica(
        _resultado_fake(), solicitante_nome='  Maria  ', codigo_ibge='3304557',
        ip='1.2.3.4', user_agent='UA')
    db.session.commit()
    assert reg.id is not None
    assert reg.solicitante_nome == 'Maria'           # strip
    assert reg.uf_destino == 'RJ'
    assert reg.codigo_ibge == '3304557'
    assert float(reg.valor_total_min) == 180.0        # menor das opcoes
    assert reg.qtd_total_motos == 3                   # 2 + 1


def test_listar_cotacoes_publicas_ordem_e_limite(db):
    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    svc = CotacaoRapidaService()
    for nome in ('A', 'B', 'C'):
        svc.registrar_cotacao_publica(_resultado_fake(), solicitante_nome=nome)
    db.session.commit()
    lista = svc.listar_cotacoes_publicas(limit=2)
    assert len(lista) == 2
    assert lista[0]['solicitante_nome'] == 'C'        # mais recente primeiro
    assert lista[0]['destino'] == 'Rio de Janeiro/RJ'
    assert lista[0]['valor_total_min'] == 180.0


def test_rate_limit_bloqueia_apos_limite():
    from app.carvia.utils import rate_limit
    fake = MagicMock()
    fake.incr.side_effect = [1, 2, 3]  # 3a chamada excede limite=2
    with patch.object(rate_limit, 'redis_cache') as rc:
        rc.client = fake
        assert rate_limit.permitir('upload', '9.9.9.9', limite=2, janela_seg=3600) is True
        assert rate_limit.permitir('upload', '9.9.9.9', limite=2, janela_seg=3600) is True
        assert rate_limit.permitir('upload', '9.9.9.9', limite=2, janela_seg=3600) is False
    fake.expire.assert_called_once()  # expire so na 1a (incr==1)


def test_rate_limit_degrada_aberto_sem_redis():
    from app.carvia.utils import rate_limit
    with patch.object(rate_limit, 'redis_cache') as rc:
        rc.client = None
        assert rate_limit.permitir('upload', '9.9.9.9', limite=1, janela_seg=60) is True


def _user_carvia():
    u = MagicMock()
    u.is_authenticated = True
    u.sistema_carvia = True
    u.perfil = 'administrador'
    u.email = 'test@bot'
    return u


def test_cotacao_rapida_com_login_renderiza(db, client):
    with patch('flask_login.utils._get_user', return_value=_user_carvia()):
        assert client.get('/carvia/cotacao-rapida').status_code == 200


def test_form_login_usa_js_externo(db, client):
    with patch('flask_login.utils._get_user', return_value=_user_carvia()):
        html = client.get('/carvia/cotacao-rapida').get_data(as_text=True)
    assert 'js/carvia/cotacao_rapida.js' in html
    assert 'id="cr-app"' in html


def test_cotacao_publica_get_sem_login(db, client):
    # Sem patch de usuario: rota publica responde 200 mesmo anonimo.
    assert client.get('/cotacao').status_code == 200


def test_cotacao_publica_calcular_exige_nome(db, client):
    r = client.post('/cotacao/calcular', json={'itens': [{'modelo_id': 1, 'quantidade': 1}],
                                               'uf_destino': 'RJ'})
    assert r.status_code == 400
    assert r.get_json()['ok'] is False


def test_cotacao_publica_calcular_persiste(db, client):
    from app.carvia.models import CarviaCotacaoRapidaPublica
    antes = CarviaCotacaoRapidaPublica.query.count()
    with patch('app.carvia.services.pricing.cotacao_rapida_service.CotacaoRapidaService.cotar',
               return_value=_resultado_fake()):
        r = client.post('/cotacao/calcular', json={
            'itens': [{'modelo_id': 1, 'quantidade': 2}],
            'uf_destino': 'RJ', 'solicitante_nome': 'Joao'})
    assert r.status_code == 200
    assert CarviaCotacaoRapidaPublica.query.count() == antes + 1


def test_cotacao_publica_sem_opcoes_nao_persiste(db, client):
    from app.carvia.models import CarviaCotacaoRapidaPublica
    vazio = {'ok': False, 'opcoes': [], 'itens': [], 'regiao': {'uf_destino': 'RJ', 'cidade_destino': None}}
    antes = CarviaCotacaoRapidaPublica.query.count()
    with patch('app.carvia.services.pricing.cotacao_rapida_service.CotacaoRapidaService.cotar',
               return_value=vazio):
        r = client.post('/cotacao/calcular', json={
            'itens': [{'modelo_id': 1, 'quantidade': 2}],
            'uf_destino': 'RJ', 'solicitante_nome': 'Joao'})
    assert r.status_code == 200
    assert CarviaCotacaoRapidaPublica.query.count() == antes


def test_cotacao_publica_rate_limit_429(db, client):
    with patch('app.carvia.cotacao_publica.permitir', return_value=False):
        r = client.post('/cotacao/calcular', json={
            'itens': [{'modelo_id': 1, 'quantidade': 1}],
            'uf_destino': 'RJ', 'solicitante_nome': 'Joao'})
    assert r.status_code == 429


def test_cotacao_publica_cidades_sem_login(db, client):
    # endpoint publico de cidades (autocomplete) responde 200 sem sessao
    r = client.get('/cotacao/cidades/SP')
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_cotacao_publica_pdf_rate_limit_429(db, client):
    with patch('app.carvia.cotacao_publica.permitir', return_value=False):
        r = client.post('/cotacao/pdf', json={
            'itens': [{'modelo_id': 1, 'quantidade': 1}], 'uf_destino': 'RJ'})
    assert r.status_code == 429


def test_cotacao_publica_cep_rate_limit_429(db, client):
    with patch('app.carvia.cotacao_publica.permitir', return_value=False):
        r = client.get('/cotacao/cep/01001000')
    assert r.status_code == 429


def test_secao_cotacoes_publicas_na_tela_logada(db, client):
    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    CotacaoRapidaService().registrar_cotacao_publica(_resultado_fake(), solicitante_nome='ZéPúblico')
    db.session.commit()
    with patch('flask_login.utils._get_user', return_value=_user_carvia()):
        html = client.get('/carvia/cotacao-rapida').get_data(as_text=True)
    assert 'Cotações da tela pública' in html
    assert 'ZéPúblico' in html
