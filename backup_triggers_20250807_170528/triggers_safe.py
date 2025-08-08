"""
Sistema de Triggers Seguro para Estoque em Tempo Real
Solução definitiva que evita erros de sessão e garante sincronização
"""

from sqlalchemy import event
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date
import logging
from app.utils.timezone import agora_brasil

logger = logging.getLogger(__name__)


class TriggerProcessor:
    """
    Processador de eventos que funciona de forma segura com SQLAlchemy
    """
    
    def __init__(self):
        self.pending_operations = []
        self.in_processing = False
    
    def add_operation(self, operation_type, data):
        """Adiciona operação para processar depois"""
        if not self.in_processing:
            self.pending_operations.append({
                'type': operation_type,
                'data': data
            })
    
    def process_all(self, db_session):
        """Processa todas as operações pendentes de forma segura"""
        if self.in_processing or not self.pending_operations:
            return
        
        self.in_processing = True
        operations_to_process = self.pending_operations.copy()
        self.pending_operations.clear()
        
        try:
            # Importar aqui para evitar circular
            from app.estoque.models import UnificacaoCodigos
            from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
            
            for op in operations_to_process:
                try:
                    if op['type'] == 'estoque_update':
                        self._process_estoque_update(op['data'], db_session)
                    elif op['type'] == 'movimentacao_prevista':
                        self._process_movimentacao_prevista(op['data'], db_session)
                except Exception as e:
                    logger.error(f"Erro ao processar operação {op['type']}: {e}")
            
            # Fazer flush apenas uma vez no final
            db_session.flush()
            
        except Exception as e:
            logger.error(f"Erro geral no processamento: {e}")
        finally:
            self.in_processing = False
    
    def _process_estoque_update(self, data, db_session):
        """Processa atualização de estoque"""
        from app.estoque.models import UnificacaoCodigos
        from app.estoque.models_tempo_real import EstoqueTempoReal
        
        # Obter códigos unificados
        codigos = UnificacaoCodigos.get_todos_codigos_relacionados(data['cod_produto'])
        
        for codigo in codigos:
            estoque = db_session.query(EstoqueTempoReal).filter_by(cod_produto=codigo).first()
            
            if not estoque:
                estoque = EstoqueTempoReal(
                    cod_produto=codigo,
                    nome_produto=data.get('nome_produto') or f"Produto {codigo}",
                    saldo_atual=Decimal('0')
                )
                db_session.add(estoque)
            
            # Atualizar saldo
            estoque.saldo_atual = Decimal(str(estoque.saldo_atual)) + Decimal(str(data['delta']))
            estoque.atualizado_em = agora_brasil()
            
            logger.debug(f"✅ Estoque: {codigo} ({data['delta']:+.2f}) = {estoque.saldo_atual}")
    
    def _process_movimentacao_prevista(self, data, db_session):
        """Processa movimentação prevista"""
        from app.estoque.models import UnificacaoCodigos
        from app.estoque.models_tempo_real import MovimentacaoPrevista
        
        # Obter códigos unificados
        codigos = UnificacaoCodigos.get_todos_codigos_relacionados(data['cod_produto'])
        
        for codigo in codigos:
            # Buscar existente pela chave única (apenas cod_produto e data_prevista)
            existente = db_session.query(MovimentacaoPrevista).filter_by(
                data_prevista=data['data'],
                cod_produto=codigo
            ).first()
            
            if existente:
                # Atualizar quantidade
                if data['tipo'] == 'ENTRADA_PREVISTA':
                    existente.entrada_prevista = Decimal(str(data['quantidade']))
                else:  # SAIDA_PREVISTA
                    existente.saida_prevista = Decimal(str(data['quantidade']))
                
                # Se zerou, deletar
                if existente.entrada_prevista <= 0 and existente.saida_prevista <= 0:
                    db_session.delete(existente)
            else:
                # Criar nova apenas se quantidade > 0
                if data['quantidade'] > 0:
                    nova = MovimentacaoPrevista(
                        data_prevista=data['data'],
                        cod_produto=codigo,
                        entrada_prevista=Decimal(str(data['quantidade'])) if data['tipo'] == 'ENTRADA_PREVISTA' else Decimal('0'),
                        saida_prevista=Decimal(str(data['quantidade'])) if data['tipo'] == 'SAIDA_PREVISTA' else Decimal('0')
                    )
                    db_session.add(nova)
            
            logger.debug(f"✅ Prevista: {codigo} em {data['data']} - {data['tipo']}: {data['quantidade']}")


# Instância global do processador
processor = TriggerProcessor()


# ============================================================================
# TRIGGERS PARA MOVIMENTAÇÃO DE ESTOQUE
# ============================================================================

