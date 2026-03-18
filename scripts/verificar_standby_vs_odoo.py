"""
Verificar SaldoStandby vs Odoo
==============================

Compara pedidos em SaldoStandby ativo no sistema local com saldos reais no Odoo.
Identifica pedidos que devem ser limpos (cancelados ou zerados no Odoo).

Gera relatório pronto para enviar ao agente para sincronização.

Uso:
    source .venv/bin/activate
    python scripts/verificar_standby_vs_odoo.py
    python scripts/verificar_standby_vs_odoo.py --limpar   # Executa limpeza automatica
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal, SaldoStandby
from app.odoo.utils.connection import get_odoo_connection
from sqlalchemy import distinct


def verificar_standby_vs_odoo(limpar: bool = False):
    """Cruza SaldoStandby ativos com dados reais do Odoo."""

    print("=" * 80)
    print("VERIFICAÇÃO: SaldoStandby vs Odoo")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 80)

    # 1. Buscar todos os standby ativos
    standby_ativos = SaldoStandby.query.filter(
        SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
    ).all()

    if not standby_ativos:
        print("\n✅ Nenhum SaldoStandby ativo encontrado. Nada a fazer.")
        return

    print(f"\n📋 {len(standby_ativos)} itens em SaldoStandby ativo")

    # 2. Agrupar por pedido
    pedidos_standby = {}
    for s in standby_ativos:
        if s.num_pedido not in pedidos_standby:
            pedidos_standby[s.num_pedido] = []
        pedidos_standby[s.num_pedido].append(s)

    print(f"📦 {len(pedidos_standby)} pedidos distintos")

    # 3. Buscar dados no Odoo (sale.order + sale.order.line)
    conn = get_odoo_connection()
    nomes_pedidos = list(pedidos_standby.keys())

    print(f"\n🔍 Consultando {len(nomes_pedidos)} pedidos no Odoo...")

    # Buscar pedidos (sale.order)
    pedidos_odoo = conn.search_read(
        'sale.order',
        [('name', 'in', nomes_pedidos)],
        ['name', 'state'],
        limit=len(nomes_pedidos) + 10
    )

    pedidos_odoo_map = {p['name']: p for p in pedidos_odoo}
    print(f"   ✅ {len(pedidos_odoo)} pedidos encontrados no Odoo")

    # Buscar linhas (sale.order.line) para pedidos encontrados
    pedidos_encontrados = [p['name'] for p in pedidos_odoo]
    linhas_odoo = conn.search_read(
        'sale.order.line',
        [('order_id.name', 'in', pedidos_encontrados)],
        ['order_id', 'product_id', 'product_uom_qty', 'qty_saldo', 'qty_cancelado'],
        limit=5000
    )

    # Mapear linhas por pedido + cod_produto (product_id)
    linhas_por_pedido = {}
    for l in linhas_odoo:
        pedido_name = l['order_id'][1] if isinstance(l['order_id'], list) else l['order_id']
        # Extrair do nome do pedido (ex: "VCD2565443 - Pedido de Venda")
        # O order_id retorna [id, display_name]
        pedido_id = l['order_id'][0] if isinstance(l['order_id'], list) else l['order_id']

        if pedido_id not in linhas_por_pedido:
            linhas_por_pedido[pedido_id] = []
        linhas_por_pedido[pedido_id].append(l)

    # Criar mapa por nome do pedido
    linhas_por_nome = {}
    for p in pedidos_odoo:
        pid = p['id']
        linhas_por_nome[p['name']] = linhas_por_pedido.get(pid, [])

    # 4. Buscar CarteiraPrincipal para comparar
    carteira_items = CarteiraPrincipal.query.filter(
        CarteiraPrincipal.num_pedido.in_(nomes_pedidos)
    ).all()

    carteira_map = {}
    for c in carteira_items:
        key = (c.num_pedido, c.cod_produto)
        carteira_map[key] = c

    # 5. Classificar cada standby
    para_limpar = []          # Saldo zerou no Odoo
    pedido_cancelado = []     # Pedido cancelado no Odoo
    pedido_nao_existe = []    # Pedido nao existe mais no Odoo
    carteira_zerada = []      # CarteiraPrincipal ja esta com saldo 0
    carteira_orfao = []       # CarteiraPrincipal nao existe
    ok = []                   # Saldo ainda pendente no Odoo

    for num_pedido, itens_standby in pedidos_standby.items():
        pedido_odoo = pedidos_odoo_map.get(num_pedido)

        if not pedido_odoo:
            # Pedido nao existe no Odoo
            for s in itens_standby:
                pedido_nao_existe.append(s)
            continue

        if pedido_odoo.get('state') == 'cancel':
            # Pedido cancelado no Odoo
            for s in itens_standby:
                pedido_cancelado.append(s)
            continue

        # Pedido existe e nao esta cancelado — verificar linhas
        linhas = linhas_por_nome.get(num_pedido, [])
        linhas_map = {}
        for l in linhas:
            prod_id = l['product_id'][0] if isinstance(l['product_id'], list) else l['product_id']
            linhas_map[prod_id] = l

        for s in itens_standby:
            # Verificar CarteiraPrincipal
            cp = carteira_map.get((s.num_pedido, s.cod_produto))

            if not cp:
                carteira_orfao.append((s, None))
                continue

            if cp.qtd_saldo_produto_pedido <= 0:
                carteira_zerada.append((s, cp))
                continue

            # Verificar se alguma linha Odoo tem saldo para este produto
            # Nota: cod_produto no sistema != product_id no Odoo
            # Precisamos verificar via CarteiraPrincipal.qtd_saldo_produto_pedido
            # que reflete o Odoo na ultima sync
            #
            # Verificar direto no Odoo: buscar linhas com qty_saldo > 0
            tem_saldo_odoo = False
            for l in linhas:
                if l.get('qty_saldo', 0) > 0:
                    tem_saldo_odoo = True
                    break

            if not tem_saldo_odoo:
                # Todas as linhas do pedido zeradas no Odoo
                para_limpar.append((s, cp))
            else:
                ok.append((s, cp))

    # 6. Relatorio
    print("\n" + "=" * 80)
    print("RESULTADO DA VERIFICAÇÃO")
    print("=" * 80)

    total_problemas = len(para_limpar) + len(pedido_cancelado) + len(pedido_nao_existe) + len(carteira_zerada) + len(carteira_orfao)

    if pedido_nao_existe:
        print(f"\n🚫 PEDIDO NÃO EXISTE NO ODOO ({len(pedido_nao_existe)} itens):")
        for s in pedido_nao_existe:
            dias = s.dias_em_standby or 0
            print(f"   {s.num_pedido} | {s.cod_produto} | {s.nome_cliente} | "
                  f"qtd={s.qtd_saldo} | {dias} dias em standby | status={s.status_standby}")

    if pedido_cancelado:
        print(f"\n❌ PEDIDO CANCELADO NO ODOO ({len(pedido_cancelado)} itens):")
        for s in pedido_cancelado:
            dias = s.dias_em_standby or 0
            print(f"   {s.num_pedido} | {s.cod_produto} | {s.nome_cliente} | "
                  f"qtd={s.qtd_saldo} | {dias} dias em standby | status={s.status_standby}")

    if para_limpar:
        print(f"\n⚠️ SALDO ZERADO NO ODOO ({len(para_limpar)} itens):")
        for s, cp in para_limpar:
            dias = s.dias_em_standby or 0
            cp_saldo = cp.qtd_saldo_produto_pedido if cp else '?'
            print(f"   {s.num_pedido} | {s.cod_produto} | {s.nome_cliente} | "
                  f"standby_qtd={s.qtd_saldo} | carteira_saldo={cp_saldo} | "
                  f"{dias} dias | status={s.status_standby}")

    if carteira_zerada:
        print(f"\n🔄 CARTEIRA JÁ ZERADA ({len(carteira_zerada)} itens) — standby deveria ter sido limpo:")
        for s, cp in carteira_zerada:
            dias = s.dias_em_standby or 0
            print(f"   {s.num_pedido} | {s.cod_produto} | {s.nome_cliente} | "
                  f"standby_qtd={s.qtd_saldo} | carteira_saldo={cp.qtd_saldo_produto_pedido} | "
                  f"{dias} dias | status={s.status_standby}")

    if carteira_orfao:
        print(f"\n👻 ÓRFÃO — sem CarteiraPrincipal ({len(carteira_orfao)} itens):")
        for s, _ in carteira_orfao:
            dias = s.dias_em_standby or 0
            print(f"   {s.num_pedido} | {s.cod_produto} | {s.nome_cliente} | "
                  f"standby_qtd={s.qtd_saldo} | {dias} dias | status={s.status_standby}")

    if ok:
        print(f"\n✅ OK — saldo ainda pendente ({len(ok)} itens)")
        for s, cp in ok:
            print(f"   {s.num_pedido} | {s.cod_produto} | {s.nome_cliente} | "
                  f"standby_qtd={s.qtd_saldo} | carteira_saldo={cp.qtd_saldo_produto_pedido}")

    print(f"\n{'=' * 80}")
    print(f"RESUMO: {total_problemas} itens com problema | {len(ok)} OK")
    print(f"{'=' * 80}")

    # 7. Limpeza automática se --limpar
    if limpar and total_problemas > 0:
        print(f"\n🧹 EXECUTANDO LIMPEZA DE {total_problemas} ITENS...")

        ids_para_resolver = []

        # Resolver todos os problemáticos
        for s in pedido_nao_existe:
            ids_para_resolver.append((s.id, 'CANCELADO', 'Pedido não existe mais no Odoo'))
        for s in pedido_cancelado:
            ids_para_resolver.append((s.id, 'CANCELADO', 'Pedido cancelado no Odoo'))
        for s, _ in para_limpar:
            ids_para_resolver.append((s.id, 'CANCELADO', 'Saldo zerado no Odoo'))
        for s, _ in carteira_zerada:
            ids_para_resolver.append((s.id, 'CANCELADO', 'CarteiraPrincipal já com saldo 0'))
        for s, _ in carteira_orfao:
            ids_para_resolver.append((s.id, 'CANCELADO', 'Sem CarteiraPrincipal correspondente'))

        from app.utils.timezone import agora_utc_naive
        agora = agora_utc_naive()

        for standby_id, resolucao, obs in ids_para_resolver:
            standby = db.session.get(SaldoStandby, standby_id)
            if standby:
                standby.status_standby = 'RESOLVIDO'
                standby.resolucao_final = resolucao
                standby.data_resolucao = agora
                standby.resolvido_por = 'script_verificacao'
                standby.observacoes_resolucao = obs

        db.session.commit()
        print(f"   ✅ {len(ids_para_resolver)} itens resolvidos como CANCELADO")

    elif total_problemas > 0 and not limpar:
        print(f"\n💡 Para limpar automaticamente, execute:")
        print(f"   python scripts/verificar_standby_vs_odoo.py --limpar")

    # 8. Texto para o agente
    if total_problemas > 0:
        print(f"\n{'=' * 80}")
        print("📋 TEXTO PARA O AGENTE (copiar e colar):")
        print("=" * 80)

        linhas_msg = []
        linhas_msg.append("Preciso que voce sincronize os seguintes pedidos que estao em SaldoStandby mas nao tem mais saldo no Odoo:\n")

        if pedido_nao_existe:
            linhas_msg.append(f"**Pedidos que NAO existem no Odoo** ({len(pedido_nao_existe)}):")
            pedidos_unicos = list(set(s.num_pedido for s in pedido_nao_existe))
            for p in pedidos_unicos:
                itens = [s for s in pedido_nao_existe if s.num_pedido == p]
                prods = ", ".join(s.cod_produto for s in itens)
                linhas_msg.append(f"- {p}: produtos {prods}")
            linhas_msg.append("")

        if pedido_cancelado:
            linhas_msg.append(f"**Pedidos CANCELADOS no Odoo** ({len(pedido_cancelado)}):")
            pedidos_unicos = list(set(s.num_pedido for s in pedido_cancelado))
            for p in pedidos_unicos:
                itens = [s for s in pedido_cancelado if s.num_pedido == p]
                prods = ", ".join(s.cod_produto for s in itens)
                linhas_msg.append(f"- {p}: produtos {prods}")
            linhas_msg.append("")

        if para_limpar:
            linhas_msg.append(f"**Pedidos com SALDO ZERADO no Odoo** ({len(para_limpar)}):")
            pedidos_unicos = list(set(s.num_pedido for s, _ in para_limpar))
            for p in pedidos_unicos:
                itens = [(s, cp) for s, cp in para_limpar if s.num_pedido == p]
                prods = ", ".join(f"{s.cod_produto} (standby={s.qtd_saldo}, carteira={cp.qtd_saldo_produto_pedido})" for s, cp in itens)
                linhas_msg.append(f"- {p}: {prods}")
            linhas_msg.append("")

        if carteira_zerada or carteira_orfao:
            total_orfao = len(carteira_zerada) + len(carteira_orfao)
            linhas_msg.append(f"**Standby órfão/desatualizado** ({total_orfao}):")
            todos_orfaos = [(s, 'saldo=0') for s, _ in carteira_zerada] + [(s, 'sem carteira') for s, _ in carteira_orfao]
            pedidos_unicos = list(set(s.num_pedido for s, _ in todos_orfaos))
            for p in pedidos_unicos:
                itens = [(s, motivo) for s, motivo in todos_orfaos if s.num_pedido == p]
                prods = ", ".join(f"{s.cod_produto} ({motivo})" for s, motivo in itens)
                linhas_msg.append(f"- {p}: {prods}")
            linhas_msg.append("")

        linhas_msg.append(f"Total: {total_problemas} itens para resolver. Rode a sincronizacao incremental da carteira para atualizar esses pedidos e limpar os standby.")

        print("\n".join(linhas_msg))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Verificar SaldoStandby vs Odoo')
    parser.add_argument('--limpar', action='store_true',
                        help='Executar limpeza automatica dos standby invalidos')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        verificar_standby_vs_odoo(limpar=args.limpar)
