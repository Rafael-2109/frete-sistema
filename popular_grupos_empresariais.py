#!/usr/bin/env python3
"""
🏢 POPULAR GRUPOS EMPRESARIAIS NO KNOWLEDGE BASE
Script para inserir os grupos empresariais conhecidos no sistema de aprendizado
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text
from config import Config

def popular_grupos_empresariais():
    """Popula os grupos empresariais conhecidos no knowledge base"""
    print("\n" + "="*80)
    print("🏢 POPULANDO GRUPOS EMPRESARIAIS NO KNOWLEDGE BASE")
    print("="*80 + "\n")
    
    app = create_app()
    
    # Detectar tipo de banco
    is_postgresql = 'postgresql' in Config.SQLALCHEMY_DATABASE_URI.lower()
    is_production = os.getenv('RENDER', 'false').lower() == 'true' or is_postgresql
    
    print(f"🗄️ Banco de dados: {'PostgreSQL (Produção)' if is_postgresql else 'SQLite (Local)'}")
    print(f"🌍 Ambiente: {'Produção (Render)' if is_production else 'Desenvolvimento'}")
    
    with app.app_context():
        try:
            # Verificar se tabela existe
            result = db.session.execute(text("SELECT COUNT(*) FROM ai_grupos_empresariais")).scalar()
            print(f"\n📊 Grupos existentes: {result}")
            
            if result and result > 0:
                print("⚠️ Já existem grupos cadastrados. Deseja continuar? (s/n)")
                # Em produção, sempre continua
                if not is_production:
                    resposta = input().lower()
                    if resposta != 's':
                        print("❌ Operação cancelada pelo usuário")
                        return False
            
            # Definir grupos empresariais conhecidos
            grupos_empresariais = [
                {
                    'nome_grupo': 'Assai',
                    'tipo_negocio': 'Atacarejo',
                    'cnpj_prefixos': ['06.057.223/'] if is_postgresql else '["06.057.223/"]',
                    'palavras_chave': ['assai', 'assaí'] if is_postgresql else '["assai", "assaí"]',
                    'filtro_sql': "nome_cliente ILIKE '%assai%'",
                    'regras_deteccao': {'cnpj_method': 'prefix', 'nome_method': 'fuzzy', 'threshold': 0.8} if is_postgresql else '{"cnpj_method": "prefix", "nome_method": "fuzzy", "threshold": 0.8}',
                    'estatisticas': {'clientes_conhecidos': 50, 'volume_mensal': 'alto'} if is_postgresql else '{"clientes_conhecidos": 50, "volume_mensal": "alto"}'
                },
                {
                    'nome_grupo': 'Atacadão',
                    'tipo_negocio': 'Atacarejo',
                    'cnpj_prefixos': ['75.315.333/', '00.063.960/', '93.209.765/'] if is_postgresql else '["75.315.333/", "00.063.960/", "93.209.765/"]',
                    'palavras_chave': ['atacadao', 'atacadão'] if is_postgresql else '["atacadao", "atacadão"]',
                    'filtro_sql': "nome_cliente ILIKE '%atacad%'",
                    'regras_deteccao': {'cnpj_method': 'multiple_prefix', 'nome_method': 'contains', 'variations': ['atacadao', 'atacadão']} if is_postgresql else '{"cnpj_method": "multiple_prefix", "nome_method": "contains", "variations": ["atacadao", "atacadão"]}',
                    'estatisticas': {'clientes_conhecidos': 80, 'volume_mensal': 'muito_alto'} if is_postgresql else '{"clientes_conhecidos": 80, "volume_mensal": "muito_alto"}'
                },
                {
                    'nome_grupo': 'Carrefour',
                    'tipo_negocio': 'Varejo',
                    'cnpj_prefixos': ['45.543.915/'] if is_postgresql else '["45.543.915/"]',
                    'palavras_chave': ['carrefour'] if is_postgresql else '["carrefour"]',
                    'filtro_sql': "nome_cliente ILIKE '%carrefour%'",
                    'regras_deteccao': {'cnpj_method': 'prefix', 'nome_method': 'exact', 'case_sensitive': False} if is_postgresql else '{"cnpj_method": "prefix", "nome_method": "exact", "case_sensitive": false}',
                    'estatisticas': {'clientes_conhecidos': 120, 'volume_mensal': 'alto'} if is_postgresql else '{"clientes_conhecidos": 120, "volume_mensal": "alto"}'
                },
                {
                    'nome_grupo': 'Tenda',
                    'tipo_negocio': 'Atacarejo',
                    'cnpj_prefixos': ['01.157.555/'] if is_postgresql else '["01.157.555/"]',
                    'palavras_chave': ['tenda'] if is_postgresql else '["tenda"]',
                    'filtro_sql': "nome_cliente ILIKE '%tenda%'",
                    'regras_deteccao': {'cnpj_method': 'prefix', 'nome_method': 'contains'} if is_postgresql else '{"cnpj_method": "prefix", "nome_method": "contains"}',
                    'estatisticas': {'clientes_conhecidos': 25, 'volume_mensal': 'medio'} if is_postgresql else '{"clientes_conhecidos": 25, "volume_mensal": "medio"}'
                },
                {
                    'nome_grupo': 'Mateus',
                    'tipo_negocio': 'Varejo Regional',
                    'cnpj_prefixos': ['12.545.228/', '58.217.678/', '23.583.231/'] if is_postgresql else '["12.545.228/", "58.217.678/", "23.583.231/"]',
                    'palavras_chave': ['mateus', 'grupo mateus'] if is_postgresql else '["mateus", "grupo mateus"]',
                    'filtro_sql': "nome_cliente ILIKE '%mateus%'",
                    'regras_deteccao': {'cnpj_method': 'multiple_prefix', 'nome_method': 'contains', 'regional': 'nordeste'} if is_postgresql else '{"cnpj_method": "multiple_prefix", "nome_method": "contains", "regional": "nordeste"}',
                    'estatisticas': {'clientes_conhecidos': 45, 'volume_mensal': 'alto', 'regiao': 'nordeste'} if is_postgresql else '{"clientes_conhecidos": 45, "volume_mensal": "alto", "regiao": "nordeste"}'
                },
                {
                    'nome_grupo': 'Fort Atacadista',
                    'tipo_negocio': 'Atacarejo',
                    'cnpj_prefixos': ['13.481.309/'] if is_postgresql else '["13.481.309/"]',
                    'palavras_chave': ['fort', 'fort atacadista'] if is_postgresql else '["fort", "fort atacadista"]',
                    'filtro_sql': "nome_cliente ILIKE '%fort%'",
                    'regras_deteccao': {'cnpj_method': 'prefix', 'nome_method': 'contains'} if is_postgresql else '{"cnpj_method": "prefix", "nome_method": "contains"}',
                    'estatisticas': {'clientes_conhecidos': 20, 'volume_mensal': 'medio'} if is_postgresql else '{"clientes_conhecidos": 20, "volume_mensal": "medio"}'
                },
                {
                    'nome_grupo': 'Coco Bambu',
                    'tipo_negocio': 'Restaurantes',
                    'cnpj_prefixos': ['08.193.805/'] if is_postgresql else '["08.193.805/"]',
                    'palavras_chave': ['coco bambu', 'coco', 'bambu'] if is_postgresql else '["coco bambu", "coco", "bambu"]',
                    'filtro_sql': "nome_cliente ILIKE '%coco%' OR nome_cliente ILIKE '%bambu%'",
                    'regras_deteccao': {'cnpj_method': 'prefix', 'nome_method': 'multi_keyword'} if is_postgresql else '{"cnpj_method": "prefix", "nome_method": "multi_keyword"}',
                    'estatisticas': {'clientes_conhecidos': 15, 'volume_mensal': 'baixo', 'segmento': 'alimentacao'} if is_postgresql else '{"clientes_conhecidos": 15, "volume_mensal": "baixo", "segmento": "alimentacao"}'
                },
                {
                    'nome_grupo': 'Mercantil Rodrigues',
                    'tipo_negocio': 'Atacarejo Regional',
                    'cnpj_prefixos': ['07.709.118/'] if is_postgresql else '["07.709.118/"]',
                    'palavras_chave': ['mercantil rodrigues', 'rodrigues'] if is_postgresql else '["mercantil rodrigues", "rodrigues"]',
                    'filtro_sql': "nome_cliente ILIKE '%rodrigues%' OR nome_cliente ILIKE '%mercantil%'",
                    'regras_deteccao': {'cnpj_method': 'prefix', 'nome_method': 'multi_keyword', 'regional': 'nordeste'} if is_postgresql else '{"cnpj_method": "prefix", "nome_method": "multi_keyword", "regional": "nordeste"}',
                    'estatisticas': {'clientes_conhecidos': 30, 'volume_mensal': 'medio', 'regiao': 'nordeste'} if is_postgresql else '{"clientes_conhecidos": 30, "volume_mensal": "medio", "regiao": "nordeste"}'
                }
            ]
            
            print(f"\n🔧 Inserindo {len(grupos_empresariais)} grupos empresariais...")
            
            inseridos = 0
            atualizados = 0
            erros = 0
            
            for grupo in grupos_empresariais:
                try:
                    # Verificar se grupo já existe
                    existe = db.session.execute(
                        text("SELECT COUNT(*) FROM ai_grupos_empresariais WHERE nome_grupo = :nome"),
                        {"nome": grupo['nome_grupo']}
                    ).scalar()
                    
                    if existe and existe > 0:
                        # Atualizar grupo existente
                        db.session.execute(
                            text("""
                                UPDATE ai_grupos_empresariais 
                                SET tipo_negocio = :tipo,
                                    cnpj_prefixos = :cnpjs,
                                    palavras_chave = :palavras,
                                    filtro_sql = :filtro,
                                    regras_deteccao = :regras,
                                    estatisticas = :stats,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE nome_grupo = :nome
                            """),
                            {
                                "nome": grupo['nome_grupo'],
                                "tipo": grupo['tipo_negocio'],
                                "cnpjs": grupo['cnpj_prefixos'],
                                "palavras": grupo['palavras_chave'],
                                "filtro": grupo['filtro_sql'],
                                "regras": grupo['regras_deteccao'],
                                "stats": grupo['estatisticas']
                            }
                        )
                        atualizados += 1
                        print(f"   ✅ {grupo['nome_grupo']} (atualizado)")
                    else:
                        # Inserir novo grupo
                        db.session.execute(
                            text("""
                                INSERT INTO ai_grupos_empresariais 
                                (nome_grupo, tipo_negocio, cnpj_prefixos, palavras_chave, 
                                 filtro_sql, regras_deteccao, estatisticas, ativo)
                                VALUES (:nome, :tipo, :cnpjs, :palavras, :filtro, :regras, :stats, TRUE)
                            """),
                            {
                                "nome": grupo['nome_grupo'],
                                "tipo": grupo['tipo_negocio'],
                                "cnpjs": grupo['cnpj_prefixos'],
                                "palavras": grupo['palavras_chave'],
                                "filtro": grupo['filtro_sql'],
                                "regras": grupo['regras_deteccao'],
                                "stats": grupo['estatisticas']
                            }
                        )
                        inseridos += 1
                        print(f"   ✅ {grupo['nome_grupo']} (inserido)")
                        
                except Exception as e:
                    erros += 1
                    print(f"   ❌ Erro ao processar {grupo['nome_grupo']}: {str(e)[:50]}...")
            
            # Commit das alterações
            db.session.commit()
            
            print(f"\n📊 RESUMO:")
            print(f"   • Inseridos: {inseridos}")
            print(f"   • Atualizados: {atualizados}")
            print(f"   • Erros: {erros}")
            print(f"   • Total processado: {len(grupos_empresariais)}")
            
            # Verificar resultado final
            total_grupos = db.session.execute(
                text("SELECT COUNT(*) FROM ai_grupos_empresariais WHERE ativo = TRUE")
            ).scalar()
            
            print(f"\n✅ GRUPOS EMPRESARIAIS ATIVOS: {total_grupos}")
            
            # Listar grupos cadastrados
            grupos_cadastrados = db.session.execute(
                text("""
                    SELECT nome_grupo, tipo_negocio, array_length(cnpj_prefixos, 1) as qtd_cnpjs
                    FROM ai_grupos_empresariais 
                    WHERE ativo = TRUE 
                    ORDER BY nome_grupo
                """ if is_postgresql else """
                    SELECT nome_grupo, tipo_negocio
                    FROM ai_grupos_empresariais 
                    WHERE ativo = 1 
                    ORDER BY nome_grupo
                """)
            ).fetchall()
            
            print(f"\n📋 GRUPOS CADASTRADOS:")
            for grupo in grupos_cadastrados:
                if is_postgresql:
                    print(f"   • {grupo[0]} ({grupo[1]}) - {grupo[2] or 0} CNPJs")
                else:
                    print(f"   • {grupo[0]} ({grupo[1]})")
            
            print("\n🎉 GRUPOS EMPRESARIAIS POPULADOS COM SUCESSO!")
            print("\n💡 BENEFÍCIOS:")
            print("1. Claude AI agora detecta automaticamente esses clientes")
            print("2. Consultas como 'entregas do Assai' funcionarão melhor")
            print("3. Sistema aprenderá padrões específicos de cada grupo")
            print("4. Análises serão mais precisas e contextualizadas")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO GERAL: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

if __name__ == "__main__":
    print(f"Inicio: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    sucesso = popular_grupos_empresariais()
    
    print(f"\nFim: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    if sucesso:
        print("\n🚀 PRÓXIMO PASSO: Teste o Claude AI com consultas como:")
        print("   • 'Entregas do Assai em junho'")
        print("   • 'Faturamento do Atacadão'") 
        print("   • 'Pedidos pendentes do Carrefour'")
        print("\n🧠 O sistema agora reconhecerá esses clientes automaticamente!")
    else:
        print("\n❌ Houve erros na operação. Verifique os logs acima.")
    
    print("\n" + "="*80) 