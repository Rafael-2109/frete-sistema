# IMPORTANTE: Registrar tipos PostgreSQL ANTES de usar db
import os
if 'postgres' in os.getenv('DATABASE_URL', ''):
    try:
        import psycopg2 # type: ignore
        from psycopg2 import extensions
        DATE = extensions.new_type((1082,), "DATE", extensions.DATE)
        extensions.register_type(DATE)
        extensions.register_type(DATE, None)
        print("✅ [MODELS] Tipos PostgreSQL registrados em estoque/models.py")
    except Exception as e:
        print(f"⚠️ Erro ao registrar tipos PostgreSQL: {e}")
        pass

from app import db
from app.utils.timezone import agora_brasil
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

    # Campos estruturados para sincronização NF (NOVO)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ID do lote de separação
    numero_nf = db.Column(db.String(20), nullable=True, index=True)  # Número da NF
    num_pedido = db.Column(db.String(50), nullable=True, index=True)  # Número do pedido
    tipo_origem = db.Column(db.String(20), nullable=True)  # ODOO, TAGPLUS, MANUAL, LEGADO
    status_nf = db.Column(db.String(20), nullable=True)  # FATURADO, CANCELADO
    codigo_embarque = db.Column(db.Integer, db.ForeignKey('embarques.id', ondelete='SET NULL'), nullable=True)

    # Campos Odoo - Rastreabilidade de Entradas de Compras
    odoo_picking_id = db.Column(db.String(50), nullable=True, index=True)  # ID do stock.picking no Odoo
    odoo_move_id = db.Column(db.String(50), nullable=True, index=True)     # ID do stock.move no Odoo
    purchase_line_id = db.Column(db.String(50), nullable=True)             # ID da linha de pedido Odoo (purchase.order.line)
    pedido_compras_id = db.Column(db.Integer, db.ForeignKey('pedido_compras.id', ondelete='SET NULL'), nullable=True)  # FK para PedidoCompras local

    # Campos de Rastreabilidade - Recebimento Físico (Fase 4)
    # Vinculam a MovimentacaoEstoque com o processamento local de recebimento
    recebimento_fisico_id = db.Column(db.Integer, db.ForeignKey('recebimento_fisico.id', ondelete='SET NULL'), nullable=True, index=True)
    recebimento_lote_id = db.Column(db.Integer, db.ForeignKey('recebimento_lote.id', ondelete='SET NULL'), nullable=True, index=True)
    lote_nome = db.Column(db.String(100), nullable=True)        # Nome do lote (ex: LOTE-2024-001)
    data_validade = db.Column(db.Date, nullable=True)           # Data de validade do lote

    # Observações (mantido para compatibilidade)
    observacao = db.Column(db.Text, nullable=True)

    # Campos de Vinculação Produção/Consumo
    # PseudoID que agrupa todas as movimentações de uma operação (PROD_YYYYMMDD_HHMMSS_XXXX)
    operacao_producao_id = db.Column(db.String(50), nullable=True, index=True)
    # Tipo de origem: RAIZ, CONSUMO_DIRETO, PRODUCAO_AUTO, CONSUMO_AUTO
    tipo_origem_producao = db.Column(db.String(20), nullable=True)
    # Código do produto raiz (produto que iniciou a cascata de produção)
    cod_produto_raiz = db.Column(db.String(50), nullable=True, index=True)
    # FK para produção que gerou este consumo (auto-referência)
    producao_pai_id = db.Column(db.Integer, db.ForeignKey('movimentacao_estoque.id', ondelete='SET NULL'), nullable=True, index=True)

    # Campos para controle de Pallet em Terceiros
    tipo_destinatario = db.Column(db.String(20), nullable=True)  # CLIENTE ou TRANSPORTADORA
    cnpj_destinatario = db.Column(db.String(20), nullable=True, index=True)
    nome_destinatario = db.Column(db.String(255), nullable=True)
    embarque_item_id = db.Column(db.Integer, db.ForeignKey('embarque_itens.id', ondelete='SET NULL'), nullable=True)
    baixado = db.Column(db.Boolean, default=False, nullable=True)  # Se a saida de pallet foi baixada
    baixado_em = db.Column(db.DateTime, nullable=True)
    baixado_por = db.Column(db.String(100), nullable=True)
    movimento_baixado_id = db.Column(db.Integer, db.ForeignKey('movimentacao_estoque.id', ondelete='SET NULL'), nullable=True)

    # Saldo fiscal para controle de devolucoes (PALLET)
    # Quantidade ja devolvida/abatida da NF de remessa
    qtd_abatida = db.Column(db.Numeric(15, 3), default=0, nullable=True)

    # Campos para substituicao de NF (quando NF cliente consome parte de NF transportadora)
    # nf_remessa_origem: NF original da transportadora que foi substituida
    nf_remessa_origem = db.Column(db.String(20), nullable=True, index=True)
    # cnpj_responsavel: CNPJ de quem e responsavel pelo retorno (pode ser diferente do destinatario)
    # Em substituicoes, destinatario pode ser CLIENTE mas responsavel continua TRANSPORTADORA
    cnpj_responsavel = db.Column(db.String(20), nullable=True, index=True)
    nome_responsavel = db.Column(db.String(255), nullable=True)

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
        db.Index('idx_movimentacao_nf', 'numero_nf'),
        db.Index('idx_movimentacao_lote', 'separacao_lote_id'),
        db.Index('idx_movimentacao_pedido', 'num_pedido'),
        db.Index('idx_movimentacao_tipo_origem', 'tipo_origem'),
        db.Index('idx_movimentacao_status_nf', 'status_nf'),
        db.Index('idx_movimentacao_odoo_picking', 'odoo_picking_id'),
        db.Index('idx_movimentacao_odoo_move', 'odoo_move_id'),
        # Índices para pallet em terceiros
        db.Index('idx_movimentacao_cnpj_destinatario', 'cnpj_destinatario'),
        db.Index('idx_movimentacao_tipo_destinatario', 'tipo_destinatario'),
        db.Index('idx_movimentacao_baixado', 'baixado'),
        db.Index('idx_movimentacao_nf_remessa_origem', 'nf_remessa_origem'),
        db.Index('idx_movimentacao_cnpj_responsavel', 'cnpj_responsavel'),
        # Índices para rastreabilidade de Recebimento Físico
        db.Index('idx_movimentacao_recebimento_fisico', 'recebimento_fisico_id'),
        db.Index('idx_movimentacao_recebimento_lote', 'recebimento_lote_id'),
    )

    def __repr__(self):
        return f'<MovimentacaoEstoque {self.cod_produto} - {self.tipo_movimentacao} - {self.qtd_movimentacao}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'separacao_lote_id': self.separacao_lote_id,
            'numero_nf': self.numero_nf,
            'num_pedido': self.num_pedido,
            'tipo_origem': self.tipo_origem,
            'status_nf': self.status_nf,
            'codigo_embarque': self.codigo_embarque,
            'data_movimentacao': self.data_movimentacao.strftime('%d/%m/%Y') if self.data_movimentacao else None,
            'tipo_movimentacao': self.tipo_movimentacao,
            'local_movimentacao': self.local_movimentacao,
            'qtd_movimentacao': float(self.qtd_movimentacao) if self.qtd_movimentacao else 0,
            'observacao': self.observacao,
            # Campos de vinculação produção/consumo
            'operacao_producao_id': self.operacao_producao_id,
            'tipo_origem_producao': self.tipo_origem_producao,
            'cod_produto_raiz': self.cod_produto_raiz,
            'producao_pai_id': self.producao_pai_id,
            # Campos de pallet em terceiros
            'tipo_destinatario': self.tipo_destinatario,
            'cnpj_destinatario': self.cnpj_destinatario,
            'nome_destinatario': self.nome_destinatario,
            'embarque_item_id': self.embarque_item_id,
            'baixado': self.baixado,
            'baixado_em': self.baixado_em.strftime('%d/%m/%Y %H:%M') if self.baixado_em else None,
            'baixado_por': self.baixado_por,
            'movimento_baixado_id': self.movimento_baixado_id,
            'qtd_abatida': float(self.qtd_abatida) if self.qtd_abatida else 0,
            # Campos de substituicao
            'nf_remessa_origem': self.nf_remessa_origem,
            'cnpj_responsavel': self.cnpj_responsavel,
            'nome_responsavel': self.nome_responsavel,
            # Campos de rastreabilidade Recebimento Físico
            'recebimento_fisico_id': self.recebimento_fisico_id,
            'recebimento_lote_id': self.recebimento_lote_id,
            'lote_nome': self.lote_nome,
            'data_validade': self.data_validade.strftime('%d/%m/%Y') if self.data_validade else None
        }

    # ========== MÉTODOS PARA PALLET EM TERCEIROS ==========

    @classmethod
    def saldo_pallet_por_destinatario(cls, cnpj_destinatario):
        """Calcula o saldo de pallets em um destinatario (SAIDA e REMESSA nao baixadas)"""
        from sqlalchemy import func
        return db.session.query(func.coalesce(func.sum(cls.qtd_movimentacao), 0)).filter(
            cls.cnpj_destinatario == cnpj_destinatario,
            cls.local_movimentacao == 'PALLET',
            cls.tipo_movimentacao.in_(['SAIDA', 'REMESSA']),  # Inclui REMESSA
            cls.baixado == False,
            cls.ativo == True
        ).scalar() or 0

    @classmethod
    def listar_saldos_pallet_pendentes(cls):
        """Lista todos os destinatarios com saldo de pallet pendente (SAIDA e REMESSA)"""
        from sqlalchemy import func
        return db.session.query(
            cls.tipo_destinatario,
            cls.cnpj_destinatario,
            cls.nome_destinatario,
            func.sum(cls.qtd_movimentacao).label('saldo')
        ).filter(
            cls.local_movimentacao == 'PALLET',
            cls.tipo_movimentacao.in_(['SAIDA', 'REMESSA']),  # Inclui REMESSA
            cls.baixado == False,
            cls.ativo == True
        ).group_by(
            cls.tipo_destinatario,
            cls.cnpj_destinatario,
            cls.nome_destinatario
        ).having(func.sum(cls.qtd_movimentacao) > 0).order_by(
            func.sum(cls.qtd_movimentacao).desc()
        ).all()

    @classmethod
    def listar_movimentos_pallet(cls, tipo_movimento=None, baixado=None, tipo_destinatario=None):
        """Lista movimentos de pallet com filtros"""
        query = cls.query.filter(
            cls.local_movimentacao == 'PALLET',
            cls.ativo == True
        )
        if tipo_movimento:
            query = query.filter(cls.tipo_movimentacao == tipo_movimento)
        if baixado is not None:
            query = query.filter(cls.baixado == baixado)
        if tipo_destinatario:
            query = query.filter(cls.tipo_destinatario == tipo_destinatario)
        return query.order_by(cls.criado_em.desc())


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
        SEMPRE inclui o próprio código, mesmo sem unificação
        """
        try:
            # Garantir que sempre inclui o próprio código (como string)
            codigo_original = str(codigo_produto)
            codigos_relacionados = set([codigo_original])
            
            # Tentar converter para int para busca na tabela de unificação
            try:
                codigo_int = int(codigo_produto)
                
                # Busca códigos que apontam para este (este é destino)
                origens = cls.query.filter_by(
                    codigo_destino=codigo_int,
                    ativo=True
                ).all()
                
                for origem in origens:
                    codigos_relacionados.add(str(origem.codigo_origem))
                
                # Busca para onde este código aponta (este é origem)
                destino = cls.query.filter_by(
                    codigo_origem=codigo_int,
                    ativo=True
                ).first()
                
                if destino:
                    codigos_relacionados.add(str(destino.codigo_destino))
                    # Busca outros códigos que também apontam para o mesmo destino
                    outros_origens = cls.query.filter_by(
                        codigo_destino=destino.codigo_destino,
                        ativo=True
                    ).all()
                    for outro in outros_origens:
                        codigos_relacionados.add(str(outro.codigo_origem))
                        
            except (ValueError, TypeError):
                # Se não conseguir converter para int, ignora unificação mas mantém o código original
                pass
            
            return list(codigos_relacionados)

        except Exception:
            # Em caso de qualquer erro, sempre retorna pelo menos o código original
            return [str(codigo_produto)]

    @classmethod
    def get_todos_codigos_relacionados_batch(cls, codigos_produtos):
        """
        Versão BATCH otimizada de get_todos_codigos_relacionados.
        Busca TODOS os códigos relacionados em UMA única query.

        SEGURANÇA: Dados frescos do banco, não cache.

        Args:
            codigos_produtos: Lista de códigos de produtos

        Returns:
            Dict[cod_produto] -> [lista de códigos relacionados]

        Performance esperada: < 50ms para 200 produtos (vs ~400ms com N queries)
        """
        from typing import Dict, List

        # Inicializar resultado com cada código apontando para si mesmo
        resultado: Dict[str, List[str]] = {
            str(cod): [str(cod)] for cod in codigos_produtos
        }

        try:
            # Converter para int para busca no banco
            codigos_int = []
            cod_to_str = {}
            for cod in codigos_produtos:
                try:
                    cod_int = int(cod)
                    codigos_int.append(cod_int)
                    cod_to_str[cod_int] = str(cod)
                except (ValueError, TypeError):
                    pass

            if not codigos_int:
                return resultado

            # UMA ÚNICA QUERY para buscar TODAS as unificações relevantes
            unificacoes = cls.query.filter(
                cls.ativo == True,
                db.or_(
                    cls.codigo_origem.in_(codigos_int),
                    cls.codigo_destino.in_(codigos_int)
                )
            ).all()

            # Construir grafo de relacionamentos bidirecionais
            for unif in unificacoes:
                origem_str = str(unif.codigo_origem)
                destino_str = str(unif.codigo_destino)

                # Se origem está na lista de produtos, adicionar destino
                if origem_str in resultado:
                    if destino_str not in resultado[origem_str]:
                        resultado[origem_str].append(destino_str)

                # Se destino está na lista de produtos, adicionar origem
                if destino_str in resultado:
                    if origem_str not in resultado[destino_str]:
                        resultado[destino_str].append(origem_str)

                # Buscar outros códigos que apontam para o mesmo destino
                # (já incluídos na query acima por causa do OR)

            # Segunda passada: garantir transitividade (A->B, C->B => A,B,C são relacionados)
            # Construir grupos conectados
            destinos_para_origens = {}  # destino -> [origens]
            for unif in unificacoes:
                dest = str(unif.codigo_destino)
                orig = str(unif.codigo_origem)
                if dest not in destinos_para_origens:
                    destinos_para_origens[dest] = set([dest])
                destinos_para_origens[dest].add(orig)

            # Para cada produto na lista, verificar se é origem ou destino
            for cod_original in resultado.keys():
                try:
                    cod_int = int(cod_original)
                    # Verificar se este código é origem de alguma unificação
                    for unif in unificacoes:
                        if unif.codigo_origem == cod_int:
                            # Adicionar todos os outros que apontam para o mesmo destino
                            dest = str(unif.codigo_destino)
                            if dest in destinos_para_origens:
                                for relacionado in destinos_para_origens[dest]:
                                    if relacionado not in resultado[cod_original]:
                                        resultado[cod_original].append(relacionado)
                        elif unif.codigo_destino == cod_int:
                            # Este código é destino, adicionar todos que apontam para ele
                            if cod_original in destinos_para_origens:
                                for relacionado in destinos_para_origens[cod_original]:
                                    if relacionado not in resultado[cod_original]:
                                        resultado[cod_original].append(relacionado)
                except (ValueError, TypeError):
                    pass

            return resultado

        except Exception as e:
            # Em caso de erro, retornar cada código apenas com ele mesmo
            import logging
            logging.getLogger(__name__).error(f"Erro em get_todos_codigos_relacionados_batch: {e}")
            return resultado

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
