"""
Job RQ: Verificacao de CTRC de CTe Complementar via SSW (opcao 101).

Background, low-priority. Disparado quando o usuario marca um CTe
Complementar com "Verificar SSW" no preview da importacao manual.

Consulta a opcao 101 do SSW pelo numero (nCT do XML) e compara com o
CTRC armazenado. Se divergir, atualiza `CarviaCteComplementar.ctrc_numero`
para o valor real do SSW.

Tipico: ~60-120s por CTe (Playwright headless).
"""
import logging

logger = logging.getLogger(__name__)


def verificar_ctrc_cte_comp_job(cte_comp_id: int) -> dict:
    """Job RQ: consulta SSW opcao 101 e atualiza ctrc_numero se divergir.

    Args:
        cte_comp_id: ID do CarviaCteComplementar a verificar

    Returns:
        dict com {status, ctrc_anterior, ctrc_novo, motivo}
        status: 'CORRIGIDO' | 'OK' | 'SKIPPED' | 'ERRO'
    """
    from app import create_app, db
    from app.carvia.models import CarviaCteComplementar
    from app.carvia.services.cte_complementar_persistencia import (
        resolver_ctrc_ssw,
    )
    from app.utils.timezone import agora_utc_naive

    app = create_app()
    with app.app_context():
        cte_comp = db.session.get(CarviaCteComplementar, cte_comp_id)
        if not cte_comp:
            logger.warning(
                "verificar_ctrc_cte_comp_job: CTe Comp %s nao encontrado",
                cte_comp_id,
            )
            return {
                'status': 'SKIPPED',
                'motivo': 'CTe Comp nao encontrado',
            }

        if not cte_comp.ctrc_numero:
            logger.info(
                "verificar_ctrc_cte_comp_job: CTe Comp %s sem ctrc_numero "
                "(nada a verificar)",
                cte_comp_id,
            )
            return {
                'status': 'SKIPPED',
                'motivo': 'CTe Comp sem ctrc_numero',
            }

        ctrc_anterior = cte_comp.ctrc_numero
        try:
            ctrc_corrigido = resolver_ctrc_ssw(
                ctrc_atual=ctrc_anterior,
                filial='CAR',
            )
        except Exception as e:
            logger.exception(
                "verificar_ctrc_cte_comp_job: erro ao consultar SSW "
                "para CTe Comp %s",
                cte_comp_id,
            )
            return {
                'status': 'ERRO',
                'erro': str(e),
                'ctrc_anterior': ctrc_anterior,
            }

        if ctrc_corrigido and ctrc_corrigido != ctrc_anterior:
            cte_comp.ctrc_numero = ctrc_corrigido
            cte_comp.atualizado_em = agora_utc_naive()
            db.session.commit()
            logger.info(
                "verificar_ctrc_cte_comp_job: CTe Comp %s — CTRC corrigido "
                "%s -> %s",
                cte_comp_id, ctrc_anterior, ctrc_corrigido,
            )
            return {
                'status': 'CORRIGIDO',
                'ctrc_anterior': ctrc_anterior,
                'ctrc_novo': ctrc_corrigido,
            }

        logger.info(
            "verificar_ctrc_cte_comp_job: CTe Comp %s — CTRC %s confirmado "
            "(sem alteracao)",
            cte_comp_id, ctrc_anterior,
        )
        return {
            'status': 'OK',
            'ctrc': ctrc_anterior,
        }