def processar_movimentacao_estoque(mapper, connection, target):
    """Processa movimentação de estoque após insert/update/delete"""
    from app.estoque.models import MovimentacaoEstoque
    
    if not isinstance(target, MovimentacaoEstoque) or not target.ativo:
        return
    
    # Calcular delta baseado no evento
    if target in connection.info.get('deleted_objects', []):
        # Delete - reverter movimentação
        delta = -Decimal(str(target.qtd_movimentacao))
    else:
        # Insert ou Update
        hist = connection.info.get('history', {}).get(id(target), {})
        if 'qtd_movimentacao' in hist:
            # Update - calcular diferença
            qtd_anterior = hist['qtd_movimentacao']
            delta = Decimal(str(target.qtd_movimentacao)) - Decimal(str(qtd_anterior))
        else:
            # Insert - usar valor direto
            delta = Decimal(str(target.qtd_movimentacao))
    
    processor.add_operation('estoque_update', {
        'cod_produto': target.cod_produto,
        'delta': delta,
        'nome_produto': target.nome_produto
    })


# ============================================================================
# TRIGGERS PARA PRÉ-SEPARAÇÃO
# ============================================================================

def processar_pre_separacao(mapper, connection, target):
    """Processa pré-separação após insert/update/delete"""
    from app.carteira.models import PreSeparacaoItem
    
    if not isinstance(target, PreSeparacaoItem):
        return
    
    # Só processar se não está recomposto e tem data de expedição
    if target.recomposto or not target.data_expedicao_editada:
        return
    
    # Determinar quantidade baseado no evento
    if target in connection.info.get('deleted_objects', []):
        # Delete - quantidade zero para remover
        quantidade = 0
    else:
        # Insert ou Update - usar quantidade atual
        quantidade = target.qtd_selecionada_usuario
    
    processor.add_operation('movimentacao_prevista', {
        'data': target.data_expedicao_editada,
        'cod_produto': target.cod_produto,
        'tipo': 'SAIDA_PREVISTA',
        'quantidade': quantidade,
        'origem': 'PreSeparacao',
        'origem_id': target.separacao_lote_id or str(target.id)
    })


# ============================================================================
# TRIGGERS PARA SEPARAÇÃO
# ============================================================================

def processar_separacao(mapper, connection, target):
    """Processa separação após insert/update/delete"""
    from app.separacao.models import Separacao
    
    if not isinstance(target, Separacao):
        return
    
    # Só processar se tem data de expedição e quantidade
    if not target.expedicao or not target.qtd_saldo:
        return
    
    # Determinar quantidade baseado no evento
    if target in connection.info.get('deleted_objects', []):
        # Delete - quantidade zero para remover
        quantidade = 0
    else:
        # Insert ou Update - usar quantidade atual
        quantidade = target.qtd_saldo or 0
    
    processor.add_operation('movimentacao_prevista', {
        'data': target.expedicao,
        'cod_produto': target.cod_produto,
        'tipo': 'SAIDA_PREVISTA',
        'quantidade': quantidade,
        'origem': 'Separacao',
        'origem_id': target.separacao_lote_id
    })


# ============================================================================
# TRIGGERS PARA PROGRAMAÇÃO DE PRODUÇÃO
# ============================================================================

def processar_producao(mapper, connection, target):
    """Processa programação de produção após insert/update/delete"""
    from app.producao.models import ProgramacaoProducao
    
    if not isinstance(target, ProgramacaoProducao):
        return
    
    # Campos corretos do modelo: data_programacao e qtd_programada
    # Só processar se tem data e quantidade
    if not target.data_programacao or not target.qtd_programada:
        return
    
    # Determinar quantidade baseado no evento
    if target in connection.info.get('deleted_objects', []):
        # Delete - quantidade zero para remover
        quantidade = 0
    else:
        # Insert ou Update - usar quantidade atual
        quantidade = target.qtd_programada or 0
    
    processor.add_operation('movimentacao_prevista', {
        'data': target.data_programacao,
        'cod_produto': target.cod_produto,
        'tipo': 'ENTRADA_PREVISTA',
        'quantidade': quantidade,
        'origem': 'Producao',
        'origem_id': str(target.id)
    })


# ============================================================================
# EVENTO PRINCIPAL: PROCESSAR APÓS FLUSH
# ============================================================================

@event.listens_for(Session, 'after_flush')
def after_flush(session, flush_context):
    """Processa todas as operações após o flush mas antes do commit"""
    # Processar todas as operações pendentes
    processor.process_all(session)


@event.listens_for(Session, 'after_rollback')
def after_rollback(session):
    """Limpa operações pendentes após rollback"""
    processor.pending_operations.clear()
    processor.in_processing = False


def registrar_triggers_safe():
    """
    Registra todos os triggers de forma segura
    """
    from app.estoque.models import MovimentacaoEstoque
    from app.carteira.models import PreSeparacaoItem
    from app.separacao.models import Separacao
    from app.producao.models import ProgramacaoProducao
    
    # Registrar eventos para cada modelo
    for evt in ['after_insert', 'after_update', 'after_delete']:
        event.listen(MovimentacaoEstoque, evt, processar_movimentacao_estoque)
        event.listen(PreSeparacaoItem, evt, processar_pre_separacao)
        event.listen(Separacao, evt, processar_separacao)
        event.listen(ProgramacaoProducao, evt, processar_producao)
    
    logger.info("✅ Triggers seguros registrados com sucesso")
    return True