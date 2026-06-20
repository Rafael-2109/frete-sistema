"""Testes do model AgenteUpload (manifesto S3 de uploads do chat) — IMP-2026-06-19-007."""
from datetime import timedelta

from app.utils.timezone import agora_brasil_naive


def test_agente_upload_persiste_e_consulta_por_user(db):
    from app.agente.models import AgenteUpload
    now = agora_brasil_naive()
    up = AgenteUpload(
        user_id=78, session_id='sess-abc', file_id='ab12cd34',
        original_name='nf_abril.xlsx', safe_name='ab12cd34_nf_abril.xlsx',
        s3_key='agente-uploads/78/ab12cd34_nf_abril.xlsx',
        file_type='excel', size_bytes=12345,
        criado_em=now, expira_em=now + timedelta(days=90), ativo=True,
    )
    db.session.add(up)
    db.session.flush()
    achados = AgenteUpload.query.filter_by(user_id=78, ativo=True).all()
    assert len(achados) == 1
    assert achados[0].s3_key == 'agente-uploads/78/ab12cd34_nf_abril.xlsx'


def test_agente_upload_unique_user_safe_name(db):
    import pytest
    from sqlalchemy.exc import IntegrityError
    from app.agente.models import AgenteUpload
    now = agora_brasil_naive()
    kw = dict(user_id=78, session_id='s', file_id='x', original_name='a.pdf',
              safe_name='x_a.pdf', s3_key='k', file_type='pdf',
              size_bytes=1, criado_em=now)
    db.session.add(AgenteUpload(**kw)); db.session.flush()
    db.session.add(AgenteUpload(**kw))
    with pytest.raises(IntegrityError):
        db.session.flush()
