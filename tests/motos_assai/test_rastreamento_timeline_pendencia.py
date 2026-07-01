import uuid
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, PENDENCIA_CATEGORIA_AVARIA, PENDENCIA_ORIGEM_GALPAO,
)
from app.motos_assai.services.pendencia_service import abrir_pendencia
from app.motos_assai.services.rastreamento_chassi_service import rastrear_chassi


def test_rastreamento_inclui_fichas_pendencia(app, admin_user):
    with app.app_context():
        chassi = f'TSTTL{uuid.uuid4().hex[:6].upper()}'
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
        db.session.flush()
        abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_AVARIA,
                        origem=PENDENCIA_ORIGEM_GALPAO, descricao='avaria teste',
                        operador_id=admin_user.id)
        db.session.commit()
        r = rastrear_chassi(chassi)
        assert 'fichas_pendencia' in r and len(r['fichas_pendencia']) == 1
        assert r['fichas_pendencia'][0]['categoria'] == PENDENCIA_CATEGORIA_AVARIA
        assert 'movimentos_peca' in r
        assert r['contadores']['fichas_pendencia'] == 1
