from app import db
from app.motos_assai.models import AssaiCd


def get_cd_principal() -> AssaiCd | None:
    """Retorna o CD ativo (na v1 esperamos 1 único 'Operação VOE')."""
    return AssaiCd.query.filter_by(ativo=True).order_by(AssaiCd.id).first()


def atualizar_cd(cd_id: int, dados: dict) -> AssaiCd:
    cd = AssaiCd.query.get_or_404(cd_id)
    for k, v in dados.items():
        if hasattr(cd, k):
            setattr(cd, k, v)
    db.session.commit()
    return cd
