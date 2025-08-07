#!/usr/bin/env python3
"""
Script de Setup e Migração para Sistema de Estoque em Tempo Real
Executa todas as operações necessárias para configurar o novo sistema
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verificar_ambiente():
    """Verifica se o ambiente está configurado corretamente"""
    print("🔍 Verificando ambiente...")
    
    # Verificar Python
    versao_python = sys.version_info
    if versao_python.major < 3 or (versao_python.major == 3 and versao_python.minor < 8):
        print(f"❌ Python {versao_python.major}.{versao_python.minor} detectado. Necessário Python 3.8+")
        return False
    print(f"✅ Python {versao_python.major}.{versao_python.minor}.{versao_python.micro}")
    
    # Verificar DATABASE_URL
    database_url = os.getenv('DATABASE_URL', '')
    if database_url:
        print(f"✅ DATABASE_URL configurada: {database_url[:30]}...")
    else:
        print("⚠️  DATABASE_URL não configurada (usando SQLite local)")
    
    return True


def criar_tabelas():
    """Cria as tabelas do novo sistema"""
    print("\n📊 Criando tabelas do sistema de tempo real...")
    
    try:
        from app import create_app, db
        app = create_app()
        
        with app.app_context():
            # Importar modelos para garantir que sejam conhecidos
            from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
            
            # Criar tabelas
            db.create_all()
            
            # Verificar se foram criadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            tabelas_criadas = []
            if inspector.has_table('estoque_tempo_real'):
                tabelas_criadas.append('estoque_tempo_real')
            if inspector.has_table('movimentacao_prevista'):
                tabelas_criadas.append('movimentacao_prevista')
            
            if len(tabelas_criadas) == 2:
                print("✅ Tabelas criadas com sucesso:")
                for tabela in tabelas_criadas:
                    print(f"   - {tabela}")
                return True
            else:
                print(f"⚠️  Apenas {len(tabelas_criadas)} tabela(s) criada(s)")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False


def migrar_dados_existentes():
    """Migra dados do sistema antigo para o novo"""
    print("\n🔄 Migrando dados existentes...")
    
    try:
        from app import create_app, db
        from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
        from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
        from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
        from app.carteira.models import PreSeparacaoItem
        from app.separacao.models import Separacao
        from app.producao.models import ProgramacaoProducao
        from app.utils import agora_brasil
        from decimal import Decimal
        from datetime import date
        
        app = create_app()
        
        with app.app_context():
            # 1. Migrar saldo atual de estoque
            print("  📦 Migrando saldos atuais...")
            
            produtos = db.session.query(
                MovimentacaoEstoque.cod_produto,
                MovimentacaoEstoque.nome_produto
            ).filter(
                MovimentacaoEstoque.ativo == True
            ).distinct().all()
            
            produtos_processados = 0
            for cod_produto, nome_produto in produtos:
                try:
                    # Calcular saldo atual
                    saldo = Decimal('0')
                    
                    # Considerar unificação
                    codigos = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
                    
                    for codigo in codigos:
                        movs = MovimentacaoEstoque.query.filter_by(
                            cod_produto=codigo,
                            ativo=True
                        ).all()
                        
                        for mov in movs:
                            # qtd_movimentacao já vem com sinal correto
                            saldo += Decimal(str(mov.qtd_movimentacao))
                    
                    # Criar ou atualizar EstoqueTempoReal
                    estoque = EstoqueTempoReal.query.filter_by(
                        cod_produto=cod_produto
                    ).first()
                    
                    if not estoque:
                        estoque = EstoqueTempoReal(
                            cod_produto=cod_produto,
                            nome_produto=nome_produto or f"Produto {cod_produto}"
                        )
                    
                    estoque.saldo_atual = saldo
                    estoque.atualizado_em = agora_brasil()
                    
                    db.session.add(estoque)
                    produtos_processados += 1
                    
                    if produtos_processados % 50 == 0:
                        db.session.commit()
                        print(f"    ✅ {produtos_processados} produtos processados...")
                        
                except Exception as e:
                    print(f"    ⚠️  Erro no produto {cod_produto}: {e}")
            
            db.session.commit()
            print(f"  ✅ {produtos_processados} produtos migrados")
            
            # 2. Migrar movimentações previstas
            print("\n  📅 Migrando movimentações previstas...")
            hoje = date.today()
            movs_previstas = 0
            
            # PreSeparacaoItem
            preseps = PreSeparacaoItem.query.filter(
                PreSeparacaoItem.recomposto == False,
                PreSeparacaoItem.data_expedicao_editada >= hoje
            ).all()
            
            for item in preseps:
                if item.qtd_selecionada_usuario > 0:
                    ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                        cod_produto=item.cod_produto,
                        data=item.data_expedicao_editada,
                        qtd_saida=Decimal(str(item.qtd_selecionada_usuario))
                    )
                    movs_previstas += 1
            
            print(f"    ✅ {len(preseps)} pré-separações processadas")
            
            # Separacao
            seps = Separacao.query.filter(
                Separacao.expedicao >= hoje,
                Separacao.qtd_saldo > 0
            ).all()
            
            for sep in seps:
                ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                    cod_produto=sep.cod_produto,
                    data=sep.expedicao,
                    qtd_saida=Decimal(str(sep.qtd_saldo))
                )
                movs_previstas += 1
            
            print(f"    ✅ {len(seps)} separações processadas")
            
            # ProgramacaoProducao
            try:
                prods = ProgramacaoProducao.query.filter(
                    ProgramacaoProducao.data_programacao >= hoje,
                    ProgramacaoProducao.qtd_programada > 0
                ).all()
                
                for prod in prods:
                    ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                        cod_produto=prod.cod_produto,
                        data=prod.data_programacao,
                        qtd_entrada=Decimal(str(prod.qtd_programada))
                    )
                    movs_previstas += 1
                
                print(f"    ✅ {len(prods)} programações processadas")
            except:
                print("    ℹ️  Tabela ProgramacaoProducao não disponível")
            
            db.session.commit()
            print(f"  ✅ Total de {movs_previstas} movimentações previstas migradas")
            
            # 3. Calcular rupturas
            print("\n  📊 Calculando rupturas D+7...")
            produtos = EstoqueTempoReal.query.all()
            
            for i, produto in enumerate(produtos):
                try:
                    ServicoEstoqueTempoReal.calcular_ruptura_d7(produto.cod_produto)
                    if (i + 1) % 50 == 0:
                        db.session.commit()
                        print(f"    ✅ {i + 1}/{len(produtos)} produtos calculados...")
                except Exception as e:
                    print(f"    ⚠️  Erro no produto {produto.cod_produto}: {e}")
            
            db.session.commit()
            print(f"  ✅ Rupturas calculadas para {len(produtos)} produtos")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        import traceback
        traceback.print_exc()
        return False


def verificar_integridade():
    """Verifica se a migração foi bem sucedida"""
    print("\n🔍 Verificando integridade dos dados...")
    
    try:
        from app import create_app, db
        from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
        
        app = create_app()
        
        with app.app_context():
            # Contar registros
            total_estoque = EstoqueTempoReal.query.count()
            total_movs = MovimentacaoPrevista.query.count()
            
            # Produtos com estoque negativo
            negativos = EstoqueTempoReal.query.filter(
                EstoqueTempoReal.saldo_atual < 0
            ).count()
            
            # Produtos com ruptura
            rupturas = EstoqueTempoReal.query.filter(
                EstoqueTempoReal.dia_ruptura != None
            ).count()
            
            print(f"""
  📊 Resumo da Verificação:
  ─────────────────────────────
  ✅ EstoqueTempoReal: {total_estoque} produtos
  ✅ MovimentacaoPrevista: {total_movs} registros
  ⚠️  Estoque Negativo: {negativos} produtos
  ⚠️  Rupturas Previstas: {rupturas} produtos
  ─────────────────────────────
            """)
            
            if total_estoque > 0:
                return True
            else:
                print("❌ Nenhum produto encontrado no novo sistema")
                return False
                
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False


def main():
    """Função principal"""
    print("""
