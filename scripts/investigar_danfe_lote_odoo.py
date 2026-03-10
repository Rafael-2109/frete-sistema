"""
Investigação — DANFE e Lotes no Odoo (CIEL IT)
================================================

OBJETIVO:
    Investigar como o Odoo (módulo CIEL IT) gera o DANFE (PDF) e se é possível
    ocultar informações de lote/rastreabilidade do PDF mantendo no XML.

    8 queries read-only para determinar qual abordagem usar:
    - Abordagem A: Override QWeb via ir.ui.view herdado
    - Abordagem B: Toggle de configuração CIEL IT
    - Abordagem C: Pós-processamento PDF (fallback)

AUTOR: Sistema de Fretes
DATA: 09/03/2026
"""

import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

# Keywords de lote/rastreabilidade para buscar em templates QWeb
LOTE_KEYWORDS = ['rastro', 'lote', 'lot', 'nlote', 'qlote', 'dfab', 'dval', 'rastreabilidade', 'tracking']


def buscar_report_actions(odoo):
    """Query 1: Buscar report actions para DANFE/NF-e"""
    print("\n" + "=" * 80)
    print("1. REPORT ACTIONS (ir.actions.report)")
    print("=" * 80)

    domains_report = [
        ("report_name ilike 'danfe'", [['report_name', 'ilike', 'danfe']]),
        ("report_name ilike 'nfe'", [['report_name', 'ilike', 'nfe']]),
        ("model=account.move AND report_type=qweb-pdf", [
            ['model', '=', 'account.move'],
            ['report_type', '=', 'qweb-pdf'],
        ]),
        ("model=l10n_br_ciel_it_account.dfe", [['model', '=', 'l10n_br_ciel_it_account.dfe']]),
        ("report_name ilike 'l10n_br'", [['report_name', 'ilike', 'l10n_br']]),
    ]

    reports_encontrados = []

    for desc, domain in domains_report:
        try:
            reports = odoo.search_read(
                'ir.actions.report',
                domain,
                fields=['id', 'name', 'model', 'report_name', 'report_type',
                        'binding_model_id', 'print_report_name'],
                limit=20,
            )
            if reports:
                print(f"\n   [{desc}] -> {len(reports)} resultado(s):")
                for r in reports:
                    print(f"      ID={r['id']} | name={r['name']}")
                    print(f"        model={r['model']} | report_name={r['report_name']}")
                    print(f"        report_type={r['report_type']}")
                    print(f"        print_report_name={r.get('print_report_name')}")
                    reports_encontrados.append(r)
            else:
                print(f"\n   [{desc}] -> Nenhum resultado")
        except Exception as e:
            print(f"\n   [{desc}] -> ERRO: {e}")

    return reports_encontrados


def buscar_templates_qweb(odoo):
    """Query 2: Buscar templates QWeb do DANFE"""
    print("\n" + "=" * 80)
    print("2. TEMPLATES QWEB (ir.ui.view)")
    print("=" * 80)

    domains_view = [
        ("name ilike 'danfe'", [['name', 'ilike', 'danfe']]),
        ("name ilike 'nfe' AND type=qweb", [
            ['name', 'ilike', 'nfe'],
            ['type', '=', 'qweb'],
        ]),
        ("key ilike 'l10n_br_ciel_it'", [['key', 'ilike', 'l10n_br_ciel_it']]),
        ("key ilike 'danfe'", [['key', 'ilike', 'danfe']]),
        ("name ilike 'l10n_br' AND type=qweb", [
            ['name', 'ilike', 'l10n_br'],
            ['type', '=', 'qweb'],
        ]),
    ]

    views_encontrados = []
    views_com_lote = []

    for desc, domain in domains_view:
        try:
            views = odoo.search_read(
                'ir.ui.view',
                domain,
                fields=['id', 'name', 'key', 'type', 'inherit_id', 'arch_db',
                        'model', 'priority', 'active'],
                limit=30,
            )
            if views:
                print(f"\n   [{desc}] -> {len(views)} resultado(s):")
                for v in views:
                    inherit_info = ""
                    if v.get('inherit_id'):
                        if isinstance(v['inherit_id'], (list, tuple)):
                            inherit_info = f" (herda de ID={v['inherit_id'][0]})"
                        else:
                            inherit_info = f" (herda de ID={v['inherit_id']})"

                    print(f"      ID={v['id']} | name={v['name']}{inherit_info}")
                    print(f"        key={v.get('key')} | type={v['type']} | model={v.get('model')}")
                    print(f"        active={v.get('active')} | priority={v.get('priority')}")

                    # Analisar arch_db para keywords de lote
                    arch = v.get('arch_db') or ''
                    if isinstance(arch, str) and arch:
                        arch_lower = arch.lower()
                        keywords_encontradas = [kw for kw in LOTE_KEYWORDS if kw in arch_lower]
                        if keywords_encontradas:
                            print(f"        >>> CONTÉM KEYWORDS DE LOTE: {keywords_encontradas}")
                            views_com_lote.append({
                                'id': v['id'],
                                'name': v['name'],
                                'key': v.get('key'),
                                'keywords': keywords_encontradas,
                                'arch_db': arch,
                            })

                        # Mostrar tamanho do template
                        print(f"        arch_db: {len(arch)} chars")

                    views_encontrados.append(v)
            else:
                print(f"\n   [{desc}] -> Nenhum resultado")
        except Exception as e:
            print(f"\n   [{desc}] -> ERRO: {e}")

    # Detalhar views com keywords de lote
    if views_com_lote:
        print("\n   " + "-" * 60)
        print("   VIEWS COM KEYWORDS DE LOTE (candidatas a override):")
        print("   " + "-" * 60)
        for v in views_com_lote:
            print(f"\n   View ID={v['id']} | name={v['name']}")
            print(f"   Keywords: {v['keywords']}")
            # Extrair trecho relevante do arch_db
            arch = v['arch_db']
            for kw in v['keywords']:
                for match in re.finditer(kw, arch, re.IGNORECASE):
                    start = max(0, match.start() - 100)
                    end = min(len(arch), match.end() + 100)
                    trecho = arch[start:end].replace('\n', ' ').strip()
                    print(f"   Trecho [{kw}]: ...{trecho}...")

    return views_encontrados, views_com_lote


