"""
Cron diario de saude do modulo Custeio.

Executa todo dia as 07:00 e detecta:
- Custos dormentes (>30d sem atualizacao)
- Produtos ativos sem CustoConsiderado
- Tabela regra_comissao vazia (todas comissoes em fallback PADRAO)
- Acabados sem custo_producao definido
- Versoes duplicadas com custo_atual=TRUE (apos partial UNIQUE deveria ser 0)

Sprint 3 - C19 (auditoria 2026-05-10)

Crontab WSL2:
    0 7 * * * cd /home/rafaelnascimento/projetos/frete_sistema && \
        source .venv/bin/activate && \
        python -m app.scheduler.health_check_custeio >> logs/cron/health_custeio.log 2>&1
"""
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


# Limiares (configuraveis via parametros, mas defaults razoaveis)
LIMIAR_DIAS_DORMENCIA = 30
LIMIAR_PRODUTOS_SEM_CUSTO = 5  # alerta se mais de N
LIMIAR_DIAS_PARAMETROS_DORMENTES = 90


def check_dormencia_custos():
    """Verifica se custo_considerado tem atualizacao recente."""
    resultado = db.session.execute(db.text("""
        SELECT MAX(atualizado_em) AS ultima,
               EXTRACT(DAY FROM NOW() - MAX(atualizado_em))::INT AS dias
        FROM custo_considerado WHERE custo_atual = TRUE
    """)).first()
    if not resultado or not resultado.ultima:
        return ('CRITICO', 'Nenhum CustoConsiderado em custo_atual=TRUE encontrado')

    if resultado.dias > LIMIAR_DIAS_DORMENCIA:
        nivel = 'CRITICO' if resultado.dias > 90 else 'WARNING'
        return (nivel, f'Custos dormentes ha {resultado.dias} dias (ultima: {resultado.ultima.strftime("%d/%m/%Y")})')
    return ('OK', f'Custos atualizados ha {resultado.dias} dias')


def check_produtos_sem_custo():
    """Conta produtos ativos sem CustoConsiderado."""
    count = db.session.execute(db.text("""
        SELECT COUNT(*) FROM cadastro_palletizacao cp
        WHERE cp.ativo = TRUE
          AND NOT EXISTS (
            SELECT 1 FROM custo_considerado cc
            WHERE cc.cod_produto = cp.cod_produto AND cc.custo_atual = TRUE
          )
    """)).scalar() or 0

    if count > LIMIAR_PRODUTOS_SEM_CUSTO:
        return ('WARNING', f'{count} produtos ativos sem CustoConsiderado')
    if count > 0:
        return ('INFO', f'{count} produtos ativos sem CustoConsiderado (pequeno volume)')
    return ('OK', '0 produtos ativos sem custo')


def check_regras_comissao():
    """Verifica se tabela de regras esta vazia (todas comissoes via fallback)."""
    total_ativas = db.session.execute(db.text("""
        SELECT COUNT(*) FROM regra_comissao
        WHERE ativo = TRUE
          AND vigencia_inicio <= CURRENT_DATE
          AND (vigencia_fim IS NULL OR vigencia_fim >= CURRENT_DATE)
    """)).scalar() or 0

    pedidos_abertos = db.session.execute(db.text("""
        SELECT COUNT(*) FROM carteira_principal WHERE qtd_saldo_produto_pedido > 0
    """)).scalar() or 0

    if total_ativas == 0 and pedidos_abertos > 0:
        return ('WARNING', f'0 regras de comissao ativas, mas {pedidos_abertos} pedidos abertos. '
                f'Todas comissoes usam fallback COMISSAO_PADRAO.')
    return ('OK', f'{total_ativas} regras de comissao ativas')


def check_acabados_sem_custo_producao():
    """Conta produtos ACABADOS sem custo_producao definido (potencial margem liquida superestimada)."""
    count = db.session.execute(db.text("""
        SELECT COUNT(*) FROM custo_considerado cc
        WHERE cc.custo_atual = TRUE
          AND cc.tipo_produto = 'ACABADO'
          AND (cc.custo_producao IS NULL OR cc.custo_producao = 0)
    """)).scalar() or 0

    if count > 50:
        return ('WARNING', f'{count} produtos ACABADOS sem custo_producao (margem liquida superestimada)')
    if count > 0:
        return ('INFO', f'{count} produtos ACABADOS sem custo_producao')
    return ('OK', '100% dos ACABADOS com custo_producao')


def check_versoes_duplicadas():
    """Detecta produtos com mais de uma versao custo_atual=TRUE (deveria ser 0 com partial UNIQUE)."""
    duplicatas = db.session.execute(db.text("""
        SELECT COUNT(*) FROM (
            SELECT cod_produto FROM custo_considerado
            WHERE custo_atual = TRUE
            GROUP BY cod_produto HAVING COUNT(*) > 1
        ) AS dup
    """)).scalar() or 0

    if duplicatas > 0:
        return ('CRITICO', f'{duplicatas} produtos com 2+ versoes custo_atual=TRUE — partial UNIQUE deveria evitar isso')
    return ('OK', '0 versoes duplicadas')


def check_parametros_dormentes():
    """Verifica se parametros globais nao foram revisados ha tempo."""
    resultado = db.session.execute(db.text("""
        SELECT MAX(atualizado_em) AS ultima,
               EXTRACT(DAY FROM NOW() - MAX(atualizado_em))::INT AS dias
        FROM parametro_custeio WHERE ativo = TRUE
    """)).first()
    if not resultado or not resultado.ultima:
        return ('WARNING', 'Nenhum parametro ativo encontrado')

    if resultado.dias > LIMIAR_DIAS_PARAMETROS_DORMENTES:
        return ('WARNING', f'Parametros nao revisados ha {resultado.dias} dias')
    return ('OK', f'Parametros revisados ha {resultado.dias} dias')


CHECKS = [
    ('Dormencia de custos', check_dormencia_custos),
    ('Produtos ativos sem custo', check_produtos_sem_custo),
    ('Regras de comissao', check_regras_comissao),
    ('Acabados sem custo_producao', check_acabados_sem_custo_producao),
    ('Versoes duplicadas custo_atual', check_versoes_duplicadas),
    ('Dormencia de parametros', check_parametros_dormentes),
]


def main():
    app = create_app()
    with app.app_context():
        logger.info("=== HEALTH CHECK CUSTEIO ===")
        criticos = []
        warnings = []

        for nome, fn in CHECKS:
            try:
                nivel, mensagem = fn()
                logger.info(f"[{nivel:8s}] {nome}: {mensagem}")
                if nivel == 'CRITICO':
                    criticos.append(f"{nome}: {mensagem}")
                elif nivel == 'WARNING':
                    warnings.append(f"{nome}: {mensagem}")
            except Exception as e:
                logger.exception(f"Erro em check {nome}: {e}")
                criticos.append(f"{nome}: erro inesperado: {e}")

        # TODO: integrar com app.teams.notificacoes para enviar alerta
        # quando houver criticos ou >2 warnings.
        if criticos:
            logger.error(f"=== {len(criticos)} CRITICOS detectados ===")
            for c in criticos:
                logger.error(f"  - {c}")

        if warnings:
            logger.warning(f"=== {len(warnings)} WARNINGS detectados ===")
            for w in warnings:
                logger.warning(f"  - {w}")

        if not criticos and not warnings:
            logger.info("Custeio saudavel: sem criticos nem warnings.")


if __name__ == '__main__':
    main()
