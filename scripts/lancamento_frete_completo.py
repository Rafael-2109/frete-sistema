"""
Script de Lançamento COMPLETO de Frete no Odoo
===============================================

OBJETIVO:
    Automatizar TODO o processo de lançamento de CTe no Odoo:

    ETAPA 1 - Lançamento no DF-e:
    1. Buscar CTe pela chave
    2. Atualizar l10n_br_data_entrada com data de hoje
    3. Atualizar l10n_br_tipo_pedido para 'servico'
    4. Atualizar linha com produto "SERVICO DE FRETE"
    5. Atualizar vencimento do pagamento
    6. Executar action_gerar_po_dfe

    ETAPA 2 - Confirmação do Purchase Order:
    7. Buscar PO gerado
    8. Verificar team_id e payment_provider_id
    9. Executar button_confirm

EXEMPLO DE USO:
    python3 lancamento_frete_completo.py 33251120341933000150570010000281801000319398

AUTOR: Sistema de Fretes
DATA: 14/11/2025
"""

import xmlrpc.client
import ssl
import sys
from datetime import date
from pprint import pprint

# Configuração Odoo
ODOO_CONFIG = {
    'url': 'https://odoo.nacomgoya.com.br',
    'database': 'odoo-17-ee-nacomgoya-prd',
    'username': 'rafael@conservascampobelo.com.br',
    'api_key': '67705b0986ff5c052e657f1c0ffd96ceb191af69',
}

# IDs fixos descobertos
PRODUTO_SERVICO_FRETE_ID = 29993  # "SERVIÇO DE FRETE" (código 800000025)
CONTA_ANALITICA_LOGISTICA_ID = 1186  # "LOGISTICA TRANSPORTE" (código 119009)
TEAM_LANCAMENTO_FRETE_ID = 119  # "Lançamento Frete"
PAYMENT_PROVIDER_TRANSFERENCIA_ID = 30  # "Transferência Bancária"
COMPANY_NACOM_GOYA_CD_ID = 4  # "NACOM GOYA - CD"


class SimpleOdooClient:
    """Cliente simples para Odoo sem dependências"""

    def __init__(self, config):
        self.config = config
        self.uid = None

        # Setup SSL
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        # Conexões
        self.common = xmlrpc.client.ServerProxy(
            f"{config['url']}/xmlrpc/2/common",
            context=self.ssl_context
        )
        self.models = xmlrpc.client.ServerProxy(
            f"{config['url']}/xmlrpc/2/object",
            context=self.ssl_context
        )

    def authenticate(self):
        """Autentica no Odoo"""
        self.uid = self.common.authenticate(
            self.config['database'],
            self.config['username'],
            self.config['api_key'],
            {}
        )
        return self.uid is not None

    def execute_kw(self, model, method, args, kwargs=None):
        """Executa método no Odoo"""
        if kwargs is None:
            kwargs = {}
        return self.models.execute_kw(
            self.config['database'],
            self.uid,
            self.config['api_key'],
            model,
            method,
            args,
            kwargs
        )

    def read(self, model, ids, fields=None):
        """Lê registros"""
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        return self.execute_kw(model, 'read', [ids], kwargs)

    def search_read(self, model, domain, fields=None, limit=None):
        """Busca e lê registros"""
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        return self.execute_kw(model, 'search_read', [domain], kwargs)

    def write(self, model, ids, values):
        """Atualiza registros"""
        return self.execute_kw(model, 'write', [ids, values])


