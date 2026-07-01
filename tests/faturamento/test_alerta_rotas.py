from app import db
from app.faturamento.models import AlertaFaturamentoCnpj


def test_index_200(client):
    assert client.get('/faturamento/alertas/').status_code == 200


def test_novo_normaliza_cnpj(client, db):
    resp = client.post('/faturamento/alertas/novo', data={
        'cnpj': '12.345.678/0001-99', 'nome_cliente': 'ACME', 'emails': 'x@a.com'})
    assert resp.status_code in (302, 200)
    reg = AlertaFaturamentoCnpj.query.filter_by(cnpj='12345678000199').first()
    assert reg is not None and reg.nome_cliente == 'ACME'


def test_novo_sem_email_rejeita(client, db):
    client.post('/faturamento/alertas/novo', data={'cnpj': '11111111000111', 'emails': ''})
    assert AlertaFaturamentoCnpj.query.filter_by(cnpj='11111111000111').first() is None


def test_editar_e_remover(client, db):
    reg = AlertaFaturamentoCnpj(cnpj='22222222000122', emails='a@a.com', ativo=True)
    db.session.add(reg); db.session.commit(); rid = reg.id
    client.post(f'/faturamento/alertas/{rid}/editar', data={'emails': 'b@b.com', 'nome_cliente': 'X'})
    assert db.session.get(AlertaFaturamentoCnpj, rid).emails == 'b@b.com'
    assert db.session.get(AlertaFaturamentoCnpj, rid).ativo is False  # checkbox ausente = off
    client.post(f'/faturamento/alertas/{rid}/remover')
    assert db.session.get(AlertaFaturamentoCnpj, rid) is None


def test_novo_prefill_emails_padrao(client):
    """A tela pré-preenche os e-mails padrão no formulário de novo CNPJ."""
    html = client.get('/faturamento/alertas/').get_data(as_text=True)
    assert 'conservascampobelo.com.br' in html
