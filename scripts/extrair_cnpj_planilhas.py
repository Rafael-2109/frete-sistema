#!/usr/bin/env python3
"""
Script para Extrair CNPJ de Múltiplas Planilhas Excel
Data: 14/10/2025

USO:
    # Processar todas planilhas de uma pasta
    python3 scripts/extrair_cnpj_planilhas.py /caminho/para/pasta

    # Processar arquivos específicos
    python3 scripts/extrair_cnpj_planilhas.py arquivo1.xlsx arquivo2.xls

    # Com modo debug
    python3 scripts/extrair_cnpj_planilhas.py /caminho/para/pasta --debug

    # Exportar para CSV
    python3 scripts/extrair_cnpj_planilhas.py /caminho/para/pasta --output resultados.csv
"""

import sys
import os
from pathlib import Path
import argparse

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.motochefe.services.extrator_cnpj_planilhas import ExtratorCNPJ


def obter_arquivos_excel(caminho: str) -> list:
    """
    Retorna lista de arquivos Excel em um caminho

    Se for diretório: retorna todos .xlsx e .xls
    Se for arquivo: retorna lista com o arquivo
    """
    caminho_path = Path(caminho)

    if caminho_path.is_file():
        # Verificar se é Excel
        if caminho_path.suffix.lower() in ['.xlsx', '.xls', '.xlsm']:
            return [str(caminho_path)]
        else:
            print(f"❌ Arquivo '{caminho}' não é Excel (.xlsx, .xls, .xlsm)")
            return []

    elif caminho_path.is_dir():
        # Buscar todos arquivos Excel recursivamente
        arquivos = []
        for extensao in ['*.xlsx', '*.xls', '*.xlsm']:
            arquivos.extend(caminho_path.rglob(extensao))

        return [str(f) for f in arquivos]

    else:
        print(f"❌ Caminho '{caminho}' não existe")
        return []


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='Extrai CNPJ de múltiplas planilhas Excel',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  %(prog)s /pasta/com/planilhas
  %(prog)s arquivo1.xlsx arquivo2.xls
  %(prog)s /pasta --debug --output resultados.xlsx
        """
    )

    parser.add_argument(
        'caminhos',
        nargs='+',
        help='Caminho(s) para pasta ou arquivo(s) Excel'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Ativa modo debug com logs detalhados'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Arquivo de saída (.csv ou .xlsx) para exportar resultados'
    )

    args = parser.parse_args()

    # Coletar todos arquivos Excel
    todos_arquivos = []
    for caminho in args.caminhos:
        arquivos = obter_arquivos_excel(caminho)
        todos_arquivos.extend(arquivos)

    # Remover duplicatas
    todos_arquivos = list(set(todos_arquivos))

    if not todos_arquivos:
        print("\n❌ Nenhum arquivo Excel encontrado!")
        print("\nVerifique se:")
        print("  1. O caminho está correto")
        print("  2. Existem arquivos .xlsx ou .xls no caminho")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"EXTRATOR DE CNPJ - MÚLTIPLAS PLANILHAS")
    print(f"{'='*60}")
    print(f"📁 Arquivos encontrados: {len(todos_arquivos)}")

    # Criar extrator
    extrator = ExtratorCNPJ()

    if args.debug:
        extrator.ativar_debug()
        print("🐛 Modo debug ativado")

    # Processar arquivos
    resultados = extrator.buscar_cnpj_em_multiplas_planilhas(todos_arquivos)

    # Exportar resultados se solicitado
    if args.output:
        caminho_saida = Path(args.output)

        if caminho_saida.suffix.lower() == '.csv':
            extrator.exportar_resultados_csv(resultados, str(caminho_saida))
        elif caminho_saida.suffix.lower() in ['.xlsx', '.xls']:
            extrator.exportar_resultados_excel(resultados, str(caminho_saida))
        else:
            print(f"\n⚠️ Extensão '{caminho_saida.suffix}' não suportada. Use .csv ou .xlsx")

    # Exibir CNPJs únicos encontrados
    print(f"\n{'='*60}")
    print("CNPJs ÚNICOS ENCONTRADOS")
    print(f"{'='*60}")

    cnpjs_unicos = {}
    for r in resultados:
        if r['sucesso']:
            cnpj = r['cnpj_formatado']
            if cnpj not in cnpjs_unicos:
                cnpjs_unicos[cnpj] = []
            cnpjs_unicos[cnpj].append(r['arquivo'])

    if cnpjs_unicos:
        for cnpj, arquivos in cnpjs_unicos.items():
            print(f"\n📋 {cnpj}")
            print(f"   Encontrado em {len(arquivos)} arquivo(s):")
            for arquivo in arquivos:
                print(f"     - {arquivo}")
    else:
        print("\n❌ Nenhum CNPJ encontrado em nenhum arquivo")

    print(f"\n{'='*60}")
    print("✅ Processamento concluído!")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
