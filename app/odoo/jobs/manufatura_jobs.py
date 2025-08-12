"""
Jobs de Integração Manufatura com Odoo
=======================================

Jobs agendados para sincronização do módulo Manufatura com Odoo.
Utiliza APScheduler para execução periódica.

Autor: Sistema de Fretes
Data: 2025-08-10
"""

import logging
from app import db
from app.odoo.services.manufatura_service import ManufaturaOdooService
from app.manufatura.services.ordem_producao_service import OrdemProducaoService
from app.manufatura.models import LogIntegracao

logger = logging.getLogger(__name__)


def job_importar_requisicoes_compras():
    """
    Job para importar requisições de compras do Odoo
    Executa a cada 1 hora
    """
    logger.info("Iniciando job de importação de requisições de compras")
    
    try:
        service = ManufaturaOdooService()
        resultado = service.importar_requisicoes_compras()
        
        logger.info(f"Job de requisições concluído: {resultado}")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro no job de requisições: {e}")
        
        # Registrar erro no log
        log = LogIntegracao(
            tipo_integracao='job_requisicoes',
            status='erro',
            mensagem=str(e),
            registros_processados=0,
            registros_erro=1
        )
        db.session.add(log)
        db.session.commit()
        
        return {'sucesso': False, 'erro': str(e)}


def job_importar_pedidos_compras():
    """
    Job para importar pedidos de compras do Odoo
    Executa a cada 2 horas
    """
    logger.info("Iniciando job de importação de pedidos de compras")
    
    try:
        service = ManufaturaOdooService()
        resultado = service.importar_pedidos_compras()
        
        logger.info(f"Job de pedidos concluído: {resultado}")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro no job de pedidos: {e}")
        
        # Registrar erro no log
        log = LogIntegracao(
            tipo_integracao='job_pedidos',
            status='erro',
            mensagem=str(e),
            registros_processados=0,
            registros_erro=1
        )
        db.session.add(log)
        db.session.commit()
        
        return {'sucesso': False, 'erro': str(e)}


def job_sincronizar_producao():
    """
    Job para sincronizar ordens de produção com Odoo
    Executa a cada 30 minutos
    """
    logger.info("Iniciando job de sincronização de produção")
    
    try:
        service = ManufaturaOdooService()
        resultado = service.sincronizar_producao()
        
        logger.info(f"Job de sincronização concluído: {resultado}")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro no job de sincronização: {e}")
        
        # Registrar erro no log
        log = LogIntegracao(
            tipo_integracao='job_sincronizacao',
            status='erro',
            mensagem=str(e),
            registros_processados=0,
            registros_erro=1
        )
        db.session.add(log)
        db.session.commit()
        
        return {'sucesso': False, 'erro': str(e)}


def job_gerar_ordens_mto():
    """
    Job para gerar ordens MTO automaticamente
    Executa a cada 4 horas
    """
    logger.info("Iniciando job de geração de ordens MTO")
    
    try:
        service = OrdemProducaoService()
        ordens = service.gerar_ordens_mto_automaticas()
        
        resultado = {
            'sucesso': True,
            'ordens_criadas': len(ordens),
            'mensagem': f'{len(ordens)} ordens MTO criadas automaticamente'
        }
        
        # Registrar sucesso no log
        if ordens:
            log = LogIntegracao(
                tipo_integracao='job_gerar_mto',
                status='sucesso',
                mensagem=resultado['mensagem'],
                registros_processados=len(ordens),
                registros_erro=0
            )
            db.session.add(log)
            db.session.commit()
        
        logger.info(f"Job MTO concluído: {resultado}")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro no job MTO: {e}")
        
        # Registrar erro no log
        log = LogIntegracao(
            tipo_integracao='job_gerar_mto',
            status='erro',
            mensagem=str(e),
            registros_processados=0,
            registros_erro=1
        )
        db.session.add(log)
        db.session.commit()
        
        return {'sucesso': False, 'erro': str(e)}


def job_importar_historico_mensal():
    """
    Job para importar histórico mensal de pedidos
    Executa 1 vez por mês
    """
    from datetime import datetime, timedelta
    
    logger.info("Iniciando job de importação de histórico mensal")
    
    try:
        # Importar dados do mês anterior
        hoje = datetime.now()
        mes_anterior = hoje.month - 1 if hoje.month > 1 else 12
        ano_anterior = hoje.year if hoje.month > 1 else hoje.year - 1
        
        service = ManufaturaOdooService()
        resultado = service.importar_historico_pedidos(mes_anterior, ano_anterior)
        
        logger.info(f"Job de histórico concluído: {resultado}")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro no job de histórico: {e}")
        
        # Registrar erro no log
        log = LogIntegracao(
            tipo_integracao='job_historico',
            status='erro',
            mensagem=str(e),
            registros_processados=0,
            registros_erro=1
        )
        db.session.add(log)
        db.session.commit()
        
        return {'sucesso': False, 'erro': str(e)}


def registrar_jobs_manufatura(scheduler):
    """
    Registra todos os jobs de manufatura no scheduler
    
    Args:
        scheduler: Instância do APScheduler
    """
    logger.info("⚠️ Jobs de Manufatura DESATIVADOS temporariamente para deploy")
    
    # JOBS DESATIVADOS TEMPORARIAMENTE PARA DEPLOY NO RENDER
    # Descomente as linhas abaixo após confirmar que o deploy está estável
    
    # # Job de requisições - a cada 1 hora
    # scheduler.add_job(
    #     id='manufatura_requisicoes',
    #     func=job_importar_requisicoes_compras,
    #     trigger='interval',
    #     hours=1,
    #     name='Importar Requisições de Compras',
    #     replace_existing=True
    # )
    
    # # Job de pedidos - a cada 2 horas
    # scheduler.add_job(
    #     id='manufatura_pedidos',
    #     func=job_importar_pedidos_compras,
    #     trigger='interval',
    #     hours=1,
    #     name='Importar Pedidos de Compras',
    #     replace_existing=True
    # )
    
    # # Job de sincronização - a cada 30 minutos
    # scheduler.add_job(
    #     id='manufatura_sincronizacao',
    #     func=job_sincronizar_producao,
    #     trigger='interval',
    #     minutes=30,
    #     name='Sincronizar Produção',
    #     replace_existing=True
    # )
    
    # # Job MTO - a cada 4 horas
    # scheduler.add_job(
    #     id='manufatura_mto',
    #     func=job_gerar_ordens_mto,
    #     trigger='interval',
    #     hours=4,
    #     name='Gerar Ordens MTO',
    #     replace_existing=True
    # )
    
    # # Job histórico - 1 vez por mês (dia 5 às 02:00)
    # scheduler.add_job(
    #     id='manufatura_historico',
    #     func=job_importar_historico_mensal,
    #     trigger='cron',
    #     day=1,
    #     hour=3,
    #     minute=0,
    #     name='Importar Histórico Mensal',
    #     replace_existing=True
    # )
    
    # logger.info("Jobs de Manufatura registrados com sucesso")