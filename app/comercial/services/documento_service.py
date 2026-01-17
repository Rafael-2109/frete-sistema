"""
Service para agregação e processamento de documentos de pedidos
================================================================

Este módulo fornece funções para agregar informações de documentos relacionados a pedidos,
incluindo Notas Fiscais, Separações e cálculo de Saldo.

Autor: Sistema de Fretes
Data: 2025-01-20
"""

from sqlalchemy import func
from app import db
from app.faturamento.models import FaturamentoProduto
from app.separacao.models import Separacao
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.embarques.models import EmbarqueItem, Embarque
from app.transportadoras.models import Transportadora
from app.carteira.models import CarteiraPrincipal
from app.cadastros_agendamento.models import ContatoAgendamento
from decimal import Decimal
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DocumentoService:
    """Service para processar e agregar dados de documentos de pedidos"""

    @staticmethod
    def obter_documentos_pedido(
        num_pedido: str,
        cnpj_cliente: str
    ) -> Dict[str, Any]:
        """
        Retorna todos os documentos relacionados a um pedido.

        Args:
            num_pedido (str): Número do pedido
            cnpj_cliente (str): CNPJ do cliente

        Returns:
            Dict contendo:
                - cliente_precisa_agendamento: Boolean indicando se cliente precisa de agendamento
                - documentos: Lista de documentos (NFs, Separações e Saldo)
                - totais: Valores totalizados
        """
        try:
            # Verificar se cliente precisa de agendamento
            cliente_precisa_agendamento = DocumentoService._cliente_precisa_agendamento(cnpj_cliente)

            # Buscar todos os tipos de documentos
            notas_fiscais = DocumentoService._obter_notas_fiscais_pedido(num_pedido)
            separacoes = DocumentoService._obter_separacoes_pedido(num_pedido)

            # Calcular valores totais
            valor_total_pedido = DocumentoService._calcular_valor_total_pedido(num_pedido)
            valor_total_faturado = DocumentoService._calcular_valor_total_faturado(notas_fiscais)
            valor_total_separacoes = DocumentoService._calcular_valor_total_separacoes(separacoes)

            # Calcular saldo
            saldo = DocumentoService._calcular_saldo(
                valor_total_pedido,
                valor_total_faturado,
                valor_total_separacoes
            )

            # Combinar todos os documentos
            documentos = []

            # Adicionar NFs (tipo 1)
            for nf in notas_fiscais:
                documentos.append({
                    'tipo': 'NF',
                    'tipo_ordem': 1,
                    **nf
                })

            # Adicionar Separações (tipo 2)
            for sep in separacoes:
                documentos.append({
                    'tipo': 'Separação',
                    'tipo_ordem': 2,
                    **sep
                })

            # Adicionar Saldo se existir (tipo 3)
            if saldo > 0:
                documentos.append({
                    'tipo': 'Saldo',
                    'tipo_ordem': 3,
                    'num_pedido': num_pedido,
                    'valor': float(saldo),
                    # Campos vazios para manter estrutura da tabela
                    'numero_nf': '-',
                    'data_faturamento': '-',
                    'data_embarque': '-',
                    'transportadora': '-',
                    'data_agendamento': '-',
                    'protocolo_agendamento': '-',
                    'status_agendamento': '-',
                    'data_entrega_prevista': '-',
                    'data_entrega_realizada': '-'
                })

            # Ordenar documentos: primeiro por tipo, depois por data
            documentos.sort(key=lambda x: (x['tipo_ordem'], x.get('data_faturamento', '9999-99-99')))

            return {
                'cliente_precisa_agendamento': cliente_precisa_agendamento,
                'documentos': documentos,
                'totais': {
                    'valor_total_pedido': float(valor_total_pedido),
                    'valor_total_faturado': float(valor_total_faturado),
                    'valor_total_separacoes': float(valor_total_separacoes),
                    'saldo': float(saldo)
                }
            }

        except Exception as e:
            logger.error(f"Erro ao obter documentos do pedido {num_pedido}: {e}")
            return {
                'cliente_precisa_agendamento': False,
                'documentos': [],
                'totais': {
                    'valor_total_pedido': 0,
                    'valor_total_faturado': 0,
                    'valor_total_separacoes': 0,
                    'saldo': 0
                }
            }

    @staticmethod
    def _cliente_precisa_agendamento(cnpj: str) -> bool:
        """
        Verifica se o cliente precisa de agendamento.

        Args:
            cnpj (str): CNPJ do cliente

        Returns:
            Boolean indicando se precisa de agendamento
        """
        try:
            contato = ContatoAgendamento.query.filter_by(cnpj=cnpj).first()

            if not contato:
                return False

            # Cliente precisa de agendamento se forma != 'SEM AGENDAMENTO'
            return contato.forma != 'SEM AGENDAMENTO'

        except Exception as e:
            logger.error(f"Erro ao verificar agendamento do cliente {cnpj}: {e}")
            return False

    @staticmethod
    def _obter_notas_fiscais_pedido(num_pedido: str) -> List[Dict[str, Any]]:
        """
        Obtém todas as notas fiscais de um pedido.

        Args:
            num_pedido (str): Número do pedido

        Returns:
            Lista de dicionários com informações das NFs
        """
        notas = []

        try:
            # Buscar NFs agrupadas por numero_nf
            nfs_query = db.session.query(
                FaturamentoProduto.numero_nf,
                func.min(FaturamentoProduto.data_fatura).label('data_fatura'),
                func.sum(FaturamentoProduto.valor_produto_faturado).label('valor_total')
            ).filter(
                FaturamentoProduto.origem == num_pedido,
                FaturamentoProduto.status_nf != 'Cancelado'
            ).group_by(
                FaturamentoProduto.numero_nf
            ).all()

            for nf in nfs_query:
                # Buscar dados de monitoramento e embarque
                entrega = EntregaMonitorada.query.filter_by(
                    numero_nf=nf.numero_nf
                ).first()

                # Buscar último agendamento se existir entrega
                ultimo_agendamento = None
                if entrega:
                    ultimo_agendamento = AgendamentoEntrega.query.filter_by(
                        entrega_id=entrega.id
                    ).order_by(
                        AgendamentoEntrega.criado_em.desc()
                    ).first()

                # Buscar dados de embarque via EmbarqueItem
                embarque_item = EmbarqueItem.query.filter_by(
                    nota_fiscal=nf.numero_nf,
                    status='ativo'
                ).first()

                embarque = None
                if embarque_item and embarque_item.status == 'ativo':
                    embarque = db.session.get(Embarque,embarque_item.embarque_id) if embarque_item.embarque_id else None

                # Montar dados da NF
                nf_data = {
                    'numero_nf': nf.numero_nf,
                    'num_pedido': num_pedido,
                    'data_faturamento': nf.data_fatura.strftime('%d/%m/%Y') if nf.data_fatura else '-',
                    'valor': float(nf.valor_total),

                    # Data de embarque (com fallback)
                    'data_embarque': '-',
                    'transportadora': '-',
                    'nome_transportadora': '-',
                    'cnpj_transportadora': '',

                    # Dados de agendamento
                    'data_agendamento': '-',
                    'protocolo_agendamento': '-',
                    'status_agendamento': '-',

                    # Entrega prevista e realizada
                    'data_entrega_prevista': '-',
                    'data_entrega_realizada': '-',
                    'status_finalizacao': entrega.status_finalizacao if entrega else '-'
                }

                # Preencher data de embarque
                if entrega and entrega.data_embarque:
                    nf_data['data_embarque'] = entrega.data_embarque.strftime('%d/%m/%Y')
                elif embarque and embarque.data_embarque:
                    nf_data['data_embarque'] = embarque.data_embarque.strftime('%d/%m/%Y')

                # Preencher transportadora
                nome_transportadora = '-'
                cnpj_transportadora = ''

                if embarque and getattr(embarque, 'transportadora', None):
                    nome_transportadora = embarque.transportadora.razao_social or '-'
                    cnpj_transportadora = embarque.transportadora.cnpj or ''
                elif embarque and embarque.transportadora_id:
                    transp = db.session.get(Transportadora,embarque.transportadora_id) if embarque.transportadora_id else None
                    if transp:
                        nome_transportadora = transp.razao_social or '-'
                        cnpj_transportadora = transp.cnpj or ''
                elif entrega and entrega.transportadora:
                    nome_transportadora = entrega.transportadora

                nf_data['transportadora'] = nome_transportadora
                nf_data['nome_transportadora'] = nome_transportadora
                nf_data['cnpj_transportadora'] = cnpj_transportadora

                # Preencher dados de agendamento
                if entrega:
                    # Data de agendamento (fallback para entrega prevista)
                    if entrega.data_agenda:
                        nf_data['data_agendamento'] = entrega.data_agenda.strftime('%d/%m/%Y')
                    elif entrega.data_entrega_prevista:
                        nf_data['data_agendamento'] = entrega.data_entrega_prevista.strftime('%d/%m/%Y')

                    # Protocolo e status do último agendamento
                    if ultimo_agendamento:
                        nf_data['protocolo_agendamento'] = ultimo_agendamento.protocolo_agendamento or '-'
                        nf_data['status_agendamento'] = ultimo_agendamento.status or 'aguardando'

                    # Data entrega realizada
                    if entrega.data_hora_entrega_realizada:
                        nf_data['data_entrega_realizada'] = entrega.data_hora_entrega_realizada.strftime('%d/%m/%Y %H:%M')

                    # Entrega prevista (sempre usar data_entrega_prevista para NFs)
                    if entrega.data_entrega_prevista:
                        nf_data['data_entrega_prevista'] = entrega.data_entrega_prevista.strftime('%d/%m/%Y')

                notas.append(nf_data)

        except Exception as e:
            logger.error(f"Erro ao obter notas fiscais do pedido {num_pedido}: {e}")

        return notas

    @staticmethod
    def _obter_separacoes_pedido(num_pedido: str) -> List[Dict[str, Any]]:
        """
        Obtém todas as separações não sincronizadas de um pedido.

        Args:
            num_pedido (str): Número do pedido

        Returns:
            Lista de dicionários com informações das separações
        """
        separacoes = []

        try:
            # Buscar separações agrupadas por separacao_lote_id
            seps_query = db.session.query(
                Separacao.separacao_lote_id,
                func.min(Separacao.expedicao).label('expedicao'),
                func.min(Separacao.agendamento).label('agendamento'),
                func.min(Separacao.protocolo).label('protocolo'),
                func.bool_and(Separacao.agendamento_confirmado).label('agendamento_confirmado'),
                func.sum(Separacao.valor_saldo).label('valor_total')
            ).filter(
                Separacao.num_pedido == num_pedido,
                Separacao.sincronizado_nf == False  # Apenas não sincronizadas
            ).group_by(
                Separacao.separacao_lote_id
            ).all()

            for sep in seps_query:
                # Tentar buscar transportadora via EmbarqueItem
                transportadora_nome = '-'
                transportadora_cnpj = ''
                embarque_item = EmbarqueItem.query.filter_by(
                    separacao_lote_id=sep.separacao_lote_id
                ).first()

                if embarque_item:
                    embarque = db.session.get(Embarque,embarque_item.embarque_id) if embarque_item.embarque_id else None
                    if embarque and getattr(embarque, 'transportadora', None):
                        transportadora_nome = embarque.transportadora.razao_social or '-'
                        transportadora_cnpj = embarque.transportadora.cnpj or ''
                    elif embarque and embarque.transportadora_id:
                        transp = db.session.get(Transportadora,embarque.transportadora_id) if embarque.transportadora_id else None
                        if transp:
                            transportadora_nome = transp.razao_social or '-'
                            transportadora_cnpj = transp.cnpj or ''

                # Montar dados da separação
                sep_data = {
                    'numero_nf': '-',  # Separação não tem NF
                    'data_faturamento': '-',  # Separação não foi faturada
                    'valor': float(sep.valor_total) if sep.valor_total else 0,

                    # Data de embarque (usar expedição com prefixo)
                    'data_embarque': f"Previsão: {sep.expedicao.strftime('%d/%m/%Y')}" if sep.expedicao else '-',
                    'transportadora': transportadora_nome,
                    'nome_transportadora': transportadora_nome,
                    'cnpj_transportadora': transportadora_cnpj,

                    # Dados de agendamento
                    'data_agendamento': sep.agendamento.strftime('%d/%m/%Y') if sep.agendamento else '-',
                    'protocolo_agendamento': sep.protocolo or '-',
                    'status_agendamento': 'confirmado' if sep.agendamento_confirmado else 'aguardando',

                    # Entrega (separação não tem entrega realizada)
                    'data_entrega_prevista': sep.agendamento.strftime('%d/%m/%Y') if sep.agendamento else '-',
                    'data_entrega_realizada': '-',

                    # Identificador do lote para futura expansão com produtos
                    'separacao_lote_id': sep.separacao_lote_id,
                    'num_pedido': num_pedido
                }

                separacoes.append(sep_data)

        except Exception as e:
            logger.error(f"Erro ao obter separações do pedido {num_pedido}: {e}")

        return separacoes

    @staticmethod
    def _calcular_valor_total_pedido(num_pedido: str) -> Decimal:
        """
        Calcula o valor total do pedido.

        Args:
            num_pedido (str): Número do pedido

        Returns:
            Valor total do pedido
        """
        try:
            # Primeiro verificar na CarteiraPrincipal
            valor_carteira = db.session.query(
                func.sum(
                    CarteiraPrincipal.preco_produto_pedido * CarteiraPrincipal.qtd_produto_pedido
                )
            ).filter(
                CarteiraPrincipal.num_pedido == num_pedido
            ).scalar()

            if valor_carteira:
                return Decimal(str(valor_carteira))

            # Se não estiver na carteira, buscar no faturamento
            valor_faturado = db.session.query(
                func.sum(FaturamentoProduto.valor_produto_faturado)
            ).filter(
                FaturamentoProduto.origem == num_pedido,
                FaturamentoProduto.status_nf != 'Cancelado'
            ).scalar()

            return Decimal(str(valor_faturado)) if valor_faturado else Decimal('0')

        except Exception as e:
            logger.error(f"Erro ao calcular valor total do pedido {num_pedido}: {e}")
            return Decimal('0')

    @staticmethod
    def _calcular_valor_total_faturado(notas_fiscais: List[Dict]) -> Decimal:
        """
        Calcula o valor total faturado das NFs.

        Args:
            notas_fiscais (List): Lista de notas fiscais

        Returns:
            Valor total faturado
        """
        total = Decimal('0')
        for nf in notas_fiscais:
            total += Decimal(str(nf['valor']))
        return total

    @staticmethod
    def _calcular_valor_total_separacoes(separacoes: List[Dict]) -> Decimal:
        """
        Calcula o valor total das separações.

        Args:
            separacoes (List): Lista de separações

        Returns:
            Valor total das separações
        """
        total = Decimal('0')
        for sep in separacoes:
            total += Decimal(str(sep['valor']))
        return total

    @staticmethod
    def _calcular_saldo(
        valor_total_pedido: Decimal,
        valor_total_faturado: Decimal,
        valor_total_separacoes: Decimal
    ) -> Decimal:
        """
        Calcula o saldo do pedido.

        Fórmula: (Total Pedido - Faturado) - Separações não sincronizadas

        Args:
            valor_total_pedido (Decimal): Valor total do pedido
            valor_total_faturado (Decimal): Valor total faturado
            valor_total_separacoes (Decimal): Valor total das separações

        Returns:
            Saldo do pedido
        """
        saldo = (valor_total_pedido - valor_total_faturado) - valor_total_separacoes
        return max(saldo, Decimal('0'))  # Não retornar valores negativos
