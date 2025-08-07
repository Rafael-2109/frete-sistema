"""
Triggers SQLAlchemy para Sistema de Estoque em Tempo Real
Conecta eventos de todas as tabelas origem ao ServicoEstoqueTempoReal
"""

from sqlalchemy import event
from decimal import Decimal
from datetime import date
from app import db
from app.estoque.models import MovimentacaoEstoque
from app.producao.models import ProgramacaoProducao
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from app.carteira.models import PreSeparacaoItem
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem


# ============================================================================
# TRIGGERS DE ATUALIZAÇÃO DO SALDO REAL (MovimentacaoEstoque → EstoqueTempoReal)
# ============================================================================

@event.listens_for(MovimentacaoEstoque, 'after_insert')
def mov_estoque_insert(mapper, connection, target):
    """Processa nova movimentação de estoque"""
    if target.ativo:
        ServicoEstoqueTempoReal.processar_movimentacao_estoque(target, 'insert')


@event.listens_for(MovimentacaoEstoque, 'after_update')
def mov_estoque_update(mapper, connection, target):
    """Processa atualização de movimentação de estoque"""
    if target.ativo:
        # Obter valor anterior da quantidade
        hist = db.inspect(target).attrs.qtd_movimentacao.history
        qtd_anterior = hist.deleted[0] if hist.deleted else target.qtd_movimentacao
        
        ServicoEstoqueTempoReal.processar_movimentacao_estoque(
            target, 'update', qtd_anterior
        )


@event.listens_for(MovimentacaoEstoque, 'after_delete')
def mov_estoque_delete(mapper, connection, target):
    """Processa exclusão de movimentação de estoque"""
    ServicoEstoqueTempoReal.processar_movimentacao_estoque(target, 'delete')


# ============================================================================
# TRIGGERS DE PRÉ-SEPARAÇÃO (PreSeparacaoItem → MovimentacaoPrevista)
# ============================================================================

@event.listens_for(PreSeparacaoItem, 'after_insert')
def presep_insert(mapper, connection, target):
    """Adiciona saída prevista quando pré-separação é criada"""
    # Só processar se não foi recomposto e tem data de expedição
    if not target.recomposto and target.data_expedicao_editada:
        ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
            cod_produto=target.cod_produto,
            data=target.data_expedicao_editada,
            qtd_saida=Decimal(str(target.qtd_selecionada_usuario))
        )


@event.listens_for(PreSeparacaoItem, 'after_update')
def presep_update(mapper, connection, target):
    """Atualiza saída prevista quando pré-separação é modificada"""
    # Só processar se não foi recomposto
    if not target.recomposto:
        hist = db.inspect(target).attrs
        
        # Verificar mudanças na data de expedição
        if hist.data_expedicao_editada.history.has_changes():
            # Reverter quantidade anterior se havia
            if hist.data_expedicao_editada.history.deleted:
                data_anterior = hist.data_expedicao_editada.history.deleted[0]
                qtd_anterior = (
                    hist.qtd_selecionada_usuario.history.deleted[0] 
                    if hist.qtd_selecionada_usuario.history.deleted 
                    else target.qtd_selecionada_usuario
                )
                
                if data_anterior and qtd_anterior:
                    # Reverter saída anterior
                    ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                        cod_produto=target.cod_produto,
                        data=data_anterior,
                        qtd_saida=-Decimal(str(qtd_anterior))
                    )
            
            # Adicionar nova saída se tem data
            if target.data_expedicao_editada:
                ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                    cod_produto=target.cod_produto,
                    data=target.data_expedicao_editada,
                    qtd_saida=Decimal(str(target.qtd_selecionada_usuario))
                )
        
        # Verificar mudanças na quantidade
        elif hist.qtd_selecionada_usuario.history.has_changes() and target.data_expedicao_editada:
            qtd_anterior = (
                hist.qtd_selecionada_usuario.history.deleted[0] 
                if hist.qtd_selecionada_usuario.history.deleted 
                else 0
            )
            diferenca = Decimal(str(target.qtd_selecionada_usuario)) - Decimal(str(qtd_anterior))
            
            if diferenca != 0:
                ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                    cod_produto=target.cod_produto,
                    data=target.data_expedicao_editada,
                    qtd_saida=diferenca
                )
        
        # Verificar mudança no status recomposto
        if hist.recomposto.history.has_changes() and target.recomposto:
            # Item foi recomposto, reverter saída prevista
            if target.data_expedicao_editada:
                ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                    cod_produto=target.cod_produto,
                    data=target.data_expedicao_editada,
                    qtd_saida=-Decimal(str(target.qtd_selecionada_usuario))
                )


