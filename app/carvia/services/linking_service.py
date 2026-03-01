"""
LinkingService — Vinculacao cross-documento CarVia
====================================================

Resolve FKs entre itens de fatura e entidades (operacoes, NFs, subcontratos).
Permite navegacao bidirecional entre os 5 tipos de documento CarVia:
NF, CTe CarVia (Operacao), CTe Subcontrato, Fatura Cliente, Fatura Transportadora.

Metodos:
- vincular_itens_fatura_cliente: resolve operacao_id e nf_id em itens existentes
- criar_itens_fatura_transportadora: gera itens a partir de subcontratos vinculados
- criar_itens_fatura_cliente_from_operacoes: gera itens a partir de operacoes (UI manual)
- resolver_operacao_por_cte: helper de matching cte_numero -> operacao_id
- resolver_nf_por_numero: helper de matching nf_numero -> nf_id
- backfill_todas_faturas: one-time para dados existentes
"""

import logging
import re

from app import db
from sqlalchemy import func, or_

logger = logging.getLogger(__name__)


class LinkingService:
    """Servico de vinculacao cross-documento CarVia."""

    # ------------------------------------------------------------------
    # Resolvers: cte_numero -> operacao_id, nf_numero -> nf_id
    # ------------------------------------------------------------------

    @staticmethod
    def resolver_operacao_por_cte(cte_numero):
        """Resolve cte_numero (string) -> CarviaOperacao.

        Normaliza zeros a esquerda: "00000001" == "1".
        Returns CarviaOperacao ou None.
        """
        if not cte_numero:
            return None

        from app.carvia.models import CarviaOperacao

        cte_norm = cte_numero.lstrip('0') or '0'
        operacao = CarviaOperacao.query.filter(
            func.ltrim(CarviaOperacao.cte_numero, '0') == cte_norm
        ).first()

        return operacao

    @staticmethod
    def resolver_nf_por_numero(nf_numero, contraparte_cnpj=None):
        """Resolve nf_numero (string) -> CarviaNf.

        Match por numero normalizado (sem zeros a esquerda).
        Se contraparte_cnpj fornecido, filtra por emitente OU destinatario.
        Returns CarviaNf ou None.
        """
        if not nf_numero:
            return None

        from app.carvia.models import CarviaNf

        nf_norm = nf_numero.lstrip('0') or '0'
        query = CarviaNf.query.filter(
            func.ltrim(CarviaNf.numero_nf, '0') == nf_norm
        )

        if contraparte_cnpj:
            cnpj_digits = re.sub(r'\D', '', contraparte_cnpj)
            if len(cnpj_digits) >= 14:
                query = query.filter(
                    or_(
                        func.regexp_replace(
                            CarviaNf.cnpj_emitente, '[^0-9]', '', 'g'
                        ) == cnpj_digits,
                        func.regexp_replace(
                            CarviaNf.cnpj_destinatario, '[^0-9]', '', 'g'
                        ) == cnpj_digits,
                    )
                )

        return query.first()

    # ------------------------------------------------------------------
    # vincular_itens_fatura_cliente: resolve FKs em itens existentes
    # ------------------------------------------------------------------

    def vincular_itens_fatura_cliente(self, fatura_id):
        """Resolve operacao_id e nf_id nos itens de uma fatura cliente existente.

        Itera sobre CarviaFaturaClienteItem onde operacao_id ou nf_id sao NULL
        e tenta resolver via cte_numero e nf_numero.

        Returns:
            dict com estatisticas (operacoes_resolvidas, nfs_resolvidas, total_itens)
        """
        from app.carvia.models import CarviaFaturaClienteItem

        itens = CarviaFaturaClienteItem.query.filter_by(
            fatura_cliente_id=fatura_id
        ).all()

        stats = {'operacoes_resolvidas': 0, 'nfs_resolvidas': 0, 'total_itens': len(itens)}

        for item in itens:
            # Resolver operacao_id via cte_numero
            if item.operacao_id is None and item.cte_numero:
                operacao = self.resolver_operacao_por_cte(item.cte_numero)
                if operacao:
                    item.operacao_id = operacao.id
                    stats['operacoes_resolvidas'] += 1
                    logger.info(
                        f"Linking: fat_cli_item={item.id} cte={item.cte_numero} -> op={operacao.id}"
                    )

            # Resolver nf_id via nf_numero + contraparte_cnpj
            if item.nf_id is None and item.nf_numero:
                nf = self.resolver_nf_por_numero(
                    item.nf_numero, item.contraparte_cnpj
                )
                if nf:
                    item.nf_id = nf.id
                    stats['nfs_resolvidas'] += 1
                    logger.info(
                        f"Linking: fat_cli_item={item.id} nf_num={item.nf_numero} -> nf={nf.id}"
                    )

        db.session.flush()
        return stats

    # ------------------------------------------------------------------
    # criar_itens_fatura_transportadora: gera itens a partir de subcontratos
    # ------------------------------------------------------------------

    def criar_itens_fatura_transportadora(self, fatura_id):
        """Gera CarviaFaturaTransportadoraItem a partir dos subcontratos vinculados.

        Para cada subcontrato da fatura, cria 1 item com todas as FKs populadas.

        Returns:
            int — numero de itens criados
        """
        from app.carvia.models import (
            CarviaFaturaTransportadora, CarviaFaturaTransportadoraItem,
            CarviaSubcontrato, CarviaOperacaoNf
        )

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            logger.warning(f"Fatura transportadora {fatura_id} nao encontrada")
            return 0

        # Buscar subcontratos vinculados a esta fatura
        subcontratos = CarviaSubcontrato.query.filter_by(
            fatura_transportadora_id=fatura_id
        ).all()

        if not subcontratos:
            logger.info(f"Fatura transportadora {fatura_id}: nenhum subcontrato vinculado")
            return 0

        # Verificar se ja existem itens (evitar duplicatas)
        itens_existentes = CarviaFaturaTransportadoraItem.query.filter_by(
            fatura_transportadora_id=fatura_id
        ).count()
        if itens_existentes > 0:
            logger.info(
                f"Fatura transportadora {fatura_id}: ja tem {itens_existentes} itens, pulando"
            )
            return 0

        count = 0
        for sub in subcontratos:
            operacao = sub.operacao if hasattr(sub, 'operacao') else None

            # Buscar primeira NF da operacao (para display)
            nf_id = None
            nf_numero = None
            if operacao:
                junction = CarviaOperacaoNf.query.filter_by(
                    operacao_id=operacao.id
                ).first()
                if junction:
                    from app.carvia.models import CarviaNf
                    nf = db.session.get(CarviaNf, junction.nf_id)
                    if nf:
                        nf_id = nf.id
                        nf_numero = nf.numero_nf

            item = CarviaFaturaTransportadoraItem(
                fatura_transportadora_id=fatura_id,
                subcontrato_id=sub.id,
                operacao_id=sub.operacao_id,
                nf_id=nf_id,
                cte_numero=sub.cte_numero,
                cte_data_emissao=sub.cte_data_emissao,
                contraparte_cnpj=operacao.cnpj_cliente if operacao else None,
                contraparte_nome=operacao.nome_cliente if operacao else None,
                nf_numero=nf_numero,
                valor_mercadoria=operacao.valor_mercadoria if operacao else None,
                peso_kg=float(operacao.peso_utilizado or 0) if operacao else None,
                valor_frete=float(sub.valor_final or 0) if sub.valor_final else None,
                valor_cotado=sub.valor_cotado,
                valor_acertado=sub.valor_acertado,
            )
            db.session.add(item)
            count += 1
            logger.info(
                f"Linking: fat_transp_item criado fatura={fatura_id} sub={sub.id} op={sub.operacao_id}"
            )

        db.session.flush()
        return count

    # ------------------------------------------------------------------
    # criar_itens_fatura_cliente_from_operacoes: gera itens (UI manual)
    # ------------------------------------------------------------------

    def criar_itens_fatura_cliente_from_operacoes(self, fatura_id):
        """Gera CarviaFaturaClienteItem a partir das operacoes vinculadas.

        Usado quando fatura e criada manualmente via UI (nao vem de PDF).
        Para cada operacao da fatura, cria 1 item com FKs populadas.

        Returns:
            int — numero de itens criados
        """
        from app.carvia.models import (
            CarviaFaturaCliente, CarviaFaturaClienteItem,
            CarviaOperacao, CarviaOperacaoNf, CarviaNf
        )

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            logger.warning(f"Fatura cliente {fatura_id} nao encontrada")
            return 0

        # Buscar operacoes vinculadas a esta fatura
        operacoes = CarviaOperacao.query.filter_by(
            fatura_cliente_id=fatura_id
        ).all()

        if not operacoes:
            logger.info(f"Fatura cliente {fatura_id}: nenhuma operacao vinculada")
            return 0

        # Verificar se ja existem itens (evitar duplicatas)
        itens_existentes = CarviaFaturaClienteItem.query.filter_by(
            fatura_cliente_id=fatura_id
        ).count()
        if itens_existentes > 0:
            logger.info(
                f"Fatura cliente {fatura_id}: ja tem {itens_existentes} itens, pulando"
            )
            return 0

        count = 0
        for op in operacoes:
            # Buscar primeira NF da operacao (para display)
            nf_id = None
            nf_numero = None
            junction = CarviaOperacaoNf.query.filter_by(
                operacao_id=op.id
            ).first()
            if junction:
                nf = db.session.get(CarviaNf, junction.nf_id)
                if nf:
                    nf_id = nf.id
                    nf_numero = nf.numero_nf

            item = CarviaFaturaClienteItem(
                fatura_cliente_id=fatura_id,
                operacao_id=op.id,
                nf_id=nf_id,
                cte_numero=op.cte_numero,
                cte_data_emissao=op.cte_data_emissao,
                contraparte_cnpj=op.cnpj_cliente,
                contraparte_nome=op.nome_cliente,
                nf_numero=nf_numero,
                valor_mercadoria=op.valor_mercadoria,
                peso_kg=float(op.peso_utilizado or 0) if op.peso_utilizado else None,
                frete=op.cte_valor,
            )
            db.session.add(item)
            count += 1
            logger.info(
                f"Linking: fat_cli_item criado fatura={fatura_id} op={op.id} cte={op.cte_numero}"
            )

        db.session.flush()
        return count

    # ------------------------------------------------------------------
    # backfill_todas_faturas: one-time para dados existentes
    # ------------------------------------------------------------------

    def backfill_todas_faturas(self):
        """Backfill de FKs em todos os itens de faturas existentes.

        1. Para cada fatura_cliente: resolver operacao_id e nf_id nos itens
        2. Para cada fatura_transportadora: gerar itens a partir de subcontratos

        Returns:
            dict com estatisticas globais
        """
        from app.carvia.models import CarviaFaturaCliente, CarviaFaturaTransportadora

        stats = {
            'faturas_cliente': 0,
            'operacoes_resolvidas': 0,
            'nfs_resolvidas': 0,
            'faturas_transportadora': 0,
            'itens_transportadora_criados': 0,
        }

        # 1. Backfill faturas cliente
        faturas_cli = CarviaFaturaCliente.query.all()
        for fatura in faturas_cli:
            result = self.vincular_itens_fatura_cliente(fatura.id)
            stats['faturas_cliente'] += 1
            stats['operacoes_resolvidas'] += result['operacoes_resolvidas']
            stats['nfs_resolvidas'] += result['nfs_resolvidas']

        # 2. Gerar itens faturas transportadora
        faturas_transp = CarviaFaturaTransportadora.query.all()
        for fatura in faturas_transp:
            count = self.criar_itens_fatura_transportadora(fatura.id)
            stats['faturas_transportadora'] += 1
            stats['itens_transportadora_criados'] += count

        db.session.flush()
        logger.info(f"Backfill concluido: {stats}")
        return stats