def buscar_config_parameters(odoo):
    """Query 3: Buscar configurações CIEL IT"""
    print("\n" + "=" * 80)
    print("3. CONFIGURAÇÕES (ir.config_parameter)")
    print("=" * 80)

    domains_config = [
        ("key ilike 'danfe'", [['key', 'ilike', 'danfe']]),
        ("key ilike 'l10n_br_ciel_it'", [['key', 'ilike', 'l10n_br_ciel_it']]),
        ("key ilike 'rastro'", [['key', 'ilike', 'rastro']]),
        ("key ilike 'lote'", [['key', 'ilike', 'lote']]),
        ("key ilike 'lot'", [['key', 'ilike', 'lot']]),
        ("key ilike 'tracking'", [['key', 'ilike', 'tracking']]),
        ("key ilike 'nfe'", [['key', 'ilike', 'nfe']]),
    ]

    configs_encontrados = []

    for desc, domain in domains_config:
        try:
            configs = odoo.search_read(
                'ir.config_parameter',
                domain,
                fields=['id', 'key', 'value'],
                limit=20,
            )
            if configs:
                print(f"\n   [{desc}] -> {len(configs)} resultado(s):")
                for c in configs:
                    valor = c.get('value', '')
                    if len(str(valor)) > 200:
                        valor = str(valor)[:200] + '...'
                    print(f"      ID={c['id']} | key={c['key']} | value={valor}")
                    configs_encontrados.append(c)
            else:
                print(f"\n   [{desc}] -> Nenhum resultado")
        except Exception as e:
            print(f"\n   [{desc}] -> ERRO: {e}")

    return configs_encontrados


def buscar_campos_dfe_line(odoo):
    """Query 4: Campos do DFe line relacionados a lote"""
    print("\n" + "=" * 80)
    print("4. CAMPOS DFe LINE (l10n_br_ciel_it_account.dfe.line)")
    print("=" * 80)

    try:
        campos = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe.line',
            'fields_get',
            [],
            {'attributes': ['string', 'type', 'help']},
        )

        # Filtrar por keywords de lote
        campos_lote = {}
        for nome, info in campos.items():
            nome_lower = nome.lower()
            string_lower = (info.get('string') or '').lower()
            help_lower = (info.get('help') or '').lower()

            for kw in LOTE_KEYWORDS:
                if kw in nome_lower or kw in string_lower or kw in help_lower:
                    campos_lote[nome] = info
                    break

        if campos_lote:
            print(f"\n   Campos com keywords de lote: {len(campos_lote)}")
            for nome, info in sorted(campos_lote.items()):
                print(f"      {nome} ({info['type']}) - {info.get('string')}")
                if info.get('help'):
                    print(f"        help: {info['help'][:200]}")
        else:
            print("\n   Nenhum campo com keywords de lote encontrado em dfe.line")

        # Também listar campos com 'rastro' ou 'med' (medicamento) no nome
        campos_rastro = {k: v for k, v in campos.items()
                         if 'rastro' in k.lower() or 'med_' in k.lower() or 'det_prod_rastro' in k.lower()}
        if campos_rastro:
            print(f"\n   Campos rastro/med adicionais: {len(campos_rastro)}")
            for nome, info in sorted(campos_rastro.items()):
                print(f"      {nome} ({info['type']}) - {info.get('string')}")

        print(f"\n   Total de campos em dfe.line: {len(campos)}")
        return campos_lote, campos

    except Exception as e:
        print(f"\n   ERRO: {e}")
        return {}, {}


