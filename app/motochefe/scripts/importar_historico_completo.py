"""
Script para Importação Completa de Dados Históricos
Sistema MotoCHEFE - Fases 5, 6 e 7

USO:
    python app/motochefe/scripts/importar_historico_completo.py

IMPORTANTE:
- Executa TODAS as fases em sequência: Fase 5 → Fase 6 → Fase 7
- Rollback TOTAL em caso de erro em qualquer fase
- Requer arquivo Excel com 3 abas: Comissoes, Montagens, Movimentacoes
- Caminho do arquivo está HARDCODED (altere se necessário)
"""
import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
import pandas as pd
from app.motochefe.services.importacao_historico_service import (
    importar_comissoes_historico,
    importar_montagens_historico,
    importar_movimentacoes_historico
)


def importar_historico_completo(arquivo_excel):
    """
    Importa dados históricos completos (Fases 5, 6 e 7)

    Args:
        arquivo_excel: str - Caminho do arquivo Excel com 3 abas

    Returns:
        bool - True se sucesso, False se erro
    """
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("IMPORTAÇÃO DE DADOS HISTÓRICOS - MOTOCHEFE")
        print("=" * 80)
        print(f"\nArquivo: {arquivo_excel}\n")

        try:
            # Carregar Excel
            print("📂 Carregando arquivo Excel...")
            excel_file = pd.ExcelFile(arquivo_excel)

            # Validar abas
            abas_necessarias = ['Comissoes', 'Montagens', 'Movimentacoes']
            abas_presentes = excel_file.sheet_names

            for aba in abas_necessarias:
                if aba not in abas_presentes:
                    raise ValueError(
                        f"❌ Aba '{aba}' não encontrada no Excel. "
                        f"Abas presentes: {', '.join(abas_presentes)}"
                    )

            # Carregar DataFrames
            df_comissoes = pd.read_excel(excel_file, sheet_name='Comissoes')
            df_montagens = pd.read_excel(excel_file, sheet_name='Montagens')
            df_movimentacoes = pd.read_excel(excel_file, sheet_name='Movimentacoes')

            print(f"✅ Arquivo carregado:")
            print(f"   - Comissões: {len(df_comissoes)} linhas")
            print(f"   - Montagens: {len(df_montagens)} linhas")
            print(f"   - Movimentações: {len(df_movimentacoes)} linhas")
            print()

            # FASE 5: COMISSÕES
            print("-" * 80)
            print("FASE 5: IMPORTANDO COMISSÕES HISTÓRICAS")
            print("-" * 80)

            resultado_fase5 = importar_comissoes_historico(df_comissoes, usuario='SCRIPT_LOCAL')

            print(f"\n{resultado_fase5.mensagem}\n")

            if not resultado_fase5.sucesso:
                print("❌ ERRO NA FASE 5 - ROLLBACK TOTAL")
                for erro in resultado_fase5.erros:
                    print(f"   {erro}")
                return False

            if resultado_fase5.avisos:
                print("⚠️  AVISOS:")
                for aviso in resultado_fase5.avisos:
                    print(f"   - {aviso}")
                print()

            # FASE 6: MONTAGENS
            print("-" * 80)
            print("FASE 6: IMPORTANDO MONTAGENS HISTÓRICAS")
            print("-" * 80)

            resultado_fase6 = importar_montagens_historico(df_montagens, usuario='SCRIPT_LOCAL')

            print(f"\n{resultado_fase6.mensagem}\n")

            if not resultado_fase6.sucesso:
                print("❌ ERRO NA FASE 6 - ROLLBACK TOTAL")
                for erro in resultado_fase6.erros:
                    print(f"   {erro}")
                return False

            if resultado_fase6.avisos:
                print("⚠️  AVISOS:")
                for aviso in resultado_fase6.avisos:
                    print(f"   - {aviso}")
                print()

            # FASE 7: MOVIMENTAÇÕES
            print("-" * 80)
            print("FASE 7: IMPORTANDO MOVIMENTAÇÕES HISTÓRICAS")
            print("-" * 80)

            resultado_fase7 = importar_movimentacoes_historico(df_movimentacoes, usuario='SCRIPT_LOCAL')

            print(f"\n{resultado_fase7.mensagem}\n")

            if not resultado_fase7.sucesso:
                print("❌ ERRO NA FASE 7 - ROLLBACK TOTAL")
                for erro in resultado_fase7.erros:
                    print(f"   {erro}")
                return False

            if resultado_fase7.avisos:
                print("⚠️  AVISOS:")
                for aviso in resultado_fase7.avisos:
                    print(f"   - {aviso}")
                print()

            # SUCESSO COMPLETO
            print("=" * 80)
            print("✅ IMPORTAÇÃO COMPLETA COM SUCESSO!")
            print("=" * 80)
            print("\n📊 RESUMO GERAL:\n")
            print(f"FASE 5 - COMISSÕES:")
            print(f"   Comissões criadas: {resultado_fase5.comissoes_criadas}")
            print(f"   Pagas: {resultado_fase5.comissoes_pagas}")
            print(f"   Pendentes: {resultado_fase5.comissoes_pendentes}")
            print(f"   Lotes criados: {resultado_fase5.movimentacoes_pai_criadas}")
            print(f"   Valor total pago: R$ {resultado_fase5.valor_total_pago}")
            print()

            print(f"FASE 6 - MONTAGENS:")
            print(f"   Itens atualizados: {resultado_fase6.itens_atualizados}")
            print(f"   Títulos A Receber: {resultado_fase6.titulos_receber_criados}")
            print(f"   Títulos A Pagar: {resultado_fase6.titulos_pagar_criados}")
            print(f"   Recebimentos: {resultado_fase6.movimentacoes_recebimento}")
            print(f"   Pagamentos: {resultado_fase6.movimentacoes_pagamento}")
            print(f"   Valor total deduzido de VENDA: R$ {resultado_fase6.valor_total_deduzido_venda}")
            print()

            print(f"FASE 7 - MOVIMENTAÇÕES:")
            print(f"   Títulos A Receber: {resultado_fase7.titulos_receber_criados}")
            print(f"   Títulos A Pagar: {resultado_fase7.titulos_pagar_criados}")
            print(f"   Recebimentos: {resultado_fase7.movimentacoes_recebimento}")
            print(f"   Pagamentos: {resultado_fase7.movimentacoes_pagamento}")
            print(f"   Valor total deduzido de VENDA: R$ {resultado_fase7.valor_total_deduzido_venda}")
            print()

            return True

        except Exception as e:
            print(f"\n❌ ERRO FATAL: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False


if __name__ == '__main__':
    # ⚠️ ALTERE O CAMINHO DO ARQUIVO CONFORME NECESSÁRIO
    arquivo_excel = '/tmp/historico_motochefe.xlsx'

    # Validar existência do arquivo
    if not os.path.exists(arquivo_excel):
        print(f"❌ Arquivo não encontrado: {arquivo_excel}")
        print("\nCrie o arquivo Excel com as 3 abas: Comissoes, Montagens, Movimentacoes")
        print("Ou altere o caminho no código.\n")
        sys.exit(1)

    # Executar importação
    sucesso = importar_historico_completo(arquivo_excel)

    # Exit code
    sys.exit(0 if sucesso else 1)
