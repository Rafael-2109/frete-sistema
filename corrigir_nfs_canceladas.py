#!/usr/bin/env python3
"""
Script para corrigir todas as NFs que estão canceladas no Odoo
mas não foram marcadas corretamente no banco de dados.

Este script:
1. Busca todas as NFs canceladas no Odoo
2. Verifica quais precisam ser corrigidas no banco
3. Atualiza FaturamentoProduto com status='Cancelado'
4. Atualiza MovimentacaoEstoque com ativo=False e status='CANCELADO'
5. Limpa EmbarqueItem e Separacao relacionados
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.odoo.services.faturamento_service import FaturamentoService
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Executa a correção de NFs canceladas"""
    
    app = create_app()
    with app.app_context():
        try:
            print("\n" + "="*80)
            print("🔧 CORREÇÃO DE NFs CANCELADAS")
            print("="*80)
            print("\nEste script irá:")
            print("  1. Buscar todas as NFs canceladas no Odoo")
            print("  2. Verificar quais não estão marcadas corretamente no banco")
            print("  3. Corrigir o status em FaturamentoProduto e MovimentacaoEstoque")
            print("  4. Limpar relacionamentos em EmbarqueItem e Separacao")
            print("\n" + "="*80)
            
            # Confirmar execução
            resposta = input("\n⚠️  Deseja continuar? (s/n): ")
            if resposta.lower() != 's':
                print("❌ Operação cancelada")
                return
            
            print("\n🚀 Iniciando correção...")
            
            # Executar correção
            service = FaturamentoService()
            resultado = service.processar_nfs_canceladas_existentes()
            
            if resultado['sucesso']:
                print("\n✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
                print(f"\n📊 ESTATÍSTICAS:")
                print(f"   - NFs canceladas no Odoo: {resultado['total_odoo']}")
                print(f"   - NFs corrigidas: {resultado['total_corrigidas']}")
                print(f"   - NFs já corretas: {resultado['ja_corretas']}")
                print(f"   - NFs não existentes no banco: {resultado['nao_existentes']}")
                
                if resultado.get('erros'):
                    print(f"\n⚠️  Houve {len(resultado['erros'])} erros durante o processamento:")
                    for erro in resultado['erros'][:5]:  # Mostrar apenas 5 primeiros erros
                        print(f"   - {erro}")
                    if len(resultado['erros']) > 5:
                        print(f"   ... e mais {len(resultado['erros']) - 5} erros")
            else:
                print(f"\n❌ ERRO na correção: {resultado.get('erro', 'Erro desconhecido')}")
            
            print("\n" + "="*80)
            print("🏁 SCRIPT FINALIZADO")
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"\n❌ ERRO FATAL: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()