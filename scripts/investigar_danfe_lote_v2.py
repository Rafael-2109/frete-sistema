"""
Investigação Profunda — DANFE e Lotes no Odoo (CIEL IT) — Fase 2
================================================================

OBJETIVO:
    10 queries focadas nos ângulos não explorados na Fase 1.
    Todas READ-ONLY — nenhuma modificação será feita.

CONTEXTO (resultados da Fase 1):
    - CIEL IT NÃO usa QWeb para DANFE (gera internamente)
    - group_lot_on_invoice = True (86 users, revertido) — CIEL IT ignora essa config
    - imprimir_validade_danfe = 0 (FUNCIONA — removeu validade do DANFE)
    - l10n_br_informacao_adicional (text) existe em account.move.line → mapeia para <infAdProd>
    - l10n_br_informacao_adicional_produto_ids (m2m→mensagem.fiscal) = [] em todas as linhas
    - Server action 874 (action_gerar_xmldanfe_nfe) gera o DANFE
    - Padrão de ir.actions.server com Python code em scripts/criar_wizard_ibscbs_odoo.py

HIPÓTESES A TESTAR:
    H1: CIEL IT gera infAdProd DINAMICAMENTE a partir de <rastro> (ignora campo text)
    H2: Existe config CIEL IT não descoberta que controla lote no infAdProd
    H3: l10n_br_informacao_adicional é preenchido pelo CIEL IT durante transmissão
    H4: Server action 874 tem código Python que referencia lote/rastro
    H5: base.automation pós-transmissão poderia interceptar e limpar o campo

USO:
    python scripts/investigar_danfe_lote_v2.py
    python scripts/investigar_danfe_lote_v2.py --invoice-id 517038
    python scripts/investigar_danfe_lote_v2.py --query 1,2,5   # Apenas queries específicas

AUTOR: Sistema de Fretes
DATA: 10/03/2026
"""

import argparse
import base64
import re
import sys
import os
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

# NF-e namespace
NFE_NS = 'http://www.portalfiscal.inf.br/nfe'

# Invoice da NF 145.630 (referência principal)
DEFAULT_INVOICE_ID = 517038


