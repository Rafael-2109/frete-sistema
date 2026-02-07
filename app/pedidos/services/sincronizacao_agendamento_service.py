"""
Serviço de Sincronização Bidirecional de Agendamentos - VERSÃO FINAL CORRIGIDA
===============================================================================

REGRAS DEFINITIVAS:
- **FONTES DA VERDADE** (propagam entre si e para receptores):
  * Separacao ↔ AgendamentoEntrega (último)

- **RECEPTORES** (apenas recebem):
  * EmbarqueItem
  * EntregaMonitorada

IMPORTANTE:
- AgendamentoEntrega é N:1 com EntregaMonitorada
- SEMPRE criar novo AgendamentoEntrega quando houver agendamento
- Usar último AgendamentoEntrega (por criado_em) como fonte da verdade

Campos Sincronizados:
- agendamento/data: Separacao.agendamento ↔ AgendamentoEntrega.data_agendada ↔ EmbarqueItem.data_agenda ↔ EntregaMonitorada.data_agenda
- protocolo: Separacao.protocolo ↔ AgendamentoEntrega.protocolo_agendamento ↔ EmbarqueItem.protocolo_agendamento
- confirmação: Separacao.agendamento_confirmado (bool) ↔ AgendamentoEntrega.status ('aguardando'/'confirmado') ↔ EmbarqueItem.agendamento_confirmado (bool)
- nf_cd: Separacao.nf_cd ↔ EntregaMonitorada.nf_cd (bidirecional)

Autor: Claude Code
Data: 2025-01-08 (VERSÃO FINAL)
"""

from app import db
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from datetime import datetime
from app.utils.timezone import agora_utc_naive
import logging

logger = logging.getLogger(__name__)


