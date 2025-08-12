#!/usr/bin/env python3
"""
Script para adicionar campo ultima_atualizacao ao RelatorioFaturamentoImportado
"""

import sys
import os
sys.path.insert(0, '.')
os.environ['FLASK_ENV'] = 'development'

from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("=" * 60)
    print("ADICIONANDO CAMPO ultima_atualizacao")
    print("=" * 60)
    
    try:
        # Verificar se a coluna já existe
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'relatorio_faturamento_importado' 
            AND column_name = 'ultima_atualizacao'
        """))
        
        if result.rowcount > 0:
            print("✅ Campo ultima_atualizacao já existe")
        else:
            # Adicionar a coluna
            db.session.execute(text("""
                ALTER TABLE relatorio_faturamento_importado 
                ADD COLUMN ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """))
            db.session.commit()
            print("✅ Campo ultima_atualizacao adicionado com sucesso")
            
            # Atualizar registros existentes
            db.session.execute(text("""
                UPDATE relatorio_faturamento_importado 
                SET ultima_atualizacao = COALESCE(criado_em, CURRENT_TIMESTAMP)
                WHERE ultima_atualizacao IS NULL
            """))
            db.session.commit()
            print("✅ Registros existentes atualizados")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        db.session.rollback()
    
    print("=" * 60)