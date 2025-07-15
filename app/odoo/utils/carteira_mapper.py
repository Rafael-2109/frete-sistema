"""
Mapeador de campos entre CarteiraPrincipal e Odoo
Usando mapeamento hardcoded diretamente no código
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class CarteiraMapper:
    def __init__(self):
        self.mapeamento_carteira = {}
        self.campos_multiplas_queries = {}
        self._carregar_mapeamento_carteira()
        self._definir_campos_multiplas_queries()
    
    def _carregar_mapeamento_carteira(self):
        """Define EXATAMENTE o mapeamento fornecido pelo usuário - hardcoded no código"""
        
        # Mapeamento completo baseado no CSV do usuário
        # CarteiraPrincipal -> Campo Odoo
        self.mapeamento_carteira = {
            # 🆔 CHAVES PRIMÁRIAS DE NEGÓCIO
            'num_pedido': 'order_id/name',
            'cod_produto': 'product_id/default_code',
            
            # 📋 DADOS DO PEDIDO
            'pedido_cliente': 'order_id/l10n_br_pedido_compra',
            'data_pedido': 'order_id/create_date',
            'data_atual_pedido': 'order_id/date_order',
            'status_pedido': 'order_id/state',
            
            # 👥 DADOS DO CLIENTE
            'cnpj_cpf': 'order_id/partner_id/l10n_br_cnpj',
            'raz_social': 'order_id/partner_id/l10n_br_razao_social',
            'raz_social_red': 'order_id/partner_id/name',
            'municipio': 'order_id/partner_id/l10n_br_municipio_id/name',
            'estado': 'order_id/partner_id/state_id/code',
            'vendedor': 'order_id/user_id',
            'equipe_vendas': 'order_id/team_id',
            
            # 📦 DADOS DO PRODUTO
            'nome_produto': 'product_id/name',
            'unid_medida_produto': 'product_id/uom_id',
            'embalagem_produto': 'product_id/categ_id/name',
            'materia_prima_produto': 'product_id/categ_id/parent_id/name',
            'categoria_produto': 'product_id/categ_id/parent_id/parent_id/name',
            
            # 📊 QUANTIDADES E VALORES
            'qtd_produto_pedido': 'product_uom_qty',
            'qtd_saldo_produto_pedido': 'qty_saldo',
            'qtd_cancelada_produto_pedido': 'qty_cancelado',
            'preco_produto_pedido': 'price_unit',
            
            # 💳 CONDIÇÕES COMERCIAIS
            'cond_pgto_pedido': 'order_id/payment_term_id',
            'forma_pgto_pedido': 'order_id/payment_provider_id',
            'incoterm': 'order_id/incoterm',
            'metodo_entrega_pedido': 'order_id/carrier_id',
            'data_entrega_pedido': 'order_id/commitment_date',
            'cliente_nec_agendamento': 'order_id/partner_id/agendamento',
            'observ_ped_1': 'order_id/picking_note',
            
            # 🏠 ENDEREÇO DE ENTREGA COMPLETO (EXATAMENTE COMO USUÁRIO ESPECIFICOU)
            'cnpj_endereco_ent': 'order_id/partner_shipping_id/l10n_br_cnpj',
            'empresa_endereco_ent': 'order_id/partner_shipping_id/name',
            'cep_endereco_ent': 'order_id/partner_shipping_id/zip',
            'nome_cidade': 'order_id/partner_shipping_id/l10n_br_municipio_id/name',
            'cod_uf': 'order_id/partner_shipping_id/l10n_br_municipio_id',
            'bairro_endereco_ent': 'order_id/partner_shipping_id/l10n_br_endereco_bairro',  # CORRETO do CSV
            'rua_endereco_ent': 'order_id/partner_shipping_id/street',
            'endereco_ent': 'order_id/partner_shipping_id/l10n_br_endereco_numero',  # CORRETO do CSV
            'telefone_endereco_ent': 'order_id/partner_shipping_id/phone',
        }
        
        logger.info(f"Mapeamento hardcoded carregado: {len(self.mapeamento_carteira)} campos")
     
    def _definir_campos_multiplas_queries(self):
        """Define quais campos do mapeamento hardcoded precisam de múltiplas queries"""
        
        # Identificar automaticamente campos que têm mais de 2 níveis de relação
        # ou que acessam campos de múltiplos modelos
        multiplas_queries = {}
        
        for campo_carteira, campo_odoo in self.mapeamento_carteira.items():
            partes = campo_odoo.split('/')
            
            # Critério: campos com 3+ níveis OU campos específicos que sabemos que precisam
            if (len(partes) >= 3 or 
                'partner_id' in campo_odoo or 
                'partner_shipping_id' in campo_odoo or
                'state_id' in campo_odoo or
                'municipio_id' in campo_odoo or
                'categ_id/parent_id' in campo_odoo):
                
                multiplas_queries[campo_odoo] = self._gerar_queries_para_campo(campo_odoo)
        
        self.campos_multiplas_queries = multiplas_queries
        logger.info(f"Campos múltiplas queries identificados: {len(multiplas_queries)}")
    
    def _gerar_queries_para_campo(self, campo_odoo: str) -> Dict[str, List]:
        """Gera automaticamente as queries necessárias para um campo"""
        partes = campo_odoo.split('/')
        
        if len(partes) == 1:
            # Campo direto - não precisa de múltiplas queries
            return {"queries": []}
        
        queries = [("sale.order.line", partes[0])]  # Sempre começa com sale.order.line
        
        for i in range(1, len(partes)):
            if partes[i-1] == 'order_id':
                queries.append(("sale.order", partes[i]))
            elif partes[i-1] == 'product_id':
                queries.append(("product.product", partes[i]))
            elif partes[i-1] == 'partner_id' or partes[i-1] == 'partner_shipping_id':
                queries.append(("res.partner", partes[i]))
            elif partes[i-1] == 'state_id':
                queries.append(("res.country.state", partes[i]))
            elif partes[i-1] == 'l10n_br_municipio_id':
                queries.append(("l10n_br_ciel_it_account.res.municipio", partes[i]))
            elif partes[i-1] == 'categ_id':
                queries.append(("product.category", partes[i]))
            elif partes[i-1] == 'parent_id' and i >= 2 and partes[i-2] == 'categ_id':
                queries.append(("product.category", partes[i]))
            elif partes[i-1] in ['user_id', 'team_id', 'payment_term_id', 'payment_provider_id', 'carrier_id']:
                # Estes são relações simples que o Odoo resolve automaticamente
                continue
            else:
                # Para outros casos, assumir que é continuação do modelo anterior
                continue
        
        return {"queries": queries}
    
    def mapear_para_carteira(self, dados_odoo: List[Dict]) -> List[Dict]:
        """
        Mapeia dados do Odoo para o formato da CarteiraPrincipal
        usando EXATAMENTE o mapeamento fornecido pelo usuário
        """
        try:
            dados_mapeados = []
            
            for linha_odoo in dados_odoo:
                item_carteira = {}
                
                for campo_carteira, campo_odoo in self.mapeamento_carteira.items():
                    try:
                        # Verificar se é um campo que precisa de múltiplas queries
                        if campo_odoo in self.campos_multiplas_queries:
                            # Para múltiplas queries, vamos precisar buscar os dados relacionados
                            # Por enquanto, marcar como None e tratar depois
                            valor = None
                            logger.debug(f"Campo {campo_odoo} requer múltiplas queries - tratamento especial necessário")
                        else:
                            # Campos simples - usar a lógica existente
                            valor = self._extrair_valor_simples(linha_odoo, campo_odoo)
                        
                        item_carteira[campo_carteira] = valor
                        
                    except Exception as e:
                        logger.warning(f"Erro ao mapear campo {campo_carteira} -> {campo_odoo}: {e}")
                        item_carteira[campo_carteira] = None
                
                dados_mapeados.append(item_carteira)
            
            logger.info(f"Mapeamento concluído: {len(dados_mapeados)} itens processados")
            return dados_mapeados
            
        except Exception as e:
            logger.error(f"Erro no mapeamento para carteira: {e}")
            return []
    
    def _extrair_valor_simples(self, dados: Dict, campo_path: str) -> Any:
        """Extrai valor usando sintaxe simples (sem múltiplas queries)"""
        try:
            if '/' not in campo_path:
                # Campo direto
                return dados.get(campo_path)
            
            # Campo com relação simples (ex: product_id/name)
            partes = campo_path.split('/')
            valor_atual = dados
            
            for parte in partes:
                if isinstance(valor_atual, dict):
                    valor_atual = valor_atual.get(parte)
                elif isinstance(valor_atual, list) and len(valor_atual) > 0:
                    # Se for uma lista, pegar o primeiro item
                    valor_atual = valor_atual[0].get(parte) if isinstance(valor_atual[0], dict) else None
                else:
                    return None
                
                if valor_atual is None:
                    break
            
            return valor_atual
            
        except Exception as e:
            logger.debug(f"Erro ao extrair valor simples para {campo_path}: {e}")
            return None
    
    def obter_campos_multiplas_queries(self) -> Dict[str, Dict]:
        """Retorna os campos que precisam de múltiplas queries"""
        return self.campos_multiplas_queries
    
    def eh_campo_multiplas_queries(self, campo_odoo: str) -> bool:
        """Verifica se um campo precisa de múltiplas queries"""
        return campo_odoo in self.campos_multiplas_queries
    
    def executar_multiplas_queries(self, odoo_connection, campo_odoo: str, linha_base: Dict) -> Any:
        """
        Executa múltiplas queries para obter o valor de um campo complexo
        """
        try:
            if campo_odoo not in self.campos_multiplas_queries:
                return None
            
            queries_info = self.campos_multiplas_queries[campo_odoo]
            queries = queries_info["queries"]
            
            valor_atual = linha_base
            id_atual = None
            
            for i, (modelo, campo) in enumerate(queries):
                if i == 0:
                    # Primeira query - pegar o ID do campo na linha base
                    id_atual = valor_atual.get(campo)
                    if isinstance(id_atual, list) and len(id_atual) > 0:
                        id_atual = id_atual[0]  # Pegar o ID da relação
                elif i == len(queries) - 1:
                    # Última query - pegar o campo final
                    if id_atual:
                        registro = odoo_connection.buscar_registro_por_id(modelo, id_atual)
                        if registro:
                            return registro.get(campo)
                else:
                    # Queries intermediárias - buscar o próximo ID
                    if id_atual:
                        registro = odoo_connection.buscar_registro_por_id(modelo, id_atual)
                        if registro:
                            id_atual = registro.get(campo)
                            if isinstance(id_atual, list) and len(id_atual) > 0:
                                id_atual = id_atual[0]
                        else:
                            break
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao executar múltiplas queries para {campo_odoo}: {e}")
            return None
    
    def mapear_para_carteira_completo(self, dados_odoo: List[Dict], odoo_connection=None) -> List[Dict]:
        """
        Mapeia dados do Odoo para CarteiraPrincipal incluindo campos com múltiplas queries
        """
        try:
            dados_mapeados = []
            
            for linha_odoo in dados_odoo:
                item_carteira = {}
                
                for campo_carteira, campo_odoo in self.mapeamento_carteira.items():
                    try:
                        if self.eh_campo_multiplas_queries(campo_odoo) and odoo_connection:
                            # Campo que precisa de múltiplas queries
                            valor = self.executar_multiplas_queries(odoo_connection, campo_odoo, linha_odoo)
                        else:
                            # Campo simples
                            valor = self._extrair_valor_simples(linha_odoo, campo_odoo)
                        
                        item_carteira[campo_carteira] = valor
                        
                    except Exception as e:
                        logger.warning(f"Erro ao mapear campo {campo_carteira} -> {campo_odoo}: {e}")
                        item_carteira[campo_carteira] = None
                
                dados_mapeados.append(item_carteira)
            
            logger.info(f"Mapeamento completo concluído: {len(dados_mapeados)} itens processados")
            return dados_mapeados
            
        except Exception as e:
            logger.error(f"Erro no mapeamento completo: {e}")
            return []
    
    def obter_estatisticas_mapeamento(self) -> Dict[str, Any]:
        """Retorna estatísticas do mapeamento"""
        total_campos = len(self.mapeamento_carteira)
        campos_simples = total_campos - len(self.campos_multiplas_queries)
        campos_complexos = len(self.campos_multiplas_queries)
        
        return {
            "total_campos": total_campos,
            "campos_simples": campos_simples,
            "campos_complexos": campos_complexos,
            "percentual_simples": (campos_simples / total_campos * 100) if total_campos > 0 else 0,
            "percentual_complexos": (campos_complexos / total_campos * 100) if total_campos > 0 else 0
        } 