#!/usr/bin/env python3
"""
Versão automática (não-interativa) do script de correção dos triggers.
Aplica todas as correções sem solicitar confirmação.

Uso:
    python aplicar_correcao_automatica.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import event, text
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar as funções do script original
from corrigir_session_triggers import (
    remover_todos_triggers,
    criar_triggers_seguros,
    verificar_instalacao,
    sincronizar_dados_existentes,
    testar_correcao
)


def main():
    """Aplica correção automaticamente sem interação"""
    print("\n" + "="*70)
    print("APLICAÇÃO AUTOMÁTICA DA CORREÇÃO DOS TRIGGERS")
    print("="*70)
    
    app = create_app()
    
    with app.app_context():
        try:
            print("\n[1/5] Removendo triggers existentes...")
            remover_todos_triggers()
            
            print("\n[2/5] Criando triggers seguros...")
            criar_triggers_seguros()
            
            print("\n[3/5] Verificando instalação...")
            if not verificar_instalacao():
                print("❌ Tabelas necessárias não existem")
                print("Execute primeiro: python init_estoque_tempo_real.py")
                return False
            
            print("\n[4/5] Sincronizando dados existentes...")
            sincronizar_dados_existentes()
            
            print("\n[5/5] Testando correção...")
            if testar_correcao():
                print("\n" + "="*70)
                print("✅ CORREÇÃO APLICADA COM SUCESSO!")
                print("="*70)
                print("\nSistema agora está usando triggers seguros que:")
                print("• Usam SQL direto (sem tocar na session)")
                print("• Evitam problemas de flush")
                print("• Atualizam dados em tempo real")
                print("\n🎯 Próximos passos:")
                print("1. Reinicie a aplicação")
                print("2. Teste criar uma pré-separação")
                print("3. Verifique se os dados aparecem no cardex")
                return True
            else:
                print("\n⚠️ Teste falhou após correção")
                print("Verifique os logs para mais detalhes")
                return False
                
        except Exception as e:
            print(f"\n❌ Erro durante correção: {e}")
            logger.error(f"Erro na correção automática: {e}", exc_info=True)
            return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)