@event.listens_for(PreSeparacaoItem, 'after_delete')
def presep_delete(mapper, connection, target):
    """Remove saída prevista quando pré-separação é excluída"""
    if not target.recomposto and target.data_expedicao_editada:
        ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
            cod_produto=target.cod_produto,
            data=target.data_expedicao_editada,
            qtd_saida=-Decimal(str(target.qtd_selecionada_usuario))
        )


# ============================================================================
# TRIGGERS DE SEPARAÇÃO (Separacao → MovimentacaoPrevista)
# ============================================================================

@event.listens_for(Separacao, 'after_insert')
def sep_insert(mapper, connection, target):
    """Adiciona saída prevista quando separação é criada"""
    if target.expedicao and target.qtd_saldo and target.qtd_saldo > 0:
        ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
            cod_produto=target.cod_produto,
            data=target.expedicao,
            qtd_saida=Decimal(str(target.qtd_saldo))
        )


@event.listens_for(Separacao, 'after_update')
def sep_update(mapper, connection, target):
    """Atualiza saída prevista quando separação é modificada"""
    hist = db.inspect(target).attrs
    
    # Verificar mudanças na data de expedição
    if hist.expedicao.history.has_changes():
        # Reverter quantidade anterior
        if hist.expedicao.history.deleted:
            data_anterior = hist.expedicao.history.deleted[0]
            qtd_anterior = (
                hist.qtd_saldo.history.deleted[0] 
                if hist.qtd_saldo.history.deleted 
                else target.qtd_saldo
            )
            
            if data_anterior and qtd_anterior and qtd_anterior > 0:
                ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                    cod_produto=target.cod_produto,
                    data=data_anterior,
                    qtd_saida=-Decimal(str(qtd_anterior))
                )
        
        # Adicionar nova
        if target.expedicao and target.qtd_saldo and target.qtd_saldo > 0:
            ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                cod_produto=target.cod_produto,
                data=target.expedicao,
                qtd_saida=Decimal(str(target.qtd_saldo))
            )
    
    # Verificar mudanças na quantidade
    elif hist.qtd_saldo.history.has_changes() and target.expedicao:
        qtd_anterior = hist.qtd_saldo.history.deleted[0] if hist.qtd_saldo.history.deleted else 0
        diferenca = Decimal(str(target.qtd_saldo or 0)) - Decimal(str(qtd_anterior or 0))
        
        if diferenca != 0:
            ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                cod_produto=target.cod_produto,
                data=target.expedicao,
                qtd_saida=diferenca
            )


@event.listens_for(Separacao, 'after_delete')
def sep_delete(mapper, connection, target):
    """Remove saída prevista quando separação é excluída"""
    if target.expedicao and target.qtd_saldo and target.qtd_saldo > 0:
        ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
            cod_produto=target.cod_produto,
            data=target.expedicao,
            qtd_saida=-Decimal(str(target.qtd_saldo))
        )


# ============================================================================
# TRIGGERS DE PRODUÇÃO (ProgramacaoProducao → MovimentacaoPrevista)
# ============================================================================

@event.listens_for(ProgramacaoProducao, 'after_insert')
def prod_insert(mapper, connection, target):
    """Adiciona entrada prevista quando programação é criada"""
    if target.data_programacao and target.qtd_programada and target.qtd_programada > 0:
        ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
            cod_produto=target.cod_produto,
            data=target.data_programacao,
            qtd_entrada=Decimal(str(target.qtd_programada))
        )


