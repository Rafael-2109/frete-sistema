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

        # 4b. VALIDACAO B4: modelos da NF presentes na cotacao
        # Se a NF traz modelo que nao existe em CarviaCotacaoMoto,
        # NAO expandir — retornar para frontend abrir modal de backfill.
        # Provisorio fica intacto ate o usuario cadastrar os modelos faltantes
        # via POST /carvia/api/cotacoes/{id}/backfill-modelos.
        modelos_faltantes = (
            EmbarqueCarViaService.validar_modelos_da_nf_contra_cotacao(
                carvia_cotacao_id, nf_obj
            ) if nf_obj else []
        )
        if modelos_faltantes:
            logger.warning(
                "expandir_provisorio AGUARDA backfill: cotacao %s NF %s "
                "modelos_faltantes=%s",
                carvia_cotacao_id, numero_nf,
                [m['modelo_nome'] for m in modelos_faltantes],
            )
            return {
                'acao': 'aguardando_backfill',
                'embarque_id': embarque_id,
                'cotacao_id': carvia_cotacao_id,
                'pedido_id': pedido_id,
                'numero_nf': numero_nf,
                'nf_id': nf_id,
                'modelos_faltantes': modelos_faltantes,
            }

        dest = cotacao.endereco_destino

        # ----------------------------------------------------------------
        # Fase B (2026-05-11): Detectar divergencia CNPJ destino
        # ----------------------------------------------------------------
        # Compara cnpj_destinatario da NF vs cnpj do endereco destino da
        # cotacao. Se divergem (mesmo grupo ou outro CNPJ), o item de
        # embarque ja nasce com os dados da NF (regra "afrouxada": a NF
        # e fonte de verdade fiscal). A NF e marcada com
        # divergencia_cnpj_cotacao=True para a UI alertar o operador, que
        # pode decidir entre "atualizar cotacao" (B4) ou "manter" (B4b).
        from app.utils.cnpj_utils import normalizar_cnpj as _norm_cnpj
        cnpj_dest_cotacao = (dest.cnpj if dest else '') or ''
        cnpj_dest_nf = (nf_obj.cnpj_destinatario if nf_obj else '') or ''
        divergencia_cnpj = bool(
            cnpj_dest_cotacao and cnpj_dest_nf
            and _norm_cnpj(cnpj_dest_cotacao) != _norm_cnpj(cnpj_dest_nf)
        )
        if divergencia_cnpj and nf_obj:
            if not nf_obj.divergencia_cnpj_cotacao:
                nf_obj.divergencia_cnpj_cotacao = True
            logger.warning(
                "Fase B: NF %s (id=%s) cnpj_destinatario=%s diverge da "
                "cotacao %s (endereco_destino_id=%s cnpj=%s). "
                "EmbarqueItem nascera com dados da NF.",
                numero_nf, nf_obj.id, cnpj_dest_nf,
                carvia_cotacao_id,
                (dest.id if dest else None), cnpj_dest_cotacao,
            )
            # B2-G3: Em FRACIONADA, mudanca de UF/cidade pode invalidar
            # snapshot da tabela (icms_destino, valor_kg, etc) carregado
            # com a cidade antiga. Sinaliza para revisao manual do custo
            # do CarviaFrete que sera gerado. Nao bloqueia.
            uf_dest_cotacao = (dest.fisico_uf if dest else None) or ''
            uf_dest_nf = nf_obj.uf_destinatario or ''
            modalidade_item = getattr(item_alvo, 'modalidade', '') or ''
            if (
                uf_dest_cotacao and uf_dest_nf
                and uf_dest_cotacao.upper() != uf_dest_nf.upper()
                and modalidade_item.upper() == 'FRACIONADA'
            ):
                logger.warning(
                    "Fase B2-G3: UF destino mudou (%s -> %s) em item "
                    "FRACIONADA (item=%s cot=%s NF=%s). Snapshot de tabela "
                    "carregado com UF antiga pode estar incorreto (ICMS, "
                    "valor_kg). REVISAR custo do CarviaFrete gerado.",
                    uf_dest_cotacao, uf_dest_nf, item_alvo.id,
                    carvia_cotacao_id, numero_nf,
                )

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

            # Em caso de divergencia CNPJ destino, a NF prevalece (Fase B).
            cnpj_cliente_novo = (
                nf_obj.cnpj_destinatario
                if (divergencia_cnpj and nf_obj and nf_obj.cnpj_destinatario)
                else (dest.cnpj if dest else (item_alvo.cnpj_cliente or ''))
            )
            cliente_novo = (
                nf_obj.nome_destinatario
                if (divergencia_cnpj and nf_obj and nf_obj.nome_destinatario)
                else (item_alvo.cliente or (cotacao.cliente.nome_comercial if cotacao.cliente else ''))
            )
            uf_destino_novo = (
                nf_obj.uf_destinatario
                if (divergencia_cnpj and nf_obj and nf_obj.uf_destinatario)
                else (item_alvo.uf_destino or (dest.fisico_uf if dest else ''))
            )
            cidade_destino_novo = (
                nf_obj.cidade_destinatario
                if (divergencia_cnpj and nf_obj and nf_obj.cidade_destinatario)
                else (item_alvo.cidade_destino or (dest.fisico_cidade if dest else ''))
            )
            novo_item = EmbarqueItem(
                embarque_id=embarque_id,
                separacao_lote_id=lote_id_nf,
                cnpj_cliente=cnpj_cliente_novo,
                cliente=cliente_novo,
                pedido=pedido.numero_pedido,
                nota_fiscal=numero_nf,
                peso=nf_peso,
                peso_cubado=round(_nf_cubado, 2) if _nf_cubado > 0 else item_alvo.peso_cubado,
                valor=nf_valor,
                pallets=0,
                uf_destino=uf_destino_novo,
                cidade_destino=cidade_destino_novo,
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

            # Fase B: se NF tem CNPJ destinatario diferente da cotacao,
            # propaga para o item (NF e fonte de verdade fiscal). Antes
            # nao atualizava, gerando inconsistencia downstream (CarviaFrete
            # agrupava por cnpj antigo, validar_nf_cliente bloqueava).
            if divergencia_cnpj and nf_obj:
                cnpj_old = item_alvo.cnpj_cliente
                if nf_obj.cnpj_destinatario:
                    item_alvo.cnpj_cliente = nf_obj.cnpj_destinatario
                if nf_obj.nome_destinatario:
                    item_alvo.cliente = nf_obj.nome_destinatario
                if nf_obj.uf_destinatario:
                    item_alvo.uf_destino = nf_obj.uf_destinatario
                if nf_obj.cidade_destinatario:
                    item_alvo.cidade_destino = nf_obj.cidade_destinatario
                logger.warning(
                    "Item legado: cnpj_cliente atualizado %s -> %s "
                    "(item=%s NF=%s)",
                    cnpj_old, nf_obj.cnpj_destinatario,
                    item_alvo.id, numero_nf,
                )

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
    def resolver_lote_carvia(lote_id: str, embarque_id: Optional[int] = None) -> Optional[Dict]:
        """Resolve separacao_lote_id CarVia para dados de cotacao/pedido/veiculos.

        Suporta todos os padroes:
          CARVIA-NF-{nf_id}   → item real (NF anexada) — escopo limitado a UMA NF
          CARVIA-COT-{cot_id} → provisorio recriado
          CARVIA-PED-{ped_id} → legado (backward compat) — escopo de todas NFs do pedido
          CARVIA-{id}         → provisorio original

        Args:
            lote_id: separacao_lote_id (prefixo CARVIA-*)
            embarque_id: opcional — se fornecido, busca o EmbarqueItem alvo para
                expor `embarque_item`, `rota`, `sub_rota`, `transportadora`,
                e calcula `resumo` (totalizadores prontos para impressao).

        Retorna dict com: cotacao, pedido, itens_pedido (filtrados pela NF do
        lote quando CARVIA-NF-*), motos, veiculos_por_nf, peso_bruto_nf,
        peso_cubado_nf, filial, eh_pedido, observacoes, nf_corrente,
        nf_obj_corrente, embarque_item, rota, sub_rota, transportadora, resumo.
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
        nf_corrente = None
        nf_obj_corrente = None

        try:
            if lote.startswith('CARVIA-NF-'):
                # Item real: NF anexada ao pedido — escopo LIMITADO a UMA NF
                nf_id = int(lote.replace('CARVIA-NF-', ''))
                nf_obj_corrente = db.session.get(CarviaNf, nf_id)
                if nf_obj_corrente:
                    nf_corrente = str(nf_obj_corrente.numero_nf)
                    # Achar PedidoItem com esse numero_nf
                    pi = CarviaPedidoItem.query.filter_by(
                        numero_nf=nf_corrente
                    ).first()
                    if pi:
                        pedido = db.session.get(CarviaPedido, pi.pedido_id)
                        if pedido:
                            cotacao = db.session.get(CarviaCotacao, pedido.cotacao_id)
                            # Filtra itens_pedido APENAS pela NF deste lote
                            itens_pedido = CarviaPedidoItem.query.filter_by(
                                pedido_id=pedido.id,
                                numero_nf=nf_corrente,
                            ).all()
                            eh_pedido = True

            elif lote.startswith('CARVIA-COT-'):
                # Provisorio recriado apos exclusao de pedido
                cot_id = int(lote.replace('CARVIA-COT-', ''))
                cotacao = db.session.get(CarviaCotacao, cot_id)

            elif lote.startswith('CARVIA-PED-'):
                # Legado: padrao antigo (backward compat) — todas NFs do pedido
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
        if nf_corrente and nf_obj_corrente:
            # CARVIA-NF-*: APENAS a NF deste lote
            veiculos_por_nf[nf_corrente] = nf_obj_corrente.veiculos.all()
            peso_bruto_nf = float(nf_obj_corrente.peso_bruto or 0)
            volumes_nf = int(nf_obj_corrente.quantidade_volumes or 0)
        elif eh_pedido:
            # CARVIA-PED-* legado: todas as NFs do pedido
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
        # Mapa modelo_nome → cubado unitario (a partir das motos da cotacao)
        cubado_por_modelo = {}
        for m in CarviaCotacaoMoto.query.filter_by(cotacao_id=cotacao.id).all():
            if m.modelo_moto and m.quantidade and m.quantidade > 0:
                cubado_por_modelo[m.modelo_moto.nome.upper()] = (
                    float(m.peso_cubado_total or 0) / int(m.quantidade)
                )
        # Somar cubado de cada veiculo das NFs do escopo (toda do pedido OU so a NF)
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

        # ==========================================================
        # ENRIQUECIMENTO p/ impressao (so quando embarque_id passado)
        # ==========================================================
        embarque_item = None
        rota = None
        sub_rota = None
        transportadora = None
        resumo = None

        if embarque_id:
            from app.embarques.models import EmbarqueItem, Embarque
            from app.localidades.models import CadastroRota, CadastroSubRota

            embarque_item = EmbarqueItem.query.filter_by(
                embarque_id=embarque_id,
                separacao_lote_id=lote,
                status='ativo',
            ).first()

            emb_obj = db.session.get(Embarque, embarque_id)
            if emb_obj and emb_obj.transportadora:
                transportadora = emb_obj.transportadora

            # Rota/sub_rota: mesma logica da VIEW pedidos (cadastro_rota por UF)
            dest = cotacao.endereco_destino if cotacao else None
            uf_lookup = (
                (embarque_item.uf_destino if embarque_item else None)
                or (dest.fisico_uf if dest else None)
            )
            cidade_lookup = (
                (embarque_item.cidade_destino if embarque_item else None)
                or (dest.fisico_cidade if dest else None)
            )
            if uf_lookup:
                cr = CadastroRota.query.filter_by(
                    cod_uf=uf_lookup, ativa=True
                ).first()
                if cr:
                    rota = cr.rota
            if uf_lookup and cidade_lookup:
                # Match accent+case-insensitive: alinhado com a busca canonica
                # `buscar_sub_rota_por_uf_cidade` (app/carteira/utils/separacao_utils.py)
                # e com a VIEW pedidos atualizada (f_unaccent). CarVia recebe
                # cidades de varias fontes (endereco destino do cliente, embarque
                # item) sem padrao de acento/caixa.
                from app.utils.string_utils import remover_acentos
                cidade_norm = remover_acentos(cidade_lookup)
                candidatas = CadastroSubRota.query.filter(
                    CadastroSubRota.cod_uf == uf_lookup,
                    CadastroSubRota.ativa == True,  # noqa: E712
                ).all()
                for csr in candidatas:
                    nome_csr = remover_acentos(csr.nome_cidade or '')
                    if nome_csr and nome_csr in cidade_norm:
                        sub_rota = csr.sub_rota
                        break

            # Resumo (totalizadores prontos para o template)
            resumo = EmbarqueCarViaService._construir_resumo_impressao(
                cotacao=cotacao,
                itens_pedido=itens_pedido,
                motos=motos,
                nf_obj_corrente=nf_obj_corrente,
                peso_bruto_nf=peso_bruto_nf,
                peso_cubado_nf=peso_cubado_nf,
                volumes_nf=volumes_nf,
                eh_pedido=eh_pedido,
                embarque_item=embarque_item,
            )

        return {
            'cotacao': cotacao,
            'pedido': pedido,
            'itens_pedido': itens_pedido,
            'motos': motos,
            'veiculos_por_nf': veiculos_por_nf,
            'peso_bruto_nf': peso_bruto_nf,
            'peso_cubado_nf': peso_cubado_nf,
            'volumes_nf': volumes_nf,
            'filial': filial,
            'eh_pedido': eh_pedido,
            'observacoes': observacoes,
            'nf_corrente': nf_corrente,
            'nf_obj_corrente': nf_obj_corrente,
            'embarque_item': embarque_item,
            'rota': rota,
            'sub_rota': sub_rota,
            'transportadora': transportadora,
            'resumo': resumo,
        }

    @staticmethod
    def adicionar_item_dedup(item) -> Dict:
        """Adiciona EmbarqueItem com dedup defensivo (BUG B1).

        Verifica se ja existe item ativo com mesmo (embarque_id, separacao_lote_id).
        - Se provisorio + ja existe ativo: skip (mantem registro original)
        - Se nao-provisorio + ja existe ativo: skip (idempotent)
        - Senao: db.session.add(item)

        Retorna {'acao': 'adicionado' | 'dedup_skip', 'item_id': int | None}.

        Uso em app/cotacao/routes.py callsites que criam provisorio CARVIA-*.
        Proteje contra race condition antes do partial unique index estar criado
        e contra retry/double-submit do usuario.
        """
        from app.embarques.models import EmbarqueItem

        if not item.embarque_id or not item.separacao_lote_id:
            db.session.add(item)
            return {'acao': 'adicionado', 'item_id': None}

        existente = EmbarqueItem.query.filter_by(
            embarque_id=item.embarque_id,
            separacao_lote_id=item.separacao_lote_id,
            status='ativo',
        ).first()

        if existente:
            logger.info(
                "F1 dedup: item %s ja existe no embarque %s (id=%s) — skip",
                item.separacao_lote_id, item.embarque_id, existente.id,
            )
            return {'acao': 'dedup_skip', 'item_id': existente.id}

        db.session.add(item)
        return {'acao': 'adicionado', 'item_id': None}

    @staticmethod
    def validar_modelos_da_nf_contra_cotacao(
        carvia_cotacao_id: int, nf_obj,
    ) -> List[Dict]:
        """Verifica se modelos trazidos pela NF estao todos cadastrados na cotacao.

        Compara `CarviaNfVeiculo.modelo` (uppercase) com
        `CarviaCotacaoMoto.modelo_moto.nome` da cotacao. Match exato OU
        substring (mesma logica de `calcular_cubado_por_modelos`).

        Args:
            carvia_cotacao_id: ID da cotacao alvo.
            nf_obj: CarviaNf instancia. Se None/sem veiculos, retorna [].

        Returns:
            Lista de dicts (vazia se tudo OK):
            [
              {
                'modelo_nome': str (do veiculo da NF),
                'modelo_moto_id_existente': int | None,
                'quantidade': int,
                'valor_unitario_sugerido': float,
                'valor_total_sugerido': float,
              },
              ...
            ]
        """
        from app.carvia.models import CarviaCotacaoMoto, CarviaModeloMoto

        if not nf_obj:
            return []

        veiculos = nf_obj.veiculos.all() if hasattr(nf_obj, 'veiculos') else []
        if not veiculos:
            return []

        modelos_cotacao = set()
        for m in CarviaCotacaoMoto.query.filter_by(
            cotacao_id=carvia_cotacao_id
        ).all():
            if m.modelo_moto and m.modelo_moto.nome:
                modelos_cotacao.add(m.modelo_moto.nome.upper())

        agregado: Dict[str, Dict] = {}
        for v in veiculos:
            mod = (v.modelo or '').strip()
            if not mod:
                continue
            mod_upper = mod.upper()
            existe = mod_upper in modelos_cotacao
            if not existe:
                for nome_cot in modelos_cotacao:
                    if nome_cot and (nome_cot in mod_upper or mod_upper in nome_cot):
                        existe = True
                        break
            if existe:
                continue
            entry = agregado.setdefault(mod_upper, {
                'modelo_nome': mod,
                'quantidade': 0,
                'valor_total': 0.0,
            })
            entry['quantidade'] += 1
            entry['valor_total'] += float(v.valor or 0)

        if not agregado:
            return []

        nomes_faltantes = list(agregado.keys())
        candidatos_mm = CarviaModeloMoto.query.filter(
            CarviaModeloMoto.ativo == True,  # noqa: E712
        ).all()
        modelos_existentes = {mm.nome.upper(): mm.id for mm in candidatos_mm}

        resultado = []
        for mod_upper, entry in agregado.items():
            modelo_id_existente = modelos_existentes.get(mod_upper)
            if modelo_id_existente is None:
                for nome_mm, id_mm in modelos_existentes.items():
                    if nome_mm in mod_upper or mod_upper in nome_mm:
                        modelo_id_existente = id_mm
                        break
            valor_unit = (
                entry['valor_total'] / entry['quantidade']
                if entry['quantidade'] > 0 else 0
            )
            resultado.append({
                'modelo_nome': entry['modelo_nome'],
                'modelo_moto_id_existente': modelo_id_existente,
                'quantidade': entry['quantidade'],
                'valor_unitario_sugerido': round(valor_unit, 2),
                'valor_total_sugerido': round(entry['valor_total'], 2),
            })

        return resultado

    @staticmethod
    def _recalcular_provisorio_saldo(
        carvia_cotacao_id: int, embarque_id: Optional[int] = None,
    ) -> Optional[Dict]:
        """Recalcula peso/valor/volumes do provisorio CARVIA-{cot_id}.

        Logica: provisorio = totais_da_cotacao - sum(CARVIA-NF-* ativos).

        Chamado apos:
          - Backfill de CarviaCotacaoMoto (B4 / F4c).
          - Atualizacao manual de motos da cotacao.
          - Adicao de pedido com itens nao previstos.

        Returns:
            Dict {acao, embarque_id, vol_antigo, vol_novo, peso_novo, valor_novo}
            ou None se nao ha provisorio.
        """
        from app.embarques.models import EmbarqueItem
        from app.carvia.models import CarviaCotacao, CarviaCotacaoMoto
        from sqlalchemy import func as _func

        query = EmbarqueItem.query.filter_by(
            carvia_cotacao_id=carvia_cotacao_id,
            provisorio=True,
            status='ativo',
        )
        if embarque_id:
            query = query.filter_by(embarque_id=embarque_id)
        provisorio = query.first()

        if not provisorio:
            logger.info(
                "_recalcular_provisorio_saldo: nao ha provisorio ativo "
                "cotacao=%s embarque=%s",
                carvia_cotacao_id, embarque_id,
            )
            return None

        cotacao = db.session.get(CarviaCotacao, carvia_cotacao_id)
        if not cotacao:
            return None

        emb_id = provisorio.embarque_id

        if cotacao.tipo_material == 'MOTO':
            motos_q = db.session.query(
                _func.coalesce(_func.sum(CarviaCotacaoMoto.quantidade), 0),
                _func.coalesce(_func.sum(CarviaCotacaoMoto.peso_cubado_total), 0),
                _func.coalesce(_func.sum(CarviaCotacaoMoto.valor_total), 0),
            ).filter_by(cotacao_id=carvia_cotacao_id).first() or (0, 0, 0)
            cot_vol = int(motos_q[0] or 0)
            cot_cubado = float(motos_q[1] or 0)
            cot_valor = float(motos_q[2] or 0)
            cot_peso = float(cotacao.peso or 0)
        else:
            cot_vol = int(cotacao.volumes or 0)
            cot_cubado = float(cotacao.peso_cubado or 0)
            cot_peso = float(cotacao.peso or 0)
            cot_valor = float(cotacao.valor_mercadoria or 0)

        consumido = db.session.query(
            _func.coalesce(_func.sum(EmbarqueItem.volumes), 0),
            _func.coalesce(_func.sum(EmbarqueItem.peso), 0),
            _func.coalesce(_func.sum(EmbarqueItem.peso_cubado), 0),
            _func.coalesce(_func.sum(EmbarqueItem.valor), 0),
        ).filter(
            EmbarqueItem.embarque_id == emb_id,
            EmbarqueItem.carvia_cotacao_id == carvia_cotacao_id,
            EmbarqueItem.status == 'ativo',
            EmbarqueItem.provisorio == False,  # noqa: E712
        ).first() or (0, 0, 0, 0)

        vol_c = int(consumido[0] or 0)
        peso_c = float(consumido[1] or 0)
        cub_c = float(consumido[2] or 0)
        val_c = float(consumido[3] or 0)

        vol_antigo = provisorio.volumes
        novo_vol = max(0, cot_vol - vol_c)
        novo_peso = max(0, cot_peso - peso_c)
        novo_cub = max(0, cot_cubado - cub_c)
        novo_val = max(0, cot_valor - val_c)

        if novo_vol <= 0:
            db.session.delete(provisorio)
            logger.info(
                "_recalcular_provisorio_saldo: provisorio DELETADO "
                "(cotacao %s 100%% resolvida)", carvia_cotacao_id,
            )
            acao = 'deletado'
        else:
            provisorio.volumes = novo_vol
            provisorio.peso = round(novo_peso, 3)
            provisorio.peso_cubado = round(novo_cub, 3) if novo_cub > 0 else None
            provisorio.valor = round(novo_val, 2)
            acao = 'atualizado'
            logger.info(
                "_recalcular_provisorio_saldo: cotacao %s saldo %s -> %s vol",
                carvia_cotacao_id, vol_antigo, novo_vol,
            )

        EmbarqueCarViaService._recalcular_totais(emb_id)

        return {
            'acao': acao,
            'embarque_id': emb_id,
            'vol_antigo': vol_antigo,
            'vol_novo': novo_vol,
            'peso_novo': novo_peso,
            'valor_novo': novo_val,
        }

    @staticmethod
    def _construir_resumo_impressao(
        cotacao, itens_pedido, motos,
        nf_obj_corrente, peso_bruto_nf, peso_cubado_nf, volumes_nf,
        eh_pedido, embarque_item,
    ) -> Dict:
        """Calcula totalizadores prontos para a impressao da separacao CarVia.

        Comportamento:
          - eh_pedido + nf_obj_corrente (CARVIA-NF-*): usa peso/valor/volumes
            da NF especifica.
          - eh_pedido sem NF (CARVIA-PED-* legado): soma itens_pedido +
            peso bruto/cubado/volumes agregados das NFs.
          - Provisorio (cotacao): usa dados da cotacao (peso_cubado_motos
            para MOTO, peso/peso_cubado/volumes/valor_mercadoria para
            CARGA_GERAL) com fallback no EmbarqueItem para saldo.
        """
        qtd_total = 0
        valor_total = 0.0
        peso_bruto_total = float(peso_bruto_nf or 0)
        peso_cubado_total = float(peso_cubado_nf or 0)
        volumes_total = int(volumes_nf or 0)

        if eh_pedido:
            # Itens do pedido (filtrados pela NF se CARVIA-NF-*)
            for it in itens_pedido or []:
                qtd_total += int(it.quantidade or 0)
                valor_total += float(it.valor_total or 0)
            # Se NF especifica: valor da NF preferencialmente
            if nf_obj_corrente:
                valor_nf = float(nf_obj_corrente.valor_total or 0)
                if valor_nf > 0:
                    valor_total = valor_nf
        else:
            # Provisorio: usar dados da cotacao
            if cotacao.tipo_material == 'MOTO' and motos:
                qtd_total = sum(int(m.quantidade or 0) for m in motos)
                valor_total = float(cotacao.valor_mercadoria or 0)
                peso_cubado_total = float(cotacao.peso_total_motos or 0)
                peso_bruto_total = float(cotacao.peso or 0)
                volumes_total = qtd_total  # 1 volume por moto
            else:
                # CARGA_GERAL provisorio: dados diretos da cotacao
                qtd_total = int(cotacao.volumes or 0)
                valor_total = float(cotacao.valor_mercadoria or 0)
                peso_bruto_total = float(cotacao.peso or 0)
                peso_cubado_total = float(cotacao.peso_cubado or 0)
                volumes_total = int(cotacao.volumes or 0)

            # Fallback para EmbarqueItem (caso provisorio ja deduzido)
            if embarque_item:
                if embarque_item.peso and embarque_item.peso > 0:
                    peso_bruto_total = float(embarque_item.peso)
                if embarque_item.peso_cubado and embarque_item.peso_cubado > 0:
                    peso_cubado_total = float(embarque_item.peso_cubado)
                if embarque_item.volumes:
                    volumes_total = int(embarque_item.volumes)
                if embarque_item.valor and embarque_item.valor > 0:
                    valor_total = float(embarque_item.valor)

        # pallets nao se aplicam a CarVia (motos nao palletizam, geral nao tem cadastro)
        pallets_total = 0.0
        if embarque_item and embarque_item.pallets:
            pallets_total = float(embarque_item.pallets)

        return {
            'qtd': qtd_total,
            'valor': round(valor_total, 2),
            'peso_bruto': round(peso_bruto_total, 2),
            'peso_cubado': round(peso_cubado_total, 2),
            'volumes': volumes_total,
            'pallets': pallets_total,
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


def coletar_documentos_pedidos(pedido_ids):
    """Retorna {pedido_id: {'ctes': [CarviaOperacao], 'faturas': [CarviaFaturaCliente]}}.

    Batch query — sem N+1. Usado para popular listagens (pedidos, cotacoes)
    com badges de CTe e Fatura sem performance ruim.

    Chave de junção:
        pedido -> CarviaPedidoItem.numero_nf
        -> CarviaNf
        -> CarviaOperacaoNf -> CarviaOperacao (CTes ativos)
        -> CarviaOperacao.fatura_cliente_id -> CarviaFaturaCliente
    """
    from app.carvia.models import (
        CarviaPedido, CarviaPedidoItem, CarviaNf,
        CarviaOperacao, CarviaOperacaoNf,
    )
    from app.carvia.models.faturas import CarviaFaturaCliente

    resultado = {pid: {'ctes': [], 'faturas': []} for pid in pedido_ids}
    if not pedido_ids:
        return resultado

    # Mapa pedido_id -> conjunto de numeros_nf
    pedido_nfs = {}
    rows = (
        db.session.query(CarviaPedidoItem.pedido_id, CarviaPedidoItem.numero_nf)
        .filter(
            CarviaPedidoItem.pedido_id.in_(pedido_ids),
            CarviaPedidoItem.numero_nf.isnot(None),
            CarviaPedidoItem.numero_nf != '',
        )
        .all()
    )
    for pid, nf_num in rows:
        pedido_nfs.setdefault(pid, set()).add(str(nf_num))

    if not pedido_nfs:
        return resultado

    # Universo de numeros_nf para 1 query
    todos_nfs = set()
    for nfs in pedido_nfs.values():
        todos_nfs.update(nfs)

    # Mapa numero_nf -> nf_id (mesmos numero podem aparecer N vezes — pega o ATIVO mais recente)
    nfs = (
        CarviaNf.query
        .filter(CarviaNf.numero_nf.in_(list(todos_nfs)))
        .order_by(CarviaNf.id.desc())
        .all()
    )
    nf_num_to_id = {}
    nf_id_to_obj = {}
    for nf in nfs:
        if str(nf.numero_nf) not in nf_num_to_id:
            nf_num_to_id[str(nf.numero_nf)] = nf.id
        nf_id_to_obj[nf.id] = nf

    if not nf_num_to_id:
        return resultado

    # Mapa nf_id -> [operacao_id]
    junctions = (
        db.session.query(CarviaOperacaoNf.nf_id, CarviaOperacaoNf.operacao_id)
        .filter(CarviaOperacaoNf.nf_id.in_(list(nf_num_to_id.values())))
        .all()
    )
    nf_id_to_op_ids = {}
    todos_op_ids = set()
    for nf_id, op_id in junctions:
        nf_id_to_op_ids.setdefault(nf_id, []).append(op_id)
        todos_op_ids.add(op_id)

    if not todos_op_ids:
        return resultado

    # Mapa operacao_id -> CarviaOperacao (ativa)
    ops = (
        CarviaOperacao.query
        .filter(
            CarviaOperacao.id.in_(list(todos_op_ids)),
            CarviaOperacao.status != 'CANCELADO',
        )
        .all()
    )
    op_id_to_obj = {op.id: op for op in ops}

    # Mapa fatura_id -> CarviaFaturaCliente
    fat_ids = {op.fatura_cliente_id for op in ops if op.fatura_cliente_id}
    fat_id_to_obj = {}
    if fat_ids:
        faturas = CarviaFaturaCliente.query.filter(
            CarviaFaturaCliente.id.in_(list(fat_ids))
        ).all()
        fat_id_to_obj = {f.id: f for f in faturas}

    # Montar resultado por pedido
    for pid, nfs_set in pedido_nfs.items():
        ctes_seen = set()
        faturas_seen = set()
        for nf_num in nfs_set:
            nf_id = nf_num_to_id.get(nf_num)
            if not nf_id:
                continue
            for op_id in nf_id_to_op_ids.get(nf_id, []):
                op_obj = op_id_to_obj.get(op_id)
                if op_obj and op_obj.id not in ctes_seen:
                    ctes_seen.add(op_obj.id)
                    resultado[pid]['ctes'].append(op_obj)
                    if op_obj.fatura_cliente_id and op_obj.fatura_cliente_id not in faturas_seen:
                        fat = fat_id_to_obj.get(op_obj.fatura_cliente_id)
                        if fat:
                            faturas_seen.add(fat.id)
                            resultado[pid]['faturas'].append(fat)

    return resultado


def coletar_documentos_cotacoes(cotacao_ids):
    """Retorna {cotacao_id: {'ctes': [...], 'faturas': [...]}}.

    Mesma logica que `coletar_documentos_pedidos` mas agregando por cotacao
    via todos os pedidos nao-cancelados de cada cotacao.
    """
    from app.carvia.models import CarviaPedido

    resultado = {cid: {'ctes': [], 'faturas': []} for cid in cotacao_ids}
    if not cotacao_ids:
        return resultado

    pedidos = (
        CarviaPedido.query
        .filter(
            CarviaPedido.cotacao_id.in_(list(cotacao_ids)),
            CarviaPedido.status != 'CANCELADO',
        )
        .all()
    )
    pid_to_cot = {p.id: p.cotacao_id for p in pedidos}
    pid_list = list(pid_to_cot.keys())
    if not pid_list:
        return resultado

    docs_por_pedido = coletar_documentos_pedidos(pid_list)

    for pid, docs in docs_por_pedido.items():
        cot_id = pid_to_cot.get(pid)
        if not cot_id:
            continue
        ctes_seen = {c.id for c in resultado[cot_id]['ctes']}
        faturas_seen = {f.id for f in resultado[cot_id]['faturas']}
        for cte in docs['ctes']:
            if cte.id not in ctes_seen:
                ctes_seen.add(cte.id)
                resultado[cot_id]['ctes'].append(cte)
        for fat in docs['faturas']:
            if fat.id not in faturas_seen:
                faturas_seen.add(fat.id)
                resultado[cot_id]['faturas'].append(fat)

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
        # P12 (2026-04-24): EMBARCADO removido do dominio de status. Whitelist
        # alinhada com `ck_carvia_pedido_status` (ABERTO, COTADO, FATURADO, CANCELADO).
        if novo_status != pedido.status and novo_status in ('ABERTO', 'COTADO', 'FATURADO'):
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
