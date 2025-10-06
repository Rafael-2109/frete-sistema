"""
Adapter para fazer PreSeparacaoItem funcionar usando Separacao
Data: 2025-01-29

Este adapter permite manter o código existente funcionando
enquanto migramos gradualmente para usar Separacao com status='PREVISAO'
"""

from app import db
from datetime import datetime
from app.separacao.models import Separacao
from app.utils.text_utils import truncar_observacao
from sqlalchemy import and_, or_
import logging

logger = logging.getLogger(__name__)

class PreSeparacaoItemAdapter:
    """
    Adapter que simula PreSeparacaoItem usando Separacao com status='PREVISAO'
    """
    
    # Status em Separacao que representa uma pré-separação
    STATUS_PREVISAO = 'PREVISAO'
    STATUS_CONFIRMADO = 'ABERTO'
    
    def __init__(self, separacao=None):
        """
        Inicializa o adapter com uma Separacao ou cria uma nova
        """
        if separacao:
            self._separacao = separacao
        else:
            self._separacao = Separacao()
            self._separacao.status = self.STATUS_PREVISAO
            self._separacao.sincronizado_nf = False  # IMPORTANTE: Sempre criar com False
    
    # Mapeamento de campos PreSeparacaoItem → Separacao
    @property
    def id(self):
        return self._separacao.id
    
    @property
    def separacao_lote_id(self):
        return self._separacao.separacao_lote_id
    
    @separacao_lote_id.setter
    def separacao_lote_id(self, value):
        self._separacao.separacao_lote_id = value
    
    @property
    def num_pedido(self):
        return self._separacao.num_pedido
    
    @num_pedido.setter
    def num_pedido(self, value):
        self._separacao.num_pedido = value
    
    @property
    def cod_produto(self):
        return self._separacao.cod_produto
    
    @cod_produto.setter
    def cod_produto(self, value):
        self._separacao.cod_produto = value
    
    @property
    def nome_produto(self):
        return self._separacao.nome_produto
    
    @nome_produto.setter
    def nome_produto(self, value):
        self._separacao.nome_produto = value
    
    @property
    def cnpj_cliente(self):
        return self._separacao.cnpj_cpf
    
    @cnpj_cliente.setter
    def cnpj_cliente(self, value):
        self._separacao.cnpj_cpf = value
    
    # Mapeamento de quantidades
    @property
    def qtd_original_carteira(self):
        # Em Separacao não temos campo específico, usar qtd_saldo como base
        return self._separacao.qtd_saldo
    
    @qtd_original_carteira.setter
    def qtd_original_carteira(self, value):
        # Armazenar em qtd_saldo se não houver qtd_selecionada
        if not hasattr(self, '_qtd_selecionada'):
            self._separacao.qtd_saldo = value
    
    @property
    def qtd_selecionada_usuario(self):
        # Usar qtd_saldo como quantidade selecionada
        return self._separacao.qtd_saldo
    
    @qtd_selecionada_usuario.setter
    def qtd_selecionada_usuario(self, value):
        self._separacao.qtd_saldo = value
        self._qtd_selecionada = value
    
    @property
    def qtd_restante_calculada(self):
        # Calcular restante (não usado em Separacao)
        return 0
    
    @qtd_restante_calculada.setter
    def qtd_restante_calculada(self, value):
        # Ignorar, não temos este campo em Separacao
        pass
    
    # Valores e pesos
    @property
    def valor_original_item(self):
        return self._separacao.valor_saldo
    
    @valor_original_item.setter
    def valor_original_item(self, value):
        self._separacao.valor_saldo = value
    
    @property
    def peso_original_item(self):
        return self._separacao.peso
    
    @peso_original_item.setter
    def peso_original_item(self, value):
        self._separacao.peso = value
    
    # Datas
    @property
    def data_expedicao_editada(self):
        return self._separacao.expedicao
    
    @data_expedicao_editada.setter
    def data_expedicao_editada(self, value):
        self._separacao.expedicao = value
    
    @property
    def data_agendamento_editada(self):
        return self._separacao.agendamento
    
    @data_agendamento_editada.setter
    def data_agendamento_editada(self, value):
        self._separacao.agendamento = value
    
    @property
    def protocolo_editado(self):
        return self._separacao.protocolo
    
    @protocolo_editado.setter
    def protocolo_editado(self, value):
        self._separacao.protocolo = value
    
    @property
    def observacoes_usuario(self):
        return self._separacao.observ_ped_1
    
    @observacoes_usuario.setter
    def observacoes_usuario(self, value):
        self._separacao.observ_ped_1 = truncar_observacao(value)
    
    # Status e controle
    @property
    def recomposto(self):
        # RECOMPOSTO ainda é PREVISAO (pré-separação recomposta do Odoo)
        # Só não é mais pré-separação quando vira ENVIADO_SEPARACAO
        return self._separacao.status != self.STATUS_PREVISAO
    
    @recomposto.setter
    def recomposto(self, value):
        # recomposto=True significa que foi sincronizado com Odoo mas ainda é pré-separação
        # Mantém status PREVISAO
        if value:
            # RECOMPOSTO ainda é pré-separação, mantém PREVISAO
            self._separacao.status = self.STATUS_PREVISAO
        else:
            self._separacao.status = self.STATUS_PREVISAO
    
    @property
    def status(self):
        # Mapear status de Separacao para status esperado de PreSeparacaoItem
        if self._separacao.status == self.STATUS_PREVISAO:
            # Verificar se tem algum flag para distinguir CRIADO de RECOMPOSTO
            # Por padrão retorna CRIADO
            return getattr(self, '_status_original', 'CRIADO')
        elif self._separacao.status == self.STATUS_CONFIRMADO or self._separacao.status == 'ABERTO':
            return 'ENVIADO_SEPARACAO'
        else:
            return self._separacao.status
    
    @status.setter
    def status(self, value):
        # Mapear status de PreSeparacaoItem para Separacao
        # CRIADO e RECOMPOSTO → PREVISAO
        # ENVIADO_SEPARACAO → ABERTO
        if value in ['CRIADO', 'RECOMPOSTO']:
            self._separacao.status = self.STATUS_PREVISAO
            self._status_original = value  # Guardar status original
        elif value == 'ENVIADO_SEPARACAO':
            self._separacao.status = self.STATUS_CONFIRMADO
        else:
            self._separacao.status = value
    
    @property
    def tipo_envio(self):
        return self._separacao.tipo_envio
    
    @tipo_envio.setter
    def tipo_envio(self, value):
        self._separacao.tipo_envio = value
    
    @property
    def data_criacao(self):
        return self._separacao.criado_em
    
    @data_criacao.setter
    def data_criacao(self, value):
        self._separacao.criado_em = value
    
    @property
    def criado_por(self):
        # Não temos este campo em Separacao, retornar valor padrão
        return getattr(self, '_criado_por', 'Sistema')
    
    @criado_por.setter
    def criado_por(self, value):
        self._criado_por = value
    
    # Métodos para salvar/deletar
    def save(self):
        """Salva a separação no banco"""
        # Garantir status PREVISAO se não estiver recomposto
        if not self.recomposto:
            self._separacao.status = self.STATUS_PREVISAO
        
        db.session.add(self._separacao)
        db.session.commit()
    
    def delete(self):
        """Remove a separação do banco"""
        db.session.delete(self._separacao)
        db.session.commit()
    
    # Query adapter
    @classmethod
    def query_adapter(cls):
        """
        Retorna um objeto que simula PreSeparacaoItem.query
        """
        return PreSeparacaoQueryAdapter()
    
    def to_dict(self):
        """Converte para dicionário (compatibilidade com APIs)"""
        return {
            'id': self.id,
            'separacao_lote_id': self.separacao_lote_id,
            'num_pedido': self.num_pedido,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'cnpj_cliente': self.cnpj_cliente,
            'qtd_original_carteira': self.qtd_original_carteira,
            'qtd_selecionada_usuario': self.qtd_selecionada_usuario,
            'qtd_restante_calculada': self.qtd_restante_calculada,
            'valor_original_item': self.valor_original_item,
            'peso_original_item': self.peso_original_item,
            'data_expedicao_editada': self.data_expedicao_editada,
            'data_agendamento_editada': self.data_agendamento_editada,
            'protocolo_editado': self.protocolo_editado,
            'observacoes_usuario': self.observacoes_usuario,
            'recomposto': self.recomposto,
            'status': self.status,
            'tipo_envio': self.tipo_envio,
            'data_criacao': self.data_criacao,
            'criado_por': self.criado_por
        }


