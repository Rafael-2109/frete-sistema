#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Migração 001: Corrigir razao_empresa_compradora em validacao_nf_po_dfe

Problema:
- 100% dos registros (181) em validacao_nf_po_dfe estão com razao_empresa_compradora = NULL
- Campo cnpj_empresa_compradora está preenchido em 93% dos registros

Solução:
- Usar mapeamento EMPRESAS_CNPJ_NOME de cnpj_utils.py para preencher razao_empresa_compradora
- baseado no cnpj_empresa_compradora existente

Evidência (produção 26/01/2026):
- total: 181
- sem_cnpj: 14 (7.7%)
- sem_razao: 181 (100%)

Uso:
    # Ambiente local (com .venv ativado)
    python scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.py

    # Dry-run (apenas mostra o que seria feito)
    python scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.py --dry-run
"""

import sys
import os
import argparse

# Adicionar path do projeto para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from datetime import datetime
from app.utils.timezone import agora_utc_naive


def main(dry_run: bool = False):
    """
    Executa correção de razao_empresa_compradora em validacao_nf_po_dfe.

    Args:
        dry_run: Se True, apenas mostra o que seria feito sem modificar o banco
    """
    # Importar dentro da função para evitar problemas de import circular
    from app import create_app, db
    from app.recebimento.models import ValidacaoNfPoDfe
    from app.utils.cnpj_utils import obter_nome_empresa, normalizar_cnpj

    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("MIGRAÇÃO 001: Corrigir razao_empresa_compradora em validacao_nf_po_dfe")
        print("=" * 70)
        print(f"Modo: {'DRY-RUN (simulação)' if dry_run else 'EXECUÇÃO REAL'}")
        print(f"Data: {agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S')}")
        print("-" * 70)

        # 1. Diagnóstico inicial
        total = ValidacaoNfPoDfe.query.count()
        sem_razao = ValidacaoNfPoDfe.query.filter(
            (ValidacaoNfPoDfe.razao_empresa_compradora == None) |
            (ValidacaoNfPoDfe.razao_empresa_compradora == '')
        ).count()
        com_cnpj_sem_razao = ValidacaoNfPoDfe.query.filter(
            (ValidacaoNfPoDfe.razao_empresa_compradora == None) |
            (ValidacaoNfPoDfe.razao_empresa_compradora == ''),
            ValidacaoNfPoDfe.cnpj_empresa_compradora != None,
            ValidacaoNfPoDfe.cnpj_empresa_compradora != ''
        ).count()

        print(f"DIAGNÓSTICO INICIAL:")
        print(f"  - Total de registros: {total}")
        print(f"  - Sem razao_empresa_compradora: {sem_razao} ({sem_razao/total*100:.1f}%)" if total > 0 else "  - Sem razao_empresa_compradora: 0")
        print(f"  - Com CNPJ mas sem razão: {com_cnpj_sem_razao}")
        print("-" * 70)

        if com_cnpj_sem_razao == 0:
            print("✓ Nenhum registro para corrigir. Saindo.")
            return

        # 2. Buscar registros para corrigir
        registros = ValidacaoNfPoDfe.query.filter(
            (ValidacaoNfPoDfe.razao_empresa_compradora == None) |
            (ValidacaoNfPoDfe.razao_empresa_compradora == ''),
            ValidacaoNfPoDfe.cnpj_empresa_compradora != None,
            ValidacaoNfPoDfe.cnpj_empresa_compradora != ''
        ).all()

        print(f"CORREÇÃO:")
        print(f"  Registros a processar: {len(registros)}")
        print()

        corrigidos = 0
        nao_mapeados = 0
        cnpjs_sem_mapeamento = set()

        for registro in registros:
            cnpj_normalizado = normalizar_cnpj(registro.cnpj_empresa_compradora)
            razao = obter_nome_empresa(cnpj_normalizado)

            if razao:
                if dry_run:
                    print(f"  [DRY-RUN] ID {registro.id}: CNPJ {cnpj_normalizado} -> '{razao}'")
                else:
                    registro.razao_empresa_compradora = razao
                corrigidos += 1
            else:
                cnpjs_sem_mapeamento.add(cnpj_normalizado)
                nao_mapeados += 1

        if not dry_run and corrigidos > 0:
            try:
                db.session.commit()
                print(f"\n✓ COMMIT realizado com sucesso!")
            except Exception as e:
                db.session.rollback()
                print(f"\n✗ ERRO ao commitar: {e}")
                return

        print("-" * 70)
        print(f"RESULTADO:")
        print(f"  - Registros corrigidos: {corrigidos}")
        print(f"  - Registros sem mapeamento: {nao_mapeados}")

        if cnpjs_sem_mapeamento:
            print(f"\n⚠ CNPJs SEM MAPEAMENTO (adicionar em cnpj_utils.py):")
            for cnpj in sorted(cnpjs_sem_mapeamento):
                print(f"    '{cnpj}': 'NOME_DA_EMPRESA',")

        # 3. Diagnóstico final
        if not dry_run:
            sem_razao_final = ValidacaoNfPoDfe.query.filter(
                (ValidacaoNfPoDfe.razao_empresa_compradora == None) |
                (ValidacaoNfPoDfe.razao_empresa_compradora == '')
            ).count()

            print("-" * 70)
            print(f"DIAGNÓSTICO FINAL:")
            print(f"  - Sem razao_empresa_compradora: {sem_razao_final}")
            print(f"  - Redução: {sem_razao - sem_razao_final} registros corrigidos")

        print("=" * 70)
        print("Migração concluída!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Corrige razao_empresa_compradora em validacao_nf_po_dfe'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Apenas mostra o que seria feito, sem modificar o banco'
    )

    args = parser.parse_args()
    main(dry_run=args.dry_run)
