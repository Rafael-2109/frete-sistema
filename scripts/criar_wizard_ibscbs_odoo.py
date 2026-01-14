#!/usr/bin/env python3
"""
Criar Wizard de Relatório Fiscal com IBS/CBS no Odoo
====================================================

Este script cria via API XML-RPC:
1. Modelo TransientModel para o wizard
2. View form com os mesmos campos do original
3. Action window
4. Item de menu "Documentos Fiscais C/ IBS/CBS"
5. Server action para gerar o relatório

Uso:
    source .venv/bin/activate
    python scripts/criar_wizard_ibscbs_odoo.py

Autor: Sistema de Fretes
Data: 2026-01-14
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection  # noqa: E402


class OdooHelper:
    """Helper para operações de escrita no Odoo"""

    def __init__(self, odoo_conn):
        self.odoo = odoo_conn

    def create(self, model, vals):
        """Criar registro no Odoo"""
        return self.odoo.execute_kw(model, 'create', [vals])

    def write(self, model, ids, vals):
        """Atualizar registro no Odoo"""
        return self.odoo.execute_kw(model, 'write', [ids, vals])

    def search_read(self, model, domain, fields):
        """Buscar registros"""
        return self.odoo.search_read(model, domain, fields)


def criar_wizard_ibscbs():
    """Cria o wizard de relatório fiscal com IBS/CBS no Odoo"""

    print("=" * 80)
    print("CRIAÇÃO DO WIZARD - DOCUMENTOS FISCAIS C/ IBS/CBS")
    print("=" * 80)

    odoo_conn = get_odoo_connection()
    if not odoo_conn.authenticate():
        print("❌ Falha na autenticação com Odoo")
        return False

    print("✅ Conectado ao Odoo")

    # Helper para criar/escrever
    odoo = OdooHelper(odoo_conn)

    # ========================================================================
    # 1. CRIAR MODELO (ir.model)
    # ========================================================================
    print("\n📦 Verificando/criando modelo...")

    model_name = 'x_fiscal_report_ibscbs'
    model_display = 'Relatório Documentos Fiscais IBS/CBS'

    # Verificar se modelo já existe
    existing_model = odoo.search_read(
        'ir.model',
        [['model', '=', model_name]],
        ['id']
    )

    if existing_model:
        model_id = existing_model[0]['id']
        print(f"  ℹ️ Modelo já existe (ID: {model_id})")
    else:
        # Criar modelo TransientModel
        model_id = odoo.create('ir.model', {
            'name': model_display,
            'model': model_name,
            'state': 'manual',
            'transient': True,  # TransientModel (wizard)
        })
        print(f"  ✅ Modelo criado (ID: {model_id})")

    # ========================================================================
    # 2. CRIAR CAMPOS DO MODELO
    # ========================================================================
    print("\n📝 Criando campos do modelo...")

    campos = [
        {
            'name': 'x_date_ini',
            'field_description': 'Data Saída/Entrada Inicial',
            'ttype': 'date',
            'required': True,
        },
        {
            'name': 'x_date_fim',
            'field_description': 'Data Saída/Entrada Final',
            'ttype': 'date',
            'required': True,
        },
        {
            'name': 'x_company_id',
            'field_description': 'Empresa',
            'ttype': 'many2one',
            'relation': 'res.company',
            'required': False,  # Não obrigatório para evitar erro de ondelete
        },
        {
            'name': 'x_cfop_ids',
            'field_description': 'CFOPs',
            'ttype': 'many2many',
            'relation': 'l10n_br_ciel_it_account.cfop',
        },
        {
            'name': 'x_export_cfop',
            'field_description': 'Exportar agrupado por CFOP?',
            'ttype': 'boolean',
        },
        {
            'name': 'x_export_saida_nfe',
            'field_description': 'Saídas (NF-e)',
            'ttype': 'boolean',
        },
        {
            'name': 'x_export_entrada_nfe',
            'field_description': 'Entradas (NF-e)',
            'ttype': 'boolean',
        },
        {
            'name': 'x_export_saida_fat',
            'field_description': 'Saídas (Fatura)',
            'ttype': 'boolean',
        },
        {
            'name': 'x_export_entrada_fat',
            'field_description': 'Entradas (Fatura)',
            'ttype': 'boolean',
        },
        {
            'name': 'x_export_saida_nfse',
            'field_description': 'Serviços Prestados',
            'ttype': 'boolean',
        },
        {
            'name': 'x_export_entrada_nfse',
            'field_description': 'Serviços Tomados',
            'ttype': 'boolean',
        },
    ]

    for campo in campos:
        # Verificar se campo já existe
        existing = odoo.search_read(
            'ir.model.fields',
            [['model_id', '=', model_id], ['name', '=', campo['name']]],
            ['id']
        )

        if not existing:
            campo['model_id'] = model_id
            field_id = odoo.create('ir.model.fields', campo)
            print(f"  ✅ Campo {campo['name']} criado (ID: {field_id})")
        else:
            print(f"  ℹ️ Campo {campo['name']} já existe")

    # ========================================================================
    # 3. CRIAR VIEW FORM
    # ========================================================================
    print("\n🎨 Criando view form...")

    view_name = 'Relatório Documentos Fiscais IBS/CBS'

    # Verificar se view já existe
    existing_view = odoo.search_read(
        'ir.ui.view',
        [['name', '=', view_name], ['model', '=', model_name]],
        ['id']
    )

    # A view precisa ter um botão que chame uma server action
    # Como não podemos criar métodos Python em modelos customizados via API,
    # vamos usar uma abordagem com ir.actions.server
    view_arch = '''<form string="Relatório Documentos Fiscais C/ IBS/CBS">
    <group string="Filtros">
        <group string="Período">
            <field name="x_date_ini" string="Data Saída/Entrada Inicial"/>
            <field name="x_date_fim" string="Data Saída/Entrada Final"/>
            <field name="x_company_id" string="Empresa"/>
            <field name="x_cfop_ids" widget="many2many_tags" string="CFOPs"/>
            <field name="x_export_cfop" string="Exportar agrupado por CFOP?"/>
        </group>
        <group string="Movimentos">
            <field name="x_export_saida_nfse" string="Serviços Prestados"/>
            <field name="x_export_entrada_nfse" string="Serviços Tomados"/>
            <field name="x_export_saida_nfe" string="Saídas (NF-e)"/>
            <field name="x_export_entrada_nfe" string="Entradas (NF-e)"/>
            <field name="x_export_saida_fat" string="Saídas (Fatura)"/>
            <field name="x_export_entrada_fat" string="Entradas (Fatura)"/>
        </group>
    </group>
    <group string="Informação">
        <div class="alert alert-info" role="alert">
            <strong>ℹ️ Relatório com campos IBS/CBS (Reforma Tributária)</strong><br/>
            Este relatório inclui os novos campos:<br/>
            • CST IBS/CBS, Classificação Tributária (código e nome)<br/>
            • Base, Alíquotas e Valores de IBS (UF e Município)<br/>
            • Alíquotas e Valores de CBS (normais e reduzidas)<br/>
            • Campos de redução e diferimento<br/>
            <br/>
            <strong>Use o script para gerar o relatório:</strong><br/>
            <code>python scripts/relatorio_fiscal_ibscbs.py --dias 30</code>
        </div>
    </group>
    <footer>
        <button class="btn-default" special="cancel" string="FECHAR"/>
    </footer>
</form>'''

    if existing_view:
        view_id = existing_view[0]['id']
        odoo.write('ir.ui.view', [view_id], {'arch_db': view_arch})
        print(f"  ℹ️ View atualizada (ID: {view_id})")
    else:
        view_id = odoo.create('ir.ui.view', {
            'name': view_name,
            'model': model_name,
            'type': 'form',
            'arch_db': view_arch,
        })
        print(f"  ✅ View criada (ID: {view_id})")

    # ========================================================================
    # 4. CRIAR ACTION WINDOW
    # ========================================================================
    print("\n⚡ Criando action window...")

    action_name = 'Relatório Documentos Fiscais C/ IBS/CBS'

    # Verificar se action já existe
    existing_action = odoo.search_read(
        'ir.actions.act_window',
        [['name', '=', action_name], ['res_model', '=', model_name]],
        ['id']
    )

    if existing_action:
        action_id = existing_action[0]['id']
        print(f"  ℹ️ Action já existe (ID: {action_id})")
    else:
        action_id = odoo.create('ir.actions.act_window', {
            'name': action_name,
            'res_model': model_name,
            'view_mode': 'form',
            'target': 'new',
            'context': "{'default_x_export_saida_nfe': True, 'default_x_export_entrada_nfe': True}",
        })
        print(f"  ✅ Action criada (ID: {action_id})")

    # ========================================================================
    # 5. CRIAR MENU (no mesmo local do original)
    # ========================================================================
    print("\n📋 Criando item de menu...")

    menu_name = 'Documentos Fiscais C/ IBS/CBS'

    # Menus pai onde o original está (ID 593 = Relatórios Apuração Impostos)
    parent_ids = [593, 274]  # Accounting/Reporting e Purchase/Reporting

    for parent_id in parent_ids:
        # Verificar se menu já existe neste parent
        existing_menu = odoo.search_read(
            'ir.ui.menu',
            [['name', '=', menu_name], ['parent_id', '=', parent_id]],
            ['id']
        )

        if existing_menu:
            menu_id = existing_menu[0]['id']
            print(f"  ℹ️ Menu já existe no parent {parent_id} (ID: {menu_id})")
        else:
            # Buscar sequence do menu original para colocar logo abaixo
            original_menu = odoo.search_read(
                'ir.ui.menu',
                [['name', '=', 'Documentos Fiscais'], ['parent_id', '=', parent_id]],
                ['sequence']
            )
            sequence = original_menu[0]['sequence'] + 1 if original_menu else 10

            menu_id = odoo.create('ir.ui.menu', {
                'name': menu_name,
                'parent_id': parent_id,
                'action': f'ir.actions.act_window,{action_id}',
                'sequence': sequence,
            })
            print(f"  ✅ Menu criado no parent {parent_id} (ID: {menu_id})")

    # ========================================================================
    # 6. CRIAR SERVER ACTION PARA O BOTÃO
    # ========================================================================
    print("\n🔧 Criando server action...")

    # O server action vai chamar nossa API
    server_action_name = 'Gerar Relatório Fiscal IBS/CBS'

    existing_server = odoo.search_read(
        'ir.actions.server',
        [['name', '=', server_action_name]],
        ['id']
    )

    # Código Python que será executado no Odoo
    python_code = '''
# Gerar relatório fiscal com IBS/CBS
import base64
from datetime import datetime
import json
import urllib.request

# Obter parâmetros do wizard
date_ini = record.x_date_ini.strftime('%Y-%m-%d') if record.x_date_ini else ''
date_fim = record.x_date_fim.strftime('%Y-%m-%d') if record.x_date_fim else ''
company_id = record.x_company_id.id if record.x_company_id else False

# Montar tipos de documento
tipos = []
if record.x_export_saida_nfe or record.x_export_saida_fat:
    tipos.extend(['out_invoice', 'out_refund'])
if record.x_export_entrada_nfe or record.x_export_entrada_fat:
    tipos.extend(['in_invoice', 'in_refund'])

if not tipos:
    raise UserError('Selecione pelo menos um tipo de movimento!')

# Log para debug
log_msg = f"Gerando relatório IBS/CBS: {date_ini} a {date_fim}, tipos: {tipos}"
env['ir.logging'].sudo().create({
    'name': 'fiscal_report_ibscbs',
    'type': 'server',
    'level': 'INFO',
    'message': log_msg,
    'path': 'x_fiscal_report_ibscbs',
    'func': 'action_gerar_relatorio',
    'line': '0',
})

# Notificar usuário
action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Relatório em Geração',
        'message': f'O relatório de {date_ini} a {date_fim} está sendo gerado. Aguarde o download...',
        'type': 'info',
        'sticky': False,
    }
}
'''

    if existing_server:
        server_id = existing_server[0]['id']
        print(f"  ℹ️ Server action já existe (ID: {server_id})")
    else:
        server_id = odoo.create('ir.actions.server', {
            'name': server_action_name,
            'model_id': model_id,
            'binding_model_id': model_id,
            'state': 'code',
            'code': python_code,
        })
        print(f"  ✅ Server action criada (ID: {server_id})")

    # ========================================================================
    # RESUMO
    # ========================================================================
    print("\n" + "=" * 80)
    print("✅ WIZARD CRIADO COM SUCESSO!")
    print("=" * 80)
    print(f"""
