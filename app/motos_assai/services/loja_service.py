from typing import Optional

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


def criar_loja(dados: dict, operador_id: Optional[int] = None) -> AssaiLoja:
    if AssaiLoja.query.filter_by(numero=dados['numero']).first():
        raise LojaJaExisteError(f"Loja com número {dados['numero']} já existe")
    loja = AssaiLoja(**dados)
    db.session.add(loja)
    db.session.commit()

    # Hook A2 (2026-05-17): nova loja com CNPJ pode resolver NFs antigas em
    # NAO_RECONCILIADO cujo `destinatario_cnpj` casa com este CNPJ.
    if loja.cnpj:
        _hook_reprocessar_nfs_por_cnpj_novo(
            loja.cnpj, operador_id, motivo='HOOK_LOJA_CRIADA',
        )

    return loja


def atualizar_loja(
    loja_id: int, dados: dict, operador_id: Optional[int] = None,
) -> AssaiLoja:
    loja = AssaiLoja.query.get_or_404(loja_id)

    # Captura CNPJ antigo ANTES do setattr — necessario para identificar NFs
    # que casavam pelo CNPJ antigo (e podem precisar regredir) alem das que
    # casam pelo CNPJ novo.
    cnpj_antigo = loja.cnpj

    for k, v in dados.items():
        if hasattr(loja, k):
            setattr(loja, k, v)
    db.session.commit()

    # Hook A1 (2026-05-17): mudancas em cnpj/ativo afetam match de loja.
    # `nfs_afetadas_por_loja` retorna NFs com loja_id == loja_id (atuais) +
    # NFs em NAO_RECONCILIADO cujo CNPJ casa com cnpj_atual ou cnpj_antigo.
    cnpj_mudou = cnpj_antigo != loja.cnpj
    if cnpj_mudou or 'ativo' in dados:
        _hook_reprocessar_nfs_por_loja(
            loja.id, cnpj_antigo if cnpj_mudou else None,
            operador_id, motivo='HOOK_LOJA_ATUALIZADA',
        )

    return loja


def get_loja(loja_id: int) -> AssaiLoja:
    return AssaiLoja.query.get_or_404(loja_id)


# ─── helpers de hook ──────────────────────────────────────────────────────────

def _hook_reprocessar_nfs_por_cnpj_novo(
    cnpj: str, operador_id: Optional[int], motivo: str,
) -> None:
    """Reprocessa NFs em NAO_RECONCILIADO cujo CNPJ destinatario casa."""
    try:
        from app.motos_assai.services.reprocessar_match_service import (
            reprocessar_match_nfs, nfs_afetadas_por_cnpj_novo,
        )
        nf_ids = nfs_afetadas_por_cnpj_novo(cnpj)
        if nf_ids:
            reprocessar_match_nfs(
                nf_ids, motivo=motivo, operador_id=operador_id,
            )
    except Exception:
        import logging as _log
        _log.getLogger(__name__).exception(
            'hook reprocessar_match (cnpj=%s motivo=%s) falhou — '
            'criacao de loja ja commitada',
            cnpj, motivo,
        )


def _hook_reprocessar_nfs_por_loja(
    loja_id: int, cnpj_antigo: Optional[str], operador_id: Optional[int],
    motivo: str,
) -> None:
    """Reprocessa NFs vinculadas a uma loja (cnpj atual ou antigo)."""
    try:
        from app.motos_assai.services.reprocessar_match_service import (
            reprocessar_match_nfs, nfs_afetadas_por_loja,
        )
        nf_ids = nfs_afetadas_por_loja(loja_id, cnpj_antigo=cnpj_antigo)
        if nf_ids:
            reprocessar_match_nfs(
                nf_ids, motivo=motivo, operador_id=operador_id,
            )
    except Exception:
        import logging as _log
        _log.getLogger(__name__).exception(
            'hook reprocessar_match (loja=%s motivo=%s) falhou — '
            'atualizacao ja commitada',
            loja_id, motivo,
        )
