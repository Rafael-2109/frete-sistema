"""AprovacaoSubcontratoService — fluxo de tratativa de subcontratos.

Porta para o CarVia o conceito de "Em Tratativa" do modulo Nacom
(`app/fretes/`). Quando a divergencia entre `valor_considerado` ou
`valor_pago` e `valor_cotado` ultrapassa a tolerancia hardcoded, uma
solicitacao de aprovacao e criada na tabela satelite
`carvia_aprovacoes_subcontrato`.

Diferencas em relacao ao Nacom:
1. Logica centralizada aqui (Nacom tem inline em `routes.py:editar_frete`)
2. Snapshot dos 3 valores no momento da solicitacao
3. Idempotente: solicitacao PENDENTE existente nao cria duplicata
4. Aprovacao usa `with_for_update()` para evitar race condition
5. Status do `sub.status_conferencia` permanece PENDENTE durante tratativa
   (e definido APROVADO ou DIVERGENTE so apos a decisao do aprovador)

Ref:
- .claude/plans/wobbly-tumbling-treasure.md (D4 — substituir totalmente)
- /tmp/subagent-findings/aprovacao_fretes_nacom.md
"""

import logging
from decimal import Decimal
from typing import Dict, Optional

from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# Tolerancia hardcoded igual Nacom (app/fretes/routes.py:887, 898)
TOLERANCIA_APROVACAO = Decimal('5.00')