def buscar_campos_account_move(odoo):
    """Query 5: Campos da invoice com DANFE/PDF"""
    print("\n" + "=" * 80)
    print("5. CAMPOS ACCOUNT.MOVE (danfe/pdf)")
    print("=" * 80)

    try:
        campos = odoo.execute_kw(
            'account.move',
            'fields_get',
            [],
            {'attributes': ['string', 'type', 'help']},
        )

        keywords_pdf = ['danfe', 'pdf', 'rastro', 'report', 'l10n_br_pdf', 'dfe', 'lote']
        campos_relevantes = {}
        for nome, info in campos.items():
            nome_lower = nome.lower()
            string_lower = (info.get('string') or '').lower()
            for kw in keywords_pdf:
                if kw in nome_lower or kw in string_lower:
                    campos_relevantes[nome] = info
                    break

        if campos_relevantes:
            print(f"\n   Campos relevantes: {len(campos_relevantes)}")
            for nome, info in sorted(campos_relevantes.items()):
                print(f"      {nome} ({info['type']}) - {info.get('string')}")
        else:
            print("\n   Nenhum campo com keywords pdf/danfe encontrado em account.move")

        return campos_relevantes

    except Exception as e:
        print(f"\n   ERRO: {e}")
        return {}


def buscar_nfe_venda_com_lotes(odoo):
    """Query 6: NF-e de venda recente com lotes"""
    print("\n" + "=" * 80)
    print("6. NF-e DE VENDA RECENTE COM LOTES")
    print("=" * 80)

    try:
        # Buscar invoices de venda recentes (posted)
        invoices = odoo.search_read(
            'account.move',
            [
                ['move_type', '=', 'out_invoice'],
                ['state', '=', 'posted'],
            ],
            fields=['id', 'name', 'partner_id', 'invoice_date', 'amount_total'],
            limit=5,
            order='id desc',
        )

        if not invoices:
            print("\n   Nenhuma invoice de venda encontrada")
            return None

        print(f"\n   Encontradas {len(invoices)} invoices de venda recentes:")
        for inv in invoices:
            print(f"      ID={inv['id']} | {inv['name']} | {inv.get('invoice_date')}")
            print(f"        Partner: {inv.get('partner_id')}")
            print(f"        Total: {inv.get('amount_total')}")

        # Verificar DFe associado à primeira invoice
        invoice_id = invoices[0]['id']
        print(f"\n   Verificando DFe da invoice ID={invoice_id}...")

        # Buscar DFe vinculado à invoice (via account.move)
        # O DFe pode estar em campos l10n_br_* ou em attachments
        # Buscar campos l10n_br_pdf e l10n_br_xml na invoice
        campos_move = odoo.execute_kw(
            'account.move',
            'fields_get',
            [],
            {'attributes': ['string', 'type']},
        )
        campos_pdf_xml = [k for k in campos_move
                          if 'pdf' in k.lower() or 'xml' in k.lower() or 'dfe' in k.lower()]

        if campos_pdf_xml:
            print(f"\n   Campos PDF/XML/DFe em account.move: {campos_pdf_xml}")
            inv_dados = odoo.read('account.move', [invoice_id], fields=campos_pdf_xml)
            if inv_dados:
                for campo, valor in sorted(inv_dados[0].items()):
                    if campo == 'id':
                        continue
                    if isinstance(valor, str) and len(valor) > 100:
                        print(f"      {campo}: [dados binários - {len(valor)} chars]")
                    elif valor:
                        print(f"      {campo}: {valor}")

        # Buscar DFe de saída
        dfes = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            [['l10n_br_tipo_pedido', '=', 'venda']],
            fields=['id', 'name', 'l10n_br_status', 'nfe_infnfe_ide_nnf',
                    'protnfe_infnfe_chnfe', 'l10n_br_pdf_dfe', 'l10n_br_xml_dfe'],
            limit=3,
            order='id desc',
        )

        if dfes:
            print(f"\n   DFes de venda encontrados: {len(dfes)}")
            for dfe in dfes:
                pdf_info = "SIM" if dfe.get('l10n_br_pdf_dfe') else "NAO"
                xml_info = "SIM" if dfe.get('l10n_br_xml_dfe') else "NAO"
                print(f"      DFe ID={dfe['id']} | NF={dfe.get('nfe_infnfe_ide_nnf')}")
                print(f"        Status: {dfe.get('l10n_br_status')} | Chave: {dfe.get('protnfe_infnfe_chnfe')}")
                print(f"        PDF: {pdf_info} | XML: {xml_info}")
        else:
            print("\n   Nenhum DFe de venda encontrado")
            # Tentar sem filtro de tipo
            dfes = odoo.search_read(
                'l10n_br_ciel_it_account.dfe',
                [],
                fields=['id', 'name', 'l10n_br_status', 'l10n_br_tipo_pedido',
                        'nfe_infnfe_ide_nnf'],
                limit=5,
                order='id desc',
            )
            if dfes:
                print(f"\n   Últimos DFes (qualquer tipo): {len(dfes)}")
                for dfe in dfes:
                    print(f"      ID={dfe['id']} | tipo={dfe.get('l10n_br_tipo_pedido')} | NF={dfe.get('nfe_infnfe_ide_nnf')}")

        return invoices[0] if invoices else None

    except Exception as e:
        print(f"\n   ERRO: {e}")
        return None


