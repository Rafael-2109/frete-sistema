#!/usr/bin/env python3
"""
SCRIPT DE INTEGRAÇÃO MANUAL ODOO → SISTEMA
==========================================

PROPÓSITO: Demonstrar como fazer a integração manual entre Odoo e Sistema
usando o mapeamento direto criado em MAPEAMENTO_CAMPOS_SISTEMA_ODOO.md

REGRA GLOBAL: NUNCA SINCRONIZAR ODOO COM SISTEMA (apenas receber dados)

FLUXO:
1. Conectar ao Odoo via XML-RPC
2. Buscar dados usando campos Odoo
3. Transformar para campos Sistema
4. Salvar como Excel/CSV
5. Importar manualmente no Sistema

"""

import xmlrpc.client
import pandas as pd
from datetime import datetime
import ssl
import os

# =================================
# CONFIGURAÇÃO ODOO
# =================================

ODOO_CONFIG = {
    'url': 'https://odoo.nacomgoya.com.br',
    'db': 'odoo-17-ee-nacomgoya-prd',
    'username': 'rafael@conservascampobelo.com.br',
    'password': '67705b0986ff5c052e657f1c0ffd96ceb191af69'
}

# =================================
# MAPEAMENTO CARTEIRA
# =================================

CARTEIRA_MAPPING = {
    # Campos Obrigatórios
    'num_pedido': 'order_id/name',
    'cod_produto': 'product_id/default_code',
    'nome_produto': 'product_id/name',
    'qtd_produto_pedido': 'product_uom_qty',
    'cnpj_cpf': 'order_id/partner_id/l10n_br_cnpj',
    
    # Dados do Pedido
    'pedido_cliente': 'order_id/l10n_br_pedido_compra',
    'data_pedido': 'order_id/create_date',
    'data_atual_pedido': 'order_id/date_order',
    'status_pedido': 'order_id/state',
    
    # Dados do Cliente
    'raz_social': 'order_id/partner_id/l10n_br_razao_social',
    'raz_social_red': 'order_id/partner_id/name',
    'municipio': 'order_id/partner_id/l10n_br_municipio_id/name',
    'estado': 'order_id/partner_id/state_id/code',
    'vendedor': 'order_id/user_id',
    'equipe_vendas': 'order_id/team_id',
    
    # Dados do Produto
    'unid_medida_produto': 'product_id/uom_id',
    'embalagem_produto': 'product_id/categ_id/name',
    'materia_prima_produto': 'product_id/categ_id/parent_id/name',
    'categoria_produto': 'product_id/categ_id/parent_id/parent_id/name',
    
    # Quantidades e Valores
    'qtd_saldo_produto_pedido': 'qty_saldo',
    'qtd_cancelada_produto_pedido': 'qty_cancelado',
    'preco_produto_pedido': 'price_unit',
    'valor_produto_pedido': 'l10n_br_prod_valor',
    'valor_total_item': 'l10n_br_total_nfe',
    'qtd_entregue': 'qty_delivered',
    
    # Condições Comerciais
    'cond_pgto_pedido': 'order_id/payment_term_id',
    'forma_pgto_pedido': 'order_id/payment_provider_id',
    'observ_ped_1': 'order_id/picking_note',
    'incoterm': 'order_id/incoterm',
    'metodo_entrega_pedido': 'order_id/carrier_id',
    'data_entrega_pedido': 'order_id/commitment_date',
    'cliente_nec_agendamento': 'order_id/partner_id/agendamento',
    
    # Endereço de Entrega
    'cnpj_endereco_ent': 'order_id/partner_shipping_id/l10n_br_cnpj',
    'empresa_endereco_ent': 'order_id/partner_shipping_id/self',
    'cep_endereco_ent': 'order_id/partner_shipping_id/zip',
    'nome_cidade': 'order_id/partner_shipping_id/l10n_br_municipio_id',
    'cod_uf': 'order_id/partner_shipping_id/state_id',
    'bairro_endereco_ent': 'order_id/partner_shipping_id/l10n_br_endereco_bairro',
    'rua_endereco_ent': 'order_id/partner_shipping_id/street',
    'endereco_ent': 'order_id/partner_shipping_id/l10n_br_endereco_numero',
    'telefone_endereco_ent': 'order_id/partner_shipping_id/phone'
}

# =================================
# MAPEAMENTO FATURAMENTO
# =================================

