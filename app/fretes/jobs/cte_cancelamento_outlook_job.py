"""
CteCancelamentoOutlookJob — Processa XMLs de cancelamento de CTe do Outlook 365
==================================================================================

Job executado periodicamente pelo scheduler principal
(`app/scheduler/sincronizacao_incremental_definitiva.py`) como step 18.

Estrategia: scheduler roda a cada 30 min + janela temporal de 3h =
**over-loop natural de 6x** por email. Dedup por `email_message_id`
garante que cada email so e processado uma unica vez (primeira execucao
cria pendencia; as outras 5 fazem skip silencioso).

Vantagens do over-loop:
- Resiliencia: se uma execucao falha antes de criar pendencia, a proxima
  (em 30 min) pega o mesmo email.
- Nao depende de `isRead`: NAO marca emails como lidos (respeita o fluxo
  humano da pessoa dona da caixa).

Fluxo por execucao:
1. GraphClient autentica via MSAL client_credentials
2. Para CADA pasta configurada (lista em GRAPH_FOLDER_NAME separada por ';'):
   a) Resolve folder_id (suporta path hierarquico tipo 'Faturas/XML CTe\\'s')
   b) Lista emails com `receivedDateTime >= now - JANELA_HORAS`
3. Para cada email:
   a) DEDUP: se CtePendenciaCancelamento ja existe com esse message_id → skip
   b) Lista anexos
   c) Filtra *.xml
   d) Para cada XML:
      - Parser detecta tipo (procEventoCTe | cteProc | invalido)
      - Se procEventoCTe: chama CancelamentoCteService.cancelar_por_chave()
      - Se cteProc: ignora silenciosamente (CTe normal, volume alto ~50/dia)
      - Se invalido: cria pendencia ERRO
4. Retorna estatisticas para o scheduler

Configuracao (env vars):
- CTE_CANCELAMENTO_ENABLED: feature flag geral (default: false)
- CTE_CANCELAMENTO_JANELA_HORAS: janela de leitura em horas (default: 3)
- GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET: credenciais
- GRAPH_MAILBOX_UPN: UPN da caixa
- GRAPH_FOLDER_NAME: nome ou path de pasta, ou LISTA separada por ';'
  Exemplo: "Faturas;Faturas/XML CTe's"
- CTE_CANCELAMENTO_MAX_EMAILS: cap por pasta por run (default: 100)

Data: 2026-04-09
Referencia: .claude/plans/temporal-exploring-biscuit.md
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Defaults de configuracao
DEFAULT_MAX_EMAILS = 100
DEFAULT_JANELA_HORAS = 3
# Pequena gordura (em minutos) para cobrir drift de timestamps entre
# Graph API e nosso servidor + eventuais atrasos de entrega do Outlook.
JANELA_GORDURA_MINUTOS = 10


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
                - pastas_processadas: int
                - emails_encontrados: int (total na janela temporal, antes do dedup)
                - emails_duplicados: int (ja processados anteriormente, skip)
                - emails_processados: int
                - xmls_processados: int
                - xmls_ignorados: int (cteProc — CTes normais)
                - cancelados_ok: int
                - pendencias: int
                - erros: int
                - mensagem: str (resumo)
        """
        stats = {
            'sucesso': True,
            'pastas_processadas': 0,
            'emails_encontrados': 0,
            'emails_duplicados': 0,
            'emails_processados': 0,
            'xmls_processados': 0,
            'xmls_ignorados': 0,
            'cancelados_ok': 0,
            'pendencias': 0,
            'erros': 0,
            # Reprocessamento automatico de ORPHANs/ERROs (race condition sync)
            'reprocess_total': 0,
            'reprocess_ok': 0,
            'reprocess_ainda_orphan': 0,
            'reprocess_pulados': 0,
            'reprocess_outros': 0,
            'mensagem': '',
        }

        # Validar config
        upn = os.environ.get('GRAPH_MAILBOX_UPN', '').strip()
        folder_config = os.environ.get('GRAPH_FOLDER_NAME', '').strip()
        max_emails = int(
            os.environ.get('CTE_CANCELAMENTO_MAX_EMAILS', str(DEFAULT_MAX_EMAILS))
        )
        janela_horas = int(
            os.environ.get('CTE_CANCELAMENTO_JANELA_HORAS', str(DEFAULT_JANELA_HORAS))
        )

        if not upn or not folder_config:
            stats['sucesso'] = False
            stats['mensagem'] = (
                "Config incompleta: GRAPH_MAILBOX_UPN ou GRAPH_FOLDER_NAME "
                "nao configurados"
            )
            logger.warning(f"[CteCancelamentoJob] {stats['mensagem']}")
            return stats

        # Parsear lista de pastas (separadas por ';')
        # Exemplo: "Faturas;Faturas/XML CTe's" -> ['Faturas', 'Faturas/XML CTe\'s']
        folder_names = self._parse_folder_list(folder_config)
        if not folder_names:
            stats['sucesso'] = False
            stats['mensagem'] = f"GRAPH_FOLDER_NAME vazio apos parse: {folder_config!r}"
            logger.warning(f"[CteCancelamentoJob] {stats['mensagem']}")
            return stats

        # Calcular janela temporal (com gordura para drift)
        received_since = datetime.now(timezone.utc) - timedelta(
            hours=janela_horas,
            minutes=JANELA_GORDURA_MINUTOS,
        )

        logger.info(
            f"[CteCancelamentoJob] Iniciando. Pastas={folder_names}, "
            f"janela={janela_horas}h (+{JANELA_GORDURA_MINUTOS}min gordura), "
            f"desde={received_since.isoformat()}"
        )

        # FASE 0: Reprocessar ORPHANs/ERROs recentes antes de olhar emails novos.
        # Cobre race condition: email chegou antes do CTe sincronizar no Odoo.
        # Configuravel via env:
        # - CTE_CANCELAMENTO_REPROCESS_DIAS (default 15)
        # - CTE_CANCELAMENTO_REPROCESS_LIMIT (default 50)
        # - CTE_CANCELAMENTO_REPROCESS_ENABLED (default true)
        reprocess_enabled = (
            os.environ.get('CTE_CANCELAMENTO_REPROCESS_ENABLED', 'true').lower()
            in ('true', '1', 'yes', 'on')
        )
        if reprocess_enabled:
            try:
                reprocess_dias = int(
                    os.environ.get('CTE_CANCELAMENTO_REPROCESS_DIAS', '15')
                )
                reprocess_limit = int(
                    os.environ.get('CTE_CANCELAMENTO_REPROCESS_LIMIT', '50')
                )
                reprocess_stats = (
                    self._get_cancelamento_service()
                    .reprocessar_pendentes_antigas(
                        janela_dias=reprocess_dias,
                        limit=reprocess_limit,
                    )
                )
                stats['reprocess_total'] = reprocess_stats.get('reprocessadas', 0)
                stats['reprocess_ok'] = reprocess_stats.get('cancelados_ok', 0)
                stats['reprocess_ainda_orphan'] = reprocess_stats.get('ainda_orphan', 0)
                stats['reprocess_pulados'] = reprocess_stats.get('pulados', 0)
                stats['reprocess_outros'] = reprocess_stats.get('outros', 0)
                logger.info(
                    f"[CteCancelamentoJob] Fase 0 (reprocess): {reprocess_stats}"
                )
            except Exception as e:
                # Nao e fatal — continuar com o processamento dos emails novos
                logger.exception(
                    f"[CteCancelamentoJob] Erro na fase 0 de reprocess: {e}"
                )

        # Processar cada pasta
        try:
            graph = self._get_graph()
        except Exception as e:
            stats['sucesso'] = False
            stats['mensagem'] = f"Erro na autenticacao Graph: {e}"
            logger.exception(f"[CteCancelamentoJob] {stats['mensagem']}")
            return stats

        for folder_name in folder_names:
            try:
                folder_id = graph.obter_pasta_id(upn=upn, folder_name=folder_name)
                logger.info(
                    f"[CteCancelamentoJob] Pasta '{folder_name}' resolvida: "
                    f"folder_id={folder_id[:20]}..."
                )

                mensagens = graph.listar_emails_pasta(
                    upn=upn,
                    folder_id=folder_id,
                    received_since=received_since,
                    unread_only=False,  # IMPORTANTE: nao depende de isRead
                    top=max_emails,
                )
                logger.info(
                    f"[CteCancelamentoJob] {len(mensagens)} email(s) em "
                    f"'{folder_name}' na janela temporal"
                )
                stats['pastas_processadas'] += 1
                stats['emails_encontrados'] += len(mensagens)
            except Exception as e:
                logger.exception(
                    f"[CteCancelamentoJob] Erro ao listar pasta '{folder_name}': {e}"
                )
                stats['erros'] += 1
                continue

            # Processar cada email
            for mensagem in mensagens:
                message_id = mensagem.get('id')
                # Guarda defensiva: se Graph retornar email sem 'id' (nao deveria,
                # mas defensive), skip em vez de crashar no slice abaixo.
                if not message_id:
                    logger.warning(
                        f"[CteCancelamentoJob] Email sem 'id' em "
                        f"'{folder_name}', pulando"
                    )
                    stats['erros'] += 1
                    continue

                # DEDUP: checar se esse email ja foi processado (over-loop protection)
                from app.fretes.services.cancelamento_cte_service import (
                    CancelamentoCteService,
                )
                if CancelamentoCteService.ja_processado(message_id):
                    stats['emails_duplicados'] += 1
                    logger.debug(
                        f"[CteCancelamentoJob] Email {message_id[:20]}... "
                        f"ja processado anteriormente, skip (over-loop dedup)"
                    )
                    continue

                resultado_email = self._processar_email(upn, mensagem)
                stats['emails_processados'] += 1
                stats['xmls_processados'] += resultado_email['xmls_processados']
                stats['xmls_ignorados'] += resultado_email['xmls_ignorados']
                stats['cancelados_ok'] += resultado_email['cancelados_ok']
                stats['pendencias'] += resultado_email['pendencias']
                stats['erros'] += resultado_email['erros']

        stats['mensagem'] = (
            f"reprocess={stats['reprocess_total']} "
            f"(ok={stats['reprocess_ok']}, ainda_orphan={stats['reprocess_ainda_orphan']}, "
            f"outros={stats['reprocess_outros']}, pulados={stats['reprocess_pulados']}) | "
            f"{stats['pastas_processadas']} pasta(s) / "
            f"{stats['emails_encontrados']} email(s) encontrado(s) / "
            f"{stats['emails_duplicados']} dedup / "
            f"{stats['emails_processados']} processado(s) / "
            f"{stats['xmls_processados']} XML(s) / "
            f"{stats['xmls_ignorados']} cteProc ignorado(s) / "
            f"{stats['cancelados_ok']} OK / "
            f"{stats['pendencias']} pendencia(s) / "
            f"{stats['erros']} erro(s)"
        )
        logger.info(f"[CteCancelamentoJob] Concluido: {stats['mensagem']}")
        return stats

    @staticmethod
    def _parse_folder_list(folder_config: str) -> List[str]:
        """
        Parseia GRAPH_FOLDER_NAME em lista de pastas.

        Aceita:
        - Nome simples: "CTe Cancelados" -> ["CTe Cancelados"]
        - Path: "Faturas/XML CTe's" -> ["Faturas/XML CTe's"]
        - Lista separada por ';': "Faturas;Faturas/XML CTe's"
          -> ["Faturas", "Faturas/XML CTe's"]

        Espacos em branco no inicio/fim sao removidos. Entradas vazias sao
        descartadas.
        """
        if not folder_config:
            return []
        partes = [p.strip() for p in folder_config.split(';')]
        return [p for p in partes if p]

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

        # NOTA: este job NAO marca emails como lidos. Respeita o fluxo humano
        # da pessoa dona da caixa. O dedup via email_message_id (feito em
        # executar()) garante que cada email e processado 1x mesmo com over-loop.
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

        # NAO marcar como lido — dedup por email_message_id + over-loop
        # garantem que o email sera processado 1x e os ciclos seguintes
        # farao skip silencioso ate a janela temporal expirar (3h).
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

        IMPORTANTE: a ordem importa. STATUS_ERRO esta dentro de STATUS_PENDENTES,
        entao o check por STATUS_ERRO tem que vir ANTES do `in STATUS_PENDENTES`
        — caso contrario erros seriam classificados como pendencias genericas.
        """
        from app.fretes.models import CtePendenciaCancelamento

        status = resultado_xml.get('status')
        if status == CtePendenciaCancelamento.STATUS_CANCELADO_OK:
            acumulado['cancelados_ok'] += 1
        elif status == CtePendenciaCancelamento.STATUS_ERRO:
            acumulado['erros'] += 1
        elif status in CtePendenciaCancelamento.STATUS_PENDENTES:
            acumulado['pendencias'] += 1

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
