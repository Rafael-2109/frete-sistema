"""Backfill: preencher `EmbarqueItem.volumes` (= qtd de motos) dos itens CarVia.

Contexto: os itens CarVia de embarque nasciam com `volumes` inconsistente —
`None`/`0` (varios call sites de fechar_frete/incluir_em_embarque) ou
`CarviaNf.quantidade_volumes` (volume FISICO de transporte do XML `<vol>/<qVol>`,
NAO a qtd de motos) no `expandir_provisorio`. Em prod (2026-06-23): de 352 itens
CarVia ativos, 146 com `volumes=0`, 45 com `1`, 3 NULL — dos 149 vazios em
`CARVIA-PED-*`, 91 recuperaveis pela NF (476 motos). O fix de codigo passa a usar
a fonte canonica (= max(chassis, itens-modelo) por NF; fallback
`CarviaCotacao.qtd_total_motos`) em TODOS os pontos de escrita; este script
corrige o passado. Idempotente.

Contagem das motos por NF reusa a fonte canonica
`CarviaPortalStatusService._qtd_motos_por_nf` (a MESMA do Portal/Gerencial e do
helper `qtd_motos_carvia`). A resolucao lote->NF e' feita em BATCH (poucas
queries) porque o banco de prod e' remoto (Oregon) — item-a-item estoura timeout.

So atualiza quando a qtd de motos resolvida e' > 0 e diverge do `volumes` atual.
NUNCA zera um `volumes` ja preenchido (carga geral / volume manual fica intacto
quando nao ha motos resolviveis).

Uso (prod):
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/migrations/2026_06_23_backfill_volumes_motos_embarque_carvia.py          # dry-run
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/migrations/2026_06_23_backfill_volumes_motos_embarque_carvia.py --apply  # efetiva
"""
import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402
from app.embarques.models import EmbarqueItem  # noqa: E402


