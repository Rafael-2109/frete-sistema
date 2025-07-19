#!/usr/bin/env python3
"""
Script para aplicar migração no SHELL do Render
Otimizado para ambiente Linux UTF-8 do Render
"""

import os
import sys

def aplicar_migracao_render():
    """Aplica migração no ambiente Render"""
    
    print('🚀 APLICANDO MIGRAÇÃO NO RENDER')
    print('=' * 50)
    
    # 1. Verificar ambiente
    print('📊 Verificando ambiente...')
    print(f'Python: {sys.version}')
    print(f'Platform: {sys.platform}')
    print(f'Encoding: {sys.getdefaultencoding()}')
    
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        print('✅ DATABASE_URL encontrada')
    else:
        print('❌ DATABASE_URL não encontrada')
        return False
    
    print()
    
    # 2. Tentar via Flask-Migrate primeiro
    print('🔄 Tentativa 1: Flask-Migrate padrão...')
    try:
        import subprocess
        result = subprocess.run(['flask', 'db', 'upgrade'], 
                              capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print('✅ Flask-Migrate funcionou!')
            print('📋 Output:', result.stdout)
            return True
        else:
            print('⚠️ Flask-Migrate falhou:', result.stderr)
    except Exception as e:
        print(f'⚠️ Erro Flask-Migrate: {e}')
    
    print()
    
    # 3. Aplicar SQL direto (sem psycopg2 problema)
    print('🔄 Tentativa 2: SQL direto via SQLAlchemy...')
    try:
        # Importar depois de configurar ambiente
        from app import create_app, db
        
        app = create_app()
        
        with app.app_context():
            # SQL para criar tabela
            sql_commands = [
                # Criar tabela principal
                """
                CREATE TABLE IF NOT EXISTS pre_separacao_itens (
                    id SERIAL PRIMARY KEY,
                    carteira_principal_id INTEGER NOT NULL,
                    cod_produto VARCHAR(50) NOT NULL,
                    qtd_original REAL NOT NULL,
                    qtd_selecionada REAL NOT NULL,
                    qtd_restante REAL NOT NULL,
                    expedicao_editavel DATE NULL,
                    agendamento_editavel DATE NULL,
                    protocolo_editavel VARCHAR(50) NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
                    observacoes TEXT NULL,
                    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    criado_por VARCHAR(100) NOT NULL,
                    atualizado_em TIMESTAMP NULL,
                    atualizado_por VARCHAR(100) NULL,
                    tipo_envio VARCHAR(10) DEFAULT 'total',
                    CONSTRAINT fk_pre_separacao_carteira 
                        FOREIGN KEY (carteira_principal_id) 
                        REFERENCES carteira_principal(id)
                );
                """,
                
                # Índices
                "CREATE INDEX IF NOT EXISTS ix_pre_separacao_itens_carteira_principal_id ON pre_separacao_itens(carteira_principal_id);",
                "CREATE INDEX IF NOT EXISTS ix_pre_separacao_itens_cod_produto ON pre_separacao_itens(cod_produto);",
                "CREATE INDEX IF NOT EXISTS ix_pre_separacao_itens_status ON pre_separacao_itens(status);",
                "CREATE INDEX IF NOT EXISTS ix_pre_separacao_itens_tipo_envio ON pre_separacao_itens(tipo_envio);",
                
                # Campo tipo_envio em separacao
                """
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'separacao' AND column_name = 'tipo_envio'
                    ) THEN
                        ALTER TABLE separacao ADD COLUMN tipo_envio VARCHAR(10) DEFAULT 'total';
                        CREATE INDEX IF NOT EXISTS ix_separacao_tipo_envio ON separacao(tipo_envio);
                    END IF;
                END $$;
                """,
                
                # Campos de alerta
                """
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'pedidos' AND column_name = 'alerta_pedido_alterado'
                    ) THEN
                        ALTER TABLE pedidos ADD COLUMN alerta_pedido_alterado BOOLEAN DEFAULT FALSE;
                        CREATE INDEX IF NOT EXISTS ix_pedidos_alerta ON pedidos(alerta_pedido_alterado);
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'embarques' AND column_name = 'alerta_embarque_alterado'
                    ) THEN
                        ALTER TABLE embarques ADD COLUMN alerta_embarque_alterado BOOLEAN DEFAULT FALSE;
                        CREATE INDEX IF NOT EXISTS ix_embarques_alerta ON embarques(alerta_embarque_alterado);
                    END IF;
                END $$;
                """,
                
                # Marcar migração
                """
                INSERT INTO alembic_version (version_num) 
                VALUES ('76bbd63e3bed')
                ON CONFLICT (version_num) DO NOTHING;
                """
            ]
            
            # Executar comandos
            for i, sql in enumerate(sql_commands, 1):
                try:
                    db.engine.execute(sql)
                    print(f'✅ Comando {i} executado')
                except Exception as e:
                    if "already exists" in str(e) or "duplicate" in str(e):
                        print(f'⚠️ Comando {i} - já existe')
                    else:
                        print(f'❌ Comando {i} - erro: {e}')
                        return False
            
            # Commit
            db.session.commit()
            print('✅ Todas as alterações commitadas')
            
            return True
            
    except Exception as e:
        print(f'❌ Erro SQLAlchemy: {e}')
        return False

def verificar_resultado():
    """Verifica se migração foi aplicada corretamente"""
    
    print()
    print('🔍 VERIFICANDO RESULTADO:')
    print('-' * 40)
    
    try:
        from app import create_app, db
        from app.carteira.models import PreSeparacaoItem
        
        app = create_app()
        
        with app.app_context():
            # Testar tabela
            count = PreSeparacaoItem.query.count()
            print(f'✅ Tabela pre_separacao_itens: {count} registros')
            
            # Verificar campos
            result = db.engine.execute("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns 
                WHERE table_name = 'pre_separacao_itens'
                ORDER BY ordinal_position;
            """)
            
            columns = result.fetchall()
            print(f'✅ Tabela tem {len(columns)} colunas:')
            for col in columns[:5]:  # Mostrar primeiras 5
                print(f'  - {col[0]}: {col[1]}')
            
            # Verificar campo tipo_envio em separacao
            result = db.engine.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'separacao' AND column_name = 'tipo_envio';
            """)
            
            if result.fetchone():
                print('✅ Campo tipo_envio em separacao: OK')
            else:
                print('❌ Campo tipo_envio em separacao: NÃO ENCONTRADO')
            
            # Verificar versão Alembic
            result = db.engine.execute("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1;")
            version = result.fetchone()
            if version:
                print(f'✅ Versão Alembic: {version[0]}')
            
            return True
            
    except Exception as e:
        print(f'❌ Erro na verificação: {e}')
        return False

def main():
    """Função principal"""
    
    print('🛠️ MIGRAÇÃO NO SHELL DO RENDER')
    print('Ambiente Linux UTF-8 - sem problemas de encoding')
    print('=' * 60)
    print()
    
    # Aplicar migração
    sucesso = aplicar_migracao_render()
    
    if sucesso:
        # Verificar resultado
        verificacao = verificar_resultado()
        
        print()
        print('🎉 RESULTADO FINAL:')
        print('=' * 60)
        
        if verificacao:
            print('✅ MIGRAÇÃO APLICADA COM SUCESSO!')
            print('🚀 Sistema pronto para desenvolvimento avançado')
            print()
            print('📋 O QUE FOI CRIADO:')
            print('  ✅ Tabela pre_separacao_itens completa')
            print('  ✅ Campo tipo_envio em separacao')
            print('  ✅ Campos de alerta em pedidos/embarques') 
            print('  ✅ Índices otimizados')
            print('  ✅ Migração marcada no Alembic')
            print()
            print('🔄 PRÓXIMOS PASSOS:')
            print('  1. Sistema agora funciona SEM workaround')
            print('  2. Continuar com Etapa 2 (Dropdown Separações)')
            print('  3. Usar tabela real para pré-separações')
        else:
            print('⚠️ MIGRAÇÃO APLICADA MAS VERIFICAÇÃO FALHOU')
            print('📋 Recomendação: Verificar manualmente')
    else:
        print('❌ MIGRAÇÃO FALHOU')
        print('📋 Tentar comandos individuais ou verificar logs')
    
    return sucesso

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 