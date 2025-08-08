"""
Triggers usando after_commit para evitar warnings de flush
Esta é a solução definitiva que funciona com triggers sem causar SAWarnings
"""

from sqlalchemy import event
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date
from app import db
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
from app.producao.models import ProgramacaoProducao
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.carteira.models import PreSeparacaoItem
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem
from app.utils.timezone import agora_brasil
import logging

logger = logging.getLogger(__name__)


class EstoqueAfterCommitProcessor:
    """
    Processa atualizações de estoque APÓS o commit
    Evita completamente warnings de Session durante flush
    """
    
    def __init__(self):
        self.pending_updates = []
        self.pending_previstas = []
    
    def add_estoque_update(self, cod_produto, delta, nome_produto=None):
        """Adiciona atualização de estoque para processar após commit"""
        self.pending_updates.append({
            'cod_produto': cod_produto,
            'delta': delta,
            'nome_produto': nome_produto
        })
    
    def add_movimentacao_prevista(self, data, cod_produto, tipo, quantidade, origem, origem_id):
        """Adiciona movimentação prevista para processar após commit"""
        self.pending_previstas.append({
            'data': data,
            'cod_produto': cod_produto,
            'tipo': tipo,
            'quantidade': quantidade,
            'origem': origem,
            'origem_id': origem_id
        })
    
    def process_all(self):
        """Processa todas as atualizações pendentes"""
        if not self.pending_updates and not self.pending_previstas:
            return
        
        try:
            # Processar atualizações de estoque
            for update in self.pending_updates:
                self._process_estoque_update(update)
            
            # Processar movimentações previstas
            for prevista in self.pending_previstas:
                self._process_movimentacao_prevista(prevista)
            
            # Commit final
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Erro ao processar após commit: {e}")
            db.session.rollback()
        finally:
            # Limpar listas
            self.pending_updates.clear()
            self.pending_previstas.clear()
    
    def _process_estoque_update(self, update):
        """Processa uma atualização de estoque"""
        try:
            # Obter códigos unificados
            codigos = UnificacaoCodigos.get_todos_codigos_relacionados(update['cod_produto'])
            
            for codigo in codigos:
                estoque = EstoqueTempoReal.query.filter_by(cod_produto=codigo).first()
                
                if not estoque:
                    estoque = EstoqueTempoReal(
                        cod_produto=codigo,
                        nome_produto=update.get('nome_produto') or f"Produto {codigo}",
                        saldo_atual=Decimal('0')
                    )
                    db.session.add(estoque)
                
                # Atualizar saldo
                estoque.saldo_atual = Decimal(str(estoque.saldo_atual)) + Decimal(str(update['delta']))
                estoque.atualizado_em = agora_brasil()
                
                logger.debug(f"✅ Estoque atualizado: {codigo} ({update['delta']:+.2f})")
                
        except Exception as e:
            logger.error(f"Erro ao atualizar estoque {update['cod_produto']}: {e}")
    
    def _process_movimentacao_prevista(self, prevista):
        """Processa uma movimentação prevista"""
        try:
            # Verificar se já existe
            existente = MovimentacaoPrevista.query.filter_by(
                data_prevista=prevista['data'],
                cod_produto=prevista['cod_produto'],
                origem=prevista['origem'],
                origem_id=prevista['origem_id']
            ).first()
            
            if existente:
                # Atualizar existente
                existente.tipo_movimentacao = prevista['tipo']
                existente.quantidade = prevista['quantidade']
                existente.atualizado_em = agora_brasil()
            else:
                # Criar nova
                nova = MovimentacaoPrevista(
                    data_prevista=prevista['data'],
                    cod_produto=prevista['cod_produto'],
                    tipo_movimentacao=prevista['tipo'],
                    quantidade=prevista['quantidade'],
                    origem=prevista['origem'],
                    origem_id=prevista['origem_id']
                )
                db.session.add(nova)
            
            logger.debug(f"✅ Movimentação prevista: {prevista['cod_produto']} em {prevista['data']}")
            
        except Exception as e:
            logger.error(f"Erro ao processar movimentação prevista: {e}")