@event.listens_for(ProgramacaoProducao, 'after_update')
def prod_update(mapper, connection, target):
    """Atualiza entrada prevista quando programação é modificada"""
    hist = db.inspect(target).attrs
    
    # Verificar mudanças na data
    if hist.data_programacao.history.has_changes():
        # Reverter anterior
        if hist.data_programacao.history.deleted:
            data_anterior = hist.data_programacao.history.deleted[0]
            qtd_anterior = (
                hist.qtd_programada.history.deleted[0] 
                if hist.qtd_programada.history.deleted 
                else target.qtd_programada
            )
            
            if data_anterior and qtd_anterior and qtd_anterior > 0:
                ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                    cod_produto=target.cod_produto,
                    data=data_anterior,
                    qtd_entrada=-Decimal(str(qtd_anterior))
                )
        
        # Adicionar nova
        if target.data_programacao and target.qtd_programada and target.qtd_programada > 0:
            ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                cod_produto=target.cod_produto,
                data=target.data_programacao,
                qtd_entrada=Decimal(str(target.qtd_programada))
            )
    
    # Verificar mudanças na quantidade
    elif hist.qtd_programada.history.has_changes() and target.data_programacao:
        qtd_anterior = hist.qtd_programada.history.deleted[0] if hist.qtd_programada.history.deleted else 0
        diferenca = Decimal(str(target.qtd_programada or 0)) - Decimal(str(qtd_anterior or 0))
        
        if diferenca != 0:
            ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                cod_produto=target.cod_produto,
                data=target.data_programacao,
                qtd_entrada=diferenca
            )


@event.listens_for(ProgramacaoProducao, 'after_delete')
def prod_delete(mapper, connection, target):
    """Remove entrada prevista quando programação é excluída"""
    if target.data_programacao and target.qtd_programada and target.qtd_programada > 0:
        ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
            cod_produto=target.cod_produto,
            data=target.data_programacao,
            qtd_entrada=-Decimal(str(target.qtd_programada))
        )


# ============================================================================
# TRIGGER ESPECIAL: EmbarqueItem.erro_validacao (cancela Separacao)
# ============================================================================

@event.listens_for(EmbarqueItem, 'after_update')
def embarque_validacao(mapper, connection, target):
    """
    Quando erro_validacao muda de valor para None, 
    cancela a saída prevista da Separacao correspondente
    """
    hist = db.inspect(target).attrs.erro_validacao.history
    
    # Se erro_validacao mudou para None (antes tinha erro, agora não tem)
    if hist.deleted and hist.deleted[0] is not None and target.erro_validacao is None:
        # Buscar separacao correspondente
        if target.separacao_lote_id:
            separacao = Separacao.query.filter_by(
                separacao_lote_id=target.separacao_lote_id,
                cod_produto=target.cod_produto if hasattr(target, 'cod_produto') else None
            ).first()
            
            if separacao and separacao.expedicao and separacao.qtd_saldo:
                # CANCELAR movimentação prevista desta separação
                ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                    cod_produto=separacao.cod_produto,
                    data=separacao.expedicao,
                    qtd_saida=-Decimal(str(separacao.qtd_saldo))
                )


# ============================================================================
# TRIGGERS DE RECÁLCULO DE PROJEÇÃO
# ============================================================================

# NOTA: Os triggers de recálculo foram removidos porque causavam loops recursivos
# durante o flush do SQLAlchemy. O cálculo de ruptura agora é feito:
# 1. Sob demanda quando get_projecao_completa é chamado
# 2. Pelo job scheduled que roda a cada 60 segundos
# 3. Manualmente quando necessário
#
# Os triggers abaixo foram comentados para evitar o erro:
# "Session is already flushing" / "This transaction is closed"

# @event.listens_for(MovimentacaoPrevista, 'after_insert')
# @event.listens_for(MovimentacaoPrevista, 'after_update')
# @event.listens_for(MovimentacaoPrevista, 'after_delete')
# def mov_prevista_changed(mapper, connection, target):
#     """Recalcula ruptura quando movimentação prevista muda"""
#     # Não pode chamar calcular_ruptura_d7 aqui pois causa flush recursivo
#     pass

# @event.listens_for(EstoqueTempoReal, 'after_update')
# def estoque_changed(mapper, connection, target):
#     """Recalcula ruptura quando saldo atual muda"""
#     # Não pode chamar calcular_ruptura_d7 aqui pois causa flush recursivo
#     pass


def registrar_triggers():
    """
    Função para garantir que todos os triggers estejam registrados.
    Deve ser chamada durante a inicialização da aplicação.
    """
    # Os decoradores @event.listens_for já registram automaticamente
    # Esta função existe apenas para documentação e possível debug
    return {
        'movimentacao_estoque': ['insert', 'update', 'delete'],
        'pre_separacao_item': ['insert', 'update', 'delete'],
        'separacao': ['insert', 'update', 'delete'],
        'programacao_producao': ['insert', 'update', 'delete'],
        'embarque_item': ['update'],
        'movimentacao_prevista': ['insert', 'update', 'delete'],
        'estoque_tempo_real': ['update']
    }