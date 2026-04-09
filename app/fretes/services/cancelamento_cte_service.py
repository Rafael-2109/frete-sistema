"""
CancelamentoCteService — Orquestra cancelamento de CTe local + Odoo
====================================================================

Invocado pelo job `CteCancelamentoOutlookJob` para processar XMLs de
cancelamento vindos do Outlook 365.

Fluxo (por chave):
1. Busca `ConhecimentoTransporte` por `chave_acesso`
2. Se NAO encontrar, tenta `CteService.importar_cte_por_chave()`
3. Se ainda nao encontrar → pendencia ORPHAN (nao cancela)
4. Se encontrar mas ja estiver `cancelado=True` → retorna idempotente (ok)
5. Se o frete vinculado tem fatura CONFERIDA → pendencia
   PENDENTE_FATURA_CONFERIDA (nao cancela, alerta para revisao manual)
6. Caso contrario:
   - Marca CTe local: cancelado, data_cancelamento, protocolo, motivo, origem, ativo=False
   - Seta odoo_status_codigo='07' (Rejeitado/Cancelado no vocabulario local)
   - Se houver frete_id, marca frete.status='CANCELADO' E cria pendencia
     FRETE_CANCELADO_REVISAR (sem limpar numero/valor para preservar auditoria)
   - Chama `CteService.marcar_cancelado_no_odoo(dfe_id)` que seta
     l10n_br_situacao_dfe='CANCELADA' + l10n_br_status='07' (active mantido)
     (se falhar, cria pendencia CANCELAMENTO_ODOO_FALHOU mas mantem
     cancelamento local)
   - Cria pendencia CANCELADO_OK
7. `db.session.commit()` no final. Chamador responsavel por rollback em erro fatal.

Data: 2026-04-09
Referencia: .claude/plans/temporal-exploring-biscuit.md
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app import db
from app.fretes.models import (
    ConhecimentoTransporte,
    CtePendenciaCancelamento,
    FaturaFrete,
    Frete,
)
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# ======================================================================
# Constantes
# ======================================================================

ORIGEM_OUTLOOK = 'OUTLOOK_XML'
ODOO_STATUS_CANCELADO = '07'  # Rejeitado no vocabulario local


class CancelamentoCteService:
    """
    Service de cancelamento de CTe.

    NAO instanciar dentro de app_context: reuse uma instancia por run do job.
    O service depende do CteService para buscar/arquivar no Odoo.
    """

    def __init__(self, cte_service):
        """
        Args:
            cte_service: instancia de app.odoo.services.cte_service.CteService
                         (injecao de dependencia para testabilidade)
        """
        self.cte_service = cte_service

    # ------------------------------------------------------------------
    # Dedup — suporte ao over-loop (scheduler 30 min + janela 3h)
    # ------------------------------------------------------------------

    @staticmethod
    def ja_processado(email_message_id: Optional[str]) -> bool:
        """
        Verifica se ja existe pendencia para esse email_message_id.

        Usado pelo job antes de processar cada email, como dedup do over-loop:
        - Scheduler principal roda a cada 30 min
        - Job le emails das ultimas 3h
        - Cada email cai em ate 6 execucoes consecutivas (30 min × 6 = 3h)
        - Primeira execucao cria pendencia (qualquer status); as 5 seguintes
          fazem skip silencioso graças a esta checagem.

        Cobre todos os statuses (CANCELADO_OK, ORPHAN, PENDENTE_FATURA_CONFERIDA,
        FRETE_CANCELADO_REVISAR, ERRO, ARQUIVAMENTO_ODOO_FALHOU) — uma vez
        registrado, o email nao e reprocessado automaticamente. Revisao manual
        pode deletar a pendencia para forcar reprocessamento.

        Args:
            email_message_id: id do email no Microsoft Graph

        Returns:
            True se ja existe pendencia com esse message_id.
            False se nao existe ou message_id e None/vazio.
        """
        if not email_message_id:
            return False
        existe = (
            db.session.query(CtePendenciaCancelamento.id)
            .filter(CtePendenciaCancelamento.email_message_id == email_message_id)
            .first()
        )
        return existe is not None

    # ------------------------------------------------------------------
    # API principal
    # ------------------------------------------------------------------

    def cancelar_por_chave(
        self,
        chave_acesso: str,
        evento_info: Dict[str, Any],
        xml_raw: Optional[str] = None,
        email_message_id: Optional[str] = None,
        email_subject: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executa o cancelamento logico do CTe a partir de evento de cancelamento.

        Args:
            chave_acesso: 44 digitos do CTe
            evento_info: dict do CteEventoParser.parse_evento() com:
                - cancelamento (bool)
                - protocolo (str or None)
                - data_evento (str ISO or None)
                - justificativa (str or None)
            xml_raw: XML original (string) para auditoria
            email_message_id: id do email no Graph
            email_subject: subject do email

        Returns:
            Dict com:
                - status: CANCELADO_OK | PENDENTE_FATURA_CONFERIDA | ORPHAN |
                          FRETE_CANCELADO_REVISAR | ERRO | ARQUIVAMENTO_ODOO_FALHOU
                - cte_id: int ou None
                - frete_id: int ou None
                - pendencia_id: int (sempre cria pendencia, ok ou nao)
                - mensagem: str
        """
        if not chave_acesso or len(chave_acesso) != 44 or not chave_acesso.isdigit():
            return self._registrar_pendencia_erro(
                chave_acesso=chave_acesso or '(vazia)',
                mensagem=f"Chave invalida: {chave_acesso!r}",
                xml_raw=xml_raw,
                email_message_id=email_message_id,
                email_subject=email_subject,
            )

        if not evento_info.get('cancelamento'):
            return self._registrar_pendencia_erro(
                chave_acesso=chave_acesso,
                mensagem=(
                    f"XML nao representa cancelamento efetivo "
                    f"(tp_evento={evento_info.get('tp_evento')}, "
                    f"cstat={evento_info.get('cstat')})"
                ),
                xml_raw=xml_raw,
                email_message_id=email_message_id,
                email_subject=email_subject,
            )

        # Passo 1: Buscar local
        cte = ConhecimentoTransporte.query.filter_by(
            chave_acesso=chave_acesso
        ).first()

        # Passo 2: Fallback Odoo
        if cte is None:
            logger.info(
                f"[CancelamentoCTe] CTe {chave_acesso} nao encontrado local. "
                f"Tentando importar do Odoo..."
            )
            try:
                cte = self.cte_service.importar_cte_por_chave(chave_acesso)
            except Exception as e:
                logger.error(
                    f"[CancelamentoCTe] Erro ao importar CTe {chave_acesso}: {e}"
                )
                db.session.rollback()
                return self._registrar_pendencia_erro(
                    chave_acesso=chave_acesso,
                    mensagem=f"Erro ao buscar CTe no Odoo: {e}",
                    xml_raw=xml_raw,
                    email_message_id=email_message_id,
                    email_subject=email_subject,
                )

            if cte is not None:
                # Persistir importacao antes do update (envolvido em try/except
                # para evitar PendingRollbackError na sessao se commit falhar)
                try:
                    db.session.commit()
                    # Re-obter cte na nova transacao para evitar stale objects
                    cte = ConhecimentoTransporte.query.filter_by(
                        chave_acesso=chave_acesso
                    ).first()
                except Exception as e:
                    logger.exception(
                        f"[CancelamentoCTe] Erro ao commitar CTe importado "
                        f"{chave_acesso}"
                    )
                    db.session.rollback()
                    return self._registrar_pendencia_erro(
                        chave_acesso=chave_acesso,
                        mensagem=f"Erro ao commitar CTe importado do Odoo: {e}",
                        xml_raw=xml_raw,
                        email_message_id=email_message_id,
                        email_subject=email_subject,
                    )

        if cte is None:
            # Passo 3: Orphan — nao existe local nem no Odoo
            return self._criar_pendencia(
                status=CtePendenciaCancelamento.STATUS_ORPHAN,
                chave_acesso=chave_acesso,
                cte_id=None,
                frete_id=None,
                mensagem=(
                    f"CTe chave {chave_acesso} nao encontrado no sistema local "
                    f"nem no Odoo. Cancelamento recebido via Outlook XML "
                    f"mas nao ha CTe correspondente para marcar."
                ),
                xml_raw=xml_raw,
                email_message_id=email_message_id,
                email_subject=email_subject,
            )

        # Passo 4: Idempotencia — se ja cancelado, nao refaz
        if cte.cancelado:
            logger.info(
                f"[CancelamentoCTe] CTe id={cte.id} chave={chave_acesso} "
                f"ja esta cancelado (idempotente)"
            )
            return self._criar_pendencia(
                status=CtePendenciaCancelamento.STATUS_CANCELADO_OK,
                chave_acesso=chave_acesso,
                cte_id=cte.id,
                frete_id=cte.frete_id,
                mensagem=(
                    f"CTe ja estava marcado como cancelado "
                    f"(data anterior: {cte.data_cancelamento}). Idempotente."
                ),
                xml_raw=xml_raw,
                email_message_id=email_message_id,
                email_subject=email_subject,
                resolvido=True,
            )

        # Passo 5: Bloqueio por fatura conferida
        frete: Optional[Frete] = None
        if cte.frete_id:
            frete = db.session.get(Frete, cte.frete_id)
            if frete and self._fatura_conferida(frete):
                logger.warning(
                    f"[CancelamentoCTe] CTe id={cte.id} tem frete id={frete.id} "
                    f"com fatura CONFERIDA — NAO cancelando, gerando alerta"
                )
                return self._criar_pendencia(
                    status=CtePendenciaCancelamento.STATUS_PENDENTE_FATURA_CONFERIDA,
                    chave_acesso=chave_acesso,
                    cte_id=cte.id,
                    frete_id=frete.id,
                    mensagem=(
                        f"BLOQUEADO: frete id={frete.id} tem fatura "
                        f"id={frete.fatura_frete_id} com status_conferencia=CONFERIDO. "
                        f"Cancelamento automatico nao aplicado. "
                        f"Revisao manual necessaria."
                    ),
                    xml_raw=xml_raw,
                    email_message_id=email_message_id,
                    email_subject=email_subject,
                )

        # Passo 6: Cancelar localmente
        try:
            self._aplicar_cancelamento_local(cte, evento_info)
        except Exception as e:
            logger.exception(
                f"[CancelamentoCTe] Erro ao aplicar cancelamento local id={cte.id}"
            )
            db.session.rollback()
            return self._registrar_pendencia_erro(
                chave_acesso=chave_acesso,
                cte_id=cte.id,
                frete_id=frete.id if frete else None,
                mensagem=f"Erro ao marcar cancelamento local: {e}",
                xml_raw=xml_raw,
                email_message_id=email_message_id,
                email_subject=email_subject,
            )

        # Passo 7: Se tem frete, marcar CANCELADO e criar pendencia para revisao
        # SEMPRE gera pendencia FRETE_CANCELADO_REVISAR quando houver frete,
        # mesmo se o update de status falhar — o CTe ja esta cancelado e o
        # humano PRECISA revisar, nao podemos esconder o alerta.
        pendencia_frete_criada = False
        frete_update_erro = None
        if frete is not None:
            pendencia_frete_criada = True  # HUMANO PRECISA REVISAR — sempre
            try:
                frete.status = 'CANCELADO'
            except Exception as e:
                frete_update_erro = str(e)
                logger.error(
                    f"[CancelamentoCTe] Erro ao atualizar status do frete "
                    f"id={frete.id}: {e}"
                )

        # Passo 8: Marcar como CANCELADO no Odoo
        # (l10n_br_situacao_dfe='CANCELADA' + l10n_br_status='07' Rejeitado,
        #  active mantido True)
        cancelamento_odoo_ok = True
        cancelamento_odoo_erro = None
        if cte.dfe_id:
            try:
                cancelamento_odoo_ok = self.cte_service.marcar_cancelado_no_odoo(
                    cte.dfe_id
                )
                if not cancelamento_odoo_ok:
                    cancelamento_odoo_erro = (
                        f"marcar_cancelado_no_odoo retornou False para "
                        f"dfe_id={cte.dfe_id}"
                    )
            except Exception as e:
                cancelamento_odoo_ok = False
                cancelamento_odoo_erro = str(e)
                logger.error(
                    f"[CancelamentoCTe] Erro ao marcar DFe {cte.dfe_id} "
                    f"como CANCELADO no Odoo: {e}"
                )

        # Passo 9: Commit + pendencia final
        # Nunca perdemos o cancelamento local mesmo que Odoo falhe.
        try:
            db.session.commit()
        except Exception as e:
            logger.exception(
                f"[CancelamentoCTe] Erro ao commitar cancelamento de {chave_acesso}"
            )
            db.session.rollback()
            return self._registrar_pendencia_erro(
                chave_acesso=chave_acesso,
                cte_id=cte.id,
                frete_id=frete.id if frete else None,
                mensagem=f"Erro no commit final: {e}",
                xml_raw=xml_raw,
                email_message_id=email_message_id,
                email_subject=email_subject,
            )

        # Determinar status da pendencia final
        if not cancelamento_odoo_ok:
            return self._criar_pendencia(
                status=CtePendenciaCancelamento.STATUS_CANCELAMENTO_ODOO_FALHOU,
                chave_acesso=chave_acesso,
                cte_id=cte.id,
                frete_id=frete.id if frete else None,
                mensagem=(
                    f"CTe cancelado localmente, mas falhou ao marcar como "
                    f"CANCELADO no Odoo (dfe_id={cte.dfe_id}). "
                    f"Erro: {cancelamento_odoo_erro}. Marcacao manual "
                    f"necessaria no Odoo: setar l10n_br_situacao_dfe='CANCELADA' "
                    f"+ l10n_br_status='07'."
                ),
                xml_raw=xml_raw,
                email_message_id=email_message_id,
                email_subject=email_subject,
            )

        if pendencia_frete_criada:
            msg_base = (
                f"CTe cancelado e arquivado no Odoo. Frete id="
                f"{frete.id if frete else 'N/A'}"
            )
            if frete_update_erro:
                msg_base += (
                    f" ⚠️ FALHOU ao atualizar status do frete para CANCELADO "
                    f"(erro: {frete_update_erro}). STATUS DO FRETE PRECISA SER "
                    f"ATUALIZADO MANUALMENTE."
                )
            else:
                msg_base += " marcado como CANCELADO."
            msg_base += (
                " REVISAR: verificar pagamentos, conta corrente, aprovacoes "
                "e documentos financeiros vinculados."
            )
            return self._criar_pendencia(
                status=CtePendenciaCancelamento.STATUS_FRETE_CANCELADO_REVISAR,
                chave_acesso=chave_acesso,
                cte_id=cte.id,
                frete_id=frete.id if frete else None,
                mensagem=msg_base,
                xml_raw=xml_raw,
                email_message_id=email_message_id,
                email_subject=email_subject,
            )

        # Caso ideal: CTe sem frete vinculado, arquivamento Odoo ok
        return self._criar_pendencia(
            status=CtePendenciaCancelamento.STATUS_CANCELADO_OK,
            chave_acesso=chave_acesso,
            cte_id=cte.id,
            frete_id=None,
            mensagem=(
                f"CTe cancelado com sucesso e arquivado no Odoo. "
                f"Protocolo: {cte.protocolo_cancelamento or 'N/A'}."
            ),
            xml_raw=xml_raw,
            email_message_id=email_message_id,
            email_subject=email_subject,
            resolvido=True,
        )

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _fatura_conferida(self, frete: Frete) -> bool:
        """Retorna True se o frete tem fatura conferida (bloqueador)."""
        if not frete.fatura_frete_id:
            return False
        fatura: Optional[FaturaFrete] = db.session.get(
            FaturaFrete, frete.fatura_frete_id
        )
        if not fatura:
            return False
        return (fatura.status_conferencia or '').upper() == 'CONFERIDO'

    def _aplicar_cancelamento_local(
        self,
        cte: ConhecimentoTransporte,
        evento_info: Dict[str, Any],
    ):
        """
        Atualiza campos de cancelamento no CTe local.
        NAO faz commit — chamador commita.
        """
        cte.cancelado = True
        cte.data_cancelamento = self._parse_data_evento(
            evento_info.get('data_evento') or evento_info.get('data_registro')
        )
        cte.protocolo_cancelamento = self._truncar(
            evento_info.get('protocolo'), 50
        )
        cte.motivo_cancelamento = evento_info.get('justificativa')
        cte.cancelamento_origem = ORIGEM_OUTLOOK
        cte.odoo_status_codigo = ODOO_STATUS_CANCELADO
        cte.ativo = False
        cte.atualizado_em = agora_utc_naive()
        cte.atualizado_por = 'Sistema CTe Cancelamento Outlook'

    @staticmethod
    def _parse_data_evento(valor: Optional[str]) -> Optional[datetime]:
        """
        Converte string ISO 8601 (com timezone) em datetime naive BRT.

        Formatos aceitos:
        - 2026-04-09T10:15:00-03:00
        - 2026-04-09T13:15:00Z
        - 2026-04-09T10:15:00
        """
        if not valor:
            return None
        try:
            # datetime.fromisoformat aceita offset a partir do Python 3.11
            # Normalizar Z -> +00:00
            v = valor.strip()
            if v.endswith('Z'):
                v = v[:-1] + '+00:00'
            dt = datetime.fromisoformat(v)
            # Se tiver timezone, converter para naive BRT (America/Sao_Paulo)
            if dt.tzinfo is not None:
                # Sem trazer pytz: assume BRT = UTC-3 fixo (suficiente para audit)
                from datetime import timedelta, timezone as tz
                brt = tz(timedelta(hours=-3))
                dt = dt.astimezone(brt).replace(tzinfo=None)
            return dt
        except (ValueError, TypeError) as e:
            logger.warning(
                f"[CancelamentoCTe] data_evento invalida: {valor!r} ({e})"
            )
            return None

    @staticmethod
    def _truncar(valor: Optional[str], tamanho: int) -> Optional[str]:
        if not valor:
            return None
        return valor[:tamanho]

    def _criar_pendencia(
        self,
        status: str,
        chave_acesso: str,
        cte_id: Optional[int],
        frete_id: Optional[int],
        mensagem: str,
        xml_raw: Optional[str],
        email_message_id: Optional[str],
        email_subject: Optional[str],
        resolvido: bool = False,
    ) -> Dict[str, Any]:
        """
        Cria registro em cte_pendencia_cancelamento e commita.
        Retorna dict de resultado.
        """
        pendencia = CtePendenciaCancelamento(
            chave_acesso=chave_acesso,
            cte_id=cte_id,
            frete_id=frete_id,
            status=status,
            mensagem=mensagem,
            xml_raw=xml_raw,
            email_message_id=email_message_id,
            email_subject=self._truncar(email_subject, 500),
        )
        if resolvido:
            pendencia.resolvido_em = agora_utc_naive()
            pendencia.resolvido_por = 'Sistema CTe Cancelamento Outlook'

        try:
            db.session.add(pendencia)
            db.session.commit()
        except Exception as e:
            logger.exception(
                f"[CancelamentoCTe] Erro ao criar pendencia {status}: {e}"
            )
            db.session.rollback()
            return {
                'status': CtePendenciaCancelamento.STATUS_ERRO,
                'cte_id': cte_id,
                'frete_id': frete_id,
                'pendencia_id': None,
                'mensagem': f"Falha ao registrar pendencia: {e}",
            }

        return {
            'status': status,
            'cte_id': cte_id,
            'frete_id': frete_id,
            'pendencia_id': pendencia.id,
            'mensagem': mensagem,
        }

    def _registrar_pendencia_erro(
        self,
        chave_acesso: str,
        mensagem: str,
        xml_raw: Optional[str] = None,
        email_message_id: Optional[str] = None,
        email_subject: Optional[str] = None,
        cte_id: Optional[int] = None,
        frete_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._criar_pendencia(
            status=CtePendenciaCancelamento.STATUS_ERRO,
            chave_acesso=chave_acesso,
            cte_id=cte_id,
            frete_id=frete_id,
            mensagem=mensagem,
            xml_raw=xml_raw,
            email_message_id=email_message_id,
            email_subject=email_subject,
        )
