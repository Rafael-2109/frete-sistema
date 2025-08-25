#!/usr/bin/env python3
"""
Script para executar migration de grupo_empresarial
"""
from app import create_app, db
app = create_app()
from sqlalchemy import text

def run_migration():
    with app.app_context():
        try:
            # Lê o arquivo SQL
            with open('migrations/manufatura_grupo_empresarial_ajuste.sql', 'r') as f:
                sql_commands = f.read()
            
            # Separa comandos por ';' e executa cada um
            commands = sql_commands.split(';')
            
            for command in commands:
                command = command.strip()
                if command and not command.startswith('--') and not command.startswith('/*'):
                    print(f"Executando: {command[:50]}...")
                    db.session.execute(text(command))
            
            db.session.commit()
            print("✅ Migration executada com sucesso!")
            
            # Insere dados de exemplo
            print("\nInserindo grupos de exemplo...")
            grupos_exemplo = [
                ('Atacadão', '75315333', 'Rede Atacadão'),
                ('Atacadão', '10776574', 'Rede Atacadão'),
                ('Carrefour', '45543915', 'Grupo Carrefour'),
                ('Carrefour', '09808432', 'Grupo Carrefour'),
                ('Pão de Açúcar', '06057223', 'Grupo Pão de Açúcar'),
                ('Extra', '07170938', 'Rede Extra'),
            ]
            
            for nome, prefixo, desc in grupos_exemplo:
                sql = text("""
                    INSERT INTO grupo_empresarial (nome_grupo, prefixo_cnpj, descricao, criado_por)
                    VALUES (:nome, :prefixo, :desc, 'Sistema')
                    ON CONFLICT (prefixo_cnpj) DO NOTHING
                """)
                db.session.execute(sql, {'nome': nome, 'prefixo': prefixo, 'desc': desc})
            
            db.session.commit()
            print("✅ Dados de exemplo inseridos!")
            
            # Verifica dados inseridos
            result = db.session.execute(text("""
                SELECT nome_grupo, COUNT(*) as qtd_prefixos 
                FROM grupo_empresarial 
                GROUP BY nome_grupo 
                ORDER BY nome_grupo
            """))
            
            print("\n📊 Grupos cadastrados:")
            for row in result:
                print(f"  - {row[0]}: {row[1]} prefixo(s)")
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()

if __name__ == "__main__":
    run_migration()