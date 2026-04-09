#!/usr/bin/env python3
"""
Script de Deploy para Render.com
Aplica migrações e configura sistema automaticamente
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_command(cmd, description=""):
    """Executa comando e registra resultado"""
    logger.info(f"🔄 {description}: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        logger.info(f"✅ {description} - Sucesso")
        if result.stdout:
            logger.info(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} - Erro: {e}")
        if e.stdout:
            logger.error(f"Stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr}")
        return False

def check_database_connection():
    """Verifica se a conexão com o banco está funcionando"""
    try:
        from app import create_app
        from sqlalchemy import text
        app = create_app()
        with app.app_context():
            from app import db
            # Tenta uma query simples
            db.session.execute(text("SELECT 1"))
            logger.info("✅ Conexão com banco PostgreSQL funcionando (NACOM GOYA)")
            return True
    except Exception as e:
        logger.error(f"❌ Erro de conexão com banco: {e}")
        return False

def check_hora_agendamento_field():
    """Verifica se o campo hora_agendamento existe"""
    try:
        from app import create_app
        from sqlalchemy import text
        from config import IS_POSTGRESQL
        app = create_app()
        with app.app_context():
            from app import db
            
            if IS_POSTGRESQL:
                # PostgreSQL - usar information_schema
                result = db.session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'carteira_principal' 
                    AND column_name = 'hora_agendamento'
                """)).fetchone()
            else:
                # SQLite - usar PRAGMA
                result = db.session.execute(text("""
                    PRAGMA table_info(carteira_principal)
                """)).fetchall()
                # Procurar pela coluna hora_agendamento
                result = any(col[1] == 'hora_agendamento' for col in result)
                result = [True] if result else None
            
            if result:
                logger.info("✅ Campo hora_agendamento já existe")
                return True
            else:
                logger.info("⚠️ Campo hora_agendamento não existe - precisa aplicar migração")
                return False
    except Exception as e:
        logger.error(f"❌ Erro ao verificar campo: {e}")
        return False

def apply_hora_agendamento_migration():
    """Aplica a migração do campo hora_agendamento diretamente"""
    try:
        from app import create_app
        from sqlalchemy import text
        from config import IS_POSTGRESQL
        app = create_app()
        with app.app_context():
            from app import db
            
            # Aplica a migração diretamente
            logger.info("🔄 Aplicando migração hora_agendamento...")
            
            if IS_POSTGRESQL:
                # PostgreSQL suporta IF NOT EXISTS
                sql = """
                    ALTER TABLE carteira_principal 
                    ADD COLUMN IF NOT EXISTS hora_agendamento TIME
                """
            else:
                # SQLite não suporta IF NOT EXISTS, mas não falha se já existir
                sql = """
                    ALTER TABLE carteira_principal 
                    ADD COLUMN hora_agendamento TIME
                """
            
            try:
                db.session.execute(text(sql))
                db.session.commit()
                logger.info("✅ Migração hora_agendamento aplicada com sucesso")
                return True
            except Exception as inner_e:
                if "duplicate column name" in str(inner_e).lower() or "already exists" in str(inner_e).lower():
                    logger.info("✅ Campo hora_agendamento já existe (erro esperado)")
                    return True
                else:
                    raise inner_e
                    
    except Exception as e:
        logger.error(f"❌ Erro ao aplicar migração: {e}")
        return False

def main():
    """Processo principal de deploy"""
    logger.info("🚀 Iniciando Deploy no Render.com")
    
    # 1. Verificar conexão com banco
    if not check_database_connection():
        logger.error("❌ Deploy falhou - Problema de conexão com banco")
        sys.exit(1)
    
    # 2. Aplicar migrações padrão
    if not run_command("flask db upgrade", "Aplicando migrações padrão"):
        logger.warning("⚠️ Algumas migrações falharam, mas continuando...")
    
    # 3. Verificar e aplicar migração hora_agendamento
    if not check_hora_agendamento_field():
        if not apply_hora_agendamento_migration():
            logger.error("❌ Falha ao aplicar migração hora_agendamento")
            sys.exit(1)
    
    # 4. Migração: icms_aliquota + tabela emissao_cte_complementar
    run_command(
        "python scripts/migrations/add_icms_aliquota_carvia_operacoes.py",
        "Migração icms_aliquota + tabela emissao_cte_complementar"
    )

    # 5. Fix CTRC: aplicar mapa nCT→CTRC do SSW
    ctrc_map = os.path.join(
        str(Path(__file__).parent), 'migrations', 'nct_ctrc_map.json'
    )
    if os.path.exists(ctrc_map):
        run_command(
            "python scripts/migrations/apply_ctrc_map_render.py",
            "Fix CTRC: aplicar mapa SSW"
        )
    else:
        logger.info("⚠️ nct_ctrc_map.json nao encontrado — skip fix CTRC")

    # 6. Verificação final
    if check_hora_agendamento_field():
        logger.info("✅ Sistema configurado com sucesso!")
        logger.info("🎉 Deploy no Render concluído!")
    else:
        logger.error("❌ Deploy falhou - Verificação final")
        sys.exit(1)

if __name__ == "__main__":
    main() 