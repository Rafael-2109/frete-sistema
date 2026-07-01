from datetime import date
from app import db
from app.faturamento.models import (
    RelatorioFaturamentoImportado,
    AlertaFaturamentoCnpj,
    AlertaFaturamentoEnviado,
)
import app.faturamento.services.alerta_faturamento_service as svc


def _cab(nf, cnpj='12345678000199', valor=100.0, mun='São Paulo', uf='SP'):
    return RelatorioFaturamentoImportado(
        numero_nf=nf, cnpj_cliente=cnpj, nome_cliente='Cliente X',
        valor_total=valor, data_fatura=date(2026, 7, 1), municipio=mun, estado=uf, ativo=True,
    )


# ── Helpers puros ────────────────────────────────────────────────────────

def test_normalizar_cnpj():
    assert svc.normalizar_cnpj('12.345.678/0001-99') == '12345678000199'
    assert svc.normalizar_cnpj(None) == ''


def test_agrupar_por_cnpj_ignora_mascara():
    a = _cab('NF1', cnpj='12.345.678/0001-99')
    b = _cab('NF2', cnpj='12345678000199')
    grupos = svc.agrupar_por_cnpj([a, b])
    assert set(grupos.keys()) == {'12345678000199'}
    assert len(grupos['12345678000199']) == 2


def test_montar_linhas_total(db):
    linhas, total = svc.montar_linhas([_cab('NF1', valor=100.0), _cab('NF2', valor=50.5)])
    assert total == 'R$ 150,50'
    assert linhas[0]['numero_nf'] == 'NF1'
    assert linhas[0]['cidade'] == 'São Paulo/SP'
    assert linhas[0]['valor'] == 'R$ 100,00'


def test_filtrar_nao_enviadas_exclui_ok(db):
    db.session.add(_cab('NF1')); db.session.add(_cab('NF2'))
    db.session.add(AlertaFaturamentoEnviado(numero_nf='NF1', canal='email', status='ok'))
    db.session.commit()
    cabs = RelatorioFaturamentoImportado.query.filter(
        RelatorioFaturamentoImportado.numero_nf.in_(['NF1', 'NF2'])).all()
    pend = svc.filtrar_nao_enviadas(cabs, 'email')
    assert {c.numero_nf for c in pend} == {'NF2'}


def test_filtrar_nao_enviadas_erro_reenvia(db):
    db.session.add(_cab('NF3'))
    db.session.add(AlertaFaturamentoEnviado(numero_nf='NF3', canal='email', status='erro'))
    db.session.commit()
    cabs = RelatorioFaturamentoImportado.query.filter_by(numero_nf='NF3').all()
    pend = svc.filtrar_nao_enviadas(cabs, 'email')
    assert {c.numero_nf for c in pend} == {'NF3'}  # erro não bloqueia retry


def test_emails_padrao_tem_quatro():
    assert svc.EMAILS_PADRAO.count('@') == 4
    assert svc.EMAILS_PADRAO == svc.EMAILS_PADRAO.lower()  # sempre minúsculo


# ── Envio + orquestração (só e-mail) ─────────────────────────────────────

class _FakeSender:
    def __init__(self): self.calls = []
    def send(self, **kw):
        self.calls.append(kw)
        return {'success': True, 'message_id': 'x', 'error': None}


def _cadastrar(db, cnpj='12345678000199', emails='a@x.com; b@x.com', ativo=True):
    reg = AlertaFaturamentoCnpj(cnpj=svc.normalizar_cnpj(cnpj), emails=emails,
                                nome_cliente='Cliente X', ativo=ativo)
    db.session.add(reg); db.session.commit()
    return reg


def test_processar_envia_email_agrupado(db, monkeypatch):
    _cadastrar(db)
    db.session.add(_cab('NF1', valor=100.0)); db.session.add(_cab('NF2', valor=50.0))
    db.session.commit()
    fake = _FakeSender()
    monkeypatch.setattr(svc, 'email_sender', fake)
    monkeypatch.setattr(svc.EmailConfig, 'is_configured', classmethod(lambda cls: True))

    resumo = svc.processar_alertas_faturamento(['NF1', 'NF2'])

    assert resumo['emails_ok'] == 1           # 1 e-mail agrupado
    assert len(fake.calls) == 1
    assert fake.calls[0]['to'] == 'a@x.com'
    assert fake.calls[0]['cc'] == ['b@x.com']  # demais em cópia
    enviados = AlertaFaturamentoEnviado.query.filter_by(canal='email', status='ok').count()
    assert enviados == 2                        # 1 registro por NF


def test_processar_nao_reenvia(db, monkeypatch):
    _cadastrar(db)
    db.session.add(_cab('NF1', valor=100.0)); db.session.commit()
    fake = _FakeSender()
    monkeypatch.setattr(svc, 'email_sender', fake)
    monkeypatch.setattr(svc.EmailConfig, 'is_configured', classmethod(lambda cls: True))

    svc.processar_alertas_faturamento(['NF1'])
    svc.processar_alertas_faturamento(['NF1'])   # 2ª rodada
    assert len(fake.calls) == 1                  # não reenviou


def test_processar_ignora_cnpj_nao_cadastrado(db, monkeypatch):
    db.session.add(_cab('NF9', cnpj='99999999000199')); db.session.commit()
    fake = _FakeSender(); monkeypatch.setattr(svc, 'email_sender', fake)
    monkeypatch.setattr(svc.EmailConfig, 'is_configured', classmethod(lambda cls: True))
    resumo = svc.processar_alertas_faturamento(['NF9'])
    assert resumo['cnpjs'] == 0 and len(fake.calls) == 0


def test_processar_nunca_levanta(db, monkeypatch):
    _cadastrar(db)
    db.session.add(_cab('NFX')); db.session.commit()
    monkeypatch.setattr(svc, 'agrupar_por_cnpj',
                        lambda c: (_ for _ in ()).throw(RuntimeError('boom')))
    resumo = svc.processar_alertas_faturamento(['NFX'])
    assert any('boom' in e for e in resumo['erros'])  # capturou, não levantou


def test_processar_vazio_noop(db):
    assert svc.processar_alertas_faturamento([]) == {'cnpjs': 0, 'emails_ok': 0, 'erros': []}