# Instância global do processador
processor = EstoqueAfterCommitProcessor()


# ============================================================================
# EVENTOS DE MOVIMENTAÇÃO DE ESTOQUE
# ============================================================================

@event.listens_for(Session, 'before_commit')
def capture_estoque_changes(session):
    """Captura mudanças ANTES do commit para processar DEPOIS"""
    
    # Processar MovimentacaoEstoque
    for obj in session.new:
        if isinstance(obj, MovimentacaoEstoque) and obj.ativo:
            # O sinal já está correto na qtd_movimentacao
            # Positivo = entrada, Negativo = saída
            delta = Decimal(str(obj.qtd_movimentacao))
            
            processor.add_estoque_update(
                obj.cod_produto,
                delta,
                obj.nome_produto
            )
    
    for obj in session.dirty:
        if isinstance(obj, MovimentacaoEstoque) and obj.ativo:
            # Obter valor anterior
            hist = db.inspect(obj).attrs.qtd_movimentacao.history
            if hist.has_changes():
                qtd_anterior = hist.deleted[0] if hist.deleted else obj.qtd_movimentacao
                
                # Calcular delta da mudança (já com sinal correto)
                delta_novo = Decimal(str(obj.qtd_movimentacao))
                delta_anterior = Decimal(str(qtd_anterior))
                delta_total = delta_novo - delta_anterior
                
                processor.add_estoque_update(
                    obj.cod_produto,
                    delta_total,
                    obj.nome_produto
                )
    
    for obj in session.deleted:
        if isinstance(obj, MovimentacaoEstoque):
            # Reverter movimentação (inverter o sinal)
            delta = -Decimal(str(obj.qtd_movimentacao))
            
            processor.add_estoque_update(
                obj.cod_produto,
                delta,
                obj.nome_produto
            )
    
    # Processar PreSeparacaoItem
    for obj in session.new:
        if isinstance(obj, PreSeparacaoItem) and not obj.recomposto:
            processor.add_movimentacao_prevista(
                obj.data_expedicao_editada,
                obj.cod_produto,
                'SAIDA_PREVISTA',
                obj.qtd_selecionada_usuario,
                'PreSeparacao',
                obj.separacao_lote_id
            )
    
    for obj in session.dirty:
        if isinstance(obj, PreSeparacaoItem):
            # Verificar se mudou de não-recomposto para recomposto
            hist = db.inspect(obj).attrs.recomposto.history
            if hist.has_changes() and obj.recomposto and not hist.deleted[0]:
                # Remover previsão (quantidade = 0)
                processor.add_movimentacao_prevista(
                    obj.data_expedicao_editada,
                    obj.cod_produto,
                    'SAIDA_PREVISTA',
                    0,
                    'PreSeparacao',
                    obj.separacao_lote_id
                )
    
    # Processar Separacao
    for obj in session.new:
        if isinstance(obj, Separacao) and obj.expedicao:
            processor.add_movimentacao_prevista(
                obj.expedicao,
                obj.cod_produto,
                'SAIDA_PREVISTA',
                obj.qtd_saldo or 0,
                'Separacao',
                obj.separacao_lote_id
            )
    
    # Processar ProgramacaoProducao
    for obj in session.new:
        if isinstance(obj, ProgramacaoProducao) and obj.data_programada:
            processor.add_movimentacao_prevista(
                obj.data_programada,
                obj.cod_produto,
                'ENTRADA_PREVISTA',
                obj.quantidade_programada,
                'Producao',
                str(obj.id)
            )


@event.listens_for(Session, 'after_commit')
def process_after_commit(session):
    """Processa todas as atualizações APÓS o commit"""
    processor.process_all()


@event.listens_for(Session, 'after_rollback')
def clear_after_rollback(session):
    """Limpa pendências após rollback"""
    processor.pending_updates.clear()
    processor.pending_previstas.clear()


def registrar_triggers_after_commit():
    """
    Registra os triggers after_commit
    Deve ser chamado na inicialização da aplicação
    """
    # Os eventos já são registrados ao importar este módulo
    logger.info("✅ Triggers after_commit registrados com sucesso")
    return True