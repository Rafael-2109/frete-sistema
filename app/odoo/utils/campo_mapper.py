"""
Mapeamento CORRETO dos campos do Odoo
====================================

Este módulo implementa o mapeamento EXATO baseado em:
- campos_faturamento.md
- campos_carteira.md

CORREÇÃO: Usa modelos corretos e campos especificados
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Sequence
from datetime import datetime

logger = logging.getLogger(__name__)

class CampoMapper:
    """
    Mapeamento corrigido baseado nas especificações reais
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    # CAMPOS DE FATURAMENTO - BASEADO EM campos_faturamento.md
    CAMPOS_FATURAMENTO = {
        "account.move.line": [
            'x_studio_nf_e',               # Linhas da fatura/NF-e
            'partner_id',                  # Parceiro (para CNPJ)
            'move_id',                     # Para acessar dados da fatura
            'product_id',                  # Produto
            'quantity',                    # Quantidade
            'price_total',                 # Valor total (equivalente a l10n_br_total_nfe)
            'date'                         # Data
        ],
        "account.move": [
            'invoice_origin',              # Origem
            'state',                       # Status
            'invoice_incoterm_id',         # Incoterm  
            'invoice_user_id',             # Vendedor
            'partner_id'                   # Cliente
        ],
        "res.partner": [
            'l10n_br_cnpj',               # CNPJ brasileiro
            'name',                       # Nome
            'l10n_br_municipio_id'        # Município brasileiro
        ],
        "product.product": [
            'default_code',               # Código/Referência
            'name',                       # Nome
            'weight'                      # Peso (gross_weight)
        ]
    }
    
    # CAMPOS DE CARTEIRA - BASEADO EM campos_carteira.md  
    CAMPOS_CARTEIRA = {
        "sale.order.line": [
            'order_id',                   # Referência do pedido
            'product_id',                 # Produto
            'product_uom_qty',            # Quantidade
            'qty_to_invoice',             # Quantidade a faturar
            'qty_invoiced',               # Quantidade faturada
            'price_unit',                 # Preço unitário
            'qty_delivered',              # Quantidade entregue
            'qty_saldo',                  # Saldo (campo chave para carteira pendente)
            'qty_cancelado',              # Cancelado
            'l10n_br_prod_valor',         # Valor do Produto
            'l10n_br_total_nfe'           # Valor do Item do Pedido
        ],
        "sale.order": [
            'l10n_br_pedido_compra',      # Pedido de Compra do Cliente
            'name',                       # Referência do pedido
            'create_date',                # Data de criação
            'date_order',                 # Data do pedido
            'partner_id',                 # Cliente
            'user_id',                    # Vendedor
            'team_id',                    # Equipe de vendas
            'state',                      # Status
            'payment_term_id',            # Condições de pagamento
            'payment_provider_id',        # Forma de Pagamento
            'picking_note',               # Notas para Expedição
            'incoterm',                   # Incoterm
            'carrier_id',                 # Método de entrega
            'commitment_date',            # Data de entrega
            'partner_shipping_id'         # Endereço de entrega
        ],
        "res.partner": [
            'l10n_br_cnpj',              # CNPJ
            'l10n_br_razao_social',      # Razão Social
            'name',                      # Nome
            'l10n_br_municipio_id',      # Município
            'state_id',                  # Estado
            'agendamento',               # Agendamento
            'zip',                       # CEP
            'l10n_br_endereco_bairro',   # Bairro
            'street',                    # Endereço
            'l10n_br_endereco_numero',   # Número
            'phone'                      # Telefone
        ],
        "product.product": [
            'default_code',              # Referência interna
            'name',                      # Nome
            'uom_id',                    # Unidade de medida
            'categ_id'                   # Categoria
        ]
    }
    
    def buscar_dados_completos(self, connection, filtros: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Busca dados completos usando múltiplas consultas - MODELO HÍBRIDO
        
        Para compatibilidade com código existente, mantém interface mas usa lógica corrigida
        """
        try:
            logger.info("Iniciando busca de dados completos do Odoo (CORRIGIDO)")
            
            # Determinar tipo de dados baseado em filtros
            if filtros.get('modelo') == 'faturamento':
                return self.buscar_faturamento_odoo(connection, filtros)
            elif filtros.get('modelo') == 'carteira' or filtros.get('carteira_pendente'):
                return self.buscar_carteira_odoo(connection, filtros)
            else:
                # Para compatibilidade, usar carteira por padrão mas com dados limitados
                logger.info("Usando modo compatibilidade - dados limitados")
                return self._buscar_compatibilidade(connection, filtros, limit)
        
        except Exception as e:
            logger.error(f"Erro ao buscar dados completos: {e}")
            return []
    
    def _buscar_compatibilidade(self, connection, filtros: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """
        Modo compatibilidade para manter funcionamento com código existente
        """
        try:
            # Buscar linhas de pedido (compatibilidade)
            domain = []
            if filtros.get('state'):
                pedidos_filtrados = connection.search(
                    'sale.order',
                    [('state', '=', filtros['state'])]
                )
                if pedidos_filtrados:
                    domain.append(('order_id', 'in', pedidos_filtrados))
            
            # Campos básicos para compatibilidade
            campos_basicos = ['id', 'product_id', 'order_id', 'name', 'product_uom_qty', 'price_unit', 'state']
            
            dados_linha = connection.search_read(
                'sale.order.line',
                domain,
                campos_basicos,
                limit=limit
            )
            
            if not dados_linha:
                return []
            
            logger.info(f"Encontradas {len(dados_linha)} linhas de pedido (compatibilidade)")
            
            # Extrair IDs para múltiplas consultas
            order_ids = self._extrair_ids(dados_linha, 'order_id')
            product_ids = self._extrair_ids(dados_linha, 'product_id')
            
            # Buscar dados relacionados
            pedidos_map = self._buscar_pedidos_basicos(connection, order_ids)
            produtos_map = self._buscar_produtos_basicos(connection, product_ids)
            
            # Extrair partner_ids
            partner_ids = []
            for pedido in pedidos_map.values():
                partner_id = pedido.get('partner_id')
                if partner_id:
                    pid = partner_id[0] if isinstance(partner_id, list) else partner_id
                    partner_ids.append(pid)
            
            clientes_map = self._buscar_clientes_basicos(connection, list(set(partner_ids)))
            
            # Integrar dados
            return self._integrar_dados_compatibilidade(dados_linha, pedidos_map, produtos_map, clientes_map)
            
        except Exception as e:
            logger.error(f"Erro no modo compatibilidade: {e}")
            return []
    
    def buscar_faturamento_odoo(self, connection, filtros: Optional[Dict] = None) -> List[Dict]:
        """
        Busca dados de faturamento usando modelo correto (account.move.line)
        """
        try:
            logger.info("Buscando dados de faturamento do Odoo (account.move.line)")
            
            # Aplicar filtro especificado em campos_faturamento.md
            filtro_faturamento = [
                "|", 
                ("l10n_br_tipo_pedido", "=", "venda"), 
                ("l10n_br_tipo_pedido", "=", "bonificacao")
            ]
            
            # Buscar linhas de fatura
            campos_linha = self.CAMPOS_FATURAMENTO["account.move.line"]
            
            dados_linha = connection.search_read(
                'account.move.line',
                filtro_faturamento,
                campos_linha,
                limit=100
            )
            
            if not dados_linha:
                logger.warning("Nenhuma linha de fatura encontrada")
                return []
            
            logger.info(f"Encontradas {len(dados_linha)} linhas de fatura")
            
            # Extrair IDs para buscar dados relacionados
            move_ids = self._extrair_ids(dados_linha, 'move_id')
            partner_ids = self._extrair_ids(dados_linha, 'partner_id')
            product_ids = self._extrair_ids(dados_linha, 'product_id')
            
            # Buscar dados das faturas
            faturas_map = {}
            if move_ids:
                faturas = connection.search_read(
                    'account.move',
                    [('id', 'in', move_ids)],
                    self.CAMPOS_FATURAMENTO["account.move"]
                )
                faturas_map = {f['id']: f for f in faturas}
            
            # Buscar dados dos parceiros
            parceiros_map = {}
            if partner_ids:
                parceiros = connection.search_read(
                    'res.partner',
                    [('id', 'in', partner_ids)],
                    self.CAMPOS_FATURAMENTO["res.partner"]
                )
                parceiros_map = {p['id']: p for p in parceiros}
            
            # Buscar dados dos produtos
            produtos_map = {}
            if product_ids:
                produtos = connection.search_read(
                    'product.product',
                    [('id', 'in', product_ids)],
                    self.CAMPOS_FATURAMENTO["product.product"]
                )
                produtos_map = {p['id']: p for p in produtos}
            
            # Integrar dados
            dados_faturamento = []
            for linha in dados_linha:
                try:
                    registro = self._processar_linha_faturamento(linha, faturas_map, parceiros_map, produtos_map)
                    if registro:
                        dados_faturamento.append(registro)
                except Exception as e:
                    logger.warning(f"Erro ao processar linha de fatura: {e}")
                    continue
            
            logger.info(f"Faturamento processado: {len(dados_faturamento)} registros")
            return dados_faturamento
            
        except Exception as e:
            logger.error(f"Erro ao buscar faturamento: {e}")
            return []
    
    def buscar_carteira_odoo(self, connection, filtros: Optional[Dict] = None) -> List[Dict]:
        """
        Busca dados de carteira usando TODOS os campos especificados
        """
        try:
            logger.info("Buscando carteira com TODOS os campos especificados")
            
            # Filtro carteira pendente
            filtro_carteira = [('qty_saldo', '>', 0)]  # Apenas com saldo pendente
            
            # Buscar linhas de pedido
            campos_linha = self.CAMPOS_CARTEIRA["sale.order.line"]
            
            dados_linha = connection.search_read(
                'sale.order.line',
                filtro_carteira,
                campos_linha,
                limit=100
            )
            
            if not dados_linha:
                logger.warning("Nenhuma linha de carteira encontrada")
                return []
            
            logger.info(f"Encontradas {len(dados_linha)} linhas de carteira")
            
            # Extrair IDs para múltiplas consultas
            order_ids = self._extrair_ids(dados_linha, 'order_id')
            product_ids = self._extrair_ids(dados_linha, 'product_id')
            
            # Buscar pedidos
            pedidos_map = {}
            if order_ids:
                pedidos = connection.search_read(
                    'sale.order',
                    [('id', 'in', order_ids)],
                    self.CAMPOS_CARTEIRA["sale.order"]
                )
                pedidos_map = {p['id']: p for p in pedidos}
            
            # Extrair partner_ids dos pedidos
            partner_ids = []
            shipping_ids = []
            for pedido in pedidos_map.values():
                partner_id = self._extrair_id_relacional(pedido.get('partner_id'))
                if partner_id:
                    partner_ids.append(partner_id)
                
                shipping_id = self._extrair_id_relacional(pedido.get('partner_shipping_id'))
                if shipping_id:
                    shipping_ids.append(shipping_id)
            
            partner_ids = list(set(partner_ids + shipping_ids))
            
            # Buscar parceiros
            parceiros_map = {}
            if partner_ids:
                parceiros = connection.search_read(
                    'res.partner',
                    [('id', 'in', partner_ids)],
                    self.CAMPOS_CARTEIRA["res.partner"]
                )
                parceiros_map = {p['id']: p for p in parceiros}
            
            # Buscar produtos
            produtos_map = {}
            if product_ids:
                produtos = connection.search_read(
                    'product.product',
                    [('id', 'in', product_ids)],
                    self.CAMPOS_CARTEIRA["product.product"]
                )
                produtos_map = {p['id']: p for p in produtos}
            
            # Integrar TODOS os campos especificados
            dados_carteira = []
            for linha in dados_linha:
                try:
                    registro = self._processar_linha_carteira(linha, pedidos_map, produtos_map, parceiros_map)
                    if registro:
                        dados_carteira.append(registro)
                except Exception as e:
                    logger.warning(f"Erro ao processar linha de carteira: {e}")
                    continue
            
            logger.info(f"Carteira processada: {len(dados_carteira)} registros")
            return dados_carteira
            
        except Exception as e:
            logger.error(f"Erro ao buscar carteira: {e}")
            return []
    
    def _processar_linha_faturamento(self, linha: Dict, faturas_map: Dict, parceiros_map: Dict, produtos_map: Dict) -> Optional[Dict]:
        """
        Processa linha de faturamento conforme campos_faturamento.md
        """
        # IDs relacionados
        move_id = self._extrair_id_relacional(linha.get('move_id'))
        partner_id = self._extrair_id_relacional(linha.get('partner_id'))
        product_id = self._extrair_id_relacional(linha.get('product_id'))
        
        # Dados relacionados
        fatura = faturas_map.get(move_id, {})
        parceiro = parceiros_map.get(partner_id, {})
        produto = produtos_map.get(product_id, {})
        
        # Mapeamento EXATO conforme campos_faturamento.md
        return {
            # Linhas da fatura/NF-e
            'numero_nf': linha.get('x_studio_nf_e'),
            
            # Parceiro/Cliente
            'cnpj_cliente': parceiro.get('l10n_br_cnpj'),
            'nome_cliente': parceiro.get('name'),
            'municipio': self._extrair_nome_relacional(parceiro.get('l10n_br_municipio_id')),
            
            # Origem e Status
            'origem': fatura.get('invoice_origin'),
            'status': fatura.get('state'),
            
            # Produto
            'codigo_produto': produto.get('default_code'),
            'nome_produto': produto.get('name'),
            'peso_bruto': produto.get('weight', 0),
            
            # Quantidade e Valores
            'quantidade': linha.get('quantity'),
            'valor_total_item_nf': linha.get('price_total'),
            
            # Data
            'data_fatura': linha.get('date'),
            
            # Incoterm e Vendedor
            'incoterm': self._extrair_nome_relacional(fatura.get('invoice_incoterm_id')),
            'vendedor': self._extrair_nome_relacional(fatura.get('invoice_user_id'))
        }
    
    def _processar_linha_carteira(self, linha: Dict, pedidos_map: Dict, produtos_map: Dict, parceiros_map: Dict) -> Optional[Dict]:
        """
        Processa linha de carteira conforme campos_carteira.md (42 campos)
        """
        # IDs relacionados
        order_id = self._extrair_id_relacional(linha.get('order_id'))
        product_id = self._extrair_id_relacional(linha.get('product_id'))
        
        # Dados relacionados
        pedido = pedidos_map.get(order_id, {})
        produto = produtos_map.get(product_id, {})
        
        # Parceiro principal
        partner_id = self._extrair_id_relacional(pedido.get('partner_id'))
        parceiro = parceiros_map.get(partner_id, {})
        
        # Endereço de entrega
        shipping_id = self._extrair_id_relacional(pedido.get('partner_shipping_id'))
        endereco_entrega = parceiros_map.get(shipping_id, {})
        
        # Mapeamento COMPLETO conforme campos_carteira.md (42 campos)
        return {
            # Referência do pedido
            'pedido_compra_cliente': pedido.get('l10n_br_pedido_compra'),
            'referencia_pedido': pedido.get('name'),
            'data_criacao': pedido.get('create_date'),
            'data_pedido': pedido.get('date_order'),
            
            # Cliente
            'cnpj_cliente': parceiro.get('l10n_br_cnpj'),
            'razao_social': parceiro.get('l10n_br_razao_social'),
            'nome_cliente': parceiro.get('name'),
            'municipio_cliente': self._extrair_nome_relacional(parceiro.get('l10n_br_municipio_id')),
            'estado_cliente': self._extrair_nome_relacional(parceiro.get('state_id')),
            
            # Vendedor e Equipe
            'vendedor': self._extrair_nome_relacional(pedido.get('user_id')),
            'equipe_vendas': self._extrair_nome_relacional(pedido.get('team_id')),
            
            # Produto
            'referencia_interna': produto.get('default_code'),
            'nome_produto': produto.get('name'),
            'unidade_medida': self._extrair_nome_relacional(produto.get('uom_id')),
            
            # Quantidades
            'quantidade': linha.get('product_uom_qty'),
            'quantidade_a_faturar': linha.get('qty_to_invoice'),
            'saldo': linha.get('qty_saldo'),
            'cancelado': linha.get('qty_cancelado'),
            'quantidade_faturada': linha.get('qty_invoiced'),
            'quantidade_entregue': linha.get('qty_delivered'),
            
            # Valores
            'preco_unitario': linha.get('price_unit'),
            'valor_produto': linha.get('l10n_br_prod_valor'),
            'valor_item_pedido': linha.get('l10n_br_total_nfe'),
            
            # Status
            'status_pedido': pedido.get('state'),
            
            # Categorias do produto
            'categoria_produto': self._extrair_nome_relacional(produto.get('categ_id')),
            'categoria_primaria': '',  # Requer consulta adicional
            'categoria_primaria_pai': '',  # Requer consulta adicional
            
            # Pagamento e Entrega
            'condicoes_pagamento': self._extrair_nome_relacional(pedido.get('payment_term_id')),
            'forma_pagamento': self._extrair_nome_relacional(pedido.get('payment_provider_id')),
            'notas_expedicao': pedido.get('picking_note'),
            'incoterm': pedido.get('incoterm'),
            'metodo_entrega': self._extrair_nome_relacional(pedido.get('carrier_id')),
            'data_entrega': pedido.get('commitment_date'),
            'agendamento_cliente': parceiro.get('agendamento'),
            
            # Endereço de entrega (todos os campos)
            'cnpj_endereco_entrega': endereco_entrega.get('l10n_br_cnpj'),
            'proprio_endereco': endereco_entrega.get('self'),
            'cep_entrega': endereco_entrega.get('zip'),
            'estado_entrega': self._extrair_nome_relacional(endereco_entrega.get('state_id')),
            'municipio_entrega': self._extrair_nome_relacional(endereco_entrega.get('l10n_br_municipio_id')),
            'bairro_entrega': endereco_entrega.get('l10n_br_endereco_bairro'),
            'endereco_entrega': endereco_entrega.get('street'),
            'numero_entrega': endereco_entrega.get('l10n_br_endereco_numero'),
            'telefone_entrega': endereco_entrega.get('phone')
        }
    
    # Métodos de compatibilidade para manter interface existente
    def mapear_para_faturamento(self, dados_integrados: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Mapeia dados integrados para formato de faturamento (COMPATIBILIDADE)
        """
        logger.info("Mapeando dados para formato de faturamento")
        
        # Se já são dados de faturamento, retornar como estão
        if dados_integrados and 'numero_nf' in dados_integrados[0]:
            return dados_integrados
        
        # Mapear dados genéricos para faturamento
        dados_faturamento = []
        for registro in dados_integrados:
            try:
                dados_faturamento.append({
                    'nome_pedido': registro.get('pedido_name', registro.get('referencia_pedido')),
                    'codigo_produto': registro.get('codigo_produto', registro.get('referencia_interna')),
                    'nome_produto': registro.get('produto_name', registro.get('nome_produto')),
                    'nome_cliente': registro.get('cliente_name', registro.get('nome_cliente')),
                    'cnpj_cliente': registro.get('cliente_vat', registro.get('cnpj_cliente')),
                    'quantidade_produto': registro.get('quantidade'),
                    'preco_unitario': registro.get('preco_unitario'),
                    'status_pedido': registro.get('pedido_state', registro.get('status_pedido')),
                    'data_pedido': registro.get('data_pedido'),
                    'valor_total_pedido': registro.get('valor_total', registro.get('valor_item_pedido')),
                    'cidade_cliente': registro.get('cliente_cidade', registro.get('municipio_cliente')),
                    'email_cliente': registro.get('cliente_email'),
                    'telefone_cliente': registro.get('cliente_telefone', registro.get('telefone_entrega'))
                })
            except Exception as e:
                logger.warning(f"Erro ao mapear registro: {e}")
                continue
        
        return dados_faturamento
    
    def mapear_para_carteira(self, dados_integrados: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Mapeia dados integrados para formato de carteira (COMPATIBILIDADE)
        """
        logger.info("Mapeando dados para formato de carteira")
        
        # Se já são dados de carteira, retornar como estão
        if dados_integrados and 'referencia_pedido' in dados_integrados[0]:
            return dados_integrados
        
        # Mapear dados genéricos para carteira
        dados_carteira = []
        for registro in dados_integrados:
            try:
                dados_carteira.append({
                    'numero_pedido': registro.get('pedido_name', registro.get('referencia_pedido')),
                    'produto': registro.get('produto_name', registro.get('nome_produto')),
                    'cliente': registro.get('cliente_name', registro.get('nome_cliente')),
                    'quantidade': registro.get('quantidade'),
                    'valor_unitario': registro.get('preco_unitario'),
                    'valor_total': registro.get('valor_total', registro.get('valor_item_pedido')),
                    'status': registro.get('pedido_state', registro.get('status_pedido')),
                    'data_criacao': registro.get('data_pedido', registro.get('data_criacao'))
                })
            except Exception as e:
                logger.warning(f"Erro ao mapear registro para carteira: {e}")
                continue
        
        return dados_carteira
    
    # Métodos auxiliares
    def _extrair_ids(self, dados: List[Dict], campo: str) -> List[int]:
        """Extrai IDs de campos relacionais"""
        ids = []
        for item in dados:
            valor = item.get(campo)
            if valor:
                if isinstance(valor, list) and len(valor) > 0:
                    ids.append(valor[0])
                elif isinstance(valor, int):
                    ids.append(valor)
        return list(set(ids))
    
    def _extrair_id_relacional(self, campo_relacional) -> Optional[int]:
        """Extrai ID de campo relacional [id, nome] ou id"""
        if isinstance(campo_relacional, list) and len(campo_relacional) > 0:
            return campo_relacional[0]
        elif isinstance(campo_relacional, int):
            return campo_relacional
        return None
    
    def _extrair_nome_relacional(self, campo_relacional) -> str:
        """Extrai nome de campo relacional [id, nome]"""
        if isinstance(campo_relacional, list) and len(campo_relacional) > 1:
            return campo_relacional[1]
        return str(campo_relacional) if campo_relacional else ''
    
    # Métodos de compatibilidade para busca básica
    def _buscar_pedidos_basicos(self, connection, order_ids: List[int]) -> Dict:
        """Busca pedidos com campos básicos"""
        if not order_ids:
            return {}
        
        campos = ['id', 'name', 'partner_id', 'date_order', 'state', 'amount_total', 'user_id']
        dados = connection.search_read('sale.order', [('id', 'in', order_ids)], campos)
        return {p['id']: p for p in dados}
    
    def _buscar_produtos_basicos(self, connection, product_ids: List[int]) -> Dict:
        """Busca produtos com campos básicos"""
        if not product_ids:
            return {}
        
        campos = ['id', 'name', 'default_code', 'list_price', 'standard_price']
        dados = connection.search_read('product.product', [('id', 'in', product_ids)], campos)
        return {p['id']: p for p in dados}
    
    def _buscar_clientes_basicos(self, connection, partner_ids: List[int]) -> Dict:
        """Busca clientes com campos básicos"""
        if not partner_ids:
            return {}
        
        campos = ['id', 'name', 'vat', 'city', 'email', 'phone']
        dados = connection.search_read('res.partner', [('id', 'in', partner_ids)], campos)
        return {c['id']: c for c in dados}
    
    def _integrar_dados_compatibilidade(self, linhas: List[Dict], pedidos_map: Dict, produtos_map: Dict, clientes_map: Dict) -> List[Dict]:
        """Integra dados no modo compatibilidade"""
        dados_integrados = []
        
        for linha in linhas:
            try:
                order_id = self._extrair_id_relacional(linha.get('order_id'))
                product_id = self._extrair_id_relacional(linha.get('product_id'))
                
                pedido = pedidos_map.get(order_id, {})
                produto = produtos_map.get(product_id, {})
                
                partner_id = self._extrair_id_relacional(pedido.get('partner_id'))
                cliente = clientes_map.get(partner_id, {})
                
                registro_integrado = {
                    'linha_id': linha.get('id'),
                    'linha_name': linha.get('name'),
                    'quantidade': linha.get('product_uom_qty'),
                    'preco_unitario': linha.get('price_unit'),
                    'linha_state': linha.get('state'),
                    'pedido_id': pedido.get('id'),
                    'pedido_name': pedido.get('name'),
                    'data_pedido': pedido.get('date_order'),
                    'pedido_state': pedido.get('state'),
                    'valor_total': pedido.get('amount_total'),
                    'produto_id': produto.get('id'),
                    'produto_name': produto.get('name'),
                    'codigo_produto': produto.get('default_code'),
                    'preco_lista': produto.get('list_price'),
                    'preco_custo': produto.get('standard_price'),
                    'cliente_id': cliente.get('id'),
                    'cliente_name': cliente.get('name'),
                    'cliente_vat': cliente.get('vat'),
                    'cliente_cidade': cliente.get('city'),
                    'cliente_email': cliente.get('email'),
                    'cliente_telefone': cliente.get('phone')
                }
                
                dados_integrados.append(registro_integrado)
                
            except Exception as e:
                logger.warning(f"Erro ao integrar linha {linha.get('id')}: {e}")
                continue
        
        return dados_integrados 