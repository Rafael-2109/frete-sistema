#!/usr/bin/env python
"""
Script de Execução - Reconciliação Separação x NF
==================================================

Este script executa a reconciliação entre Separações e NFs faturadas.
Pode ser executado manualmente ou agendado via cron.

Uso:
    python executar_reconciliacao.py [--dias DIAS]

Exemplos:
    python executar_reconciliacao.py              # Últimos 30 dias (padrão)
    python executar_reconciliacao.py --dias 7     # Últimos 7 dias
    python executar_reconciliacao.py --dias 90    # Últimos 90 dias

Para agendar via cron (executar todo dia às 2h da manhã):
    0 2 * * * cd /caminho/do/projeto && python executar_reconciliacao.py
"""

import sys
import argparse
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/reconciliacao_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """
    Função principal do script
    """
    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description='Executa reconciliação entre Separações e NFs faturadas'
    )
    parser.add_argument(
        '--dias',
        type=int,
        default=30,
        help='Número de dias retroativos para verificar (padrão: 30)'
    )
    parser.add_argument(
        '--lote',
        type=str,
        help='ID específico do lote para verificar (opcional)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Executa sem fazer alterações no banco (modo simulação)'
    )
    
    args = parser.parse_args()
    
    try:
        # Importar app e serviço
        from app import create_app, db
        from app.faturamento.services.reconciliacao_separacao_nf import ReconciliacaoSeparacaoNF
        
        # Criar contexto da aplicação
        app = create_app()
        
        with app.app_context():
            logger.info("=" * 60)
            logger.info("🚀 INICIANDO RECONCILIAÇÃO SEPARAÇÃO x NF")
            logger.info(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"📊 Parâmetros: dias={args.dias}, lote={args.lote}, dry_run={args.dry_run}")
            logger.info("=" * 60)
            
            if args.lote:
                # Verificar integridade de lote específico
                logger.info(f"🔍 Verificando integridade do lote {args.lote}")
                resultado = ReconciliacaoSeparacaoNF.verificar_integridade_lote(args.lote)
                
                if resultado['integro']:
                    logger.info(f"✅ Lote {args.lote} está íntegro")
                else:
                    logger.warning(f"⚠️ Problemas encontrados no lote {args.lote}:")
                    for problema in resultado['problemas']:
                        logger.warning(f"  - {problema}")
                    
                    # Tentar reconciliar
                    if not args.dry_run:
                        logger.info("🔄 Tentando reconciliar o lote...")
                        from app.pedidos.models import Pedido
                        pedido = Pedido.query.filter_by(separacao_lote_id=args.lote).first()
                        if pedido:
                            resultado_rec = ReconciliacaoSeparacaoNF._reconciliar_lote(
                                lote_id=args.lote,
                                num_pedido=pedido.num_pedido,
                                numero_nf=pedido.nf
                            )
                            if resultado_rec['sincronizado']:
                                db.session.commit()
                                logger.info("✅ Lote reconciliado com sucesso")
                            else:
                                logger.warning("⚠️ Lote não pôde ser totalmente reconciliado")
            else:
                # Executar reconciliação completa
                logger.info(f"🔄 Executando reconciliação dos últimos {args.dias} dias")
                
                if args.dry_run:
                    logger.info("⚠️ MODO DRY-RUN - Nenhuma alteração será salva")
                    # Em dry-run, não commitar
                    resultado = ReconciliacaoSeparacaoNF.executar_reconciliacao_completa(args.dias)
                    db.session.rollback()  # Desfazer alterações
                else:
                    resultado = ReconciliacaoSeparacaoNF.executar_reconciliacao_completa(args.dias)
                
                # Exibir resultados
                if resultado['sucesso']:
                    logger.info("=" * 60)
                    logger.info("✅ RECONCILIAÇÃO CONCLUÍDA COM SUCESSO")
                    logger.info(f"📊 Separações analisadas: {resultado['separacoes_analisadas']}")
                    logger.info(f"✅ Sincronizadas: {resultado['separacoes_sincronizadas']}")
                    logger.info(f"⚠️ Com discrepância: {resultado['separacoes_com_discrepancia']}")
                    logger.info(f"❌ Sem NF: {resultado['separacoes_sem_nf']}")
                    
                    if resultado['discrepancias']:
                        logger.info(f"📋 Total de discrepâncias encontradas: {len(resultado['discrepancias'])}")
                    
                    if resultado['erros']:
                        logger.warning(f"⚠️ Erros durante processamento: {len(resultado['erros'])}")
                    
                    logger.info("=" * 60)
                    
                    # Retornar código de sucesso
                    return 0
                else:
                    logger.error("=" * 60)
                    logger.error("❌ ERRO NA RECONCILIAÇÃO")
                    logger.error(f"Erro: {resultado.get('erro_geral', 'Erro desconhecido')}")
                    logger.error("=" * 60)
                    
                    # Retornar código de erro
                    return 1
                
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 2


if __name__ == '__main__':
    sys.exit(main())