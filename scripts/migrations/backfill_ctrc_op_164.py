"""
Backfill idempotente: corrige `CarviaOperacao.ctrc_numero` deduzido usando
a consulta 101 do SSW por nCT (script `consultar_ctrc_101.py --cte`).

O `ctrc_numero` de operacoes pre-existentes foi preenchido pelo parser
XML como `CAR-{nCT}-{cDV}`. Esse valor frequentemente diverge do CTRC
interno real do SSW (ex: op 164 tinha `CAR-161-2`, mas o SSW retornou
`CAR-164-3`). Este script chama `verificar_ctrc_operacao_job` — que:

  1. Consulta a 101 pelo numero do CTe (nCT)
  2. Extrai o `ctrc_completo` real do SSW (ex: CAR000164-3)
  3. Formata para `CAR-164-3`
  4. Atualiza `operacao.ctrc_numero` + `CarviaEmissaoCte.ctrc_numero`
     (emissao mais recente vinculada, se houver)

**Idempotencia garantida pelo proprio job**: se o CTRC atual ja bate
com o real do SSW, `verificar_ctrc_operacao_job` retorna `status='OK'`
sem tocar no banco. Re-execucoes sao seguras.

Requisitos:
  - SSW_URL, SSW_DOMINIO, SSW_CPF, SSW_LOGIN, SSW_SENHA no ambiente
  - DATABASE_URL apontando para o banco alvo
  - Playwright com chromium instalado

Uso:
  # Default: corrige apenas op 164
  python scripts/migrations/backfill_ctrc_op_164.py

  # Lista explicita
  python scripts/migrations/backfill_ctrc_op_164.py --op-ids 164,170,182

  # Uma op especifica
  python scripts/migrations/backfill_ctrc_op_164.py --op-id 170

  # Varre TODAS as ops com CTRC deduzido (padrao CAR-{nCT}-{cDV})
  python scripts/migrations/backfill_ctrc_op_164.py --todas

Tipico: ~60-120s por operacao (Playwright headless por consulta).
"""
import argparse
import logging
import re
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)


def _eh_ctrc_deduzido(cte_numero, ctrc_numero, cte_chave_acesso):
    """True se `ctrc_numero` parece deduzido via `FILIAL-{nCT}-{cDV}`."""
    if not ctrc_numero or not cte_numero or not cte_chave_acesso:
        return False
    if len(cte_chave_acesso) < 44:
        return False
    try:
        nct = str(int(str(cte_numero).strip()))
    except (ValueError, TypeError):
        return False
    cdv_esperado = cte_chave_acesso[-1]
    m = re.match(r'^[A-Z]{2,4}-(\d+)-(\d)$', ctrc_numero.strip())
    if not m:
        return False
    return m.group(1) == nct and m.group(2) == cdv_esperado


def _listar_ops_deduzidas():
    """Varre o banco e retorna IDs de ops com CTRC deduzido."""
    from app import create_app, db
    from app.carvia.models import CarviaOperacao

    app = create_app()
    with app.app_context():
        ops = (
            db.session.query(
                CarviaOperacao.id,
                CarviaOperacao.cte_numero,
                CarviaOperacao.ctrc_numero,
                CarviaOperacao.cte_chave_acesso,
            )
            .filter(CarviaOperacao.ctrc_numero.isnot(None))
            .filter(CarviaOperacao.cte_numero.isnot(None))
            .filter(CarviaOperacao.cte_chave_acesso.isnot(None))
            .order_by(CarviaOperacao.id)
            .all()
        )
        return [
            row[0] for row in ops
            if _eh_ctrc_deduzido(row[1], row[2], row[3])
        ]


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Corrige ctrc_numero deduzido de CarviaOperacao via SSW 101. "
            "Idempotente."
        )
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--op-id', type=int, default=164,
        help='ID da CarviaOperacao a corrigir (default: 164)',
    )
    group.add_argument(
        '--op-ids', type=str,
        help='Lista de IDs separados por virgula (ex: 164,170,182)',
    )
    group.add_argument(
        '--todas', action='store_true',
        help='Varre todas as ops com padrao CAR-{nCT}-{cDV} deduzido',
    )
    parser.add_argument(
        '--continue-on-error', action='store_true', default=True,
        help='Nao interrompe em erro (default: True)',
    )
    args = parser.parse_args()

    # Determinar lista de IDs ANTES de entrar no app context do job
    # (o job cria o proprio app context — nao queremos contexts aninhados)
    if args.todas:
        op_ids = _listar_ops_deduzidas()
        logger.info(
            "Varredura --todas: %d ops com CTRC deduzido encontradas",
            len(op_ids),
        )
    elif args.op_ids:
        op_ids = [
            int(x.strip()) for x in args.op_ids.split(',') if x.strip()
        ]
    else:
        op_ids = [args.op_id]

    if not op_ids:
        logger.info("Nenhuma op para processar. Saindo.")
        return 0

    logger.info("Processando %d op(s): %s", len(op_ids), op_ids)

    # Importa o job apos determinar a lista (lazy)
    from app.carvia.workers.verificar_ctrc_ssw_jobs import (
        verificar_ctrc_operacao_job,
    )

    resultados = {'CORRIGIDO': 0, 'OK': 0, 'SKIPPED': 0, 'ERRO': 0}
    detalhes_erro = []

    for idx, op_id in enumerate(op_ids, start=1):
        logger.info(
            "[%d/%d] Processando op %s...", idx, len(op_ids), op_id,
        )
        try:
            resultado = verificar_ctrc_operacao_job(op_id)
        except Exception as e:
            logger.exception(
                "Op %s: excecao nao capturada — %s", op_id, e,
            )
            resultados['ERRO'] += 1
            detalhes_erro.append({'op_id': op_id, 'erro': str(e)})
            if not args.continue_on_error:
                break
            continue

        status = resultado.get('status', 'ERRO')
        resultados[status] = resultados.get(status, 0) + 1

        if status == 'CORRIGIDO':
            logger.info(
                "  OK op %s: %s -> %s",
                op_id,
                resultado.get('ctrc_anterior'),
                resultado.get('ctrc_novo'),
            )
        elif status == 'OK':
            logger.info(
                "  OK op %s: CTRC %s ja esta correto (idempotente)",
                op_id, resultado.get('ctrc'),
            )
        elif status == 'SKIPPED':
            logger.info(
                "  SKIP op %s: %s",
                op_id, resultado.get('motivo'),
            )
        else:
            logger.warning(
                "  ERRO op %s: %s",
                op_id, resultado.get('erro'),
            )
            detalhes_erro.append({
                'op_id': op_id,
                'erro': resultado.get('erro'),
            })

    logger.info("=" * 60)
    logger.info("RESUMO:")
    logger.info("  CORRIGIDO : %d", resultados['CORRIGIDO'])
    logger.info("  OK        : %d (ja estava correto)", resultados['OK'])
    logger.info("  SKIPPED   : %d", resultados['SKIPPED'])
    logger.info("  ERRO      : %d", resultados['ERRO'])
    logger.info("=" * 60)

    if detalhes_erro:
        logger.warning("Detalhes dos erros:")
        for d in detalhes_erro:
            logger.warning("  op %s: %s", d['op_id'], d['erro'])

    return 0 if resultados['ERRO'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
