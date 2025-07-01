from app import db
from datetime import datetime
from app.utils.timezone import agora_brasil
from sqlalchemy import inspect, and_, or_
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MovimentacaoEstoque(db.Model):
    """
    Modelo para controle das movimentações de estoque
    """
    __tablename__ = 'movimentacao_estoque'

    id = db.Column(db.Integer, primary_key=True)
    
    # Dados do produto
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(200), nullable=False)
    
    # Dados da movimentação
    data_movimentacao = db.Column(db.Date, nullable=False, index=True)
    tipo_movimentacao = db.Column(db.String(50), nullable=False, index=True)  # ENTRADA, SAIDA, AJUSTE, PRODUCAO
    local_movimentacao = db.Column(db.String(50), nullable=False)  # COMPRA, VENDA, PRODUCAO, AJUSTE, DEVOLUCAO
    
    # Quantidades
    qtd_movimentacao = db.Column(db.Numeric(15, 3), nullable=False)

    # Observações
    observacao = db.Column(db.Text, nullable=True)

        
    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)

    # Índices compostos para performance  
    __table_args__ = (
        db.Index('idx_movimentacao_produto_data', 'cod_produto', 'data_movimentacao'),
        db.Index('idx_movimentacao_tipo_data', 'tipo_movimentacao', 'data_movimentacao'),
    )

    def __repr__(self):
        return f'<MovimentacaoEstoque {self.cod_produto} - {self.tipo_movimentacao} - {self.qtd_movimentacao}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'data_movimentacao': self.data_movimentacao.strftime('%d/%m/%Y') if self.data_movimentacao else None,
            'tipo_movimentacao': self.tipo_movimentacao,
            'local_movimentacao': self.local_movimentacao,
            'qtd_movimentacao': float(self.qtd_movimentacao) if self.qtd_movimentacao else 0,
            'observacao': self.observacao
        }


class UnificacaoCodigos(db.Model):
    """
    Modelo para unificação de códigos de produtos
    Permite tratar códigos diferentes como mesmo produto físico para fins de estoque
    """
    __tablename__ = 'unificacao_codigos'

    id = db.Column(db.Integer, primary_key=True)
    
    # Códigos de unificação
    codigo_origem = db.Column(db.Integer, nullable=False, index=True)
    codigo_destino = db.Column(db.Integer, nullable=False, index=True) 
    
    # Observações
    observacao = db.Column(db.Text, nullable=True)
    
    # Auditoria completa
    ativo = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    created_by = db.Column(db.String(100), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)
    
    # Histórico de ativação/desativação
    data_ativacao = db.Column(db.DateTime, nullable=True)
    data_desativacao = db.Column(db.DateTime, nullable=True)
    motivo_desativacao = db.Column(db.Text, nullable=True)
    
    # Índices compostos para performance e integridade
    __table_args__ = (
        # Evita duplicação: mesmo par origem-destino
        db.UniqueConstraint('codigo_origem', 'codigo_destino', name='uq_unificacao_origem_destino'),
        # Evita ciclos: A->B e B->A simultaneamente  
        db.Index('idx_unificacao_origem', 'codigo_origem'),
        db.Index('idx_unificacao_destino', 'codigo_destino'),
        db.Index('idx_unificacao_ativo', 'ativo'),
    )

    def __repr__(self):
        status = "Ativo" if self.ativo else "Inativo"
        return f'<UnificacaoCodigos {self.codigo_origem} → {self.codigo_destino} [{status}]>'

    def to_dict(self):
        return {
            'id': self.id,
            'codigo_origem': self.codigo_origem,
            'codigo_destino': self.codigo_destino,
            'observacao': self.observacao,
            'ativo': self.ativo,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%d/%m/%Y %H:%M') if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'data_ativacao': self.data_ativacao.strftime('%d/%m/%Y %H:%M') if self.data_ativacao else None,
            'data_desativacao': self.data_desativacao.strftime('%d/%m/%Y %H:%M') if self.data_desativacao else None,
            'motivo_desativacao': self.motivo_desativacao
        }

    @classmethod
    def get_codigo_unificado(cls, codigo_produto):
        """
        Retorna o código destino se existe unificação ativa, senão retorna o próprio código
        """
        try:
            codigo_produto = int(codigo_produto)
            
            # Busca se o código é origem em alguma unificação ativa
            unificacao = cls.query.filter_by(
                codigo_origem=codigo_produto,
                ativo=True
            ).first()
            
            if unificacao:
                return unificacao.codigo_destino
                
            # Se não é origem, verifica se é destino (para estatísticas)
            return codigo_produto
            
        except (ValueError, TypeError):
            return codigo_produto

    @classmethod
    def get_todos_codigos_relacionados(cls, codigo_produto):
        """
        Retorna todos os códigos relacionados ao código informado
        Usado para estatísticas e consolidação
        """
        try:
            codigo_produto = int(codigo_produto)
            codigos_relacionados = set([codigo_produto])
            
            # Busca códigos que apontam para este (este é destino)
            origens = cls.query.filter_by(
                codigo_destino=codigo_produto,
                ativo=True
            ).all()
            
            for origem in origens:
                codigos_relacionados.add(origem.codigo_origem)
            
            # Busca para onde este código aponta (este é origem)
            destino = cls.query.filter_by(
                codigo_origem=codigo_produto,
                ativo=True
            ).first()
            
            if destino:
                codigos_relacionados.add(destino.codigo_destino)
                # Busca outros códigos que também apontam para o mesmo destino
                outros_origens = cls.query.filter_by(
                    codigo_destino=destino.codigo_destino,
                    ativo=True
                ).all()
                for outro in outros_origens:
                    codigos_relacionados.add(outro.codigo_origem)
            
            return list(codigos_relacionados)
            
        except (ValueError, TypeError):
            return [codigo_produto]

    def ativar(self, usuario=None, motivo=None):
        """Ativa a unificação"""
        self.ativo = True
        self.data_ativacao = agora_brasil()
        self.updated_by = usuario
        self.motivo_desativacao = None
        
    def desativar(self, usuario=None, motivo=None):
        """Desativa a unificação"""
        self.ativo = False
        self.data_desativacao = agora_brasil()
        self.updated_by = usuario
        self.motivo_desativacao = motivo 

