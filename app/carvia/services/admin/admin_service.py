"""
Admin Service CarVia — Exclusao, auditoria e correcao de dados
================================================================

Operacoes administrativas de hard delete com auditoria completa.
Cada metodo segue o padrao:
1. Load + validate preconditions (bloqueios)
2. Serialize entity + children → JSON snapshot
3. Clean relationships (nullify FKs, revert statuses, financial cleanup)
4. db.session.delete(entity)
5. Create CarviaAdminAudit
6. db.session.commit() (single transaction)
7. Return {sucesso: True, mensagem: '...', auditoria_id: N}
"""

import logging
from datetime import date, datetime
from decimal import Decimal

from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class AdminService:
    """Service para operacoes administrativas no modulo CarVia."""

    # ------------------------------------------------------------------ #
    #  Serializacao
    # ------------------------------------------------------------------ #

    @staticmethod
    def serializar_entidade(entity):
        """Converte model SQLAlchemy para dict JSON-safe (todas as colunas)."""
        result = {}
        for col in entity.__table__.columns:
            val = getattr(entity, col.name, None)
            if isinstance(val, Decimal):
                val = float(val)
            elif isinstance(val, (datetime, date)):
                val = val.isoformat()
            result[col.name] = val
        return result

    @staticmethod
    def serializar_relacionados(_entity, relacoes):
        """Serializa filhos/relacionados de uma entidade.

        Args:
            _entity: model pai (reservado para uso futuro)
            relacoes: dict {nome: query_or_list} de relacionamentos a serializar

        Returns:
            dict com listas de dicts serializados por tipo
        """
        resultado = {}
        for nome, items in relacoes.items():
            if hasattr(items, 'all'):
                items = items.all()
            elif callable(items):
                items = items()
            serialized = []
            for item in (items or []):
                serialized.append(AdminService.serializar_entidade(item))
            if serialized:
                resultado[nome] = serialized
        return resultado

    # ------------------------------------------------------------------ #
    #  Auditoria
    # ------------------------------------------------------------------ #

    @staticmethod
    def registrar_auditoria(acao, entidade_tipo, entidade_id, dados_snapshot,
                            motivo, executado_por, dados_relacionados=None,
                            detalhes=None):
        """Cria registro de auditoria."""
        from app.carvia.models import CarviaAdminAudit

        audit = CarviaAdminAudit(
            acao=acao,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            dados_snapshot=dados_snapshot,
            dados_relacionados=dados_relacionados,
            motivo=motivo,
            executado_por=executado_por,
            executado_em=agora_utc_naive(),
            detalhes=detalhes,
        )
        db.session.add(audit)
        return audit

    # ------------------------------------------------------------------ #
    #  Limpeza Financeira
    # ------------------------------------------------------------------ #

    @staticmethod
    def _limpar_movimentacao_financeira(tipo_doc, doc_id):
        """Remove ContaMovimentacao + Conciliacoes vinculadas a um documento.

        Recalcula total_conciliado e status_conciliacao nas linhas de extrato afetadas.
        """
        from app.carvia.models import CarviaContaMovimentacao, CarviaConciliacao

        # 1. Remover movimentacao financeira
        mov = CarviaContaMovimentacao.query.filter_by(
            tipo_doc=tipo_doc, doc_id=doc_id
        ).first()
        if mov:
            db.session.delete(mov)

        # 2. Remover conciliacoes e recalcular extrato
        conciliacoes = CarviaConciliacao.query.filter_by(
            tipo_documento=tipo_doc, documento_id=doc_id
        ).all()

        extrato_ids_afetados = set()
        for conc in conciliacoes:
            extrato_ids_afetados.add(conc.extrato_linha_id)
            db.session.delete(conc)

        # Flush para que as conciliacoes deletadas nao interfiram no recalculo
        db.session.flush()

        # Recalcular total_conciliado nas linhas de extrato afetadas
        if extrato_ids_afetados:
            from app.carvia.models import CarviaExtratoLinha
            from sqlalchemy import func

            for extrato_id in extrato_ids_afetados:
                linha = CarviaExtratoLinha.query.get(extrato_id)
                if not linha:
                    continue

                total = db.session.query(
                    func.coalesce(func.sum(CarviaConciliacao.valor_alocado), 0)
                ).filter(
                    CarviaConciliacao.extrato_linha_id == extrato_id
                ).scalar()

                linha.total_conciliado = total
                valor_abs = abs(float(linha.valor or 0))
                if float(total) >= valor_abs:
                    linha.status_conciliacao = 'CONCILIADO'
                elif float(total) > 0:
                    linha.status_conciliacao = 'PARCIAL'
                else:
                    linha.status_conciliacao = 'PENDENTE'

    # ------------------------------------------------------------------ #
    #  REMOVIDOS (Sprint 0 — CRITICO + MEDIO):
    #    - excluir_nf (CRITICO: sem guards)
    #    - excluir_operacao (MEDIO: bypass CarviaFrete, CTe Comp, CE)
    #    - excluir_subcontrato (MEDIO: bypass CarviaFrete)
    #
    #  Motivo: essas rotas bypassavam guards de rotas normais e quebravam
    #  integridade do fluxo unidirecional. Para corrigir dados, use:
    #  1. Desconciliar (se conciliado)
    #  2. Reabrir fatura conferida
    #  3. Desanexar de faturas
    #  4. Cancelar dependencias (CTe Comp, CustoEntrega, Subs)
    #  5. Cancelar a entidade principal (soft-delete via status=CANCELADO)
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Excluir Fatura Cliente
    # ------------------------------------------------------------------ #

    def excluir_fatura_cliente(self, fatura_id, motivo, executado_por):
        """Hard delete de CarviaFaturaCliente + cascade (itens).

        Revert: Operacoes → CONFIRMADO, CteComp → EMITIDO
        Nullify: Operacao.fatura_cliente_id, CteComp.fatura_cliente_id
        Bloqueio: conciliado=True
        Limpar: ContaMovimentacao + Conciliacao
        """
        from app.carvia.models import (
            CarviaFaturaCliente, CarviaFaturaClienteItem,
            CarviaOperacao, CarviaCteComplementar,
        )

        fatura = CarviaFaturaCliente.query.get(fatura_id)
        if not fatura:
            return {'sucesso': False, 'mensagem': f'Fatura cliente {fatura_id} nao encontrada.'}

        if getattr(fatura, 'conciliado', False):
            return {
                'sucesso': False,
                'mensagem': 'Fatura bloqueada: ja esta conciliada. Desfaca a conciliacao primeiro.',
            }

        snapshot = self.serializar_entidade(fatura)
        itens = CarviaFaturaClienteItem.query.filter_by(fatura_cliente_id=fatura_id).all()
        relacionados = self.serializar_relacionados(fatura, {'itens': itens})

        # 1. Revert operacoes vinculadas → CONFIRMADO
        ops_vinculadas = CarviaOperacao.query.filter_by(fatura_cliente_id=fatura_id).all()
        for op in ops_vinculadas:
            op.fatura_cliente_id = None
            if op.status == 'FATURADO':
                op.status = 'CONFIRMADO'

        # 2. Revert CTe complementares → EMITIDO
        ctes_comp = CarviaCteComplementar.query.filter_by(fatura_cliente_id=fatura_id).all()
        for cte_comp in ctes_comp:
            cte_comp.fatura_cliente_id = None
            if cte_comp.status == 'FATURADO':
                cte_comp.status = 'EMITIDO'

        # 3. Limpeza financeira
        self._limpar_movimentacao_financeira('fatura_cliente', fatura_id)

        # 4. Delete itens (DB CASCADE faria, mas explicito para auditoria)
        for item in itens:
            db.session.delete(item)

        db.session.delete(fatura)

        audit = self.registrar_auditoria(
            acao='HARD_DELETE',
            entidade_tipo='CarviaFaturaCliente',
            entidade_id=fatura_id,
            dados_snapshot=snapshot,
            dados_relacionados=relacionados,
            motivo=motivo,
            executado_por=executado_por,
            detalhes={
                'itens_deletados': len(itens),
                'ops_revertidas': len(ops_vinculadas),
                'ctes_comp_revertidos': len(ctes_comp),
            },
        )

        db.session.commit()
        logger.info(f"[ADMIN] Fatura cliente {fatura_id} excluida por {executado_por}. Audit #{audit.id}")

        return {
            'sucesso': True,
            'mensagem': f'Fatura {snapshot.get("numero_fatura")} excluida permanentemente.',
            'auditoria_id': audit.id,
        }

    # ------------------------------------------------------------------ #
    #  Excluir Fatura Transportadora
    # ------------------------------------------------------------------ #

    def excluir_fatura_transportadora(self, fatura_id, motivo, executado_por):
        """Hard delete de CarviaFaturaTransportadora + cascade (itens).

        Revert: Subcontratos → CONFIRMADO, fatura_transportadora_id = NULL
        Bloqueio: conciliado (total_conciliado > 0 e conciliado em CarviaConciliacao)
        Limpar: ContaMovimentacao + Conciliacao
        """
        from app.carvia.models import (
            CarviaFaturaTransportadora, CarviaFaturaTransportadoraItem,
            CarviaSubcontrato, CarviaConciliacao,
        )

        fatura = CarviaFaturaTransportadora.query.get(fatura_id)
        if not fatura:
            return {'sucesso': False, 'mensagem': f'Fatura transportadora {fatura_id} nao encontrada.'}

        # Verificar conciliacao
        conc_count = CarviaConciliacao.query.filter_by(
            tipo_documento='fatura_transportadora', documento_id=fatura_id
        ).count()
        if conc_count > 0:
            return {
                'sucesso': False,
                'mensagem': 'Fatura bloqueada: possui conciliacoes bancarias. Desfaca primeiro.',
            }

        snapshot = self.serializar_entidade(fatura)
        itens = CarviaFaturaTransportadoraItem.query.filter_by(
            fatura_transportadora_id=fatura_id
        ).all()
        relacionados = self.serializar_relacionados(fatura, {'itens': itens})

        # 1. Revert subcontratos → CONFIRMADO
        subs = CarviaSubcontrato.query.filter_by(fatura_transportadora_id=fatura_id).all()
        for sub in subs:
            sub.fatura_transportadora_id = None
            if sub.status == 'FATURADO':
                sub.status = 'CONFIRMADO'

        # 2. Limpeza financeira
        self._limpar_movimentacao_financeira('fatura_transportadora', fatura_id)

        # 3. Delete itens
        for item in itens:
            db.session.delete(item)

        db.session.delete(fatura)

        audit = self.registrar_auditoria(
            acao='HARD_DELETE',
            entidade_tipo='CarviaFaturaTransportadora',
            entidade_id=fatura_id,
            dados_snapshot=snapshot,
            dados_relacionados=relacionados,
            motivo=motivo,
            executado_por=executado_por,
            detalhes={
                'itens_deletados': len(itens),
                'subs_revertidos': len(subs),
            },
        )

        db.session.commit()
        logger.info(
            f"[ADMIN] Fatura transportadora {fatura_id} excluida por {executado_por}. "
            f"Audit #{audit.id}"
        )

        return {
            'sucesso': True,
            'mensagem': f'Fatura {snapshot.get("numero_fatura")} excluida permanentemente.',
            'auditoria_id': audit.id,
        }

    # ------------------------------------------------------------------ #
    #  REMOVIDOS (Sprint 0 — MEDIO):
    #    - excluir_cte_complementar (cascade sem guards)
    #    - excluir_custo_entrega (bypass CTe Comp vinculado)
    #    - excluir_despesa (bypass COMISSAO vinculada a Fechamento)
    #
    #  Para remover estas entidades, use o fluxo normal: status=CANCELADO.
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Excluir Receita
    # ------------------------------------------------------------------ #

    def excluir_receita(self, receita_id, motivo, executado_por):
        """Hard delete de CarviaReceita.

        Bloqueio: status=RECEBIDO
        Limpar: ContaMovimentacao + Conciliacao
        """
        from app.carvia.models import CarviaReceita

        receita = CarviaReceita.query.get(receita_id)
        if not receita:
            return {'sucesso': False, 'mensagem': f'Receita {receita_id} nao encontrada.'}

        if receita.status == 'RECEBIDO':
            return {
                'sucesso': False,
                'mensagem': 'Receita bloqueada: status RECEBIDO. Desfaca o recebimento primeiro.',
            }

        snapshot = self.serializar_entidade(receita)

        # Limpeza financeira
        self._limpar_movimentacao_financeira('receita', receita_id)

        db.session.delete(receita)

        audit = self.registrar_auditoria(
            acao='HARD_DELETE',
            entidade_tipo='CarviaReceita',
            entidade_id=receita_id,
            dados_snapshot=snapshot,
            motivo=motivo,
            executado_por=executado_por,
        )

        db.session.commit()
        logger.info(
            f"[ADMIN] Receita {receita_id} excluida por {executado_por}. "
            f"Audit #{audit.id}"
        )

        return {
            'sucesso': True,
            'mensagem': f'Receita #{receita_id} excluida permanentemente.',
            'auditoria_id': audit.id,
        }

    # ------------------------------------------------------------------ #
    #  Excluir Subcontrato Orfao (Legado pre-CarviaFrete)
    # ------------------------------------------------------------------ #

    def excluir_subcontrato_orfao(self, sub_id, motivo, executado_por):
        """Hard delete de CarviaSubcontrato que NAO pertence ao fluxo novo.

        Escopo: subcontratos criados antes do fluxo unificado
        (portaria -> CarviaFrete -> CarviaSubcontrato) via importacao direta
        de CTe XML. Caracterizados por `frete_id IS NULL` e
        `fatura_transportadora_id IS NULL`.

        ===================================================================
        GUARDS (qualquer um bloqueia o delete):
        ===================================================================
        Estes guards juntos garantem que nenhuma conciliacao bancaria pode
        existir vinculada (direta ou indiretamente) a este subcontrato — o
        sub esta totalmente desconectado do extrato bancario.

          1. frete_id IS NOT NULL
             — sub pertence ao fluxo atual via CarviaFrete; nao e legado
          2. fatura_transportadora_id IS NOT NULL
             — sub esta em fatura; a fatura PODE estar conciliada com extrato
             (CarviaConciliacao.tipo_documento='fatura_transportadora')
          3. status IN ('FATURADO', 'CONFERIDO')
             — estado terminal, indica fluxo completo
          4. CarviaFaturaTransportadoraItem.subcontrato_id aponta
             — defesa em profundidade: caso o item exista mesmo sem fatura
          5. CarviaCustoEntrega.subcontrato_id aponta (LEGADO — pre-FK direta)
             — CEs agora usam CarviaCustoEntrega.fatura_transportadora_id direto
             (padrao DespesaExtra.fatura_frete_id do Nacom). O check de sub_id
             permanece como defesa em profundidade ate a migration destructive.
          6. CarviaFrete.subcontrato_id legado aponta
             — caso historico de FK legado pre-frete_id

        ===================================================================
        DESCONCILIACAO (extrato bancario):
        ===================================================================
        Defensivo: o modelo CarviaConciliacao em uso atualmente NAO suporta
        tipo_documento='subcontrato' (so fatura_cliente, fatura_transportadora,
        despesa, custo_entrega, receita). Mas tratamos o caso historico via
        _limpar_movimentacao_financeira('subcontrato', sub_id), que:
          - Remove CarviaContaMovimentacao(tipo_doc='subcontrato', doc_id=sub_id)
          - Remove CarviaConciliacao(tipo_documento='subcontrato', documento_id=sub_id)
          - Recalcula CarviaExtratoLinha.total_conciliado e status_conciliacao

        ===================================================================
        LIMPEZA DE FKS TECNICAS (NAO eh desconciliacao):
        ===================================================================
        Tabelas com FK direta para carvia_subcontratos.id que precisam sair
        ANTES do delete (FK NOT NULL ou sem ON DELETE CASCADE):

          a. CarviaContaCorrenteTransportadora (subcontrato_id legado,
             nullable pos-Phase 5) — DELETE registros + reverter compensacoes
             apontando via compensacao_subcontrato_id (caso borda)

        Nota (Phase C 2026-04-14): CarviaAprovacaoFrete agora aponta para
        CarviaFrete.id, nao mais para CarviaSubcontrato.id. Subs orfaos
        legados (sem frete_id) nao tem aprovacoes apontando.

        Auditoria: CarviaAdminAudit com snapshot + dados_relacionados.
        """
        from app.carvia.models import (
            CarviaSubcontrato,
            CarviaFaturaTransportadoraItem,
            CarviaCustoEntrega,
            CarviaFrete,
            CarviaContaCorrenteTransportadora,
            CarviaConciliacao,
        )

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            return {'sucesso': False, 'mensagem': f'Subcontrato {sub_id} nao encontrado.'}

        # ============================================================
        # GUARDS — bloqueiam exclusao (qualquer um interrompe)
        # ============================================================
        if sub.frete_id is not None:
            return {
                'sucesso': False,
                'mensagem': (
                    f'Subcontrato #{sub_id} faz parte do fluxo atual '
                    f'(CarviaFrete #{sub.frete_id}). Use o fluxo normal '
                    f'(cancelar via status).'
                ),
            }

        if sub.fatura_transportadora_id is not None:
            return {
                'sucesso': False,
                'mensagem': (
                    f'Subcontrato #{sub_id} esta vinculado a Fatura Transportadora '
                    f'#{sub.fatura_transportadora_id}. Desanexe a fatura primeiro '
                    f'(a fatura pode estar conciliada com o extrato bancario).'
                ),
            }

        if sub.status in ('FATURADO', 'CONFERIDO'):
            return {
                'sucesso': False,
                'mensagem': (
                    f'Subcontrato #{sub_id} esta em status {sub.status}, '
                    f'incompativel com exclusao legada.'
                ),
            }

        itens_fat = CarviaFaturaTransportadoraItem.query.filter_by(
            subcontrato_id=sub_id
        ).count()
        if itens_fat > 0:
            return {
                'sucesso': False,
                'mensagem': (
                    f'Subcontrato #{sub_id} tem {itens_fat} itens de Fatura '
                    f'Transportadora apontando. Remova a vinculacao antes.'
                ),
            }

        custos_vinc = CarviaCustoEntrega.query.filter_by(subcontrato_id=sub_id).count()
        if custos_vinc > 0:
            return {
                'sucesso': False,
                'mensagem': (
                    f'Subcontrato #{sub_id} tem {custos_vinc} Custos de Entrega '
                    f'vinculados (CE pode estar conciliado com extrato). '
                    f'Reatribua os custos antes de excluir.'
                ),
            }

        fretes_legado = CarviaFrete.query.filter_by(subcontrato_id=sub_id).count()
        if fretes_legado > 0:
            return {
                'sucesso': False,
                'mensagem': (
                    f'Subcontrato #{sub_id} tem {fretes_legado} CarviaFrete (legado) '
                    f'apontando via subcontrato_id. Inconsistencia — nao excluir.'
                ),
            }

        # Defesa em profundidade: bloqueia se houver conciliacao historica
        # com tipo_documento='subcontrato' (modelo nao gera, mas pode existir
        # via importacao legada ou correcao manual). Bloqueio explicito ao
        # inves de delete silencioso para evitar perda inadvertida.
        conc_historicas = CarviaConciliacao.query.filter_by(
            tipo_documento='subcontrato', documento_id=sub_id
        ).count()
        if conc_historicas > 0:
            return {
                'sucesso': False,
                'mensagem': (
                    f'Subcontrato #{sub_id} tem {conc_historicas} conciliacao(es) '
                    f'historica(s) com extrato bancario (tipo_documento="subcontrato"). '
                    f'Desconcilie via /carvia/conciliacao antes de excluir.'
                ),
            }

        # Phase 14 (2026-04-14): subcontrato_id e compensacao_subcontrato_id foram
        # removidos de CarviaContaCorrenteTransportadora. Registros CC de subs legados
        # (pre-Phase 5) foram migrados para frete_id ou deletados nas phases anteriores.
        # Novos registros CC nunca usaram subcontrato_id (fonte canonica: frete_id).
        # Guard de CC-com-fatura e limpeza de movs/compensacoes via sub_id deixaram
        # de ser necessarios — nenhum registro CC atual aponta para sub por sub_id.

        # ============================================================
        # SNAPSHOT — antes de qualquer mutacao
        # ============================================================
        snapshot = self.serializar_entidade(sub)

        # Listas vazias: pos-Phase 14, nao ha mais CC apontando por subcontrato_id
        movs_cc = []
        compensacoes_apontando = []
        compensacoes_revertidas = 0

        relacionados = self.serializar_relacionados(sub, {
            'movimentacoes_cc': movs_cc,
            'compensacoes_apontando': compensacoes_apontando,
        })

        # ============================================================
        # DESCONCILIACAO — extrato bancario (defensivo)
        # ============================================================
        # Mesmo que conc_historicas == 0 (verificado no guard), executamos
        # _limpar_movimentacao_financeira para garantir limpeza idempotente
        # de CarviaContaMovimentacao(tipo_doc='subcontrato') + qualquer
        # CarviaConciliacao residual + recalculo de status_conciliacao das
        # CarviaExtratoLinha afetadas. Reusa o helper canonico do AdminService.
        self._limpar_movimentacao_financeira('subcontrato', sub_id)

        # Phase C: campos de conferencia (valor_pago, requer_aprovacao, etc.)
        # migrados para CarviaFrete. Sub orfao nao tem esses campos a resetar.

        # ============================================================
        # DELETE do sub
        # ============================================================
        db.session.delete(sub)

        audit = self.registrar_auditoria(
            acao='HARD_DELETE',
            entidade_tipo='CarviaSubcontrato',
            entidade_id=sub_id,
            dados_snapshot=snapshot,
            dados_relacionados=relacionados,
            motivo=motivo,
            executado_por=executado_por,
            detalhes={
                'origem': 'orfao_legado_pre_carviafrete',
                'desconciliacao_extrato': 'limpar_movimentacao_financeira(subcontrato)',
                'movs_cc_deletadas': len(movs_cc),
                'compensacoes_revertidas': compensacoes_revertidas,
                'cte_numero': snapshot.get('cte_numero'),
                'valor_cotado': snapshot.get('valor_cotado'),
            },
        )

        db.session.commit()
        logger.info(
            f"[ADMIN] Subcontrato orfao #{sub_id} ({snapshot.get('cte_numero')}) "
            f"excluido por {executado_por}. CC deletadas: {len(movs_cc)}, "
            f"compensacoes revertidas: {compensacoes_revertidas}. "
            f"Audit #{audit.id}"
        )

        return {
            'sucesso': True,
            'mensagem': (
                f'CTe Subcontrato {snapshot.get("cte_numero") or f"#{sub_id}"} '
                f'excluido permanentemente (orfao legado).'
            ),
            'auditoria_id': audit.id,
        }

    # ------------------------------------------------------------------ #
    #  Listar Auditoria
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Edicao Completa (Fase 4)
    # ------------------------------------------------------------------ #

    # Mapeamento tipo URL → model class
    # Review Sprint 0 MED #4: mapa reduzido para cobrir apenas tipos
    # ativos nas conversoes suportadas (_CONVERSOES_SUPORTADAS abaixo).
    # Tipos removidos (nf, cte-complementar, custo-entrega, despesa, receita)
    # nao sao origem/destino de nenhuma conversao e suas rotas de exclusao
    # foram removidas — mante-los aqui era dead code.
    _TIPO_MODEL_MAP = {
        'operacao': 'CarviaOperacao',
        'subcontrato': 'CarviaSubcontrato',
        'fatura-cliente': 'CarviaFaturaCliente',
        'fatura-transportadora': 'CarviaFaturaTransportadora',
    }

    def _get_model_class(self, tipo):
        """Retorna a classe do model pelo tipo URL."""
        import app.carvia.models as models
        model_name = self._TIPO_MODEL_MAP.get(tipo)
        if not model_name:
            return None
        return getattr(models, model_name, None)

    # ------------------------------------------------------------------ #
    #  REMOVIDOS (Sprint 0 — CRITICO):
    #    - editar_entidade (FIELD_EDIT): bypass TOTAL. Permitia setar
    #      qualquer campo (cte_valor, status, fatura_id) sem respeitar
    #      guards de bloqueio das rotas normais.
    #    - obter_campos_editaveis: helper so usado por editar_entidade.
    #
    #  Para alterar campos, use as rotas especificas da entidade
    #  (ex: operacao_routes.editar_cte_valor) que respeitam os metodos
    #  pode_* do model.
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Re-link NF ↔ CTe (Fase 6.1)
    # ------------------------------------------------------------------ #

    def relink_operacao_nfs(self, operacao_id, nf_ids_vincular, nf_ids_desvincular,
                            motivo, executado_por):
        """Re-vincula/desvincula NFs de uma operacao.

        Args:
            operacao_id: ID da CarviaOperacao
            nf_ids_vincular: list[int] de NF IDs para vincular
            nf_ids_desvincular: list[int] de NF IDs para desvincular
            motivo: texto
            executado_por: email

        Returns:
            dict {sucesso, mensagem, auditoria_id}
        """
        from app.carvia.models import CarviaOperacao, CarviaOperacaoNf, CarviaNf

        op = CarviaOperacao.query.get(operacao_id)
        if not op:
            return {'sucesso': False, 'mensagem': f'Operacao {operacao_id} nao encontrada.'}

        detalhes = {'vinculadas': [], 'desvinculadas': []}

        # Desvincular
        for nf_id in (nf_ids_desvincular or []):
            junction = CarviaOperacaoNf.query.filter_by(
                operacao_id=operacao_id, nf_id=nf_id
            ).first()
            if junction:
                db.session.delete(junction)
                detalhes['desvinculadas'].append(nf_id)

        # Vincular
        for nf_id in (nf_ids_vincular or []):
            nf = CarviaNf.query.get(nf_id)
            if not nf:
                continue
            existing = CarviaOperacaoNf.query.filter_by(
                operacao_id=operacao_id, nf_id=nf_id
            ).first()
            if not existing:
                junction = CarviaOperacaoNf(operacao_id=operacao_id, nf_id=nf_id)
                db.session.add(junction)
                detalhes['vinculadas'].append(nf_id)

        if not detalhes['vinculadas'] and not detalhes['desvinculadas']:
            return {'sucesso': False, 'mensagem': 'Nenhuma alteracao a fazer.'}

        audit = self.registrar_auditoria(
            acao='RELINK',
            entidade_tipo='CarviaOperacao',
            entidade_id=operacao_id,
            dados_snapshot=self.serializar_entidade(op),
            motivo=motivo,
            executado_por=executado_por,
            detalhes=detalhes,
        )

        db.session.commit()
        logger.info(
            f"[ADMIN] Re-link operacao {operacao_id}: "
            f"+{len(detalhes['vinculadas'])} -{len(detalhes['desvinculadas'])} "
            f"por {executado_por}. Audit #{audit.id}"
        )

        total = len(detalhes['vinculadas']) + len(detalhes['desvinculadas'])
        return {
            'sucesso': True,
            'mensagem': f'{total} alteracao(oes) de vinculo realizadas.',
            'auditoria_id': audit.id,
        }

    # ------------------------------------------------------------------ #
    #  Conversao de Tipo (Fase 5)
    # ------------------------------------------------------------------ #

    # Conversoes suportadas: (tipo_origem, tipo_destino)
    _CONVERSOES_SUPORTADAS = {
        ('operacao', 'subcontrato'),
        ('subcontrato', 'operacao'),
        ('fatura-cliente', 'fatura-transportadora'),
        ('fatura-transportadora', 'fatura-cliente'),
    }

    def conversao_suportada(self, tipo_origem, tipo_destino):
        """Verifica se a conversao e suportada."""
        return (tipo_origem, tipo_destino) in self._CONVERSOES_SUPORTADAS

    def obter_mapeamento_conversao(self, tipo_origem, tipo_destino, entity):
        """Retorna campos mapeados para conversao.

        Returns:
            (campos_origem, campos_destino, mapeamento_campos)
        """
        snapshot = self.serializar_entidade(entity)
        campos_origem = []
        for col in entity.__table__.columns:
            campos_origem.append({
                'name': col.name,
                'label': col.name.replace('_', ' ').title(),
                'valor': snapshot.get(col.name),
            })

        # Mapeamento por tipo de conversao
        mapeamento = {}
        campos_destino = []

        if tipo_origem == 'operacao' and tipo_destino == 'subcontrato':
            mapeamento = {
                'cte_numero': 'cte_numero',
                'cte_chave_acesso': 'cte_chave_acesso',
                'cte_valor': 'valor_cotado',
                'cte_data_emissao': 'cte_data_emissao',
                'uf_origem': 'uf_origem',
                'cidade_origem': 'cidade_origem',
                'uf_destino': 'uf_destino',
                'cidade_destino': 'cidade_destino',
                'peso_bruto': 'peso_bruto',
                'peso_cubado': 'peso_cubado',
                'valor_mercadoria': 'valor_mercadoria',
            }
            campos_destino = [
                {'name': 'transportadora_id', 'label': 'Transportadora ID', 'tipo': 'number',
                 'valor': None, 'col': 6, 'obrigatorio': True, 'step': '1'},
                {'name': 'cte_numero', 'label': 'CTe Numero', 'tipo': 'text',
                 'valor': snapshot.get('cte_numero'), 'col': 6},
                {'name': 'valor_cotado', 'label': 'Valor Cotado', 'tipo': 'number',
                 'valor': snapshot.get('cte_valor'), 'col': 6},
                {'name': 'cte_data_emissao', 'label': 'Data Emissao', 'tipo': 'date',
                 'valor': snapshot.get('cte_data_emissao'), 'col': 6},
                {'name': 'uf_origem', 'label': 'UF Origem', 'tipo': 'text',
                 'valor': snapshot.get('uf_origem'), 'col': 3},
                {'name': 'cidade_origem', 'label': 'Cidade Origem', 'tipo': 'text',
                 'valor': snapshot.get('cidade_origem'), 'col': 9},
                {'name': 'uf_destino', 'label': 'UF Destino', 'tipo': 'text',
                 'valor': snapshot.get('uf_destino'), 'col': 3},
                {'name': 'cidade_destino', 'label': 'Cidade Destino', 'tipo': 'text',
                 'valor': snapshot.get('cidade_destino'), 'col': 9},
                {'name': 'peso_bruto', 'label': 'Peso Bruto', 'tipo': 'number',
                 'valor': snapshot.get('peso_bruto'), 'col': 4},
                {'name': 'peso_cubado', 'label': 'Peso Cubado', 'tipo': 'number',
                 'valor': snapshot.get('peso_cubado'), 'col': 4},
                {'name': 'valor_mercadoria', 'label': 'Valor Mercadoria', 'tipo': 'number',
                 'valor': snapshot.get('valor_mercadoria'), 'col': 4},
            ]

        elif tipo_origem == 'fatura-cliente' and tipo_destino == 'fatura-transportadora':
            mapeamento = {
                'numero_fatura': 'numero_fatura',
                'valor_total': 'valor_total',
                'data_emissao': 'data_emissao',
                'vencimento': 'vencimento',
            }
            campos_destino = [
                {'name': 'transportadora_id', 'label': 'Transportadora ID', 'tipo': 'number',
                 'valor': None, 'col': 6, 'obrigatorio': True, 'step': '1'},
                {'name': 'numero_fatura', 'label': 'Numero Fatura', 'tipo': 'text',
                 'valor': snapshot.get('numero_fatura'), 'col': 6},
                {'name': 'valor_total', 'label': 'Valor Total', 'tipo': 'number',
                 'valor': snapshot.get('valor_total'), 'col': 6},
                {'name': 'data_emissao', 'label': 'Data Emissao', 'tipo': 'date',
                 'valor': snapshot.get('data_emissao'), 'col': 6},
                {'name': 'vencimento', 'label': 'Vencimento', 'tipo': 'date',
                 'valor': snapshot.get('vencimento'), 'col': 6},
            ]

        elif tipo_origem == 'fatura-transportadora' and tipo_destino == 'fatura-cliente':
            mapeamento = {
                'numero_fatura': 'numero_fatura',
                'valor_total': 'valor_total',
                'data_emissao': 'data_emissao',
                'vencimento': 'vencimento',
            }
            campos_destino = [
                {'name': 'cnpj_cliente', 'label': 'CNPJ Cliente', 'tipo': 'text',
                 'valor': None, 'col': 6, 'obrigatorio': True},
                {'name': 'nome_cliente', 'label': 'Nome Cliente', 'tipo': 'text',
                 'valor': None, 'col': 6},
                {'name': 'numero_fatura', 'label': 'Numero Fatura', 'tipo': 'text',
                 'valor': snapshot.get('numero_fatura'), 'col': 6},
                {'name': 'valor_total', 'label': 'Valor Total', 'tipo': 'number',
                 'valor': snapshot.get('valor_total'), 'col': 6},
                {'name': 'data_emissao', 'label': 'Data Emissao', 'tipo': 'date',
                 'valor': snapshot.get('data_emissao'), 'col': 6},
                {'name': 'vencimento', 'label': 'Vencimento', 'tipo': 'date',
                 'valor': snapshot.get('vencimento'), 'col': 6},
            ]

        return campos_origem, campos_destino, mapeamento

    def converter_documento(self, tipo_origem, entity_id, tipo_destino,
                            campos_destino_form, motivo, executado_por):
        """Converte uma entidade de um tipo para outro.

        1. Cria entidade nova (tipo destino)
        2. Audita entidade antiga
        3. Deleta entidade antiga
        4. Tudo em single transaction
        """
        OrigemClass = self._get_model_class(tipo_origem)
        DestinoClass = self._get_model_class(tipo_destino)

        if not OrigemClass or not DestinoClass:
            return {'sucesso': False, 'mensagem': 'Tipo origem ou destino invalido.'}

        if not self.conversao_suportada(tipo_origem, tipo_destino):
            return {
                'sucesso': False,
                'mensagem': f'Conversao {tipo_origem} -> {tipo_destino} nao suportada.',
            }

        entity = OrigemClass.query.get(entity_id)
        if not entity:
            return {'sucesso': False, 'mensagem': f'{tipo_origem} #{entity_id} nao encontrado.'}

        snapshot = self.serializar_entidade(entity)

        # Criar nova entidade
        novo = DestinoClass()
        for campo, valor in campos_destino_form.items():
            if hasattr(novo, campo) and valor not in (None, ''):
                col = novo.__table__.columns.get(campo)
                if col is not None:
                    col_type = str(col.type)
                    if 'INTEGER' in col_type:
                        valor = int(valor)
                    elif 'NUMERIC' in col_type or 'FLOAT' in col_type:
                        valor = float(str(valor).replace(',', '.'))
                    elif 'DATE' in col_type and 'TIME' not in col_type:
                        from datetime import date as date_cls
                        if isinstance(valor, str):
                            valor = date_cls.fromisoformat(valor)
                setattr(novo, campo, valor)

        # Campos obrigatorios de auditoria
        if hasattr(novo, 'criado_por'):
            novo.criado_por = executado_por
        if hasattr(novo, 'criado_em'):
            novo.criado_em = agora_utc_naive()
        if hasattr(novo, 'status'):
            novo.status = 'RASCUNHO'
        if hasattr(novo, 'operacao_id') and tipo_origem == 'operacao':
            # Subcontrato precisa de operacao_id — aponta para si mesmo na conversao
            # Na pratica o admin deve ajustar manualmente depois
            pass

        db.session.add(novo)
        db.session.flush()  # Para obter o ID

        # Deletar original
        db.session.delete(entity)

        # Auditoria
        audit = self.registrar_auditoria(
            acao='TYPE_CHANGE',
            entidade_tipo=type(entity).__name__,
            entidade_id=entity_id,
            dados_snapshot=snapshot,
            motivo=motivo,
            executado_por=executado_por,
            detalhes={
                'tipo_destino': tipo_destino,
                'novo_id': novo.id,
                'campos_destino': campos_destino_form,
            },
        )

        db.session.commit()
        logger.info(
            f"[ADMIN] Converteu {tipo_origem} #{entity_id} -> {tipo_destino} #{novo.id} "
            f"por {executado_por}. Audit #{audit.id}"
        )

        return {
            'sucesso': True,
            'mensagem': f'Convertido para {tipo_destino} #{novo.id}.',
            'auditoria_id': audit.id,
            'novo_id': novo.id,
        }

    # ------------------------------------------------------------------ #
    #  Listar Auditoria
    # ------------------------------------------------------------------ #

    def listar_auditoria(self, page=1, per_page=50, acao=None,
                         entidade_tipo=None, executado_por=None):
        """Lista registros de auditoria com paginacao e filtros."""
        from app.carvia.models import CarviaAdminAudit

        query = CarviaAdminAudit.query.order_by(CarviaAdminAudit.executado_em.desc())

        if acao:
            query = query.filter(CarviaAdminAudit.acao == acao)
        if entidade_tipo:
            query = query.filter(CarviaAdminAudit.entidade_tipo == entidade_tipo)
        if executado_por:
            query = query.filter(CarviaAdminAudit.executado_por == executado_por)

        return query.paginate(page=page, per_page=per_page, error_out=False)
