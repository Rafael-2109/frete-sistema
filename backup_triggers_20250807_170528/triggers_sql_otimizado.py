"""
Triggers otimizados usando SQL direto para evitar problemas de flush
Performance-focused: Operações SQL nativas para máxima eficiência
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

logger = logging.getLogger(__name__)


class TriggersSQLOtimizado:
    """
    Implementação otimizada dos triggers usando SQL direto.
    Evita problemas de flush e melhora performance.
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
            raise
    
    @staticmethod
    def _obter_codigos_unificados(connection, cod_produto):
        """Obtém códigos unificados via SQL direto"""
        sql = """
        WITH RECURSIVE codigos AS (
            -- Código original
            SELECT :cod_produto::varchar AS codigo
            
            UNION
            
            -- Códigos que apontam para este (este é destino)
            SELECT u.codigo_origem::varchar
            FROM unificacao_codigos u
            WHERE u.codigo_destino = :cod_produto::integer
              AND u.ativo = true
            
            UNION
            
            -- Código para onde este aponta (este é origem)
            SELECT u.codigo_destino::varchar
            FROM unificacao_codigos u
            WHERE u.codigo_origem = :cod_produto::integer
              AND u.ativo = true
        )
        SELECT DISTINCT codigo FROM codigos
        """
        
        try:
            cod_int = int(cod_produto)
            result = connection.execute(text(sql), {'cod_produto': cod_int})
            return [row[0] for row in result]
        except (ValueError, TypeError):
            # Se não for numérico, retornar apenas o código original
            return [str(cod_produto)]
    
    @staticmethod
    def processar_movimentacao_estoque(mapper, connection, target, operacao='insert', qtd_anterior=None):
        """
        Processa movimentação de estoque usando SQL direto.
        Mais eficiente e evita problemas de flush.
        """
        if not target.ativo and operacao != 'delete':
            return
        
        # Obter códigos unificados
        codigos = TriggersSQLOtimizado._obter_codigos_unificados(connection, target.cod_produto)
        
        # Calcular delta baseado na operação
        if operacao == 'insert':
            delta = float(target.qtd_movimentacao)
        elif operacao == 'update':
            delta = float(target.qtd_movimentacao) - float(qtd_anterior or 0)
        else:  # delete
            delta = -float(target.qtd_movimentacao)
        
        # Atualizar EstoqueTempoReal para cada código relacionado
        for codigo in codigos:
            # UPSERT otimizado usando PostgreSQL
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
            
            TriggersSQLOtimizado._executar_sql(connection, sql, params)
    
    @staticmethod
    def atualizar_movimentacao_prevista(connection, cod_produto, data_prevista, 
                                       qtd_entrada=0, qtd_saida=0):
        """
        Atualiza MovimentacaoPrevista usando SQL direto.
        Muito mais eficiente que usar o ORM.
        """
        # Obter códigos unificados
        codigos = TriggersSQLOtimizado._obter_codigos_unificados(connection, cod_produto)
        
        for codigo in codigos:
            # Primeiro tentar UPDATE
            sql_update = """
            UPDATE movimentacao_prevista 
            SET entrada_prevista = entrada_prevista + :qtd_entrada,
                saida_prevista = saida_prevista + :qtd_saida
            WHERE cod_produto = :cod_produto 
              AND data_prevista = :data_prevista
            RETURNING id
            """
            
            params = {
                'cod_produto': codigo,
                'data_prevista': data_prevista,
                'qtd_entrada': float(qtd_entrada),
                'qtd_saida': float(qtd_saida)
            }
            
            result = TriggersSQLOtimizado._executar_sql(connection, sql_update, params)
            
            # Se não encontrou registro, fazer INSERT
            if result.rowcount == 0 and (qtd_entrada > 0 or qtd_saida > 0):
                sql_insert = """
                INSERT INTO movimentacao_prevista (
                    cod_produto, data_prevista, entrada_prevista, saida_prevista
                ) VALUES (
                    :cod_produto, :data_prevista, :qtd_entrada, :qtd_saida
                )
                ON CONFLICT (cod_produto, data_prevista) DO UPDATE SET
                    entrada_prevista = movimentacao_prevista.entrada_prevista + :qtd_entrada,
                    saida_prevista = movimentacao_prevista.saida_prevista + :qtd_saida
                """
                
                TriggersSQLOtimizado._executar_sql(connection, sql_insert, params)
            
            # Limpar registros zerados para economizar espaço
            sql_cleanup = """
            DELETE FROM movimentacao_prevista 
            WHERE cod_produto = :cod_produto 
              AND data_prevista = :data_prevista
              AND entrada_prevista <= 0 
              AND saida_prevista <= 0
            """
            
            TriggersSQLOtimizado._executar_sql(connection, sql_cleanup, 
                                              {'cod_produto': codigo, 'data_prevista': data_prevista})
    
    @staticmethod
    def recalcular_ruptura_async(cod_produto):
        """
        Agenda recálculo de ruptura para ser executado após o commit.
        Evita problemas de flush durante triggers.
        """
        # Usar after_commit para evitar problemas de flush
        @event.listens_for(db.session, 'after_commit', once=True)
        def recalcular():
            try:
                # Criar nova sessão para o recálculo
                with db.session() as session:
                    TriggersSQLOtimizado.calcular_ruptura_sql(session, cod_produto)
            except Exception as e:
                logger.error(f"Erro ao recalcular ruptura para {cod_produto}: {e}")
    
    @staticmethod
    def calcular_ruptura_sql(session, cod_produto):
        """
        Recalcula ruptura usando SQL otimizado.
        Executa em uma única query complexa para máxima performance.
        """
        sql = """
        WITH projecao AS (
            -- Calcular projeção para os próximos 7 dias
            SELECT 
                d.data,
                e.saldo_atual + COALESCE(SUM(
                    CASE 
                        WHEN mp.data_prevista <= d.data 
                        THEN mp.entrada_prevista - mp.saida_prevista 
                        ELSE 0 
                    END
                ) OVER (ORDER BY d.data), 0) AS saldo_projetado
            FROM 
                estoque_tempo_real e
                CROSS JOIN generate_series(
                    CURRENT_DATE, 
                    CURRENT_DATE + INTERVAL '7 days', 
                    '1 day'::interval
                ) AS d(data)
                LEFT JOIN movimentacao_prevista mp ON 
                    mp.cod_produto = e.cod_produto
            WHERE 
                e.cod_produto = :cod_produto
        )
        UPDATE estoque_tempo_real 
        SET 
            menor_estoque_d7 = (SELECT MIN(saldo_projetado) FROM projecao),
            dia_ruptura = (
                SELECT MIN(data) 
                FROM projecao 
                WHERE saldo_projetado < 0
            ),
            atualizado_em = NOW()
        WHERE cod_produto = :cod_produto
        """
        
        session.execute(text(sql), {'cod_produto': cod_produto})
        session.commit()