def query_1_xml_conteudo(odoo, invoice_id):
    """Query 1: Conteúdo do XML da NF — extrair infAdProd e rastro"""
    print("\n" + "=" * 80)
    print("QUERY 1: CONTEÚDO DO XML DA NF-e (infAdProd + rastro)")
    print("=" * 80)

    try:
        inv = odoo.read(
            'account.move',
            [invoice_id],
            fields=['id', 'name', 'l10n_br_xml_aut_nfe'],
        )
        if not inv or not inv[0].get('l10n_br_xml_aut_nfe'):
            print(f"\n   Invoice {invoice_id} sem XML autorizado")
            return None

        xml_b64 = inv[0]['l10n_br_xml_aut_nfe']
        xml_bytes = base64.b64decode(xml_b64)
        xml_str = xml_bytes.decode('utf-8')
        print(f"\n   Invoice: {inv[0]['name']} (ID={invoice_id})")
        print(f"   XML: {len(xml_bytes)} bytes")

        # Parsear XML
        root = ET.fromstring(xml_str)
        prefix = f'{{{NFE_NS}}}'

        resultado = {
            'itens': [],
            'total_itens': 0,
            'itens_com_infadprod': 0,
            'itens_com_rastro': 0,
            'infadprod_conteudos': [],
        }

        for det in root.iter(f'{prefix}det'):
            resultado['total_itens'] += 1
            n_item = det.get('nItem', '?')
            prod = det.find(f'{prefix}prod')

            xprod_elem = prod.find(f'{prefix}xProd') if prod is not None else None
            xprod = xprod_elem.text if xprod_elem is not None else '?'

            # Extrair infAdProd
            infadprod_elem = det.find(f'{prefix}infAdProd')
            infadprod = infadprod_elem.text if infadprod_elem is not None else None

            if infadprod:
                resultado['itens_com_infadprod'] += 1
                resultado['infadprod_conteudos'].append({
                    'item': n_item,
                    'produto': xprod[:50],
                    'conteudo': infadprod,
                })

            # Extrair rastro(s)
            rastros = []
            if prod is not None:
                for rastro in prod.findall(f'{prefix}rastro'):
                    r = {}
                    for campo in ['nLote', 'qLote', 'dFab', 'dVal']:
                        elem = rastro.find(f'{prefix}{campo}')
                        if elem is not None:
                            r[campo] = elem.text
                    rastros.append(r)
                    resultado['itens_com_rastro'] += 1

            resultado['itens'].append({
                'nItem': n_item,
                'xProd': xprod[:50],
                'infAdProd': infadprod,
                'rastros': rastros,
            })

        # Exibir resultado
        print(f"\n   Total de itens: {resultado['total_itens']}")
        print(f"   Itens com infAdProd: {resultado['itens_com_infadprod']}")
        print(f"   Itens com <rastro>: {resultado['itens_com_rastro']}")

        print("\n   --- infAdProd encontrados ---")
        if resultado['infadprod_conteudos']:
            for info in resultado['infadprod_conteudos'][:15]:
                print(f"   Item {info['item']} | {info['produto']}")
                print(f"     infAdProd: \"{info['conteudo']}\"")
        else:
            print("   Nenhum infAdProd encontrado nos itens")

        print("\n   --- Rastros encontrados ---")
        for item in resultado['itens']:
            if item['rastros']:
                for r in item['rastros']:
                    print(f"   Item {item['nItem']} | {item['xProd']}")
                    print(f"     nLote={r.get('nLote')} qLote={r.get('qLote')} "
                          f"dFab={r.get('dFab')} dVal={r.get('dVal')}")

        # Analisar padrão do infAdProd
        if resultado['infadprod_conteudos']:
            print("\n   --- Análise do padrão infAdProd ---")
            primeiro = resultado['infadprod_conteudos'][0]['conteudo']
            tem_lote = bool(re.search(r'[Ll]ote\s*:', primeiro))
            tem_validade = bool(re.search(r'[Vv]alidade\s*:', primeiro))
            tem_fabricacao = bool(re.search(r'[Ff]abrica[çc][ãa]o\s*:', primeiro))
            print(f"   Contém 'Lote:': {tem_lote}")
            print(f"   Contém 'Validade:': {tem_validade}")
            print(f"   Contém 'Fabricação:': {tem_fabricacao}")
            print(f"   Conteúdo completo: \"{primeiro}\"")

            # Verificar se há MAIS texto além do lote
            sem_lote = re.sub(r'[Ll]ote\s*:\s*\S+', '', primeiro).strip()
            sem_lote = re.sub(r'[Dd]ata\s+de\s+[Vv]alidade\s*:\s*\S+', '', sem_lote).strip()
            sem_lote = re.sub(r'[Dd]ata\s+de\s+[Ff]abrica[çc][ãa]o\s*:\s*\S+', '', sem_lote).strip()
            sem_lote = re.sub(r'\s+', ' ', sem_lote).strip()
            if sem_lote:
                print(f"   Texto residual (sem lote/validade/fabricação): \"{sem_lote}\"")
            else:
                print("   Sem texto residual — infAdProd contém APENAS lote/validade/fabricação")

        return resultado

    except Exception as e:
        print(f"\n   ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None


def query_2_move_lines(odoo, invoice_id):
    """Query 2: l10n_br_informacao_adicional nas move lines da NF"""
    print("\n" + "=" * 80)
    print("QUERY 2: MOVE LINES — l10n_br_informacao_adicional")
    print("=" * 80)

    try:
        # Buscar move lines da invoice
        lines = odoo.search_read(
            'account.move.line',
            [
                ['move_id', '=', invoice_id],
                ['display_type', '=', 'product'],  # Apenas linhas de produto
            ],
            fields=[
                'id', 'name', 'product_id', 'quantity',
                'l10n_br_informacao_adicional',
                'l10n_br_informacao_adicional_produto_ids',
            ],
            limit=30,
        )

        print(f"\n   Invoice ID={invoice_id} — {len(lines)} move lines de produto")

        campo_preenchido = 0
        campo_vazio = 0

        for line in lines:
            info_ad = line.get('l10n_br_informacao_adicional')
            info_ad_ids = line.get('l10n_br_informacao_adicional_produto_ids', [])
            produto = line.get('product_id')
            produto_nome = produto[1] if isinstance(produto, (list, tuple)) else str(produto)

            if info_ad:
                campo_preenchido += 1
            else:
                campo_vazio += 1

            status_ad = f'"{info_ad[:80]}..."' if info_ad and len(info_ad) > 80 else (
                f'"{info_ad}"' if info_ad else 'VAZIO')

            print(f"\n   Line ID={line['id']}")
            print(f"     Produto: {produto_nome[:60]}")
            print(f"     Qtd: {line.get('quantity')}")
            print(f"     l10n_br_informacao_adicional: {status_ad}")
            print(f"     l10n_br_informacao_adicional_produto_ids: {info_ad_ids}")

        print(f"\n   --- Resumo ---")
        print(f"   Campo preenchido: {campo_preenchido}/{len(lines)}")
        print(f"   Campo vazio: {campo_vazio}/{len(lines)}")

        if campo_vazio == len(lines):
            print("\n   >>> CONCLUSÃO: Campo VAZIO em TODAS as linhas")
            print("       → CIEL IT gera infAdProd DINAMICAMENTE (não copia do campo)")
            print("       → Limpar o campo NÃO resolve — precisa de outra abordagem")
        elif campo_preenchido == len(lines):
            print("\n   >>> CONCLUSÃO: Campo PREENCHIDO em TODAS as linhas")
            print("       → CIEL IT pode copiar do campo para infAdProd")
            print("       → Limpar o campo ANTES da transmissão pode funcionar")
        else:
            print("\n   >>> CONCLUSÃO: Campo MISTO (nem todos preenchidos)")
            print("       → Precisa de mais análise")

        return lines

    except Exception as e:
        print(f"\n   ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None


def query_3_mensagem_fiscal(odoo):
    """Query 3: l10n_br_ciel_it_account.mensagem.fiscal — listar TODOS"""
    print("\n" + "=" * 80)
    print("QUERY 3: MENSAGEM FISCAL (mensagem.fiscal)")
    print("=" * 80)

    # Tentar diferentes nomes de modelo
    model_names = [
        'l10n_br_ciel_it_account.mensagem.fiscal',
        'mensagem.fiscal',
        'l10n_br_fiscal.document.related',
        'l10n_br_fiscal.comment',
    ]

    for model_name in model_names:
        try:
            # Verificar se modelo existe
            campos = odoo.execute_kw(
                model_name,
                'fields_get',
                [],
                {'attributes': ['string', 'type', 'help']},
            )
            print(f"\n   Modelo '{model_name}' EXISTE — {len(campos)} campos")

            # Listar campos relevantes
            campos_relevantes = {}
            for nome, info in campos.items():
                nome_lower = nome.lower()
                string_lower = (info.get('string') or '').lower()
                for kw in ['lote', 'lot', 'rastro', 'adicional', 'infad', 'danfe',
                           'print', 'imprim', 'visib', 'mostrar', 'ocultar', 'hide']:
                    if kw in nome_lower or kw in string_lower:
                        campos_relevantes[nome] = info
                        break

            if campos_relevantes:
                print(f"\n   Campos relevantes ({len(campos_relevantes)}):")
                for nome, info in sorted(campos_relevantes.items()):
                    print(f"      {nome} ({info['type']}) — {info.get('string')}")
            else:
                print(f"\n   Nenhum campo com keywords de lote/danfe")

            # Listar registros
            registros = odoo.search_read(
                model_name,
                [],
                fields=list(campos.keys())[:15],  # Primeiros 15 campos
                limit=50,
            )
            print(f"\n   Registros encontrados: {len(registros)}")
            for reg in registros[:20]:
                print(f"      ID={reg['id']} | {reg.get('name', reg.get('display_name', '?'))}")
                # Mostrar campos não-triviais
                for k, v in reg.items():
                    if k in ('id', 'name', 'display_name', '__last_update',
                             'create_uid', 'write_uid', 'create_date', 'write_date'):
                        continue
                    if v and v is not False:
                        v_str = str(v)
                        if len(v_str) > 100:
                            v_str = v_str[:100] + '...'
                        print(f"        {k}: {v_str}")

            return registros

        except Exception as e:
            e_str = str(e)
            if 'does not exist' in e_str or 'not found' in e_str or 'Object' in e_str:
                print(f"\n   Modelo '{model_name}' NÃO EXISTE")
            else:
                print(f"\n   Modelo '{model_name}' — ERRO: {e}")

    print("\n   >>> Nenhum modelo de mensagem fiscal encontrado")
    return None


def query_4_res_config_settings(odoo):
    """Query 4: res.config.settings — TODOS os campos com keywords"""
    print("\n" + "=" * 80)
    print("QUERY 4: RES.CONFIG.SETTINGS — Campos com Keywords")
    print("=" * 80)

    try:
        campos = odoo.execute_kw(
            'res.config.settings',
            'fields_get',
            [],
            {'attributes': ['string', 'type', 'help', 'default']},
        )

        keywords = ['lot', 'lote', 'tracking', 'rastro', 'danfe', 'infad',
                     'adicional', 'imprimir', 'print', 'serial', 'rastreab']

        campos_relevantes = {}
        for nome, info in campos.items():
            nome_lower = nome.lower()
            string_lower = (info.get('string') or '').lower()
            help_lower = (info.get('help') or '').lower()

            for kw in keywords:
                if kw in nome_lower or kw in string_lower or kw in help_lower:
                    campos_relevantes[nome] = info
                    break

        print(f"\n   Total de campos em res.config.settings: {len(campos)}")
        print(f"   Campos com keywords: {len(campos_relevantes)}")

        if campos_relevantes:
            for nome, info in sorted(campos_relevantes.items()):
                print(f"\n      {nome} ({info['type']}) — {info.get('string')}")
                if info.get('help'):
                    print(f"        help: {info['help'][:200]}")
                if info.get('default') is not None:
                    print(f"        default: {info['default']}")

            # Ler valores atuais
            print("\n   --- Valores atuais ---")
            settings_id = odoo.create('res.config.settings', {})
            field_names = list(campos_relevantes.keys())
            settings = odoo.read('res.config.settings', [settings_id], fields=field_names)
            if settings:
                for nome in sorted(field_names):
                    valor = settings[0].get(nome)
                    print(f"      {nome} = {valor}")

        return campos_relevantes

    except Exception as e:
        print(f"\n   ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None


def query_5_config_parameters_ciel_it(odoo):
    """Query 5: TODAS as configs CIEL IT (sem filtro de keyword)"""
    print("\n" + "=" * 80)
    print("QUERY 5: IR.CONFIG_PARAMETER — CIEL IT COMPLETO")
    print("=" * 80)

    try:
        domains = [
            ("TODOS l10n_br_ciel_it", [['key', 'ilike', 'l10n_br_ciel_it']]),
            ("imprimir%", [['key', 'ilike', 'imprimir']]),
            ("danfe%", [['key', 'ilike', 'danfe']]),
            ("print%lote%", [['key', 'ilike', '%lote%']]),
            ("print%lot%", [['key', 'ilike', '%lot%']]),
            ("print%rastro%", [['key', 'ilike', '%rastro%']]),
            ("infad%", [['key', 'ilike', 'infad']]),
            ("adicional%", [['key', 'ilike', 'adicional']]),
        ]

        todos_configs = {}  # dedup por ID

        for desc, domain in domains:
            configs = odoo.search_read(
                'ir.config_parameter',
                domain,
                fields=['id', 'key', 'value'],
                limit=50,
            )
            if configs:
                print(f"\n   [{desc}] -> {len(configs)} resultado(s)")
                for c in configs:
                    if c['id'] not in todos_configs:
                        todos_configs[c['id']] = c
                        valor = str(c.get('value', ''))
                        if len(valor) > 200:
                            valor = valor[:200] + '...'
                        print(f"      ID={c['id']} | key={c['key']}")
                        print(f"        value={valor}")
            else:
                print(f"\n   [{desc}] -> Nenhum resultado")

        # Análise: buscar padrão de nomenclatura baseado no que funciona
        print("\n   --- Análise de padrão de nomenclatura ---")
        ciel_keys = [c['key'] for c in todos_configs.values()
                     if 'l10n_br_ciel_it' in (c.get('key') or '')]
        if ciel_keys:
            print(f"   Keys CIEL IT encontradas ({len(ciel_keys)}):")
            for k in sorted(ciel_keys):
                valor = next(
                    (c['value'] for c in todos_configs.values() if c['key'] == k), '?')
                print(f"      {k} = {valor}")

            # Verificar padrão: imprimir_validade_danfe funciona → buscar imprimir_*_danfe
            imprimir_keys = [k for k in ciel_keys if 'imprimir' in k]
            if imprimir_keys:
                print(f"\n   Keys com 'imprimir' ({len(imprimir_keys)}):")
                for k in imprimir_keys:
                    print(f"      {k}")
                print("\n   >>> Buscar por padrão: l10n_br_ciel_it_account.imprimir_lote_danfe")
        else:
            print("   Nenhuma key CIEL IT encontrada")

        # Buscar explicitamente a config que esperaríamos existir
        print("\n   --- Busca direta por configs esperadas ---")
        expected_keys = [
            'l10n_br_ciel_it_account.imprimir_lote_danfe',
            'l10n_br_ciel_it_account.imprimir_lote',
            'l10n_br_ciel_it_account.lot_on_danfe',
            'l10n_br_ciel_it_account.mostrar_lote_danfe',
            'l10n_br_ciel_it_account.ocultar_lote_danfe',
            'l10n_br_ciel_it_account.print_lot_danfe',
            'l10n_br_ciel_it_account.group_lot_on_invoice',
            'l10n_br_ciel_it_account.infadprod_lote',
        ]
        for expected in expected_keys:
            existing = odoo.search_read(
                'ir.config_parameter',
                [['key', '=', expected]],
                fields=['id', 'key', 'value'],
            )
            status = f"EXISTE (value={existing[0]['value']})" if existing else "NÃO EXISTE"
            print(f"      {expected}: {status}")

        return todos_configs

    except Exception as e:
        print(f"\n   ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None


def query_6_server_action_874(odoo):
    """Query 6: Server action 874 — detalhes completos"""
    print("\n" + "=" * 80)
    print("QUERY 6: SERVER ACTION 874 (action_gerar_xmldanfe_nfe)")
    print("=" * 80)

    try:
        # Buscar por ID e por nome
        actions = odoo.search_read(
            'ir.actions.server',
            ['|',
             ['id', '=', 874],
             ['name', 'ilike', 'gerar%danfe%nfe'],
             ],
            fields=[
                'id', 'name', 'state', 'code', 'model_id',
                'binding_model_id', 'binding_type',
                'sequence', 'groups_id',
            ],
            limit=10,
        )

        if not actions:
            # Busca mais ampla
            print("   ID 874 não encontrado. Buscando por keywords...")
            actions = odoo.search_read(
                'ir.actions.server',
                ['|', '|', '|',
                 ['name', 'ilike', 'danfe'],
                 ['name', 'ilike', 'xmldanfe'],
                 ['name', 'ilike', 'gerar%nfe'],
                 ['name', 'ilike', 'gerar%pdf%nfe'],
                 ],
                fields=[
                    'id', 'name', 'state', 'code', 'model_id',
                    'binding_model_id', 'binding_type',
                ],
                limit=20,
            )

        if actions:
            for action in actions:
                print(f"\n   Server Action ID={action['id']}")
                print(f"     Nome: {action['name']}")
                print(f"     State: {action['state']}")
                print(f"     Model: {action.get('model_id')}")
                print(f"     Binding: {action.get('binding_model_id')}")
                print(f"     Binding Type: {action.get('binding_type')}")
                print(f"     Groups: {action.get('groups_id')}")

                code = action.get('code')
                if code:
                    print(f"\n     --- Código Python ({len(code)} chars) ---")
                    # Mostrar código completo (é importante para análise)
                    for i, line in enumerate(code.split('\n'), 1):
                        print(f"     {i:3d}| {line}")

                    # Análise de keywords no código
                    print(f"\n     --- Análise de keywords no código ---")
                    code_lower = code.lower()
                    for kw in ['lote', 'lot', 'rastro', 'infadprod', 'informacao_adicional',
                               'config_parameter', 'imprimir', 'grupo', 'group', 'tracking']:
                        if kw in code_lower:
                            # Encontrar linhas com a keyword
                            linhas = [l.strip() for l in code.split('\n')
                                      if kw in l.lower()]
                            print(f"     '{kw}' encontrado em {len(linhas)} linha(s):")
                            for l in linhas[:5]:
                                print(f"        {l[:120]}")
                        else:
                            print(f"     '{kw}': NÃO encontrado")
                else:
                    print("     Código: VAZIO (pode ser ação de tipo diferente)")
        else:
            print("\n   Nenhum server action encontrado para DANFE/NF-e")

        return actions

    except Exception as e:
        print(f"\n   ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None


def query_7_base_automation(odoo):
    """Query 7: base.automation em account.move"""
    print("\n" + "=" * 80)
    print("QUERY 7: BASE.AUTOMATION em account.move")
    print("=" * 80)

    try:
        # Buscar modelo account.move
        model_ids = odoo.search_read(
            'ir.model',
            [['model', '=', 'account.move']],
            fields=['id'],
            limit=1,
        )
        model_id = model_ids[0]['id'] if model_ids else None

        automations = odoo.search_read(
            'base.automation',
            [['model_id.model', '=', 'account.move']],
            fields=[
                'id', 'name', 'trigger', 'trigger_field_ids',
                'action_server_ids', 'active', 'filter_domain',
                'filter_pre_domain', 'last_run',
            ],
            limit=20,
        )

        if automations:
            print(f"\n   Automated actions em account.move: {len(automations)}")
            for a in automations:
                print(f"\n   ID={a['id']} | {a['name']}")
                print(f"     Trigger: {a.get('trigger')}")
                print(f"     Active: {a.get('active')}")
                print(f"     Trigger fields: {a.get('trigger_field_ids')}")
                print(f"     Server actions: {a.get('action_server_ids')}")
                print(f"     Filter domain: {a.get('filter_domain')}")
                print(f"     Filter pre domain: {a.get('filter_pre_domain')}")
                print(f"     Last run: {a.get('last_run')}")

                # Detalhar server actions vinculadas
                sa_ids = a.get('action_server_ids', [])
                if sa_ids:
                    for sa_id in sa_ids:
                        sa = odoo.read(
                            'ir.actions.server',
                            [sa_id],
                            fields=['id', 'name', 'state', 'code'],
                        )
                        if sa:
                            sa = sa[0]
                            print(f"\n     Server Action ID={sa['id']} | {sa['name']}")
                            code = sa.get('code')
                            if code:
                                # Mostrar primeiras 20 linhas
                                linhas = code.split('\n')
                                print(f"     Código ({len(linhas)} linhas):")
                                for l in linhas[:20]:
                                    print(f"       {l}")
                                if len(linhas) > 20:
                                    print(f"       ... ({len(linhas) - 20} linhas restantes)")
        else:
            print("\n   Nenhuma automated action em account.move")

        # Também buscar para account.move.line
        automations_line = odoo.search_read(
            'base.automation',
            [['model_id.model', '=', 'account.move.line']],
            fields=['id', 'name', 'trigger', 'active'],
            limit=10,
        )
        if automations_line:
            print(f"\n   Automated actions em account.move.line: {len(automations_line)}")
            for a in automations_line:
                print(f"      ID={a['id']} | {a['name']} | trigger={a.get('trigger')} | active={a.get('active')}")
        else:
            print("\n   Nenhuma automated action em account.move.line")

        return automations

    except Exception as e:
        print(f"\n   ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None


def query_8_server_actions_account_move(odoo):
    """Query 8: Todos os server actions vinculados a account.move"""
    print("\n" + "=" * 80)
    print("QUERY 8: SERVER ACTIONS VINCULADOS A ACCOUNT.MOVE")
    print("=" * 80)

    try:
        # Buscar model ID de account.move
        model_ids = odoo.search_read(
            'ir.model',
            [['model', '=', 'account.move']],
            fields=['id'],
            limit=1,
        )

        if not model_ids:
            print("\n   Modelo account.move não encontrado no ir.model!")
            return None

        model_id = model_ids[0]['id']
        print(f"\n   account.move model_id = {model_id}")

        # Server actions com binding_model_id = account.move
        actions = odoo.search_read(
            'ir.actions.server',
            [['binding_model_id', '=', model_id]],
            fields=[
                'id', 'name', 'state', 'binding_type',
                'groups_id', 'sequence',
            ],
            limit=50,
        )

        if actions:
            print(f"\n   Server actions com binding em account.move: {len(actions)}")
            for a in sorted(actions, key=lambda x: x.get('sequence', 0)):
                print(f"\n      ID={a['id']} | {a['name']}")
                print(f"        State: {a['state']} | Binding: {a.get('binding_type')}")
                print(f"        Groups: {a.get('groups_id')} | Seq: {a.get('sequence')}")

            # Buscar detalhes dos que parecem relacionados a DANFE/PDF/NF-e
            danfe_related = [a for a in actions
                            if any(kw in (a.get('name') or '').lower()
                                   for kw in ['danfe', 'pdf', 'nfe', 'xml', 'gerar',
                                              'imprimir', 'regenerar', 'reprocessar'])]

            if danfe_related:
                print(f"\n   --- Ações relacionadas a DANFE/PDF/NF-e ({len(danfe_related)}) ---")
                for a in danfe_related:
                    # Ler código completo
                    full = odoo.read(
                        'ir.actions.server',
                        [a['id']],
                        fields=['code'],
                    )
                    code = full[0].get('code') if full else None
                    print(f"\n   Action ID={a['id']} | {a['name']}")
                    if code:
                        print(f"   Código ({len(code)} chars):")
                        for i, line in enumerate(code.split('\n'), 1):
                            print(f"     {i:3d}| {line}")
                    else:
                        print(f"   Código: VAZIO")
        else:
            print("\n   Nenhum server action com binding em account.move")

        return actions

    except Exception as e:
        print(f"\n   ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None


def query_9_campos_stock_lot_product(odoo):
    """Query 9: Campos de stock.lot e product.template relevantes"""
    print("\n" + "=" * 80)
    print("QUERY 9: CAMPOS stock.lot E product.template")
    print("=" * 80)

    keywords = ['danfe', 'infadprod', 'informacao', 'adicional', 'lot', 'lote',
                'display', 'visibility', 'visib', 'ocultar', 'hide', 'show',
                'print', 'imprimir', 'rastro']

    for model_name in ['stock.lot', 'product.template', 'product.product']:
        try:
            campos = odoo.execute_kw(
                model_name,
                'fields_get',
                [],
                {'attributes': ['string', 'type', 'help']},
            )

            campos_relevantes = {}
            for nome, info in campos.items():
                nome_lower = nome.lower()
                string_lower = (info.get('string') or '').lower()
                help_lower = (info.get('help') or '').lower()

                for kw in keywords:
                    if kw in nome_lower or kw in string_lower or kw in help_lower:
                        campos_relevantes[nome] = info
                        break

            print(f"\n   {model_name}: {len(campos)} campos total, "
                  f"{len(campos_relevantes)} relevantes")

            if campos_relevantes:
                for nome, info in sorted(campos_relevantes.items()):
                    print(f"      {nome} ({info['type']}) — {info.get('string')}")
                    if info.get('help'):
                        print(f"        help: {info['help'][:200]}")

        except Exception as e:
            print(f"\n   {model_name}: ERRO — {e}")

    return None


def query_10_campo_writeable(odoo, invoice_id):
    """Query 10: Verificar se l10n_br_informacao_adicional é writable"""
    print("\n" + "=" * 80)
    print("QUERY 10: CAMPO l10n_br_informacao_adicional — WRITE TEST")
    print("=" * 80)

    try:
        # Verificar atributos do campo
        campos = odoo.execute_kw(
            'account.move.line',
            'fields_get',
            [['l10n_br_informacao_adicional']],
            {'attributes': ['string', 'type', 'readonly', 'required',
                            'help', 'store', 'depends', 'compute']},
        )

        campo = campos.get('l10n_br_informacao_adicional', {})
        print(f"\n   Campo: l10n_br_informacao_adicional")
        print(f"   Type: {campo.get('type')}")
        print(f"   String: {campo.get('string')}")
        print(f"   Readonly: {campo.get('readonly')}")
        print(f"   Required: {campo.get('required')}")
        print(f"   Store: {campo.get('store')}")
        print(f"   Compute: {campo.get('compute')}")
        print(f"   Depends: {campo.get('depends')}")
        print(f"   Help: {campo.get('help')}")

        is_computed = bool(campo.get('compute'))
        is_stored = campo.get('store', True)
        is_readonly = campo.get('readonly', False)

        if is_computed and not is_stored:
            print("\n   >>> CAMPO É COMPUTED E NÃO ARMAZENADO")
            print("       → Não é possível escrever diretamente")
            print("       → Valor é gerado dinamicamente")
        elif is_computed and is_stored:
            print("\n   >>> CAMPO É COMPUTED E ARMAZENADO")
            print("       → Escrita pode ser sobrescrita na próxima recomputação")
        elif is_readonly:
            print("\n   >>> CAMPO É READONLY")
            print("       → Pode não aceitar escrita via XML-RPC")
        else:
            print("\n   >>> CAMPO PARECE WRITEABLE")

        # Verificar se campo existe e ler valor de uma move line (sem escrever)
        lines = odoo.search_read(
            'account.move.line',
            [
                ['move_id', '=', invoice_id],
                ['display_type', '=', 'product'],
            ],
            fields=['id', 'l10n_br_informacao_adicional'],
            limit=1,
        )

        if lines:
            line = lines[0]
            valor_atual = line.get('l10n_br_informacao_adicional')
            print(f"\n   Valor atual na line ID={line['id']}:")
            print(f"     \"{valor_atual}\"" if valor_atual else "     VAZIO (None/False)")

            # Verificar infAdProd no XML para comparar
            print("\n   >>> NÃO ESCREVENDO (produção) — apenas verificação de atributos")
        else:
            print("\n   Nenhuma move line de produto encontrada para a invoice")

        # Verificar campos relacionados que podem influenciar
        print("\n   --- Outros campos l10n_br_informacao* ---")
        all_fields = odoo.execute_kw(
            'account.move.line',
            'fields_get',
            [],
            {'attributes': ['string', 'type', 'compute', 'store']},
        )
        info_fields = {k: v for k, v in all_fields.items()
                       if 'informacao' in k.lower() or 'infad' in k.lower()
                       or 'adicional' in k.lower()}
        for nome, info in sorted(info_fields.items()):
            computed = 'COMPUTED' if info.get('compute') else 'STORED'
            print(f"      {nome} ({info['type']}) — {info.get('string')} [{computed}]")

        return campo

    except Exception as e:
        print(f"\n   ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None


def gerar_relatorio_final(resultados):
    """Gera relatório com recomendação de abordagem"""
    print("\n" + "=" * 80)
    print("RELATÓRIO FINAL — RECOMENDAÇÃO DE ABORDAGEM")
    print("=" * 80)

    q1 = resultados.get('q1')
    q2 = resultados.get('q2')
    q5 = resultados.get('q5')
    q6 = resultados.get('q6')
    q10 = resultados.get('q10')

    # Análise H1: infAdProd é dinâmico?
    h1_dinamico = False
    if q2 is not None:
        campo_vazio = all(
            not line.get('l10n_br_informacao_adicional') for line in (q2 or []))
        h1_dinamico = campo_vazio

    # Análise H2: config CIEL IT existe?
    h2_config_existe = False
    if q5:
        ciel_keys = [c['key'] for c in q5.values()
                     if 'imprimir' in (c.get('key') or '').lower()
                     and 'lote' in (c.get('key') or '').lower()]
        h2_config_existe = len(ciel_keys) > 0

    # Análise H4: server action tem referência a lote?
    h4_sa_lote = False
    if q6:
        for action in (q6 or []):
            code = action.get('code', '')
            if code and any(kw in code.lower() for kw in ['lote', 'lot', 'rastro']):
                h4_sa_lote = True

    # Análise campo writable
    campo_writable = False
    if q10:
        campo_writable = (
            not q10.get('compute')
            and q10.get('store', True)
            and not q10.get('readonly', False)
        )

    print(f"""
   HIPÓTESES TESTADAS:
   -------------------
   H1 (infAdProd dinâmico): {'CONFIRMADO — campo vazio, CIEL IT gera dinamicamente' if h1_dinamico else 'NÃO — campo preenchido antes da transmissão'}
   H2 (config CIEL IT):     {'ENCONTRADA' if h2_config_existe else 'NÃO ENCONTRADA — sem config nativa para lote no infAdProd'}
   H4 (server action 874):  {'REFERENCIA LOTE' if h4_sa_lote else 'SEM REFERÊNCIA — código não menciona lote/rastro'}

   CAMPO l10n_br_informacao_adicional:
   - Writable via API: {'SIM' if campo_writable else 'NÃO (computed ou readonly)'}
   - Computed: {q10.get('compute', '?') if q10 else '?'}

   ABORDAGENS (ordenadas por viabilidade):
   ----------------------------------------
""")

    if h2_config_existe:
        print("   >>> OPÇÃO A: CONFIG CIEL IT (MELHOR CENÁRIO)")
        print("       Config encontrada — alterar via ir.config_parameter")
        print("       Reversível, simples, sem side effects")
        return 'A'

    if not h1_dinamico and campo_writable:
        print("   >>> OPÇÃO B: LIMPAR l10n_br_informacao_adicional")
        print("       Campo preenchido e writable — limpar antes da transmissão")
        print("       Risco: CIEL IT pode sobrescrever durante geração")
        print()

    print("   >>> OPÇÃO D: PÓS-PROCESSAMENTO PDF (FALLBACK MAIS CONFIÁVEL)")
    print("       1. Ler l10n_br_pdf_aut_nfe (base64)")
    print("       2. Decodar PDF")
    print("       3. Redactar texto 'Lote: XXX' com pypdf/pikepdf")
    print("       4. Re-encodar e gravar PDF modificado")
    print("       5. XML (<rastro>) permanece intacto")
    print()
    print("   >>> OPÇÃO E: base.automation + server action pós-transmissão")
    print("       Trigger: on_write quando l10n_br_situacao_nf → 'autorizado'")
    print("       Automático para toda NF-e nova")
    print("       Pode combinar com Opção D (redação do PDF)")

    return 'D'


def main():
    parser = argparse.ArgumentParser(
        description='Investigação Profunda — DANFE e Lotes (Fase 2)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s                              # Todas as 10 queries
  %(prog)s --invoice-id 517038          # Invoice específica
  %(prog)s --query 1,2,5               # Apenas queries 1, 2 e 5
  %(prog)s --query 6                    # Apenas server action 874
""",
    )
    parser.add_argument('--invoice-id', type=int, default=DEFAULT_INVOICE_ID,
                        help=f'ID da invoice (default: {DEFAULT_INVOICE_ID})')
    parser.add_argument('--query', type=str, default=None,
                        help='Queries específicas (ex: 1,2,5)')

    args = parser.parse_args()

    queries_selecionadas = None
    if args.query:
        queries_selecionadas = set(int(q.strip()) for q in args.query.split(','))

    def deve_executar(n):
        return queries_selecionadas is None or n in queries_selecionadas

    print("=" * 80)
    print("INVESTIGAÇÃO PROFUNDA — DANFE E LOTES NO ODOO (CIEL IT) — FASE 2")
    print("Todas as queries são READ-ONLY — nenhuma modificação será feita")
    print(f"Invoice de referência: ID={args.invoice_id}")
    if queries_selecionadas:
        print(f"Queries selecionadas: {sorted(queries_selecionadas)}")
    print("=" * 80)

    app = create_app()

    with app.app_context():
        odoo = get_odoo_connection()

        resultados = {}

        if deve_executar(1):
            resultados['q1'] = query_1_xml_conteudo(odoo, args.invoice_id)

        if deve_executar(2):
            resultados['q2'] = query_2_move_lines(odoo, args.invoice_id)

        if deve_executar(3):
            resultados['q3'] = query_3_mensagem_fiscal(odoo)

        if deve_executar(4):
            resultados['q4'] = query_4_res_config_settings(odoo)

        if deve_executar(5):
            resultados['q5'] = query_5_config_parameters_ciel_it(odoo)

        if deve_executar(6):
            resultados['q6'] = query_6_server_action_874(odoo)

        if deve_executar(7):
            resultados['q7'] = query_7_base_automation(odoo)

        if deve_executar(8):
            resultados['q8'] = query_8_server_actions_account_move(odoo)

        if deve_executar(9):
            resultados['q9'] = query_9_campos_stock_lot_product(odoo)

        if deve_executar(10):
            resultados['q10'] = query_10_campo_writeable(odoo, args.invoice_id)

        # Relatório final (somente se rodou queries suficientes)
        if queries_selecionadas is None or len(queries_selecionadas) >= 3:
            abordagem = gerar_relatorio_final(resultados)
            print(f"\n   ABORDAGEM RECOMENDADA: {abordagem}")

    print("\n" + "=" * 80)
    print("INVESTIGAÇÃO FASE 2 CONCLUÍDA")
    print("=" * 80)


if __name__ == '__main__':
    main()
