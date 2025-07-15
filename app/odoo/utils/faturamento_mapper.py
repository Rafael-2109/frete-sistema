"""
Mapeador de campos entre FaturamentoProduto e Odoo
Usando mapeamento hardcoded baseado em mapeamento_faturamento.csv
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class FaturamentoMapper:
    def __init__(self):
        self.mapeamento_faturamento = {}
        self.campos_multiplas_queries = {}
        self._carregar_mapeamento_faturamento()
        self._definir_campos_multiplas_queries()
    
    def _carregar_mapeamento_faturamento(self):
        """Define EXATAMENTE o mapeamento de faturamento - hardcoded no código"""
        
        # Mapeamento completo baseado no mapeamento_faturamento.csv
        # FaturamentoProduto -> Campo Odoo
        self.mapeamento_faturamento = {
            # 📄 DADOS DA NOTA FISCAL
            'numero_nf': 'move_id/name',  # Número da NF
            'data_fatura': 'date',  # Data da fatura/linha
            'origem': 'move_id/invoice_origin',  # Origem da fatura
            'status_nf': 'move_id/state',  # Status da fatura
            
            # 👥 DADOS DO CLIENTE
            'cnpj_cliente': 'partner_id/l10n_br_cnpj',  # CNPJ do cliente
            'nome_cliente': 'partner_id/name',  # Nome/Razão Social do cliente
            'municipio': 'partner_id/l10n_br_municipio_id/name',  # Município com tratamento especial
            'estado': 'partner_id/l10n_br_municipio_id',  # UF extraída do município (tratamento especial)
            
            # 🏢 DADOS COMERCIAIS
            'vendedor': 'move_id/invoice_user_id/name',  # Vendedor da fatura
            'incoterm': 'move_id/invoice_incoterm_id/name',  # Incoterm da fatura
            
            # 📦 DADOS DO PRODUTO
            'cod_produto': 'product_id/default_code',  # Código/Referência do produto
            'nome_produto': 'product_id/name',  # Nome do produto
            'peso_unitario_produto': 'product_id/weight',  # Peso unitário do produto
            
            # 📊 QUANTIDADES E VALORES
            'qtd_produto_faturado': 'quantity',  # Quantidade faturada
            'valor_produto_faturado': 'price_total',  # Valor total do item
            'preco_produto_faturado': 'price_unit',  # Preço unitário
            
            # 📏 CAMPOS CALCULADOS (serão calculados após importação)
            'peso_total': 'calculado',  # peso_unitario_produto * qtd_produto_faturado
        }
        
        logger.info(f"Mapeamento de faturamento hardcoded carregado: {len(self.mapeamento_faturamento)} campos")
     
    def _definir_campos_multiplas_queries(self):
        """Define quais campos do mapeamento de faturamento precisam de múltiplas queries"""
        
        multiplas_queries = {}
        
        for campo_faturamento, campo_odoo in self.mapeamento_faturamento.items():
            if campo_odoo == 'calculado':
                continue  # Campos calculados não precisam de queries
                
            partes = campo_odoo.split('/')
            
            # Critério: campos com 2+ níveis de relação
            if (len(partes) >= 2 or 
                'partner_id' in campo_odoo or 
                'move_id' in campo_odoo or
                'product_id' in campo_odoo or
                'municipio_id' in campo_odoo or
                'invoice_user_id' in campo_odoo or
                'invoice_incoterm_id' in campo_odoo):
                
                multiplas_queries[campo_odoo] = self._gerar_queries_para_campo_faturamento(campo_odoo)
        
        self.campos_multiplas_queries = multiplas_queries
        logger.info(f"Campos faturamento múltiplas queries identificados: {len(multiplas_queries)}")
    
    def _gerar_queries_para_campo_faturamento(self, campo_odoo: str) -> Dict[str, List]:
        """Gera automaticamente as queries necessárias para um campo de faturamento"""
        partes = campo_odoo.split('/')
        
        if len(partes) == 1:
            # Campo direto na account.move.line - não precisa de múltiplas queries
            return {"queries": []}
        
        # Faturamento sempre começa com account.move.line
        queries = [("account.move.line", partes[0])]
        
        for i in range(1, len(partes)):
            if partes[i-1] == 'move_id':
                queries.append(("account.move", partes[i]))
            elif partes[i-1] == 'product_id':
                queries.append(("product.product", partes[i]))
            elif partes[i-1] == 'partner_id':
                queries.append(("res.partner", partes[i]))
            elif partes[i-1] == 'l10n_br_municipio_id':
                queries.append(("l10n_br_ciel_it_account.res.municipio", partes[i]))
            elif partes[i-1] == 'invoice_user_id':
                queries.append(("res.users", partes[i]))
            elif partes[i-1] == 'invoice_incoterm_id':
                queries.append(("account.incoterms", partes[i]))
            else:
                # Para outros casos, assumir que é continuação do modelo anterior
                continue
        
        return {"queries": queries}
    
    def mapear_para_faturamento(self, dados_odoo: List[Dict]) -> List[Dict]:
        """
        Mapeia dados do Odoo para o formato do FaturamentoProduto
        usando EXATAMENTE o mapeamento de faturamento
        """
        try:
            dados_mapeados = []
            
            for linha_odoo in dados_odoo:
                item_faturamento = {}
                
                for campo_faturamento, campo_odoo in self.mapeamento_faturamento.items():
                    try:
                        if campo_odoo == 'calculado':
                            # Campos calculados serão tratados depois
                            valor = None
                        elif campo_odoo in self.campos_multiplas_queries:
                            # Campo que precisa de múltiplas queries
                            valor = None
                            logger.debug(f"Campo {campo_odoo} requer múltiplas queries - tratamento especial necessário")
                        else:
                            # Campos simples - usar a lógica existente
                            valor = self._extrair_valor_simples(linha_odoo, campo_odoo)
                        
                        item_faturamento[campo_faturamento] = valor
                        
                    except Exception as e:
                        logger.warning(f"Erro ao mapear campo {campo_faturamento} -> {campo_odoo}: {e}")
                        item_faturamento[campo_faturamento] = None
                
                dados_mapeados.append(item_faturamento)
            
            logger.info(f"Mapeamento de faturamento concluído: {len(dados_mapeados)} itens processados")
            return dados_mapeados
            
        except Exception as e:
            logger.error(f"Erro no mapeamento de faturamento: {e}")
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
        Executa múltiplas queries para obter o valor de um campo complexo de faturamento
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
    
    def mapear_para_faturamento_completo(self, dados_odoo: List[Dict], odoo_connection=None) -> List[Dict]:
        """
        Mapeia dados do Odoo para FaturamentoProduto incluindo campos com múltiplas queries
        """
        try:
            dados_mapeados = []
            
            for linha_odoo in dados_odoo:
                item_faturamento = {}
                
                for campo_faturamento, campo_odoo in self.mapeamento_faturamento.items():
                    try:
                        if campo_odoo == 'calculado':
                            # Campos calculados - tratar depois
                            valor = None
                        elif self.eh_campo_multiplas_queries(campo_odoo) and odoo_connection:
                            # Campo que precisa de múltiplas queries
                            valor = self.executar_multiplas_queries(odoo_connection, campo_odoo, linha_odoo)
                        else:
                            # Campo simples
                            valor = self._extrair_valor_simples(linha_odoo, campo_odoo)
                        
                        item_faturamento[campo_faturamento] = valor
                        
                    except Exception as e:
                        logger.warning(f"Erro ao mapear campo {campo_faturamento} -> {campo_odoo}: {e}")
                        item_faturamento[campo_faturamento] = None
                
                # Processar campos calculados
                item_faturamento = self._processar_campos_calculados(item_faturamento)
                
                dados_mapeados.append(item_faturamento)
            
            logger.info(f"Mapeamento completo de faturamento concluído: {len(dados_mapeados)} itens processados")
            return dados_mapeados
            
        except Exception as e:
            logger.error(f"Erro no mapeamento completo de faturamento: {e}")
            return []
    
    def _processar_campos_calculados(self, item_faturamento: Dict) -> Dict:
        """Processa campos calculados após o mapeamento básico"""
        try:
            # peso_total = peso_unitario_produto * qtd_produto_faturado
            peso_unitario = item_faturamento.get('peso_unitario_produto', 0) or 0
            qtd_faturado = item_faturamento.get('qtd_produto_faturado', 0) or 0
            
            item_faturamento['peso_total'] = float(peso_unitario) * float(qtd_faturado)
            
            # preco_produto_faturado = valor_produto_faturado / qtd_produto_faturado
            valor_faturado = item_faturamento.get('valor_produto_faturado', 0) or 0
            if qtd_faturado > 0:
                item_faturamento['preco_produto_faturado'] = float(valor_faturado) / float(qtd_faturado)
            else:
                item_faturamento['preco_produto_faturado'] = 0
            
            # Tratamento especial para município e estado
            municipio_completo = item_faturamento.get('municipio', '')
            if municipio_completo and '(' in municipio_completo and ')' in municipio_completo:
                # Ex: "Fortaleza (CE)" -> separar cidade e UF
                partes = municipio_completo.split('(')
                item_faturamento['municipio'] = partes[0].strip()
                if len(partes) > 1:
                    item_faturamento['estado'] = partes[1].replace(')', '').strip()
            
            return item_faturamento
            
        except Exception as e:
            logger.warning(f"Erro ao processar campos calculados: {e}")
            return item_faturamento
    
    def obter_estatisticas_mapeamento(self) -> Dict[str, Any]:
        """Retorna estatísticas do mapeamento de faturamento"""
        total_campos = len(self.mapeamento_faturamento)
        campos_calculados = sum(1 for v in self.mapeamento_faturamento.values() if v == 'calculado')
        campos_complexos = len(self.campos_multiplas_queries)
        campos_simples = total_campos - campos_calculados - campos_complexos
        
        return {
            "total_campos": total_campos,
            "campos_simples": campos_simples,
            "campos_complexos": campos_complexos,
            "campos_calculados": campos_calculados,
            "percentual_simples": (campos_simples / total_campos * 100) if total_campos > 0 else 0,
            "percentual_complexos": (campos_complexos / total_campos * 100) if total_campos > 0 else 0,
            "percentual_calculados": (campos_calculados / total_campos * 100) if total_campos > 0 else 0
        } 