class SincronizadorAgendamentoService:
    """
    Serviço para sincronizar agendamentos entre TODAS as tabelas relacionadas

    LÓGICA FINAL:
    - Separacao e AgendamentoEntrega são fontes da verdade (propagam entre si)
    - EmbarqueItem e EntregaMonitorada são receptores
    - nf_cd sincroniza bidirecionalmente entre Separacao e EntregaMonitorada
    """

    def __init__(self, usuario='Sistema'):
        self.usuario = usuario
        self.log_operacoes = []

    def sincronizar_desde_separacao(self, separacao_lote_id, criar_agendamento=True):
        """
        🔴 FONTE DA VERDADE: Separacao

        Propaga dados de Separacao para:
        1. AgendamentoEntrega (cria novo registro se criar_agendamento=True)
        2. EmbarqueItem (receptor)
        3. EntregaMonitorada (receptor)

        Args:
            separacao_lote_id: ID do lote de separação
            criar_agendamento: Se True, cria novo AgendamentoEntrega

        Returns:
            dict: Resultado da sincronização
        """
        try:
            # Buscar Separacao (primeira ocorrência como referência)
            separacao = Separacao.query.filter_by(
                separacao_lote_id=separacao_lote_id
            ).first()

            if not separacao:
                return {
                    'success': False,
                    'error': f'Separacao com lote {separacao_lote_id} não encontrada'
                }

            # Extrair dados da fonte
            dados_agendamento = {
                'agendamento': separacao.agendamento,
                'protocolo': separacao.protocolo,
                'agendamento_confirmado': separacao.agendamento_confirmado or False,
                'numero_nf': separacao.numero_nf,
                'nf_cd': separacao.nf_cd or False
            }

            identificador = {
                'separacao_lote_id': separacao_lote_id,
                'numero_nf': separacao.numero_nf
            }

            tabelas_atualizadas = []
            detalhes = {}

            # 1. ATUALIZAR RECEPTORES (EmbarqueItem + EntregaMonitorada)
            resultado_receptores = self._propagar_para_receptores(dados_agendamento, identificador)
            if resultado_receptores['success']:
                tabelas_atualizadas.extend(resultado_receptores.get('tabelas_atualizadas', []))
                detalhes.update(resultado_receptores.get('detalhes', {}))

            # 2. CRIAR NOVO AGENDAMENTOENTREGA (se solicitado e houver agendamento)
            if criar_agendamento and dados_agendamento.get('agendamento'):
                # Buscar EntregaMonitorada para vincular
                entrega = EntregaMonitorada.query.filter_by(
                    separacao_lote_id=separacao_lote_id
                ).first()

                if not entrega and dados_agendamento.get('numero_nf'):
                    entrega = EntregaMonitorada.query.filter_by(
                        numero_nf=dados_agendamento['numero_nf']
                    ).first()

                if entrega:
                    novo_agendamento = self._criar_agendamento_entrega(
                        entrega_id=entrega.id,
                        data_agendada=dados_agendamento['agendamento'],
                        protocolo=dados_agendamento.get('protocolo'),
                        confirmado=dados_agendamento['agendamento_confirmado']
                    )
                    if novo_agendamento:
                        tabelas_atualizadas.append('AgendamentoEntrega')
                        detalhes['agendamento_entrega'] = novo_agendamento.id

            # Commit final
            db.session.commit()

            logger.info(f"[SINCRONIZAÇÃO DESDE Separacao] Sucesso | Lote: {separacao_lote_id} | Tabelas: {', '.join(tabelas_atualizadas)}")

            return {
                'success': True,
                'fonte': 'Separacao',
                'tabelas_atualizadas': tabelas_atualizadas,
                'detalhes': detalhes,
                'log': self.log_operacoes
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"[SINCRONIZAÇÃO SEPARACAO] Erro: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def sincronizar_desde_agendamento_entrega(self, entrega_id, agendamento_id=None):
        """
        🔴 FONTE DA VERDADE: AgendamentoEntrega (último)

        Propaga dados do último AgendamentoEntrega para:
        1. Separacao (outra fonte da verdade)
        2. EmbarqueItem (receptor)
        3. EntregaMonitorada (receptor)

        Args:
            entrega_id: ID da EntregaMonitorada
            agendamento_id: ID específico do AgendamentoEntrega (None = buscar último)

        Returns:
            dict: Resultado da sincronização
        """
        try:
            # Buscar EntregaMonitorada
            entrega = db.session.get(EntregaMonitorada,entrega_id) if entrega_id else None

            if not entrega:
                return {
                    'success': False,
                    'error': f'EntregaMonitorada {entrega_id} não encontrada'
                }

            # Buscar agendamento específico ou último
            if agendamento_id:
                agendamento = db.session.get(AgendamentoEntrega,agendamento_id) if agendamento_id else None
            else:
                if not entrega.agendamentos:
                    return {
                        'success': False,
                        'error': 'Nenhum agendamento encontrado para esta entrega'
                    }
                agendamento = max(entrega.agendamentos, key=lambda ag: ag.criado_em)

            if not agendamento:
                return {
                    'success': False,
                    'error': 'Agendamento não encontrado'
                }

            # Extrair dados da fonte
            dados_agendamento = {
                'agendamento': agendamento.data_agendada,
                'protocolo': agendamento.protocolo_agendamento,
                'agendamento_confirmado': (agendamento.status == 'confirmado'),
                'numero_nf': entrega.numero_nf,
                'nf_cd': entrega.nf_cd or False
            }

            identificador = {
                'separacao_lote_id': entrega.separacao_lote_id,
                'numero_nf': entrega.numero_nf
            }

            tabelas_atualizadas = []
            detalhes = {}

            # 1. ATUALIZAR SEPARACAO (outra fonte da verdade)
            separacoes_atualizadas = self._atualizar_separacao(
                separacao_lote_id=entrega.separacao_lote_id,
                agendamento=dados_agendamento['agendamento'],
                protocolo=dados_agendamento.get('protocolo'),
                agendamento_confirmado=dados_agendamento['agendamento_confirmado'],
                numero_nf=dados_agendamento['numero_nf'],
                nf_cd=dados_agendamento['nf_cd']
            )
            if separacoes_atualizadas > 0:
                tabelas_atualizadas.append('Separacao')
                detalhes['separacao'] = separacoes_atualizadas

            # 2. ATUALIZAR RECEPTORES (EmbarqueItem + EntregaMonitorada)
            resultado_receptores = self._propagar_para_receptores(dados_agendamento, identificador)
            if resultado_receptores['success']:
                tabelas_atualizadas.extend(resultado_receptores.get('tabelas_atualizadas', []))
                detalhes.update(resultado_receptores.get('detalhes', {}))

            # Commit final
            db.session.commit()

            logger.info(f"[SINCRONIZAÇÃO DESDE AgendamentoEntrega] Sucesso | Entrega: {entrega_id} | Tabelas: {', '.join(tabelas_atualizadas)}")

            return {
                'success': True,
                'fonte': 'AgendamentoEntrega',
                'tabelas_atualizadas': tabelas_atualizadas,
                'detalhes': detalhes,
                'log': self.log_operacoes
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"[SINCRONIZAÇÃO AGENDAMENTO_ENTREGA] Erro: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _propagar_para_receptores(self, dados_agendamento, identificador):
        """
        Propaga dados apenas para receptores (EmbarqueItem e EntregaMonitorada)
        """
        try:
            tabelas_atualizadas = []
            detalhes = {}

            agendamento = dados_agendamento.get('agendamento')
            protocolo = dados_agendamento.get('protocolo')
            agendamento_confirmado = dados_agendamento.get('agendamento_confirmado', False)
            numero_nf = dados_agendamento.get('numero_nf')
            nf_cd = dados_agendamento.get('nf_cd', False)
            separacao_lote_id = identificador.get('separacao_lote_id')

            # 1. ATUALIZAR EMBARQUEITEM
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

            # 2. ATUALIZAR ENTREGAMONITORADA
            entrega_monitorada = self._atualizar_entrega_monitorada(
                separacao_lote_id=separacao_lote_id,
                numero_nf=numero_nf,
                agendamento=agendamento,
                nf_cd=nf_cd
            )
            if entrega_monitorada:
                tabelas_atualizadas.append('EntregaMonitorada')
                detalhes['entrega_monitorada'] = entrega_monitorada.id

            return {
                'success': True,
                'tabelas_atualizadas': tabelas_atualizadas,
                'detalhes': detalhes
            }

        except Exception as e:
            raise e

    def _atualizar_separacao(self, separacao_lote_id, agendamento, protocolo, agendamento_confirmado, numero_nf, nf_cd=None):
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

    def _atualizar_entrega_monitorada(self, separacao_lote_id, numero_nf, agendamento, nf_cd=None):
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
        """Cria novo registro em AgendamentoEntrega (sempre criar novo, relação N:1)"""
        try:
            status = 'confirmado' if confirmado else 'aguardando'

            agendamento = AgendamentoEntrega(
                entrega_id=entrega_id,
                data_agendada=data_agendada,
                protocolo_agendamento=protocolo,
                status=status,
                autor=self.usuario,
                motivo='Sincronização automática',
                criado_em=agora_utc_naive()
            )

            if confirmado:
                agendamento.confirmado_por = self.usuario
                agendamento.confirmado_em = agora_utc_naive()

            db.session.add(agendamento)
            self.log_operacoes.append(f"AgendamentoEntrega: Criado (status={status})")
            return agendamento

        except Exception as e:
            logger.warning(f"Não foi possível criar AgendamentoEntrega: {e}")
            return None

    # ===== MÉTODO LEGADO (manter para compatibilidade) =====
    def sincronizar_agendamento(self, dados_agendamento, identificador):
        """
        MÉTODO LEGADO - Mantido para compatibilidade com código existente

        Detecta automaticamente o contexto e chama o método apropriado
        """
        # Detectar contexto
        separacao_lote_id = identificador.get('separacao_lote_id')

        # Por padrão, propaga como se fosse desde Separacao (fonte)
        if separacao_lote_id:
            return self.sincronizar_desde_separacao(separacao_lote_id, criar_agendamento=True)
        else:
            # Fallback: propagação simples para receptores
            return self._propagar_para_receptores(dados_agendamento, identificador)
