#!/usr/bin/env python3
"""
Auditoria 100% contas_a_receber — Correções baseadas em cruzamento Local × Odoo
================================================================================

CONTEXTO:
Auditoria cruzou 19,291 registros locais com 39,790 do Odoo (21/02/2026).
Match rate: 99.4% (19,177 matches).

CORREÇÕES APLICADAS (baseadas em dados REAIS do cruzamento):
1. odoo_line_id:          1,234 registros sem ID que encontraram match por (empresa, NF, parcela)
2. valor_residual:        13,962 registros NULL → abs(amount_residual) do Odoo
3. parcela_paga:          860 registros False→True (Odoo mostra amount_residual=0)
4. status_pagamento_odoo: 7,636 registros com valor diferente do Odoo

NÃO ALTERADOS (flagados para revisão manual):
- 123 registros com parcela_paga=True local mas Odoo mostra aberto
  (70 ODOO_DIRETO + 53 CNAB, todos empresa CD)
- 114 registros sem match no Odoo (NFs antigas/canceladas)

FORMATO DO ARQUIVO COMPANION (auditoria_contas_receber_correcoes.json):
  Array de arrays: [id, novo_line_id|null, novo_valor_residual|null, set_paga(0/1), novo_status|null]

Executar:
    source .venv/bin/activate
    python scripts/migrations/auditoria_contas_receber_vs_odoo.py              # dry-run
    python scripts/migrations/auditoria_contas_receber_vs_odoo.py --execute    # executa
    python scripts/migrations/auditoria_contas_receber_vs_odoo.py --verify-only

Data: 21/02/2026
"""

import sys
import os
import argparse
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Arquivo companion: mesmo diretório que este script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CORRECOES_COMPANION = os.path.join(SCRIPT_DIR, 'auditoria_contas_receber_correcoes.json')

BATCH_SIZE = 200


def carregar_correcoes() -> list:
    """
    Carrega correções do arquivo companion (formato compacto).

    Formato: [[id, line_id|null, valor_residual|null, set_paga(0/1), status|null], ...]
    """
    if not os.path.exists(CORRECOES_COMPANION):
        raise FileNotFoundError(
            f"Arquivo companion não encontrado: {CORRECOES_COMPANION}\n"
            f"O arquivo deve estar no mesmo diretório deste script."
        )

    with open(CORRECOES_COMPANION) as f:
        raw = json.load(f)

    # Converter formato compacto → dicts
    correcoes = []
    for rec in raw:
        local_id, line_id, valor_residual, set_paga, status = rec

        c = {'local_id': local_id}
        tem_algo = False

        if line_id is not None:
            c['line_id'] = line_id
            tem_algo = True

        if valor_residual is not None:
            c['valor_residual'] = valor_residual
            tem_algo = True

        if set_paga == 1:
            c['set_paga'] = True
            tem_algo = True

        if status is not None:
            c['status'] = status
            tem_algo = True

        if tem_algo:
            correcoes.append(c)

    logger.info(f"Carregadas {len(correcoes)} correções de {CORRECOES_COMPANION}")
    return correcoes