def buscar_views_herdados(odoo):
    """Query 7: Verificar overrides existentes"""
    print("\n" + "=" * 80)
    print("7. VIEWS HERDADOS EXISTENTES (overrides)")
    print("=" * 80)

    try:
        views = odoo.search_read(
            'ir.ui.view',
            [
                ['inherit_id', '!=', False],
                '|', '|',
                ['name', 'ilike', 'danfe'],
                ['name', 'ilike', 'nacom'],
                ['name', 'ilike', 'lote'],
            ],
            fields=['id', 'name', 'key', 'inherit_id', 'active', 'priority', 'arch_db'],
            limit=20,
        )

        if views:
            print(f"\n   Views herdados encontrados: {len(views)}")
            for v in views:
                inherit = v.get('inherit_id')
                if isinstance(inherit, (list, tuple)):
                    inherit = f"ID={inherit[0]} ({inherit[1]})"
                print(f"      ID={v['id']} | name={v['name']}")
                print(f"        inherit_id={inherit}")
                print(f"        active={v.get('active')} | priority={v.get('priority')}")
                arch = v.get('arch_db') or ''
                if arch:
                    print(f"        arch_db: {len(arch)} chars")
                    # Mostrar primeiras linhas
                    primeiras_linhas = arch[:300].replace('\n', ' ').strip()
                    print(f"        preview: {primeiras_linhas}...")
        else:
            print("\n   Nenhum view herdado encontrado (danfe/nacom/lote)")

        return views

    except Exception as e:
        print(f"\n   ERRO: {e}")
        return []


def buscar_modulos_ciel_it(odoo):
    """Query 8: Confirmar versão CIEL IT"""
    print("\n" + "=" * 80)
    print("8. MÓDULOS CIEL IT INSTALADOS")
    print("=" * 80)

    try:
        modulos = odoo.search_read(
            'ir.module.module',
            [
                ['name', 'ilike', 'l10n_br_ciel_it'],
                ['state', '=', 'installed'],
            ],
            fields=['id', 'name', 'shortdesc', 'installed_version', 'author',
                    'summary', 'website'],
            limit=20,
        )

        if modulos:
            print(f"\n   Módulos CIEL IT instalados: {len(modulos)}")
            for m in modulos:
                print(f"      ID={m['id']} | name={m['name']}")
                print(f"        version={m.get('installed_version')}")
                print(f"        desc={m.get('shortdesc')}")
                print(f"        author={m.get('author')}")
                if m.get('summary'):
                    print(f"        summary={m['summary'][:200]}")
        else:
            print("\n   Nenhum módulo CIEL IT instalado!")
            # Buscar qualquer módulo l10n_br
            modulos_br = odoo.search_read(
                'ir.module.module',
                [
                    ['name', 'ilike', 'l10n_br'],
                    ['state', '=', 'installed'],
                ],
                fields=['id', 'name', 'installed_version'],
                limit=20,
            )
            if modulos_br:
                print(f"\n   Módulos l10n_br instalados: {len(modulos_br)}")
                for m in modulos_br:
                    print(f"      {m['name']} (v{m.get('installed_version')})")

        return modulos

    except Exception as e:
        print(f"\n   ERRO: {e}")
        return []


