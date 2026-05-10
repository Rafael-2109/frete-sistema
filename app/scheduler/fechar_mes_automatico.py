"""
Fechamento mensal automatico de custeio.

Decisao Nacom (2026-05-10): fechamento manual via UI desabilitado.
Cron e o unico caminho de fechamento. Idempotente — se mes ja foi fechado,
ServicoCusteio.fechar_mes faz UPDATE in-place (constraint UNIQUE protege
duplicatas).

Uso:

1. INTEGRADO ao scheduler unico (Render) — recomendado:
   Importar `executar_fechamento_mes_anterior_no_contexto()` no
   `sincronizacao_incremental_definitiva.py` step 26.

2. STANDALONE via CLI (dev/staging/recovery):
   python -m app.scheduler.fechar_mes_automatico

Sprint 2 - C10 (auditoria 2026-05-10)
"""
import sys
import os
import logging
from datetime import date, timedelta

# Path setup obrigatorio quando rodado via python -m (standalone CLI)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


def executar_fechamento_mes_anterior_no_contexto():
    """Executa fechamento do mes anterior. ASSUME app_context ja ativo.

    Retorna o dict resultado do ServicoCusteio.fechar_mes (com chave 'erro'
    se falhar). Nao chama sys.exit — caller decide como reportar.

    Idempotente: se mes ja foi fechado, faz UPDATE in-place.
    """
    from app.custeio.services.custeio_service import ServicoCusteio

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
            return resultado

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

        return resultado

    except Exception as e:
        logger.exception(f"Erro fatal no fechamento automatico: {e}")
        return {'erro': str(e)}


def main():
    """Modo standalone CLI: cria app_context e roda fechamento."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    from app import create_app
    app = create_app()
    with app.app_context():
        resultado = executar_fechamento_mes_anterior_no_contexto()
        if resultado.get('erro'):
            sys.exit(1)


if __name__ == '__main__':
    main()
