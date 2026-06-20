"""Contagem de motos por separacao_lote_id (CarVia) para o mapa de roteirizacao.

Espelha o padrao de `financeiro/viabilidade_service.receita_carvia_por_lotes`:
recebe os `separacao_lote_id` selecionados e devolve `{lote: qtd_motos}`,
consumido por `app/carteira/services/mapa_service.py` via LAZY import (R1 — a
carteira le CarVia, CarVia nao le carteira).

FONTE CANONICA da moto = ITEM da NF (`carvia_nf_itens.modelo_moto_id` +
`quantidade`), a MESMA do peso cubado e do simulador (R1 do CarVia). Reusa
`simulador_routes._contar_modelos_por_nf` em vez de duplicar a regra. NAO conta
por `CarviaPedidoItem.modelo_moto_id` — esse campo e NULL em 100% dos itens de
pedido; as motos so existem na NF.

Resolucao por prefixo de lote (os unicos que o mapa monta — ver
`mapa_service._obter_clientes_carvia` e a VIEW `pedidos`):
- `CARVIA-PED-{id}`: NFs do pedido (`CarviaPedidoItem.numero_nf`, excluindo
  `status='CANCELADA'`) + fallback de itens diretos com `modelo_moto_id`
  (pre-faturamento; hoje sempre vazio, mantido por robustez).
- `CARVIA-{cot}`:    cotacao "solta" (sem pedido) -> `CarviaCotacao.qtd_total_motos`
  apenas quando `tipo_material='MOTO'` (motos de `carvia_cotacao_motos`).
- `CARVIA-NF-{id}`:  a NF direto (o mapa nao monta hoje, mas suportado).
- lote NACOM:        0 (conservas Nacom nao transporta motos).
"""
from collections import defaultdict


def qtd_motos_por_lotes(lotes):
    """Retorna {separacao_lote_id: qtd_motos (int)} para os lotes informados.

    Batch (sem N+1): resolve todos os pedidos/NFs de uma vez e conta as motos
    por `nf_id` numa unica passagem pela fonte canonica.
    """
    resultado = {str(l): 0 for l in (lotes or [])}
    if not lotes:
        return resultado

    from app.carvia.models.config_moto import CarviaModeloMoto
    from app.carvia.models.documentos import CarviaNf
    from app.carvia.models.cotacao import (
        CarviaPedidoItem, CarviaCotacao,
    )
    from app.carvia.routes.simulador_routes import _contar_modelos_por_nf

    ped_ids, cot_ids, nf_ids = set(), set(), set()
    for lote in lotes:
        s = str(lote)
        try:
            if s.startswith('CARVIA-NF-'):
                nf_ids.add(int(s.rsplit('-', 1)[1]))
            elif s.startswith('CARVIA-PED-'):
                ped_ids.add(int(s.rsplit('-', 1)[1]))
            elif s.startswith('CARVIA-'):
                cot_ids.add(int(s.rsplit('-', 1)[1]))
        except (ValueError, IndexError):
            pass  # lote malformado -> permanece 0

    # 1. Itens dos pedidos -> numero_nf por pedido + itens diretos (fallback)
    numeros_nf_por_ped = defaultdict(set)
    diretos_por_ped = defaultdict(int)
    todos_numeros = set()
    if ped_ids:
        itens = CarviaPedidoItem.query.filter(
            CarviaPedidoItem.pedido_id.in_(list(ped_ids))
        ).all()
        for it in itens:
            num = (it.numero_nf or '').strip()
            if num:
                numeros_nf_por_ped[it.pedido_id].add(num)
                todos_numeros.add(num)
            elif it.modelo_moto_id:
                diretos_por_ped[it.pedido_id] += int(it.quantidade or 0)

    # 2. numero_nf -> nf_id (exclui CANCELADA — numero_nf nao e unico) em batch
    nf_ids_por_numero = defaultdict(set)
    numeros_nf_ids = set()
    if todos_numeros:
        rows = CarviaNf.query.filter(
            CarviaNf.numero_nf.in_(list(todos_numeros)),
            CarviaNf.status != 'CANCELADA',
        ).with_entities(CarviaNf.id, CarviaNf.numero_nf).all()
        for nid, num in rows:
            nf_ids_por_numero[(num or '').strip()].add(nid)
            numeros_nf_ids.add(nid)

    # 3. Contar motos por nf_id (fonte canonica) — 1 query
    todos_nf_ids = numeros_nf_ids | nf_ids
    motos_por_nf = {}
    if todos_nf_ids:
        modelos_dict = {
            m.id: m for m in CarviaModeloMoto.query.filter_by(ativo=True).all()
        }
        por_nf = _contar_modelos_por_nf(list(todos_nf_ids), modelos_dict)
        motos_por_nf = {
            nid: sum(bucket['modelos'].values())
            for nid, bucket in por_nf.items()
        }

    # 4. Atribuir por lote
    for lote in lotes:
        s = str(lote)
        try:
            if s.startswith('CARVIA-NF-'):
                resultado[s] = motos_por_nf.get(int(s.rsplit('-', 1)[1]), 0)
            elif s.startswith('CARVIA-PED-'):
                pid = int(s.rsplit('-', 1)[1])
                total = diretos_por_ped.get(pid, 0)
                for num in numeros_nf_por_ped.get(pid, ()):
                    for nid in nf_ids_por_numero.get(num, ()):
                        total += motos_por_nf.get(nid, 0)
                resultado[s] = total
            elif s.startswith('CARVIA-'):
                cot = CarviaCotacao.query.get(int(s.rsplit('-', 1)[1]))
                if cot and cot.tipo_material == 'MOTO':
                    resultado[s] = int(cot.qtd_total_motos or 0)
        except (ValueError, IndexError):
            pass

    return resultado
