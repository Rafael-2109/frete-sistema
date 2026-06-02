"""Transferência de saldo entre CÓDIGOS em FB/Estoque (Odoo) — one-off.

Replica a parte Odoo da lógica de TransferenciaSaldoCodigoService.transferir()
(passos 4-6: reduzir origem → criar lote destino → aumentar destino), porém em
FB/Estoque (company 1, loc 8) em vez de CD. NÃO grava espelho MovimentacaoEstoque
(decisão do usuário: "esquece o render, é no Odoo").

Usa os MESMOS átomos do service (não reinventa XML-RPC):
  - StockQuantAdjustmentService.ajustar_quant (guard CICLAMATO via delta_esperado)
  - StockLotService.criar_se_nao_existe (lote no produto destino c/ validade origem)

Caso: 72 kg de 101002015 (COGUMELO FATIADO TIPO OYSTER) → 101004100
(COGUMELO FATIADO CX - IND), lote 152/26, FB/Estoque.
Par validado em unificacao_codigos (Render): 101002015→101001001 (id 57) e
101004100→101001001 (id 56) — irmãos via destino comum.

--dry-run é DEFAULT. Só efetiva com --confirmar.
"""
import argparse
import sys

sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

from app import create_app
from app.odoo.constants.locations import COMPANY_LOCATIONS
from app.odoo.services.stock_lot_service import StockLotService
from app.odoo.services.stock_quant_adjustment_service import StockQuantAdjustmentService
from app.odoo.utils.connection import get_odoo_connection

FB_COMPANY_ID = 1
FB_ESTOQUE_LOC = COMPANY_LOCATIONS[1]  # 8


def main():
    ap = argparse.ArgumentParser(description='Transferir saldo entre códigos em FB/Estoque (Odoo)')
    ap.add_argument('--cod-origem', default='101002015')
    ap.add_argument('--cod-destino', default='101004100')
    ap.add_argument('--lote', default='152/26')
    ap.add_argument('--qty', type=float, default=72.0)
    ap.add_argument('--confirmar', action='store_true', help='Executa de verdade (sem isto = dry-run)')
    args = ap.parse_args()

    dry = not args.confirmar
    qty = round(float(args.qty), 6)
    modo = 'DRY-RUN' if dry else 'CONFIRMAR (ESCRITA REAL NO ODOO)'

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        adj_svc = StockQuantAdjustmentService(odoo=odoo, lot_svc=lot_svc)

        # resolver produtos (default_code -> product_id), exigindo tracking='lot'
        def resolver(cod):
            res = odoo.search_read('product.product', [['default_code', '=', str(cod).strip()]],
                                   ['id', 'default_code', 'name', 'active', 'tracking',
                                    'uom_id', 'use_expiration_date'], limit=0)
            ativos = [p for p in res if p.get('active')] or res
            if not ativos:
                raise SystemExit(f'ERRO: produto {cod} não encontrado no Odoo')
            if len(ativos) > 1:
                raise SystemExit(f'ERRO: produto {cod} ambíguo ({len(ativos)} ativos)')
            return ativos[0]

        po = resolver(args.cod_origem)
        pd = resolver(args.cod_destino)
        for p in (po, pd):
            if p['tracking'] != 'lot':
                raise SystemExit(f"ERRO: produto {p['default_code']} tracking={p['tracking']} (esperado lot)")
        pid_o, pid_d = po['id'], pd['id']

        print(f"\n{'='*70}\n  TRANSFERÊNCIA DE SALDO FB/Estoque — {modo}\n{'='*70}")
        print(f"  Origem : {args.cod_origem} (pid {pid_o}) {po['name']}")
        print(f"  Destino: {args.cod_destino} (pid {pid_d}) {pd['name']}")
        print(f"  Lote   : {args.lote} | Qtd: {qty} {po['uom_id'][1] if po.get('uom_id') else ''}")
        print(f"  Empresa: FB (company_id={FB_COMPANY_ID}) | location_id={FB_ESTOQUE_LOC}\n")

        # resolver lote origem + validade (replicar no destino se usar validade)
        lot_id_origem = lot_svc.buscar_por_nome(args.lote, pid_o, FB_COMPANY_ID)
        if not lot_id_origem:
            raise SystemExit(f'ERRO: lote {args.lote!r} não encontrado no produto {args.cod_origem} (FB)')
        lots = odoo.read('stock.lot', [lot_id_origem], ['expiration_date'])
        validade = (lots[0].get('expiration_date') or None) if lots else None
        print(f"  lote origem lot_id={lot_id_origem} | validade={validade}")

        # PASSO 4 — reduzir origem (delta_esperado herda guard CICLAMATO)
        r_red = adj_svc.ajustar_quant(
            product_id=pid_o, company_id=FB_COMPANY_ID, location_id=FB_ESTOQUE_LOC,
            lot_id=lot_id_origem, delta=-qty, delta_esperado=-qty,
            validar_nao_negativar=True, validar_nao_abaixo_reserva=True, dry_run=dry)
        print(f"\n  [REDUZIR ORIGEM] status={r_red['status']} "
              f"antes={r_red.get('qty_antes')} apos={r_red.get('qty_apos')} "
              f"reservada={r_red.get('reservada')} erro={r_red.get('erro')}")
        if r_red['status'] not in ('EXECUTADO', 'DRY_RUN_OK'):
            raise SystemExit(f"ABORTADO na redução: {r_red['status']} / {r_red.get('erro')}")

        # PASSO 5 — garantir lote no destino (só cria de verdade fora do dry-run)
        exp = validade if pd['use_expiration_date'] else None
        if dry:
            lot_id_destino = lot_svc.buscar_por_nome(args.lote, pid_d, FB_COMPANY_ID)
            print(f"\n  [LOTE DESTINO] (dry) lot_id existente={lot_id_destino} "
                  f"(seria criado com validade={exp} se ausente)")
        else:
            lot_id_destino, criado = lot_svc.criar_se_nao_existe(
                args.lote, pid_d, FB_COMPANY_ID, expiration_date=exp)
            print(f"\n  [LOTE DESTINO] lot_id={lot_id_destino} criado={criado}")

        # PASSO 6 — aumentar destino (compensa origem se falhar)
        r_aum = adj_svc.ajustar_quant(
            product_id=pid_d, company_id=FB_COMPANY_ID, location_id=FB_ESTOQUE_LOC,
            lot_id=lot_id_destino, delta=qty, delta_esperado=qty, criar_se_faltar=True,
            validar_nao_negativar=True, validar_nao_abaixo_reserva=True, dry_run=dry)
        print(f"\n  [AUMENTAR DESTINO] status={r_aum['status']} "
              f"antes={r_aum.get('qty_antes')} apos={r_aum.get('qty_apos')} erro={r_aum.get('erro')}")

        if not dry and r_aum['status'] not in ('EXECUTADO', 'DRY_RUN_OK'):
            # compensar a redução já efetivada na origem
            comp = adj_svc.ajustar_quant(
                product_id=pid_o, company_id=FB_COMPANY_ID, location_id=FB_ESTOQUE_LOC,
                lot_id=lot_id_origem, delta=qty,
                validar_nao_negativar=False, validar_nao_abaixo_reserva=False, dry_run=False)
            print(f"\n  [COMPENSAÇÃO] aumento falhou → devolveu {qty} à origem: {comp['status']}")
            raise SystemExit(f"FALHA no aumento (compensado): {r_aum.get('erro')}")

        print(f"\n{'='*70}\n  {'PLANO (nada escrito)' if dry else 'EXECUTADO NO ODOO'}\n{'='*70}\n")


if __name__ == '__main__':
    main()