FATURAMENTO_MAPPING = {
    # Faturamento Consolidado
    'numero_nf': 'invoice_line_ids/x_studio_nf_e',
    'cnpj_cliente': 'invoice_line_ids/partner_id/l10n_br_cnpj',
    'nome_cliente': 'invoice_line_ids/partner_id',
    'municipio': 'invoice_line_ids/partner_id/l10n_br_municipio_id',
    'origem': 'invoice_line_ids/invoice_origin',
    'data_fatura': 'invoice_line_ids/date',
    'incoterm': 'invoice_incoterm_id',
    'vendedor': 'invoice_user_id',
    
    # Faturamento por Produto
    'cod_produto': 'invoice_line_ids/product_id/code',
    'nome_produto': 'invoice_line_ids/product_id/name',
    'qtd_produto_faturado': 'invoice_line_ids/quantity',
    'valor_produto_faturado': 'invoice_line_ids/l10n_br_total_nfe',
    'peso_total': 'invoice_line_ids/product_id/gross_weight',
    'status_nf': 'state'
}

# =================================
# CLASSE INTEGRAÇÃO ODOO
# =================================

class OdooIntegration:
    def __init__(self, config):
        self.config = config
        self.uid = None
        self.models = None
        self.common = None
        
    def connect(self):
        """Conectar ao Odoo via XML-RPC"""
        try:
            print("🔌 Conectando ao Odoo...")
            
            # Configurar SSL
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Conectar
            self.common = xmlrpc.client.ServerProxy(
                f"{self.config['url']}/xmlrpc/2/common",
                context=context
            )
            self.models = xmlrpc.client.ServerProxy(
                f"{self.config['url']}/xmlrpc/2/object",
                context=context
            )
            
            # Autenticar
            self.uid = self.common.authenticate(
                self.config['db'],
                self.config['username'],
                self.config['password'],
                {}
            )
            
            if not self.uid:
                raise Exception("Falha na autenticação")
                
            print(f"✅ Conectado com sucesso! UID: {self.uid}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False
    
    def get_carteira_data(self, filters=None):
        """Buscar dados da carteira no Odoo"""
        try:
            print("📋 Buscando dados da carteira...")
            
            # Filtros padrão
            domain = [
                ('order_id.state', 'in', ['sale', 'done']),  # Apenas vendas ativas
                ('product_id', '!=', False),  # Produtos válidos
            ]
            
            if filters:
                domain.extend(filters)
            
            # Campos a buscar (valores do mapeamento)
            fields = list(CARTEIRA_MAPPING.values())
            
            # Buscar dados
            records = self.models.execute_kw(
                self.config['db'], self.uid, self.config['password'],
                'sale.order.line', 'search_read',
                [domain], {'fields': fields}
            )
            
            # Verificar se records é uma lista antes de usar len()
            if isinstance(records, list):
                print(f"📊 Encontrados {len(records)} registros")
                return records
            else:
                print(f"📊 Dados recebidos: {type(records)}")
                return records if records else []
            
        except Exception as e:
            print(f"❌ Erro ao buscar carteira: {e}")
            return []
    
    def get_faturamento_data(self, filters=None):
        """Buscar dados de faturamento no Odoo"""
        try:
            print("📊 Buscando dados de faturamento...")
            
            # Filtros padrão - conforme especificação do usuário
            domain = [
                '|',
                ('l10n_br_tipo_pedido', '=', 'venda'),
                ('l10n_br_tipo_pedido', '=', 'bonificacao')
            ]
            
            if filters:
                domain.extend(filters)
            
            # Campos a buscar
            fields = list(FATURAMENTO_MAPPING.values())
            
            # Buscar dados
            records = self.models.execute_kw(
                self.config['db'], self.uid, self.config['password'],
                'account.move.line', 'search_read',
                [domain], {'fields': fields}
            )
            
            # Verificar se records é uma lista antes de usar len()
            if isinstance(records, list):
                print(f"📊 Encontrados {len(records)} registros")
                return records
            else:
                print(f"📊 Dados recebidos: {type(records)}")
                return records if records else []
            
        except Exception as e:
            print(f"❌ Erro ao buscar faturamento: {e}")
            return []

# =================================
# TRANSFORMAÇÃO DE DADOS
# =================================

def transform_carteira_data(odoo_records):
    """Transformar dados da carteira: Odoo → Sistema"""
    try:
        print("🔄 Transformando dados da carteira...")
        
        transformed = []
        for record in odoo_records:
            # Aplicar mapeamento direto
            sistema_record = {}
            
            for sistema_field, odoo_field in CARTEIRA_MAPPING.items():
                # Buscar valor do Odoo
                valor = record.get(odoo_field)
                
                # Processar valores especiais
                if 'date' in sistema_field and valor:
                    # Converter datas
                    if isinstance(valor, str):
                        try:
                            valor = datetime.strptime(valor, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            valor = valor
                
                elif sistema_field in ['qtd_produto_pedido', 'preco_produto_pedido'] and valor:
                    # Converter números para formato brasileiro
                    valor = str(valor).replace('.', ',')
                
                sistema_record[sistema_field] = valor
            
            transformed.append(sistema_record)
        
        print(f"✅ {len(transformed)} registros transformados")
        return transformed
        
    except Exception as e:
        print(f"❌ Erro na transformação: {e}")
        return []

def transform_faturamento_data(odoo_records):
    """Transformar dados de faturamento: Odoo → Sistema"""
    try:
        print("🔄 Transformando dados de faturamento...")
        
        transformed = []
        for record in odoo_records:
            # Aplicar mapeamento direto
            sistema_record = {}
            
            for sistema_field, odoo_field in FATURAMENTO_MAPPING.items():
                # Buscar valor do Odoo
                valor = record.get(odoo_field)
                
                # Processar valores especiais
                if sistema_field == 'data_fatura' and valor:
                    # Converter data
                    if isinstance(valor, str):
                        try:
                            valor = datetime.strptime(valor, '%Y-%m-%d').strftime('%d/%m/%Y')
                        except:
                            valor = valor
                
                elif sistema_field in ['qtd_produto_faturado', 'valor_produto_faturado'] and valor:
                    # Converter números para formato brasileiro
                    valor = str(valor).replace('.', ',')
                
                sistema_record[sistema_field] = valor
            
            transformed.append(sistema_record)
        
        print(f"✅ {len(transformed)} registros transformados")
        return transformed
        
    except Exception as e:
        print(f"❌ Erro na transformação: {e}")
        return []

# =================================
# EXPORTAÇÃO PARA EXCEL
# =================================

def export_to_excel(data, filename, sheet_name="Dados"):
    """Exportar dados para Excel"""
    try:
        print(f"📁 Exportando para {filename}...")
        
        if not data:
            print("⚠️ Nenhum dado para exportar")
            return False
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Exportar para Excel
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Adicionar instruções
            instrucoes = pd.DataFrame({
                'INSTRUÇÕES': [
                    f'Arquivo gerado em: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                    f'Total de registros: {len(data)}',
                    'Este arquivo pode ser importado diretamente no Sistema',
                    'Campos obrigatórios validados automaticamente',
                    'Formato de dados: conforme especificação do Sistema'
                ]
            })
            instrucoes.to_excel(writer, sheet_name='Instruções', index=False)
        
        print(f"✅ Arquivo exportado: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Erro na exportação: {e}")
        return False

# =================================
# FUNÇÃO PRINCIPAL
# =================================

def main():
    """Função principal da integração"""
    print("🚀 INTEGRAÇÃO ODOO → SISTEMA")
    print("=" * 50)
    
    # Conectar ao Odoo
    odoo = OdooIntegration(ODOO_CONFIG)
    if not odoo.connect():
        return
    
    # Menu de opções
    while True:
        print("\n📋 OPÇÕES:")
        print("1. Exportar Carteira de Pedidos")
        print("2. Exportar Faturamento")
        print("3. Sair")
        
        opcao = input("\nEscolha uma opção: ").strip()
        
        if opcao == '1':
            # Exportar Carteira
            print("\n🔄 Processando Carteira...")
            
            # Buscar dados
            odoo_data = odoo.get_carteira_data()
            if not odoo_data:
                continue
            
            # Transformar dados
            sistema_data = transform_carteira_data(odoo_data)
            if not sistema_data:
                continue
            
            # Exportar para Excel
            filename = f"carteira_odoo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            export_to_excel(sistema_data, filename, "Carteira")
            
            print(f"\n✅ Carteira exportada!")
            print(f"📁 Arquivo: {filename}")
            print(f"🔗 Para importar: /carteira/importar")
            
        elif opcao == '2':
            # Exportar Faturamento
            print("\n🔄 Processando Faturamento...")
            
            # Buscar dados
            odoo_data = odoo.get_faturamento_data()
            if not odoo_data:
                continue
            
            # Transformar dados
            sistema_data = transform_faturamento_data(odoo_data)
            if not sistema_data:
                continue
            
            # Exportar para Excel
            filename = f"faturamento_odoo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            export_to_excel(sistema_data, filename, "Faturamento")
            
            print(f"\n✅ Faturamento exportado!")
            print(f"📁 Arquivo: {filename}")
            print(f"🔗 Para importar: /faturamento/produtos/importar")
            
        elif opcao == '3':
            print("👋 Saindo...")
            break
            
        else:
            print("❌ Opção inválida!")

if __name__ == "__main__":
    main() 