class AprovacaoSubcontratoService:
    """Servico de gerenciamento de tratativas de subcontratos."""

    # =================================================================
    # Verificacao automatica e solicitacao
    # =================================================================
    def verificar_e_solicitar_se_necessario(
        self, sub_id: int, usuario: str
    ) -> Dict:
        """Avalia se sub requer tratativa e cria solicitacao se sim.

        Aplicado quando:
        - Conferente registra DIVERGENTE no `ConferenciaService`
        - Operador atualiza `valor_pago` via endpoint `registrar-pagamento`

        Regras (espelho do Nacom `app/fretes/routes.py:882-914`):
        - Regra A: `abs(valor_considerado - valor_cotado) > TOLERANCIA`
        - Regra B: `abs(valor_pago - valor_cotado) > TOLERANCIA`

        Se nenhuma regra dispara: retorna sucesso sem criar solicitacao
        (diff dentro da tolerancia — pode ser lancada em CC sem aprovacao).
        """
        from app.carvia.models import CarviaSubcontrato

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            return {'sucesso': False, 'erro': 'Subcontrato nao encontrado'}

        if sub.status == 'CANCELADO':
            return {'sucesso': False, 'erro': 'Subcontrato cancelado — sem tratativa'}

        valor_cotado = Decimal(str(sub.valor_cotado or 0))
        valor_considerado = (
            Decimal(str(sub.valor_considerado))
            if sub.valor_considerado is not None
            else None
        )
        valor_pago = (
            Decimal(str(sub.valor_pago)) if sub.valor_pago is not None else None
        )

        motivos = []
        diff_relevante = Decimal('0')

        if valor_considerado is not None:
            diff_a = abs(valor_considerado - valor_cotado)
            if diff_a > TOLERANCIA_APROVACAO:
                motivos.append(
                    f'Diferenca de R$ {diff_a:.2f} entre valor considerado '
                    f'(R$ {valor_considerado:.2f}) e cotado (R$ {valor_cotado:.2f})'
                )
                diff_relevante = max(diff_relevante, diff_a)

        if valor_pago is not None:
            diff_b = abs(valor_pago - valor_cotado)
            if diff_b > TOLERANCIA_APROVACAO:
                motivos.append(
                    f'Diferenca de R$ {diff_b:.2f} entre valor pago '
                    f'(R$ {valor_pago:.2f}) e cotado (R$ {valor_cotado:.2f})'
                )
                diff_relevante = max(diff_relevante, diff_b)

        if not motivos:
            return {
                'sucesso': True,
                'tratativa_aberta': False,
                'motivo': 'dentro da tolerancia',
            }

        # Solicitar aprovacao (idempotente)
        return self.solicitar_aprovacao(
            sub_id=sub_id,
            motivo=' | '.join(motivos),
            usuario=usuario,
            valor_cotado=valor_cotado,
            valor_considerado=valor_considerado,
            valor_pago=valor_pago,
            diferenca=diff_relevante,
        )

    def solicitar_aprovacao(
        self,
        sub_id: int,
        motivo: str,
        usuario: str,
        valor_cotado: Optional[Decimal] = None,
        valor_considerado: Optional[Decimal] = None,
        valor_pago: Optional[Decimal] = None,
        diferenca: Optional[Decimal] = None,
    ) -> Dict:
        """Cria solicitacao de aprovacao PENDENTE (idempotente).

        Se ja existe PENDENTE para este sub, retorna ela sem criar duplicata.
        Aprovacoes finalizadas (APROVADO/REJEITADO) anteriores nao bloqueiam
        nova solicitacao — historico completo e preservado.
        """
        from app.carvia.models import CarviaAprovacaoSubcontrato, CarviaSubcontrato

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            return {'sucesso': False, 'erro': 'Subcontrato nao encontrado'}

        # Snapshot atual se nao fornecido (computado ANTES da verificacao
        # de idempotencia para permitir atualizacao de snaps stale)
        if valor_cotado is None and sub.valor_cotado is not None:
            valor_cotado = Decimal(str(sub.valor_cotado))
        if valor_considerado is None and sub.valor_considerado is not None:
            valor_considerado = Decimal(str(sub.valor_considerado))
        if valor_pago is None and sub.valor_pago is not None:
            valor_pago = Decimal(str(sub.valor_pago))

        # Idempotencia: PENDENTE existente?
        existente = CarviaAprovacaoSubcontrato.query.filter_by(
            subcontrato_id=sub_id,
            status='PENDENTE',
        ).first()
        if existente:
            # Atualiza snapshots se os valores mudaram desde a solicitacao
            # original (ex: operador corrigiu valor_pago apos criar tratativa).
            # Evita que aprovador veja dados desatualizados na tela.
            snaps_atualizados = False
            if valor_cotado is not None and existente.valor_cotado_snap != valor_cotado:
                existente.valor_cotado_snap = valor_cotado
                snaps_atualizados = True
            if valor_considerado is not None and existente.valor_considerado_snap != valor_considerado:
                existente.valor_considerado_snap = valor_considerado
                snaps_atualizados = True
            if valor_pago is not None and existente.valor_pago_snap != valor_pago:
                existente.valor_pago_snap = valor_pago
                snaps_atualizados = True
            if diferenca is not None and existente.diferenca_snap != diferenca:
                existente.diferenca_snap = diferenca
                snaps_atualizados = True
            if motivo and existente.motivo_solicitacao != motivo:
                existente.motivo_solicitacao = motivo
                snaps_atualizados = True

            logger.info(
                f'Solicitacao PENDENTE ja existe para sub {sub_id} '
                f'(aprovacao_id={existente.id}) — idempotente '
                f'(snaps_atualizados={snaps_atualizados})'
            )
            return {
                'sucesso': True,
                'tratativa_aberta': True,
                'aprovacao_id': existente.id,
                'criada': False,
                'snaps_atualizados': snaps_atualizados,
            }

        try:
            aprovacao = CarviaAprovacaoSubcontrato(
                subcontrato_id=sub_id,
                status='PENDENTE',
                solicitado_por=usuario,
                solicitado_em=agora_utc_naive(),
                motivo_solicitacao=motivo,
                valor_cotado_snap=valor_cotado,
                valor_considerado_snap=valor_considerado,
                valor_pago_snap=valor_pago,
                diferenca_snap=diferenca,
            )
            db.session.add(aprovacao)
            sub.requer_aprovacao = True
            db.session.flush()  # popula aprovacao.id sem commit

            logger.info(
                f'Solicitacao de aprovacao criada | sub={sub_id} | '
                f'aprovacao={aprovacao.id} | usuario={usuario}'
            )
            return {
                'sucesso': True,
                'tratativa_aberta': True,
                'aprovacao_id': aprovacao.id,
                'criada': True,
            }

        except Exception as e:
            logger.exception(f'Erro ao criar solicitacao para sub {sub_id}: {e}')
            return {'sucesso': False, 'erro': str(e)}

    # =================================================================
    # Decisoes do aprovador
    # =================================================================
    def aprovar(
        self,
        aprovacao_id: int,
        lancar_diferenca: bool,
        observacoes: str,
        usuario: str,
    ) -> Dict:
        """Aprova a tratativa.

        Acoes:
        1. Lock pessimista (with_for_update) para evitar race condition
        2. Valida que aprovacao ainda esta PENDENTE
        3. Marca aprovacao como APROVADO + grava aprovador + observacoes
        4. sub.status_conferencia = 'APROVADO'
        5. sub.requer_aprovacao = False
        6. Se lancar_diferenca: chama ContaCorrenteService.lancar_movimentacao
        7. Cascata: reverifica fatura completa via ConferenciaService

        Tudo em uma transacao atomica.
        """
        from app.carvia.models import (
            CarviaAprovacaoSubcontrato,
            CarviaSubcontrato,
            CarviaFaturaTransportadora,
        )

        try:
            # Lock pessimista
            aprovacao = (
                db.session.query(CarviaAprovacaoSubcontrato)
                .filter(CarviaAprovacaoSubcontrato.id == aprovacao_id)
                .with_for_update()
                .first()
            )
            if not aprovacao:
                return {'sucesso': False, 'erro': 'Aprovacao nao encontrada'}

            if aprovacao.status != 'PENDENTE':
                return {
                    'sucesso': False,
                    'erro': f'Aprovacao ja processada (status={aprovacao.status})',
                }

            sub = db.session.get(CarviaSubcontrato, aprovacao.subcontrato_id)
            if not sub:
                return {'sucesso': False, 'erro': 'Subcontrato nao encontrado'}

            # Gate adicional: se fatura ja CONFERIDO, nao permitir lancar CC
            fatura = None
            if sub.fatura_transportadora_id:
                fatura = db.session.get(
                    CarviaFaturaTransportadora, sub.fatura_transportadora_id
                )
            if (
                lancar_diferenca
                and fatura is not None
                and fatura.status_conferencia == 'CONFERIDO'
            ):
                return {
                    'sucesso': False,
                    'erro': (
                        'Nao e possivel lancar diferenca em CC: fatura ja CONFERIDO. '
                        'Reabra a fatura primeiro.'
                    ),
                }

            # Atualiza aprovacao
            aprovacao.status = 'APROVADO'
            aprovacao.aprovador = usuario
            aprovacao.aprovado_em = agora_utc_naive()
            aprovacao.observacoes_aprovacao = observacoes
            aprovacao.lancar_diferenca = bool(lancar_diferenca)

            # Atualiza sub
            sub.status_conferencia = 'APROVADO'
            sub.requer_aprovacao = False
            sub.conferido_por = usuario
            sub.conferido_em = agora_utc_naive()

            # Lanca CC se opt-in
            cc_id = None
            if lancar_diferenca:
                from app.carvia.services.financeiro.conta_corrente_service import (
                    ContaCorrenteService,
                )
                cc_resultado = ContaCorrenteService.lancar_movimentacao(
                    sub_id=sub.id,
                    descricao=f'Diferenca aprovada (aprovacao #{aprovacao.id})',
                    usuario=usuario,
                    fatura_transportadora_id=sub.fatura_transportadora_id,
                    observacoes=observacoes,
                )
                if not cc_resultado.get('sucesso'):
                    # Falha ao lancar CC -> aborta a aprovacao inteira
                    # (aprovador marcou "lancar diferenca" mas o sub nao atende
                    # pre-requisitos como valor_pago/valor_considerado preenchidos).
                    db.session.rollback()
                    return {
                        'sucesso': False,
                        'erro': (
                            f'Aprovacao cancelada: falha ao lancar CC — '
                            f'{cc_resultado.get("erro")}. '
                            f'Verifique se valor_pago e valor_considerado estao '
                            f'preenchidos antes de marcar "lancar diferenca".'
                        ),
                    }
                cc_id = cc_resultado.get('movimentacao_id')

            # Cascata fatura (delega para ConferenciaService — ele ja tem essa logica)
            fatura_atualizada = None
            if sub.fatura_transportadora_id:
                from app.carvia.services.documentos.conferencia_service import (
                    ConferenciaService,
                )
                conf_svc = ConferenciaService()
                _, fatura_atualizada = conf_svc._verificar_fatura_completa(
                    sub.fatura_transportadora_id, usuario
                )

            db.session.commit()

            logger.info(
                f'Aprovacao APROVADA | aprovacao={aprovacao_id} | sub={sub.id} | '
                f'lancar_diferenca={lancar_diferenca} | cc_id={cc_id} | '
                f'usuario={usuario}'
            )
            return {
                'sucesso': True,
                'aprovacao_id': aprovacao_id,
                'cc_id': cc_id,
                'fatura_status': fatura_atualizada,
            }

        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao aprovar aprovacao {aprovacao_id}: {e}')
            return {'sucesso': False, 'erro': str(e)}

    def rejeitar(
        self, aprovacao_id: int, observacoes: str, usuario: str
    ) -> Dict:
        """Rejeita a tratativa.

        Acoes:
        1. Lock pessimista
        2. Valida PENDENTE
        3. aprovacao.status = 'REJEITADO'
        4. sub.status_conferencia = 'DIVERGENTE' (final, sem CC)
        5. sub.requer_aprovacao = False
        6. Cascata fatura
        """
        from app.carvia.models import (
            CarviaAprovacaoSubcontrato,
            CarviaSubcontrato,
        )

        try:
            aprovacao = (
                db.session.query(CarviaAprovacaoSubcontrato)
                .filter(CarviaAprovacaoSubcontrato.id == aprovacao_id)
                .with_for_update()
                .first()
            )
            if not aprovacao:
                return {'sucesso': False, 'erro': 'Aprovacao nao encontrada'}

            if aprovacao.status != 'PENDENTE':
                return {
                    'sucesso': False,
                    'erro': f'Aprovacao ja processada (status={aprovacao.status})',
                }

            sub = db.session.get(CarviaSubcontrato, aprovacao.subcontrato_id)
            if not sub:
                return {'sucesso': False, 'erro': 'Subcontrato nao encontrado'}

            aprovacao.status = 'REJEITADO'
            aprovacao.aprovador = usuario
            aprovacao.aprovado_em = agora_utc_naive()
            aprovacao.observacoes_aprovacao = observacoes
            aprovacao.lancar_diferenca = False

            sub.status_conferencia = 'DIVERGENTE'
            sub.requer_aprovacao = False
            sub.conferido_por = usuario
            sub.conferido_em = agora_utc_naive()

            # Cascata fatura
            fatura_atualizada = None
            if sub.fatura_transportadora_id:
                from app.carvia.services.documentos.conferencia_service import (
                    ConferenciaService,
                )
                conf_svc = ConferenciaService()
                _, fatura_atualizada = conf_svc._verificar_fatura_completa(
                    sub.fatura_transportadora_id, usuario
                )

            db.session.commit()

            logger.info(
                f'Aprovacao REJEITADA | aprovacao={aprovacao_id} | sub={sub.id} | '
                f'usuario={usuario}'
            )
            return {
                'sucesso': True,
                'aprovacao_id': aprovacao_id,
                'fatura_status': fatura_atualizada,
            }

        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao rejeitar aprovacao {aprovacao_id}: {e}')
            return {'sucesso': False, 'erro': str(e)}

    # =================================================================
    # Listagem (fila de pendentes)
    # =================================================================
    def listar_pendentes(self):
        """Retorna queryset de aprovacoes PENDENTE com sub joined.

        Usado pela rota `/carvia/subcontratos/aprovacoes`.
        """
        from app.carvia.models import (
            CarviaAprovacaoSubcontrato,
            CarviaSubcontrato,
        )

        return (
            db.session.query(CarviaAprovacaoSubcontrato, CarviaSubcontrato)
            .join(
                CarviaSubcontrato,
                CarviaSubcontrato.id == CarviaAprovacaoSubcontrato.subcontrato_id,
            )
            .filter(CarviaAprovacaoSubcontrato.status == 'PENDENTE')
            .order_by(CarviaAprovacaoSubcontrato.solicitado_em.desc())
            .all()
        )

    def contar_pendentes(self) -> int:
        """Conta total de aprovacoes PENDENTE — usado para badge no menu."""
        from app.carvia.models import CarviaAprovacaoSubcontrato

        return CarviaAprovacaoSubcontrato.query.filter_by(status='PENDENTE').count()

    # =================================================================
    # Cancelamento automatico (chamado por hooks)
    # =================================================================
    def rejeitar_pendentes_de_sub(self, sub_id: int, motivo: str, usuario: str) -> int:
        """Rejeita silenciosamente todas as aprovacoes PENDENTE de um sub.

        Usado em hooks de cancelamento (sub.status='CANCELADO',
        desanexar_subcontrato_fatura_transportadora). NAO commita —
        chamador deve commitar.
        """
        from app.carvia.models import CarviaAprovacaoSubcontrato

        pendentes = CarviaAprovacaoSubcontrato.query.filter_by(
            subcontrato_id=sub_id, status='PENDENTE'
        ).all()

        if not pendentes:
            return 0

        for ap in pendentes:
            ap.status = 'REJEITADO'
            ap.aprovador = usuario
            ap.aprovado_em = agora_utc_naive()
            ap.observacoes_aprovacao = f'[AUTO] {motivo}'
            ap.lancar_diferenca = False

        logger.info(
            f'{len(pendentes)} aprovacao(oes) PENDENTE rejeitadas auto | '
            f'sub={sub_id} | motivo={motivo}'
        )
        return len(pendentes)
