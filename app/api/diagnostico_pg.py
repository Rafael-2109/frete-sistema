"""
Endpoint de diagnóstico para verificar tipos PostgreSQL
"""
from flask import Blueprint, jsonify
import psycopg2
from psycopg2 import extensions
from sqlalchemy import text
from app import db

diagnostico_pg_bp = Blueprint('diagnostico_pg', __name__, url_prefix='/api')

@diagnostico_pg_bp.route('/diagnostico/pg-types', methods=['GET'])
def diagnostico_pg_types():
    """
    Endpoint para verificar se os tipos PostgreSQL estão registrados corretamente
    """
    resultado = {
        'tipos_registrados': {},
        'teste_conexao': {},
        'teste_date_field': {},
        'info_sistema': {}
    }
    
    try:
        # 1. Verificar tipos registrados
        tipos_esperados = {
            'DATE (1082)': 1082,
            'TIME (1083)': 1083,
            'TIMESTAMP (1114)': 1114,
            'TIMESTAMPTZ (1184)': 1184,
            'DATEARRAY (1182)': 1182
        }
        
        for nome, oid in tipos_esperados.items():
            try:
                # Tentar obter o tipo do registro global
                tipo_registrado = extensions.string_types.get(oid)
                resultado['tipos_registrados'][nome] = {
                    'registrado': tipo_registrado is not None,
                    'detalhes': str(tipo_registrado) if tipo_registrado else 'Não registrado'
                }
            except Exception as e:
                resultado['tipos_registrados'][nome] = {
                    'registrado': False,
                    'erro': str(e)
                }
        
        # 2. Testar conexão com banco
        try:
            result = db.session.execute(text("SELECT version()"))
            version = result.scalar()
            resultado['teste_conexao']['sucesso'] = True
            resultado['teste_conexao']['versao_pg'] = version
        except Exception as e:
            resultado['teste_conexao']['sucesso'] = False
            resultado['teste_conexao']['erro'] = str(e)
        
        # 3. Testar campo DATE especificamente
        try:
            # Testar com uma query que usa campo DATE
            result = db.session.execute(text("""
                SELECT 
                    CURRENT_DATE as data_atual,
                    pg_typeof(CURRENT_DATE) as tipo_pg
            """))
            row = result.fetchone()
            resultado['teste_date_field']['sucesso'] = True
            resultado['teste_date_field']['data_atual'] = str(row[0])
            resultado['teste_date_field']['tipo_pg'] = str(row[1])
        except Exception as e:
            resultado['teste_date_field']['sucesso'] = False
            resultado['teste_date_field']['erro'] = str(e)
            resultado['teste_date_field']['tipo_erro'] = type(e).__name__
        
        # 4. Informações do sistema
        import os
        resultado['info_sistema']['ambiente'] = os.getenv('ENVIRONMENT', 'development')
        resultado['info_sistema']['database_url'] = 'postgres://' in os.getenv('DATABASE_URL', '')
        
        # 5. Testar tabela projecao_estoque_cache
        try:
            result = db.session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'projecao_estoque_cache' 
                AND column_name IN ('dia_offset', 'estoque_d0', 'estoque_d1')
                ORDER BY column_name
            """))
            colunas = result.fetchall()
            resultado['teste_date_field']['colunas_cache'] = [
                {'nome': col[0], 'tipo': col[1]} for col in colunas
            ]
        except Exception as e:
            resultado['teste_date_field']['erro_colunas'] = str(e)
        
        # Status geral
        resultado['status'] = 'OK' if all(
            t.get('registrado', False) 
            for t in resultado['tipos_registrados'].values()
        ) else 'ERRO'
        
    except Exception as e:
        resultado['erro_geral'] = str(e)
        resultado['status'] = 'ERRO'
    
    return jsonify(resultado), 200 if resultado['status'] == 'OK' else 500