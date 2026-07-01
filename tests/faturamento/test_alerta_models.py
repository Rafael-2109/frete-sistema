import pytest
from app import db
from app.faturamento.models import (
    AlertaFaturamentoCnpj,
    AlertaFaturamentoConfig,
    AlertaFaturamentoEnviado,
)


def test_lista_emails_separadores(db):
    reg = AlertaFaturamentoCnpj(cnpj='12345678000199', emails='a@x.com; b@x.com , c@x.com')
    assert reg.lista_emails() == ['a@x.com', 'b@x.com', 'c@x.com']


def test_get_config_cria_linha_unica(db):
    cfg = AlertaFaturamentoConfig.get_config()
    assert cfg.id is not None
    assert cfg.email_ativo is True
    assert cfg.teams_ativo is False
    # segunda chamada não cria outra
    cfg2 = AlertaFaturamentoConfig.get_config()
    assert cfg2.id == cfg.id


def test_unique_nf_canal(db):
    db.session.add(AlertaFaturamentoEnviado(numero_nf='NF1', canal='email', status='ok'))
    db.session.commit()
    db.session.add(AlertaFaturamentoEnviado(numero_nf='NF1', canal='email', status='ok'))
    with pytest.raises(Exception):
        db.session.commit()
    db.session.rollback()
