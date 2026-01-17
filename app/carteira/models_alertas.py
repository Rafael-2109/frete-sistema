"""
Modelo para Alertas de Separações Cotadas Alteradas
=====================================================

Sistema de controle de alterações em separações com status COTADO
que precisam de reimpressão após sincronização com Odoo.
"""

from app import db
from datetime import datetime
from sqlalchemy import and_


class AlertaSeparacaoCotada(db.Model):
    """
    Registra alterações em separações COTADAS que precisam ser reimpressas
    
    Regra: QUALQUER alteração em separação COTADA (TOTAL ou PARCIAL) gera alerta
    """
    __tablename__ = 'alertas_separacao_cotada'
    
    id = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50), nullable=False, index=True)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False)
    
    # Tipo de alteração
    tipo_alteracao = db.Column(db.String(20), nullable=False)  # 'REDUCAO', 'AUMENTO', 'REMOCAO', 'ADICAO'
    qtd_anterior = db.Column(db.Float, default=0)
    qtd_nova = db.Column(db.Float, default=0)
    qtd_diferenca = db.Column(db.Float, default=0)  # Positivo=aumento, Negativo=redução
    
    # Controle de reimpressão
    reimpresso = db.Column(db.Boolean, default=False, index=True)
    data_alerta = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    data_reimpressao = db.Column(db.DateTime, nullable=True)
    reimpresso_por = db.Column(db.String(100), nullable=True)
    
    # Dados adicionais para contexto
    nome_produto = db.Column(db.String(255), nullable=True)
    cliente = db.Column(db.String(255), nullable=True)
    embarque_numero = db.Column(db.Integer, nullable=True)
    tipo_separacao = db.Column(db.String(10), nullable=True)  # 'TOTAL' ou 'PARCIAL'
    
    # Observações
    observacao = db.Column(db.Text, nullable=True)
    
    @classmethod
    def criar_alerta(cls, separacao_lote_id, num_pedido, cod_produto, tipo_alteracao, 
                     qtd_anterior, qtd_nova, embarque_numero=None, tipo_separacao=None):
        """
        Cria um novo alerta de alteração em separação COTADA
        """
        # Verificar se já existe alerta não reimpresso para este item
        alerta_existente = cls.query.filter(
            and_(
                cls.separacao_lote_id == separacao_lote_id,
                cls.num_pedido == num_pedido,
                cls.cod_produto == cod_produto,
                cls.reimpresso == False
            )
        ).first()
        
        if alerta_existente:
            # Atualizar alerta existente com nova alteração
            alerta_existente.qtd_nova = qtd_nova
            alerta_existente.qtd_diferenca = qtd_nova - alerta_existente.qtd_anterior
            alerta_existente.tipo_alteracao = tipo_alteracao
            alerta_existente.data_alerta = datetime.utcnow()
            return alerta_existente
        
        # Criar novo alerta
        alerta = cls(
            separacao_lote_id=separacao_lote_id,
            num_pedido=num_pedido,
            cod_produto=cod_produto,
            tipo_alteracao=tipo_alteracao,
            qtd_anterior=qtd_anterior,
            qtd_nova=qtd_nova,
            qtd_diferenca=qtd_nova - qtd_anterior,
            embarque_numero=embarque_numero,
            tipo_separacao=tipo_separacao
        )
        
        # Buscar dados adicionais
        try:
            from app.separacao.models import Separacao
            separacao = Separacao.query.filter_by(
                separacao_lote_id=separacao_lote_id,
                num_pedido=num_pedido,
                cod_produto=cod_produto
            ).first()
            
            if separacao:
                alerta.nome_produto = separacao.nome_produto
                alerta.cliente = separacao.raz_social_red
        except Exception as e:
            print(f"Erro ao buscar dados adicionais: {e}")
            pass
        
        db.session.add(alerta)
        return alerta
    
    @classmethod
    def buscar_alertas_pendentes(cls):
        """
        Retorna todos os alertas não reimpresos agrupados por embarque
        """
        from app.embarques.models import Embarque, EmbarqueItem
        from app.pedidos.models import Pedido
        
        # Buscar alertas não reimpresos
        alertas = cls.query.filter_by(reimpresso=False).all()
        
        if not alertas:
            return {}
        
        # Agrupar por embarque
        alertas_por_embarque = {}
        
        for alerta in alertas:
            # Buscar o embarque através do separacao_lote_id
            pedido = Pedido.query.filter_by(
                separacao_lote_id=alerta.separacao_lote_id
            ).first()
            
            if pedido:
                # Buscar o embarque - IMPORTANTE: só embarques ATIVOS!
                embarque_item = EmbarqueItem.query.filter_by(
                    separacao_lote_id=alerta.separacao_lote_id,
                    status='ativo'  # Ignorar embarques cancelados
                ).first()
                
                if not embarque_item:
                    # Se não achou pelo lote, tentar pelo pedido (caso lote tenha sido substituído)
                    embarque_item = EmbarqueItem.query.filter_by(
                        pedido=alerta.num_pedido,
                        status='ativo'
                    ).first()
                
                if embarque_item:
                    embarque = db.session.get(Embarque,embarque_item.embarque_id) if embarque_item.embarque_id else None

                    if embarque:
                        embarque_num = embarque.numero or f"ID-{embarque.id}"
                        
                        if embarque_num not in alertas_por_embarque:
                            alertas_por_embarque[embarque_num] = {
                                'embarque_id': embarque.id,
                                'embarque_numero': embarque_num,
                                'data_embarque': embarque.data_embarque,
                                'transportadora': embarque.transportadora.razao_social if embarque.transportadora and hasattr(embarque.transportadora, 'razao_social') else 'N/A',
                                'pedidos': {}
                            }
                        
                        if alerta.num_pedido not in alertas_por_embarque[embarque_num]['pedidos']:
                            alertas_por_embarque[embarque_num]['pedidos'][alerta.num_pedido] = {
                                'separacao_lote_id': alerta.separacao_lote_id,
                                'cliente': alerta.cliente,
                                'itens': []
                            }
                        
                        alertas_por_embarque[embarque_num]['pedidos'][alerta.num_pedido]['itens'].append({
                            'alerta_id': alerta.id,
                            'cod_produto': alerta.cod_produto,
                            'nome_produto': alerta.nome_produto,
                            'tipo_alteracao': alerta.tipo_alteracao,
                            'qtd_anterior': alerta.qtd_anterior,
                            'qtd_nova': alerta.qtd_nova,
                            'qtd_diferenca': alerta.qtd_diferenca,
                            'data_alerta': alerta.data_alerta
                        })
        
        return alertas_por_embarque
    
    @classmethod
    def marcar_como_reimpresso(cls, num_pedido, separacao_lote_id, usuario):
        """
        Marca todos os alertas de um pedido/separação como reimpresos
        """
        alertas = cls.query.filter(
            and_(
                cls.num_pedido == num_pedido,
                cls.separacao_lote_id == separacao_lote_id,
                cls.reimpresso == False
            )
        ).all()
        
        for alerta in alertas:
            alerta.reimpresso = True
            alerta.data_reimpressao = datetime.utcnow()
            alerta.reimpresso_por = usuario
        
        db.session.commit()
        return len(alertas)
    
    @classmethod
    def contar_alertas_pendentes(cls):
        """
        Retorna a quantidade de alertas pendentes de reimpressão
        que têm pedido e embarque ativo (que serão exibidos)
        """
        # Usar o mesmo método que busca os alertas para garantir consistência
        alertas_agrupados = cls.buscar_alertas_pendentes()
        
        # Contar total de alertas em todos os embarques
        total = 0
        for embarque_info in alertas_agrupados.values():
            for pedido_info in embarque_info['pedidos'].values():
                total += len(pedido_info['itens'])
        
        return total
    
    def __repr__(self):
        return f'<AlertaSeparacaoCotada {self.num_pedido}/{self.cod_produto} - {self.tipo_alteracao}>'
