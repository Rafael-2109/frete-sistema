"""
Scheduler para Sincronização Incremental da Carteira com Odoo
==============================================================

Este job executa a cada 30 minutos, buscando alterações dos últimos 40 minutos.

ESTRATÉGIA DE SOBREPOSIÇÃO:
- Execução: a cada 30 minutos
- Janela de busca: 40 minutos
- Sobreposição: 10 minutos

Isso garante que mesmo durante deploys ou falhas temporárias,
nenhum dado seja perdido.

Autor: Sistema de Fretes
Data: 2025-01-19
"""

import logging
import os
from datetime import datetime
from threading import Lock
import traceback
import redis
from app import create_app, db
from app.odoo.services.carteira_service import CarteiraService
from app.utils.timezone import agora_brasil

logger = logging.getLogger(__name__)

# Lock global para evitar execuções concorrentes
_sync_lock = Lock()

# Redis para controle distribuído (se houver múltiplas instâncias)
try:
    redis_client = redis.StrictRedis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        db=int(os.environ.get('REDIS_DB', 0)),
        decode_responses=True
    )
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False
    logger.warning("⚠️ Redis não disponível - usando lock local apenas")


class SincronizacaoIncrementalJob:
    """Job de sincronização incremental com proteção contra execuções concorrentes"""

    # Configurações do job
    INTERVALO_EXECUCAO = 30  # minutos
    JANELA_BUSCA = 40  # minutos
    LOCK_TIMEOUT = 25 * 60  # 25 minutos (menor que intervalo)
    REDIS_LOCK_KEY = "carteira:sync:incremental:lock"
    REDIS_LAST_RUN_KEY = "carteira:sync:incremental:last_run"

    @classmethod
    def executar(cls):
        """
        Executa a sincronização incremental com proteção contra concorrência

        Returns:
            dict: Resultado da sincronização
        """
        inicio = datetime.now()
        logger.info("="*80)
        logger.info("🔄 INICIANDO JOB DE SINCRONIZAÇÃO INCREMENTAL")
        logger.info(f"📅 Horário: {agora_brasil().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)

        # Verificar e adquirir lock
        if not cls._adquirir_lock():
            logger.warning("⚠️ Sincronização já em execução - pulando esta vez")
            return {
                'sucesso': False,
                'motivo': 'Já existe uma sincronização em execução',
                'tempo_execucao': 0
            }

        try:
            # Criar contexto da aplicação
            app = create_app()
            with app.app_context():

                # Verificar última execução
                ultima_execucao = cls._obter_ultima_execucao()
                if ultima_execucao:
                    minutos_desde_ultima = (inicio - ultima_execucao).total_seconds() / 60
                    logger.info(f"📊 Última execução: {minutos_desde_ultima:.1f} minutos atrás")

                    # Se executou muito recentemente, pular
                    if minutos_desde_ultima < 5:
                        logger.warning("⚠️ Execução muito recente - aguardando intervalo mínimo")
                        return {
                            'sucesso': False,
                            'motivo': 'Intervalo mínimo não atingido',
                            'tempo_execucao': 0
                        }

                # Executar sincronização
                logger.info(f"🔍 Buscando alterações dos últimos {cls.JANELA_BUSCA} minutos...")

                service = CarteiraService()
                resultado = service.sincronizar_incremental(
                    minutos_janela=cls.JANELA_BUSCA,
                    primeira_execucao=False
                )

                tempo_total = (datetime.now() - inicio).total_seconds()

                if resultado.get('sucesso'):
                    logger.info("✅ SINCRONIZAÇÃO INCREMENTAL CONCLUÍDA COM SUCESSO")
                    logger.info(f"📊 Estatísticas:")
                    logger.info(f"   - Pedidos processados: {resultado.get('pedidos_processados', 0)}")
                    logger.info(f"   - Itens atualizados: {resultado.get('itens_atualizados', 0)}")
                    logger.info(f"   - Itens inseridos: {resultado.get('itens_inseridos', 0)}")
                    logger.info(f"   - Tempo total: {tempo_total:.2f} segundos")

                    # Salvar timestamp da última execução bem-sucedida
                    cls._salvar_ultima_execucao(inicio)

                else:
                    logger.error(f"❌ Erro na sincronização: {resultado.get('erro')}")

                # Adicionar timestamp ao resultado
                resultado['timestamp'] = inicio.isoformat()
                resultado['tempo_execucao'] = tempo_total

                return resultado

        except Exception as e:
            logger.error(f"❌ ERRO FATAL no job de sincronização: {e}")
            logger.error(traceback.format_exc())

            return {
                'sucesso': False,
                'erro': str(e),
                'timestamp': inicio.isoformat(),
                'tempo_execucao': (datetime.now() - inicio).total_seconds()
            }

        finally:
            # Sempre liberar o lock
            cls._liberar_lock()
            logger.info("="*80)

    @classmethod
    def _adquirir_lock(cls) -> bool:
        """
        Adquire lock para evitar execuções concorrentes

        Returns:
            bool: True se conseguiu adquirir o lock
        """
        # Tentar lock distribuído primeiro (Redis)
        if REDIS_AVAILABLE:
            try:
                # SET com NX (only if not exists) e EX (expire)
                acquired = redis_client.set(
                    cls.REDIS_LOCK_KEY,
                    datetime.now().isoformat(),
                    nx=True,
                    ex=cls.LOCK_TIMEOUT
                )
                if acquired:
                    logger.info("🔒 Lock distribuído adquirido (Redis)")
                    return True
                else:
                    return False
            except Exception as e:
                logger.warning(f"⚠️ Erro ao adquirir lock Redis: {e}")

        # Fallback para lock local
        acquired = _sync_lock.acquire(blocking=False)
        if acquired:
            logger.info("🔒 Lock local adquirido")
        return acquired

    @classmethod
    def _liberar_lock(cls):
        """Libera o lock após execução"""
        # Liberar lock distribuído
        if REDIS_AVAILABLE:
            try:
                redis_client.delete(cls.REDIS_LOCK_KEY)
                logger.info("🔓 Lock distribuído liberado (Redis)")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao liberar lock Redis: {e}")

        # Liberar lock local se estiver sendo usado
        try:
            _sync_lock.release()
            logger.info("🔓 Lock local liberado")
        except:
            pass  # Pode não estar locked

    @classmethod
    def _obter_ultima_execucao(cls) -> datetime:
        """
        Obtém timestamp da última execução bem-sucedida

        Returns:
            datetime: Timestamp ou None
        """
        if REDIS_AVAILABLE:
            try:
                timestamp_str = redis_client.get(cls.REDIS_LAST_RUN_KEY)
                if timestamp_str:
                    return datetime.fromisoformat(timestamp_str)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao obter última execução do Redis: {e}")

        return None

    @classmethod
    def _salvar_ultima_execucao(cls, timestamp: datetime):
        """
        Salva timestamp da última execução bem-sucedida

        Args:
            timestamp: Momento da execução
        """
        if REDIS_AVAILABLE:
            try:
                redis_client.set(
                    cls.REDIS_LAST_RUN_KEY,
                    timestamp.isoformat(),
                    ex=86400  # Expira em 24 horas
                )
                logger.info("💾 Timestamp salvo no Redis")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao salvar última execução no Redis: {e}")

    @classmethod
    def executar_manualmente(cls, janela_minutos: int = None):
        """
        Permite execução manual com janela customizada

        Args:
            janela_minutos: Janela de busca em minutos (opcional)

        Returns:
            dict: Resultado da sincronização
        """
        if janela_minutos:
            original = cls.JANELA_BUSCA
            cls.JANELA_BUSCA = janela_minutos
            logger.info(f"🔧 Execução manual com janela de {janela_minutos} minutos")

        try:
            return cls.executar()
        finally:
            if janela_minutos:
                cls.JANELA_BUSCA = original


# Função para registrar no scheduler
def registrar_job(scheduler):
    """
    Registra o job no APScheduler

    Args:
        scheduler: Instância do APScheduler
    """
    from apscheduler.triggers.interval import IntervalTrigger

    # Remover job existente se houver
    job_id = 'sincronizacao_incremental_carteira'

    existing_job = scheduler.get_job(job_id)
    if existing_job:
        scheduler.remove_job(job_id)
        logger.info(f"♻️ Job existente '{job_id}' removido")

    # Adicionar novo job
    scheduler.add_job(
        func=SincronizacaoIncrementalJob.executar,
        trigger=IntervalTrigger(
            minutes=SincronizacaoIncrementalJob.INTERVALO_EXECUCAO
        ),
        id=job_id,
        name='Sincronização Incremental Carteira-Odoo',
        replace_existing=True,
        max_instances=1,  # Apenas uma instância por vez
        misfire_grace_time=300  # 5 minutos de tolerância
    )

    logger.info(f"✅ Job '{job_id}' registrado - execução a cada {SincronizacaoIncrementalJob.INTERVALO_EXECUCAO} minutos")

    # Executar primeira vez em 1 minuto
    from datetime import datetime, timedelta
    run_date = datetime.now() + timedelta(minutes=1)

    scheduler.add_job(
        func=SincronizacaoIncrementalJob.executar,
        trigger='date',
        run_date=run_date,
        id=f'{job_id}_inicial',
        name='Sincronização Incremental (Primeira Execução)',
        replace_existing=True
    )

    logger.info(f"⏰ Primeira execução agendada para {run_date.strftime('%H:%M:%S')}")


if __name__ == "__main__":
    # Teste manual
    print("Executando sincronização incremental manualmente...")
    resultado = SincronizacaoIncrementalJob.executar_manualmente()
    print(f"Resultado: {resultado}")