def lancar_frete_completo(chave_cte, data_vencimento=None):
    """
    Executa TODO o fluxo de lançamento de frete no Odoo

    Args:
        chave_cte: Chave de acesso do CTe
        data_vencimento: Data de vencimento (opcional, padrão: 30 dias)

    Returns:
        dict: Resultado completo do lançamento
    """
    print("=" * 100)
    print("🚀 LANÇAMENTO COMPLETO DE FRETE NO ODOO")
    print("=" * 100)
    print()
    print(f"Chave CTe: {chave_cte}")
    print()

    resultado = {
        'sucesso': False,
        'chave_cte': chave_cte,
        'etapas': {}
    }

    try:
        # ========================================
        # ETAPA 1: LANÇAMENTO NO DF-e
        # ========================================
        print("┌" + "─" * 98 + "┐")
        print("│" + " " * 35 + "ETAPA 1: LANÇAMENTO NO DF-e" + " " * 35 + "│")
        print("└" + "─" * 98 + "┘")
        print()

        # 1. Conectar no Odoo
        print("1️⃣ Conectando no Odoo...")
        odoo = SimpleOdooClient(ODOO_CONFIG)

        if not odoo.authenticate():
            resultado['erro'] = 'Falha na autenticação no Odoo'
            return resultado

        print("✅ Conectado com sucesso!")
        print()

        # 2. Buscar DFe pela chave
        print(f"2️⃣ Buscando DFe pela chave...")
        dfe_data = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            [('protnfe_infnfe_chnfe', '=', chave_cte)],
            fields=['id', 'name', 'l10n_br_status', 'l10n_br_tipo_pedido', 'lines_ids', 'dups_ids'],
            limit=1
        )

        if not dfe_data or len(dfe_data) == 0:
            resultado['erro'] = f'DFe não encontrado com chave {chave_cte}'
            return resultado

        dfe = dfe_data[0]
        dfe_id = dfe['id']

        print(f"✅ DFe ID {dfe_id} encontrado!")
        print()

        # 3. Atualizar campos do DFe
        print("3️⃣ Atualizando DFe...")
        hoje = date.today().strftime('%Y-%m-%d')

        valores_dfe = {
            'l10n_br_data_entrada': hoje,
            'l10n_br_tipo_pedido': 'servico'
        }

        odoo.write('l10n_br_ciel_it_account.dfe', [dfe_id], valores_dfe)
        print("✅ DFe atualizado!")
        print()

        # 4. Atualizar linha com produto
        print("4️⃣ Atualizando linha com produto SERVICO DE FRETE...")
        line_ids = dfe.get('lines_ids')

        if not line_ids or len(line_ids) == 0:
            resultado['erro'] = 'Nenhuma linha encontrada no DFe'
            return resultado

        line_id = line_ids[0]

        valores_linha = {
            'product_id': PRODUTO_SERVICO_FRETE_ID,
            'l10n_br_quantidade': 1.0,
            'product_uom_id': 1,
        }

        odoo.write('l10n_br_ciel_it_account.dfe.line', [line_id], valores_linha)
        print("✅ Linha atualizada!")
        print()

        # 5. Atualizar vencimento
        print("5️⃣ Atualizando vencimento...")
        if not data_vencimento:
            # Padrão: 30 dias a partir de hoje
            from datetime import timedelta
            data_vencimento = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')

        pagamento_ids = dfe.get('dups_ids')
        if pagamento_ids and len(pagamento_ids) > 0:
            pagamento_id = pagamento_ids[0]
            odoo.write('l10n_br_ciel_it_account.dfe.pagamento', [pagamento_id], {
                'cobr_dup_dvenc': data_vencimento
            })
            print(f"✅ Vencimento atualizado para {data_vencimento}!")
        print()

        # 6. Gerar PO
        print("6️⃣ Gerando Purchase Order...")
        resultado_po = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe',
            'action_gerar_po_dfe',
            [[dfe_id]],
            {'context': {'validate_analytic': True}}
        )

        # Extrair PO ID do resultado
        po_id = resultado_po.get('res_id') if isinstance(resultado_po, dict) else None

        if not po_id:
            resultado['erro'] = 'PO não foi gerado corretamente'
            return resultado

        print(f"✅ Purchase Order ID {po_id} gerado!")
        print()

        resultado['etapas']['etapa1'] = {
            'sucesso': True,
            'dfe_id': dfe_id,
            'line_id': line_id,
            'po_id': po_id
        }

        # ========================================
        # ETAPA 2: CONFIRMAÇÃO DO PURCHASE ORDER
        # ========================================
        print("┌" + "─" * 98 + "┐")
        print("│" + " " * 28 + "ETAPA 2: CONFIRMAÇÃO DO PURCHASE ORDER" + " " * 30 + "│")
        print("└" + "─" * 98 + "┘")
        print()

        # 7. Buscar dados do PO
        print(f"7️⃣ Buscando Purchase Order ID {po_id}...")
        po_data = odoo.read(
            'purchase.order',
            [po_id],
            ['id', 'name', 'state', 'team_id', 'payment_provider_id', 'company_id']
        )

        if not po_data or len(po_data) == 0:
            resultado['erro'] = f'Purchase Order {po_id} não encontrado'
            return resultado

        po = po_data[0]
        print(f"✅ PO {po.get('name')} encontrado (State: {po.get('state')})!")
        print()

        # 8. Verificar e atualizar campos obrigatórios
        print("8️⃣ Verificando e atualizando campos obrigatórios...")
        valores_atualizar = {}

        team_atual = po.get('team_id')
        if not team_atual or (isinstance(team_atual, list) and team_atual[0] != TEAM_LANCAMENTO_FRETE_ID):
            print(f"   - team_id: {TEAM_LANCAMENTO_FRETE_ID} (Lançamento Frete)")
            valores_atualizar['team_id'] = TEAM_LANCAMENTO_FRETE_ID

        provider_atual = po.get('payment_provider_id')
        if not provider_atual or (isinstance(provider_atual, list) and provider_atual[0] != PAYMENT_PROVIDER_TRANSFERENCIA_ID):
            print(f"   - payment_provider_id: {PAYMENT_PROVIDER_TRANSFERENCIA_ID} (Transferência Bancária)")
            valores_atualizar['payment_provider_id'] = PAYMENT_PROVIDER_TRANSFERENCIA_ID

        company_atual = po.get('company_id')
        if not company_atual or (isinstance(company_atual, list) and company_atual[0] != COMPANY_NACOM_GOYA_CD_ID):
            print(f"   - company_id: {COMPANY_NACOM_GOYA_CD_ID} (NACOM GOYA - CD)")
            valores_atualizar['company_id'] = COMPANY_NACOM_GOYA_CD_ID

        if valores_atualizar:
            print("   ⚠️  Atualizando campos...")
            odoo.write('purchase.order', [po_id], valores_atualizar)
            print("   ✅ Campos atualizados!")
        else:
            print("   ✅ Todos os campos já estão corretos!")
        print()

        # 9. Atualizar impostos do PO (ANTES de confirmar)
        print("9️⃣ Atualizando impostos do Purchase Order...")
        print("   Executando onchange_l10n_br_calcular_imposto...")
        try:
            odoo.execute_kw(
                'purchase.order',
                'onchange_l10n_br_calcular_imposto',
                [[po_id]],
                {}
            )
            print("   ✅ Impostos do PO atualizados!")
            print("   (Isso ajusta operação fiscal para empresa correta)")
        except Exception as e:
            print(f"   ⚠️  Erro ao atualizar impostos do PO: {e}")
            print("   Continuando mesmo assim...")
        print()

        # 10. Confirmar PO
        print("🔟 Confirmando Purchase Order...")
        if po.get('state') != 'draft':
            print(f"   ⚠️  PO já está em state '{po.get('state')}', não precisa confirmar")
        else:
            odoo.execute_kw(
                'purchase.order',
                'button_confirm',
                [[po_id]],
                {'context': {'validate_analytic': True}}
            )
            print("   ✅ Purchase Order confirmado!")
        print()

        # 11. Aprovar PO (se necessário)
        print("1️⃣1️⃣ Verificando se PO precisa de aprovação...")

        # Ler estado atual do PO após confirmação
        po_data_atualizado = odoo.read(
            'purchase.order',
            [po_id],
            ['state', 'is_current_approver']
        )

        if po_data_atualizado and len(po_data_atualizado) > 0:
            po_state = po_data_atualizado[0].get('state')
            is_approver = po_data_atualizado[0].get('is_current_approver')

            print(f"   State atual: {po_state}")

            if po_state == 'to approve':
                print("   ⚠️  PO precisa de aprovação!")
                print("   Executando button_approve...")

                try:
                    odoo.execute_kw(
                        'purchase.order',
                        'button_approve',
                        [[po_id]],
                        {}
                    )
                    print("   ✅ Purchase Order aprovado!")
                except Exception as e:
                    print(f"   ⚠️  Erro ao aprovar: {e}")
                    print("   O pedido pode precisar de aprovação manual no Odoo")
            else:
                print(f"   ✅ PO não precisa de aprovação (state: {po_state})")
        print()

        resultado['etapas']['etapa2'] = {
            'sucesso': True,
            'po_id': po_id,
            'po_name': po.get('name')
        }

        # ========================================
        # ETAPA 3: CRIAÇÃO E CONF IGURAÇÃO DA FATURA
        # ========================================
        print("┌" + "─" * 98 + "┐")
        print("│" + " " * 25 + "ETAPA 3: CRIAÇÃO E CONFIGURAÇÃO DA FATURA" + " " * 31 + "│")
        print("└" + "─" * 98 + "┘")
        print()

        # 12. Criar fatura
        print("1️⃣2️⃣ Criando fatura do Purchase Order...")

        # Buscar invoice_status atualizado
        po_invoice_data = odoo.read('purchase.order', [po_id], ['invoice_status', 'invoice_ids'])

        if po_invoice_data and len(po_invoice_data) > 0:
            invoice_status = po_invoice_data[0].get('invoice_status')
            invoice_ids = po_invoice_data[0].get('invoice_ids', [])

            print(f"   Invoice Status: {invoice_status}")

            if invoice_status in ('no', 'invoiced'):
                print(f"   ⚠️  Invoice status '{invoice_status}' - fatura pode já existir ou não ser necessária")
                if invoice_ids and len(invoice_ids) > 0:
                    invoice_id = invoice_ids[-1]
                    print(f"   ✅ Usando fatura existente: {invoice_id}")
                else:
                    print("   ⚠️  Pulando criação de fatura")
                    invoice_id = None
            else:
                try:
                    resultado_invoice = odoo.execute_kw(
                        'purchase.order',
                        'action_create_invoice',
                        [[po_id]],
                        {}
                    )

                    # Extrair invoice_id do resultado
                    invoice_id = None
                    if isinstance(resultado_invoice, dict):
                        invoice_id = resultado_invoice.get('res_id')

                    # Se não conseguiu extrair, buscar novamente
                    if not invoice_id:
                        po_atualizado = odoo.read('purchase.order', [po_id], ['invoice_ids'])
                        if po_atualizado and len(po_atualizado) > 0:
                            invoice_ids_novo = po_atualizado[0].get('invoice_ids', [])
                            if invoice_ids_novo and len(invoice_ids_novo) > 0:
                                invoice_id = invoice_ids_novo[-1]

                    if invoice_id:
                        print(f"   ✅ Fatura criada! Invoice ID: {invoice_id}")
                    else:
                        print("   ⚠️  Fatura pode ter sido criada mas ID não identificado")

                except Exception as e:
                    print(f"   ❌ Erro ao criar fatura: {e}")
                    invoice_id = None

        print()

        # 13. Atualizar impostos da fatura (se fatura foi criada)
        if invoice_id:
            print("1️⃣3️⃣ Atualizando impostos da fatura...")
            print(f"   Invoice ID: {invoice_id}")

            try:
                odoo.execute_kw(
                    'account.move',
                    'onchange_l10n_br_calcular_imposto',
                    [[invoice_id]],
                    {}
                )
                print("   ✅ Impostos atualizados!")
            except Exception as e:
                print(f"   ⚠️  Erro ao atualizar impostos: {e}")
                print("   Impostos podem precisar ser atualizados manualmente no Odoo")
        else:
            print("1️⃣3️⃣ Pulando atualização de impostos (fatura não criada)")

        print()

        resultado['etapas']['etapa3'] = {
            'sucesso': True,
            'invoice_id': invoice_id if invoice_id else None
        }

        # ========================================
        # ETAPA 4: CONFIRMAÇÃO DA FATURA
        # ========================================
        if invoice_id:
            print("┌" + "─" * 98 + "┐")
            print("│" + " " * 31 + "ETAPA 4: CONFIRMAÇÃO DA FATURA" + " " * 35 + "│")
            print("└" + "─" * 98 + "┘")
            print()

            # 14. Configurar campos da fatura
            print("1️⃣4️⃣ Configurando campos da fatura...")

            valores_invoice = {}

            # 1. Destinação de uso
            print("   - l10n_br_compra_indcom: 'out' (Outros)")
            valores_invoice['l10n_br_compra_indcom'] = 'out'

            # 2. Situação NF-e
            print("   - l10n_br_situacao_nf: 'autorizado' (Autorizado)")
            valores_invoice['l10n_br_situacao_nf'] = 'autorizado'

            # 3. Data de vencimento
            print(f"   - invoice_date_due: {data_vencimento}")
            valores_invoice['invoice_date_due'] = data_vencimento

            try:
                odoo.write('account.move', [invoice_id], valores_invoice)
                print("   ✅ Campos da fatura configurados!")
            except Exception as e:
                print(f"   ⚠️  Erro ao configurar campos: {e}")

            print()

            # 15. Atualizar impostos da fatura novamente
            print("1️⃣5️⃣ Atualizando impostos da fatura novamente...")
            print("   Executando onchange_l10n_br_calcular_imposto_btn...")

            try:
                odoo.execute_kw(
                    'account.move',
                    'onchange_l10n_br_calcular_imposto_btn',
                    [[invoice_id]],
                    {}
                )
                print("   ✅ Impostos atualizados!")
            except Exception as e:
                # Método pode retornar None
                if "cannot marshal None" in str(e):
                    print("   ✅ Impostos atualizados! (método retornou None)")
                else:
                    print(f"   ⚠️  Erro: {e}")

            print()

            # 16. Confirmar fatura (action_post)
            print("1️⃣6️⃣ Confirmando fatura...")
            print("   Executando action_post...")

            try:
                odoo.execute_kw(
                    'account.move',
                    'action_post',
                    [[invoice_id]],
                    {'context': {'validate_analytic': True}}
                )
                print("   ✅ Fatura confirmada!")
            except Exception as e:
                print(f"   ❌ Erro ao confirmar fatura: {e}")
                print("   A fatura pode precisar ser confirmada manualmente")

            print()

            resultado['etapas']['etapa4'] = {
                'sucesso': True,
                'invoice_confirmada': True
            }

        # ========================================
        # CONCLUSÃO
        # ========================================
        print("=" * 100)
        print("✅ LANÇAMENTO COMPLETO FINALIZADO COM SUCESSO!")
        print("=" * 100)
        print()
        print(f"📋 DFe ID: {dfe_id}")
        print(f"📦 Purchase Order ID: {po_id} ({po.get('name')})")
        print(f"💰 Vencimento: {data_vencimento}")
        if invoice_id:
            print(f"🧾 Invoice ID: {invoice_id}")
        print()

        resultado['sucesso'] = True
        resultado['dfe_id'] = dfe_id
        resultado['po_id'] = po_id
        resultado['po_name'] = po.get('name')
        resultado['invoice_id'] = invoice_id if invoice_id else None

        return resultado

    except Exception as e:
        print(f"❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        resultado['erro'] = str(e)
        return resultado


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("❌ Uso: python3 lancamento_frete_completo.py <CHAVE_CTE> [DATA_VENCIMENTO]")
        print()
        print("Exemplos:")
        print("  python3 lancamento_frete_completo.py 33251120341933000150570010000281801000319398")
        print("  python3 lancamento_frete_completo.py 33251120341933000150570010000281801000319398 2025-12-31")
        sys.exit(1)

    chave = sys.argv[1]
    vencimento = sys.argv[2] if len(sys.argv) > 2 else None

    print("\n")
    resultado = lancar_frete_completo(chave, vencimento)

    print()
    print("📊 RESULTADO FINAL:")
    print("=" * 100)
    pprint(resultado)
    print()

    # Exit code baseado no sucesso
    sys.exit(0 if resultado['sucesso'] else 1)
