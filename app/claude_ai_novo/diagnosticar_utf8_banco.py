#!/usr/bin/env python3
"""
🔍 DIAGNÓSTICO: Problemas UTF-8 no Banco de Dados
================================================
"""

import sys
import os
import logging
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_database_connection():
    """Verifica conexão com banco de dados"""
    print("\n1️⃣ Verificando conexão com banco de dados...")
    
    try:
        from app import create_app, db
        app = create_app()
        
        with app.app_context():
            # Tentar executar query simples
            result = db.session.execute(db.text("SELECT 1"))
            print("✅ Conexão com banco estabelecida")
            
            # Verificar encoding do banco
            encoding_query = db.text("SHOW server_encoding")
            encoding = db.session.execute(encoding_query).scalar()
            print(f"📝 Encoding do servidor: {encoding}")
            
            # Verificar encoding do cliente
            client_encoding_query = db.text("SHOW client_encoding")
            client_encoding = db.session.execute(client_encoding_query).scalar()
            print(f"📝 Encoding do cliente: {client_encoding}")
            
            return True, encoding, client_encoding
            
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        logger.error(f"Erro detalhado: {e}", exc_info=True)
        return False, None, None

def check_problematic_data():
    """Identifica dados problemáticos no banco"""
    print("\n2️⃣ Procurando dados com problemas de encoding...")
    
    try:
        from app import create_app, db
        from app.pedidos.models import Pedido
        from app.monitoramento.models import EntregaMonitorada
        
        app = create_app()
        problemas = []
        
        with app.app_context():
            # Verificar tabelas principais
            tabelas = [
                ('pedidos', Pedido, ['nome_cliente', 'endereco_entrega', 'observacao']),
                ('entregas_monitoradas', EntregaMonitorada, ['nome_cliente', 'cidade', 'observacao'])
            ]
            
            for nome_tabela, Model, campos in tabelas:
                print(f"\n📋 Verificando tabela: {nome_tabela}")
                
                try:
                    # Contar total de registros
                    total = db.session.query(Model).count()
                    print(f"   Total de registros: {total}")
                    
                    # Verificar campos de texto
                    for campo in campos:
                        if hasattr(Model, campo):
                            # Tentar ler alguns registros
                            try:
                                registros = db.session.query(Model).limit(10).all()
                                for reg in registros:
                                    valor = getattr(reg, campo, None)
                                    if valor and isinstance(valor, str):
                                        # Tentar decodificar
                                        try:
                                            valor.encode('utf-8').decode('utf-8')
                                        except UnicodeDecodeError as e:
                                            problemas.append({
                                                'tabela': nome_tabela,
                                                'campo': campo,
                                                'id': reg.id,
                                                'erro': str(e)
                                            })
                                            print(f"   ⚠️ Problema em {campo} (ID: {reg.id})")
                            except Exception as e:
                                print(f"   ❌ Erro ao verificar campo {campo}: {e}")
                                
                except Exception as e:
                    print(f"   ❌ Erro ao verificar tabela: {e}")
                    
        return problemas
        
    except Exception as e:
        print(f"❌ Erro ao verificar dados: {e}")
        logger.error(f"Erro detalhado: {e}", exc_info=True)
        return []

def check_database_charset():
    """Verifica charset das tabelas"""
    print("\n3️⃣ Verificando charset das tabelas...")
    
    try:
        from app import create_app, db
        app = create_app()
        
        with app.app_context():
            # Query para verificar charset das tabelas (PostgreSQL)
            query = db.text("""
                SELECT 
                    table_name,
                    character_set_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND character_set_name IS NOT NULL
                GROUP BY table_name, character_set_name
                LIMIT 10
            """)
            
            try:
                results = db.session.execute(query).fetchall()
                if results:
                    for table, charset in results:
                        print(f"   📋 {table}: {charset}")
                else:
                    print("   ℹ️ PostgreSQL não retorna charset por tabela (usa encoding do banco)")
            except:
                # Tentar query alternativa para PostgreSQL
                print("   ℹ️ Verificando configuração geral do PostgreSQL...")
                
                configs = [
                    "SHOW server_encoding",
                    "SHOW client_encoding", 
                    "SELECT current_database()",
                    "SELECT version()"
                ]
                
                for config_query in configs:
                    try:
                        result = db.session.execute(db.text(config_query)).scalar()
                        print(f"   📝 {config_query}: {result}")
                    except Exception as e:
                        print(f"   ⚠️ Erro em {config_query}: {e}")
                        
    except Exception as e:
        print(f"❌ Erro ao verificar charset: {e}")
        logger.error(f"Erro detalhado: {e}", exc_info=True)

def suggest_fixes(problemas):
    """Sugere correções para os problemas encontrados"""
    print("\n4️⃣ Sugestões de correção:")
    
    if not problemas:
        print("✅ Nenhum problema de encoding detectado!")
        return
        
    print("\n⚠️ PROBLEMAS ENCONTRADOS:")
    for p in problemas[:5]:  # Mostrar apenas os 5 primeiros
        print(f"   - Tabela: {p['tabela']}, Campo: {p['campo']}, ID: {p['id']}")
        
    print("\n🔧 SUGESTÕES:")
    print("1. Configurar DATABASE_URL com charset UTF-8:")
    print("   postgresql://user:pass@host/db?client_encoding=utf8")
    print("\n2. Executar no banco de dados:")
    print("   ALTER DATABASE seu_banco SET client_encoding TO 'UTF8';")
    print("\n3. Corrigir dados problemáticos:")
    print("   UPDATE tabela SET campo = convert_from(convert_to(campo, 'LATIN1'), 'UTF8')")
    print("\n4. No SQLAlchemy, adicionar:")
    print("   create_engine(url, encoding='utf-8')")

def main():
    """Executa diagnóstico completo"""
    print("="*60)
    print("🔍 DIAGNÓSTICO UTF-8 - BANCO DE DADOS")
    print("="*60)
    
    # 1. Verificar conexão
    conectado, server_enc, client_enc = check_database_connection()
    
    if not conectado:
        print("\n❌ Não foi possível conectar ao banco. Verifique DATABASE_URL")
        return
        
    # 2. Verificar dados problemáticos
    problemas = check_problematic_data()
    
    # 3. Verificar charset
    check_database_charset()
    
    # 4. Sugerir correções
    suggest_fixes(problemas)
    
    print("\n" + "="*60)
    print("📊 RESUMO:")
    print(f"   - Encoding servidor: {server_enc}")
    print(f"   - Encoding cliente: {client_enc}")
    print(f"   - Problemas encontrados: {len(problemas)}")
    print("="*60)

if __name__ == "__main__":
    main() 