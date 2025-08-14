"""
Triggers SQL Corrigidos - Versão definitiva sem erros de sintaxe
Usa SQL direto de forma segura e eficiente
"""

from sqlalchemy import event, text
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date
import logging
from app import db
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
from app.producao.models import ProgramacaoProducao
from app.carteira.models import PreSeparacaoItem
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem
from app.estoque.triggers_recalculo_otimizado import RecalculoMovimentacaoPrevista

logger = logging.getLogger(__name__)


class TriggersSQLCorrigido:
    """
    Implementação corrigida dos triggers usando SQL direto.
    Evita problemas de flush e erros de sintaxe SQL.
    """
    
    @staticmethod
    def _executar_sql(connection, sql, params=None):
        """Executa SQL direto na conexão, evitando o ORM"""
        try:
            result = connection.execute(text(sql), params or {})
            return result
        except Exception as e:
            logger.error(f"Erro SQL: {e}")
            logger.error(f"SQL: {sql}")
            logger.error(f"Params: {params}")
            # Não re-raise para não quebrar o fluxo
            return None
    
    @staticmethod
    def _obter_codigos_unificados(connection, cod_produto):
        """
        Obtém códigos unificados de forma segura.
        Versão simplificada que evita problemas de sintaxe SQL.
        """
        # Lista para armazenar todos os códigos
        codigos = [str(cod_produto)]
        
        try:
            cod_int = int(cod_produto)
            
            # 1. Buscar códigos que apontam para este (este é destino)
            sql_origem = """
            SELECT DISTINCT codigo_origem::varchar 
            FROM unificacao_codigos 
            WHERE codigo_destino = :cod_int AND ativo = true
            """
            result = connection.execute(text(sql_origem), {'cod_int': cod_int})
            for row in result:
                if row[0] and row[0] not in codigos:
                    codigos.append(row[0])
            
            # 2. Buscar código para onde este aponta (este é origem)
            sql_destino = """
            SELECT DISTINCT codigo_destino::varchar 
            FROM unificacao_codigos 
            WHERE codigo_origem = :cod_int AND ativo = true
            """
            result = connection.execute(text(sql_destino), {'cod_int': cod_int})
            for row in result:
                if row[0] and row[0] not in codigos:
                    codigos.append(row[0])
            
        except (ValueError, TypeError):
            # Se não for numérico, usar apenas o código original
            pass
        except Exception as e:
            logger.debug(f"Erro ao buscar códigos unificados para {cod_produto}: {e}")
        
        return codigos
    
    @staticmethod
    def processar_movimentacao_estoque(mapper, connection, target, operacao='insert', qtd_anterior=None):
        """
        Processa movimentação de estoque usando SQL direto.
        Mais eficiente e evita problemas de flush.
        """
        if not target.ativo and operacao != 'delete':
            return
        
        # Obter códigos unificados
        codigos = TriggersSQLCorrigido._obter_codigos_unificados(connection, target.cod_produto)
        
        # Calcular delta baseado na operação
        if operacao == 'insert':
            delta = float(target.qtd_movimentacao)
        elif operacao == 'update':
            delta = float(target.qtd_movimentacao) - float(qtd_anterior or 0)
        else:  # delete
            delta = -float(target.qtd_movimentacao)
        
        # Atualizar EstoqueTempoReal para cada código relacionado
        for codigo in codigos:
            # UPSERT otimizado
            sql = """
            INSERT INTO estoque_tempo_real (
                cod_produto, nome_produto, saldo_atual, atualizado_em
            ) VALUES (
                :cod_produto, :nome_produto, :delta, NOW()
            )
            ON CONFLICT (cod_produto) DO UPDATE SET
                saldo_atual = estoque_tempo_real.saldo_atual + :delta,
                atualizado_em = NOW()
            """
            
            params = {
                'cod_produto': codigo,
                'nome_produto': target.nome_produto or f'Produto {codigo}',
                'delta': delta
            }
            
            TriggersSQLCorrigido._executar_sql(connection, sql, params)
    
    @staticmethod
    def atualizar_movimentacao_prevista(connection, cod_produto, data_prevista, 
                                       qtd_entrada=0, qtd_saida=0):
        """
        Atualiza MovimentacaoPrevista usando SQL direto.
        """
        # Obter códigos unificados
        codigos = TriggersSQLCorrigido._obter_codigos_unificados(connection, cod_produto)
        
        for codigo in codigos:
            # UPSERT na movimentacao_prevista
            sql = """
            INSERT INTO movimentacao_prevista (
                cod_produto, data_prevista, entrada_prevista, saida_prevista
            ) VALUES (
                :cod_produto, :data_prevista, :qtd_entrada, :qtd_saida
            )
            ON CONFLICT (cod_produto, data_prevista) DO UPDATE SET
                entrada_prevista = movimentacao_prevista.entrada_prevista + :qtd_entrada,
                saida_prevista = movimentacao_prevista.saida_prevista + :qtd_saida
            """
            
            params = {
                'cod_produto': codigo,
                'data_prevista': data_prevista,
                'qtd_entrada': float(qtd_entrada),
                'qtd_saida': float(qtd_saida)
            }
            
            TriggersSQLCorrigido._executar_sql(connection, sql, params)
            
            # Limpar registros zerados
            sql_cleanup = """
            DELETE FROM movimentacao_prevista 
            WHERE cod_produto = :cod_produto 
              AND data_prevista = :data_prevista
              AND entrada_prevista <= 0 
              AND saida_prevista <= 0
            """
            
            TriggersSQLCorrigido._executar_sql(connection, sql_cleanup, 
                                              {'cod_produto': codigo, 'data_prevista': data_prevista})


