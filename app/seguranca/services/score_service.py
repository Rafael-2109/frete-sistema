"""
Score Service
=============

Calcula score de risco de seguranca (0-100, onde 100=melhor).

Pesos:
- email_breach: 30%
- password_health: 30%
- domain: 20%
- remediacao: 20%
"""

from typing import Dict, Any, Optional

from app import db
from app.utils.timezone import agora_utc_naive
from app.utils.logging_config import logger


def calcular_score_usuario(user_id: int) -> Dict[str, Any]:
    """
    Calcula score de seguranca de um usuario.

    Args:
        user_id: ID do usuario

    Returns:
        dict com score total e componentes
    """
    from app.seguranca.models import SegurancaVulnerabilidade, SegurancaScore

    vulns = SegurancaVulnerabilidade.query.filter_by(
        user_id=user_id,
    ).filter(
        SegurancaVulnerabilidade.status.in_(['ABERTA', 'EM_ANDAMENTO'])
    ).all()

    componentes = {
        'email_breach': 100,
        'password_health': 100,
        'domain': 100,
        'remediacao': 100,
    }

    # Penalidades por categoria
    for v in vulns:
        penalidade = _penalidade_por_severidade(v.severidade)

        if v.categoria == 'EMAIL_BREACH':
            componentes['email_breach'] = max(
                0, componentes['email_breach'] - penalidade
            )
        elif v.categoria in ('SENHA_FRACA', 'SENHA_VAZADA'):
            componentes['password_health'] = max(
                0, componentes['password_health'] - penalidade
            )
        elif v.categoria.startswith('DOMINIO_'):
            componentes['domain'] = max(
                0, componentes['domain'] - penalidade
            )

    # Bonus por remediacao (vulnerabilidades resolvidas)
    resolvidas = SegurancaVulnerabilidade.query.filter_by(
        user_id=user_id,
    ).filter(
        SegurancaVulnerabilidade.status.in_(['RESOLVIDA', 'ACEITA'])
    ).count()

    total_vulns = len(vulns) + resolvidas
    if total_vulns > 0:
        taxa_remediacao = resolvidas / total_vulns
        componentes['remediacao'] = int(taxa_remediacao * 100)

    # Score ponderado
    pesos = {
        'email_breach': 0.30,
        'password_health': 0.30,
        'domain': 0.20,
        'remediacao': 0.20,
    }
    score = sum(
        componentes[k] * pesos[k] for k in pesos
    )
    score = int(round(score))

    # Penalidade extra por vulnerabilidades criticas abertas
    criticas_abertas = sum(
        1 for v in vulns if v.severidade == 'CRITICA'
    )
    if criticas_abertas > 0:
        score = max(0, score - (criticas_abertas * 10))

    resultado = {
        'score': max(0, min(100, score)),
        'componentes': componentes,
        'vulnerabilidades_abertas': len(vulns),
        'vulnerabilidades_criticas': criticas_abertas,
    }

    # Gravar historico
    try:
        score_registro = SegurancaScore(
            user_id=user_id,
            score=resultado['score'],
            componentes=componentes,
            vulnerabilidades_abertas=len(vulns),
            vulnerabilidades_criticas=criticas_abertas,
        )
        db.session.add(score_registro)
        db.session.flush()
    except Exception as e:
        logger.error(f"Erro ao gravar score usuario {user_id}: {e}")

    return resultado


def calcular_score_empresa() -> Dict[str, Any]:
    """
    Calcula score agregado da empresa.

    Returns:
        dict com score total, componentes e breakdown
    """
    from app.auth.models import Usuario
    from app.seguranca.models import SegurancaVulnerabilidade, SegurancaScore

    usuarios = Usuario.query.filter_by(status='ativo').all()
    if not usuarios:
        return {
            'score': 100,
            'componentes': {
                'email_breach': 100,
                'password_health': 100,
                'domain': 100,
                'remediacao': 100,
            },
            'vulnerabilidades_abertas': 0,
            'vulnerabilidades_criticas': 0,
            'total_usuarios': 0,
        }

    # Contar vulnerabilidades totais
    vulns_abertas = SegurancaVulnerabilidade.query.filter(
        SegurancaVulnerabilidade.status.in_(['ABERTA', 'EM_ANDAMENTO'])
    ).all()

    vulns_resolvidas = SegurancaVulnerabilidade.query.filter(
        SegurancaVulnerabilidade.status.in_(['RESOLVIDA', 'ACEITA'])
    ).count()

    total_vulns = len(vulns_abertas) + vulns_resolvidas

    # Componentes
    componentes = {
        'email_breach': 100,
        'password_health': 100,
        'domain': 100,
        'remediacao': 100,
    }

    for v in vulns_abertas:
        penalidade = _penalidade_por_severidade(v.severidade)
        # Normalizar penalidade pelo numero de usuarios
        penalidade_norm = penalidade / max(len(usuarios), 1)

        if v.categoria == 'EMAIL_BREACH':
            componentes['email_breach'] = max(
                0, componentes['email_breach'] - penalidade_norm
            )
        elif v.categoria in ('SENHA_FRACA', 'SENHA_VAZADA'):
            componentes['password_health'] = max(
                0, componentes['password_health'] - penalidade_norm
            )
        elif v.categoria.startswith('DOMINIO_'):
            componentes['domain'] = max(
                0, componentes['domain'] - penalidade_norm
            )

    if total_vulns > 0:
        taxa_remediacao = vulns_resolvidas / total_vulns
        componentes['remediacao'] = int(taxa_remediacao * 100)

    pesos = {
        'email_breach': 0.30,
        'password_health': 0.30,
        'domain': 0.20,
        'remediacao': 0.20,
    }
    score = sum(componentes[k] * pesos[k] for k in pesos)

    criticas = sum(1 for v in vulns_abertas if v.severidade == 'CRITICA')
    if criticas > 0:
        score = max(0, score - (criticas * 5))

    score = int(round(max(0, min(100, score))))

    resultado = {
        'score': score,
        'componentes': {k: int(round(v)) for k, v in componentes.items()},
        'vulnerabilidades_abertas': len(vulns_abertas),
        'vulnerabilidades_criticas': criticas,
        'total_usuarios': len(usuarios),
    }

    # Gravar historico empresa (user_id=NULL)
    try:
        score_registro = SegurancaScore(
            user_id=None,
            score=resultado['score'],
            componentes=resultado['componentes'],
            vulnerabilidades_abertas=len(vulns_abertas),
            vulnerabilidades_criticas=criticas,
        )
        db.session.add(score_registro)
        db.session.flush()
    except Exception as e:
        logger.error(f"Erro ao gravar score empresa: {e}")

    return resultado


def _penalidade_por_severidade(severidade: str) -> int:
    """Retorna penalidade de score por severidade"""
    return {
        'CRITICA': 40,
        'ALTA': 25,
        'MEDIA': 15,
        'BAIXA': 8,
        'INFO': 3,
    }.get(severidade, 5)
