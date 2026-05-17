"""F7.2 — Carrega planilha do inventario fisico em /tmp.

Formato esperado:
- 1 aba por company: FB, CD, LF
- Header na linha 1
- Colunas (na ordem): cod_produto, nome, lote, qtd_contada
  (colunas adicionais sao ignoradas)

Validacoes:
- cod_produto deve comecar com 1, 2, 3 ou 4 (P002)
- qtd_contada >= 0
- abas FB/CD/LF obrigatorias (faltantes geram erro)

Uso:
    python scripts/inventario_2026_05/02_carregar_inventario_xlsx.py \\
        --xlsx ~/Downloads/inventario_2026_05.xlsx [--dry-run]

Spec: docs/superpowers/plans/2026-05-17-ajuste-inventario-nacom-lf.md Task 7.2
"""
import argparse
import json
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

# sys.path para `from app import ...`
_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

import openpyxl  # noqa: E402

from app import create_app  # noqa: E402
from app.utils.timezone import agora_utc_naive  # noqa: E402

CODIGO_PARA_COMPANY_ID = {'FB': 1, 'CD': 4, 'LF': 5}
TIPOS_ACEITOS = {'1', '2', '3', '4'}
OUTPUT_JSON = '/tmp/inventario_fisico_2026_05.json'


def carregar_xlsx(path: str) -> dict:
    """Le planilha + valida. Retorna dict {timestamp, origem, companies, erros}."""
    wb = openpyxl.load_workbook(path, data_only=True)
    result = {
        'timestamp': agora_utc_naive().isoformat(),
        'origem': path,
        'companies': {},
    }
    erros = []

    for codigo, cid in CODIGO_PARA_COMPANY_ID.items():
        if codigo not in wb.sheetnames:
            erros.append(f'Sheet {codigo!r} ausente em {path}')
            continue
        ws = wb[codigo]
        linhas = []
        for idx, row in enumerate(
            ws.iter_rows(min_row=2, values_only=True), start=2
        ):
            if not row or all(c is None for c in row):
                continue
            # Pega 4 primeiras colunas (extra ignorada)
            padded = (list(row) + [None] * 4)[:4]
            cod, nome, lote, qtd = padded

            cod = str(cod).strip() if cod is not None else ''
            if not cod:
                erros.append(f'{codigo} linha {idx}: cod_produto vazio')
                continue
            if cod[0] not in TIPOS_ACEITOS:
                erros.append(
                    f'{codigo} linha {idx}: cod_produto {cod!r} '
                    'nao comeca com 1-4'
                )
                continue
            try:
                qtd_dec = Decimal(str(qtd)) if qtd is not None else Decimal('0')
            except (InvalidOperation, ValueError):
                erros.append(
                    f'{codigo} linha {idx}: qtd_contada nao numerica '
                    f'({qtd!r})'
                )
                continue
            if qtd_dec < 0:
                erros.append(
                    f'{codigo} linha {idx}: qtd_contada negativa '
                    f'({qtd_dec})'
                )
                continue

            linhas.append({
                'cod_produto': cod,
                'nome': str(nome).strip() if nome else '',
                'lote_inventariado': str(lote).strip() if lote else '',
                'qtd_inventario': str(qtd_dec),
                'tipo_produto': int(cod[0]),
            })
        result['companies'][cid] = {'codigo': codigo, 'linhas': linhas}
        print(f'  {codigo}: {len(linhas)} linhas validas')

    if erros:
        print(f'\nERROS ({len(erros)}):')
        for e in erros[:20]:
            print(f'  - {e}')
        if len(erros) > 20:
            print(f'  ... +{len(erros) - 20} erros adicionais')
        result['erros'] = erros
    return result


def main(path: str, dry_run: bool) -> None:
    app = create_app()
    with app.app_context():
        if not os.path.exists(path):
            raise FileNotFoundError(f'Planilha nao encontrada: {path}')

        result = carregar_xlsx(path)

        if result.get('erros') and not dry_run:
            print(
                '\nABORTANDO: ha erros de validacao. Corrija a planilha '
                'e rode novamente. (Use --dry-run para gerar parcial.)'
            )
            sys.exit(2)

        if not dry_run:
            with open(OUTPUT_JSON, 'w') as f:
                json.dump(result, f, default=str, indent=2)
            print(f'\nSnapshot: {OUTPUT_JSON}')
        else:
            print(f'\n[DRY RUN] nao gravou {OUTPUT_JSON}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--xlsx', required=True,
        help='caminho do .xlsx do inventario fisico',
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='nao grava JSON; apenas valida e imprime estatisticas',
    )
    args = parser.parse_args()
    main(args.xlsx, args.dry_run)
