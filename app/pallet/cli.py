#!/usr/bin/env python3
"""
CLI para Emissão de NF de Pallet
================================

Uso:
    python -m app.pallet.cli --empresa CD --cliente 88586 --transportadora 1208 --quantidade 17
    python -m app.pallet.cli --empresa FB --cliente 12345 --transportadora 1208 --quantidade 10 --dry-run

Autor: Sistema de Fretes
Data: 02/01/2026
"""

import sys
import os
import argparse
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.pallet.services.emissao_nf_pallet import emitir_nf_pallet, PRODUTO_PALLET


def main():
    parser = argparse.ArgumentParser(
        description='Emite NF de Pallet no Odoo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Emitir NF de 17 pallets para cliente 88586 com transportadora 1208 na empresa CD
  python -m app.pallet.cli --empresa CD --cliente 88586 --transportadora 1208 --quantidade 17

  # Simular sem criar registros (dry-run)
  python -m app.pallet.cli --empresa FB --cliente 12345 --transportadora 1208 --quantidade 10 --dry-run

  # Saída em JSON
  python -m app.pallet.cli --empresa SC --cliente 99999 --transportadora 1208 --quantidade 5 --json

Empresas disponíveis:
  CD - NACOM GOYA - CD (Centro de Distribuição)
  FB - NACOM GOYA - FB (Fábrica)
  SC - NACOM GOYA - SC (Santa Catarina)
        """
    )

    parser.add_argument('--empresa', required=True, choices=['CD', 'FB', 'SC'],
                        help='Código da empresa (CD, FB ou SC)')
    parser.add_argument('--cliente', required=True, type=int,
                        help='ID do cliente no Odoo (res.partner)')
    parser.add_argument('--transportadora', required=True, type=int,
                        help='ID da transportadora no Odoo (delivery.carrier)')
    parser.add_argument('--quantidade', required=True, type=int,
                        help='Quantidade de pallets')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simula a operação sem criar registros')
    parser.add_argument('--json', action='store_true',
                        help='Saída em formato JSON')

    args = parser.parse_args()

    # Executar
    resultado = emitir_nf_pallet(
        empresa=args.empresa,
        cliente_id=args.cliente,
        transportadora_id=args.transportadora,
        quantidade=args.quantidade,
        dry_run=args.dry_run
    )

    # Saída
    if args.json:
        print(json.dumps(resultado, indent=2, default=str, ensure_ascii=False))
    else:
        print("\n" + "=" * 60)
        print("EMISSÃO DE NF DE PALLET")
        print("=" * 60)
        print(f"Empresa: {resultado.get('config', {}).get('company_name', args.empresa)}")
        print(f"Cliente: {resultado.get('cliente', {}).get('name', args.cliente)}")
        print(f"Transportadora: {resultado.get('transportadora', {}).get('name', args.transportadora)}")
        print(f"Quantidade: {args.quantidade} pallets")
        print(f"Valor Total: R$ {args.quantidade * PRODUTO_PALLET['price_unit']:.2f}")
        print("-" * 60)

        print("\nETAPAS:")
        for etapa in resultado.get('etapas', []):
            print(f"  - {etapa}")

        if resultado['sucesso']:
            print("\n" + "-" * 60)
            print("RESULTADO:")

            if resultado.get('picking'):
                picking = resultado['picking']
                if not picking.get('simulado'):
                    print(f"  Picking: {picking.get('name', 'N/A')}")
                    print(f"  Status: {picking.get('state', 'N/A')}")

            if resultado.get('fatura'):
                fatura = resultado['fatura']
                if not fatura.get('simulado'):
                    print(f"  Fatura: {fatura.get('name', 'N/A')}")
                    print(f"  NF-e: {fatura.get('l10n_br_numero_nota_fiscal', 'N/A')}")
                    print(f"  Situação: {fatura.get('l10n_br_situacao_nf', 'N/A')}")
                    if fatura.get('l10n_br_chave_nf'):
                        print(f"  Chave: {fatura['l10n_br_chave_nf']}")
        else:
            print(f"\nERRO: {resultado.get('erro', 'Erro desconhecido')}")

        print("\n" + "=" * 60)

    # Exit code
    sys.exit(0 if resultado['sucesso'] else 1)


if __name__ == '__main__':
    main()
