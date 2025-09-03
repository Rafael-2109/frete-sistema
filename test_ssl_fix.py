#!/usr/bin/env python3
"""
Script de teste para verificar a correção do erro SSL na sincronização
"""
import logging
import sys
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_carteira_sync():
    """Testa a sincronização da carteira com a correção SSL"""
    try:
        logger.info("🚀 Iniciando teste de sincronização da carteira...")
        
        from app import create_app, db
        from app.odoo.services.carteira_service import CarteiraService
        from app.faturamento.models import FaturamentoProduto
        from sqlalchemy import func
        
        # Criar app context
        app = create_app()
        with app.app_context():
            logger.info("✅ Contexto da aplicação criado")
            
            # Testar conexão com banco
            from app.utils.database_helpers import ensure_connection
            if ensure_connection():
                logger.info("✅ Conexão com banco de dados OK")
            else:
                logger.error("❌ Falha na conexão com banco")
                return False
            
            # Teste 1: Query otimizada de faturamentos
            logger.info("📊 Teste 1: Query otimizada de faturamentos...")
            
            # Simular busca de faturamentos para múltiplos pedidos
            pedidos_teste = ['VCD2543425', 'VCD2543184', 'VCD2543155', 'VCD2543111']
            
            from app.utils.database_helpers import retry_on_ssl_error
            
            @retry_on_ssl_error(max_retries=3)
            def buscar_faturamentos_teste():
                resultados = db.session.query(
                    FaturamentoProduto.origem,
                    FaturamentoProduto.cod_produto,
                    func.sum(FaturamentoProduto.qtd_produto_faturado).label('qtd_faturada')
                ).filter(
                    FaturamentoProduto.origem.in_(pedidos_teste),
                    FaturamentoProduto.status_nf != 'Cancelado'
                ).group_by(
                    FaturamentoProduto.origem,
                    FaturamentoProduto.cod_produto
                ).all()
                return resultados
            
            try:
                start_time = datetime.now()
                resultados = buscar_faturamentos_teste()
                elapsed = (datetime.now() - start_time).total_seconds()
                
                logger.info(f"✅ Query executada com sucesso em {elapsed:.2f}s")
                logger.info(f"   📊 {len(resultados)} faturamentos encontrados")
                
                # Mostrar alguns resultados
                for i, row in enumerate(resultados[:5]):
                    logger.info(f"   • {row.origem}/{row.cod_produto}: {row.qtd_faturada:.2f}")
                if len(resultados) > 5:
                    logger.info(f"   ... e mais {len(resultados) - 5} registros")
                    
            except Exception as e:
                logger.error(f"❌ Erro na query de teste: {e}")
                return False
            
            # Teste 2: Verificar se o serviço de carteira funciona
            logger.info("\n📊 Teste 2: Inicializando serviço de carteira...")
            
            try:
                service = CarteiraService()
                logger.info("✅ Serviço de carteira inicializado")
                
                # Não vamos executar sincronização completa, apenas verificar se inicializa
                logger.info("✅ Todos os testes passaram com sucesso!")
                return True
                
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar serviço: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Erro geral no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("TESTE DE CORREÇÃO SSL - SINCRONIZAÇÃO CARTEIRA")
    logger.info("=" * 60)
    
    success = test_carteira_sync()
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ TESTE CONCLUÍDO COM SUCESSO")
        sys.exit(0)
    else:
        logger.error("❌ TESTE FALHOU")
        sys.exit(1)