def _resolver_motos_em_batch(itens):
    """{item_id: qtd_motos} para os EmbarqueItem CarVia, em poucas queries.

    Cascata (igual ao helper qtd_motos_carvia, em batch):
      1. lote CARVIA-NF-{id} -> a NF direto.
      2. lote CARVIA-PED-{id} -> NFs do pedido (CarviaPedidoItem.numero_nf != CANCELADA).
      3. nota_fiscal          -> NF por numero (item sem nf resolvida acima).
      4. fallback             -> CarviaCotacao.qtd_total_motos (tipo MOTO) via
         carvia_cotacao_id ou lote CARVIA-{cot}/CARVIA-COT-{cot}.
    """
    from app.carvia.models.documentos import CarviaNf
    from app.carvia.models.cotacao import CarviaPedidoItem, CarviaCotacaoMoto, CarviaCotacao
    from app.carvia.services.documentos.portal_status_service import (
        CarviaPortalStatusService,
    )

    nf_direto = {}            # item_id -> nf_id
    ped_por_item = {}         # item_id -> ped_id
    cot_por_item = {}         # item_id -> cot_id (fallback)
    numero_por_item = {}      # item_id -> numero_nf (fallback de resolucao)

    def _int_suffix(s):
        try:
            return int(s.rsplit('-', 1)[1])
        except (ValueError, IndexError, AttributeError):
            return None

    for it in itens:
        lote = str(it.separacao_lote_id or '')
        if lote.startswith('CARVIA-NF-'):
            nid = _int_suffix(lote)
            if nid is not None:
                nf_direto[it.id] = nid
        elif lote.startswith('CARVIA-PED-'):
            pid = _int_suffix(lote)
            if pid is not None:
                ped_por_item[it.id] = pid
        # fallback de resolucao por numero da NF
        if (it.nota_fiscal or '').strip():
            numero_por_item[it.id] = it.nota_fiscal.strip()
        # fallback de cotacao
        if it.carvia_cotacao_id:
            cot_por_item[it.id] = it.carvia_cotacao_id
        elif lote.startswith('CARVIA-') and not lote.startswith(('CARVIA-NF-', 'CARVIA-PED-')):
            cid = _int_suffix(lote)
            if cid is not None:
                cot_por_item[it.id] = cid

    # 1 query: numeros_nf por pedido
    numeros_por_ped = defaultdict(set)
    if ped_por_item:
        ped_ids = set(ped_por_item.values())
        rows = (CarviaPedidoItem.query
                .filter(CarviaPedidoItem.pedido_id.in_(ped_ids),
                        CarviaPedidoItem.numero_nf.isnot(None))
                .with_entities(CarviaPedidoItem.pedido_id, CarviaPedidoItem.numero_nf)
                .all())
        for pid, num in rows:
            num = (num or '').strip()
            if num:
                numeros_por_ped[pid].add(num)

    # 1 query: numero_nf -> [nf_id] (exclui CANCELADA; numero nao e unico)
    todos_numeros = set(numero_por_item.values())
    for nums in numeros_por_ped.values():
        todos_numeros |= nums
    nf_ids_por_numero = defaultdict(set)
    if todos_numeros:
        rows = (CarviaNf.query
                .filter(CarviaNf.numero_nf.in_(todos_numeros),
                        CarviaNf.status != 'CANCELADA')
                .with_entities(CarviaNf.id, CarviaNf.numero_nf)
                .all())
        for nid, num in rows:
            nf_ids_por_numero[(num or '').strip()].add(nid)

    # 2 queries (batch): contagem canonica de motos por nf_id
    todos_nf_ids = set(nf_direto.values())
    for nids in nf_ids_por_numero.values():
        todos_nf_ids |= nids
    motos_por_nf = {}
    if todos_nf_ids:
        motos_por_nf = CarviaPortalStatusService._qtd_motos_por_nf(list(todos_nf_ids))

    # 1 query: fallback de cotacao (SUM quantidade das motos por cotacao MOTO)
    motos_por_cot = {}
    cot_ids = set(cot_por_item.values())
    if cot_ids:
        cots_moto = dict(
            CarviaCotacao.query
            .filter(CarviaCotacao.id.in_(cot_ids),
                    CarviaCotacao.tipo_material == 'MOTO')
            .with_entities(CarviaCotacao.id, CarviaCotacao.id).all()
        )
        if cots_moto:
            rows = (db.session.query(
                        CarviaCotacaoMoto.cotacao_id,
                        db.func.coalesce(db.func.sum(CarviaCotacaoMoto.quantidade), 0))
                    .filter(CarviaCotacaoMoto.cotacao_id.in_(cots_moto.keys()))
                    .group_by(CarviaCotacaoMoto.cotacao_id).all())
            motos_por_cot = {cid: int(q or 0) for cid, q in rows}

    # Atribuir por item (mesma cascata do helper)
    resultado = {}
    for it in itens:
        total = 0
        if it.id in nf_direto:
            total = int(motos_por_nf.get(nf_direto[it.id], 0) or 0)
        elif it.id in ped_por_item:
            for num in numeros_por_ped.get(ped_por_item[it.id], ()):
                for nid in nf_ids_por_numero.get(num, ()):
                    total += int(motos_por_nf.get(nid, 0) or 0)
        if total <= 0 and it.id in numero_por_item:
            for nid in nf_ids_por_numero.get(numero_por_item[it.id], ()):
                total += int(motos_por_nf.get(nid, 0) or 0)
        if total <= 0 and it.id in cot_por_item:
            total = int(motos_por_cot.get(cot_por_item[it.id], 0) or 0)
        resultado[it.id] = total
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true',
                        help='Efetiva as alteracoes (default = dry-run).')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        itens = (
            EmbarqueItem.query
            .filter(
                EmbarqueItem.status == 'ativo',
                db.or_(
                    EmbarqueItem.separacao_lote_id.ilike('CARVIA-%'),
                    EmbarqueItem.carvia_cotacao_id.isnot(None),
                ),
            )
            .order_by(EmbarqueItem.id)
            .all()
        )
        motos = _resolver_motos_em_batch(itens)

        alterar = []   # (item, antigo, novo)
        sem_motos = 0
        for item in itens:
            novo = motos.get(item.id, 0)
            if novo and novo > 0:
                if (item.volumes or 0) != novo:
                    alterar.append((item, item.volumes, novo))
            else:
                sem_motos += 1

        print(f"\n{'='*72}")
        print(f"Backfill volumes (qtd motos) — EmbarqueItem CarVia")
        print(f"{'='*72}")
        print(f"Itens CarVia ativos analisados : {len(itens)}")
        print(f"A atualizar (volumes diverge)  : {len(alterar)}")
        print(f"Sem motos resolviveis (preserva): {sem_motos}")
        print(f"{'-'*72}")
        for item, antigo, novo in alterar[:80]:
            print(f"  item={item.id:>6} lote={item.separacao_lote_id or '-':<22} "
                  f"NF={item.nota_fiscal or '-':<10} volumes {antigo} -> {novo}")
        if len(alterar) > 80:
            print(f"  ... (+{len(alterar) - 80} itens)")
        print(f"{'-'*72}")
        total_motos = sum(n for _, _, n in alterar)
        print(f"Total de motos a gravar (linhas alteradas): {total_motos}")

        if not args.apply:
            print("\nDRY-RUN — nada gravado. Rode com --apply para efetivar.\n")
            return

        for item, _antigo, novo in alterar:
            item.volumes = novo
        db.session.commit()
        print(f"\n✅ APLICADO — {len(alterar)} itens atualizados.\n")


if __name__ == '__main__':
    main()