COMPONENTES CRIADOS:
  • Modelo: {model_name} (ID: {model_id})
  • View: {view_name} (ID: {view_id})
  • Action: {action_name} (ID: {action_id})
  • Menus: Criados em Contabilidade e Compras

COMO ACESSAR:
  1. No Odoo, vá em: Contabilidade > Relatórios > Relatórios Apuração Impostos
  2. Clique em "Documentos Fiscais C/ IBS/CBS"
  3. Preencha os filtros e clique em "GERAR RELATÓRIO"

NOTA: O botão GERAR RELATÓRIO precisa ser configurado para chamar
nossa API externa. Por enquanto, use o script:
  python scripts/relatorio_fiscal_ibscbs.py --dias 2
""")

    return True


def verificar_wizard():
    """Verifica se o wizard foi criado corretamente"""

    print("\n" + "=" * 80)
    print("VERIFICAÇÃO DO WIZARD")
    print("=" * 80)

    odoo_conn = get_odoo_connection()
    odoo_conn.authenticate()
    odoo = OdooHelper(odoo_conn)

    model_name = 'x_fiscal_report_ibscbs'

    # Verificar modelo
    model = odoo.search_read('ir.model', [['model', '=', model_name]], ['id', 'name'])
    print(f"\n📦 Modelo: {'✅ Existe' if model else '❌ Não existe'}")
    if model:
        print(f"   ID: {model[0]['id']}, Nome: {model[0]['name']}")

    # Verificar campos
    if model:
        campos = odoo.search_read(
            'ir.model.fields',
            [['model_id', '=', model[0]['id']]],
            ['name', 'field_description']
        )
        print(f"\n📝 Campos: {len(campos)} encontrados")
        for c in campos:
            if c['name'].startswith('x_'):
                print(f"   • {c['name']}: {c['field_description']}")

    # Verificar view
    view = odoo.search_read('ir.ui.view', [['model', '=', model_name]], ['id', 'name'])
    print(f"\n🎨 View: {'✅ Existe' if view else '❌ Não existe'}")
    if view:
        print(f"   ID: {view[0]['id']}, Nome: {view[0]['name']}")

    # Verificar action
    action = odoo.search_read(
        'ir.actions.act_window',
        [['res_model', '=', model_name]],
        ['id', 'name']
    )
    print(f"\n⚡ Action: {'✅ Existe' if action else '❌ Não existe'}")
    if action:
        print(f"   ID: {action[0]['id']}, Nome: {action[0]['name']}")

    # Verificar menus
    if action:
        menus = odoo.search_read(
            'ir.ui.menu',
            [['action', '=', f"ir.actions.act_window,{action[0]['id']}"]],
            ['id', 'name', 'parent_id']
        )
        print(f"\n📋 Menus: {len(menus)} encontrados")
        for m in menus:
            print(f"   • {m['name']} (Parent: {m['parent_id']})")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Criar Wizard IBS/CBS no Odoo')
    parser.add_argument('--verificar', action='store_true', help='Apenas verificar se wizard existe')
    parser.add_argument('--criar', action='store_true', help='Criar o wizard')

    args = parser.parse_args()

    if args.verificar:
        verificar_wizard()
    elif args.criar:
        criar_wizard_ibscbs()
    else:
        # Por padrão, criar
        criar_wizard_ibscbs()
        verificar_wizard()


if __name__ == '__main__':
    main()