# ============================================================================
# REGISTRAR TRIGGERS
# ============================================================================

@event.listens_for(MovimentacaoEstoque, 'after_insert')
def mov_estoque_insert(mapper, connection, target):
    """Trigger para INSERT em MovimentacaoEstoque"""
    TriggersSQLCorrigido.processar_movimentacao_estoque(
        mapper, connection, target, 'insert'
    )


@event.listens_for(MovimentacaoEstoque, 'after_update')
def mov_estoque_update(mapper, connection, target):
    """Trigger para UPDATE em MovimentacaoEstoque"""
    # Obter valor anterior se disponível
    try:
        hist = db.inspect(target).attrs.qtd_movimentacao.history
        qtd_anterior = hist.deleted[0] if hist.deleted else target.qtd_movimentacao
    except:
        qtd_anterior = target.qtd_movimentacao
    
    TriggersSQLCorrigido.processar_movimentacao_estoque(
        mapper, connection, target, 'update', qtd_anterior
    )


@event.listens_for(MovimentacaoEstoque, 'after_delete')
def mov_estoque_delete(mapper, connection, target):
    """Trigger para DELETE em MovimentacaoEstoque"""
    TriggersSQLCorrigido.processar_movimentacao_estoque(
        mapper, connection, target, 'delete'
    )


@event.listens_for(PreSeparacaoItem, 'after_insert')
def presep_insert(mapper, connection, target):
    """Trigger para INSERT em PreSeparacaoItem - Usa RECÁLCULO"""
    if target.data_expedicao_editada and target.status in ('CRIADO', 'RECOMPOSTO'):
        # Recalcular ao invés de somar
        RecalculoMovimentacaoPrevista.recalcular_saida_prevista_produto(
            connection,
            cod_produto=target.cod_produto,
            data_prevista=target.data_expedicao_editada
        )


