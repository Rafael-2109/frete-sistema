"""
Script para inicializar dados padrão do sistema de permissões
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.permissions.models import inicializar_dados_padrao

def main():
    """Inicializa dados padrão do sistema de permissões"""
    app = create_app()
    
    with app.app_context():
        print("🚀 Inicializando dados padrão do sistema de permissões...")
        
        try:
            # Chamar função de inicialização
            sucesso = inicializar_dados_padrao()
            
            if sucesso:
                print("✅ Dados padrão inicializados com sucesso!")
            else:
                print("❌ Erro ao inicializar dados padrão")
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            print("\n💡 Verifique se as tabelas foram criadas executando:")
            print("   flask db upgrade")

if __name__ == "__main__":
    main()