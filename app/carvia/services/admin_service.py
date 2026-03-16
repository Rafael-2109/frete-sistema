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
    #  Excluir NF
    # ------------------------------------------------------------------ #

    def excluir_nf(self, nf_id, motivo, executado_por):
        """Hard delete de CarviaNf + cascade (itens, junctions).

        Nullify: FaturaClienteItem.nf_id, FaturaTranspItem.nf_id
        """
        from app.carvia.models import (
            CarviaNf, CarviaNfItem, CarviaOperacaoNf,
            CarviaFaturaClienteItem, CarviaFaturaTransportadoraItem,
        )

        nf = CarviaNf.query.get(nf_id)
        if not nf:
            return {'sucesso': False, 'mensagem': f'NF {nf_id} nao encontrada.'}

        # Serialize
        snapshot = self.serializar_entidade(nf)
        itens = CarviaNfItem.query.filter_by(nf_id=nf_id).all()
        junctions = CarviaOperacaoNf.query.filter_by(nf_id=nf_id).all()
        relacionados = self.serializar_relacionados(nf, {
            'itens': itens,
            'junctions': junctions,
        })

        # Nullify FKs em itens de fatura
        CarviaFaturaClienteItem.query.filter_by(nf_id=nf_id).update(
            {'nf_id': None}, synchronize_session='fetch'
        )
        CarviaFaturaTransportadoraItem.query.filter_by(nf_id=nf_id).update(
            {'nf_id': None}, synchronize_session='fetch'
        )

        # Delete cascade (itens e junctions) — ORM cascade handles itens
        for j in junctions:
            db.session.delete(j)
        for item in itens:
            db.session.delete(item)

        db.session.delete(nf)

        audit = self.registrar_auditoria(
            acao='HARD_DELETE',
            entidade_tipo='CarviaNf',
            entidade_id=nf_id,
            dados_snapshot=snapshot,
            dados_relacionados=relacionados,
            motivo=motivo,
            executado_por=executado_por,
            detalhes={'itens_deletados': len(itens), 'junctions_deletadas': len(junctions)},
        )

        db.session.commit()
        logger.info(f"[ADMIN] NF {nf_id} excluida por {executado_por}. Audit #{audit.id}")

        return {
            'sucesso': True,
            'mensagem': f'NF {snapshot.get("numero_nf")} excluida permanentemente.',
            'auditoria_id': audit.id,
        }

    # ------------------------------------------------------------------ #
    #  Excluir Operacao (CTe CarVia) — Mais complexo
    # ------------------------------------------------------------------ #

    def excluir_operacao(self, operacao_id, motivo, executado_por):
        """Hard delete de CarviaOperacao + cascade seletivo.

        Cascade: OperacaoNf, Subcontratos (se sem fatura_transportadora), CteComplementar*, CustoEntrega*
        Nullify: FaturaClienteItem.operacao_id, FaturaTranspItem.operacao_id
        Revert: FaturaCliente recalc valor se vinculada
        Bloqueio: Subcontrato com fatura_transportadora FATURADO/CONFERIDO
        """
        from app.carvia.models import (
            CarviaOperacao, CarviaOperacaoNf, CarviaSubcontrato,
            CarviaCteComplementar, CarviaCustoEntrega, CarviaCustoEntregaAnexo,
            CarviaFaturaClienteItem, CarviaFaturaTransportadoraItem,
        )

        op = CarviaOperacao.query.get(operacao_id)
        if not op:
            return {'sucesso': False, 'mensagem': f'Operacao {operacao_id} nao encontrada.'}

        # Check bloqueios: subs com fatura transportadora em FATURADO/CONFERIDO
        subs = CarviaSubcontrato.query.filter_by(operacao_id=operacao_id).all()
        subs_bloqueados = [
            s for s in subs
            if s.fatura_transportadora_id and s.status in ('FATURADO', 'CONFERIDO')
        ]
        if subs_bloqueados:
            nomes = [f'Sub #{s.id} (status={s.status})' for s in subs_bloqueados]
            return {
                'sucesso': False,
                'mensagem': (
                    f'Operacao bloqueada: subcontratos com fatura transportadora '
                    f'FATURADO/CONFERIDO: {", ".join(nomes)}. Exclua as faturas primeiro.'
                ),
            }

        # Serialize
        snapshot = self.serializar_entidade(op)
        junctions = CarviaOperacaoNf.query.filter_by(operacao_id=operacao_id).all()
        ctes_comp = CarviaCteComplementar.query.filter_by(operacao_id=operacao_id).all()
        custos = CarviaCustoEntrega.query.filter_by(operacao_id=operacao_id).all()

        relacionados = self.serializar_relacionados(op, {
            'junctions': junctions,
            'subcontratos': subs,
            'ctes_complementares': ctes_comp,
            'custos_entrega': custos,
        })

        # 1. Nullify FKs em itens de fatura
        CarviaFaturaClienteItem.query.filter_by(operacao_id=operacao_id).update(
            {'operacao_id': None}, synchronize_session='fetch'
        )
        CarviaFaturaTransportadoraItem.query.filter_by(operacao_id=operacao_id).update(
            {'operacao_id': None}, synchronize_session='fetch'
        )

        # 2. Delete custos de entrega (com anexos e limpeza financeira)
        for custo in custos:
            self._limpar_movimentacao_financeira('custo_entrega', custo.id)
            anexos = CarviaCustoEntregaAnexo.query.filter_by(custo_entrega_id=custo.id).all()
            for anexo in anexos:
                db.session.delete(anexo)
            db.session.delete(custo)

        # 3. Delete CTe complementares
        for cte_comp in ctes_comp:
            db.session.delete(cte_comp)

        # 4. Delete subcontratos (apenas sem fatura transportadora)
        for sub in subs:
            CarviaFaturaTransportadoraItem.query.filter_by(subcontrato_id=sub.id).update(
                {'subcontrato_id': None}, synchronize_session='fetch'
            )
            db.session.delete(sub)

        # 5. Delete junctions
        for j in junctions:
            db.session.delete(j)

        # 6. Desvincular da fatura cliente se vinculada
        if op.fatura_cliente_id:
            from app.carvia.models import CarviaFaturaCliente
            fatura = CarviaFaturaCliente.query.get(op.fatura_cliente_id)
            if fatura:
                # Recalcular valor da fatura removendo esta operacao
                if op.cte_valor:
                    novo_valor = float(fatura.valor_total or 0) - float(op.cte_valor or 0)
                    fatura.valor_total = max(0, novo_valor)

        db.session.delete(op)

        audit = self.registrar_auditoria(
            acao='HARD_DELETE',
            entidade_tipo='CarviaOperacao',
            entidade_id=operacao_id,
            dados_snapshot=snapshot,
            dados_relacionados=relacionados,
            motivo=motivo,
            executado_por=executado_por,
            detalhes={
                'subs_deletados': len(subs),
                'ctes_comp_deletados': len(ctes_comp),
                'custos_deletados': len(custos),
            },
        )

        db.session.commit()
        logger.info(f"[ADMIN] Operacao {operacao_id} excluida por {executado_por}. Audit #{audit.id}")

        return {
            'sucesso': True,
            'mensagem': f'Operacao #{operacao_id} excluida permanentemente.',
            'auditoria_id': audit.id,
        }

    # ------------------------------------------------------------------ #
    #  Excluir Subcontrato
    # ------------------------------------------------------------------ #

    def excluir_subcontrato(self, sub_id, motivo, executado_por):
        """Hard delete de CarviaSubcontrato.

        Nullify: FaturaTranspItem.subcontrato_id
        Bloqueio: fatura_transportadora_id != NULL
        """
        from app.carvia.models import (
            CarviaSubcontrato, CarviaFaturaTransportadoraItem,
        )

        sub = CarviaSubcontrato.query.get(sub_id)
        if not sub:
            return {'sucesso': False, 'mensagem': f'Subcontrato {sub_id} nao encontrado.'}

        if sub.fatura_transportadora_id:
            return {
                'sucesso': False,
                'mensagem': (
                    f'Subcontrato bloqueado: vinculado a fatura transportadora '
                    f'#{sub.fatura_transportadora_id}. Exclua a fatura primeiro.'
                ),
            }

        snapshot = self.serializar_entidade(sub)

        # Nullify FK em itens de fatura
        CarviaFaturaTransportadoraItem.query.filter_by(subcontrato_id=sub_id).update(
            {'subcontrato_id': None}, synchronize_session='fetch'
        )

        db.session.delete(sub)

        audit = self.registrar_auditoria(
            acao='HARD_DELETE',
            entidade_tipo='CarviaSubcontrato',
            entidade_id=sub_id,
            dados_snapshot=snapshot,
            motivo=motivo,
            executado_por=executado_por,
        )

        db.session.commit()
        logger.info(f"[ADMIN] Subcontrato {sub_id} excluido por {executado_por}. Audit #{audit.id}")

        return {
            'sucesso': True,
            'mensagem': f'Subcontrato #{sub_id} excluido permanentemente.',
            'auditoria_id': audit.id,
        }

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
    #  Excluir CTe Complementar
    # ------------------------------------------------------------------ #

    def excluir_cte_complementar(self, cte_comp_id, motivo, executado_por):
        """Hard delete de CarviaCteComplementar + cascade (custos entrega filhos).

        Recalc fatura se vinculada.
        Bloqueio: status=FATURADO (deve desvincular fatura primeiro)
        """
        from app.carvia.models import (
            CarviaCteComplementar, CarviaCustoEntrega, CarviaCustoEntregaAnexo,
            CarviaFaturaCliente,
        )

        cte_comp = CarviaCteComplementar.query.get(cte_comp_id)
        if not cte_comp:
            return {'sucesso': False, 'mensagem': f'CTe Complementar {cte_comp_id} nao encontrado.'}

        if cte_comp.status == 'FATURADO':
            return {
                'sucesso': False,
                'mensagem': (
                    'CTe Complementar bloqueado: status FATURADO. '
                    'Exclua a fatura cliente vinculada primeiro.'
                ),
            }

        snapshot = self.serializar_entidade(cte_comp)

        # Cascade: custos de entrega vinculados
        custos = CarviaCustoEntrega.query.filter_by(cte_complementar_id=cte_comp_id).all()
        relacionados = self.serializar_relacionados(cte_comp, {'custos_entrega': custos})

        for custo in custos:
            self._limpar_movimentacao_financeira('custo_entrega', custo.id)
            anexos = CarviaCustoEntregaAnexo.query.filter_by(custo_entrega_id=custo.id).all()
            for anexo in anexos:
                db.session.delete(anexo)
            db.session.delete(custo)

        # Recalc fatura se vinculada
        if cte_comp.fatura_cliente_id:
            fatura = CarviaFaturaCliente.query.get(cte_comp.fatura_cliente_id)
            if fatura and cte_comp.cte_valor:
                novo_valor = float(fatura.valor_total or 0) - float(cte_comp.cte_valor or 0)
                fatura.valor_total = max(0, novo_valor)

        db.session.delete(cte_comp)

        audit = self.registrar_auditoria(
            acao='HARD_DELETE',
            entidade_tipo='CarviaCteComplementar',
            entidade_id=cte_comp_id,
            dados_snapshot=snapshot,
            dados_relacionados=relacionados,
            motivo=motivo,
            executado_por=executado_por,
            detalhes={'custos_deletados': len(custos)},
        )

        db.session.commit()
        logger.info(
            f"[ADMIN] CTe Complementar {cte_comp_id} excluido por {executado_por}. "
            f"Audit #{audit.id}"
        )

        return {
            'sucesso': True,
            'mensagem': f'CTe Complementar #{cte_comp_id} excluido permanentemente.',
            'auditoria_id': audit.id,
        }

    # ------------------------------------------------------------------ #
    #  Excluir Custo Entrega
    # ------------------------------------------------------------------ #

    def excluir_custo_entrega(self, custo_id, motivo, executado_por):
        """Hard delete de CarviaCustoEntrega + cascade (anexos).

        Bloqueio: status=PAGO
        Limpar: ContaMovimentacao + Conciliacao
        """
        from app.carvia.models import CarviaCustoEntrega, CarviaCustoEntregaAnexo

        custo = CarviaCustoEntrega.query.get(custo_id)
        if not custo:
            return {'sucesso': False, 'mensagem': f'Custo Entrega {custo_id} nao encontrado.'}

        if custo.status == 'PAGO':
            return {
                'sucesso': False,
                'mensagem': 'Custo bloqueado: status PAGO. Desfaca o pagamento primeiro.',
            }

        snapshot = self.serializar_entidade(custo)
        anexos = CarviaCustoEntregaAnexo.query.filter_by(custo_entrega_id=custo_id).all()
        relacionados = self.serializar_relacionados(custo, {'anexos': anexos})

        # Limpeza financeira
        self._limpar_movimentacao_financeira('custo_entrega', custo_id)

        for anexo in anexos:
            db.session.delete(anexo)

        db.session.delete(custo)

        audit = self.registrar_auditoria(
            acao='HARD_DELETE',
            entidade_tipo='CarviaCustoEntrega',
            entidade_id=custo_id,
            dados_snapshot=snapshot,
            dados_relacionados=relacionados,
            motivo=motivo,
            executado_por=executado_por,
            detalhes={'anexos_deletados': len(anexos)},
        )

        db.session.commit()
        logger.info(
            f"[ADMIN] Custo Entrega {custo_id} excluido por {executado_por}. "
            f"Audit #{audit.id}"
        )

        return {
            'sucesso': True,
            'mensagem': f'Custo Entrega #{custo_id} excluido permanentemente.',
            'auditoria_id': audit.id,
        }

    # ------------------------------------------------------------------ #
    #  Excluir Despesa
    # ------------------------------------------------------------------ #

    def excluir_despesa(self, despesa_id, motivo, executado_por):
        """Hard delete de CarviaDespesa.

        Bloqueio: status=PAGO
        Limpar: ContaMovimentacao + Conciliacao
        """
        from app.carvia.models import CarviaDespesa

        despesa = CarviaDespesa.query.get(despesa_id)
        if not despesa:
            return {'sucesso': False, 'mensagem': f'Despesa {despesa_id} nao encontrada.'}

        if despesa.status == 'PAGO':
            return {
                'sucesso': False,
                'mensagem': 'Despesa bloqueada: status PAGO. Desfaca o pagamento primeiro.',
            }

        snapshot = self.serializar_entidade(despesa)

        # Limpeza financeira
        self._limpar_movimentacao_financeira('despesa', despesa_id)

        db.session.delete(despesa)

        audit = self.registrar_auditoria(
            acao='HARD_DELETE',
            entidade_tipo='CarviaDespesa',
            entidade_id=despesa_id,
            dados_snapshot=snapshot,
            motivo=motivo,
            executado_por=executado_por,
        )

        db.session.commit()
        logger.info(
            f"[ADMIN] Despesa {despesa_id} excluida por {executado_por}. "
            f"Audit #{audit.id}"
        )

        return {
            'sucesso': True,
            'mensagem': f'Despesa #{despesa_id} excluida permanentemente.',
            'auditoria_id': audit.id,
        }

    # ------------------------------------------------------------------ #
    #  Listar Auditoria
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Edicao Completa (Fase 4)
    # ------------------------------------------------------------------ #

    # Mapeamento tipo URL → model class
    _TIPO_MODEL_MAP = {
        'nf': 'CarviaNf',
        'operacao': 'CarviaOperacao',
        'subcontrato': 'CarviaSubcontrato',
        'fatura-cliente': 'CarviaFaturaCliente',
        'fatura-transportadora': 'CarviaFaturaTransportadora',
        'cte-complementar': 'CarviaCteComplementar',
        'custo-entrega': 'CarviaCustoEntrega',
        'despesa': 'CarviaDespesa',
    }

    def _get_model_class(self, tipo):
        """Retorna a classe do model pelo tipo URL."""
        import app.carvia.models as models
        model_name = self._TIPO_MODEL_MAP.get(tipo)
        if not model_name:
            return None
        return getattr(models, model_name, None)

    def obter_campos_editaveis(self, tipo, entity):
        """Retorna lista de campos editaveis para o formulario generico.

        Cada campo: {name, label, tipo, valor, col, readonly, opcoes, step, maxlength}
        """
        snapshot = self.serializar_entidade(entity)
        campos = []

        # Campos comuns ignorados (auto-gerenciados)
        SKIP = {'id', 'criado_em', 'criado_por', 'atualizado_em'}

        for col in entity.__table__.columns:
            if col.name in SKIP:
                continue

            campo_def = {
                'name': col.name,
                'label': col.name.replace('_', ' ').title(),
                'valor': snapshot.get(col.name),
                'col': 6,
            }

            # Determinar tipo do input
            col_type = str(col.type)
            if 'DATE' in col_type and 'TIME' not in col_type:
                campo_def['tipo'] = 'date'
            elif 'NUMERIC' in col_type or 'FLOAT' in col_type or 'INTEGER' in col_type:
                campo_def['tipo'] = 'number'
                if 'NUMERIC' in col_type:
                    campo_def['step'] = '0.01'
                else:
                    campo_def['step'] = '1'
            elif 'TEXT' in col_type:
                campo_def['tipo'] = 'textarea'
            elif 'BOOLEAN' in col_type:
                campo_def['tipo'] = 'select'
                campo_def['opcoes'] = [('True', 'Sim'), ('False', 'Nao')]
                campo_def['valor'] = str(campo_def['valor']) if campo_def['valor'] is not None else ''
            elif col.name == 'status' or col.name.startswith('status_'):
                campo_def['tipo'] = 'text'
            else:
                campo_def['tipo'] = 'text'

            # PK e campos readonly
            if col.primary_key:
                campo_def['readonly'] = True
                campo_def['col'] = 3

            campos.append(campo_def)

        return campos

    def editar_entidade(self, tipo, entity_id, campos_form, motivo, executado_por):
        """Aplica edicoes a uma entidade existente com auditoria.

        Args:
            tipo: tipo URL (nf, operacao, etc.)
            entity_id: ID da entidade
            campos_form: dict {campo: valor} do formulario
            motivo: texto do motivo
            executado_por: email do admin

        Returns:
            dict {sucesso, mensagem, auditoria_id}
        """
        ModelClass = self._get_model_class(tipo)
        if not ModelClass:
            return {'sucesso': False, 'mensagem': f'Tipo invalido: {tipo}'}

        entity = ModelClass.query.get(entity_id)
        if not entity:
            return {'sucesso': False, 'mensagem': f'{tipo} #{entity_id} nao encontrado.'}

        # Snapshot antes
        snapshot_antes = self.serializar_entidade(entity)

        # Aplicar alteracoes
        alteracoes = {}
        for col in entity.__table__.columns:
            if col.name in ('id', 'criado_em', 'criado_por', 'atualizado_em'):
                continue
            if col.primary_key:
                continue
            if col.name not in campos_form:
                continue

            novo_valor = campos_form[col.name]
            valor_atual = getattr(entity, col.name)

            # Converter tipos
            col_type = str(col.type)
            if novo_valor == '' or novo_valor is None:
                novo_valor_convertido = None
            elif 'INTEGER' in col_type:
                novo_valor_convertido = int(novo_valor) if novo_valor else None
            elif 'NUMERIC' in col_type or 'FLOAT' in col_type:
                novo_valor_convertido = float(str(novo_valor).replace(',', '.')) if novo_valor else None
            elif 'BOOLEAN' in col_type:
                novo_valor_convertido = str(novo_valor).lower() in ('true', '1', 'sim')
            elif 'DATE' in col_type and 'TIME' not in col_type:
                from datetime import date as date_cls
                if isinstance(novo_valor, str) and novo_valor:
                    novo_valor_convertido = date_cls.fromisoformat(novo_valor)
                else:
                    novo_valor_convertido = None
            else:
                novo_valor_convertido = str(novo_valor) if novo_valor else None

            # Comparar (converte para string para simplificar)
            val_atual_str = str(valor_atual) if valor_atual is not None else ''
            val_novo_str = str(novo_valor_convertido) if novo_valor_convertido is not None else ''
            if val_atual_str != val_novo_str:
                setattr(entity, col.name, novo_valor_convertido)
                alteracoes[col.name] = {
                    'antes': snapshot_antes.get(col.name),
                    'depois': novo_valor_convertido if not isinstance(novo_valor_convertido, (date, datetime)) else str(novo_valor_convertido),
                }

        if not alteracoes:
            return {'sucesso': False, 'mensagem': 'Nenhuma alteracao detectada.'}

        audit = self.registrar_auditoria(
            acao='FIELD_EDIT',
            entidade_tipo=type(entity).__name__,
            entidade_id=entity_id,
            dados_snapshot=snapshot_antes,
            motivo=motivo,
            executado_por=executado_por,
            detalhes={'alteracoes': alteracoes},
        )

        db.session.commit()
        logger.info(
            f"[ADMIN] Editou {tipo} #{entity_id}: "
            f"{len(alteracoes)} campos alterados por {executado_por}. Audit #{audit.id}"
        )

        return {
            'sucesso': True,
            'mensagem': f'{len(alteracoes)} campo(s) alterado(s) com sucesso.',
            'auditoria_id': audit.id,
        }

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
