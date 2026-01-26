#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Migração 002: Corrigir dados em cadastro_primeira_compra

Problemas:
1. 100% dos registros (345) estão com cnpj_empresa_compradora vazio
2. 100% dos registros (345) estão com razao_empresa_compradora vazio
3. 100% dos registros (345) têm cod_produto = product_id (numérico) ao invés de default_code

Solução:
1. Buscar cnpj_empresa_compradora do DFE no Odoo (nfe_infnfe_dest_cnpj)
2. Preencher razao_empresa_compradora via mapeamento EMPRESAS_CNPJ_NOME
3. Converter cod_produto de product_id para default_code via consulta Odoo em batch

Evidência (produção 26/01/2026):
- total: 345
- sem_cnpj: 345 (100%)
- sem_razao: 345 (100%)
- cod_produto é product_id: 100% (range 27656 a 36957)

Uso:
    # Ambiente local (com .venv ativado)
    python scripts/recebimento/002_corrigir_primeira_compra.py

    # Dry-run (apenas mostra o que seria feito)
    python scripts/recebimento/002_corrigir_primeira_compra.py --dry-run

    # Apenas corrigir CNPJ/razão (sem converter cod_produto)
    python scripts/recebimento/002_corrigir_primeira_compra.py --skip-produto

    # Apenas corrigir cod_produto (sem CNPJ/razão)
    python scripts/recebimento/002_corrigir_primeira_compra.py --only-produto

