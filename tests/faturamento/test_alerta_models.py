import pytest
from app import db
from app.faturamento.models import (
    AlertaFaturamentoCnpj,
    AlertaFaturamentoEnviado,
)


def test_lista_emails_separadores(db):
    reg = AlertaFaturamentoCnpj(cnpj='12345678000199', emails='a@x.com; b@x.com , c@x.com')
    assert reg.lista_emails() == ['a@x.com', 'b@x.com', 'c@x.com']


def test_unique_nf_canal(db):
    db.session.add(AlertaFaturamentoEnviado(numero_nf='NF1', canal='email', status='ok'))
    db.session.commit()
    db.session.add(AlertaFaturamentoEnviado(numero_nf='NF1', canal='email', status='ok'))
    with pytest.raises(Exception):
        db.session.commit()
    db.session.rollback()