def gerar_relatorio(reports, views, views_com_lote, configs, campos_lote_dfe,
                    views_herdados, modulos):
    """Gera relatório final com recomendação de abordagem"""
    print("\n" + "=" * 80)
    print("RELATÓRIO FINAL — RECOMENDAÇÃO DE ABORDAGEM")
    print("=" * 80)

    tem_qweb_danfe = any(
        r.get('report_type') == 'qweb-pdf'
        and ('danfe' in (r.get('report_name') or '').lower()
             or 'danfe' in (r.get('name') or '').lower())
        for r in reports
    )

    tem_template_com_lote = len(views_com_lote) > 0

    tem_config_toggle = any(
        'rastro' in (c.get('key') or '').lower()
        or 'lote' in (c.get('key') or '').lower()
        or 'danfe' in (c.get('key') or '').lower()
        for c in configs
    )

    print(f"""
   EVIDÊNCIAS:
   - Reports QWeb para DANFE encontrados: {'SIM' if tem_qweb_danfe else 'NAO'}
   - Templates com keywords de lote: {'SIM (' + str(len(views_com_lote)) + ')' if tem_template_com_lote else 'NAO'}
   - Toggle de configuração CIEL IT: {'SIM' if tem_config_toggle else 'NAO'}
   - Campos de lote em DFe line: {'SIM (' + str(len(campos_lote_dfe)) + ')' if campos_lote_dfe else 'NAO'}
   - Views herdados existentes: {'SIM (' + str(len(views_herdados)) + ')' if views_herdados else 'NAO'}
   - Módulos CIEL IT: {len(modulos)} instalados
   - Reports encontrados total: {len(reports)}
   - Views QWeb encontrados total: {len(views)}
   """)

    # Determinar abordagem
    if tem_config_toggle:
        print("   >>> ABORDAGEM B RECOMENDADA: Toggle de configuração CIEL IT")
        print("       A mais simples — apenas alterar parâmetro de configuração.")
        abordagem = 'B'
    elif tem_qweb_danfe and tem_template_com_lote:
        print("   >>> ABORDAGEM A RECOMENDADA: Override QWeb via ir.ui.view herdado")
        print("       Template QWeb encontrado com conteúdo de lote — criar view herdado com XPath.")
        for v in views_com_lote:
            print(f"       Target: View ID={v['id']} ({v['name']}) — keywords: {v['keywords']}")
        abordagem = 'A'
    elif tem_qweb_danfe:
        print("   >>> ABORDAGEM A POSSÍVEL, MAS SEM KEYWORDS DE LOTE")
        print("       Reports QWeb existem, mas nenhum template tem keywords de lote.")
        print("       Pode ser que o lote venha de sub-template ou campo computado.")
        print("       Analisar arch_db dos templates manualmente.")
        abordagem = 'A_parcial'
    else:
        print("   >>> ABORDAGEM C (FALLBACK): Pós-processamento PDF")
        print("       CIEL IT provavelmente gera DANFE internamente (sem QWeb).")
        print("       Necessário baixar PDF, redactar seção de lotes, re-upload.")
        abordagem = 'C'

    print("\n" + "=" * 80)
    return abordagem


def main():
    print("=" * 80)
    print("INVESTIGAÇÃO — DANFE E LOTES NO ODOO (CIEL IT)")
    print("Todas as queries são READ-ONLY — nenhuma modificação será feita")
    print("=" * 80)

    app = create_app()

    with app.app_context():
        odoo = get_odoo_connection()

        # Query 1: Report actions
        reports = buscar_report_actions(odoo)

        # Query 2: Templates QWeb
        views, views_com_lote = buscar_templates_qweb(odoo)

        # Query 3: Configurações
        configs = buscar_config_parameters(odoo)

        # Query 4: Campos DFe line
        campos_lote_dfe, _ = buscar_campos_dfe_line(odoo)

        # Query 5: Campos account.move
        buscar_campos_account_move(odoo)

        # Query 6: NF-e de venda com lotes
        buscar_nfe_venda_com_lotes(odoo)

        # Query 7: Views herdados existentes
        views_herdados = buscar_views_herdados(odoo)

        # Query 8: Módulos CIEL IT
        modulos = buscar_modulos_ciel_it(odoo)

        # Relatório final
        abordagem = gerar_relatorio(
            reports, views, views_com_lote, configs,
            campos_lote_dfe, views_herdados, modulos,
        )

        print(f"\n   ABORDAGEM SELECIONADA: {abordagem}")
        print(f"\n   PRÓXIMO PASSO: Executar ocultar_lote_danfe_odoo.py --abordagem {abordagem}")
        print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
