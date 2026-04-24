"""
Task 23 — hook de notificacao de CTe divergente do cotado.

Dispara alerta quando conhecimento de transporte tem valor divergente
da cotacao inicial. Chamado pelo servico de controle de frete ao detectar
divergencia.

Uso (app/fretes/services/... ao detectar divergencia):

    from app.chat.hooks.cte_divergente import notify_cte_divergente
    try:
        notify_cte_divergente(cte, valor_cotado=500.00, valor_cte=650.00)
    except Exception as e:
        logger.error(f'[CHAT hook] cte notify falhou: {e}')
"""
from decimal import Decimal
from typing import List, Optional, Union

from sqlalchemy import select

from app import db
from app.auth.models import Usuario
from app.chat.services.system_notifier import SystemNotifier
from app.utils.logging_config import logger


Numeric = Union[int, float, Decimal]


def _get_frete_controllers() -> List[int]:
    """Controllers de frete — `sistema_logistica=True` (alinhamento com receb.).

    Futuro: flag dedicado `sistema_fretes` ou tabela por tipo de evento.
    """
    controllers = db.session.execute(
        select(Usuario.id).where(
            Usuario.status == 'ativo',
            db.or_(
                Usuario.sistema_logistica.is_(True),
                Usuario.perfil == 'administrador',
            ),
        )
    ).scalars().all()
    return list(controllers)


def notify_cte_divergente(
    cte,
    valor_cotado: Numeric,
    valor_cte: Numeric,
    destinatarios: Optional[List[int]] = None,
):
    """Envia alerta ATENCAO/CRITICO quando CTe diverge da cotacao.

    Nivel decidido por % de divergencia:
    - >= 20% -> CRITICO
    - < 20% -> ATENCAO

    Nao levanta excecoes — loga e engolе.
    """
    try:
        if destinatarios is None:
            destinatarios = _get_frete_controllers()
        if not destinatarios:
            logger.warning('[CHAT hook] sem destinatarios para CTe divergente')
            return

        valor_cotado_d = Decimal(str(valor_cotado))
        valor_cte_d = Decimal(str(valor_cte))
        if valor_cotado_d > 0:
            pct = abs(valor_cte_d - valor_cotado_d) / valor_cotado_d * 100
        else:
            pct = Decimal('100')  # cotado zero + CTe > 0 eh divergencia maxima

        nivel = 'CRITICO' if pct >= 20 else 'ATENCAO'
        cte_numero = getattr(cte, 'numero', None) or getattr(cte, 'id', '-')
        cte_id = getattr(cte, 'id', 0)

        titulo = f'CTe {cte_numero} divergente ({pct:.1f}%)'
        content = (
            f'Cotado: R$ {valor_cotado_d:.2f}\n'
            f'CTe: R$ {valor_cte_d:.2f}\n'
            f'Divergencia: R$ {valor_cte_d - valor_cotado_d:+.2f} ({pct:.1f}%)'
        )

        SystemNotifier.alert(
            user_ids=destinatarios,
            source='cte',
            titulo=titulo,
            content=content,
            deep_link=f'/fretes/cte/{cte_id}',
            nivel=nivel,
            dados={
                'cte_id': cte_id,
                'cte_numero': str(cte_numero),
                'valor_cotado': valor_cotado_d,
                'valor_cte': valor_cte_d,
                'divergencia_pct': pct,
            },
        )
        logger.info(
            f'[CHAT hook] notify_cte_divergente: cte={cte_numero} '
            f'pct={pct:.1f}% nivel={nivel} destinatarios={len(destinatarios)}'
        )
    except Exception as e:
        logger.error(f'[CHAT hook] notify_cte_divergente falhou: {e}', exc_info=True)