IMPORTANTE:
- Este script requer conexão com Odoo para buscar dados do DFE e converter product_id
- Executar em horário de baixa carga (muitas requisições ao Odoo)
- Fazer backup do banco antes de executar em produção
"""

import sys
import os
import argparse
from typing import Dict, List, Set

# Adicionar path do projeto para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from datetime import datetime


def buscar_dfes_odoo(dfe_ids: List[int], conn) -> Dict[int, Dict]:
    """
    Busca dados dos DFEs no Odoo em batch.

    Args:
        dfe_ids: Lista de IDs de DFEs para buscar
        conn: Conexão com Odoo

    Returns:
        Dict[dfe_id, {'cnpj': str, ...}]
    """
    if not dfe_ids:
        return {}

    campos = [
        'id',
        'nfe_infnfe_dest_cnpj',  # CNPJ da empresa compradora
        'company_id',            # Para debug
    ]

    try:
        dfes = conn.search_read(
            'l10n_br_fiscal.document',
            [('id', 'in', dfe_ids)],
            campos
        )

        resultado = {}
        for dfe in dfes:
            cnpj = dfe.get('nfe_infnfe_dest_cnpj') or ''
            # Normalizar CNPJ (remover formatação)
            cnpj_limpo = ''.join(c for c in cnpj if c.isdigit())
            if cnpj_limpo and len(cnpj_limpo) < 14:
                cnpj_limpo = cnpj_limpo.zfill(14)

            resultado[dfe['id']] = {
                'cnpj': cnpj_limpo,
                'company_id': dfe.get('company_id', [None, ''])[0] if isinstance(dfe.get('company_id'), list) else dfe.get('company_id'),
            }

        return resultado

    except Exception as e:
        print(f"  ⚠ Erro ao buscar DFEs no Odoo: {e}")
        return {}


def buscar_default_codes_odoo(product_ids: List[int], conn) -> Dict[int, str]:
    """
    Busca default_code de produtos no Odoo em batch.

    Args:
        product_ids: Lista de IDs de produtos
        conn: Conexão com Odoo

    Returns:
        Dict[product_id, default_code]
    """
    if not product_ids:
        return {}

    try:
        produtos = conn.search_read(
            'product.product',
            [('id', 'in', product_ids)],
            ['id', 'default_code', 'name']
        )

        resultado = {}
        for prod in produtos:
            default_code = prod.get('default_code')
            if default_code:
                resultado[prod['id']] = default_code

        return resultado

    except Exception as e:
        print(f"  ⚠ Erro ao buscar produtos no Odoo: {e}")
        return {}


def main(dry_run: bool = False, skip_produto: bool = False, only_produto: bool = False):
    """
    Executa correção de dados em cadastro_primeira_compra.

    Args:
        dry_run: Se True, apenas mostra o que seria feito sem modificar o banco
        skip_produto: Se True, não converte cod_produto
        only_produto: Se True, apenas converte cod_produto (ignora CNPJ/razão)
    """
    # Importar dentro da função para evitar problemas de import circular
    from app import create_app, db
    from app.recebimento.models import CadastroPrimeiraCompra
    from app.utils.cnpj_utils import obter_nome_empresa
    from app.odoo.utils.connection import get_odoo_connection

    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("MIGRAÇÃO 002: Corrigir dados em cadastro_primeira_compra")
        print("=" * 70)
        print(f"Modo: {'DRY-RUN (simulação)' if dry_run else 'EXECUÇÃO REAL'}")
        print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"Opções: skip_produto={skip_produto}, only_produto={only_produto}")
        print("-" * 70)

        # 1. Diagnóstico inicial
        total = CadastroPrimeiraCompra.query.count()
        sem_cnpj = CadastroPrimeiraCompra.query.filter(
            (CadastroPrimeiraCompra.cnpj_empresa_compradora == None) |
            (CadastroPrimeiraCompra.cnpj_empresa_compradora == '')
        ).count()
        sem_razao = CadastroPrimeiraCompra.query.filter(
            (CadastroPrimeiraCompra.razao_empresa_compradora == None) |
            (CadastroPrimeiraCompra.razao_empresa_compradora == '')
        ).count()

        # Verificar cod_produto numérico (product_id)
        # Se cod_produto é apenas dígitos, provavelmente é product_id
        registros_cod_numerico = CadastroPrimeiraCompra.query.filter(
            CadastroPrimeiraCompra.cod_produto.op('~')('^[0-9]+$')
        ).count()

        print(f"DIAGNÓSTICO INICIAL:")
        print(f"  - Total de registros: {total}")
        print(f"  - Sem cnpj_empresa_compradora: {sem_cnpj} ({sem_cnpj/total*100:.1f}%)" if total > 0 else "  - Sem cnpj_empresa_compradora: 0")
        print(f"  - Sem razao_empresa_compradora: {sem_razao} ({sem_razao/total*100:.1f}%)" if total > 0 else "  - Sem razao_empresa_compradora: 0")
        print(f"  - cod_produto numérico (provavelmente product_id): {registros_cod_numerico}")
        print("-" * 70)

        if total == 0:
            print("✓ Nenhum registro para corrigir. Saindo.")
            return

        # 2. Conectar ao Odoo
        print("Conectando ao Odoo...")
        try:
            conn = get_odoo_connection()
            print(f"  ✓ Conectado ao Odoo")
        except Exception as e:
            print(f"  ✗ Erro ao conectar ao Odoo: {e}")
            print("  Algumas correções requerem dados do Odoo. Abortando.")
            return

        # 3. Buscar todos os registros para processar
        registros = CadastroPrimeiraCompra.query.all()

        # Coletar IDs únicos para buscar no Odoo em batch
        dfe_ids: Set[int] = set()
        product_ids_para_converter: Set[int] = set()

        for reg in registros:
            # Coletar DFE IDs para buscar CNPJ
            if not only_produto:
                if not reg.cnpj_empresa_compradora:
                    try:
                        dfe_id = int(reg.odoo_dfe_id)
                        dfe_ids.add(dfe_id)
                    except (ValueError, TypeError):
                        pass

            # Coletar product_ids para converter
            if not skip_produto and reg.cod_produto:
                try:
                    # Se cod_produto é numérico, pode ser product_id
                    product_id = int(reg.cod_produto)
                    if product_id > 0:
                        product_ids_para_converter.add(product_id)
                except ValueError:
                    # cod_produto já é alfanumérico (default_code), ignorar
                    pass

        print(f"\nBUSCAS NO ODOO:")
        print(f"  - DFEs para buscar CNPJ: {len(dfe_ids)}")
        print(f"  - Produtos para converter cod: {len(product_ids_para_converter)}")

        # 4. Buscar dados do Odoo em batch
        dfe_data: Dict[int, Dict] = {}
        product_codes: Dict[int, str] = {}

        if dfe_ids and not only_produto:
            print(f"\nBuscando DFEs no Odoo (batch de {len(dfe_ids)})...")
            dfe_data = buscar_dfes_odoo(list(dfe_ids), conn)
            print(f"  ✓ Obtidos dados de {len(dfe_data)} DFEs")

        if product_ids_para_converter and not skip_produto:
            print(f"\nBuscando default_codes no Odoo (batch de {len(product_ids_para_converter)})...")
            product_codes = buscar_default_codes_odoo(list(product_ids_para_converter), conn)
            print(f"  ✓ Obtidos {len(product_codes)} códigos de produtos")

        # 5. Processar registros
        print(f"\nPROCESSAMENTO:")

        cnpj_corrigidos = 0
        razao_corrigidas = 0
        cod_convertidos = 0
        erros = []

        for reg in registros:
            # 5a. Corrigir CNPJ
            if not only_produto and not reg.cnpj_empresa_compradora:
                try:
                    dfe_id = int(reg.odoo_dfe_id)
                    if dfe_id in dfe_data:
                        cnpj = dfe_data[dfe_id].get('cnpj')
                        if cnpj:
                            if dry_run:
                                print(f"  [DRY-RUN] ID {reg.id}: cnpj -> {cnpj}")
                            else:
                                reg.cnpj_empresa_compradora = cnpj
                            cnpj_corrigidos += 1
                except (ValueError, TypeError):
                    pass

            # 5b. Corrigir razão (depois do CNPJ, pois depende dele)
            if not only_produto:
                cnpj_atual = reg.cnpj_empresa_compradora
                if cnpj_atual and not reg.razao_empresa_compradora:
                    razao = obter_nome_empresa(cnpj_atual)
                    if razao:
                        if dry_run:
                            print(f"  [DRY-RUN] ID {reg.id}: razao -> {razao}")
                        else:
                            reg.razao_empresa_compradora = razao
                        razao_corrigidas += 1

            # 5c. Converter cod_produto
            if not skip_produto and reg.cod_produto:
                try:
                    product_id = int(reg.cod_produto)
                    if product_id in product_codes:
                        novo_codigo = product_codes[product_id]
                        if dry_run:
                            print(f"  [DRY-RUN] ID {reg.id}: cod_produto {reg.cod_produto} -> {novo_codigo}")
                        else:
                            reg.cod_produto = novo_codigo
                        cod_convertidos += 1
                except ValueError:
                    # cod_produto já é alfanumérico, ignorar
                    pass

        # 6. Commit
        if not dry_run and (cnpj_corrigidos > 0 or razao_corrigidas > 0 or cod_convertidos > 0):
            try:
                db.session.commit()
                print(f"\n✓ COMMIT realizado com sucesso!")
            except Exception as e:
                db.session.rollback()
                print(f"\n✗ ERRO ao commitar: {e}")
                return

        # 7. Relatório final
        print("-" * 70)
        print(f"RESULTADO:")
        print(f"  - CNPJs corrigidos: {cnpj_corrigidos}")
        print(f"  - Razões corrigidas: {razao_corrigidas}")
        print(f"  - cod_produto convertidos: {cod_convertidos}")

        if erros:
            print(f"\n⚠ ERROS:")
            for erro in erros[:10]:  # Mostrar apenas 10 primeiros
                print(f"  - {erro}")
            if len(erros) > 10:
                print(f"  ... e mais {len(erros) - 10} erros")

        # 8. Diagnóstico final
        if not dry_run:
            sem_cnpj_final = CadastroPrimeiraCompra.query.filter(
                (CadastroPrimeiraCompra.cnpj_empresa_compradora == None) |
                (CadastroPrimeiraCompra.cnpj_empresa_compradora == '')
            ).count()
            sem_razao_final = CadastroPrimeiraCompra.query.filter(
                (CadastroPrimeiraCompra.razao_empresa_compradora == None) |
                (CadastroPrimeiraCompra.razao_empresa_compradora == '')
            ).count()
            cod_numerico_final = CadastroPrimeiraCompra.query.filter(
                CadastroPrimeiraCompra.cod_produto.op('~')('^[0-9]+$')
            ).count()

            print("-" * 70)
            print(f"DIAGNÓSTICO FINAL:")
            print(f"  - Ainda sem CNPJ: {sem_cnpj_final} (antes: {sem_cnpj})")
            print(f"  - Ainda sem razão: {sem_razao_final} (antes: {sem_razao})")
            print(f"  - Ainda com cod numérico: {cod_numerico_final} (antes: {registros_cod_numerico})")

        print("=" * 70)
        print("Migração concluída!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Corrige dados em cadastro_primeira_compra'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Apenas mostra o que seria feito, sem modificar o banco'
    )
    parser.add_argument(
        '--skip-produto',
        action='store_true',
        help='Não converte cod_produto (apenas corrige CNPJ/razão)'
    )
    parser.add_argument(
        '--only-produto',
        action='store_true',
        help='Apenas converte cod_produto (ignora CNPJ/razão)'
    )

    args = parser.parse_args()

    if args.skip_produto and args.only_produto:
        print("ERRO: Não pode usar --skip-produto e --only-produto juntos")
        sys.exit(1)

    main(dry_run=args.dry_run, skip_produto=args.skip_produto, only_produto=args.only_produto)
