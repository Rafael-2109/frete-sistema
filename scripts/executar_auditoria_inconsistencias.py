"""
Executar auditoria de inconsistencias Odoo (Receber + Pagar).

Detecta divergencias entre dados locais e Odoo para contas a receber
e/ou contas a pagar, usando os services existentes.

Uso:
    # Dry run (apenas lista, sem gravar flags)
    python scripts/executar_auditoria_inconsistencias.py --dry-run

    # Executar de verdade (grava flags no banco)
    python scripts/executar_auditoria_inconsistencias.py

    # Apenas contas a pagar, empresa CD
    python scripts/executar_auditoria_inconsistencias.py --tipo pagar --empresa 3

    # Apenas contas a receber, todas as empresas
    python scripts/executar_auditoria_inconsistencias.py --tipo receber

Flags:
    --empresa   Filtrar por empresa (1=FB, 2=SC, 3=CD). Default: todas.
    --dry-run   Apenas lista inconsistencias sem gravar no banco.
    --tipo      receber, pagar ou ambos (default: ambos).
    --todos     Verificar TODOS os titulos com odoo_line_id (default: apenas pagos).
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

EMPRESAS = {1: 'FB', 2: 'SC', 3: 'CD'}


def parse_args():
    parser = argparse.ArgumentParser(
        description='Auditoria de inconsistencias Odoo (Receber + Pagar)',
    )
    parser.add_argument(
        '--empresa',
        type=int,
        choices=[1, 2, 3],
        default=None,
        help='Filtrar por empresa: 1=FB, 2=SC, 3=CD (default: todas)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='Apenas lista inconsistencias sem gravar no banco',
    )
    parser.add_argument(
        '--tipo',
        choices=['receber', 'pagar', 'ambos'],
        default='ambos',
        help='Tipo de auditoria: receber, pagar ou ambos (default: ambos)',
    )
    parser.add_argument(
        '--todos',
        action='store_true',
        default=False,
        help='Verificar TODOS os titulos com odoo_line_id (default: apenas pagos)',
    )
    return parser.parse_args()


def imprimir_resultado(label: str, resultado: dict):
    """Imprime resultado de um service de auditoria."""
    print(f'\n{"=" * 60}')
    print(f'  {label}')
    print(f'{"=" * 60}')
    print(f'  Sucesso:          {resultado.get("sucesso", "?")}')
    print(f'  Dry run:          {resultado.get("dry_run", "?")}')
    print(f'  Verificados:      {resultado.get("total_verificados", 0)}')
    print(f'  Detectadas:       {resultado.get("inconsistencias_detectadas", 0)}')
    print(f'  Limpas:           {resultado.get("inconsistencias_limpas", 0)}')
    print(f'  Sem match Odoo:   {resultado.get("sem_match_odoo", 0)}')
    print(f'  Erros de batch:   {resultado.get("erros_batch", 0)}')
    print(f'  Duracao:          {resultado.get("duracao_segundos", 0)}s')

    detalhes = resultado.get('detalhes_por_tipo', {})
    if detalhes:
        print(f'\n  Detalhes por tipo:')
        for tipo, qtd in sorted(detalhes.items(), key=lambda x: -x[1]):
            print(f'    {tipo}: {qtd}')


def imprimir_resumo(resultados: dict):
    """Imprime resumo consolidado de todos os resultados."""
    print(f'\n{"=" * 60}')
    print(f'  RESUMO CONSOLIDADO')
    print(f'{"=" * 60}')

    total_verificados = 0
    total_detectadas = 0
    total_limpas = 0
    total_erros = 0

    for label, res in resultados.items():
        total_verificados += res.get('total_verificados', 0)
        total_detectadas += res.get('inconsistencias_detectadas', 0)
        total_limpas += res.get('inconsistencias_limpas', 0)
        total_erros += res.get('erros_batch', 0)

    print(f'  Total verificados:      {total_verificados}')
    print(f'  Total detectadas:       {total_detectadas}')
    print(f'  Total limpas:           {total_limpas}')
    print(f'  Total erros de batch:   {total_erros}')
    print(f'{"=" * 60}\n')


def main():
    args = parse_args()

    empresa_label = EMPRESAS.get(args.empresa, 'TODAS')
    modo = 'DRY RUN' if args.dry_run else 'EXECUCAO REAL'
    apenas_pagos = not args.todos
    escopo = 'TODOS com odoo_line_id' if args.todos else 'APENAS PAGOS'

    print(f'\n  Auditoria de Inconsistencias Odoo')
    print(f'  Empresa: {empresa_label} | Tipo: {args.tipo} | Modo: {modo}')
    print(f'  Escopo: {escopo}')
    print(f'  {"-" * 50}')

    from app import create_app
    app = create_app()

    resultados = {}

    with app.app_context():
        if args.tipo in ('receber', 'ambos'):
            print(f'\n  Executando auditoria CONTAS A RECEBER...')
            from app.financeiro.services.auditoria_inconsistencias_service import (
                AuditoriaInconsistenciasService,
            )
            service_receber = AuditoriaInconsistenciasService()
            resultado_receber = service_receber.detectar_inconsistencias(
                empresa=args.empresa,
                dry_run=args.dry_run,
                apenas_pagos=apenas_pagos,
            )
            resultados['Contas a Receber'] = resultado_receber
            imprimir_resultado('CONTAS A RECEBER', resultado_receber)

        if args.tipo in ('pagar', 'ambos'):
            print(f'\n  Executando auditoria CONTAS A PAGAR...')
            from app.financeiro.services.auditoria_inconsistencias_pagar_service import (
                AuditoriaInconsistenciasPagarService,
            )
            service_pagar = AuditoriaInconsistenciasPagarService()
            resultado_pagar = service_pagar.detectar_inconsistencias(
                empresa=args.empresa,
                dry_run=args.dry_run,
                apenas_pagos=apenas_pagos,
            )
            resultados['Contas a Pagar'] = resultado_pagar
            imprimir_resultado('CONTAS A PAGAR', resultado_pagar)

        if len(resultados) > 1:
            imprimir_resumo(resultados)


if __name__ == '__main__':
    main()
