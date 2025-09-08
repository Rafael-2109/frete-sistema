#!/usr/bin/env python3
"""
Script para criar as tabelas do Portal Sendas no banco de dados local
Execute: python criar_tabelas_sendas.py
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.portal.sendas.models import ProdutoDeParaSendas, FilialDeParaSendas

def criar_tabelas():
    """Cria as tabelas do Portal Sendas no banco de dados"""
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("CRIAÇÃO DE TABELAS DO PORTAL SENDAS")
        print("=" * 60)
        
        try:
            # Criar tabelas
            print("\n1. Criando tabelas...")
            
            # Criar apenas as tabelas dos modelos Sendas
            # Usando inspect para verificar se as tabelas já existem
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # Verificar tabela de produtos
            if 'portal_sendas_produto_depara' not in existing_tables:
                ProdutoDeParaSendas.__table__.create(db.engine)
                print("   ✅ Tabela 'portal_sendas_produto_depara' criada com sucesso!")
            else:
                print("   ℹ️  Tabela 'portal_sendas_produto_depara' já existe")
            
            # Verificar tabela de filiais
            if 'portal_sendas_filial_depara' not in existing_tables:
                FilialDeParaSendas.__table__.create(db.engine)
                print("   ✅ Tabela 'portal_sendas_filial_depara' criada com sucesso!")
            else:
                print("   ℹ️  Tabela 'portal_sendas_filial_depara' já existe")
            
            # Commit das mudanças
            db.session.commit()
            
            # Verificar se as tabelas foram criadas
            print("\n2. Verificando tabelas criadas...")
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            sendas_tables = [t for t in tables if 'sendas' in t]
            if sendas_tables:
                print(f"   Tabelas do Sendas encontradas:")
                for table in sendas_tables:
                    # Contar registros
                    from sqlalchemy import text
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"   - {table}: {count} registros")
            
            # Opcional: Inserir dados de exemplo
            inserir_exemplo = input("\n3. Deseja inserir dados de exemplo? (s/N): ").lower()
            
            if inserir_exemplo == 's':
                print("\n   Inserindo dados de exemplo...")
                
                # Exemplo de produto
                produto_exemplo = ProdutoDeParaSendas(
                    codigo_nosso='1001',
                    descricao_nosso='Produto Exemplo A',
                    codigo_sendas='SND001',
                    descricao_sendas='Produto Sendas A',
                    fator_conversao=1.0,
                    ativo=True,
                    criado_por='Script Inicial'
                )
                
                # Verificar se já existe
                existe = ProdutoDeParaSendas.query.filter_by(
                    codigo_nosso='1001',
                    codigo_sendas='SND001'
                ).first()
                
                if not existe:
                    db.session.add(produto_exemplo)
                    print("   ✅ Produto de exemplo inserido")
                else:
                    print("   ℹ️  Produto de exemplo já existe")
                
                # Exemplo de filial
                filial_exemplo = FilialDeParaSendas(
                    cnpj='12.345.678/0001-90',
                    filial='001',
                    nome_filial='Sendas Centro',
                    cidade='Rio de Janeiro',
                    uf='RJ',
                    ativo=True,
                    criado_por='Script Inicial'
                )
                
                # Verificar se já existe
                existe = FilialDeParaSendas.query.filter_by(
                    cnpj='12.345.678/0001-90'
                ).first()
                
                if not existe:
                    db.session.add(filial_exemplo)
                    print("   ✅ Filial de exemplo inserida")
                else:
                    print("   ℹ️  Filial de exemplo já existe")
                
                db.session.commit()
            
            print("\n" + "=" * 60)
            print("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
            print("=" * 60)
            
            print("\n📝 PRÓXIMOS PASSOS:")
            print("1. Acesse /portal/sendas/depara para gerenciar os mapeamentos")
            print("2. Importe um CSV com os produtos do Sendas")
            print("3. Importe um CSV com as filiais do Sendas")
            print("4. Configure os agendamentos automáticos")
            
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            return False
    
    return True

if __name__ == "__main__":
    print("\n🚀 Iniciando criação das tabelas do Portal Sendas...")
    
    # Verificar se o banco está acessível
    try:
        criar_tabelas()
    except Exception as e:
        print(f"\n❌ Erro ao conectar com o banco de dados: {e}")
        print("\nVerifique:")
        print("1. Se o PostgreSQL está rodando")
        print("2. Se as configurações do banco estão corretas no .env")
        print("3. Se o banco de dados existe")
        sys.exit(1)