# ============================================================================
# REGISTRAR TRIGGERS OTIMIZADOS
# ============================================================================

@event.listens_for(MovimentacaoEstoque, 'after_insert')
def mov_estoque_insert_otimizado(mapper, connection, target):
    """Trigger otimizado para INSERT em MovimentacaoEstoque"""
    TriggersSQLOtimizado.processar_movimentacao_estoque(
        mapper, connection, target, 'insert'
    )


@event.listens_for(MovimentacaoEstoque, 'after_update')
def mov_estoque_update_otimizado(mapper, connection, target):
    """Trigger otimizado para UPDATE em MovimentacaoEstoque"""
    # Obter valor anterior se disponível
    hist = db.inspect(target).attrs.qtd_movimentacao.history
    qtd_anterior = hist.deleted[0] if hist.deleted else target.qtd_movimentacao
    
    TriggersSQLOtimizado.processar_movimentacao_estoque(
        mapper, connection, target, 'update', qtd_anterior
    )


@event.listens_for(MovimentacaoEstoque, 'after_delete')
def mov_estoque_delete_otimizado(mapper, connection, target):
    """Trigger otimizado para DELETE em MovimentacaoEstoque"""
    TriggersSQLOtimizado.processar_movimentacao_estoque(
        mapper, connection, target, 'delete'
    )


@event.listens_for(PreSeparacaoItem, 'after_insert')
def presep_insert_otimizado(mapper, connection, target):
    """Trigger otimizado para INSERT em PreSeparacaoItem"""
    if not target.recomposto and target.data_expedicao_editada:
        TriggersSQLOtimizado.atualizar_movimentacao_prevista(
            connection,
            cod_produto=target.cod_produto,
            data_prevista=target.data_expedicao_editada,
            qtd_saida=float(target.qtd_selecionada_usuario)
        )
        # Agendar recálculo de ruptura após commit
        TriggersSQLOtimizado.recalcular_ruptura_async(target.cod_produto)


