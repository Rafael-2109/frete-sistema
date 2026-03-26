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

        # 1. Buscar item CarVia no embarque (3 niveis de fallback)
        # 1a. Busca ideal: carvia_cotacao_id + provisorio=True
        item_alvo = EmbarqueItem.query.filter_by(
            carvia_cotacao_id=carvia_cotacao_id,
            provisorio=True,
            status='ativo',
        ).first()

        # 1b. Fallback: carvia_cotacao_id sem exigir provisorio
        if not item_alvo:
            item_alvo = EmbarqueItem.query.filter_by(
                carvia_cotacao_id=carvia_cotacao_id,
                status='ativo',
            ).first()

        # 1c. Fallback: separacao_lote_id por padrao (CARVIA-{cot_id} ou CARVIA-COT-{cot_id})
        if not item_alvo:
            for pattern in [f'CARVIA-{carvia_cotacao_id}', f'CARVIA-COT-{carvia_cotacao_id}']:
                item_alvo = EmbarqueItem.query.filter_by(
                    separacao_lote_id=pattern,
                    status='ativo',
                ).first()
                if item_alvo:
                    logger.info("Item encontrado por lote_id=%s", pattern)
                    break

        # 1d. Fallback: CARVIA-PED-{ped_id} dos pedidos desta cotacao
        if not item_alvo:
            peds = CarviaPedido.query.filter_by(
                cotacao_id=carvia_cotacao_id,
            ).filter(CarviaPedido.status != 'CANCELADO').all()
            for p in peds:
                item_alvo = EmbarqueItem.query.filter_by(
                    separacao_lote_id=f'CARVIA-PED-{p.id}',
                    status='ativo',
                ).first()
                if item_alvo:
                    logger.info("Item encontrado por lote_id=CARVIA-PED-%s", p.id)
                    break

        if not item_alvo:
            logger.info(
                "Cotacao CarVia %s nao esta em nenhum embarque ativo, skip expansao",
                carvia_cotacao_id,
            )
            return None

        # Corrigir carvia_cotacao_id se estava NULL
        if not item_alvo.carvia_cotacao_id:
            item_alvo.carvia_cotacao_id = carvia_cotacao_id

        embarque_id = item_alvo.embarque_id
        eh_provisorio_real = item_alvo.provisorio  # True = padrao novo, False = legado

        # 2. Carregar pedido e cotacao
        pedido = db.session.get(CarviaPedido, pedido_id)
        if not pedido:
            logger.warning("CarviaPedido %s nao encontrado", pedido_id)
            return None

        cotacao = db.session.get(CarviaCotacao, carvia_cotacao_id)
        if not cotacao:
            logger.warning("CarViaCotacao %s nao encontrada", carvia_cotacao_id)
            return None

        # 3. Buscar dados reais da NF para peso/valor/volumes
        from app.carvia.models import CarviaNf
        nf_obj = CarviaNf.query.filter_by(numero_nf=str(numero_nf)).order_by(
            CarviaNf.id.desc()
        ).first()
        nf_peso = float(nf_obj.peso_bruto or 0) if nf_obj else 0
        nf_valor = float(nf_obj.valor_total or 0) if nf_obj else 0
        nf_volumes = int(nf_obj.quantidade_volumes or 1) if nf_obj else 1
        nf_id = nf_obj.id if nf_obj else 0

        lote_id_nf = f'CARVIA-NF-{nf_id}'

        # 4. Verificar dedup por NF
        existente = EmbarqueItem.query.filter_by(
            embarque_id=embarque_id,
            separacao_lote_id=lote_id_nf,
            status='ativo',
        ).first()

        if existente:
            logger.info("EmbarqueItem %s ja existe no embarque %s", lote_id_nf, embarque_id)
            return {
                'acao': 'atualizado',
                'embarque_id': embarque_id,
                'embarque_item_id': existente.id,
            }

        dest = cotacao.endereco_destino

        if eh_provisorio_real:
            # ===== CAMINHO PADRAO: provisorio=True =====
            # Criar novo EmbarqueItem real + deduzir/deletar provisorio

            novo_item = EmbarqueItem(
                embarque_id=embarque_id,
                separacao_lote_id=lote_id_nf,
                cnpj_cliente=dest.cnpj if dest else (item_alvo.cnpj_cliente or ''),
                cliente=item_alvo.cliente or (cotacao.cliente.nome_comercial if cotacao.cliente else ''),
                pedido=pedido.numero_pedido,
                nota_fiscal=numero_nf,
                peso=nf_peso,
                valor=nf_valor,
                pallets=0,
                uf_destino=item_alvo.uf_destino or (dest.fisico_uf if dest else ''),
                cidade_destino=item_alvo.cidade_destino or (dest.fisico_cidade if dest else ''),
                volumes=nf_volumes,
                provisorio=False,
                carvia_cotacao_id=carvia_cotacao_id,
            )

            # Copiar dados de tabela do provisorio (FRACIONADA) se existirem
            if getattr(item_alvo, 'tabela_nome_tabela', None):
                for campo in [
                    'tabela_nome_tabela', 'tabela_valor_kg', 'tabela_percentual_valor',
                    'tabela_frete_minimo_valor', 'tabela_frete_minimo_peso', 'tabela_icms',
                    'tabela_percentual_gris', 'tabela_pedagio_por_100kg', 'tabela_valor_tas',
                    'tabela_percentual_adv', 'tabela_percentual_rca', 'tabela_valor_despacho',
                    'tabela_valor_cte', 'tabela_icms_incluso', 'tabela_gris_minimo',
                    'tabela_adv_minimo', 'tabela_icms_proprio', 'icms_destino', 'modalidade',
                ]:
                    setattr(novo_item, campo, getattr(item_alvo, campo, None))

            db.session.add(novo_item)
            db.session.flush()

            # Deduzir do provisorio
            item_alvo.volumes = max(0, (item_alvo.volumes or 0) - nf_volumes)
            item_alvo.peso = max(0, (item_alvo.peso or 0) - nf_peso)
            item_alvo.valor = max(0, (item_alvo.valor or 0) - nf_valor)

            if item_alvo.volumes <= 0:
                db.session.delete(item_alvo)
                logger.info("Provisorio REMOVIDO: cotacao %s embarque %s", carvia_cotacao_id, embarque_id)
                acao = 'expandido_completo'
            else:
                logger.info("Provisorio DEDUZIDO: %d vol restantes cotacao %s", item_alvo.volumes, carvia_cotacao_id)
                acao = 'expandido_parcial'

            resultado_item_id = novo_item.id

        else:
            # ===== CAMINHO LEGADO: provisorio=False =====
            # Item criado pela sessao anterior sem flag provisorio.
            # Atualizar IN-PLACE em vez de criar novo.

            item_alvo.separacao_lote_id = lote_id_nf
            item_alvo.pedido = pedido.numero_pedido
            item_alvo.nota_fiscal = numero_nf
            item_alvo.peso = nf_peso
            item_alvo.valor = nf_valor
            item_alvo.volumes = nf_volumes
            item_alvo.carvia_cotacao_id = carvia_cotacao_id

            logger.info(
                "Item legado ATUALIZADO in-place: id=%s → lote=%s pedido=%s nf=%s",
                item_alvo.id, lote_id_nf, pedido.numero_pedido, numero_nf,
            )
            acao = 'atualizado_inplace'
            resultado_item_id = item_alvo.id

        # Recalcular totais do embarque
        EmbarqueCarViaService._recalcular_totais(embarque_id)

        # Sinalizar que embarque precisa reimprimir (se ja foi impresso)
        from app.embarques.models import Embarque as _Embarque
        _emb = db.session.get(_Embarque, embarque_id)
        if _emb:
            _emb.marcar_alterado_apos_impressao()

        # Se portaria ja deu saida, gerar frete CarVia
        try:
            from app.embarques.models import Embarque
            embarque = db.session.get(Embarque, embarque_id)
            if embarque and embarque.data_embarque:
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
            'embarque_item_id': resultado_item_id,
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
        """Recalcula peso_total e valor_total do embarque.

        NAO toca em pallet_total — pallets sao calculados pelo fluxo
        de palletizacao Nacom (CadastroPalletizacao) e nao devem ser
        sobrescritos por operacoes CarVia.
        """
        from app.embarques.models import Embarque, EmbarqueItem
        from sqlalchemy import func as sqlfunc

        totais = db.session.query(
            sqlfunc.coalesce(sqlfunc.sum(EmbarqueItem.peso), 0),
            sqlfunc.coalesce(sqlfunc.sum(EmbarqueItem.valor), 0),
        ).filter(
            EmbarqueItem.embarque_id == embarque_id,
            EmbarqueItem.status == 'ativo',
        ).first()

        embarque = db.session.get(Embarque, embarque_id)
        if embarque and totais:
            embarque.peso_total = float(totais[0])
            embarque.valor_total = float(totais[1])

    @staticmethod
    def resolver_lote_carvia(lote_id: str) -> Optional[Dict]:
        """Resolve separacao_lote_id CarVia para dados de cotacao/pedido/veiculos.

        Suporta todos os padroes:
          CARVIA-NF-{nf_id}   → item real (NF anexada)
          CARVIA-COT-{cot_id} → provisorio recriado
          CARVIA-PED-{ped_id} → legado (backward compat)
          CARVIA-{id}         → provisorio original

        Retorna dict com: cotacao, pedido, itens_pedido, motos,
                          veiculos_por_nf, filial, eh_pedido
        Retorna None se nao encontrar a cotacao.
        """
        from app.carvia.models import (
            CarviaCotacao, CarviaCotacaoMoto, CarviaNf,
            CarviaPedido, CarviaPedidoItem,
        )

        lote = str(lote_id)
        cotacao = None
        pedido = None
        itens_pedido = []
        eh_pedido = False

        try:
            if lote.startswith('CARVIA-NF-'):
                # Item real: NF anexada ao pedido
                nf_id = int(lote.replace('CARVIA-NF-', ''))
                nf_obj = db.session.get(CarviaNf, nf_id)
                if nf_obj:
                    # Achar PedidoItem com esse numero_nf
                    pi = CarviaPedidoItem.query.filter_by(
                        numero_nf=str(nf_obj.numero_nf)
                    ).first()
                    if pi:
                        pedido = db.session.get(CarviaPedido, pi.pedido_id)
                        if pedido:
                            cotacao = db.session.get(CarviaCotacao, pedido.cotacao_id)
                            itens_pedido = CarviaPedidoItem.query.filter_by(
                                pedido_id=pedido.id
                            ).all()
                            eh_pedido = True

            elif lote.startswith('CARVIA-COT-'):
                # Provisorio recriado apos exclusao de pedido
                cot_id = int(lote.replace('CARVIA-COT-', ''))
                cotacao = db.session.get(CarviaCotacao, cot_id)

            elif lote.startswith('CARVIA-PED-'):
                # Legado: padrao antigo (backward compat)
                ped_id = int(lote.replace('CARVIA-PED-', ''))
                pedido = db.session.get(CarviaPedido, ped_id)
                if pedido:
                    cotacao = db.session.get(CarviaCotacao, pedido.cotacao_id)
                    itens_pedido = CarviaPedidoItem.query.filter_by(
                        pedido_id=ped_id
                    ).all()
                    eh_pedido = True

            else:
                # Provisorio original: CARVIA-{id}
                raw_id = lote.replace('CARVIA-', '')
                cot_id = int(raw_id)
                cotacao = db.session.get(CarviaCotacao, cot_id)

        except (ValueError, TypeError):
            logger.warning(f'resolver_lote_carvia: formato invalido "{lote_id}"')
            return None

        if not cotacao:
            return None

        # Motos da cotacao (para provisorios)
        motos = []
        if cotacao.tipo_material == 'MOTO' and not eh_pedido:
            motos = CarviaCotacaoMoto.query.filter_by(cotacao_id=cotacao.id).all()

        # Veiculos por NF (para itens reais com NF)
        veiculos_por_nf = {}
        for item in itens_pedido:
            if item.numero_nf and item.numero_nf not in veiculos_por_nf:
                nf_obj = CarviaNf.query.filter_by(
                    numero_nf=str(item.numero_nf)
                ).order_by(CarviaNf.id.desc()).first()
                if nf_obj:
                    veiculos_por_nf[item.numero_nf] = nf_obj.veiculos.all()

        # Filial do pedido (SP/RJ)
        filial = pedido.filial if pedido else None

        return {
            'cotacao': cotacao,
            'pedido': pedido,
            'itens_pedido': itens_pedido,
            'motos': motos,
            'veiculos_por_nf': veiculos_por_nf,
            'filial': filial,
            'eh_pedido': eh_pedido,
        }