class SaldoEstoque:
    """
    Classe de serviço para cálculos de saldo de estoque em tempo real
    Não é uma tabela persistente, mas sim um calculador que integra dados de:
    - MovimentacaoEstoque (módulo já existente)
    - ProgramacaoProducao (módulo já existente) 
    - CarteiraPedidos (futuro - arquivo 1)
    - UnificacaoCodigos (módulo recém implementado)
    """
    
    @staticmethod
    def obter_produtos_com_estoque():
        """Obtém lista de produtos únicos que têm movimentação de estoque"""
        try:
            inspector = inspect(db.engine)
            if not inspector.has_table('movimentacao_estoque'):
                return []
            
            # Buscar produtos únicos com movimentação
            produtos = db.session.query(
                MovimentacaoEstoque.cod_produto,
                MovimentacaoEstoque.nome_produto
            ).filter(
                MovimentacaoEstoque.ativo == True
            ).distinct().all()
            
            return produtos
            
        except Exception as e:
            logger.error(f"Erro ao obter produtos com estoque: {str(e)}")
            return []
    
    @staticmethod
    def calcular_estoque_inicial(cod_produto):
        """Calcula estoque inicial (D0) baseado em todas as movimentações"""
        try:
            inspector = inspect(db.engine)
            if not inspector.has_table('movimentacao_estoque'):
                return 0
            
            # Buscar todos os códigos relacionados (considerando unificação)
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(int(cod_produto))
            
            # Somar movimentações de todos os códigos relacionados
            total_estoque = 0
            for codigo in codigos_relacionados:
                movimentacoes = MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.cod_produto == str(codigo),
                    MovimentacaoEstoque.ativo == True
                ).all()
                
                total_estoque += sum(float(m.qtd_movimentacao) for m in movimentacoes)
            
            return total_estoque
            
        except Exception as e:
            logger.error(f"Erro ao calcular estoque inicial para {cod_produto}: {str(e)}")
            return 0
    
    @staticmethod
    def calcular_producao_periodo(cod_produto, data_inicio, data_fim):
        """Calcula produção programada para um produto em um período"""
        try:
            inspector = inspect(db.engine)
            if not inspector.has_table('programacao_producao'):
                return 0
            
            # Buscar todos os códigos relacionados (considerando unificação)
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(int(cod_produto))
            
            # Somar produção de todos os códigos relacionados
            total_producao = 0
            for codigo in codigos_relacionados:
                from app.producao.models import ProgramacaoProducao
                
                producoes = ProgramacaoProducao.query.filter(
                    ProgramacaoProducao.cod_produto == str(codigo),
                    ProgramacaoProducao.data_programacao >= data_inicio,
                    ProgramacaoProducao.data_programacao <= data_fim
                ).all()
                
                total_producao += sum(float(p.qtd_programada) for p in producoes)
            
            return total_producao
            
        except Exception as e:
            logger.error(f"Erro ao calcular produção para {cod_produto}: {str(e)}")
            return 0
    
    @staticmethod
    def calcular_saida_periodo(cod_produto, data_inicio, data_fim):
        """
        Calcula saída prevista para um produto em um período
        Por enquanto retorna 0 - será implementado quando tiver carteira de pedidos
        """
        # TODO: Implementar quando tiver módulo carteira de pedidos (arquivo 1)
        return 0
    
    @staticmethod
    def calcular_projecao_completa(cod_produto):
        """Calcula projeção completa de estoque para 29 dias (D0 até D+28)"""
        try:
            projecao = []
            data_hoje = datetime.now().date()
            
            # Estoque inicial (D0)
            estoque_atual = SaldoEstoque.calcular_estoque_inicial(cod_produto)
            
            # Calcular para cada dia (D0 até D+28)
            for dia in range(29):
                data_calculo = data_hoje + timedelta(days=dia)
                data_fim_dia = data_calculo
                
                # Saída prevista para o dia (futuro - carteira de pedidos)
                saida_dia = SaldoEstoque.calcular_saida_periodo(cod_produto, data_calculo, data_fim_dia)
                
                # Produção programada para o dia
                producao_dia = SaldoEstoque.calcular_producao_periodo(cod_produto, data_calculo, data_fim_dia)
                
                # Cálculo do estoque final do dia
                if dia == 0:
                    estoque_inicial_dia = estoque_atual
                else:
                    estoque_inicial_dia = projecao[dia-1]['estoque_final']
                
                estoque_final_dia = estoque_inicial_dia - saida_dia + producao_dia
                
                # Dados do dia
                dia_dados = {
                    'dia': dia,
                    'data': data_calculo,
                    'data_formatada': data_calculo.strftime('%d/%m'),
                    'estoque_inicial': estoque_inicial_dia,
                    'saida_prevista': saida_dia,
                    'producao_programada': producao_dia,
                    'estoque_final': estoque_final_dia
                }
                
                projecao.append(dia_dados)
            
            return projecao
            
        except Exception as e:
            logger.error(f"Erro ao calcular projeção para {cod_produto}: {str(e)}")
            return []
    
    @staticmethod
    def calcular_previsao_ruptura(projecao):
        """Calcula previsão de ruptura (menor estoque em 7 dias)"""
        try:
            if not projecao or len(projecao) < 8:
                return 0
            
            # Pegar estoque final dos primeiros 8 dias (D0 até D7)
            estoques_7_dias = [dia['estoque_final'] for dia in projecao[:8]]
            
            return min(estoques_7_dias)
            
        except Exception as e:
            logger.error(f"Erro ao calcular previsão de ruptura: {str(e)}")
            return 0
    
    @staticmethod
    def obter_resumo_produto(cod_produto, nome_produto):
        """Obtém resumo completo de um produto"""
        try:
            # Calcular projeção completa
            projecao = SaldoEstoque.calcular_projecao_completa(cod_produto)
            
            if not projecao:
                return None
            
            # Dados principais
            estoque_inicial = projecao[0]['estoque_inicial']
            previsao_ruptura = SaldoEstoque.calcular_previsao_ruptura(projecao)
            
            # Totais carteira (futuro)
            qtd_total_carteira = 0  # TODO: Implementar com arquivo 1
            
            resumo = {
                'cod_produto': cod_produto,
                'nome_produto': nome_produto,
                'estoque_inicial': estoque_inicial,
                'qtd_total_carteira': qtd_total_carteira,
                'previsao_ruptura': previsao_ruptura,
                'projecao_29_dias': projecao,
                'status_ruptura': 'CRÍTICO' if previsao_ruptura <= 0 else 'ATENÇÃO' if previsao_ruptura < 10 else 'OK'
            }
            
            return resumo
            
        except Exception as e:
            logger.error(f"Erro ao obter resumo do produto {cod_produto}: {str(e)}")
            return None
    
    @staticmethod
    def processar_ajuste_estoque(cod_produto, qtd_ajuste, motivo, usuario):
        """Processa ajuste de estoque gerando movimentação automática"""
        try:
            # Buscar nome do produto
            produto_existente = MovimentacaoEstoque.query.filter_by(
                cod_produto=str(cod_produto),
                ativo=True
            ).first()
            
            if not produto_existente:
                raise ValueError(f"Produto {cod_produto} não encontrado nas movimentações")
            
            # Criar movimentação de ajuste
            ajuste = MovimentacaoEstoque(
                cod_produto=str(cod_produto),
                nome_produto=produto_existente.nome_produto,
                tipo_movimentacao='AJUSTE',
                local_movimentacao='CD',
                data_movimentacao=datetime.now().date(),
                qtd_movimentacao=float(qtd_ajuste),
                observacao=f'Ajuste manual: {motivo}',
                criado_por=usuario,
                atualizado_por=usuario
            )
            
            db.session.add(ajuste)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao processar ajuste de estoque: {str(e)}")
            raise e 