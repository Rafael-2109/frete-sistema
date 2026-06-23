"""CCe da entrega CarVia no monitoramento — C5 do plano."""
import io
from app import db as _db
from werkzeug.datastructures import FileStorage


def _nf_com_cce(numero):
    from app.carvia.models.documentos import CarviaNf
    from app.carvia.services.documentos.carta_correcao_service import CarviaCartaCorrecaoService
    nf = CarviaNf(numero_nf=numero, cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='2', nome_destinatario='D',
                  cidade_destinatario='C', uf_destinatario='SP',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf)
    _db.session.flush()
    CarviaCartaCorrecaoService.criar(
        'nf', nf.id,
        FileStorage(stream=io.BytesIO(b'%PDF-1.4 x'), filename='c.pdf',
                    content_type='application/pdf'), 'u')
    return nf


def test_resolver_cces_da_entrega_carvia(db):
    from app.monitoramento import routes as mon_routes
    nf = _nf_com_cce('9100')
    _db.session.commit()

    class _E:
        numero_nf = '9100'
        origem = 'CARVIA'
    pares, nf_id = mon_routes._cces_da_entrega(_E())
    assert len(pares) == 1
    assert nf_id == nf.id


def test_resolver_cces_entrega_nacom_vazio(db):
    from app.monitoramento import routes as mon_routes

    class _E:
        numero_nf = '9100'
        origem = 'NACOM'
    pares, nf_id = mon_routes._cces_da_entrega(_E())
    assert pares == [] and nf_id is None
