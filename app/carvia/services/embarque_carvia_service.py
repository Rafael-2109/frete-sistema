"""
EmbarqueCarViaService — Gestao de itens provisorios CarVia em embarques
========================================================================

Gerencia o ciclo de vida dos EmbarqueItems provisorios:
  provisorio (cotacao) → real (pedido c/ NF) → provisorio removido quando 100%

Chamado por:
  - pedido_routes.py: ao anexar NF ao pedido CarVia
  - cotacao_v2_service.py: ao cancelar cotacao que esta em embarque

Referencia: app/carvia/INTEGRACAO_EMBARQUE.md
"""

import logging
from typing import Dict, List, Optional

from app import db

logger = logging.getLogger(__name__)


class EmbarqueCarViaService:
    """Gestao de itens provisorios CarVia em embarques."""

    @staticmethod
    def expandir_provisorio(carvia_cotacao_id: int, pedido_id: int, numero_nf: str) -> Optional[Dict]:
        """Cria EmbarqueItem real para um pedido CarVia que recebeu NF.

        Chamado quando Jessica anexa NF ao pedido. Verifica se a cotacao
        esta em algum embarque e cria o item real correspondente.

        Apos criar, verifica se a cotacao esta 100% resolvida e remove
        o provisorio se sim.

        Args:
            carvia_cotacao_id: ID da CarViaCotacao
            pedido_id: ID do CarviaPedido que recebeu NF
            numero_nf: Numero da NF anexada

        Returns:
            Dict com resultado ou None se cotacao nao esta em embarque.
        """
        from app.embarques.models import EmbarqueItem
        from app.carvia.models import CarviaPedido, CarviaCotacao

        # 1. Buscar provisorio no embarque
        provisorio = EmbarqueItem.query.filter_by(
            carvia_cotacao_id=carvia_cotacao_id,
            provisorio=True,
            status='ativo',
        ).first()

        if not provisorio:
            logger.info(
                "Cotacao CarVia %s nao esta em nenhum embarque ativo, skip expansao",
                carvia_cotacao_id
            )
            return None

        embarque_id = provisorio.embarque_id

        # 2. Carregar pedido e cotacao
        pedido = db.session.get(CarviaPedido, pedido_id)
        if not pedido:
            logger.warning("CarviaPedido %s nao encontrado", pedido_id)
            return None

        cotacao = db.session.get(CarviaCotacao, carvia_cotacao_id)
        if not cotacao:
            logger.warning("CarViaCotacao %s nao encontrada", carvia_cotacao_id)
            return None

        # 3. Verificar se ja existe EmbarqueItem para este pedido (dedup)
        lote_id_pedido = f'CARVIA-PED-{pedido_id}'
        existente = EmbarqueItem.query.filter_by(
            embarque_id=embarque_id,
            separacao_lote_id=lote_id_pedido,
            status='ativo',
        ).first()

        if existente:
            # Ja expandido — apenas atualizar NF se mudou
            if existente.nota_fiscal != numero_nf:
                existente.nota_fiscal = numero_nf
                logger.info("EmbarqueItem %s NF atualizada para %s", lote_id_pedido, numero_nf)
            return {
                'acao': 'atualizado',
                'embarque_id': embarque_id,
                'embarque_item_id': existente.id,
            }

        # 4. Criar EmbarqueItem real
        dest = cotacao.endereco_destino

        novo_item = EmbarqueItem(
            embarque_id=embarque_id,
            separacao_lote_id=lote_id_pedido,
            cnpj_cliente=dest.cnpj if dest else (provisorio.cnpj_cliente or ''),
            cliente=provisorio.cliente,
            pedido=pedido.numero_pedido,
            nota_fiscal=numero_nf,
            peso=provisorio.peso or 0,  # Sera refinado quando tiver dados reais
            valor=provisorio.valor or 0,
            pallets=0,
            uf_destino=provisorio.uf_destino,
            cidade_destino=provisorio.cidade_destino,
            volumes=None,
            provisorio=False,
            carvia_cotacao_id=carvia_cotacao_id,
        )

        # Copiar dados de tabela do provisorio (FRACIONADA) se existirem
        if provisorio.tabela_nome_tabela:
            for campo in [
                'tabela_nome_tabela', 'tabela_valor_kg', 'tabela_percentual_valor',
                'tabela_frete_minimo_valor', 'tabela_frete_minimo_peso', 'tabela_icms',
                'tabela_percentual_gris', 'tabela_pedagio_por_100kg', 'tabela_valor_tas',
                'tabela_percentual_adv', 'tabela_percentual_rca', 'tabela_valor_despacho',
                'tabela_valor_cte', 'tabela_icms_incluso', 'tabela_gris_minimo',
                'tabela_adv_minimo', 'tabela_icms_proprio', 'icms_destino', 'modalidade',
            ]:
                setattr(novo_item, campo, getattr(provisorio, campo, None))

        db.session.add(novo_item)
        db.session.flush()

        logger.info(
            "EmbarqueItem real criado: %s (NF %s) no embarque %s",
            lote_id_pedido, numero_nf, embarque_id
        )

        # 5. Verificar se cotacao esta 100% resolvida → remover provisorio
        if EmbarqueCarViaService._cotacao_totalmente_resolvida(carvia_cotacao_id):
            db.session.delete(provisorio)
            logger.info(
                "Provisorio REMOVIDO: cotacao %s 100%% resolvida no embarque %s",
                carvia_cotacao_id, embarque_id
            )
            acao = 'expandido_completo'
        else:
            acao = 'expandido_parcial'

        # 6. Recalcular totais do embarque
        EmbarqueCarViaService._recalcular_totais(embarque_id)

        # 6b. Sinalizar que embarque precisa reimprimir (se ja foi impresso)
        from app.embarques.models import Embarque as _Embarque
        _emb = db.session.get(_Embarque, embarque_id)
        if _emb:
            _emb.marcar_alterado_apos_impressao()

        # 7. Se portaria ja deu saida, gerar frete CarVia para o grupo desta NF
        try:
            from app.embarques.models import Embarque
            embarque = db.session.get(Embarque, embarque_id)
            if embarque and embarque.data_embarque:
                # Portaria ja deu saida → gatilho pela NF
                from app.carvia.services.carvia_frete_service import CarviaFreteService
                CarviaFreteService.lancar_frete_carvia(
                    embarque_id=embarque_id,
                    usuario='sistema',
                )
        except Exception as e:
            logger.warning("Erro ao lancar frete CarVia pos-NF: %s", e)

        return {
            'acao': acao,
            'embarque_id': embarque_id,
            'embarque_item_id': novo_item.id,
        }

    @staticmethod
    def _cotacao_totalmente_resolvida(carvia_cotacao_id: int) -> bool:
        """Verifica se TODOS pedidos da cotacao tem NF preenchida."""
        from app.carvia.models import CarviaPedido, CarviaPedidoItem

        pedidos = CarviaPedido.query.filter_by(
            cotacao_id=carvia_cotacao_id,
        ).filter(
            CarviaPedido.status != 'CANCELADO'
        ).all()

        if not pedidos:
            return False  # Sem pedidos = nao resolvida

        for pedido in pedidos:
            itens = CarviaPedidoItem.query.filter_by(pedido_id=pedido.id).all()
            for item in itens:
                if not item.numero_nf or not item.numero_nf.strip():
                    return False  # Pelo menos 1 item sem NF

        return True

    @staticmethod
    def verificar_embarque_completo(embarque_id: int) -> Dict:
        """Verifica se embarque tem provisorios pendentes.

        Returns:
            {
                'completo': bool,
                'provisorios': int (qtd de itens provisorios),
                'total': int (qtd total de itens ativos),
            }
        """
        from app.embarques.models import EmbarqueItem

        total = EmbarqueItem.query.filter_by(
            embarque_id=embarque_id,
            status='ativo',
        ).count()

        provisorios = EmbarqueItem.query.filter_by(
            embarque_id=embarque_id,
            provisorio=True,
            status='ativo',
        ).count()

        return {
            'completo': provisorios == 0,
            'provisorios': provisorios,
            'total': total,
        }

    @staticmethod
    def obter_embarques_com_provisorios() -> List[Dict]:
        """Lista embarques ativos com itens provisorios CarVia.

        Returns:
            List[Dict] com embarque_id, numero, qtd_provisorios
        """
        from app.embarques.models import Embarque, EmbarqueItem
        from sqlalchemy import func as sqlfunc

        resultados = db.session.query(
            Embarque.id,
            Embarque.numero,
            sqlfunc.count(EmbarqueItem.id).label('qtd_provisorios'),
        ).join(
            EmbarqueItem, EmbarqueItem.embarque_id == Embarque.id
        ).filter(
            Embarque.status == 'ativo',
            EmbarqueItem.provisorio == True,  # noqa: E712
            EmbarqueItem.status == 'ativo',
        ).group_by(
            Embarque.id, Embarque.numero
        ).all()

        return [
            {
                'embarque_id': r.id,
                'numero': r.numero,
                'qtd_provisorios': r.qtd_provisorios,
            }
            for r in resultados
        ]

    @staticmethod
    def remover_provisorio_cotacao(carvia_cotacao_id: int) -> Optional[Dict]:
        """Remove provisorio do embarque quando cotacao e cancelada.

        Returns:
            Dict com embarque_id e numero, ou None se nao estava em embarque.
        """
        from app.embarques.models import EmbarqueItem, Embarque

        provisorio = EmbarqueItem.query.filter_by(
            carvia_cotacao_id=carvia_cotacao_id,
            provisorio=True,
            status='ativo',
        ).first()

        if not provisorio:
            return None

        embarque_id = provisorio.embarque_id
        embarque = db.session.get(Embarque, embarque_id)

        db.session.delete(provisorio)

        # Tambem remover itens reais desta cotacao (pedidos ja expandidos)
        itens_reais = EmbarqueItem.query.filter_by(
            carvia_cotacao_id=carvia_cotacao_id,
            status='ativo',
        ).all()
        for item in itens_reais:
            db.session.delete(item)

        EmbarqueCarViaService._recalcular_totais(embarque_id)

        # Sinalizar que embarque precisa reimprimir (se ja foi impresso)
        if embarque:
            embarque.marcar_alterado_apos_impressao()

        logger.info(
            "Provisorio + %d reais removidos do embarque %s (cotacao %s cancelada)",
            len(itens_reais), embarque_id, carvia_cotacao_id
        )

        return {
            'embarque_id': embarque_id,
            'numero': embarque.numero if embarque else None,
        }

    @staticmethod
    def _recalcular_totais(embarque_id: int):
        """Recalcula peso_total, valor_total e pallet_total do embarque."""
        from app.embarques.models import Embarque, EmbarqueItem
        from sqlalchemy import func as sqlfunc

        totais = db.session.query(
            sqlfunc.coalesce(sqlfunc.sum(EmbarqueItem.peso), 0),
            sqlfunc.coalesce(sqlfunc.sum(EmbarqueItem.valor), 0),
            sqlfunc.coalesce(sqlfunc.sum(EmbarqueItem.pallets), 0),
        ).filter(
            EmbarqueItem.embarque_id == embarque_id,
            EmbarqueItem.status == 'ativo',
        ).first()

        embarque = db.session.get(Embarque, embarque_id)
        if embarque and totais:
            embarque.peso_total = float(totais[0])
            embarque.valor_total = float(totais[1])
            embarque.pallet_total = float(totais[2])