def aplicar_correcoes(correcoes: list, dry_run: bool = True) -> dict:
    """
    Aplica correções ao banco de dados.

    Padrão detach-first:
    - Correções pré-calculadas (sem leitura DB)
    - Updates por batch de 200 com commit + close
    """
    stats = {
        'total_correcoes': len(correcoes),
        'line_id_atribuidos': sum(1 for c in correcoes if 'line_id' in c),
        'valor_residual_atualizados': sum(1 for c in correcoes if 'valor_residual' in c),
        'parcela_paga_corrigidos': sum(1 for c in correcoes if c.get('set_paga')),
        'status_atualizados': sum(1 for c in correcoes if 'status' in c),
        'erros': 0,
        'batches_processados': 0,
    }

    logger.info("=" * 60)
    logger.info("APLICAÇÃO DE CORREÇÕES — CONTAS A RECEBER")
    logger.info("=" * 60)
    logger.info(f"Total correções: {stats['total_correcoes']}")
    logger.info(f"  odoo_line_id:         {stats['line_id_atribuidos']}")
    logger.info(f"  valor_residual:       {stats['valor_residual_atualizados']}")
    logger.info(f"  parcela_paga:         {stats['parcela_paga_corrigidos']}")
    logger.info(f"  status_pagamento:     {stats['status_atualizados']}")
    logger.info(f"  Batch size:           {BATCH_SIZE}")
    logger.info(f"  Modo:                 {'DRY-RUN' if dry_run else 'EXECUÇÃO'}")

    if dry_run:
        logger.info("\nDRY-RUN: Nenhuma alteração será aplicada.")
        return stats

    total_batches = (len(correcoes) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(correcoes), BATCH_SIZE):
        batch = correcoes[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        try:
            for c in batch:
                sets = []
                params = {'id': c['local_id']}

                if 'line_id' in c:
                    sets.append('odoo_line_id = :novo_line_id')
                    params['novo_line_id'] = c['line_id']

                if 'valor_residual' in c:
                    sets.append('valor_residual = :novo_vr')
                    params['novo_vr'] = c['valor_residual']

                if c.get('set_paga'):
                    sets.append('parcela_paga = TRUE')
                    sets.append("metodo_baixa = COALESCE(metodo_baixa, 'ODOO_DIRETO')")

                if 'status' in c:
                    sets.append('status_pagamento_odoo = :novo_status')
                    params['novo_status'] = c['status']

                sets.append("atualizado_em = NOW()")
                sets.append("atualizado_por = 'Auditoria Odoo 2026-02-21'")

                if sets:
                    sql = f"UPDATE contas_a_receber SET {', '.join(sets)} WHERE id = :id"
                    db.session.execute(text(sql), params)

            db.session.commit()
            stats['batches_processados'] += 1

            if batch_num % 10 == 0 or batch_num == total_batches:
                logger.info(
                    f"  Batch {batch_num}/{total_batches}: "
                    f"{len(batch)} updates (total: {i + len(batch)})"
                )

        except Exception as e:
            db.session.rollback()
            logger.error(f"  ERRO batch {batch_num}: {e}")
            stats['erros'] += len(batch)
        finally:
            db.session.close()

    return stats


def verificar_resultado():
    """Executa queries de verificação pós-correção."""
    logger.info("\n" + "=" * 60)
    logger.info("VERIFICAÇÃO PÓS-CORREÇÃO")
    logger.info("=" * 60)

    queries = [
        (
            "Sem odoo_line_id",
            "SELECT COUNT(*) FROM contas_a_receber WHERE odoo_line_id IS NULL"
        ),
        (
            "Sem valor_residual",
            "SELECT COUNT(*) FROM contas_a_receber WHERE valor_residual IS NULL"
        ),
        (
            "paid + parcela_paga=False",
            "SELECT COUNT(*) FROM contas_a_receber "
            "WHERE status_pagamento_odoo = 'paid' AND parcela_paga = false"
        ),
        (
            "parcela_paga=True + status NOT IN (paid,reversed)",
            "SELECT COUNT(*) FROM contas_a_receber "
            "WHERE parcela_paga = true "
            "AND (status_pagamento_odoo IS NULL "
            "OR status_pagamento_odoo NOT IN ('paid', 'reversed'))"
        ),
    ]

    for label, sql in queries:
        try:
            result = db.session.execute(text(sql)).scalar()
            logger.info(f"  {label}: {result}")
        except Exception as e:
            logger.error(f"  {label}: ERRO - {e}")
        finally:
            db.session.close()


def main():
    parser = argparse.ArgumentParser(
        description='Auditoria contas_a_receber × Odoo — Script de correção'
    )
    parser.add_argument(
        '--execute', action='store_true',
        help='Executar as alterações (default: dry-run)'
    )
    parser.add_argument(
        '--verify-only', action='store_true',
        help='Apenas executar queries de verificação'
    )
    args = parser.parse_args()

    dry_run = not args.execute

    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("AUDITORIA contas_a_receber × Odoo — SCRIPT DE CORREÇÃO")
        print("=" * 70)

        if args.verify_only:
            print("\nMODO VERIFICAÇÃO\n")
            verificar_resultado()
            return

        if dry_run:
            print("\nMODO DRY-RUN: Nenhuma alteração será salva")
        else:
            print("\nMODO EXECUÇÃO: As alterações serão salvas no banco!")

        print()

        # Carregar correções
        correcoes = carregar_correcoes()

        # Aplicar
        stats = aplicar_correcoes(correcoes, dry_run=dry_run)

        # Relatório final
        print("\n" + "=" * 70)
        print("RELATÓRIO FINAL")
        print("=" * 70)
        print(f"  Correções processadas: {stats['total_correcoes']}")
        print(f"  odoo_line_id:          {stats['line_id_atribuidos']}")
        print(f"  valor_residual:        {stats['valor_residual_atualizados']}")
        print(f"  parcela_paga:          {stats['parcela_paga_corrigidos']}")
        print(f"  status_pagamento:      {stats['status_atualizados']}")
        print(f"  Batches processados:   {stats['batches_processados']}")
        print(f"  Erros:                 {stats['erros']}")

        # Verificação pós-correção
        if not dry_run:
            verificar_resultado()

        if dry_run:
            print("\nDRY-RUN: Nenhuma alteração foi aplicada.")
            print("Execute com --execute para aplicar as mudanças.")
        else:
            ok = stats['total_correcoes'] - stats['erros']
            print(f"\n{ok} correções aplicadas com sucesso.")

        print("\nITENS PARA REVISÃO MANUAL:")
        print("  114 registros sem match no Odoo (NFs antigas/canceladas)")
        print("  123 registros local=pago, Odoo=aberto (70 ODOO_DIRETO + 53 CNAB)")


if __name__ == '__main__':
    main()