class PreSeparacaoQueryAdapter:
    """
    Adapter que simula PreSeparacaoItem.query usando Separacao
    """
    
    def filter_by(self, **kwargs):
        """Simula filter_by convertendo para query de Separacao"""
        query = Separacao.query
        
        # Converter filtros de PreSeparacaoItem para Separacao
        if 'separacao_lote_id' in kwargs:
            query = query.filter_by(separacao_lote_id=kwargs['separacao_lote_id'])
        
        if 'recomposto' in kwargs:
            if kwargs['recomposto']:
                # Recomposto = status != PREVISAO
                query = query.filter(Separacao.status != PreSeparacaoItemAdapter.STATUS_PREVISAO)
            else:
                # Não recomposto = status = PREVISAO
                query = query.filter_by(status=PreSeparacaoItemAdapter.STATUS_PREVISAO)
        
        if 'status' in kwargs:
            status_map = {
                'CRIADO': PreSeparacaoItemAdapter.STATUS_PREVISAO,
                'CONFIRMADO': PreSeparacaoItemAdapter.STATUS_CONFIRMADO
            }
            mapped_status = status_map.get(kwargs['status'], kwargs['status'])
            query = query.filter_by(status=mapped_status)
        
        if 'cnpj_cliente' in kwargs:
            query = query.filter_by(cnpj_cpf=kwargs['cnpj_cliente'])
        
        if 'cod_produto' in kwargs:
            query = query.filter_by(cod_produto=kwargs['cod_produto'])
        
        if 'num_pedido' in kwargs:
            query = query.filter_by(num_pedido=kwargs['num_pedido'])
        
        # Retornar wrapper dos resultados
        return PreSeparacaoQueryResults(query)
    
    def filter(self, *args):
        """Simula filter convertendo para query de Separacao"""
        from sqlalchemy import and_, or_
        
        query = Separacao.query
        conditions = []
        
        for arg in args:
            # Se for uma comparação ==
            if hasattr(arg, 'left') and hasattr(arg, 'right'):
                if hasattr(arg.left, 'key'):
                    # É uma comparação com campo
                    if arg.left.key == 'num_pedido':
                        conditions.append(Separacao.num_pedido == arg.right.value)
                    elif arg.left.key == 'cod_produto':
                        conditions.append(Separacao.cod_produto == arg.right.value)
                    elif arg.left.key == 'separacao_lote_id':
                        conditions.append(Separacao.separacao_lote_id == arg.right.value)
                    else:
                        # Tentar adicionar como está
                        conditions.append(arg)
            else:
                # Se for outro tipo de filtro (como status.in_), já foi tratado pela StatusField
                # Adicionar direto
                conditions.append(arg)
        
        if conditions:
            query = query.filter(*conditions)
        else:
            # Se não há condições, retornar apenas status PREVISAO
            query = query.filter_by(status=PreSeparacaoItemAdapter.STATUS_PREVISAO)
        
        return PreSeparacaoQueryResults(query)
    
    def get(self, id):
        """Simula get por ID"""
        separacao = Separacao.query.get(id)
        if separacao and separacao.status == PreSeparacaoItemAdapter.STATUS_PREVISAO:
            return PreSeparacaoItemAdapter(separacao)
        return None
    
    def all(self):
        """Retorna todas as pré-separações (status=PREVISAO)"""
        separacoes = Separacao.query.filter_by(
            status=PreSeparacaoItemAdapter.STATUS_PREVISAO
        ).all()
        return [PreSeparacaoItemAdapter(s) for s in separacoes]


