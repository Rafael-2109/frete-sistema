"""
Mapeador de campos entre Manufatura e Odoo
Seguindo o padrão de FaturamentoMapper e CarteiraMapper
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class ManufaturaMapper:
    def __init__(self):
        self.mapeamento_requisicao = {}
        self.mapeamento_pedido_compra = {}
        self.mapeamento_ordem_producao = {}
        self.mapeamento_historico = {}
        self.campos_multiplas_queries = {}
        self._carregar_mapeamentos()
        self._definir_campos_multiplas_queries()
    
    def _carregar_mapeamentos(self):
        """Define mapeamentos hardcoded para módulo Manufatura"""
        
        # 📋 MAPEAMENTO REQUISIÇÃO DE COMPRAS
        # RequisicaoCompras -> Campo Odoo (purchase.requisition)
        self.mapeamento_requisicao = {
            'num_requisicao': 'name',
            'data_requisicao_criacao': 'create_date',
            'usuario_requisicao_criacao': 'user_id/name',
            'lead_time_requisicao': 'lead_time',
            'lead_time_previsto': 'schedule_date',
            'data_requisicao_solicitada': 'ordering_date',
            'cod_produto': 'product_id/default_code',
            'nome_produto': 'product_id/name',
            'qtd_produto_requisicao': 'product_qty',
            'necessidade': 'state',  # confirmed = True, else False
            'data_necessidade': 'schedule_date',
            'status': 'state',  # draft/confirmed/done/cancel
            'odoo_id': 'id',
        }
        
        # 📦 MAPEAMENTO PEDIDO DE COMPRAS
        # PedidoCompras -> Campo Odoo (purchase.order + purchase.order.line)
        self.mapeamento_pedido_compra = {
            # Dados do pedido (purchase.order)
            'num_pedido': 'name',
            'cnpj_fornecedor': 'partner_id/l10n_br_cnpj',
            'raz_social': 'partner_id/name',
            'numero_nf': 'invoice_ids/name',  # Relação com faturas
            'data_pedido_criacao': 'create_date',
            'usuario_pedido_criacao': 'user_id/name',
            'lead_time_pedido': 'days_to_purchase',
            'lead_time_previsto': 'date_planned',
            'data_pedido_previsao': 'date_planned',
            'data_pedido_entrega': 'date_approve',
            'confirmacao_pedido': 'state',  # purchase = True
            'confirmado_por': 'user_id/name',
            'confirmado_em': 'date_approve',
            'odoo_id': 'id',
            
            # Dados das linhas (purchase.order.line)
            'cod_produto': 'product_id/default_code',
            'nome_produto': 'product_id/name',
            'qtd_produto_pedido': 'product_qty',
            'preco_produto_pedido': 'price_unit',
            'icms_produto_pedido': 'price_tax',  # Calculado
            'pis_produto_pedido': 'taxes_id',  # Relação com impostos
            'cofins_produto_pedido': 'taxes_id',  # Relação com impostos
        }
        
        # 🏭 MAPEAMENTO ORDEM DE PRODUÇÃO
        # OrdemProducao -> Campo Odoo (mrp.production)
        self.mapeamento_ordem_producao = {
            'numero_ordem': 'name',
            'origem_ordem': 'origin',
            'status': 'state',  # draft/confirmed/progress/done/cancel
            'cod_produto': 'product_id/default_code',
            'nome_produto': 'product_id/name',
            'qtd_planejada': 'product_qty',
            'qtd_produzida': 'qty_produced',
            'data_inicio_prevista': 'date_planned_start',
            'data_fim_prevista': 'date_planned_finished',
            'data_inicio_real': 'date_start',
            'data_fim_real': 'date_finished',
            'linha_producao': 'workcenter_id/name',
            'turno': 'shift',  # Campo customizado
            'lote_producao': 'lot_producing_id/name',
            'custo_previsto': 'planned_cost',  # Campo calculado
            'custo_real': 'total_cost',  # Campo calculado
            'odoo_id': 'id',
        }
        
        # 📊 MAPEAMENTO HISTÓRICO DE PEDIDOS
        # HistoricoPedidos -> Campo Odoo (sale.order + sale.order.line)
        self.mapeamento_historico = {
            'num_pedido': 'order_id/name',
            'data_pedido': 'order_id/date_order',
            'cnpj_cliente': 'order_id/partner_id/l10n_br_cnpj',
            'raz_social_red': 'order_id/partner_id/name',
            'nome_grupo': 'order_id/partner_id/parent_id/name',  # Grupo empresarial
            'vendedor': 'order_id/user_id/name',
            'equipe_vendas': 'order_id/team_id/name',
            'incoterm': 'order_id/incoterm/name',
            'nome_cidade': 'order_id/partner_id/l10n_br_municipio_id/name',
            'cod_uf': 'order_id/partner_id/state_id/code',
            'cod_produto': 'product_id/default_code',
            'nome_produto': 'product_id/name',
            'qtd_produto_pedido': 'product_uom_qty',
            'preco_produto_pedido': 'price_unit',
            'valor_produto_pedido': 'price_total',
            'icms_produto_pedido': 'price_tax',
            'pis_produto_pedido': 'tax_id',  # Relação com impostos
            'cofins_produto_pedido': 'tax_id',  # Relação com impostos
        }
        
        logger.info(f"Mapeamentos Manufatura carregados:")
        logger.info(f"  - Requisição: {len(self.mapeamento_requisicao)} campos")
        logger.info(f"  - Pedido Compra: {len(self.mapeamento_pedido_compra)} campos")
        logger.info(f"  - Ordem Produção: {len(self.mapeamento_ordem_producao)} campos")
        logger.info(f"  - Histórico: {len(self.mapeamento_historico)} campos")
    
    def _definir_campos_multiplas_queries(self):
        """Define campos que precisam de múltiplas queries para manufatura"""
        
        multiplas_queries = {}
        
        # Processar todos os mapeamentos
        todos_mapeamentos = {
            'requisicao': self.mapeamento_requisicao,
            'pedido_compra': self.mapeamento_pedido_compra,
            'ordem_producao': self.mapeamento_ordem_producao,
            'historico': self.mapeamento_historico
        }
        
        for tipo, mapeamento in todos_mapeamentos.items():
            for campo_local, campo_odoo in mapeamento.items():
                partes = campo_odoo.split('/')
                
                # Campos que precisam de múltiplas queries
                if (len(partes) >= 2 or 
                    'partner_id' in campo_odoo or 
                    'product_id' in campo_odoo or
                    'user_id' in campo_odoo or
                    'workcenter_id' in campo_odoo or
                    'invoice_ids' in campo_odoo or
                    'taxes_id' in campo_odoo or
                    'municipio_id' in campo_odoo):
                    
                    multiplas_queries[f"{tipo}.{campo_odoo}"] = self._gerar_queries_para_campo(tipo, campo_odoo)
        
        self.campos_multiplas_queries = multiplas_queries
        logger.info(f"Campos manufatura múltiplas queries identificados: {len(multiplas_queries)}")
    
    def _gerar_queries_para_campo(self, tipo: str, campo_odoo: str) -> Dict[str, List]:
        """Gera queries necessárias para um campo de manufatura"""
        partes = campo_odoo.split('/')
        
        if len(partes) == 1:
            # Campo direto - não precisa de múltiplas queries
            return {"queries": []}
        
        # Definir modelo base conforme tipo
        modelo_base = {
            'requisicao': 'purchase.requisition',
            'pedido_compra': 'purchase.order',
            'ordem_producao': 'mrp.production',
            'historico': 'sale.order.line'
        }.get(tipo, '')
        
        queries = [(modelo_base, partes[0])]
        
        # Mapear relações
        for i in range(1, len(partes)):
            campo_anterior = partes[i-1]
            
            if campo_anterior == 'partner_id':
                queries.append(("res.partner", partes[i]))
            elif campo_anterior == 'product_id':
                queries.append(("product.product", partes[i]))
            elif campo_anterior == 'user_id':
                queries.append(("res.users", partes[i]))
            elif campo_anterior == 'order_id':
                if tipo == 'historico':
                    queries.append(("sale.order", partes[i]))
                else:
                    queries.append(("purchase.order", partes[i]))
            elif campo_anterior == 'workcenter_id':
                queries.append(("mrp.workcenter", partes[i]))
            elif campo_anterior == 'lot_producing_id':
                queries.append(("stock.production.lot", partes[i]))
            elif campo_anterior == 'invoice_ids':
                queries.append(("account.move", partes[i]))
            elif campo_anterior == 'taxes_id' or campo_anterior == 'tax_id':
                queries.append(("account.tax", partes[i]))
            elif campo_anterior == 'l10n_br_municipio_id':
                queries.append(("l10n_br.city", partes[i]))
            elif campo_anterior == 'state_id':
                queries.append(("res.country.state", partes[i]))
            elif campo_anterior == 'team_id':
                queries.append(("crm.team", partes[i]))
            elif campo_anterior == 'incoterm':
                queries.append(("account.incoterms", partes[i]))
            elif campo_anterior == 'parent_id':
                queries.append(("res.partner", partes[i]))  # Grupo empresarial
        
        return {"queries": queries}
    
    def get_campos_odoo(self, tipo: str) -> List[str]:
        """Retorna lista de campos do Odoo para um tipo específico"""
        
        mapeamento = {
            'requisicao': self.mapeamento_requisicao,
            'pedido_compra': self.mapeamento_pedido_compra,
            'ordem_producao': self.mapeamento_ordem_producao,
            'historico': self.mapeamento_historico
        }.get(tipo, {})
        
        campos = set()
        for campo_odoo in mapeamento.values():
            # Adicionar apenas o campo raiz (antes da primeira /)
            campo_raiz = campo_odoo.split('/')[0]
            campos.add(campo_raiz)
        
        return list(campos)
    
    def processar_campo_com_multiplas_queries(self, tipo: str, campo_odoo: str, dados_relacionados: Dict) -> Any:
        """
        Processa um campo que requer múltiplas queries
        
        Args:
            tipo: Tipo do mapeamento (requisicao, pedido_compra, etc)
            campo_odoo: Campo no formato "model_id/field/subfield"
            dados_relacionados: Dicionário com dados já buscados
        
        Returns:
            Valor final do campo processado
        """
        chave = f"{tipo}.{campo_odoo}"
        
        if chave not in self.campos_multiplas_queries:
            # Campo simples, retornar direto
            return dados_relacionados.get(campo_odoo.split('/')[0])
        
        # Processar campo complexo
        partes = campo_odoo.split('/')
        valor_atual = dados_relacionados
        
        for parte in partes:
            if isinstance(valor_atual, dict):
                valor_atual = valor_atual.get(parte)
            elif isinstance(valor_atual, (list, tuple)) and len(valor_atual) > 1:
                # Para campos do tipo [id, name], pegar o name
                valor_atual = valor_atual[1]
            else:
                break
        
        return valor_atual