@event.listens_for(PreSeparacaoItem, 'after_update')
def presep_update(mapper, connection, target):
    """Trigger para UPDATE em PreSeparacaoItem - Usa RECÁLCULO"""
    try:
        hist = db.inspect(target).attrs
        
        # Detectar mudanças relevantes
        mudou_data = hist.data_expedicao_editada.history.has_changes()
        mudou_qtd = hist.qtd_selecionada_usuario.history.has_changes()
        mudou_status = hist.status.history.has_changes() if hasattr(hist, 'status') else False
        
        # Se mudou algo relevante, recalcular
        if mudou_data or mudou_qtd or mudou_status:
            # Recalcular data anterior se mudou
            if mudou_data and hist.data_expedicao_editada.history.deleted:
                data_anterior = hist.data_expedicao_editada.history.deleted[0]
                if data_anterior:
                    RecalculoMovimentacaoPrevista.recalcular_saida_prevista_produto(
                        connection,
                        cod_produto=target.cod_produto,
                        data_prevista=data_anterior
                    )
            
            # Recalcular data atual
            if target.data_expedicao_editada and target.status in ('CRIADO', 'RECOMPOSTO'):
                RecalculoMovimentacaoPrevista.recalcular_saida_prevista_produto(
                    connection,
                    cod_produto=target.cod_produto,
                    data_prevista=target.data_expedicao_editada
                )
    except Exception as e:
        logger.debug(f"Erro no trigger presep_update: {e}")


@event.listens_for(PreSeparacaoItem, 'after_delete')
def presep_delete(mapper, connection, target):
    """Trigger para DELETE em PreSeparacaoItem - Usa RECÁLCULO"""
    if target.data_expedicao_editada:
        # Recalcular após deletar
        RecalculoMovimentacaoPrevista.recalcular_saida_prevista_produto(
            connection,
            cod_produto=target.cod_produto,
            data_prevista=target.data_expedicao_editada
        )


@event.listens_for(Separacao, 'after_insert')
def sep_insert(mapper, connection, target):
    """
    Trigger para INSERT em Separacao - Usa RECÁLCULO
    Recalcula sempre, pois o método já considera NF faturada
    """
    if target.expedicao and target.qtd_saldo and target.qtd_saldo > 0:
        # Sempre recalcular - o método já verifica se tem NF faturada
        RecalculoMovimentacaoPrevista.recalcular_saida_prevista_produto(
            connection,
            cod_produto=target.cod_produto,
            data_prevista=target.expedicao
        )


@event.listens_for(Separacao, 'after_update')
def sep_update(mapper, connection, target):
    """
    Trigger para UPDATE em Separacao - Usa RECÁLCULO
    """
    try:
        hist = db.inspect(target).attrs
        
        # Detectar mudanças relevantes
        mudou_data = hist.expedicao.history.has_changes()
        mudou_qtd = hist.qtd_saldo.history.has_changes()
        
        # Se mudou algo relevante, recalcular
        if mudou_data or mudou_qtd:
            # Recalcular data anterior se mudou
            if mudou_data and hist.expedicao.history.deleted:
                data_anterior = hist.expedicao.history.deleted[0]
                if data_anterior:
                    RecalculoMovimentacaoPrevista.recalcular_saida_prevista_produto(
                        connection,
                        cod_produto=target.cod_produto,
                        data_prevista=data_anterior
                    )
            
            # Recalcular data atual
            if target.expedicao and target.qtd_saldo and target.qtd_saldo > 0:
                RecalculoMovimentacaoPrevista.recalcular_saida_prevista_produto(
                    connection,
                    cod_produto=target.cod_produto,
                    data_prevista=target.expedicao
                )
    except Exception as e:
        logger.debug(f"Erro no trigger sep_update: {e}")


@event.listens_for(Separacao, 'after_delete')
def sep_delete(mapper, connection, target):
    """
    Trigger para DELETE em Separacao - Usa RECÁLCULO
    """
    if target.expedicao:
        # Recalcular após deletar
        RecalculoMovimentacaoPrevista.recalcular_saida_prevista_produto(
            connection,
            cod_produto=target.cod_produto,
            data_prevista=target.expedicao
        )


@event.listens_for(ProgramacaoProducao, 'after_insert')
def prod_insert(mapper, connection, target):
    """Trigger para INSERT em ProgramacaoProducao"""
    if target.data_programacao and target.qtd_programada and target.qtd_programada > 0:
        TriggersSQLCorrigido.atualizar_movimentacao_prevista(
            connection,
            cod_produto=target.cod_produto,
            data_prevista=target.data_programacao,
            qtd_entrada=float(target.qtd_programada)
        )