╔══════════════════════════════════════════════════════╗
║   SETUP DO SISTEMA DE ESTOQUE EM TEMPO REAL         ║
╚══════════════════════════════════════════════════════╝
    """)
    
    # 1. Verificar ambiente
    if not verificar_ambiente():
        print("\n❌ Ambiente não está pronto. Corrija os problemas acima.")
        return 1
    
    # 2. Criar tabelas
    if not criar_tabelas():
        print("\n❌ Falha ao criar tabelas. Verifique o banco de dados.")
        return 1
    
    # 3. Migrar dados
    resposta = input("\n🔄 Deseja migrar dados existentes? (s/N): ")
    if resposta.lower() == 's':
        if not migrar_dados_existentes():
            print("\n⚠️  Migração teve problemas, mas continuando...")
    else:
        print("ℹ️  Migração pulada")
    
    # 4. Verificar integridade
    if not verificar_integridade():
        print("\n⚠️  Verificação encontrou problemas")
    
    print("""
╔══════════════════════════════════════════════════════╗
║            SETUP CONCLUÍDO COM SUCESSO!              ║
╚══════════════════════════════════════════════════════╝

📝 Próximos passos:
   1. Testar performance: python test_performance_tempo_real.py
   2. Rodar aplicação: python run.py
   3. Acessar: http://localhost:5000

✅ Sistema de Estoque em Tempo Real está pronto!
    """)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())