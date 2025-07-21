#!/usr/bin/env python3
"""
Verificação simples da estrutura do banco - sem dependências Flask
"""

import os
import sys

def check_migration_files():
    print("VERIFICACAO DE ARQUIVOS DE MIGRACAO")
    print("=" * 50)
    
    # 1. Verificar diretório migrations
    migrations_dir = 'migrations'
    if os.path.exists(migrations_dir):
        print(f"OK - Diretorio {migrations_dir} existe")
        
        # Verificar versions
        versions_dir = os.path.join(migrations_dir, 'versions')
        if os.path.exists(versions_dir):
            print(f"OK - Diretorio {versions_dir} existe")
            
            # Listar arquivos de migração
            migration_files = [f for f in os.listdir(versions_dir) if f.endswith('.py')]
            print(f"OK - {len(migration_files)} arquivos de migracao encontrados")
            
            # Mostrar os últimos arquivos
            migration_files.sort(reverse=True)
            for i, file in enumerate(migration_files[:3]):
                print(f"   {i+1}. {file}")
                
        else:
            print("ERRO - Diretorio versions nao existe")
    else:
        print("ERRO - Diretorio migrations nao existe")
    
    print()

def check_model_definition():
    print("VERIFICACAO DA DEFINICAO DO MODELO")
    print("=" * 50)
    
    model_file = 'app/carteira/models.py'
    if os.path.exists(model_file):
        print(f"OK - Arquivo {model_file} existe")
        
        with open(model_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar elementos críticos
        checks = [
            ('class PreSeparacaoItem', 'Classe PreSeparacaoItem definida'),
            ('data_expedicao_editada = db.Column(db.Date, nullable=False)', 'Campo obrigatorio definido'),
            ('__table_args__', 'Constraints de tabela definidas'),
            ('uq_pre_separacao_contexto_unico', 'Constraint unica nomeada'),
            ('aplicar_reducao_quantidade', 'Metodo pos-Odoo reducao'),
            ('aplicar_aumento_quantidade', 'Metodo pos-Odoo aumento')
        ]
        
        for check_text, description in checks:
            if check_text in content:
                print(f"OK - {description}")
            else:
                print(f"ERRO - {description} NAO ENCONTRADO")
    else:
        print(f"ERRO - Arquivo {model_file} nao existe")
    
    print()

def check_sql_migration():
    print("VERIFICACAO DE MIGRACOES SQL")
    print("=" * 50)
    
    # Verificar se existe alguma migração que menciona pre_separacao_item
    versions_dir = os.path.join('migrations', 'versions')
    if os.path.exists(versions_dir):
        migration_files = [f for f in os.listdir(versions_dir) if f.endswith('.py')]
        
        found_pre_sep_migration = False
        for file in migration_files:
            file_path = os.path.join(versions_dir, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'pre_separacao_item' in content.lower():
                    print(f"OK - Migracao encontrada: {file}")
                    found_pre_sep_migration = True
                    
                    # Verificar elementos específicos
                    if 'data_expedicao_editada' in content:
                        print("  -> Contem campo data_expedicao_editada")
                    if 'uq_pre_separacao_contexto_unico' in content:
                        print("  -> Contem constraint unica")
                    if 'CREATE TABLE' in content.upper():
                        print("  -> Cria tabela")
                    if 'ALTER TABLE' in content.upper():
                        print("  -> Altera tabela")
                        
            except Exception as e:
                print(f"ERRO ao ler {file}: {e}")
        
        if not found_pre_sep_migration:
            print("ATENCAO - Nenhuma migracao para pre_separacao_item encontrada")
            print("  -> Pode precisar executar: flask db migrate")
    
    print()

def main():
    print("VERIFICACAO DO SISTEMA PRE-SEPARACAO")
    print("=" * 60)
    print()
    
    check_migration_files()
    check_model_definition()
    check_sql_migration()
    
    print("RESUMO E PROXIMOS PASSOS:")
    print("=" * 50)
    print("1. Se a migracao NAO foi encontrada:")
    print("   -> Execute: flask db migrate -m 'Implementar pre-separacao'")
    print("   -> Depois: flask db upgrade")
    print()
    print("2. Se a migracao foi encontrada mas nao aplicada:")
    print("   -> Execute: flask db upgrade")
    print()
    print("3. Para verificar o status no servidor:")
    print("   -> Use o arquivo verificar_coluna.sql no PostgreSQL")
    print()
    print("4. Para verificar no ambiente de producao:")
    print("   -> Acesse o painel do Render e execute comandos Flask")

if __name__ == "__main__":
    main()