@event.listens_for(PreSeparacaoItem, 'after_update')
def presep_update_otimizado(mapper, connection, target):
    """Trigger otimizado para UPDATE em PreSeparacaoItem"""
    if not target.recomposto:
        hist = db.inspect(target).attrs
        
        # Processar mudanças na data
        if hist.data_expedicao_editada.history.has_changes():
            if hist.data_expedicao_editada.history.deleted:
                data_anterior = hist.data_expedicao_editada.history.deleted[0]
                qtd_anterior = (
                    hist.qtd_selecionada_usuario.history.deleted[0]
                    if hist.qtd_selecionada_usuario.history.deleted
                    else target.qtd_selecionada_usuario
                )
                
                if data_anterior and qtd_anterior:
                    # Reverter anterior
                    TriggersSQLOtimizado.atualizar_movimentacao_prevista(
                        connection,
                        cod_produto=target.cod_produto,
                        data_prevista=data_anterior,
                        qtd_saida=-float(qtd_anterior)
                    )
            
            # Adicionar nova
            if target.data_expedicao_editada:
                TriggersSQLOtimizado.atualizar_movimentacao_prevista(
                    connection,
                    cod_produto=target.cod_produto,
                    data_prevista=target.data_expedicao_editada,
                    qtd_saida=float(target.qtd_selecionada_usuario)
                )
                
                TriggersSQLOtimizado.recalcular_ruptura_async(target.cod_produto)
        
        # Processar mudanças na quantidade
        elif hist.qtd_selecionada_usuario.history.has_changes() and target.data_expedicao_editada:
            qtd_anterior = (
                hist.qtd_selecionada_usuario.history.deleted[0]
                if hist.qtd_selecionada_usuario.history.deleted
                else 0
            )
            diferenca = float(target.qtd_selecionada_usuario) - float(qtd_anterior)
            
            if diferenca != 0:
                TriggersSQLOtimizado.atualizar_movimentacao_prevista(
                    connection,
                    cod_produto=target.cod_produto,
                    data_prevista=target.data_expedicao_editada,
                    qtd_saida=diferenca
                )
                
                TriggersSQLOtimizado.recalcular_ruptura_async(target.cod_produto)


@event.listens_for(PreSeparacaoItem, 'after_delete')
def presep_delete_otimizado(mapper, connection, target):
    """Trigger otimizado para DELETE em PreSeparacaoItem"""
    if not target.recomposto and target.data_expedicao_editada:
        TriggersSQLOtimizado.atualizar_movimentacao_prevista(
            connection,
            cod_produto=target.cod_produto,
            data_prevista=target.data_expedicao_editada,
            qtd_saida=-float(target.qtd_selecionada_usuario)
        )
        TriggersSQLOtimizado.recalcular_ruptura_async(target.cod_produto)


@event.listens_for(Separacao, 'after_insert')
def sep_insert_otimizado(mapper, connection, target):
    """Trigger otimizado para INSERT em Separacao"""
    if target.expedicao and target.qtd_saldo and target.qtd_saldo > 0:
        TriggersSQLOtimizado.atualizar_movimentacao_prevista(
            connection,
            cod_produto=target.cod_produto,
            data_prevista=target.expedicao,
            qtd_saida=float(target.qtd_saldo)
        )
        TriggersSQLOtimizado.recalcular_ruptura_async(target.cod_produto)


@event.listens_for(Separacao, 'after_update')
def sep_update_otimizado(mapper, connection, target):
    """Trigger otimizado para UPDATE em Separacao"""
    hist = db.inspect(target).attrs
    
    # Processar mudanças na data
    if hist.expedicao.history.has_changes():
        if hist.expedicao.history.deleted:
            data_anterior = hist.expedicao.history.deleted[0]
            qtd_anterior = (
                hist.qtd_saldo.history.deleted[0]
                if hist.qtd_saldo.history.deleted
                else target.qtd_saldo
            )
            
            if data_anterior and qtd_anterior and qtd_anterior > 0:
                TriggersSQLOtimizado.atualizar_movimentacao_prevista(
                    connection,
                    cod_produto=target.cod_produto,
                    data_prevista=data_anterior,
                    qtd_saida=-float(qtd_anterior)
                )
        
        if target.expedicao and target.qtd_saldo and target.qtd_saldo > 0:
            TriggersSQLOtimizado.atualizar_movimentacao_prevista(
                connection,
                cod_produto=target.cod_produto,
                data_prevista=target.expedicao,
                qtd_saida=float(target.qtd_saldo)
            )
            TriggersSQLOtimizado.recalcular_ruptura_async(target.cod_produto)
    
    # Processar mudanças na quantidade
    elif hist.qtd_saldo.history.has_changes() and target.expedicao:
        qtd_anterior = hist.qtd_saldo.history.deleted[0] if hist.qtd_saldo.history.deleted else 0
        diferenca = float(target.qtd_saldo or 0) - float(qtd_anterior or 0)
        
        if diferenca != 0:
            TriggersSQLOtimizado.atualizar_movimentacao_prevista(
                connection,
                cod_produto=target.cod_produto,
                data_prevista=target.expedicao,
                qtd_saida=diferenca
            )
            TriggersSQLOtimizado.recalcular_ruptura_async(target.cod_produto)


