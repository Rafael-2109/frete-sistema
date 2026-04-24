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

            # Peso cubado da NF: somar cubado real de cada veiculo pelo modelo
            from app.carvia.models import CarviaCotacaoMoto as _CCM
            _cubado_por_modelo = {}
            for _m in _CCM.query.filter_by(cotacao_id=carvia_cotacao_id).all():
                if _m.modelo_moto and _m.quantidade and _m.quantidade > 0:
                    _cubado_por_modelo[_m.modelo_moto.nome.upper()] = (
                        float(_m.peso_cubado_total or 0) / int(_m.quantidade)
                    )
            _nf_cubado = 0
            if nf_obj:
                for _v in nf_obj.veiculos.all():
                    _mod = (_v.modelo or '').upper()
                    if _mod in _cubado_por_modelo:
                        _nf_cubado += _cubado_por_modelo[_mod]
                    else:
                        for _nome, _cub in _cubado_por_modelo.items():
                            if _nome in _mod or _mod in _nome:
                                _nf_cubado += _cub
                                break

            novo_item = EmbarqueItem(
                embarque_id=embarque_id,
                separacao_lote_id=lote_id_nf,
                cnpj_cliente=dest.cnpj if dest else (item_alvo.cnpj_cliente or ''),
                cliente=item_alvo.cliente or (cotacao.cliente.nome_comercial if cotacao.cliente else ''),
                pedido=pedido.numero_pedido,
                nota_fiscal=numero_nf,
                peso=nf_peso,
                peso_cubado=round(_nf_cubado, 2) if _nf_cubado > 0 else item_alvo.peso_cubado,
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

            # Preencher volumes do provisorio se NULL (defensivo: calcula dos motos da cotacao)
            if item_alvo.volumes is None and carvia_cotacao_id:
                from app.carvia.models import CarviaCotacaoMoto
                item_alvo.volumes = db.session.query(
                    db.func.coalesce(db.func.sum(CarviaCotacaoMoto.quantidade), 0)
                ).filter_by(cotacao_id=carvia_cotacao_id).scalar() or 1

            # Deduzir do provisorio
            item_alvo.volumes = max(0, (item_alvo.volumes or 0) - nf_volumes)
            item_alvo.peso = max(0, (item_alvo.peso or 0) - nf_peso)
            item_alvo.peso_cubado = max(0, (item_alvo.peso_cubado or 0) - _nf_cubado) if item_alvo.peso_cubado else None
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
                from app.carvia.services.documentos.carvia_frete_service import CarviaFreteService
                CarviaFreteService.lancar_frete_carvia(
                    embarque_id=embarque_id,
                    usuario='sistema',
                )
                # FIX CR1: sincronizar EntregaMonitorada (data_embarque + transportadora)
                # apos frete gerado. Sem isso, NF anexada pos-portaria fica com
                # monitoramento vazio (portaria executa uma unica vez e ja passou).
                # NOTA: sincronizar_entrega_carvia_por_nf faz db.session.commit()
                # interno — isso e DELIBERADO. Neste ponto novo_item + frete ja
                # foram flushed, e os callers (pedido_routes/cotacao_v2_routes)
                # farao um commit subsequente (no-op para estas entidades).
                try:
                    from app.utils.sincronizar_entregas_carvia import (
                        sincronizar_entrega_carvia_por_nf,
                    )
                    sincronizar_entrega_carvia_por_nf(numero_nf)
                except Exception as e_sync:
                    logger.warning(
                        "Erro ao sincronizar monitoramento CarVia pos-NF "
                        "(nao-bloqueante) NF=%s: %s",
                        numero_nf, e_sync,
                    )
        except Exception as e:
            logger.warning("Erro ao lancar frete CarVia pos-NF: %s", e)

        return {
            'acao': acao,
            'embarque_id': embarque_id,
            'embarque_item_id': resultado_item_id,
        }

    @staticmethod
    def calcular_cubado_por_modelos(carvia_cotacao_id: int, modelos_veiculos: List[str]) -> float:
        """Calcula peso cubado total de N veiculos somando o cubado unitario por modelo.

        Usa `CarviaCotacaoMoto.peso_cubado_total / quantidade` como cubado unitario
        de cada modelo cadastrado na cotacao; match exato por nome.upper(), com
        fallback por substring.

        Args:
            carvia_cotacao_id: ID da CarviaCotacao (fonte dos modelos)
            modelos_veiculos: lista de strings com modelo de cada veiculo a contabilizar

        Returns:
            peso cubado total (float, arredondado 2 casas). Zero se modelos nao batem.
        """
        from app.carvia.models import CarviaCotacaoMoto

        cubado_por_modelo: Dict[str, float] = {}
        for m in CarviaCotacaoMoto.query.filter_by(cotacao_id=carvia_cotacao_id).all():
            if m.modelo_moto and m.quantidade and m.quantidade > 0:
                cubado_por_modelo[m.modelo_moto.nome.upper()] = (
                    float(m.peso_cubado_total or 0) / int(m.quantidade)
                )

        total = 0.0
        for modelo_raw in modelos_veiculos:
            mod = (modelo_raw or '').upper()
            if mod in cubado_por_modelo:
                total += cubado_por_modelo[mod]
            else:
                for nome, cubado in cubado_por_modelo.items():
                    if nome in mod or mod in nome:
                        total += cubado
                        break
        return round(total, 2)

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
    def auto_expandir_provisorios(embarque) -> int:
        """Expande provisorios CarVia cujas cotacoes ja tem NFs anexadas.

        Chamado por fechar_frete, fechar_frete_grupo e processar_cotacao_manual
        APOS o commit que persiste os EmbarqueItem provisorios.

        Cobre 2 cenarios:
          (a) Parte 2A (CARVIA-{cot_id}): view retorna nf=NULL por design, mas
              a cotacao ja tem CarviaPedidoItem.numero_nf preenchido.
          (b) Parte 2B multi-NF: pedido.nf vem com "NF1, NF2" via string_agg —
              FIX CR3 marcou como provisorio e este metodo expande cada NF.

        expandir_provisorio e idempotente: dedup por (embarque_id, CARVIA-NF-{nf_id}).

        Returns:
            Quantidade de cotacoes processadas.
        """
        from app.carvia.models import CarviaPedido, CarviaPedidoItem

        itens_carvia_prov = [
            ei for ei in embarque.itens
            if ei.status == 'ativo' and ei.provisorio and ei.carvia_cotacao_id
        ]
        if not itens_carvia_prov:
            return 0

        cot_ids_processadas = set()
        for ei in itens_carvia_prov:
            cot_id = ei.carvia_cotacao_id
            if cot_id in cot_ids_processadas:
                continue
            cot_ids_processadas.add(cot_id)
            try:
                peds = CarviaPedido.query.filter_by(
                    cotacao_id=cot_id
                ).filter(CarviaPedido.status != 'CANCELADO').all()
                for ped in peds:
                    nfs_unicas = {
                        nf for (nf,) in db.session.query(
                            CarviaPedidoItem.numero_nf
                        ).filter(
                            CarviaPedidoItem.pedido_id == ped.id,
                            CarviaPedidoItem.numero_nf.isnot(None),
                            CarviaPedidoItem.numero_nf != '',
                        ).distinct().all()
                    }
                    for nf_individual in nfs_unicas:
                        try:
                            EmbarqueCarViaService.expandir_provisorio(
                                carvia_cotacao_id=cot_id,
                                pedido_id=ped.id,
                                numero_nf=nf_individual,
                            )
                            logger.info(
                                "CR2 auto-expand: cot=%s ped=%s NF=%s emb=%s",
                                cot_id, ped.id, nf_individual, embarque.id,
                            )
                        except Exception as e_nf:
                            logger.warning(
                                "CR2 falha NF=%s cot=%s: %s",
                                nf_individual, cot_id, e_nf,
                            )
            except Exception as e_cot:
                logger.warning("CR2 falha cot=%s: %s", cot_id, e_cot)

        if cot_ids_processadas:
            db.session.commit()

        return len(cot_ids_processadas)

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
    def remover_itens_cotacao(carvia_cotacao_id: int) -> Optional[Dict]:
        """Remove TODOS os EmbarqueItems de uma cotacao (provisorio + reais).

        Diferente de remover_provisorio_cotacao(), nao depende do provisorio existir.
        Usado no cancelamento de cotacao — corrige caso em que provisorio ja foi
        consumido (expandido_completo) mas itens reais CARVIA-NF-* permanecem.
        """
        from app.embarques.models import EmbarqueItem, Embarque

        todos_itens = EmbarqueItem.query.filter_by(
            carvia_cotacao_id=carvia_cotacao_id,
            status='ativo',
        ).all()

        if not todos_itens:
            return None

        embarque_id = todos_itens[0].embarque_id
        embarque = db.session.get(Embarque, embarque_id)

        for item in todos_itens:
            db.session.delete(item)

        EmbarqueCarViaService._recalcular_totais(embarque_id)

        if embarque:
            embarque.marcar_alterado_apos_impressao()

        logger.info(
            "%d EmbarqueItem(s) removido(s) do embarque %s (cotacao %s cancelada)",
            len(todos_itens), embarque_id, carvia_cotacao_id,
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

        # Veiculos por NF, peso bruto e cubado (para itens reais com NF)
        veiculos_por_nf = {}
        peso_bruto_nf = 0
        volumes_nf = 0
        for item in itens_pedido:
            if item.numero_nf and item.numero_nf not in veiculos_por_nf:
                nf_obj = CarviaNf.query.filter_by(
                    numero_nf=str(item.numero_nf)
                ).order_by(CarviaNf.id.desc()).first()
                if nf_obj:
                    veiculos_por_nf[item.numero_nf] = nf_obj.veiculos.all()
                    peso_bruto_nf += float(nf_obj.peso_bruto or 0)
                    volumes_nf += int(nf_obj.quantidade_volumes or 0)

        # Cubado real: somar cubado unitario de cada veiculo pelo modelo
        from app.carvia.models import CarviaModeloMoto
        # Mapa modelo_nome → cubado unitario (a partir das motos da cotacao)
        cubado_por_modelo = {}
        for m in CarviaCotacaoMoto.query.filter_by(cotacao_id=cotacao.id).all():
            if m.modelo_moto and m.quantidade and m.quantidade > 0:
                cubado_por_modelo[m.modelo_moto.nome.upper()] = (
                    float(m.peso_cubado_total or 0) / int(m.quantidade)
                )
        # Somar cubado de cada veiculo das NFs deste pedido
        peso_cubado_nf = 0
        for nf_num, veics in veiculos_por_nf.items():
            for v in veics:
                modelo_upper = (v.modelo or '').upper()
                if modelo_upper in cubado_por_modelo:
                    peso_cubado_nf += cubado_por_modelo[modelo_upper]
                else:
                    # Fallback: match com word boundary (evita "RET" in "PRETA")
                    import re as _re
                    for nome, cubado in cubado_por_modelo.items():
                        nome_esc = _re.escape(nome)
                        modelo_esc = _re.escape(modelo_upper)
                        if (_re.search(r'(?<![A-Za-z])' + nome_esc + r'(?![A-Za-z])', modelo_upper)
                                or _re.search(r'(?<![A-Za-z])' + modelo_esc + r'(?![A-Za-z])', nome)):
                            peso_cubado_nf += cubado
                            break
        peso_cubado_nf = round(peso_cubado_nf, 2)

        # Filial do pedido (SP/RJ)
        filial = pedido.filial if pedido else None

        # Observacoes: do pedido (se real) ou da cotacao (se provisorio)
        observacoes = None
        if pedido and pedido.observacoes:
            observacoes = pedido.observacoes
        elif cotacao and cotacao.observacoes:
            observacoes = cotacao.observacoes

        return {
            'cotacao': cotacao,
            'pedido': pedido,
            'itens_pedido': itens_pedido,
            'motos': motos,
            'veiculos_por_nf': veiculos_por_nf,
            'peso_bruto_nf': peso_bruto_nf,
            'peso_cubado_nf': peso_cubado_nf,
            'filial': filial,
            'eh_pedido': eh_pedido,
            'observacoes': observacoes,
        }


# ==============================================================================
# F5 (2026-04-19): Propagacao cancelamento Nacom→CarVia
# ==============================================================================

def cancelar_artefatos_carvia_do_embarque(
    embarque_id: int, usuario: str, motivo: str,
) -> Dict:
    """F5: cancela em cascata artefatos CarVia gerados por um embarque.

    Quando embarque Nacom e cancelado, os artefatos CarVia vinculados
    (CarviaFrete, CarviaOperacao, CarviaSubcontrato, CTe Comp, CustoEntrega)
    podem ficar orfaos. Este hook cancela todos os ELEGIVEIS (nao-FATURADOS,
    nao-CONFERIDOS) usando o service B3 ja atomico e idempotente.

    Apenas itens BLOQUEADOS sao reportados (nao lanca excecao) — operador
    recebe alerta para tratar manualmente.

    Args:
        embarque_id: ID do Embarque Nacom cancelado
        usuario: email do usuario
        motivo: texto do motivo de cancelamento do embarque

    Returns:
        dict {
            'cancelados_total': int,
            'operacoes_canceladas': list[int],
            'bloqueados': list[dict],  # artefatos que nao puderam
            'erros': list[str],
        }
    """
    from app.carvia.models.frete import CarviaFrete
    from app.carvia.services.documentos.operacao_cancel_service import (
        listar_dependencias_ativas, executar_cancelamento_cascata,
    )

    resultado = {
        'cancelados_total': 0,
        'operacoes_canceladas': [],
        'bloqueados': [],
        'erros': [],
    }

    try:
        # Busca CarviaFrete vinculados ao embarque (cada frete pode ter
        # 1 operacao pai + subcontratos + CTe Comps + CEs).
        fretes = (
            CarviaFrete.query
            .filter(
                CarviaFrete.embarque_id == embarque_id,
                CarviaFrete.status != 'CANCELADO',
            )
            .all()
        )
        if not fretes:
            return resultado

        # Fretes ORFAOS (sem operacao_id): cancelar diretamente sem cascata.
        # Acontece quando CarviaFrete foi criado via hook portaria mas a
        # CarviaOperacao nao foi emitida ainda, ou em dados legados. Sem esse
        # bloco, embarque cancelado deixava CarviaFrete ativo. (P5, 2026-04-24)
        from app.utils.timezone import agora_utc_naive as _agora_naive
        _agora = _agora_naive()
        for frete in fretes:
            if getattr(frete, 'operacao_id', None) is not None:
                continue
            if frete.status == 'CANCELADO':
                continue
            if getattr(frete, 'status_conferencia', None) == 'CONFERIDO':
                resultado['bloqueados'].append({
                    'tipo': 'carvia_fretes',
                    'id': frete.id,
                    'motivo': 'CarviaFrete CONFERIDO — reabrir primeiro',
                })
                continue
            frete.status = 'CANCELADO'
            if hasattr(frete, 'cancelado_em'):
                frete.cancelado_em = _agora
            if hasattr(frete, 'cancelado_por'):
                frete.cancelado_por = usuario
            resultado['cancelados_total'] += 1
            logger.info(
                'CarviaFrete orfao %s cancelado (embarque %s, sem operacao_id)',
                frete.id, embarque_id,
            )

        operacoes_tocadas = set()
        for frete in fretes:
            op_id = getattr(frete, 'operacao_id', None)
            if op_id is None or op_id in operacoes_tocadas:
                continue
            operacoes_tocadas.add(op_id)

            deps = listar_dependencias_ativas(op_id)
            if deps.get('operacao') is None:
                continue

            # Coleta bloqueados primeiro (define se pode cancelar operacao)
            tem_bloqueado = False
            for cat in ('subcontratos', 'ctes_complementares',
                        'custos_entrega', 'carvia_fretes'):
                for item in deps[cat]:
                    if item['bloqueado']:
                        tem_bloqueado = True
                        resultado['bloqueados'].append({
                            'tipo': cat,
                            'id': item['id'],
                            'motivo': item['motivo'],
                        })

            ids_a_cancelar = {
                'subcontratos': [
                    s['id'] for s in deps['subcontratos']
                    if not s['bloqueado']
                ],
                'ctes_complementares': [
                    c['id'] for c in deps['ctes_complementares']
                    if not c['bloqueado']
                ],
                'custos_entrega': [
                    ce['id'] for ce in deps['custos_entrega']
                    if not ce['bloqueado']
                ],
                'carvia_fretes': [
                    f['id'] for f in deps['carvia_fretes']
                    if not f['bloqueado']
                ],
                # SEGURANCA (auto-revisao): cancelar operacao APENAS se
                # nenhum filho esta bloqueado. Operacao orfa com filhos
                # FATURADO/CONFERIDO cria inconsistencia pior que o problema
                # original. Se ha bloqueado, operacao fica viva e
                # operador resolve manualmente.
                'cancelar_operacao': not tem_bloqueado,
            }

            try:
                res_exec = executar_cancelamento_cascata(
                    operacao_id=op_id,
                    ids_a_cancelar=ids_a_cancelar,
                    usuario=usuario,
                    motivo=f'F5 cascade Nacom→CarVia: {motivo}',
                )
                if res_exec.get('status') in ('OK', 'PARCIAL'):
                    cancelados_cat = res_exec.get('cancelados', {})
                    total_item = (
                        len(cancelados_cat.get('subcontratos') or [])
                        + len(cancelados_cat.get('ctes_complementares') or [])
                        + len(cancelados_cat.get('custos_entrega') or [])
                        + len(cancelados_cat.get('carvia_fretes') or [])
                        + (1 if cancelados_cat.get('operacao') else 0)
                    )
                    resultado['cancelados_total'] += total_item
                    if cancelados_cat.get('operacao'):
                        resultado['operacoes_canceladas'].append(op_id)
                resultado['erros'].extend(res_exec.get('erros') or [])
            except Exception as e_exec:
                logger.exception(
                    'F5 cascade falhou op=%s embarque=%s: %s',
                    op_id, embarque_id, e_exec,
                )
                resultado['erros'].append(f'op_{op_id}: {e_exec}')

        # RESET de CarviaPedido.status (P1, 2026-04-24):
        # Cancelar embarque NAO revertia `CarviaPedido.status='EMBARCADO'`,
        # deixando pedidos travados na tela `lista_pedidos.html` sem permitir
        # recotar/embarcar novamente. Aqui recalculamos `status` a partir do
        # proprio `status_calculado` (que le EmbarqueItem.status='ativo').
        # `embarques/routes.py:1011` ja marca todos os itens como 'cancelado'
        # ANTES deste hook rodar, entao o recalculo pega o estado correto.
        try:
            _resetar_status_pedidos_carvia_do_embarque(embarque_id)
        except Exception as e_reset:
            logger.warning(
                'Reset CarviaPedido.status embarque=%s falhou: %s',
                embarque_id, e_reset,
            )
            resultado['erros'].append(f'reset_pedidos: {e_reset}')

        logger.info(
            'F5 propagacao Nacom→CarVia embarque=%s: %s cancelados, '
            '%s bloqueados, %s erros',
            embarque_id,
            resultado['cancelados_total'],
            len(resultado['bloqueados']),
            len(resultado['erros']),
        )
        return resultado

    except Exception as e:
        logger.exception(
            'F5 propagacao Nacom→CarVia: erro inesperado embarque=%s: %s',
            embarque_id, e,
        )
        resultado['erros'].append(str(e))
        return resultado


def atualizar_status_pedido_carvia_pelo_faturamento(numero_nf: str) -> int:
    """Revalida status de CarviaPedidos afetados por uma NF.

    Chamado apos:
    - Importacao de CarviaNf (NF recem-ativa no CarVia)
    - Anexar NF a CarviaPedidoItem (api_anexar_nf_pedido)

    Fluxo CarVia (P7 revisado, 2026-04-24):
        ABERTO -> COTADO -> FATURADO -> EMBARCADO
        (90% dos pedidos CarVia sao cotados ja com NF. FATURADO acontece
        ANTES de embarcar, via NF ativa em CarviaNf. EMBARCADO e o estado
        final, aplicado pelo hook da portaria.)

    Regra de transicao desta funcao:
    - ABERTO/COTADO -> FATURADO: todos os itens do pedido tem numero_nf
      preenchido E cada NF existe em CarviaNf ATIVA.
    - EMBARCADO nao volta para FATURADO (idempotente — pedido ja progrediu).

    Returns:
        Quantidade de CarviaPedidos cujo status foi alterado. Nao commita.
    """
    from app.carvia.models import CarviaPedido, CarviaPedidoItem, CarviaNf

    if not numero_nf:
        return 0

    # Pedidos candidatos: que tem item apontando para esta NF
    ped_ids = {
        pi.pedido_id for pi in CarviaPedidoItem.query.filter_by(
            numero_nf=str(numero_nf)
        ).all() if pi.pedido_id
    }
    if not ped_ids:
        return 0

    atualizados = 0
    for pid in ped_ids:
        pedido = db.session.get(CarviaPedido, pid)
        if not pedido or pedido.status in (
            'CANCELADO', 'FATURADO', 'EMBARCADO',
        ):
            continue

        itens_pedido = pedido.itens.all()
        if not itens_pedido:
            continue

        nfs_pedido = [it.numero_nf for it in itens_pedido]
        todos_tem_nf = all(nf and str(nf).strip() for nf in nfs_pedido)
        if not todos_tem_nf:
            continue

        nfs_existentes = CarviaNf.query.filter(
            CarviaNf.numero_nf.in_([str(n) for n in nfs_pedido]),
            CarviaNf.status == 'ATIVA',
        ).all()
        numeros_existentes = {str(nf.numero_nf) for nf in nfs_existentes}
        todas_ativas = all(
            str(nf) in numeros_existentes for nf in nfs_pedido
        )
        if not todas_ativas:
            continue

        # ABERTO ou COTADO -> FATURADO (NF ativa antes de embarcar)
        logger.info(
            'CarviaPedido %s %s -> FATURADO (NF %s ativa)',
            pedido.numero_pedido, pedido.status, numero_nf,
        )
        pedido.status = 'FATURADO'
        atualizados += 1

    return atualizados


def cancelar_pedido_carvia_por_lote(lote_id: str, usuario: str, motivo: str = '') -> Dict:
    """Cancela CarviaPedido a partir de um lote (CARVIA-PED-* ou CARVIA-NF-*).

    Uso publico: chamado por rotas admin Nacom (`excluir_pedido`,
    `cancelar_separacao`) quando o lote e CarVia. Mantem integridade:
    - marca `CarviaPedido.status='CANCELADO'`
    - cancela EmbarqueItems ativos (CARVIA-PED-* e CARVIA-NF-* do pedido)
    - bloqueia se ha CarviaFrete CONFERIDO/FATURADO ou vinculado a fatura

    Args:
        lote_id: separacao_lote_id (ex: CARVIA-PED-123 ou CARVIA-NF-456)
        usuario: identificador do operador
        motivo: texto livre

    Returns:
        dict {'sucesso': bool, 'mensagem': str, 'pedido_id': int | None}

    Nao commita — caller e responsavel.
    """
    from app.embarques.models import EmbarqueItem
    from app.carvia.models import (
        CarviaPedido, CarviaPedidoItem, CarviaNf,
    )
    from app.carvia.models.frete import CarviaFrete

    pedido = None

    if lote_id.startswith('CARVIA-PED-'):
        try:
            pid = int(lote_id.replace('CARVIA-PED-', ''))
            pedido = db.session.get(CarviaPedido, pid)
        except (ValueError, TypeError):
            pass
    elif lote_id.startswith('CARVIA-NF-'):
        try:
            nf_id = int(lote_id.replace('CARVIA-NF-', ''))
            nf = db.session.get(CarviaNf, nf_id)
            if nf and nf.numero_nf:
                pi = CarviaPedidoItem.query.filter_by(
                    numero_nf=nf.numero_nf
                ).first()
                if pi and pi.pedido_id:
                    pedido = db.session.get(CarviaPedido, pi.pedido_id)
        except (ValueError, TypeError):
            pass

    if not pedido:
        return {
            'sucesso': False,
            'mensagem': f'Pedido CarVia nao localizado para lote {lote_id}',
            'pedido_id': None,
        }

    if pedido.status == 'CANCELADO':
        return {
            'sucesso': True,
            'mensagem': f'Pedido {pedido.numero_pedido} ja estava CANCELADO',
            'pedido_id': pedido.id,
        }

    # Bloqueio: CarviaFrete CONFERIDO/FATURADO para qualquer NF do pedido
    nfs_do_pedido = [i.numero_nf for i in pedido.itens.all() if i.numero_nf]
    if nfs_do_pedido:
        conds_csv = [
            CarviaFrete.numeros_nfs.ilike(f'%{nf}%')
            for nf in nfs_do_pedido
        ]
        if conds_csv:
            bloq = CarviaFrete.query.filter(
                db.or_(*conds_csv),
                db.or_(
                    CarviaFrete.status == 'CONFERIDO',
                    CarviaFrete.status == 'FATURADO',
                    CarviaFrete.fatura_cliente_id.isnot(None),
                ),
            ).first()
            if bloq:
                return {
                    'sucesso': False,
                    'mensagem': (
                        f'Bloqueado: CarviaFrete #{bloq.id} CONFERIDO/FATURADO/'
                        f'vinculado a fatura. Desfaca no modulo CarVia primeiro.'
                    ),
                    'pedido_id': pedido.id,
                }

    # Cancelar EmbarqueItems ativos (CARVIA-PED-{id} + CARVIA-NF-{nf_id})
    lotes_a_cancelar = [f'CARVIA-PED-{pedido.id}']
    for nf_num in set(nfs_do_pedido):
        nf_obj = CarviaNf.query.filter_by(numero_nf=str(nf_num)).first()
        if nf_obj:
            lotes_a_cancelar.append(f'CARVIA-NF-{nf_obj.id}')

    if lotes_a_cancelar:
        EmbarqueItem.query.filter(
            EmbarqueItem.separacao_lote_id.in_(lotes_a_cancelar),
            EmbarqueItem.status == 'ativo',
        ).update({'status': 'cancelado'}, synchronize_session='fetch')

    pedido.status = 'CANCELADO'
    logger.info(
        'CarviaPedido %s CANCELADO via lote (usuario=%s, motivo=%s)',
        pedido.numero_pedido, usuario, motivo,
    )

    return {
        'sucesso': True,
        'mensagem': (
            f'Pedido CarVia {pedido.numero_pedido} cancelado. '
            f'EmbarqueItems ativos associados foram desativados.'
        ),
        'pedido_id': pedido.id,
    }


def resetar_status_pedidos_carvia_por_lotes(
    lotes: list,
    carvia_cotacao_id: int = None,
) -> int:
    """Recalcula `CarviaPedido.status` dado um conjunto de lotes.

    Uso publico: chamado por rotas que cancelam/removem itens individuais
    (cancelar_item_embarque, excluir_item_embarque, desvincular_pedido)
    para resetar pedidos CarVia afetados.

    Args:
        lotes: lista de `separacao_lote_id` (CARVIA-PED-*, CARVIA-NF-*,
            CARVIA-{cot_id}) dos itens removidos/cancelados.
        carvia_cotacao_id: fallback quando o lote nao identifica diretamente
            o pedido (ex: provisorio CARVIA-{cot_id}).

    Returns:
        Quantidade de CarviaPedidos cujo status foi alterado.

    Nao commita — caller e responsavel. Faz flush antes de chamar
    status_calculado para garantir visibilidade de mutacoes de EmbarqueItem.
    """
    from app.carvia.models import CarviaPedido, CarviaPedidoItem, CarviaNf

    pedido_ids = set()
    for lote in lotes or []:
        lote = str(lote or '')
        if lote.startswith('CARVIA-PED-'):
            try:
                pedido_ids.add(int(lote.replace('CARVIA-PED-', '')))
            except (ValueError, TypeError):
                pass
        elif lote.startswith('CARVIA-NF-'):
            try:
                nf_id = int(lote.replace('CARVIA-NF-', ''))
                nf = db.session.get(CarviaNf, nf_id)
                if nf and nf.numero_nf:
                    for pi in CarviaPedidoItem.query.filter_by(
                        numero_nf=nf.numero_nf
                    ).all():
                        if pi.pedido_id:
                            pedido_ids.add(pi.pedido_id)
            except (ValueError, TypeError):
                pass

    # Fallback via carvia_cotacao_id (provisorio)
    if carvia_cotacao_id:
        for p in CarviaPedido.query.filter_by(
            cotacao_id=carvia_cotacao_id
        ).filter(CarviaPedido.status != 'CANCELADO').all():
            pedido_ids.add(p.id)

    if not pedido_ids:
        return 0

    # Flush obrigatorio: status_calculado re-consulta EmbarqueItem.
    db.session.flush()

    resetados = 0
    for pid in pedido_ids:
        pedido = db.session.get(CarviaPedido, pid)
        if not pedido or pedido.status == 'CANCELADO':
            continue
        novo_status = pedido.status_calculado
        if (
            novo_status != pedido.status
            and novo_status in ('ABERTO', 'COTADO', 'FATURADO')
        ):
            logger.info(
                'CarviaPedido %s status %s -> %s (reset por lote)',
                pedido.numero_pedido, pedido.status, novo_status,
            )
            pedido.status = novo_status
            resetados += 1

    return resetados


def _resetar_status_pedidos_carvia_do_embarque(embarque_id: int) -> None:
    """Recalcula `CarviaPedido.status` apos cancelamento de embarque.

    Identifica todos os CarviaPedidos que tinham EmbarqueItems neste embarque
    (via lotes CARVIA-PED-*, CARVIA-NF-* ou `carvia_cotacao_id`) e reseta
    `status` para o valor derivado de `status_calculado` (que considera
    EmbarqueItem.status='ativo').

    Chamado apos o embarque ser marcado cancelado (item.status='cancelado'
    ja aplicado em embarques/routes.py:1011), garantindo que os pedidos
    voltem a ABERTO/COTADO e destravem a lista de pedidos para recotacao.
    """
    from app.embarques.models import EmbarqueItem
    from app.carvia.models import CarviaPedido, CarviaPedidoItem, CarviaNf

    # Itens do embarque (incluindo ja cancelados — precisamos dos lotes)
    itens = EmbarqueItem.query.filter_by(embarque_id=embarque_id).all()
    if not itens:
        return

    pedido_ids = set()
    for item in itens:
        lote = item.separacao_lote_id or ''

        # CARVIA-PED-{id}: mapeamento direto
        if lote.startswith('CARVIA-PED-'):
            try:
                pedido_ids.add(int(lote.replace('CARVIA-PED-', '')))
            except (ValueError, TypeError):
                pass

        # CARVIA-NF-{nf_id}: via CarviaNf.numero_nf -> CarviaPedidoItem.pedido_id
        elif lote.startswith('CARVIA-NF-'):
            try:
                nf_id = int(lote.replace('CARVIA-NF-', ''))
                nf = db.session.get(CarviaNf, nf_id)
                if nf and nf.numero_nf:
                    for pi in CarviaPedidoItem.query.filter_by(
                        numero_nf=nf.numero_nf
                    ).all():
                        if pi.pedido_id:
                            pedido_ids.add(pi.pedido_id)
            except (ValueError, TypeError):
                pass

        # Fallback: provisorio com carvia_cotacao_id — pega pedidos da cotacao
        elif item.carvia_cotacao_id:
            for p in CarviaPedido.query.filter_by(
                cotacao_id=item.carvia_cotacao_id
            ).filter(CarviaPedido.status != 'CANCELADO').all():
                pedido_ids.add(p.id)

    if not pedido_ids:
        return

    # Garante que cancelamentos de EmbarqueItem aplicados em routes.py:1011
    # estejam visiveis ao `status_calculado` (que re-consulta EmbarqueItem).
    # Sem o flush, a property pode ler identity map stale e retornar 'EMBARCADO'
    # para um pedido cujo unico item acabou de ser marcado 'cancelado'.
    db.session.flush()

    resetados = 0
    for pid in pedido_ids:
        pedido = db.session.get(CarviaPedido, pid)
        if not pedido or pedido.status == 'CANCELADO':
            continue

        novo_status = pedido.status_calculado  # property: reconstroi de EmbarqueItem
        if novo_status != pedido.status and novo_status in ('ABERTO', 'COTADO', 'EMBARCADO'):
            logger.info(
                'CarviaPedido %s status %s -> %s (cancel embarque %s)',
                pedido.numero_pedido, pedido.status, novo_status, embarque_id,
            )
            pedido.status = novo_status
            resetados += 1

    if resetados:
        logger.info(
            'Reset de status aplicado em %s CarviaPedido(s) apos cancel embarque %s',
            resetados, embarque_id,
        )
