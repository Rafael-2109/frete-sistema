"""Service da Carta de Correção (CCe) CarVia — B3 do plano."""
import io
import pytest
from app import db as _db
from werkzeug.datastructures import FileStorage
from app.carvia.services.documentos.carta_correcao_service import CarviaCartaCorrecaoService


def _fake_pdf():
    return FileStorage(stream=io.BytesIO(b'%PDF-1.4 fake'),
                       filename='cce.pdf', content_type='application/pdf')


def _nf(numero='800'):
    from app.carvia.models.documentos import CarviaNf
    nf = CarviaNf(numero_nf=numero, cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='2', nome_destinatario='D',
                  cidade_destinatario='C', uf_destinatario='SP',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf)
    _db.session.flush()
    return nf


def test_criar_e_listar_cce_na_nf(db):
    nf = _nf()
    carta = CarviaCartaCorrecaoService.criar('nf', nf.id, _fake_pdf(), 'user@bot',
                                             descricao='corrige endereco')
    _db.session.commit()
    assert carta.id
    pares = CarviaCartaCorrecaoService.listar('nf', nf.id)
    assert len(pares) == 1
    assert pares[0][0].descricao == 'corrige endereco'


def test_entidade_invalida_levanta(db):
    with pytest.raises(ValueError):
        CarviaCartaCorrecaoService.criar('operacao', 1, _fake_pdf(), 'u')


def test_soft_delete(db):
    nf = _nf('801')
    carta = CarviaCartaCorrecaoService.criar('nf', nf.id, _fake_pdf(), 'u')
    _db.session.commit()
    CarviaCartaCorrecaoService.soft_delete(carta.id)
    _db.session.commit()
    assert CarviaCartaCorrecaoService.listar('nf', nf.id) == []
