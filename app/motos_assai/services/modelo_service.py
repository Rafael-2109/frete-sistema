import re
from typing import Optional

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


def atualizar_modelo(
    modelo_id: int, dados: dict, operador_id: Optional[int] = None,
) -> AssaiModelo:
    m = AssaiModelo.query.get_or_404(modelo_id)

    # Captura campos que afetam match (codigo, descricao_qpa) — quando mudam,
    # resolver_modelo no _calcular_match pode resolver diferente.
    codigo_antigo = m.codigo
    descricao_qpa_antiga = m.descricao_qpa

    for k, v in dados.items():
        if hasattr(m, k):
            setattr(m, k, v)
    db.session.commit()

    # Hook F1 (2026-05-17): mudancas em codigo/descricao_qpa afetam
    # resolver_modelo que e usado no _calcular_match para validacao
    # MODELO_DIVERGENTE. NFs com chassis cujo AssaiMoto.modelo_id == este
    # modelo podem ter divergencia resolvida/criada.
    afetou_match = (
        m.codigo != codigo_antigo or m.descricao_qpa != descricao_qpa_antiga
    )
    if afetou_match:
        _hook_reprocessar_nfs_por_modelo(
            m.id, operador_id, motivo='HOOK_MODELO_ATUALIZADO',
        )

    return m


def testar_regex(regex: str, chassi: str) -> bool:
    """Valida se o chassi bate com o regex (anchors aplicados se faltarem)."""
    pattern = regex
    if not pattern.startswith('^'):
        pattern = '^' + pattern
    if not pattern.endswith('$'):
        pattern = pattern + '$'
    return bool(re.match(pattern, chassi))


# ─── helpers de hook ──────────────────────────────────────────────────────────

def _hook_reprocessar_nfs_por_modelo(
    modelo_id: int, operador_id: Optional[int], motivo: str,
) -> None:
    """Reprocessa NFs com chassis cujo AssaiMoto.modelo_id == X."""
    try:
        from app.motos_assai.services.reprocessar_match_service import (
            reprocessar_match_nfs, nfs_afetadas_por_modelo,
        )
        nf_ids = nfs_afetadas_por_modelo(modelo_id)
        if nf_ids:
            reprocessar_match_nfs(
                nf_ids, motivo=motivo, operador_id=operador_id,
            )
    except Exception:
        import logging as _log
        _log.getLogger(__name__).exception(
            'hook reprocessar_match (modelo=%s motivo=%s) falhou — '
            'atualizacao ja commitada',
            modelo_id, motivo,
        )
