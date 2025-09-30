"""
Service para agregação e processamento de dados de clientes
"""
from sqlalchemy import distinct, func, or_
from app import db
from app.carteira.models import CarteiraPrincipal
from app.faturamento.models import FaturamentoProduto
from app.monitoramento.models import EntregaMonitorada
from app.cadastros_agendamento.models import ContatoAgendamento
from decimal import Decimal
from typing import List, Dict, Any, Optional


class ClienteService:

    @staticmethod
    def obter_todos_clientes_distintos() -> List[str]:
        """
        Retorna lista de CNPJs únicos de todos os clientes
        (faturados + carteira)
        """
        # Clientes da carteira
        clientes_carteira = db.session.query(
            distinct(CarteiraPrincipal.cnpj_cpf)
        ).filter(
            CarteiraPrincipal.cnpj_cpf.isnot(None),
            CarteiraPrincipal.cnpj_cpf != ''
        )

        # Clientes faturados
        clientes_faturados = db.session.query(
            distinct(FaturamentoProduto.cnpj_cliente)
        ).filter(
            FaturamentoProduto.cnpj_cliente.isnot(None),
            FaturamentoProduto.cnpj_cliente != '',
            FaturamentoProduto.status_nf != 'Cancelado'
        )

        # União e distinct
        todos_cnpjs = set()
        for cliente in clientes_carteira:
            if cliente[0]:
                todos_cnpjs.add(cliente[0])

        for cliente in clientes_faturados:
            if cliente[0]:
                todos_cnpjs.add(cliente[0])

        return sorted(list(todos_cnpjs))

    @staticmethod
    def obter_clientes_por_equipe(equipe_vendas: str) -> List[str]:
        """
        Retorna CNPJs de clientes de uma equipe específica
        """
        clientes = set()

        # Da carteira
        carteira_clientes = db.session.query(
            distinct(CarteiraPrincipal.cnpj_cpf)
        ).filter(
            CarteiraPrincipal.equipe_vendas == equipe_vendas,
            CarteiraPrincipal.cnpj_cpf.isnot(None)
        ).all()

        # Do faturamento
        faturamento_clientes = db.session.query(
            distinct(FaturamentoProduto.cnpj_cliente)
        ).filter(
            FaturamentoProduto.equipe_vendas == equipe_vendas,
            FaturamentoProduto.cnpj_cliente.isnot(None),
            FaturamentoProduto.status_nf != 'Cancelado'
        ).all()

        for c in carteira_clientes:
            if c[0]:
                clientes.add(c[0])

        for c in faturamento_clientes:
            if c[0]:
                clientes.add(c[0])

        return sorted(list(clientes))

    @staticmethod
    def obter_clientes_por_vendedor(vendedor: str, equipe_vendas: Optional[str] = None) -> List[str]:
        """
        Retorna CNPJs de clientes de um vendedor específico
        """
        clientes = set()

        # Da carteira
        carteira_clientes = db.session.query(
            distinct(CarteiraPrincipal.cnpj_cpf)
        ).filter(
            CarteiraPrincipal.vendedor == vendedor,
            CarteiraPrincipal.cnpj_cpf.isnot(None)
        )

        if equipe_vendas:
            carteira_clientes = carteira_clientes.filter(
                CarteiraPrincipal.equipe_vendas == equipe_vendas
            )

        carteira_clientes = carteira_clientes.all()

        # Do faturamento
        faturamento_clientes = db.session.query(
            distinct(FaturamentoProduto.cnpj_cliente)
        ).filter(
            FaturamentoProduto.vendedor == vendedor,
            FaturamentoProduto.cnpj_cliente.isnot(None),
            FaturamentoProduto.status_nf != 'Cancelado'
        )

        if equipe_vendas:
            faturamento_clientes = faturamento_clientes.filter(
                FaturamentoProduto.equipe_vendas == equipe_vendas
            )

        faturamento_clientes = faturamento_clientes.all()

        for c in carteira_clientes:
            if c[0]:
                clientes.add(c[0])

        for c in faturamento_clientes:
            if c[0]:
                clientes.add(c[0])

        return sorted(list(clientes))

    @staticmethod
    def obter_dados_cliente(cnpj: str, filtro_posicao: str = 'em_aberto') -> Dict[str, Any]:
        """
        Agrega todos os dados de um cliente específico

        Args:
            cnpj: CNPJ do cliente
            filtro_posicao: 'em_aberto' ou 'todos'

        Returns:
            Dicionário com dados agregados do cliente
        """
        dados = {
            'cnpj_cpf': cnpj,
            'raz_social': None,
            'raz_social_red': None,
            'estado': None,
            'municipio': None,
            'vendedor': None,
            'equipe_vendas': None,
            'forma_agendamento': None,
            'valor_em_aberto': Decimal('0.00'),
            'valor_total': Decimal('0.00'),
            'pedidos': [],
            'total_pedidos': 0
        }

        # Buscar dados básicos do cliente primeiro na CarteiraPrincipal
        cliente_carteira = db.session.query(
            CarteiraPrincipal.raz_social,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.estado,
            CarteiraPrincipal.municipio,
            CarteiraPrincipal.vendedor,
            CarteiraPrincipal.equipe_vendas
        ).filter(
            CarteiraPrincipal.cnpj_cpf == cnpj
        ).order_by(
            CarteiraPrincipal.updated_at.desc(),
            CarteiraPrincipal.id.desc()
        ).first()

        if cliente_carteira:
            dados['raz_social'] = cliente_carteira.raz_social
            dados['raz_social_red'] = cliente_carteira.raz_social_red
            dados['estado'] = cliente_carteira.estado
            dados['municipio'] = cliente_carteira.municipio
            dados['vendedor'] = cliente_carteira.vendedor
            dados['equipe_vendas'] = cliente_carteira.equipe_vendas
        else:
            # Se não encontrou na carteira, buscar no faturamento
            cliente_faturamento = db.session.query(
                FaturamentoProduto.nome_cliente,
                FaturamentoProduto.estado,
                FaturamentoProduto.municipio,
                FaturamentoProduto.vendedor,
                FaturamentoProduto.equipe_vendas
            ).filter(
                FaturamentoProduto.cnpj_cliente == cnpj,
                FaturamentoProduto.status_nf != 'Cancelado'
            ).order_by(
                FaturamentoProduto.data_fatura.desc(),
                FaturamentoProduto.id.desc()
            ).first()

            if cliente_faturamento:
                dados['raz_social_red'] = cliente_faturamento.nome_cliente
                dados['estado'] = cliente_faturamento.estado
                dados['municipio'] = cliente_faturamento.municipio
                dados['vendedor'] = cliente_faturamento.vendedor
                dados['equipe_vendas'] = cliente_faturamento.equipe_vendas

        # Se não tem razão social, poderia buscar do Odoo futuramente
        # TODO: Implementar busca de cliente no Odoo quando a função estiver disponível
        # if not dados['raz_social']:
        #     # Futuramente implementar busca no Odoo via res.partner

        # Buscar forma de agendamento
        contato = db.session.query(
            ContatoAgendamento.forma
        ).filter(
            ContatoAgendamento.cnpj == cnpj
        ).first()

        if contato:
            dados['forma_agendamento'] = contato.forma

        # Buscar pedidos e calcular valores
        pedidos = ClienteService.obter_pedidos_cliente(cnpj, filtro_posicao)
        dados['pedidos'] = pedidos
        dados['total_pedidos'] = len(pedidos)

        # Calcular valores financeiros
        componentes_valor = ClienteService._calcular_componentes_valor(cnpj)

        valor_em_aberto = componentes_valor['saldo'] + componentes_valor['faturado_nao_entregue']
        valor_total = componentes_valor['saldo'] + componentes_valor['faturado_total']

        dados['valor_em_aberto'] = valor_em_aberto
        dados['valor_total'] = valor_total

        return dados

    @staticmethod
    def obter_pedidos_cliente(cnpj: str, filtro_posicao: str = 'em_aberto') -> List[str]:
        """
        Retorna lista de pedidos do cliente conforme filtro

        Args:
            cnpj: CNPJ do cliente
            filtro_posicao: 'em_aberto' ou 'todos'

        Returns:
            Lista de números de pedidos únicos
        """
        pedidos = set()

        if filtro_posicao == 'em_aberto':
            # Pedidos em carteira
            pedidos_carteira = db.session.query(
                distinct(CarteiraPrincipal.num_pedido)
            ).filter(
                CarteiraPrincipal.cnpj_cpf == cnpj,
                CarteiraPrincipal.num_pedido.isnot(None)
            ).all()

            for p in pedidos_carteira:
                if p[0]:
                    pedidos.add(p[0])

            # Pedidos faturados mas não entregues
            # Primeiro buscar NFs não entregues
            nfs_nao_entregues = db.session.query(
                distinct(EntregaMonitorada.numero_nf)
            ).filter(
                or_(
                    EntregaMonitorada.status_finalizacao != 'Entregue',
                    EntregaMonitorada.status_finalizacao.is_(None)
                )
            ).subquery()

            # Depois buscar pedidos dessas NFs
            pedidos_nao_entregues = db.session.query(
                distinct(FaturamentoProduto.origem)
            ).filter(
                FaturamentoProduto.cnpj_cliente == cnpj,
                FaturamentoProduto.numero_nf.in_(nfs_nao_entregues),
                FaturamentoProduto.origem.isnot(None),
                FaturamentoProduto.status_nf != 'Cancelado'
            ).all()

            for p in pedidos_nao_entregues:
                if p[0]:
                    pedidos.add(p[0])

        else:  # todos
            # Pedidos em carteira
            pedidos_carteira = db.session.query(
                distinct(CarteiraPrincipal.num_pedido)
            ).filter(
                CarteiraPrincipal.cnpj_cpf == cnpj,
                CarteiraPrincipal.num_pedido.isnot(None)
            ).all()

            for p in pedidos_carteira:
                if p[0]:
                    pedidos.add(p[0])

            # Todos os pedidos faturados
            pedidos_faturados = db.session.query(
                distinct(FaturamentoProduto.origem)
            ).filter(
                FaturamentoProduto.cnpj_cliente == cnpj,
                FaturamentoProduto.origem.isnot(None),
                FaturamentoProduto.status_nf != 'Cancelado'
            ).all()

            for p in pedidos_faturados:
                if p[0]:
                    pedidos.add(p[0])

        return sorted(list(pedidos))

    @staticmethod
    def calcular_valor_em_aberto(cnpj: str, filtro_posicao: str = 'em_aberto') -> Decimal:
        """
        Calcula o valor em aberto do cliente

        Args:
            cnpj: CNPJ do cliente
            filtro_posicao: 'em_aberto' ou 'todos'

        Returns:
            Valor total em aberto
        """
        componentes_valor = ClienteService._calcular_componentes_valor(cnpj)

        if filtro_posicao == 'todos':
            return componentes_valor['saldo'] + componentes_valor['faturado_total']

        return componentes_valor['saldo'] + componentes_valor['faturado_nao_entregue']

    @staticmethod
    def _calcular_componentes_valor(cnpj: str) -> Dict[str, Decimal]:
        """
        Calcula componentes financeiros utilizados nas visões de cliente.

        Retorna um dicionário contendo:
            - saldo: valor ainda em carteira
            - faturado_total: total já faturado (independente da entrega)
            - faturado_nao_entregue: total faturado ainda não entregue
        """
        componentes = {
            'saldo': Decimal('0.00'),
            'faturado_total': Decimal('0.00'),
            'faturado_nao_entregue': Decimal('0.00')
        }

        # Saldo em carteira
        saldos_carteira = db.session.query(
            func.sum(
                CarteiraPrincipal.qtd_saldo_produto_pedido *
                CarteiraPrincipal.preco_produto_pedido
            )
        ).filter(
            CarteiraPrincipal.cnpj_cpf == cnpj,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).scalar()

        if saldos_carteira:
            componentes['saldo'] = Decimal(str(saldos_carteira))

        # Total faturado (todas as NFs não canceladas)
        valores_faturados = db.session.query(
            func.sum(FaturamentoProduto.valor_produto_faturado)
        ).filter(
            FaturamentoProduto.cnpj_cliente == cnpj,
            FaturamentoProduto.status_nf != 'Cancelado'
        ).scalar()

        if valores_faturados:
            componentes['faturado_total'] = Decimal(str(valores_faturados))

        # Total faturado ainda não entregue
        valores_nao_entregues = db.session.query(
            func.sum(FaturamentoProduto.valor_produto_faturado)
        ).outerjoin(
            EntregaMonitorada,
            FaturamentoProduto.numero_nf == EntregaMonitorada.numero_nf
        ).filter(
            FaturamentoProduto.cnpj_cliente == cnpj,
            FaturamentoProduto.status_nf != 'Cancelado',
            or_(
                EntregaMonitorada.status_finalizacao != 'Entregue',
                EntregaMonitorada.status_finalizacao.is_(None)
            )
        ).scalar()

        if valores_nao_entregues:
            componentes['faturado_nao_entregue'] = Decimal(str(valores_nao_entregues))

        return componentes
