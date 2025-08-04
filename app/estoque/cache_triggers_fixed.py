"""
Triggers automáticos para manter o cache de estoque atualizado
VERSÃO CORRIGIDA: Não faz operações de sessão durante flush
"""
from sqlalchemy import event
from sqlalchemy.orm import Session
from app import db
from app.estoque.models import MovimentacaoEstoque
from app.estoque.models_cache import SaldoEstoqueCache, ProjecaoEstoqueCache, CacheUpdateLog
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Flag global para controlar se triggers estão ativos
TRIGGERS_ENABLED = True

def desabilitar_triggers():
    """Desabilita temporariamente os triggers"""
    global TRIGGERS_ENABLED
    TRIGGERS_ENABLED = False
    logger.info("🔴 Triggers de cache desabilitados temporariamente")

def habilitar_triggers():
    """Habilita os triggers"""
    global TRIGGERS_ENABLED
    TRIGGERS_ENABLED = True
    logger.info("🟢 Triggers de cache habilitados")

def configurar_triggers_cache():
    """
    Configura todos os triggers para atualização automática do cache
    Versão corrigida que não interfere no processo de flush
    """
    
    # 1. Trigger para MovimentacaoEstoque
    @event.listens_for(MovimentacaoEstoque, 'after_insert')
    def atualizar_cache_apos_insert_movimentacao(mapper, connection, target):
        """Atualiza cache após inserir movimentação"""
        if not TRIGGERS_ENABLED:
            return
            
        if target.ativo:
            try:
                # Apenas registrar a mudança, não fazer operações de sessão
                _registrar_mudanca_pendente(connection, 'movimentacao_estoque', 'INSERT', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger insert MovimentacaoEstoque: {e}")
    
    @event.listens_for(MovimentacaoEstoque, 'after_update')
    def atualizar_cache_apos_update_movimentacao(mapper, connection, target):
        """Atualiza cache após alterar movimentação"""
        if not TRIGGERS_ENABLED:
            return
            
        if target.ativo:
            try:
                _registrar_mudanca_pendente(connection, 'movimentacao_estoque', 'UPDATE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger update MovimentacaoEstoque: {e}")
    
    @event.listens_for(MovimentacaoEstoque, 'after_delete')
    def atualizar_cache_apos_delete_movimentacao(mapper, connection, target):
        """Atualiza cache após deletar movimentação"""
        if not TRIGGERS_ENABLED:
            return
            
        try:
            _registrar_mudanca_pendente(connection, 'movimentacao_estoque', 'DELETE', target.cod_produto)
        except Exception as e:
            logger.error(f"Erro no trigger delete MovimentacaoEstoque: {e}")
    
    
    # 2. Triggers para CarteiraPrincipal
    try:
        from app.carteira.models import CarteiraPrincipal
        
        @event.listens_for(CarteiraPrincipal, 'after_insert')
        def atualizar_cache_apos_insert_carteira(mapper, connection, target):
            """Atualiza cache após inserir item na carteira"""
            if not TRIGGERS_ENABLED:
                return
                
            if target.ativo:
                try:
                    _registrar_mudanca_pendente(connection, 'carteira_principal', 'INSERT', target.cod_produto)
                except Exception as e:
                    logger.error(f"Erro no trigger insert CarteiraPrincipal: {e}")
        
        @event.listens_for(CarteiraPrincipal, 'after_update')
        def atualizar_cache_apos_update_carteira(mapper, connection, target):
            """Atualiza cache após alterar item na carteira"""
            if not TRIGGERS_ENABLED:
                return
                
            if target.ativo:
                try:
                    _registrar_mudanca_pendente(connection, 'carteira_principal', 'UPDATE', target.cod_produto)
                except Exception as e:
                    logger.error(f"Erro no trigger update CarteiraPrincipal: {e}")
        
        @event.listens_for(CarteiraPrincipal, 'after_delete')
        def atualizar_cache_apos_delete_carteira(mapper, connection, target):
            """Atualiza cache após deletar item da carteira"""
            if not TRIGGERS_ENABLED:
                return
                
            try:
                _registrar_mudanca_pendente(connection, 'carteira_principal', 'DELETE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger delete CarteiraPrincipal: {e}")
                
    except ImportError:
        logger.warning("CarteiraPrincipal não disponível para triggers")
    
    
    # 3. Triggers para PreSeparacaoItem
    try:
        from app.carteira.models import PreSeparacaoItem
        
        @event.listens_for(PreSeparacaoItem, 'after_insert')
        def atualizar_cache_apos_insert_pre_separacao(mapper, connection, target):
            """Atualiza cache após inserir pré-separação"""
            if not TRIGGERS_ENABLED:
                return
                
            try:
                if hasattr(target, 'cod_produto') and target.cod_produto:
                    _registrar_mudanca_pendente(connection, 'pre_separacao_item', 'INSERT', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger insert PreSeparacaoItem: {e}")
        
        @event.listens_for(PreSeparacaoItem, 'after_update')
        def atualizar_cache_apos_update_pre_separacao(mapper, connection, target):
            """Atualiza cache após alterar pré-separação"""
            if not TRIGGERS_ENABLED:
                return
                
            try:
                if hasattr(target, 'cod_produto') and target.cod_produto:
                    _registrar_mudanca_pendente(connection, 'pre_separacao_item', 'UPDATE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger update PreSeparacaoItem: {e}")
        
        @event.listens_for(PreSeparacaoItem, 'after_delete')
        def atualizar_cache_apos_delete_pre_separacao(mapper, connection, target):
            """Atualiza cache após deletar pré-separação"""
            if not TRIGGERS_ENABLED:
                return
                
            try:
                if hasattr(target, 'cod_produto') and target.cod_produto:
                    _registrar_mudanca_pendente(connection, 'pre_separacao_item', 'DELETE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger delete PreSeparacaoItem: {e}")
                
    except ImportError:
        logger.warning("PreSeparacaoItem não disponível para triggers")
    
    
    # 4. Triggers para Separacao
    try:
        from app.separacao.models import Separacao
        
        @event.listens_for(Separacao, 'after_insert')
        def atualizar_cache_apos_insert_separacao(mapper, connection, target):
            """Atualiza cache após inserir separação"""
            if not TRIGGERS_ENABLED:
                return
                
            try:
                _registrar_mudanca_pendente(connection, 'separacao', 'INSERT', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger insert Separacao: {e}")
        
        @event.listens_for(Separacao, 'after_update')
        def atualizar_cache_apos_update_separacao(mapper, connection, target):
            """Atualiza cache após alterar separação"""
            if not TRIGGERS_ENABLED:
                return
                
            try:
                _registrar_mudanca_pendente(connection, 'separacao', 'UPDATE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger update Separacao: {e}")
        
        @event.listens_for(Separacao, 'after_delete')
        def atualizar_cache_apos_delete_separacao(mapper, connection, target):
            """Atualiza cache após deletar separação"""
            if not TRIGGERS_ENABLED:
                return
                
            try:
                _registrar_mudanca_pendente(connection, 'separacao', 'DELETE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger delete Separacao: {e}")
                
    except ImportError:
        logger.warning("Separacao não disponível para triggers")
    
    
    # 5. Triggers para ProgramacaoProducao
    try:
        from app.producao.models import ProgramacaoProducao
        
        @event.listens_for(ProgramacaoProducao, 'after_insert')
        def atualizar_cache_apos_insert_producao(mapper, connection, target):
            """Atualiza cache após inserir programação de produção"""
            if not TRIGGERS_ENABLED:
                return
                
            try:
                _registrar_mudanca_pendente(connection, 'programacao_producao', 'INSERT', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger insert ProgramacaoProducao: {e}")
        
        @event.listens_for(ProgramacaoProducao, 'after_update')
        def atualizar_cache_apos_update_producao(mapper, connection, target):
            """Atualiza cache após alterar programação de produção"""
            if not TRIGGERS_ENABLED:
                return
                
            try:
                _registrar_mudanca_pendente(connection, 'programacao_producao', 'UPDATE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger update ProgramacaoProducao: {e}")
        
        @event.listens_for(ProgramacaoProducao, 'after_delete')
        def atualizar_cache_apos_delete_producao(mapper, connection, target):
            """Atualiza cache após deletar programação de produção"""
            if not TRIGGERS_ENABLED:
                return
                
            try:
                _registrar_mudanca_pendente(connection, 'programacao_producao', 'DELETE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger delete ProgramacaoProducao: {e}")
                
    except ImportError:
        logger.warning("ProgramacaoProducao não disponível para triggers")
    
    logger.info("✅ Triggers de cache configurados com sucesso (versão corrigida)")


def _registrar_mudanca_pendente(connection, tabela, operacao, cod_produto):
    """
    Registra mudança pendente diretamente via SQL, sem usar a sessão
    Isso evita problemas durante o flush
    """
    try:
        # Usar SQL direto para evitar problemas de sessão
        sql = """
            INSERT INTO cache_update_log (tabela_origem, operacao, cod_produto, processado, criado_em)
            VALUES (:tabela, :operacao, :produto, false, :agora)
        """
        connection.execute(sql, {
            'tabela': tabela,
            'operacao': operacao,
            'produto': str(cod_produto) if cod_produto else None,
            'agora': datetime.now()
        })
    except Exception as e:
        # Log silencioso para não interromper o fluxo
        logger.debug(f"Não foi possível registrar mudança no cache: {e}")


def processar_atualizacoes_pendentes():
    """
    Processa atualizações pendentes do cache
    Deve ser executado periodicamente (ex: a cada minuto)
    """
    try:
        from app.utils.helpers import agora_brasil
        
        # Buscar atualizações pendentes
        pendentes = CacheUpdateLog.query.filter_by(processado=False).limit(100).all()
        
        produtos_para_atualizar = set()
        
        for log in pendentes:
            if log.cod_produto:
                produtos_para_atualizar.add(log.cod_produto)
            
            # Marcar como processado
            log.processado = True
            log.processado_em = agora_brasil()
        
        # Atualizar produtos únicos
        for cod_produto in produtos_para_atualizar:
            try:
                # Recalcular saldo do cache
                cache = SaldoEstoqueCache.query.filter_by(cod_produto=str(cod_produto)).first()
                if cache:
                    # Recalcular saldo total
                    from app.estoque.models import MovimentacaoEstoque
                    movimentacoes = MovimentacaoEstoque.query.filter_by(
                        cod_produto=str(cod_produto),
                        ativo=True
                    ).all()
                    
                    saldo_total = sum(float(m.qtd_movimentacao) for m in movimentacoes)
                    cache.saldo_atual = saldo_total
                    cache.ultima_atualizacao_saldo = agora_brasil()
                    
                    # Atualizar quantidades de carteira
                    SaldoEstoqueCache.atualizar_carteira(cod_produto)
                    
                    # Atualizar projeção
                    ProjecaoEstoqueCache.atualizar_projecao(cod_produto)
                    
            except Exception as e:
                logger.error(f"Erro ao processar atualização para {cod_produto}: {e}")
        
        db.session.commit()
        
        if pendentes:
            logger.info(f"✅ Processadas {len(pendentes)} atualizações de cache")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar atualizações pendentes: {e}")


# Context manager para desabilitar triggers temporariamente
class DisableTriggers:
    """Context manager para desabilitar triggers temporariamente"""
    
    def __enter__(self):
        desabilitar_triggers()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        habilitar_triggers()
        return False