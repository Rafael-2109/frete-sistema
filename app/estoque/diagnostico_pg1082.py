"""
Endpoint de diagnóstico para erro PG 1082
Permite testar e diagnosticar o problema em produção
"""
from flask import Blueprint, jsonify
from app import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

pg1082_bp = Blueprint('pg1082', __name__, url_prefix='/diagnostico')

@pg1082_bp.route('/pg1082', methods=['GET'])
def diagnostico_pg1082():
    """
    Diagnóstico completo do erro PG 1082
    Testa diferentes abordagens e retorna relatório
    """
    resultado = {
        'status': 'iniciado',
        'testes': [],
        'erro_pg1082_presente': False,
        'solucao_funcionando': False
    }
    
    try:
        # TESTE 1: Query simples com DATE
        teste1 = {'nome': 'Query simples com DATE', 'status': 'pendente'}
        try:
            result = db.session.execute(text("""
                SELECT data_projecao FROM projecao_estoque_cache LIMIT 1
            """))
            result.fetchone()
            teste1['status'] = 'sucesso'
            teste1['mensagem'] = 'DATE funcionando normalmente'
        except Exception as e:
            if "1082" in str(e):
                teste1['status'] = 'erro_pg1082'
                teste1['mensagem'] = str(e)
                resultado['erro_pg1082_presente'] = True
            else:
                teste1['status'] = 'erro_outro'
                teste1['mensagem'] = str(e)
        resultado['testes'].append(teste1)
        
        # TESTE 2: Query com TO_CHAR
        teste2 = {'nome': 'Query com TO_CHAR', 'status': 'pendente'}
        try:
            result = db.session.execute(text("""
                SELECT TO_CHAR(data_projecao, 'YYYY-MM-DD') as data_str 
                FROM projecao_estoque_cache LIMIT 1
            """))
            row = result.fetchone()
            teste2['status'] = 'sucesso'
            teste2['mensagem'] = f'TO_CHAR funcionando: {row[0] if row else "sem dados"}'
            resultado['solucao_funcionando'] = True
        except Exception as e:
            teste2['status'] = 'erro'
            teste2['mensagem'] = str(e)
        resultado['testes'].append(teste2)
        
        # TESTE 3: Query sem campo DATE
        teste3 = {'nome': 'Query sem DATE', 'status': 'pendente'}
        try:
            result = db.session.execute(text("""
                SELECT cod_produto, dia_offset, estoque_inicial 
                FROM projecao_estoque_cache LIMIT 1
            """))
            row = result.fetchone()
            teste3['status'] = 'sucesso'
            teste3['mensagem'] = 'Query sem DATE funcionando'
        except Exception as e:
            teste3['status'] = 'erro'
            teste3['mensagem'] = str(e)
        resultado['testes'].append(teste3)
        
        # TESTE 4: Função segura
        teste4 = {'nome': 'Função cache segura', 'status': 'pendente'}
        try:
            from app.estoque.cache_fix_pg1082 import obter_cache_seguro
            # Testar com um produto qualquer
            result = db.session.execute(text("""
                SELECT DISTINCT cod_produto FROM saldo_estoque_cache LIMIT 1
            """))
            row = result.fetchone()
            if row:
                cache_data = obter_cache_seguro(row[0])
                if cache_data:
                    teste4['status'] = 'sucesso'
                    teste4['mensagem'] = f'Cache obtido para produto {row[0]}'
                    teste4['dados'] = {
                        'produto': cache_data['cod_produto'],
                        'estoque': cache_data['estoque_inicial'],
                        'projecoes': len(cache_data.get('projecao_29_dias', []))
                    }
                else:
                    teste4['status'] = 'aviso'
                    teste4['mensagem'] = 'Função executou mas sem dados'
            else:
                teste4['status'] = 'aviso'
                teste4['mensagem'] = 'Sem produtos no cache para testar'
        except Exception as e:
            teste4['status'] = 'erro'
            teste4['mensagem'] = str(e)
        resultado['testes'].append(teste4)
        
        # TESTE 5: Verificar registro de tipos
        teste5 = {'nome': 'Registro de tipos PG', 'status': 'pendente'}
        try:
            import psycopg2
            from psycopg2 import extensions
            
            # Verificar se tipos estão registrados
            teste5['status'] = 'info'
            teste5['mensagem'] = 'psycopg2 disponível'
            teste5['detalhes'] = {
                'versao_psycopg2': psycopg2.__version__,
                'database_url_inicio': db.engine.url.drivername[:20]
            }
        except Exception as e:
            teste5['status'] = 'aviso'
            teste5['mensagem'] = f'psycopg2 não disponível: {e}'
        resultado['testes'].append(teste5)
        
        # Resumo final
        if resultado['erro_pg1082_presente']:
            if resultado['solucao_funcionando']:
                resultado['status'] = 'corrigido'
                resultado['mensagem'] = 'Erro PG 1082 detectado mas solução TO_CHAR está funcionando'
            else:
                resultado['status'] = 'erro'
                resultado['mensagem'] = 'Erro PG 1082 presente e sem solução funcionando'
        else:
            resultado['status'] = 'ok'
            resultado['mensagem'] = 'Sem erro PG 1082 detectado'
        
        return jsonify(resultado), 200
        
    except Exception as e:
        resultado['status'] = 'erro_critico'
        resultado['mensagem'] = str(e)
        return jsonify(resultado), 500

@pg1082_bp.route('/pg1082/fix', methods=['POST'])
def aplicar_fix_pg1082():
    """
    Aplica correção forçada para PG 1082
    """
    try:
        from app.estoque.pg_register import force_register_global, setup_pg_types
        from app import create_app
        
        # Forçar registro global
        force_register_global()
        
        # Tentar configurar no app
        app = create_app()
        setup_pg_types(app)
        
        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Registro de tipos forçado com sucesso',
            'acoes': [
                'Tipos registrados globalmente',
                'Listener configurado para novas conexões'
            ]
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': str(e)
        }), 500