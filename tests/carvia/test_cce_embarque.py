"""CCe das NFs CarVia no PDF do embarque — C4 do plano."""
import io
from app import db as _db
from werkzeug.datastructures import FileStorage


def _nf(numero):
    from app.carvia.models.documentos import CarviaNf
    nf = CarviaNf(numero_nf=numero, cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='2', nome_destinatario='D',
                  cidade_destinatario='C', uf_destinatario='SP',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf)
    _db.session.flush()
    return nf


def test_coletar_cces_do_embarque_por_nf(db, monkeypatch):
    from app.embarques import routes as emb_routes
    from app.carvia.services.documentos.carta_correcao_service import CarviaCartaCorrecaoService
    nf = _nf('9001')
    CarviaCartaCorrecaoService.criar(
        'nf', nf.id,
        FileStorage(stream=io.BytesIO(b'%PDF-1.4 x'), filename='c.pdf',
                    content_type='application/pdf'), 'u')
    _db.session.commit()
    # evita render real (PDF fake): mocka no namespace do cce_render (lazy import resolve la)
    monkeypatch.setattr(
        'app.carvia.services.documentos.cce_render.render_cces_para_impressao',
        lambda cces: [{'carta_id': c.id, 'descricao': None, 'paginas': ['AAA']}
                      for c, _ in cces])
    out = emb_routes._coletar_cces_embarque(['9001'])
    assert len(out) == 1 and out[0]['paginas'] == ['AAA']


def test_coletar_cces_vazio(db):
    from app.embarques import routes as emb_routes
    assert emb_routes._coletar_cces_embarque([]) == []