class PreSeparacaoQueryResults:
    """
    Wrapper para resultados de query que converte Separacao em PreSeparacaoItemAdapter
    """
    
    def __init__(self, query):
        self._query = query
    
    def all(self):
        """Retorna todos os resultados como adapters"""
        separacoes = self._query.all()
        return [PreSeparacaoItemAdapter(s) for s in separacoes]
    
    def first(self):
        """Retorna o primeiro resultado como adapter"""
        separacao = self._query.first()
        if separacao:
            return PreSeparacaoItemAdapter(separacao)
        return None
    
    def count(self):
        """Conta os resultados"""
        return self._query.count()
    
    def delete(self):
        """Deleta os registros"""
        return self._query.delete()


class StatusField:
    """
    Classe especial para simular o campo status e suportar .in_()
    """
    def in_(self, values):
        """Simula status.in_(['CRIADO', 'RECOMPOSTO'])"""
        # CRIADO e RECOMPOSTO ambos mapeiam para PREVISAO
        if 'CRIADO' in values or 'RECOMPOSTO' in values:
            return Separacao.status == 'PREVISAO'
        elif 'ENVIADO_SEPARACAO' in values:
            return Separacao.status.in_(['ABERTO', 'FATURADO', 'EMBARCADO'])
        else:
            # Outros valores, passar direto
            return Separacao.status.in_(values)
    
    def __eq__(self, value):
        """Simula status == 'CRIADO'"""
        if value in ['CRIADO', 'RECOMPOSTO']:
            return Separacao.status == 'PREVISAO'
        elif value == 'ENVIADO_SEPARACAO':
            return Separacao.status.in_(['ABERTO', 'FATURADO', 'EMBARCADO'])
        else:
            return Separacao.status == value
    
    def __ne__(self, value):
        """Simula status != 'CRIADO'"""
        if value in ['CRIADO', 'RECOMPOSTO']:
            return Separacao.status != 'PREVISAO'
        elif value == 'ENVIADO_SEPARACAO':
            return ~Separacao.status.in_(['ABERTO', 'FATURADO', 'EMBARCADO'])
        else:
            return Separacao.status != value


class PreSeparacaoItemProxy:
    """
    Proxy para PreSeparacaoItem que intercepta atributos de classe
    """
    # Atributos de classe
    query = PreSeparacaoQueryAdapter()
    status = StatusField()
    
    # Campos que podem ser usados em queries
    num_pedido = Separacao.num_pedido
    cod_produto = Separacao.cod_produto
    separacao_lote_id = Separacao.separacao_lote_id
    cnpj_cliente = Separacao.cnpj_cpf  # Mapeamento de nome
    
    def __new__(cls, *args, **kwargs):
        """Quando instanciado, retorna um adapter"""
        return PreSeparacaoItemAdapter(*args, **kwargs)
    
    def __class_getitem__(cls, key):
        """Para suportar Type hints se necessário"""
        return cls


# Criar alias para manter compatibilidade
PreSeparacaoItem = PreSeparacaoItemProxy