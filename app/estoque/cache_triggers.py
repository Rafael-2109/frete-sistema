"""
Triggers automáticos para manter o cache de estoque atualizado
"""
from sqlalchemy import event
from app import db
from app.estoque.models import MovimentacaoEstoque
from app.estoque.models_cache import SaldoEstoqueCache, ProjecaoEstoqueCache, CacheUpdateLog
import logging

logger = logging.getLogger(__name__)


def configurar_triggers_cache():
    """
    Configura todos os triggers para atualização automática do cache
    Deve ser chamado na inicialização da aplicação
    """
    
    # 1. Trigger para MovimentacaoEstoque
    @event.listens_for(MovimentacaoEstoque, 'after_insert')
    def atualizar_cache_apos_insert_movimentacao(mapper, connection, target):
        """Atualiza cache após inserir movimentação"""
        if target.ativo:
            try:
                # Atualizar saldo incremental imediatamente
                SaldoEstoqueCache.atualizar_saldo_incremental(
                    target.cod_produto, 
                    target.nome_produto, 
                    float(target.qtd_movimentacao)
                )
                # Marcar para recalcular projeção
                CacheUpdateLog.registrar_mudanca('movimentacao_estoque', 'INSERT', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger insert MovimentacaoEstoque: {e}")
    
    @event.listens_for(MovimentacaoEstoque, 'after_update')
    def atualizar_cache_apos_update_movimentacao(mapper, connection, target):
        """Atualiza cache após alterar movimentação"""
        if target.ativo:
            try:
                # Marcar para recálculo completo do produto
                CacheUpdateLog.registrar_mudanca('movimentacao_estoque', 'UPDATE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger update MovimentacaoEstoque: {e}")
    
    @event.listens_for(MovimentacaoEstoque, 'after_delete')
    def atualizar_cache_apos_delete_movimentacao(mapper, connection, target):
        """Atualiza cache após deletar movimentação"""
        try:
            # Marcar para recálculo completo
            CacheUpdateLog.registrar_mudanca('movimentacao_estoque', 'DELETE', target.cod_produto)
        except Exception as e:
            logger.error(f"Erro no trigger delete MovimentacaoEstoque: {e}")
    
    
    # 2. Triggers para CarteiraPrincipal
    try:
        from app.carteira.models import CarteiraPrincipal
        
        @event.listens_for(CarteiraPrincipal, 'after_insert')
        def atualizar_cache_apos_insert_carteira(mapper, connection, target):
            """Atualiza cache após inserir item na carteira"""
            if target.ativo:
                try:
                    SaldoEstoqueCache.atualizar_carteira(target.cod_produto)
                    CacheUpdateLog.registrar_mudanca('carteira_principal', 'INSERT', target.cod_produto)
                except Exception as e:
                    logger.error(f"Erro no trigger insert CarteiraPrincipal: {e}")
        
        @event.listens_for(CarteiraPrincipal, 'after_update')
        def atualizar_cache_apos_update_carteira(mapper, connection, target):
            """Atualiza cache após alterar item na carteira"""
            if target.ativo:
                try:
                    SaldoEstoqueCache.atualizar_carteira(target.cod_produto)
                    CacheUpdateLog.registrar_mudanca('carteira_principal', 'UPDATE', target.cod_produto)
                except Exception as e:
                    logger.error(f"Erro no trigger update CarteiraPrincipal: {e}")
        
        @event.listens_for(CarteiraPrincipal, 'after_delete')
        def atualizar_cache_apos_delete_carteira(mapper, connection, target):
            """Atualiza cache após deletar item da carteira"""
            try:
                SaldoEstoqueCache.atualizar_carteira(target.cod_produto)
                CacheUpdateLog.registrar_mudanca('carteira_principal', 'DELETE', target.cod_produto)
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
            try:
                SaldoEstoqueCache.atualizar_carteira(target.cod_produto)
                ProjecaoEstoqueCache.atualizar_projecao(target.cod_produto)
                CacheUpdateLog.registrar_mudanca('pre_separacao_item', 'INSERT', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger insert PreSeparacaoItem: {e}")
        
        @event.listens_for(PreSeparacaoItem, 'after_update')
        def atualizar_cache_apos_update_pre_separacao(mapper, connection, target):
            """Atualiza cache após alterar pré-separação"""
            try:
                SaldoEstoqueCache.atualizar_carteira(target.cod_produto)
                ProjecaoEstoqueCache.atualizar_projecao(target.cod_produto)
                CacheUpdateLog.registrar_mudanca('pre_separacao_item', 'UPDATE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger update PreSeparacaoItem: {e}")
        
        @event.listens_for(PreSeparacaoItem, 'after_delete')
        def atualizar_cache_apos_delete_pre_separacao(mapper, connection, target):
            """Atualiza cache após deletar pré-separação"""
            try:
                SaldoEstoqueCache.atualizar_carteira(target.cod_produto)
                ProjecaoEstoqueCache.atualizar_projecao(target.cod_produto)
                CacheUpdateLog.registrar_mudanca('pre_separacao_item', 'DELETE', target.cod_produto)
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
            try:
                SaldoEstoqueCache.atualizar_carteira(target.cod_produto)
                ProjecaoEstoqueCache.atualizar_projecao(target.cod_produto)
                CacheUpdateLog.registrar_mudanca('separacao', 'INSERT', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger insert Separacao: {e}")
        
        @event.listens_for(Separacao, 'after_update')
        def atualizar_cache_apos_update_separacao(mapper, connection, target):
            """Atualiza cache após alterar separação"""
            try:
                SaldoEstoqueCache.atualizar_carteira(target.cod_produto)
                ProjecaoEstoqueCache.atualizar_projecao(target.cod_produto)
                CacheUpdateLog.registrar_mudanca('separacao', 'UPDATE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger update Separacao: {e}")
        
        @event.listens_for(Separacao, 'after_delete')
        def atualizar_cache_apos_delete_separacao(mapper, connection, target):
            """Atualiza cache após deletar separação"""
            try:
                SaldoEstoqueCache.atualizar_carteira(target.cod_produto)
                ProjecaoEstoqueCache.atualizar_projecao(target.cod_produto)
                CacheUpdateLog.registrar_mudanca('separacao', 'DELETE', target.cod_produto)
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
            try:
                ProjecaoEstoqueCache.atualizar_projecao(target.cod_produto)
                CacheUpdateLog.registrar_mudanca('programacao_producao', 'INSERT', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger insert ProgramacaoProducao: {e}")
        
        @event.listens_for(ProgramacaoProducao, 'after_update')
        def atualizar_cache_apos_update_producao(mapper, connection, target):
            """Atualiza cache após alterar programação de produção"""
            try:
                ProjecaoEstoqueCache.atualizar_projecao(target.cod_produto)
                CacheUpdateLog.registrar_mudanca('programacao_producao', 'UPDATE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger update ProgramacaoProducao: {e}")
        
        @event.listens_for(ProgramacaoProducao, 'after_delete')
        def atualizar_cache_apos_delete_producao(mapper, connection, target):
            """Atualiza cache após deletar programação de produção"""
            try:
                ProjecaoEstoqueCache.atualizar_projecao(target.cod_produto)
                CacheUpdateLog.registrar_mudanca('programacao_producao', 'DELETE', target.cod_produto)
            except Exception as e:
                logger.error(f"Erro no trigger delete ProgramacaoProducao: {e}")
                
    except ImportError:
        logger.warning("ProgramacaoProducao não disponível para triggers")
    
    logger.info("✅ Triggers de cache configurados com sucesso")


def processar_atualizacoes_pendentes():
    """
    Processa atualizações pendentes do cache
    Deve ser executado periodicamente (ex: a cada minuto)
    """
    try:
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