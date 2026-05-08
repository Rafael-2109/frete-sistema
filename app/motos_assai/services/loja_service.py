from app import db
from app.motos_assai.models import AssaiLoja


class LojaJaExisteError(Exception):
    pass


def listar_lojas(somente_ativas: bool = False, busca: str | None = None):
    q = AssaiLoja.query
    if somente_ativas:
        q = q.filter_by(ativo=True)
    if busca:
        like = f'%{busca}%'
        q = q.filter(
            db.or_(
                AssaiLoja.numero.ilike(like),
                AssaiLoja.nome.ilike(like),
                AssaiLoja.cidade.ilike(like),
            )
        )
    return q.order_by(AssaiLoja.numero).all()


def criar_loja(dados: dict) -> AssaiLoja:
    if AssaiLoja.query.filter_by(numero=dados['numero']).first():
        raise LojaJaExisteError(f"Loja com número {dados['numero']} já existe")
    loja = AssaiLoja(**dados)
    db.session.add(loja)
    db.session.commit()
    return loja


def atualizar_loja(loja_id: int, dados: dict) -> AssaiLoja:
    loja = AssaiLoja.query.get_or_404(loja_id)
    for k, v in dados.items():
        if hasattr(loja, k):
            setattr(loja, k, v)
    db.session.commit()
    return loja


def get_loja(loja_id: int) -> AssaiLoja:
    return AssaiLoja.query.get_or_404(loja_id)