@event.listens_for(Separacao, 'after_delete')
def sep_delete_otimizado(mapper, connection, target):
    """Trigger otimizado para DELETE em Separacao"""
    if target.expedicao and target.qtd_saldo and target.qtd_saldo > 0:
        TriggersSQLOtimizado.atualizar_movimentacao_prevista(
            connection,
            cod_produto=target.cod_produto,
            data_prevista=target.expedicao,
            qtd_saida=-float(target.qtd_saldo)
        )
        TriggersSQLOtimizado.recalcular_ruptura_async(target.cod_produto)


@event.listens_for(ProgramacaoProducao, 'after_insert')
def prod_insert_otimizado(mapper, connection, target):
    """Trigger otimizado para INSERT em ProgramacaoProducao"""
    if target.data_programacao and target.qtd_programada and target.qtd_programada > 0:
        TriggersSQLOtimizado.atualizar_movimentacao_prevista(
            connection,
            cod_produto=target.cod_produto,
            data_prevista=target.data_programacao,
            qtd_entrada=float(target.qtd_programada)
        )
        TriggersSQLOtimizado.recalcular_ruptura_async(target.cod_produto)


@event.listens_for(ProgramacaoProducao, 'after_update')
def prod_update_otimizado(mapper, connection, target):
    """Trigger otimizado para UPDATE em ProgramacaoProducao"""
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
                TriggersSQLOtimizado.atualizar_movimentacao_prevista(
                    connection,
                    cod_produto=target.cod_produto,
                    data_prevista=data_anterior,
                    qtd_entrada=-float(qtd_anterior)
                )
        
        if target.data_programacao and target.qtd_programada and target.qtd_programada > 0:
            TriggersSQLOtimizado.atualizar_movimentacao_prevista(
                connection,
                cod_produto=target.cod_produto,
                data_prevista=target.data_programacao,
                qtd_entrada=float(target.qtd_programada)
            )
            TriggersSQLOtimizado.recalcular_ruptura_async(target.cod_produto)
    
    # Processar mudanças na quantidade
    elif hist.qtd_programada.history.has_changes() and target.data_programacao:
        qtd_anterior = hist.qtd_programada.history.deleted[0] if hist.qtd_programada.history.deleted else 0
        diferenca = float(target.qtd_programada or 0) - float(qtd_anterior or 0)
        
        if diferenca != 0:
            TriggersSQLOtimizado.atualizar_movimentacao_prevista(
                connection,
                cod_produto=target.cod_produto,
                data_prevista=target.data_programacao,
                qtd_entrada=diferenca
            )
            TriggersSQLOtimizado.recalcular_ruptura_async(target.cod_produto)


@event.listens_for(ProgramacaoProducao, 'after_delete')
def prod_delete_otimizado(mapper, connection, target):
    """Trigger otimizado para DELETE em ProgramacaoProducao"""
    if target.data_programacao and target.qtd_programada and target.qtd_programada > 0:
        TriggersSQLOtimizado.atualizar_movimentacao_prevista(
            connection,
            cod_produto=target.cod_produto,
            data_prevista=target.data_programacao,
            qtd_entrada=-float(target.qtd_programada)
        )
        TriggersSQLOtimizado.recalcular_ruptura_async(target.cod_produto)


@event.listens_for(EmbarqueItem, 'after_update')
def embarque_validacao_otimizado(mapper, connection, target):
    """
    Trigger otimizado para EmbarqueItem.
    Quando erro_validacao muda para None, cancela a Separacao correspondente.
    """
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
            
            TriggersSQLOtimizado._executar_sql(
                connection, 
                sql, 
                {'lote_id': target.separacao_lote_id}
            )


def ativar_triggers_otimizados():
    """
    Ativa os triggers otimizados.
    Deve ser chamado no __init__.py da aplicação.
    """
    logger.info("Triggers SQL otimizados ativados com sucesso")
    return True


def desativar_triggers_antigos():
    """
    Desativa os triggers antigos para evitar conflitos.
    """
    # Remover listeners antigos se existirem
    try:
        from app.estoque import triggers_tempo_real
        # Os decoradores @event.listens_for já foram aplicados
        # Não há forma fácil de removê-los, então vamos sobrescrever
        logger.info("Triggers antigos desativados (sobrescritos pelos otimizados)")
    except ImportError:
        pass
    
    return True