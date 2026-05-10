"""
Cron mensal: fecha automaticamente o mes anterior no dia 5 as 04:00.

Decisao Nacom (2026-05-10): fechamento manual via UI desabilitado.
Cron e o unico caminho de fechamento. Idempotente — se mes ja foi fechado,
ServicoCusteio.fechar_mes faz UPDATE in-place (constraint UNIQUE protege duplicatas).

Crontab WSL2:
    0 4 5 * * cd /home/rafaelnascimento/projetos/frete_sistema && \
        source .venv/bin/activate && \
        python -m app.scheduler.fechar_mes_automatico >> logs/cron/fechar_mes.log 2>&1

Sprint 2 - C10 (auditoria 2026-05-10)
"""
import sys
import os
import logging
from datetime import date, timedelta

# Path setup obrigatorio quando rodado via python -m
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.custeio.services.custeio_service import ServicoCusteio


# Configurar logging para cron (alem do que o Flask configura)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Executa fechamento do mes anterior."""
    app = create_app()
    with app.app_context():
        hoje = date.today()
        # Calcular mes anterior (mes que acabou de ser encerrado)
        primeiro_dia_mes_atual = hoje.replace(day=1)
        ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
        mes_alvo = ultimo_dia_mes_anterior.month
        ano_alvo = ultimo_dia_mes_anterior.year

        logger.info(f"=== FECHAMENTO AUTOMATICO {mes_alvo:02d}/{ano_alvo} ===")
        logger.info(f"Hoje: {hoje}, Mes alvo: {mes_alvo:02d}/{ano_alvo}")

        try:
            resultado = ServicoCusteio.fechar_mes(mes_alvo, ano_alvo, 'cron-automatico')

            if resultado.get('erro'):
                logger.error(f"Falha no fechamento: {resultado['erro']}")
                sys.exit(1)

            comprados = resultado.get('comprados', {})
            intermediarios = resultado.get('intermediarios', {})
            acabados = resultado.get('acabados', {})

            logger.info(
                f"Concluido: {resultado.get('total', 0)} produtos processados "
                f"(comprados={comprados.get('processados', 0)}, "
                f"intermediarios={intermediarios.get('processados', 0)}, "
                f"acabados={acabados.get('processados', 0)})"
            )

            erros_total = (len(comprados.get('erros', []))
                           + len(intermediarios.get('erros', []))
                           + len(acabados.get('erros', [])))
            if erros_total > 0:
                logger.warning(f"Houve {erros_total} erros parciais durante fechamento.")
                for tipo, info in [('comprados', comprados), ('intermediarios', intermediarios), ('acabados', acabados)]:
                    for erro in info.get('erros', [])[:5]:
                        logger.warning(f"  [{tipo}] {erro}")

        except Exception as e:
            logger.exception(f"Erro fatal no fechamento automatico: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()
