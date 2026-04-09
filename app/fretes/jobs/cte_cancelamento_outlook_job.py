"""
CteCancelamentoOutlookJob — Processa XMLs de cancelamento de CTe do Outlook 365
==================================================================================

Job executado periodicamente pelo scheduler principal
(`app/scheduler/sincronizacao_incremental_definitiva.py`) como novo step
apos o step 7 (Importacao de CTes do Odoo).

Fluxo por execucao:
1. GraphClient autentica via MSAL client_credentials
2. Resolve folder_id da pasta configurada
3. Lista emails nao lidos (ate MAX_EMAILS_POR_RUN)
4. Para cada email:
   a) Lista anexos
   b) Filtra *.xml
   c) Para cada XML:
      - Parser detecta tipo (procEventoCTe | cteProc | invalido)
      - Se procEventoCTe: chama CancelamentoCteService.cancelar_por_chave()
      - Se cteProc: loga e ignora (nao e cancelamento)
      - Se invalido: cria pendencia ERRO
   d) SO marca email como lido se TODOS os XMLs foram processados com
      pendencia criada (sucesso ou erro capturado) — evita perda de dados

Configuracao (env vars):
- CTE_CANCELAMENTO_ENABLED: feature flag geral (default: false)
- GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET: credenciais Graph API
- GRAPH_MAILBOX_UPN: UPN da caixa (ex: fiscal@empresa.com)
- GRAPH_FOLDER_NAME: nome exato da pasta (ex: "CTe Cancelados")
- CTE_CANCELAMENTO_MAX_EMAILS: limite por run (default: 100)

Data: 2026-04-09
Referencia: .claude/plans/temporal-exploring-biscuit.md
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Defaults de configuracao
DEFAULT_MAX_EMAILS = 100


class CteCancelamentoOutlookJob:
    """
    Job de processamento de XMLs de cancelamento via Outlook 365.

    Instanciado FORA do app_context (igual aos outros services do scheduler)
    para evitar problemas de SSL. O app_context e aberto DENTRO do `executar()`.

    Reuse entre runs e seguro (instancia unica no scheduler).
    """

    def __init__(self):
        # Lazy: so cria na primeira chamada real, assim a instanciacao FORA
        # do contexto nao falha se libs nao estiverem disponiveis.
        self._graph = None
        self._parser = None
        self._cte_service = None
        self._cancelamento_service = None

    # ------------------------------------------------------------------
    # Lazy getters (app_context-safe)
    # ------------------------------------------------------------------

    def _get_graph(self):
        if self._graph is None:
            from app.utils.graph_client import GraphClient
            self._graph = GraphClient()
        return self._graph

    def _get_parser(self):
        if self._parser is None:
            from app.utils.cte_evento_parser import CteEventoParser
            self._parser = CteEventoParser()
        return self._parser

    def _get_cte_service(self):
        if self._cte_service is None:
            from app.odoo.services.cte_service import CteService
            self._cte_service = CteService()
        return self._cte_service

    def _get_cancelamento_service(self):
        if self._cancelamento_service is None:
            from app.fretes.services.cancelamento_cte_service import (
                CancelamentoCteService,
            )
            self._cancelamento_service = CancelamentoCteService(
                cte_service=self._get_cte_service()
            )
        return self._cancelamento_service

    # ------------------------------------------------------------------
    # API principal
    # ------------------------------------------------------------------

    def executar(self) -> Dict[str, Any]:
        """
        Executa uma iteracao do job.

        Returns:
            Dict com estatisticas:
                - sucesso: bool (False so em erro fatal — ex: auth falhou)
                - emails_lidos: int
                - xmls_processados: int
                - cancelados_ok: int
                - pendencias: int
                - erros: int
                - mensagem: str (resumo)
        """
        stats = {
            'sucesso': True,
            'emails_lidos': 0,
            'xmls_processados': 0,
            'xmls_ignorados': 0,  # cteProc (CTes originais, nao cancelamento)
            'cancelados_ok': 0,
            'pendencias': 0,
            'erros': 0,
            'mensagem': '',
        }

        # Validar config
        upn = os.environ.get('GRAPH_MAILBOX_UPN', '').strip()
        folder_name = os.environ.get('GRAPH_FOLDER_NAME', '').strip()
        max_emails = int(
            os.environ.get('CTE_CANCELAMENTO_MAX_EMAILS', str(DEFAULT_MAX_EMAILS))
        )

        if not upn or not folder_name:
            stats['sucesso'] = False
            stats['mensagem'] = (
                "Config incompleta: GRAPH_MAILBOX_UPN ou GRAPH_FOLDER_NAME "
                "nao configurados"
            )
            logger.warning(f"[CteCancelamentoJob] {stats['mensagem']}")
            return stats

        # Autenticar e listar emails
        try:
            graph = self._get_graph()
            folder_id = graph.obter_pasta_id(upn=upn, folder_name=folder_name)
            logger.info(
                f"[CteCancelamentoJob] Pasta '{folder_name}' resolvida: "
                f"folder_id={folder_id}"
            )

            mensagens = graph.listar_emails_pasta(
                upn=upn,
                folder_id=folder_id,
                unread_only=True,
                top=max_emails,
            )
        except Exception as e:
            stats['sucesso'] = False
            stats['mensagem'] = f"Erro ao listar emails: {e}"
            logger.exception(f"[CteCancelamentoJob] {stats['mensagem']}")
            return stats

        logger.info(
            f"[CteCancelamentoJob] {len(mensagens)} email(s) nao lido(s) "
            f"encontrado(s) em '{folder_name}'"
        )

        # Processar cada email
        for mensagem in mensagens:
            resultado_email = self._processar_email(upn, mensagem)
            stats['emails_lidos'] += 1
            stats['xmls_processados'] += resultado_email['xmls_processados']
            stats['xmls_ignorados'] += resultado_email['xmls_ignorados']
            stats['cancelados_ok'] += resultado_email['cancelados_ok']
            stats['pendencias'] += resultado_email['pendencias']
            stats['erros'] += resultado_email['erros']

        stats['mensagem'] = (
            f"{stats['emails_lidos']} email(s) / "
            f"{stats['xmls_processados']} XML(s) processado(s) / "
            f"{stats['xmls_ignorados']} cteProc(s) ignorado(s) / "
            f"{stats['cancelados_ok']} OK / "
            f"{stats['pendencias']} pendencia(s) / "
            f"{stats['erros']} erro(s)"
        )
        logger.info(f"[CteCancelamentoJob] Concluido: {stats['mensagem']}")
        return stats

    # ------------------------------------------------------------------
    # Processamento de email individual
    # ------------------------------------------------------------------

    def _processar_email(
        self,
        upn: str,
        mensagem: Dict[str, Any],
    ) -> Dict[str, int]:
        """
        Processa um email: baixa anexos XML, roteia para o service de cancelamento.

        SO marca o email como lido se TODOS os XMLs forem processados com
        resultado registrado (pendencia criada, seja sucesso ou erro capturado).

        Returns:
            Dict com: xmls_processados, xmls_ignorados, cancelados_ok, pendencias, erros
        """
        resultado = {
            'xmls_processados': 0,
            'xmls_ignorados': 0,  # cteProc (CTes normais, nao cancelamento)
            'cancelados_ok': 0,
            'pendencias': 0,
            'erros': 0,
        }

        message_id = mensagem.get('id')
        subject = mensagem.get('subject', '(sem assunto)')
        has_attachments = mensagem.get('hasAttachments', False)

        if not has_attachments:
            # Email sem anexos — NAO e da alcada do job.
            # NAO marcar como lido: pode ser notificacao operacional que a
            # pessoa dona da caixa precisa ler (ex: "Ocorrencia NF", "Transporte
            # Inicializado"). Apenas ignorar silenciosamente.
            logger.debug(
                f"[CteCancelamentoJob] Email sem anexos ignorado: '{subject[:50]}'"
            )
            return resultado

        # Listar anexos
        try:
            anexos = self._get_graph().listar_anexos(
                upn=upn, message_id=message_id
            )
        except Exception as e:
            logger.error(
                f"[CteCancelamentoJob] Erro ao listar anexos de '{subject[:50]}': {e}"
            )
            resultado['erros'] += 1
            return resultado  # NAO marca como lido — tentar de novo no proximo run

        # Filtrar XMLs
        xmls = [a for a in anexos if (a.get('name') or '').lower().endswith('.xml')]
        if not xmls:
            # Email tem anexos mas nao e XML (ex: so PDF DACTe). NAO e da
            # alcada do job. NAO marcar como lido — respeitar o fluxo humano.
            logger.debug(
                f"[CteCancelamentoJob] Email sem anexos XML ignorado: "
                f"'{subject[:50]}' ({len(anexos)} anexo(s) de outros tipos)"
            )
            return resultado

        todos_processados = True

        for anexo in xmls:
            att_id = anexo.get('id')
            att_name = anexo.get('name', '?')

            # Baixar conteudo
            try:
                xml_bytes = self._get_graph().baixar_anexo(
                    upn=upn,
                    message_id=message_id,
                    attachment_id=att_id,
                )
            except Exception as e:
                logger.error(
                    f"[CteCancelamentoJob] Erro ao baixar anexo {att_name}: {e}"
                )
                resultado['erros'] += 1
                todos_processados = False
                continue

            # Processar XML
            try:
                res_xml = self._processar_xml(
                    xml_bytes=xml_bytes,
                    email_message_id=message_id,
                    email_subject=subject,
                )
                if res_xml is None:
                    # cteProc — CTe normal (nao cancelamento). Ignorar silenciosamente.
                    resultado['xmls_ignorados'] += 1
                else:
                    resultado['xmls_processados'] += 1
                    self._contabilizar(res_xml, resultado)
            except Exception:
                logger.exception(
                    f"[CteCancelamentoJob] Erro ao processar XML {att_name}"
                )
                resultado['erros'] += 1
                todos_processados = False

        # Se todos os XMLs foram processados, marcar como lido
        if todos_processados:
            try:
                self._get_graph().marcar_como_lido(
                    upn=upn, message_id=message_id
                )
                logger.info(
                    f"[CteCancelamentoJob] Email '{subject}' marcado como lido"
                )
            except Exception as e:
                logger.warning(
                    f"[CteCancelamentoJob] Falha ao marcar lido '{subject}': {e}"
                )

        return resultado

    def _processar_xml(
        self,
        xml_bytes: bytes,
        email_message_id: Optional[str],
        email_subject: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Roteia um XML para o parser e o service apropriados.

        Returns:
            - Dict (resultado de cancelar_por_chave) se for procEventoCTe
            - Dict (pendencia ERRO) se for XML invalido
            - None se for cteProc (CTe normal — ignorar silenciosamente)
        """
        parser = self._get_parser()
        tipo = parser.detectar_tipo(xml_bytes)

        if tipo == 'cteProc':
            # CTe normal — NAO e cancelamento. Ignorar silenciosamente.
            # A pasta recebe MUITOS cteProc por dia (todos os CTes que a empresa
            # recebe como tomadora). Criar pendencia para cada um poluiria a
            # tabela. Retornamos None para sinalizar "ignorar".
            info = parser.parse_cte(xml_bytes) or {}
            logger.debug(
                f"[CteCancelamentoJob] XML cteProc ignorado "
                f"(CTe normal, nao cancelamento): "
                f"chave={info.get('chave')}, numero={info.get('numero')}"
            )
            return None

        xml_raw = self._xml_to_str(xml_bytes)

        if tipo == 'invalido':
            return self._registrar_xml_invalido(
                xml_raw, email_message_id, email_subject,
                'XML nao reconhecido (nem procEventoCTe nem cteProc)',
            )

        # procEventoCTe
        info = parser.parse_evento(xml_bytes)
        if info is None:
            return self._registrar_xml_invalido(
                xml_raw, email_message_id, email_subject,
                'Falha ao parsear procEventoCTe',
            )

        chave = info.get('chave')
        if not chave:
            return self._registrar_xml_invalido(
                xml_raw, email_message_id, email_subject,
                'procEventoCTe sem chave extraida',
            )

        # Chama o service de cancelamento (gerenciamento completo)
        return self._get_cancelamento_service().cancelar_por_chave(
            chave_acesso=chave,
            evento_info=info,
            xml_raw=xml_raw,
            email_message_id=email_message_id,
            email_subject=email_subject,
        )

    def _registrar_xml_invalido(
        self,
        xml_raw: Optional[str],
        email_message_id: Optional[str],
        email_subject: Optional[str],
        mensagem: str,
    ) -> Dict[str, Any]:
        """
        Registra pendencia ERRO para XML que nao pode ser processado.
        Delega para o cancelamento_service que ja faz isso.
        """
        return self._get_cancelamento_service()._registrar_pendencia_erro(
            chave_acesso='(nao-extraida)',
            mensagem=mensagem,
            xml_raw=xml_raw,
            email_message_id=email_message_id,
            email_subject=email_subject,
        )

    @staticmethod
    def _contabilizar(resultado_xml: Dict[str, Any], acumulado: Dict[str, int]):
        """
        Atualiza contadores do resultado do email com base no status da pendencia.
        """
        from app.fretes.models import CtePendenciaCancelamento

        status = resultado_xml.get('status')
        if status == CtePendenciaCancelamento.STATUS_CANCELADO_OK:
            acumulado['cancelados_ok'] += 1
        elif status in CtePendenciaCancelamento.STATUS_PENDENTES:
            acumulado['pendencias'] += 1
        elif status == CtePendenciaCancelamento.STATUS_ERRO:
            acumulado['erros'] += 1

    @staticmethod
    def _xml_to_str(xml_bytes: bytes) -> Optional[str]:
        """Converte XML bytes em string para persistir em xml_raw."""
        if not xml_bytes:
            return None
        try:
            return xml_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return xml_bytes.decode('iso-8859-1', errors='replace')
            except Exception:
                return None
