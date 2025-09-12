#!/usr/bin/env python3
"""
Script AUTOMÁTICO para corrigir todas as NFs canceladas - SEM confirmação
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Executa a correção de NFs canceladas automaticamente"""
    
    app = create_app()
    with app.app_context():
        try:
            print("\n" + "="*80)
            print("🔧 CORREÇÃO AUTOMÁTICA DE NFs CANCELADAS")
            print("="*80)
            
            print("\n🚀 Iniciando correção automática...")
            
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
                    for erro in resultado['erros'][:10]:  # Mostrar 10 primeiros erros
                        print(f"   - {erro}")
                    if len(resultado['erros']) > 10:
                        print(f"   ... e mais {len(resultado['erros']) - 10} erros")
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