#!/usr/bin/env python3
"""
Script para adicionar campo protocolo na tabela portal_integracoes
Executa a migração de forma segura
"""

import sys
import os
from datetime import datetime

# Adicionar o diretório do projeto ao path
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

from app import create_app, db
from sqlalchemy import text

def executar_migracao():
    """Executa a migração do campo protocolo"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("MIGRAÇÃO: Adicionar campo protocolo em portal_integracoes")
        print("="*60)
        
        try:
            # 1. Verificar se tabela existe
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'portal_integracoes'
                )
            """))
            
            if not result.scalar():
                print("❌ ERRO: Tabela portal_integracoes não existe!")
                print("Execute primeiro: python criar_tabelas_portal.py")
                return False
            
            print("✅ Tabela portal_integracoes encontrada")
            
            # 2. Verificar se campo protocolo já existe
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'portal_integracoes' 
                    AND column_name = 'protocolo'
                )
            """))
            
            if result.scalar():
                print("⚠️ Campo protocolo JÁ EXISTE")
            else:
                # 3. Adicionar campo protocolo
                print("🔧 Adicionando campo protocolo...")
                db.session.execute(text("""
                    ALTER TABLE portal_integracoes 
                    ADD COLUMN protocolo VARCHAR(100)
                """))
                db.session.commit()
                print("✅ Campo protocolo adicionado com sucesso!")
            
            # 4. Criar índice único (se não existir)
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = 'portal_integracoes'
                    AND indexname = 'ix_portal_integracoes_protocolo'
                )
            """))
            
            if not result.scalar():
                print("🔧 Criando índice único no campo protocolo...")
                db.session.execute(text("""
                    CREATE UNIQUE INDEX ix_portal_integracoes_protocolo 
                    ON portal_integracoes(protocolo) 
                    WHERE protocolo IS NOT NULL
                """))
                db.session.commit()
                print("✅ Índice criado com sucesso!")
            else:
                print("⚠️ Índice já existe")
            
            # 5. Verificar se existe campo protocolo_portal para migrar
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'portal_integracoes' 
                    AND column_name = 'protocolo_portal'
                )
            """))
            
            if result.scalar():
                print("🔧 Migrando dados de protocolo_portal para protocolo...")
                result = db.session.execute(text("""
                    UPDATE portal_integracoes 
                    SET protocolo = protocolo_portal 
                    WHERE protocolo_portal IS NOT NULL 
                    AND protocolo IS NULL
                """))
                rows_updated = result.rowcount
                db.session.commit()
                print(f"✅ {rows_updated} registros migrados")
            
            # 6. Mostrar estrutura final
            print("\n📊 ESTRUTURA FINAL DA TABELA:")
            print("-" * 40)
            
            result = db.session.execute(text("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable
                FROM information_schema.columns
                WHERE table_name = 'portal_integracoes'
                AND column_name IN ('protocolo', 'protocolo_portal', 'lote_id', 'status')
                ORDER BY ordinal_position
            """))
            
            for row in result:
                nullable = "NULL" if row.is_nullable == 'YES' else "NOT NULL"
                length = f"({row.character_maximum_length})" if row.character_maximum_length else ""
                print(f"  {row.column_name:20} {row.data_type}{length:10} {nullable}")
            
            # 7. Estatísticas
            print("\n📈 ESTATÍSTICAS:")
            print("-" * 40)
            
            result = db.session.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(protocolo) as com_protocolo,
                    COUNT(*) - COUNT(protocolo) as sem_protocolo
                FROM portal_integracoes
            """)).first()
            
            print(f"  Total de registros: {result.total}")
            print(f"  Com protocolo: {result.com_protocolo}")
            print(f"  Sem protocolo: {result.sem_protocolo}")
            
            # 8. Exemplos de registros
            print("\n📋 ÚLTIMOS REGISTROS:")
            print("-" * 40)
            
            result = db.session.execute(text("""
                SELECT 
                    id,
                    portal,
                    lote_id,
                    protocolo,
                    status
                FROM portal_integracoes
                ORDER BY criado_em DESC
                LIMIT 5
            """))
            
            for row in result:
                protocolo = row.protocolo or "N/A"
                print(f"  ID: {row.id} | Portal: {row.portal} | Lote: {row.lote_id}")
                print(f"     Protocolo: {protocolo} | Status: {row.status}")
            
            print("\n" + "="*60)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("="*60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO NA MIGRAÇÃO: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = executar_migracao()
    sys.exit(0 if success else 1)