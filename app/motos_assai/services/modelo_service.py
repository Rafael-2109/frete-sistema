import re
from app import db
from app.motos_assai.models import AssaiModelo


class ModeloJaExisteError(Exception):
    pass


def listar_modelos(somente_ativos: bool = False):
    q = AssaiModelo.query
    if somente_ativos:
        q = q.filter_by(ativo=True)
    return q.order_by(AssaiModelo.codigo).all()


def get_modelo(modelo_id: int) -> AssaiModelo:
    return AssaiModelo.query.get_or_404(modelo_id)


def criar_modelo(dados: dict) -> AssaiModelo:
    if AssaiModelo.query.filter_by(codigo=dados['codigo']).first():
        raise ModeloJaExisteError(f"Modelo {dados['codigo']} já existe")
    m = AssaiModelo(**dados)
    db.session.add(m)
    db.session.commit()
    return m


def atualizar_modelo(modelo_id: int, dados: dict) -> AssaiModelo:
    m = AssaiModelo.query.get_or_404(modelo_id)
    for k, v in dados.items():
        if hasattr(m, k):
            setattr(m, k, v)
    db.session.commit()
    return m


def testar_regex(regex: str, chassi: str) -> bool:
    """Valida se o chassi bate com o regex (anchors aplicados se faltarem)."""
    pattern = regex
    if not pattern.startswith('^'):
        pattern = '^' + pattern
    if not pattern.endswith('$'):
        pattern = pattern + '$'
    return bool(re.match(pattern, chassi))
