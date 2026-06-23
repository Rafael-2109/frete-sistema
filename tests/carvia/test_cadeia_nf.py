"""SOT compartilhado do fecho da cadeia documental CarVia (resolver_cadeia_nf).

B1 do plano: extrai _entidades_relacionadas do comprovante para um modulo unico.
Regressao: a saida deve ser identica a do metodo antigo do comprovante.
"""
from app import db as _db
from app.carvia.services.documentos._cadeia_nf import resolver_cadeia_nf
from app.carvia.services.documentos.comprovante_service import CarviaComprovanteService


def _nf(numero):
    from app.carvia.models.documentos import CarviaNf
    nf = CarviaNf(numero_nf=numero, cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='2', nome_destinatario='D',
                  cidade_destinatario='C', uf_destinatario='SP',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf)
    _db.session.flush()
    return nf


def test_cadeia_de_nf_inclui_ela_mesma(db):
    nf = _nf('700')
    fecho = resolver_cadeia_nf('nf', nf.id)
    assert ('nf', nf.id) in fecho


def test_extracao_identica_ao_metodo_antigo(db):
    nf = _nf('701')
    assert (resolver_cadeia_nf('nf', nf.id)
            == CarviaComprovanteService._entidades_relacionadas('nf', nf.id))
