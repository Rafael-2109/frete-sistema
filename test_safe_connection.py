#!/usr/bin/env python3
"""
Script para testar a conexão segura com Odoo
Verifica se o tratamento automático de campos problemáticos funciona
"""

import os
import sys

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.odoo.utils.safe_connection import get_safe_odoo_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def testar_conexao_segura():
    """Testa a conexão segura com tratamento de erros"""
    
    app = create_app()
    with app.app_context():
        try:
            logger.info("🚀 Testando conexão segura com Odoo...")
            
            # Obter conexão segura
            connection = get_safe_odoo_connection()
            
            if not connection:
                logger.error("❌ Não foi possível criar conexão segura")
                return False
            
            # Autenticar
            if not connection.authenticate():
                logger.error("❌ Falha na autenticação")
                return False
            
            logger.info("✅ Autenticado com sucesso")
            
            # Teste 1: Consulta que normalmente causaria erro
            logger.info("\n🔍 Teste 1: Consulta account.move.line com campos relacionados...")
            
            domain = [
                ('move_id.state', '=', 'posted'),
                '|',
                ('move_id.l10n_br_tipo_pedido', '=', 'venda'),
                ('move_id.l10n_br_tipo_pedido', '=', 'bonificacao')
            ]
            
            campos = [
                'id', 'move_id', 'partner_id', 'product_id',
                'quantity', 'price_unit', 'price_total', 'date'
            ]
            
            try:
                # Esta consulta deve funcionar mesmo com o problema do campo l10n_br_gnre_ok
                resultados = connection.search_read_safe(
                    'account.move.line',
                    domain,
                    campos,
                    limit=5
                )
                
                logger.info(f"✅ Consulta bem-sucedida! {len(resultados)} registros obtidos")
                
                if resultados:
                    primeiro = resultados[0]
                    logger.info(f"📊 Exemplo de registro obtido:")
                    logger.info(f"   - ID: {primeiro.get('id')}")
                    logger.info(f"   - Move ID: {primeiro.get('move_id')}")
                    logger.info(f"   - Partner ID: {primeiro.get('partner_id')}")
                    logger.info(f"   - Product ID: {primeiro.get('product_id')}")
                    logger.info(f"   - Quantity: {primeiro.get('quantity')}")
                    logger.info(f"   - Price: {primeiro.get('price_unit')}")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Erro na consulta segura: {e}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Erro geral: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

def testar_servico_faturamento():
    """Testa o serviço de faturamento com a conexão segura"""
    
    app = create_app()
    with app.app_context():
        try:
            logger.info("\n🔄 Testando serviço de faturamento com conexão segura...")
            
            from app.odoo.services.faturamento_service import FaturamentoService
            
            service = FaturamentoService()
            
            # Testar busca de faturamento
            resultado = service.obter_faturamento_otimizado(
                usar_filtro_postado=True,
                limite=5
            )
            
            if resultado.get('sucesso'):
                logger.info(f"✅ Serviço funcionando! {resultado.get('total_registros')} registros")
                logger.info(f"📊 Estatísticas: {resultado.get('estatisticas')}")
                return True
            else:
                logger.error(f"❌ Erro no serviço: {resultado.get('erro')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao testar serviço: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("TESTE DE CONEXÃO SEGURA COM ODOO")
    logger.info("=" * 60)
    
    # Teste 1: Conexão segura direta
    sucesso1 = testar_conexao_segura()
    
    # Teste 2: Serviço de faturamento
    sucesso2 = testar_servico_faturamento()
    
    logger.info("\n" + "=" * 60)
    if sucesso1 and sucesso2:
        logger.info("✅ TODOS OS TESTES PASSARAM!")
        logger.info("A conexão segura está funcionando corretamente.")
        logger.info("O sistema agora trata automaticamente campos problemáticos.")
    else:
        logger.info("❌ ALGUNS TESTES FALHARAM")
        logger.info("Verifique os logs acima para mais detalhes.")