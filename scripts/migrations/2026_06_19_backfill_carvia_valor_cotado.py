#!/usr/bin/env python3
"""
Backfill do valor_cotado (CUSTO) de CarviaFrete que nasceram com 0.

Contexto: ate o fix d0041eed3, a rota `incluir_em_embarque` ZERAVA a tabela de
frete do item CarVia ("por design"), fazendo o CarviaFrete nascer com
`valor_cotado=0` e `tabela_nome_tabela='0'`. Este script recalcula o custo
RETROATIVO desses fretes reusando a MESMA logica de cotacao do sistema
(CotacaoService), com origem fixa SP (Santana de Parnaiba) — a verdade de
negocio "subcontrato CarVia sai de SP". NAO inventa calculo nem ICMS:
CotacaoService passa `cidade=None` => sem ICMS (regra CarVia).

Seguranca:
- `--dry-run` e o DEFAULT (so imprime; nao escreve). Escreve so com `--confirmar`.
- NAO toca fretes com custo REAL ja registrado por outra via:
  fatura_transportadora_id / subcontrato_id / status_conferencia=APROVADO /
  valor_cte>0  (a menos que `--incluir-com-custo-real`).
- Idempotente: so atualiza fretes que continuam com valor_cotado=0/NULL.
- So grava onde a tabela RESOLVEU (rota com tabela cadastrada). Sem tabela ->
  fica 0 (legitimo, ex.: freteiro pessoa fisica sem tabela) e e reportado.

Uso:
  python scripts/migrations/2026_06_19_backfill_carvia_valor_cotado.py            # dry-run, so PENDENTE
  python scripts/migrations/2026_06_19_backfill_carvia_valor_cotado.py --status todos
  python scripts/migrations/2026_06_19_backfill_carvia_valor_cotado.py --confirmar # aplica
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

UF_ORIGEM_HUB = 'SP'  # mercadoria CarVia centralizada em SP (Santana de Parnaiba)
USUARIO_BACKFILL = 'backfill_carvia_valor_cotado'


def _resolver_melhor_opcao(svc, frete):
    """Cota via CotacaoService (origem SP) e devolve a opcao da transportadora
    do frete com menor valor, ou None. Reusa a logica oficial — sem calculo manual."""
    opcoes = svc.cotar_todas_opcoes(
        peso=float(frete.peso_total or 0),
        valor_mercadoria=float(frete.valor_total_nfs or 0),
        uf_destino=frete.uf_destino,
        cidade_destino=frete.cidade_destino,
        uf_origem=UF_ORIGEM_HUB,
    )
    # cotar_todas_opcoes ja vem ordenado por valor (menor primeiro).
    for o in opcoes:
        if o.get('transportadora_id') == frete.transportadora_id:
            return o
    return None


def _tem_custo_real(frete):
    """True se o frete ja tem custo registrado por outra via (nao tocar)."""
    return bool(
        frete.fatura_transportadora_id
        or frete.subcontrato_id
        or (frete.status_conferencia == 'APROVADO')
        or (frete.valor_cte and float(frete.valor_cte) > 0)
    )


def _tem_item_ativo(frete):
    """True se o frete tem >=1 EmbarqueItem ATIVO (embarque + NF).

    Frete cujo(s) EmbarqueItem foi(ram) CANCELADO(s), ou sem item algum, NAO deve
    ser recotado — a carga foi removida do embarque. O `status` do CarviaFrete nem
    sempre acompanha o cancelamento do EmbarqueItem (ha fretes PENDENTE com item
    cancelado — fantasmas), por isso o filtro olha o ITEM, nao so o status do frete.
    """
    from app.embarques.models import EmbarqueItem
    if not frete.embarque_id or not frete.numeros_nfs:
        return False
    nfs = [n.strip() for n in frete.numeros_nfs.split(',') if n.strip()]
    if not nfs:
        return False
    return EmbarqueItem.query.filter(
        EmbarqueItem.embarque_id == frete.embarque_id,
        EmbarqueItem.nota_fiscal.in_(nfs),
        EmbarqueItem.status == 'ativo',
    ).count() > 0


def main():
    parser = argparse.ArgumentParser(description='Backfill valor_cotado CarviaFrete')
    parser.add_argument('--confirmar', action='store_true',
                        help='Aplica as gravacoes (sem isto = dry-run, nao escreve)')
    parser.add_argument('--status', choices=['pendente', 'todos'], default='pendente',
                        help='pendente (default) = so status PENDENTE; todos = qualquer status')
    parser.add_argument('--incluir-com-custo-real', action='store_true',
                        help='Inclui fretes com fatura/subcontrato/CTe/conferido (NAO recomendado)')
    args = parser.parse_args()

    from app import create_app, db
    from app.carvia.models import CarviaFrete
    from app.carvia.services.pricing.cotacao_service import CotacaoService
    from app.tabelas.models import TabelaFrete
    from app.utils.tabela_frete_manager import TabelaFreteManager

    app = create_app()
    with app.app_context():
        svc = CotacaoService()

        q = CarviaFrete.query.filter(
            db.or_(CarviaFrete.valor_cotado == 0, CarviaFrete.valor_cotado.is_(None)),
            CarviaFrete.status != 'CANCELADO',  # nunca recotar frete cancelado
        )
        if args.status == 'pendente':
            q = q.filter(CarviaFrete.status == 'PENDENTE')
        fretes = q.order_by(CarviaFrete.id).all()

        modo = 'CONFIRMAR (escreve)' if args.confirmar else 'DRY-RUN (nao escreve)'
        print(f"=== Backfill valor_cotado CarVia | modo={modo} | status={args.status} ===")
        print(f"Fretes candidatos (valor_cotado=0): {len(fretes)}\n")

        resolvidos, sem_tabela, pulados_custo_real, sem_item_ativo, aplicados = [], [], [], [], 0

        for f in fretes:
            if _tem_custo_real(f) and not args.incluir_com_custo_real:
                pulados_custo_real.append(f)
                continue

            if not _tem_item_ativo(f):
                sem_item_ativo.append(f)
                print(f"[ITEM CANCELADO/AUSENTE] frete {f.id} | "
                      f"{f.cidade_destino}/{f.uf_destino} | status={f.status} -> nao recota")
                continue

            opcao = _resolver_melhor_opcao(svc, f)
            destino = f"{f.cidade_destino}/{f.uf_destino}"
            transp = f.transportadora.razao_social if f.transportadora else f.transportadora_id

            if not opcao:
                sem_tabela.append((f, destino, transp))
                print(f"[SEM TABELA] frete {f.id} | {transp} | {destino} | "
                      f"peso={f.peso_total} -> mantem 0")
                continue

            valor = round(float(opcao['valor_frete']), 2)
            resolvidos.append((f, opcao, valor))
            print(f"[OK] frete {f.id} | {transp} | {destino} | peso={f.peso_total} | "
                  f"tabela={opcao.get('tabela_nome')} | valor_cotado: 0 -> {valor}")

            if args.confirmar:
                f.valor_cotado = valor
                f.valor_considerado = valor
                tf = db.session.get(TabelaFrete, opcao.get('tabela_frete_id'))
                if tf:
                    TabelaFreteManager.copiar_de_tabela_frete(tf, f)  # snapshot tabela_*
                f.observacoes = ((f.observacoes or '') +
                                 f" [backfill valor_cotado {valor} em SP]").strip()
                aplicados += 1

        print("\n=== RESUMO ===")
        print(f"Resolvidos (tabela encontrada): {len(resolvidos)}")
        print(f"Sem tabela (mantem 0, legitimo): {len(sem_tabela)}")
        print(f"Pulados por item cancelado/ausente: {len(sem_item_ativo)}")
        print(f"Pulados por custo real ja existente: {len(pulados_custo_real)} "
              f"(use --incluir-com-custo-real para incluir)")
        if args.confirmar:
            db.session.commit()
            print(f"GRAVADOS: {aplicados} fretes atualizados (commit ok).")
        else:
            print("DRY-RUN: nada gravado. Rode com --confirmar para aplicar.")


if __name__ == '__main__':
    main()
