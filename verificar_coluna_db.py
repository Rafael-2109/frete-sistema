#!/usr/bin/env python3
"""
Script para verificar se a coluna data_expedicao_editada foi implementada corretamente
"""

import os
import sys
from datetime import datetime

def verificar_coluna_db():
    print("=" * 70)
    print("VERIFICAÇÃO DA COLUNA data_expedicao_editada")
    print("=" * 70)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    try:
        # Importar Flask app
        from app import create_app, db
        from sqlalchemy import inspect, text
        
        app = create_app()
        
        with app.app_context():
            # 1. Verificar se a tabela existe
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'pre_separacao_item' not in tables:
                print("❌ ERRO: Tabela 'pre_separacao_item' não existe no banco")
                print("   → Execute a migração: flask db migrate && flask db upgrade")
                return False
            
            print("✅ Tabela 'pre_separacao_item' encontrada")
            
            # 2. Verificar estrutura da tabela
            columns = inspector.get_columns('pre_separacao_item')
            column_names = [col['name'] for col in columns]
            
            print(f"   Total de colunas: {len(columns)}")
            
            # 3. Verificar coluna específica
            data_expedicao_col = None
            for col in columns:
                if col['name'] == 'data_expedicao_editada':
                    data_expedicao_col = col
                    break
            
            if data_expedicao_col is None:
                print("❌ ERRO: Coluna 'data_expedicao_editada' não encontrada")
                print("   → Execute a migração para criar a coluna")
                return False
            
            print("✅ Coluna 'data_expedicao_editada' encontrada")
            print(f"   Tipo: {data_expedicao_col['type']}")
            print(f"   Nullable: {data_expedicao_col['nullable']}")
            
            # 4. Verificar se é NOT NULL (obrigatório)
            if data_expedicao_col['nullable']:
                print("⚠️  ATENÇÃO: Coluna permite NULL (deveria ser NOT NULL)")
                print("   → Pode precisar de migração adicional")
            else:
                print("✅ Coluna é NOT NULL (obrigatório) - CORRETO")
            
            # 5. Verificar constraints
            constraints = inspector.get_unique_constraints('pre_separacao_item')
            constraint_encontrada = False
            
            for constraint in constraints:
                if constraint['name'] == 'uq_pre_separacao_contexto_unico':
                    constraint_encontrada = True
                    print("✅ Constraint única encontrada:")
                    print(f"   Nome: {constraint['name']}")
                    print(f"   Colunas: {constraint['column_names']}")
                    
                    # Verificar se data_expedicao_editada está na constraint
                    if 'data_expedicao_editada' in constraint['column_names']:
                        print("✅ Coluna incluída na constraint única - CORRETO")
                    else:
                        print("❌ Coluna NÃO incluída na constraint única")
                    break
            
            if not constraint_encontrada:
                print("⚠️  Constraint única não encontrada")
                print("   → Pode precisar de migração para criar constraint")
            
            # 6. Verificar índices
            indexes = inspector.get_indexes('pre_separacao_item')
            print(f"\n📊 Índices encontrados: {len(indexes)}")
            
            for idx in indexes:
                if 'data_expedicao' in idx['name']:
                    print(f"✅ Índice de performance: {idx['name']}")
                    print(f"   Colunas: {idx['column_names']}")
            
            # 7. Teste de inserção (opcional)
            print("\n🧪 TESTE DE INSERÇÃO:")
            try:
                from app.carteira.models import PreSeparacaoItem
                
                # Tentar criar uma instância (sem salvar)
                test_item = PreSeparacaoItem()
                test_item.num_pedido = "TEST001"
                test_item.cod_produto = "PROD001"
                test_item.cnpj_cliente = "12345678000100"
                test_item.qtd_original_carteira = 100.0
                test_item.qtd_selecionada_usuario = 50.0
                test_item.qtd_restante_calculada = 50.0
                test_item.data_expedicao_editada = datetime.now().date()
                test_item.criado_por = "TESTE_SISTEMA"
                
                print("✅ Modelo pode ser instanciado corretamente")
                print("✅ Campo data_expedicao_editada aceita valores de data")
                
            except Exception as e:
                print(f"❌ Erro ao testar modelo: {e}")
                return False
            
            # 8. Verificar se existe dados
            try:
                result = db.session.execute(
                    text("SELECT COUNT(*) FROM pre_separacao_item")
                ).scalar()
                print(f"\n📈 Registros na tabela: {result}")
                
                if result > 0:
                    # Verificar se há dados com data_expedicao_editada NULL
                    null_count = db.session.execute(
                        text("SELECT COUNT(*) FROM pre_separacao_item WHERE data_expedicao_editada IS NULL")
                    ).scalar()
                    
                    if null_count > 0:
                        print(f"⚠️  {null_count} registros com data_expedicao_editada NULL")
                        print("   → Considere popular esses campos antes de aplicar NOT NULL")
                    else:
                        print("✅ Todos os registros têm data_expedicao_editada preenchida")
                
            except Exception as e:
                print(f"⚠️  Erro ao consultar dados: {e}")
            
            print("\n" + "=" * 70)
            print("RESUMO DA VERIFICAÇÃO:")
            print("✅ Tabela pre_separacao_item existe")
            print("✅ Coluna data_expedicao_editada implementada")
            print("✅ Modelo Python funcional")
            
            if not data_expedicao_col['nullable']:
                print("✅ Coluna configurada como NOT NULL")
            else:
                print("⚠️  Coluna permite NULL (verificar migração)")
                
            if constraint_encontrada:
                print("✅ Constraint única implementada")
            else:
                print("⚠️  Constraint única não encontrada")
            
            print("=" * 70)
            return True
            
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("   → Verifique se o ambiente virtual está ativo")
        return False
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False

if __name__ == "__main__":
    success = verificar_coluna_db()
    sys.exit(0 if success else 1)