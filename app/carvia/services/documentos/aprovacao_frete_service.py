"""AprovacaoFreteService — fluxo de tratativa de divergencia em CarviaFrete.

Porta para o CarVia o conceito de "Em Tratativa" do modulo Nacom
(`app/fretes/`). Quando a divergencia ultrapassa a tolerancia, uma
solicitacao de aprovacao e criada em `carvia_aprovacoes_frete`.

Paridade Nacom Frete.requer_aprovacao_por_valor (app/fretes/models.py:145-174):
- Regra A: |valor_considerado - valor_cotado| > R$5
- Regra B: |valor_pago - valor_cotado| > R$5
- Regra C: |valor_pago - valor_considerado| > R$5  (a mais importante)

Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional

from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


TOLERANCIA_APROVACAO = Decimal('5.00')


class AprovacaoFreteService:
    """Servico de gerenciamento de tratativas de CarviaFrete."""

    # =================================================================
    # Verificacao automatica e solicitacao
    # =================================================================
    def verificar_e_solicitar_se_necessario(
        self, frete_id: int, usuario: str
    ) -> Dict:
        """Avalia se frete requer tratativa e cria solicitacao se sim.

        Aplicado quando:
        - Conferente registra conferencia via ConferenciaService
        - Operador atualiza valor_pago via form editar_frete_carvia

        Regras (espelho do Nacom):
        - Regra A: |valor_considerado - valor_cotado| > TOLERANCIA
        - Regra B: |valor_pago - valor_cotado| > TOLERANCIA
        - Regra C: |valor_pago - valor_considerado| > TOLERANCIA
        """
        from app.carvia.models import CarviaFrete

        frete = db.session.get(CarviaFrete, frete_id)
        if not frete:
            return {'sucesso': False, 'erro': 'Frete nao encontrado'}

        if frete.status == 'CANCELADO':
            return {'sucesso': False, 'erro': 'Frete cancelado — sem tratativa'}

        valor_cotado = Decimal(str(frete.valor_cotado or 0))
        valor_considerado = (
            Decimal(str(frete.valor_considerado))
            if frete.valor_considerado is not None else None
        )
        valor_pago = (
            Decimal(str(frete.valor_pago))
            if frete.valor_pago is not None else None
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

        # Regra C: pago vs considerado (paridade Nacom)
        if valor_considerado is not None and valor_pago is not None:
            diff_c = abs(valor_pago - valor_considerado)
            if diff_c > TOLERANCIA_APROVACAO:
                if valor_pago > valor_considerado:
                    motivos.append(
                        f'Valor Pago (R$ {valor_pago:.2f}) superior ao '
                        f'Considerado (R$ {valor_considerado:.2f}) em R$ {diff_c:.2f}'
                    )
                else:
                    motivos.append(
                        f'Valor Considerado (R$ {valor_considerado:.2f}) superior ao '
                        f'Pago (R$ {valor_pago:.2f}) em R$ {diff_c:.2f}'
                    )
                diff_relevante = max(diff_relevante, diff_c)

        if not motivos:
            return {
                'sucesso': True,
                'tratativa_aberta': False,
                'motivo': 'dentro da tolerancia',
            }

        return self.solicitar_aprovacao(
            frete_id=frete_id,
            motivo=' | '.join(motivos),
            usuario=usuario,
            valor_cotado=valor_cotado,
            valor_considerado=valor_considerado,
            valor_pago=valor_pago,
            diferenca=diff_relevante,
        )

    # =================================================================
    # Solicitacao (idempotente)
    # =================================================================
    def solicitar_aprovacao(
        self,
        frete_id: int,
        motivo: str,
        usuario: str,
        valor_cotado: Optional[Decimal] = None,
        valor_considerado: Optional[Decimal] = None,
        valor_pago: Optional[Decimal] = None,
        diferenca: Optional[Decimal] = None,
    ) -> Dict:
        """Cria aprovacao PENDENTE. Idempotente — se ja existe, retorna."""
        from app.carvia.models import CarviaAprovacaoFrete, CarviaFrete

        frete = db.session.get(CarviaFrete, frete_id)
        if not frete:
            return {'sucesso': False, 'erro': 'Frete nao encontrado'}

        # Snapshot atual se nao fornecido
        if valor_cotado is None and frete.valor_cotado is not None:
            valor_cotado = Decimal(str(frete.valor_cotado))
        if valor_considerado is None and frete.valor_considerado is not None:
            valor_considerado = Decimal(str(frete.valor_considerado))
        if valor_pago is None and frete.valor_pago is not None:
            valor_pago = Decimal(str(frete.valor_pago))

        # Idempotencia
        existente = CarviaAprovacaoFrete.query.filter_by(
            frete_id=frete_id,
            status='PENDENTE',
        ).with_for_update().first()

        if existente:
            logger.info(
                f"Aprovacao PENDENTE ja existe | frete={frete_id} | "
                f"aprovacao={existente.id}"
            )
            return {
                'sucesso': True,
                'tratativa_aberta': True,
                'aprovacao_id': existente.id,
                'motivo': 'Aprovacao PENDENTE ja existente',
            }

        aprovacao = CarviaAprovacaoFrete(
            frete_id=frete_id,
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
        db.session.flush()

        frete.requer_aprovacao = True

        logger.info(
            f"Aprovacao criada | frete={frete_id} | aprovacao={aprovacao.id} | "
            f"diff={diferenca}"
        )

        return {
            'sucesso': True,
            'tratativa_aberta': True,
            'aprovacao_id': aprovacao.id,
            'motivo': motivo,
        }

    # =================================================================
    # Decisao: APROVAR
    # =================================================================
    def aprovar(
        self,
        aprovacao_id: int,
        lancar_diferenca: bool,
        observacoes: str,
        usuario: str,
    ) -> Dict:
        """Processa decisao APROVADO em uma aprovacao PENDENTE."""
        from app.carvia.models import CarviaAprovacaoFrete, CarviaFrete

        aprovacao = CarviaAprovacaoFrete.query.filter_by(
            id=aprovacao_id
        ).with_for_update().first()

        if not aprovacao:
            return {'sucesso': False, 'erro': 'Aprovacao nao encontrada'}

        if aprovacao.status != 'PENDENTE':
            return {
                'sucesso': False,
                'erro': f'Aprovacao ja finalizada (status={aprovacao.status})',
            }

        try:
            aprovacao.status = 'APROVADO'
            aprovacao.aprovador = usuario
            aprovacao.aprovado_em = agora_utc_naive()
            aprovacao.observacoes_aprovacao = observacoes
            aprovacao.lancar_diferenca = lancar_diferenca

            frete = db.session.get(CarviaFrete, aprovacao.frete_id)
            if frete:
                frete.status_conferencia = 'APROVADO'
                frete.requer_aprovacao = False
                frete.conferido_por = usuario
                frete.conferido_em = agora_utc_naive()

                # Opt-in: lancar em CC se usuario marcou checkbox
                if lancar_diferenca:
                    from app.carvia.services.financeiro.conta_corrente_service import (
                        ContaCorrenteService,
                    )
                    cc_result = ContaCorrenteService.lancar_movimentacao(
                        frete_id=frete.id,
                        descricao=f'Aprovacao #{aprovacao.id}: {aprovacao.motivo_solicitacao[:100]}',
                        usuario=usuario,
                        fatura_transportadora_id=frete.fatura_transportadora_id,
                        observacoes=observacoes,
                    )
                    if not cc_result.get('sucesso'):
                        logger.warning(
                            f"Lancamento CC falhou para aprovacao {aprovacao_id}: "
                            f"{cc_result.get('erro')}"
                        )

            db.session.commit()

            logger.info(
                f"Aprovacao APROVADO | aprovacao={aprovacao_id} | "
                f"frete={aprovacao.frete_id} | lancar_diff={lancar_diferenca}"
            )

            return {
                'sucesso': True,
                'decisao': 'APROVADO',
                'frete_status': frete.status_conferencia if frete else None,
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao aprovar {aprovacao_id}: {e}")
            return {'sucesso': False, 'erro': str(e)}

    # =================================================================
    # Decisao: REJEITAR
    # =================================================================
    def rejeitar(
        self,
        aprovacao_id: int,
        observacoes: str,
        usuario: str,
    ) -> Dict:
        """Processa decisao REJEITADO em uma aprovacao PENDENTE."""
        from app.carvia.models import CarviaAprovacaoFrete, CarviaFrete

        aprovacao = CarviaAprovacaoFrete.query.filter_by(
            id=aprovacao_id
        ).with_for_update().first()

        if not aprovacao:
            return {'sucesso': False, 'erro': 'Aprovacao nao encontrada'}

        if aprovacao.status != 'PENDENTE':
            return {
                'sucesso': False,
                'erro': f'Aprovacao ja finalizada (status={aprovacao.status})',
            }

        try:
            aprovacao.status = 'REJEITADO'
            aprovacao.aprovador = usuario
            aprovacao.aprovado_em = agora_utc_naive()
            aprovacao.observacoes_aprovacao = observacoes
            aprovacao.lancar_diferenca = False

            frete = db.session.get(CarviaFrete, aprovacao.frete_id)
            if frete:
                frete.status_conferencia = 'DIVERGENTE'
                frete.requer_aprovacao = False
                frete.conferido_por = usuario
                frete.conferido_em = agora_utc_naive()

            db.session.commit()

            logger.info(
                f"Aprovacao REJEITADO | aprovacao={aprovacao_id} | "
                f"frete={aprovacao.frete_id}"
            )

            return {
                'sucesso': True,
                'decisao': 'REJEITADO',
                'frete_status': frete.status_conferencia if frete else None,
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao rejeitar {aprovacao_id}: {e}")
            return {'sucesso': False, 'erro': str(e)}

    # =================================================================
    # Listagem de PENDENTES
    # =================================================================
    def listar_pendentes(
        self,
        transportadora: Optional[str] = None,
        cte_numero: Optional[str] = None,
        nf_numero: Optional[str] = None,
    ) -> List:
        """Lista tratativas PENDENTE com filtros opcionais.

        Retorna lista de tuplas (aprovacao, frete) para uso em templates.
        """
        from app.carvia.models import CarviaAprovacaoFrete, CarviaFrete

        query = (
            db.session.query(CarviaAprovacaoFrete, CarviaFrete)
            .join(CarviaFrete, CarviaAprovacaoFrete.frete_id == CarviaFrete.id)
            .filter(CarviaAprovacaoFrete.status == 'PENDENTE')
        )

        if transportadora:
            from app.transportadoras.models import Transportadora
            query = query.join(
                Transportadora,
                CarviaFrete.transportadora_id == Transportadora.id,
            ).filter(Transportadora.razao_social.ilike(f'%{transportadora}%'))

        # cte_numero e nf_numero dependem de joins com Sub (que carrega CTe).
        # Mantido opcional — se necessario, iterar frete.subcontratos.
        if cte_numero:
            from app.carvia.models import CarviaSubcontrato
            query = query.join(
                CarviaSubcontrato,
                CarviaSubcontrato.frete_id == CarviaFrete.id,
            ).filter(CarviaSubcontrato.cte_numero.ilike(f'%{cte_numero}%'))

        if nf_numero:
            query = query.filter(CarviaFrete.numeros_nfs.ilike(f'%{nf_numero}%'))

        return query.order_by(
            CarviaAprovacaoFrete.solicitado_em.desc()
        ).all()

    # =================================================================
    # Contagem PENDENTE (para badge em menu)
    # =================================================================
    def contar_pendentes(self) -> int:
        """Retorna quantidade de tratativas PENDENTE."""
        from app.carvia.models import CarviaAprovacaoFrete
        return CarviaAprovacaoFrete.query.filter_by(status='PENDENTE').count()

    # =================================================================
    # Rejeicao em lote (hook de desanexar sub/cancelar)
    # =================================================================
    def rejeitar_pendentes_de_frete(
        self, frete_id: int, motivo: str, usuario: str
    ) -> int:
        """Rejeita silenciosamente todas aprovacoes PENDENTE de um frete.

        Usado em hooks de cancelamento (frete.status='CANCELADO',
        desanexar subcontrato). NAO commita — chamador deve commitar.
        Retorna qtd de rejeicoes aplicadas.
        """
        from app.carvia.models import CarviaAprovacaoFrete, CarviaFrete

        pendentes = CarviaAprovacaoFrete.query.filter_by(
            frete_id=frete_id,
            status='PENDENTE',
        ).all()

        count = 0
        for ap in pendentes:
            ap.status = 'REJEITADO'
            ap.aprovador = usuario
            ap.aprovado_em = agora_utc_naive()
            ap.observacoes_aprovacao = f'Auto-rejeitado: {motivo}'
            ap.lancar_diferenca = False
            count += 1

        if count > 0:
            frete = db.session.get(CarviaFrete, frete_id)
            if frete:
                frete.requer_aprovacao = False

        return count
