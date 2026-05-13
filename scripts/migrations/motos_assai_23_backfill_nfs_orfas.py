"""Migration 23 (Plano 3 Fase 4): backfill NFs orfas — invoca ajustar_separacao_pela_nf v2.

A15: rodar MANUAL no Render Shell APOS deploy da Fase 4 (sem incluir em build.sh).

Objetivo: para cada AssaiNfQpa com status_match=NAO_RECONCILIADO, executar
`ajustar_separacao_pela_nf` v2 (S1=b cria sep em FATURADA + A11 gera Excel +
A7 detecta CHASSI_OUTRA_LOJA + S19=b NF parcial).

Idempotente:
- N-M5: skip se nf.separacao_id ja preenchido (NF ja processada).
- Erros sao logados e nao bloqueiam outras NFs (rollback por NF).

Estimativa: ~30 NFs orfas em prod (2026-05-12).

Padrao: rodar via `python scripts/migrations/motos_assai_23_backfill_nfs_orfas.py`.

Variaveis de ambiente:
- OPERADOR_ID: ID do usuario operador (default: 1, admin)
- DRY_RUN: 'true' para apenas listar sem mutar (default: false)
"""
import os
import sys
import logging

# sys.path para encontrar app modules quando rodando standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from app.motos_assai.models import AssaiNfQpa, NF_STATUS_NAO_RECONCILIADO  # noqa: E402
from app.motos_assai.services.separacao_service import (  # noqa: E402
    ajustar_separacao_pela_nf,
)


def main():
    operador_id = int(os.environ.get('OPERADOR_ID', '1'))
    dry_run = os.environ.get('DRY_RUN', 'false').lower() in ('true', '1', 'yes')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
    )
    logger = logging.getLogger(__name__)

    app = create_app()
    with app.app_context():
        nfs_orfas = AssaiNfQpa.query.filter_by(
            status_match=NF_STATUS_NAO_RECONCILIADO,
        ).order_by(AssaiNfQpa.importada_em).all()
        logger.info('[start] %d NFs orfas (NAO_RECONCILIADO)', len(nfs_orfas))
        if dry_run:
            logger.warning('[DRY_RUN=true] Apenas listando, NAO mutando estado')

        contadores = {
            'sucesso': 0,
            'sucesso_s1b': 0,
            'falhou': 0,
            'sem_chassi_cadastrado': 0,
            'ja_processada': 0,
            'sem_loja': 0,
            'ambiguidade': 0,
        }
        log_entries = []

        for nf in nfs_orfas:
            # N-M5 fix: idempotencia — se NF ja tem sep (parcialmente processada antes), skip
            if nf.separacao_id:
                contadores['ja_processada'] += 1
                log_entries.append(
                    f'  SKIP nf={nf.numero} chave_44={nf.chave_44[:10]}... '
                    f'— ja tem sep_id={nf.separacao_id}'
                )
                continue

            if dry_run:
                log_entries.append(
                    f'  DRY  nf={nf.numero} chave_44={nf.chave_44[:10]}... '
                    f'loja_id={nf.loja_id} (seria processada)'
                )
                continue

            try:
                result = ajustar_separacao_pela_nf(nf.id, operador_id=operador_id)
                if result['ok']:
                    db.session.commit()
                    if result.get('sep_criada_via_nf'):
                        contadores['sucesso_s1b'] += 1
                        log_entries.append(
                            f'  OK*  nf={nf.numero} -> sep_id={result["sep_alvo_id"]} '
                            f'(criada via S1=b, +{len(result["chassis_adicionados"])} chassi(s))'
                        )
                    else:
                        contadores['sucesso'] += 1
                        log_entries.append(
                            f'  OK   nf={nf.numero} -> sep_id={result["sep_alvo_id"]} '
                            f'(+{len(result["chassis_adicionados"])} chassi(s), '
                            f'-{len(result["chassis_removidos"])} chassi(s))'
                        )
                else:
                    db.session.rollback()  # garantir rollback de divergencias parciais
                    razao = result.get('razao', 'sem razao')
                    if 'nao cadastrado' in razao.lower() or result.get('chassis_desconhecidos'):
                        contadores['sem_chassi_cadastrado'] += 1
                        log_entries.append(
                            f'  SKIP nf={nf.numero} — chassis desconhecidos: '
                            f'{len(result.get("chassis_desconhecidos", []))}'
                        )
                    elif 'sem loja_id' in razao.lower():
                        contadores['sem_loja'] += 1
                        log_entries.append(f'  SKIP nf={nf.numero} — sem loja_id')
                    elif 'ambigu' in razao.lower():
                        contadores['ambiguidade'] += 1
                        log_entries.append(f'  SKIP nf={nf.numero} — ambiguidade: {razao}')
                    else:
                        contadores['falhou'] += 1
                        log_entries.append(f'  SKIP nf={nf.numero} — {razao}')
            except Exception as e:
                db.session.rollback()
                contadores['falhou'] += 1
                log_entries.append(f'  ERR  nf={nf.numero}: {e}')

        for line in log_entries:
            logger.info(line)

        logger.info('')
        logger.info('=' * 60)
        logger.info('[done]')
        logger.info('  sucesso (sep ja existia)  : %d', contadores['sucesso'])
        logger.info('  sucesso_s1b (sep criada)  : %d', contadores['sucesso_s1b'])
        logger.info('  ja_processada (idempotente): %d', contadores['ja_processada'])
        logger.info('  sem_chassi_cadastrado     : %d', contadores['sem_chassi_cadastrado'])
        logger.info('  sem_loja                  : %d', contadores['sem_loja'])
        logger.info('  ambiguidade               : %d', contadores['ambiguidade'])
        logger.info('  falhou (erro)             : %d', contadores['falhou'])
        logger.info('  TOTAL                     : %d', sum(contadores.values()))


if __name__ == '__main__':
    main()
