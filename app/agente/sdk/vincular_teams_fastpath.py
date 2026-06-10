"""Fast-path determinístico 'vincular CODIGO' — pareamento Teams <-> Web.

Fase A do plano docs/superpowers/plans/2026-06-10-teams-melhorias.md.

Fluxo: usuário logado no web gera código (tela /auth/vincular-teams) e envia
"vincular ABC123" ao bot no Teams. Este fast-path valida o hash (sha256, TTL,
uso único) e grava Usuario.teams_user_id (AAD object ID) — prova de posse das
DUAS contas, independente do e-mail cadastrado estar correto.

Padrão espelha baseline_fastpath.py: should_intercept_* (regex conservador) +
executar_* (NUNCA levanta; respostas de erro são determinísticas — código
inválido/expirado NÃO cai no LLM, pois a intenção é inequívoca).

Anti-colisão com o fast-path NF×PO (vinculacao_fastpath.py, Gabriella):
- frases como "vincular pedido X na nota Y" têm palavras extras -> regex exige
  fim de string logo após o código;
- códigos de pareamento começam com LETRA (gerados assim na tela web) -> regex
  rejeita dígitos puros ("vincular 123456" pode ser número de pedido).
"""
import hashlib
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 6 chars, primeiro obrigatoriamente letra (códigos gerados garantem isso).
_VINCULAR_RE = re.compile(r'^\s*vincular\s+([A-Za-z][A-Za-z0-9]{5})\s*$', re.IGNORECASE)


def should_intercept_vincular(mensagem: Optional[str]) -> bool:
    """True se a mensagem é EXATAMENTE 'vincular <CODIGO>' (conservador)."""
    if not mensagem or not str(mensagem).strip():
        return False
    return bool(_VINCULAR_RE.match(str(mensagem).strip()))


def executar_vincular_fastpath(
    mensagem: str,
    aad_id: Optional[str],
    email: Optional[str],
    nome: Optional[str],
    fallback_user_id: Optional[int],
) -> dict:
    """Valida o código de pareamento e grava o vínculo. NUNCA levanta.

    Args:
        mensagem: texto já aprovado por should_intercept_vincular
        aad_id: AAD object ID do falante (obrigatório para vincular)
        email: e-mail corporativo (apenas log)
        nome: nome do falante no Teams (localiza fantasma p/ merge)
        fallback_user_id: user_id resolvido pela hierarquia (apenas log)

    Returns:
        {"ok": True, "resposta": str} — sempre ok=True (resposta determinística);
        ok=False apenas em erro interno inesperado (caller cai no fluxo normal).
    """
    try:
        from app import db
        from app.auth.models import Usuario, TeamsVinculoCodigo
        from app.utils.timezone import agora_utc_naive

        m = _VINCULAR_RE.match(str(mensagem).strip())
        if not m:
            return {"ok": False, "resposta": None}
        codigo = m.group(1).upper()
        codigo_hash = hashlib.sha256(codigo.encode()).hexdigest()

        vc = TeamsVinculoCodigo.query.filter(
            TeamsVinculoCodigo.codigo_hash == codigo_hash,
            TeamsVinculoCodigo.used_at.is_(None),
            TeamsVinculoCodigo.expires_at > agora_utc_naive(),
        ).first()
        if not vc:
            return {
                "ok": True,
                "resposta": (
                    "Código inválido ou expirado. Gere um novo no sistema web "
                    "(menu do usuário → Vincular Teams) e envie aqui de novo: "
                    "vincular SEUCODIGO"
                ),
            }

        if not aad_id or not str(aad_id).strip():
            return {
                "ok": True,
                "resposta": (
                    "Não consegui identificar sua conta do Teams nesta mensagem. "
                    "Tente enviar o código novamente."
                ),
            }

        user = db.session.get(Usuario, vc.user_id)
        if not user:
            return {
                "ok": True,
                "resposta": "Código inválido ou expirado. Gere um novo no sistema web.",
            }

        user.teams_user_id = str(aad_id).strip()
        user.teams_vinculo_origem = 'codigo'
        vc.used_at = agora_utc_naive()
        db.session.commit()
        logger.info(
            f"[TEAMS-VINCULO] Vínculo por código: user_id={user.id} "
            f"aad={str(aad_id)[:12]}... nome_teams='{nome}' email_teams='{email}' "
            f"(fallback_user_id={fallback_user_id})"
        )

        # Merge best-effort do usuário fantasma (histórico/memórias) — Task A7
        merge_resumo = ""
        try:
            from app.teams.services import _merge_usuario_fantasma
            merge_resumo = _merge_usuario_fantasma(nome, user.id) or ""
        except Exception as merge_err:
            logger.warning(
                f"[TEAMS-VINCULO] Merge de fantasma falhou (vínculo OK): {merge_err}"
            )

        resposta = (
            f"Vinculado! Você agora é {user.nome} ({user.email}) no sistema."
        )
        if merge_resumo:
            resposta += f" {merge_resumo}"
        return {"ok": True, "resposta": resposta}

    except Exception as e:
        logger.error(f"[TEAMS-VINCULO] Erro inesperado: {e}", exc_info=True)
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        return {"ok": False, "resposta": None}
