#!/usr/bin/env python3
"""
Script para testar a inicialização do estoque localmente
Simula o ambiente do Render para validar antes do deploy
"""

import os
import sys
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def simular_ambiente_render():
    """Simula as variáveis de ambiente do Render"""
    logger.info("🔧 Simulando ambiente do Render...")
    
    # Simular DATABASE_URL do Render (ajuste conforme seu ambiente local)
    if not os.getenv('DATABASE_URL'):
        # Use sua URL de desenvolvimento local
        os.environ['DATABASE_URL'] = 'postgresql://usuario:senha@localhost/frete_sistema'
        logger.info("📝 DATABASE_URL configurada para teste local")
    
    # Habilitar inicialização do estoque
    os.environ['INIT_ESTOQUE_TEMPO_REAL'] = 'true'
    
    # Configurar Flask
    os.environ['FLASK_APP'] = 'run.py'
    os.environ['FLASK_ENV'] = 'development'
    
    logger.info("✅ Ambiente simulado configurado")


def executar_pre_start():
    """Executa o script pre_start.py"""
    logger.info("\n🚀 Executando pre_start.py...")
    
    try:
        # Importar e executar pre_start
        import pre_start
        logger.info("✅ pre_start.py executado com sucesso")
        
    except Exception as e:
        logger.error(f"❌ Erro ao executar pre_start.py: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def verificar_tabelas():
    """Verifica se as tabelas foram criadas corretamente"""
    from app import create_app, db
    from sqlalchemy import inspect
    
    logger.info("\n🔍 Verificando tabelas criadas...")
    
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        tabelas_esperadas = [
            'estoque_tempo_real',
            'movimentacao_prevista',
            'programacao_producao'
        ]
        
        tabelas_encontradas = []
        tabelas_faltando = []
        
        for tabela in tabelas_esperadas:
            if inspector.has_table(tabela):
                tabelas_encontradas.append(tabela)
                logger.info(f"✅ Tabela {tabela} encontrada")
            else:
                tabelas_faltando.append(tabela)
                logger.error(f"❌ Tabela {tabela} NÃO encontrada")
        
        return len(tabelas_faltando) == 0


def verificar_dados():
    """Verifica se os dados foram populados"""
    from app import create_app, db
    from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
    
    logger.info("\n📊 Verificando dados populados...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Contar registros
            total_estoque = EstoqueTempoReal.query.count()
            total_movs = MovimentacaoPrevista.query.count()
            
            # Produtos com estoque negativo
            negativos = EstoqueTempoReal.query.filter(
                EstoqueTempoReal.saldo_atual < 0
            ).count()
            
            # Produtos com ruptura prevista
            rupturas = EstoqueTempoReal.query.filter(
                EstoqueTempoReal.dia_ruptura.isnot(None)
            ).count()
            
            # Amostra de produtos
            amostra = EstoqueTempoReal.query.limit(5).all()
            
            logger.info(f"""
📈 ESTATÍSTICAS DOS DADOS:
─────────────────────────────
• Produtos em EstoqueTempoReal: {total_estoque}
• Movimentações Previstas: {total_movs}
• Produtos com Estoque Negativo: {negativos}
• Produtos com Ruptura Prevista: {rupturas}
─────────────────────────────
            """)
            
            if amostra:
                logger.info("📦 Amostra de produtos:")
                for produto in amostra:
                    logger.info(f"  - {produto.cod_produto}: {produto.saldo_atual:.2f} unidades")
            
            return total_estoque > 0
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar dados: {e}")
            return False


def testar_api():
    """Testa se a API de estoque está funcionando"""
    from app import create_app
    
    logger.info("\n🌐 Testando API de estoque...")
    
    app = create_app()
    
    with app.test_client() as client:
        try:
            # Testar endpoint de saldo de estoque
            response = client.get('/api/estoque/saldo/teste')
            
            if response.status_code == 404:
                logger.info("ℹ️ Produto teste não existe (esperado)")
            elif response.status_code == 200:
                logger.info(f"✅ API respondeu: {response.json}")
            else:
                logger.warning(f"⚠️ API retornou status {response.status_code}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao testar API: {e}")
            return False


def main():
    """Função principal de teste"""
    logger.info("""
╔══════════════════════════════════════════════════════╗
║     TESTE LOCAL - INICIALIZAÇÃO DO ESTOQUE          ║
╚══════════════════════════════════════════════════════╝
    """)
    
    testes_ok = True
    
    # 1. Simular ambiente
    simular_ambiente_render()
    
    # 2. Executar pre_start
    if not executar_pre_start():
        testes_ok = False
        logger.error("❌ Falha no pre_start.py")
    
    # 3. Verificar tabelas
    if not verificar_tabelas():
        testes_ok = False
        logger.error("❌ Tabelas não foram criadas corretamente")
    
    # 4. Verificar dados
    if not verificar_dados():
        logger.warning("⚠️ Dados não foram populados (pode ser normal se banco vazio)")
    
    # 5. Testar API
    if not testar_api():
        logger.warning("⚠️ API não respondeu como esperado")
    
    # Resultado final
    if testes_ok:
        logger.info("""
╔══════════════════════════════════════════════════════╗
║           TESTE CONCLUÍDO COM SUCESSO!              ║
║                                                      ║
║   Sistema pronto para deploy no Render              ║
╚══════════════════════════════════════════════════════╝
        """)
        return 0
    else:
        logger.error("""
╔══════════════════════════════════════════════════════╗
║             TESTE FALHOU - REVISAR                  ║
║                                                      ║
║   Corrija os erros antes do deploy                  ║
╚══════════════════════════════════════════════════════╝
        """)
        return 1


if __name__ == '__main__':
    sys.exit(main())