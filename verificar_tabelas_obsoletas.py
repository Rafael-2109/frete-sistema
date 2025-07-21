#!/usr/bin/env python3
"""
SCRIPT DE VERIFICAÇÃO: Tabelas Obsoletas da Carteira
Verifica quais tabelas existem no banco e se contêm dados
antes de recomendar remoção das classes obsoletas.
"""

import os
import sys
from sqlalchemy import text, inspect, MetaData
from datetime import datetime

def verificar_tabelas_carteira():
    """Verifica status das tabelas obsoletas/em avaliação"""
    
    try:
        # Inicializar contexto da aplicação
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app import create_app, db
        
        app = create_app()
        
        with app.app_context():
            # Obter engine e inspector
            engine = db.engine
            inspector = inspect(engine)
            
            # Definir classes obsoletas e em avaliação
            classes_obsoletas = {
                'historico_faturamento': 'HistoricoFaturamento',
                'log_atualizacao_carteira': 'LogAtualizacaoCarteira', 
                'vinculacao_carteira_separacao': 'VinculacaoCarteiraSeparacao',
                'evento_carteira': 'EventoCarteira',
                'aprovacao_mudanca_carteira': 'AprovacaoMudancaCarteira',
                'controle_alteracao_carga': 'ControleAlteracaoCarga',
                'controle_descasamento_nf': 'ControleDescasamentoNF',
                'snapshot_carteira': 'SnapshotCarteira',
                'tipo_envio': 'TipoEnvio'
            }
            
            classes_avaliacao = {
                'carteira_copia': 'CarteiraCopia',
                'controle_cruzado_separacao': 'ControleCruzadoSeparacao',
                'tipo_carga': 'TipoCarga',
                'saldo_standby': 'SaldoStandby'
            }
            
            # Obter todas as tabelas do banco
            tabelas_existentes = inspector.get_table_names()
            
            print("🔍 VERIFICAÇÃO DE TABELAS OBSOLETAS/EM AVALIAÇÃO")
            print("=" * 60)
            print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            print(f"📊 Total de tabelas no banco: {len(tabelas_existentes)}")
            print()
            
            # Verificar classes obsoletas
            print("🔴 CLASSES OBSOLETAS (recomendadas para remoção)")
            print("-" * 60)
            
            obsoletas_com_dados = []
            obsoletas_vazias = []
            obsoletas_inexistentes = []
            
            for nome_tabela, nome_classe in classes_obsoletas.items():
                if nome_tabela in tabelas_existentes:
                    try:
                        # Contar registros
                        result = engine.execute(text(f"SELECT COUNT(*) as count FROM {nome_tabela}"))
                        count = result.fetchone()['count']
                        
                        # Obter informações da tabela
                        colunas = inspector.get_columns(nome_tabela)
                        indices = inspector.get_indexes(nome_tabela)
                        fks = inspector.get_foreign_keys(nome_tabela)
                        
                        status = "🔴 COM DADOS" if count > 0 else "🟡 VAZIA"
                        
                        print(f"{status} {nome_classe}")
                        print(f"  📋 Tabela: {nome_tabela}")
                        print(f"  📊 Registros: {count:,}")
                        print(f"  📁 Colunas: {len(colunas)}")
                        print(f"  🔑 Índices: {len(indices)}")
                        print(f"  🔗 Foreign Keys: {len(fks)}")
                        
                        if count > 0:
                            obsoletas_com_dados.append((nome_tabela, nome_classe, count))
                        else:
                            obsoletas_vazias.append((nome_tabela, nome_classe))
                            
                        print()
                        
                    except Exception as e:
                        print(f"❌ ERRO ao verificar {nome_classe}: {e}")
                        print()
                else:
                    print(f"⚪ NÃO EXISTE {nome_classe} (tabela: {nome_tabela})")
                    obsoletas_inexistentes.append((nome_tabela, nome_classe))
                    print()
            
            # Verificar classes em avaliação
            print("\n🟡 CLASSES EM AVALIAÇÃO")
            print("-" * 60)
            
            avaliacao_com_dados = []
            avaliacao_vazias = []
            avaliacao_inexistentes = []
            
            for nome_tabela, nome_classe in classes_avaliacao.items():
                if nome_tabela in tabelas_existentes:
                    try:
                        # Contar registros
                        result = engine.execute(text(f"SELECT COUNT(*) as count FROM {nome_tabela}"))
                        count = result.fetchone()['count']
                        
                        # Obter informações da tabela
                        colunas = inspector.get_columns(nome_tabela)
                        indices = inspector.get_indexes(nome_tabela)
                        fks = inspector.get_foreign_keys(nome_tabela)
                        
                        status = "🔴 COM DADOS" if count > 0 else "🟡 VAZIA"
                        
                        print(f"{status} {nome_classe}")
                        print(f"  📋 Tabela: {nome_tabela}")
                        print(f"  📊 Registros: {count:,}")
                        print(f"  📁 Colunas: {len(colunas)}")
                        print(f"  🔑 Índices: {len(indices)}")
                        print(f"  🔗 Foreign Keys: {len(fks)}")
                        
                        if count > 0:
                            avaliacao_com_dados.append((nome_tabela, nome_classe, count))
                        else:
                            avaliacao_vazias.append((nome_tabela, nome_classe))
                            
                        print()
                        
                    except Exception as e:
                        print(f"❌ ERRO ao verificar {nome_classe}: {e}")
                        print()
                else:
                    print(f"⚪ NÃO EXISTE {nome_classe} (tabela: {nome_tabela})")
                    avaliacao_inexistentes.append((nome_tabela, nome_classe))
                    print()
            
            # Resumo executivo
            print("\n📊 RESUMO EXECUTIVO")
            print("=" * 60)
            
            print(f"\n🔴 CLASSES OBSOLETAS:")
            print(f"  ✅ Com dados: {len(obsoletas_com_dados)}")
            print(f"  🟡 Vazias: {len(obsoletas_vazias)}")
            print(f"  ⚪ Inexistentes: {len(obsoletas_inexistentes)}")
            
            print(f"\n🟡 CLASSES EM AVALIAÇÃO:")
            print(f"  ✅ Com dados: {len(avaliacao_com_dados)}")
            print(f"  🟡 Vazias: {len(avaliacao_vazias)}")
            print(f"  ⚪ Inexistentes: {len(avaliacao_inexistentes)}")
            
            # Recomendações específicas
            print("\n🎯 RECOMENDAÇÕES ESPECÍFICAS")
            print("=" * 60)
            
            if obsoletas_vazias or obsoletas_inexistentes:
                print(f"\n✅ REMOVER IMEDIATAMENTE ({len(obsoletas_vazias + obsoletas_inexistentes)} classes):")
                for tabela, classe in obsoletas_vazias + obsoletas_inexistentes:
                    print(f"  - {classe} ({tabela})")
                    
            if obsoletas_com_dados:
                print(f"\n⚠️  ANALISAR ANTES DE REMOVER ({len(obsoletas_com_dados)} classes):")
                for tabela, classe, count in obsoletas_com_dados:
                    print(f"  - {classe} ({tabela}) - {count:,} registros")
                    
            if avaliacao_vazias or avaliacao_inexistentes:
                print(f"\n🤔 AVALIAR NECESSIDADE ({len(avaliacao_vazias + avaliacao_inexistentes)} classes):")
                for tabela, classe in avaliacao_vazias + avaliacao_inexistentes:
                    print(f"  - {classe} ({tabela})")
                    
            if avaliacao_com_dados:
                print(f"\n🔍 INVESTIGAR USO REAL ({len(avaliacao_com_dados)} classes):")
                for tabela, classe, count in avaliacao_com_dados:
                    print(f"  - {classe} ({tabela}) - {count:,} registros")
            
            # Script de limpeza sugerido
            if obsoletas_vazias or obsoletas_inexistentes:
                print("\n🛠️  SCRIPT DE LIMPEZA SUGERIDO")
                print("=" * 60)
                print("""
# 1. Remover imports desnecessários de __init__.py
# 2. Remover classes do models.py
# 3. Criar migration para remover tabelas vazias:

def upgrade():
    # Drop tabelas vazias""")
                
                for tabela, classe in obsoletas_vazias:
                    print(f"    op.drop_table('{tabela}')  # {classe}")
                    
                print("""
def downgrade():
    # Opcional: recriar estruturas se necessário
    pass
                """)
            
            return True
            
    except Exception as e:
        print(f"❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executa verificação completa"""
    print("🔍 INICIANDO VERIFICAÇÃO DE TABELAS OBSOLETAS")
    print("=" * 60)
    print("Este script verifica quais tabelas existem no banco")
    print("e se contêm dados antes de recomendar remoção.")
    print()
    
    try:
        sucesso = verificar_tabelas_carteira()
        
        if sucesso:
            print("\n✅ VERIFICAÇÃO CONCLUÍDA COM SUCESSO!")
            print("📋 Consulte as recomendações acima para decidir sobre remoção.")
            return 0
        else:
            print("\n❌ VERIFICAÇÃO FALHOU!")
            print("🔧 Verifique a conexão com o banco e tente novamente.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Verificação interrompida pelo usuário.")
        return 1
    except Exception as e:
        print(f"\n💥 ERRO INESPERADO: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)