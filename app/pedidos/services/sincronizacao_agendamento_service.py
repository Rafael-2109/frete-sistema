"""
Serviço de Sincronização Bidirecional de Agendamentos
=====================================================

Sincroniza dados de agendamento entre:
- Separacao
- EmbarqueItem
- EntregaMonitorada
- AgendamentoEntrega (histórico)

Autor: Claude Code
Data: 2025-01-06
"""

from app import db
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SincronizadorAgendamentoService:
    """
    Serviço para sincronizar agendamentos entre todas as tabelas relacionadas
    """

    def __init__(self, usuario='Sistema'):
        self.usuario = usuario
        self.log_operacoes = []

    def sincronizar_agendamento(self, dados_agendamento, identificador):
        """
        Sincroniza agendamento entre TODAS as tabelas

        Args:
            dados_agendamento (dict): {
                'agendamento': date,
                'protocolo': str,
                'agendamento_confirmado': bool,
                'numero_nf': str (optional),
                'nf_cd': bool (optional)
            }
            identificador (dict): {
                'separacao_lote_id': str (optional),
                'numero_nf': str (optional)
            }

        Returns:
            dict: {
                'success': bool,
                'tabelas_atualizadas': list,
                'detalhes': dict,
                'log': list
            }
        """
        try:
            tabelas_atualizadas = []
            detalhes = {}

            # Extrair dados
            agendamento = dados_agendamento.get('agendamento')
            protocolo = dados_agendamento.get('protocolo')
            agendamento_confirmado = dados_agendamento.get('agendamento_confirmado', False)
            numero_nf = dados_agendamento.get('numero_nf')
            nf_cd = dados_agendamento.get('nf_cd', False)

            separacao_lote_id = identificador.get('separacao_lote_id')
            numero_nf_identificador = identificador.get('numero_nf')

            # Usar NF do identificador se não vier em dados
            if not numero_nf:
                numero_nf = numero_nf_identificador

            # 1. ATUALIZAR SEPARACAO
            separacoes_atualizadas = self._atualizar_separacao(
                separacao_lote_id=separacao_lote_id,
                agendamento=agendamento,
                protocolo=protocolo,
                agendamento_confirmado=agendamento_confirmado,
                numero_nf=numero_nf,
                nf_cd=nf_cd
            )
            if separacoes_atualizadas > 0:
                tabelas_atualizadas.append('Separacao')
                detalhes['separacao'] = separacoes_atualizadas

            # 2. ATUALIZAR EMBARQUEITEM
            embarques_atualizados = self._atualizar_embarque_item(
                separacao_lote_id=separacao_lote_id,
                numero_nf=numero_nf,
                agendamento=agendamento,
                protocolo=protocolo,
                agendamento_confirmado=agendamento_confirmado
            )
            if embarques_atualizados > 0:
                tabelas_atualizadas.append('EmbarqueItem')
                detalhes['embarque_item'] = embarques_atualizados

            # 3. ATUALIZAR ENTREGAMONITORADA + CRIAR AGENDAMENTOENTREGA
            entrega_monitorada = self._atualizar_entrega_monitorada(
                separacao_lote_id=separacao_lote_id,
                numero_nf=numero_nf,
                agendamento=agendamento,
                protocolo=protocolo,
                agendamento_confirmado=agendamento_confirmado,
                nf_cd=nf_cd
            )
            if entrega_monitorada:
                tabelas_atualizadas.append('EntregaMonitorada')
                detalhes['entrega_monitorada'] = entrega_monitorada.id

                # Criar AgendamentoEntrega se houver agendamento
                if agendamento:
                    agendamento_entrega_criado = self._criar_agendamento_entrega(
                        entrega_id=entrega_monitorada.id,
                        data_agendada=agendamento,
                        protocolo=protocolo,
                        confirmado=agendamento_confirmado
                    )
                    if agendamento_entrega_criado:
                        tabelas_atualizadas.append('AgendamentoEntrega')
                        detalhes['agendamento_entrega'] = agendamento_entrega_criado.id

            # Commit final
            db.session.commit()

            logger.info(f"[SINCRONIZAÇÃO] Sucesso | Tabelas: {', '.join(tabelas_atualizadas)} | Lote: {separacao_lote_id} | NF: {numero_nf}")

            return {
                'success': True,
                'tabelas_atualizadas': tabelas_atualizadas,
                'detalhes': detalhes,
                'log': self.log_operacoes
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"[SINCRONIZAÇÃO] Erro: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'log': self.log_operacoes
            }

    def _atualizar_separacao(self, separacao_lote_id, agendamento, protocolo, agendamento_confirmado, numero_nf, nf_cd):
        """Atualiza registros de Separacao"""
        if not separacao_lote_id:
            return 0

        update_data = {}
        if agendamento is not None:
            update_data['agendamento'] = agendamento
        if protocolo is not None:
            update_data['protocolo'] = protocolo
        if agendamento_confirmado is not None:
            update_data['agendamento_confirmado'] = agendamento_confirmado
        if numero_nf is not None:
            update_data['numero_nf'] = numero_nf
        if nf_cd is not None:
            update_data['nf_cd'] = nf_cd

        if not update_data:
            return 0

        count = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).update(update_data)

        self.log_operacoes.append(f"Separacao: {count} registros atualizados")
        return count

    def _atualizar_embarque_item(self, separacao_lote_id, numero_nf, agendamento, protocolo, agendamento_confirmado):
        """Atualiza registros de EmbarqueItem"""
        if not separacao_lote_id and not numero_nf:
            return 0

        # Buscar por separacao_lote_id (prioridade)
        query = EmbarqueItem.query
        if separacao_lote_id:
            query = query.filter_by(separacao_lote_id=separacao_lote_id)
        elif numero_nf:
            query = query.filter_by(nota_fiscal=numero_nf)

        update_data = {}
        if agendamento is not None:
            # EmbarqueItem usa data_agenda (String DD/MM/YYYY)
            update_data['data_agenda'] = agendamento.strftime('%d/%m/%Y') if agendamento else None
        if protocolo is not None:
            update_data['protocolo_agendamento'] = protocolo
        if agendamento_confirmado is not None:
            update_data['agendamento_confirmado'] = agendamento_confirmado

        if not update_data:
            return 0

        count = query.update(update_data)
        self.log_operacoes.append(f"EmbarqueItem: {count} registros atualizados")
        return count

    def _atualizar_entrega_monitorada(self, separacao_lote_id, numero_nf, agendamento, protocolo, agendamento_confirmado, nf_cd):
        """Atualiza registro de EntregaMonitorada"""
        if not separacao_lote_id and not numero_nf:
            return None

        # Buscar EntregaMonitorada
        entrega = None
        if separacao_lote_id:
            entrega = EntregaMonitorada.query.filter_by(
                separacao_lote_id=separacao_lote_id
            ).first()

        if not entrega and numero_nf:
            entrega = EntregaMonitorada.query.filter_by(
                numero_nf=numero_nf
            ).first()

        if not entrega:
            self.log_operacoes.append("EntregaMonitorada: Não encontrada")
            return None

        # Atualizar campos
        if agendamento is not None:
            entrega.data_agenda = agendamento
        if nf_cd is not None:
            entrega.nf_cd = nf_cd

        self.log_operacoes.append(f"EntregaMonitorada: ID {entrega.id} atualizado")
        return entrega

    def _criar_agendamento_entrega(self, entrega_id, data_agendada, protocolo, confirmado):
        """Cria registro em AgendamentoEntrega (histórico)"""
        try:
            status = 'confirmado' if confirmado else 'aguardando'

            agendamento = AgendamentoEntrega(
                entrega_id=entrega_id,
                data_agendada=data_agendada,
                protocolo_agendamento=protocolo,
                status=status,
                autor=self.usuario,
                motivo='Sincronização automática',
                criado_em=datetime.utcnow()
            )

            if confirmado:
                agendamento.confirmado_por = self.usuario
                agendamento.confirmado_em = datetime.utcnow()

            db.session.add(agendamento)
            self.log_operacoes.append(f"AgendamentoEntrega: Criado (status={status})")
            return agendamento

        except Exception as e:
            logger.warning(f"Não foi possível criar AgendamentoEntrega: {e}")
            return None