@event.listens_for(ProgramacaoProducao, 'after_update')
def prod_update(mapper, connection, target):
    """Trigger para UPDATE em ProgramacaoProducao"""
    try:
        hist = db.inspect(target).attrs
        
        # Processar mudanças na data
        if hist.data_programacao.history.has_changes():
            if hist.data_programacao.history.deleted:
                data_anterior = hist.data_programacao.history.deleted[0]
                qtd_anterior = (
                    hist.qtd_programada.history.deleted[0]
                    if hist.qtd_programada.history.deleted
                    else target.qtd_programada
                )
                
                if data_anterior and qtd_anterior and qtd_anterior > 0:
                    TriggersSQLCorrigido.atualizar_movimentacao_prevista(
                        connection,
                        cod_produto=target.cod_produto,
                        data_prevista=data_anterior,
                        qtd_entrada=-float(qtd_anterior)
                    )
            
            if target.data_programacao and target.qtd_programada and target.qtd_programada > 0:
                TriggersSQLCorrigido.atualizar_movimentacao_prevista(
                    connection,
                    cod_produto=target.cod_produto,
                    data_prevista=target.data_programacao,
                    qtd_entrada=float(target.qtd_programada)
                )
        
        # Processar mudanças na quantidade
        elif hist.qtd_programada.history.has_changes() and target.data_programacao:
            qtd_anterior = hist.qtd_programada.history.deleted[0] if hist.qtd_programada.history.deleted else 0
            diferenca = float(target.qtd_programada or 0) - float(qtd_anterior or 0)
            
            if diferenca != 0:
                TriggersSQLCorrigido.atualizar_movimentacao_prevista(
                    connection,
                    cod_produto=target.cod_produto,
                    data_prevista=target.data_programacao,
                    qtd_entrada=diferenca
                )
    except Exception as e:
        logger.debug(f"Erro no trigger prod_update: {e}")


@event.listens_for(ProgramacaoProducao, 'after_delete')
def prod_delete(mapper, connection, target):
    """Trigger para DELETE em ProgramacaoProducao"""
    if target.data_programacao and target.qtd_programada and target.qtd_programada > 0:
        TriggersSQLCorrigido.atualizar_movimentacao_prevista(
            connection,
            cod_produto=target.cod_produto,
            data_prevista=target.data_programacao,
            qtd_entrada=-float(target.qtd_programada)
        )


@event.listens_for(EmbarqueItem, 'after_update')
def embarque_validacao(mapper, connection, target):
    """
    Trigger para EmbarqueItem.
    Quando erro_validacao muda para None, cancela a Separacao correspondente.
    """
    try:
        hist = db.inspect(target).attrs.erro_validacao.history
        
        # Se erro_validacao mudou para None (validação OK)
        if hist.deleted and hist.deleted[0] is not None and target.erro_validacao is None:
            if target.separacao_lote_id:
                # Buscar e cancelar separação via SQL
                sql = """
                UPDATE movimentacao_prevista mp
                SET saida_prevista = GREATEST(0, mp.saida_prevista - s.qtd_saldo)
                FROM separacao s
                WHERE s.separacao_lote_id = :lote_id
                  AND s.cod_produto = mp.cod_produto
                  AND s.expedicao = mp.data_prevista
                  AND s.qtd_saldo > 0
                """
                
                TriggersSQLCorrigido._executar_sql(
                    connection, 
                    sql, 
                    {'lote_id': target.separacao_lote_id}
                )
    except Exception as e:
        logger.debug(f"Erro no trigger embarque_validacao: {e}")


def ativar_triggers_corrigidos():
    """
    Ativa os triggers corrigidos.
    Deve ser chamado no __init__.py da aplicação.
    """
    logger.info("✅ Triggers SQL corrigidos ativados com sucesso")
    return True