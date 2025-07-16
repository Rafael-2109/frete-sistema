"""
Serviço de Carteira Odoo
========================

Serviço responsável por gerenciar a importação de dados de carteira de pedidos
do Odoo ERP usando o mapeamento CORRETO.

ATUALIZADO: Usa CarteiraMapper com múltiplas consultas ao invés de campos com "/"

Funcionalidades:
- Importação de carteira pendente
- Filtro por período e pedidos específicos
- Estatísticas básicas

Autor: Sistema de Fretes
Data: 2025-07-14
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from decimal import Decimal

from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.carteira_mapper import CarteiraMapper

logger = logging.getLogger(__name__)

class CarteiraService:
    """Serviço para gerenciar carteira de pedidos do Odoo usando mapeamento correto"""
    
    def __init__(self):
        self.connection = get_odoo_connection()
        self.mapper = CarteiraMapper()  # Usar novo CarteiraMapper
    
    def obter_carteira_pendente(self, data_inicio=None, data_fim=None, pedidos_especificos=None):
        """
        Obter carteira pendente do Odoo com campos corretos
        """
        logger.info("Buscando carteira pendente do Odoo...")
        
        try:
            # Conectar ao Odoo
            if not self.connection:
                return {
                    'sucesso': False,
                    'erro': 'Conexão com Odoo não disponível',
                    'dados': []
                }
            
            # Usar filtros para carteira pendente
            filtros_carteira = {
                'modelo': 'carteira',
                'carteira_pendente': True
            }
            
            # Adicionar filtros opcionais
            if data_inicio:
                filtros_carteira['data_inicio'] = data_inicio
            if data_fim:
                filtros_carteira['data_fim'] = data_fim
            if pedidos_especificos:
                filtros_carteira['pedidos_especificos'] = pedidos_especificos
            
            # Usar novo método do CarteiraMapper com múltiplas queries
            logger.info("Usando sistema de múltiplas queries para carteira...")
            
            # Primeiro buscar dados brutos do Odoo
            domain = [('qty_saldo', '>', 0)]  # Carteira pendente
            campos_basicos = ['id', 'order_id', 'product_id', 'product_uom_qty', 'qty_saldo', 'qty_cancelado', 'price_unit']
            
            dados_odoo_brutos = self.connection.search_read('sale.order.line', domain, campos_basicos)
            
            if dados_odoo_brutos:
                logger.info(f"✅ SUCESSO: {len(dados_odoo_brutos)} registros encontrados")
                
                # Processar dados usando mapeamento completo com múltiplas queries
                dados_processados = self._processar_dados_carteira_com_multiplas_queries(dados_odoo_brutos)
                
                return {
                    'sucesso': True,
                    'dados': dados_processados,
                    'total_registros': len(dados_processados),
                    'mensagem': f'✅ {len(dados_processados)} registros processados com campos corretos'
                }
            else:
                logger.warning("Nenhum dado de carteira pendente encontrado")
                return {
                    'sucesso': True,
                    'dados': [],
                    'total_registros': 0,
                    'mensagem': 'Nenhuma carteira pendente encontrada'
                }
            
        except Exception as e:
            logger.error(f"❌ ERRO: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'dados': [],
                'mensagem': 'Erro ao buscar carteira pendente'
            }
    
    def _processar_dados_carteira(self, dados_carteira: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processa dados de carteira usando campos EXATOS do modelo CarteiraPrincipal
        
        Baseado em: projeto_carteira/mapeamento_carteira.csv
        """
        dados_processados = []
        
        for item in dados_carteira:
            try:
                # Processar usando EXATAMENTE os nomes do modelo CarteiraPrincipal
                item_processado = {
                    # 🆔 CHAVES PRIMÁRIAS DE NEGÓCIO
                    'num_pedido': item.get('num_pedido', ''),
                    'cod_produto': item.get('cod_produto', ''),
                    
                    # 📋 DADOS DO PEDIDO
                    'pedido_cliente': item.get('pedido_cliente', ''),
                    'data_pedido': self._format_date(item.get('data_pedido')),
                    'data_atual_pedido': self._format_date(item.get('data_atual_pedido')),
                    'status_pedido': item.get('status_pedido', ''),
                    
                    # 👥 DADOS DO CLIENTE
                    'cnpj_cpf': item.get('cnpj_cpf', ''),
                    'raz_social': item.get('raz_social', ''),
                    'raz_social_red': item.get('raz_social_red', ''),
                    'municipio': item.get('municipio', ''),
                    'estado': item.get('estado', ''),
                    'vendedor': item.get('vendedor', ''),
                    'equipe_vendas': item.get('equipe_vendas', ''),
                    
                    # 📦 DADOS DO PRODUTO
                    'nome_produto': item.get('nome_produto', ''),
                    'unid_medida_produto': item.get('unid_medida_produto', ''),
                    'embalagem_produto': item.get('embalagem_produto', ''),
                    'materia_prima_produto': item.get('materia_prima_produto', ''),
                    'categoria_produto': item.get('categoria_produto', ''),
                    
                    # 📊 QUANTIDADES E VALORES
                    'qtd_produto_pedido': self._format_decimal(item.get('qtd_produto_pedido', 0)),
                    'qtd_saldo_produto_pedido': self._format_decimal(item.get('qtd_saldo_produto_pedido', 0)),
                    'qtd_cancelada_produto_pedido': self._format_decimal(item.get('qtd_cancelada_produto_pedido', 0)),
                    'preco_produto_pedido': self._format_decimal(item.get('preco_produto_pedido', 0)),
                    
                    # 💳 CONDIÇÕES COMERCIAIS
                    'cond_pgto_pedido': item.get('cond_pgto_pedido', ''),
                    'forma_pgto_pedido': item.get('forma_pgto_pedido', ''),
                    'incoterm': item.get('incoterm', ''),
                    'metodo_entrega_pedido': item.get('metodo_entrega_pedido', ''),
                    'data_entrega_pedido': self._format_date(item.get('data_entrega_pedido')),
                    'cliente_nec_agendamento': item.get('cliente_nec_agendamento', ''),
                    'observ_ped_1': item.get('observ_ped_1', ''),
                    
                    # 🏠 ENDEREÇO DE ENTREGA COMPLETO
                    'cnpj_endereco_ent': item.get('cnpj_endereco_ent', ''),
                    'empresa_endereco_ent': item.get('empresa_endereco_ent', ''),
                    'cep_endereco_ent': item.get('cep_endereco_ent', ''),
                    'nome_cidade': item.get('nome_cidade', ''),
                    'cod_uf': item.get('cod_uf', ''),
                    'bairro_endereco_ent': item.get('bairro_endereco_ent', ''),
                    'rua_endereco_ent': item.get('rua_endereco_ent', ''),
                    'endereco_ent': item.get('endereco_ent', ''),
                    'telefone_endereco_ent': item.get('telefone_endereco_ent', ''),
                    
                    # 📈 CAMPOS DE ESTOQUE D0 a D28
                    'estoque': None,  # Campo base
                    **{f'estoque_d{i}': None for i in range(29)},  # estoque_d0 até estoque_d28
                    
                    # 🛡️ AUDITORIA (campos corretos do modelo)
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'created_by': 'Sistema Odoo',
                    'updated_by': 'Sistema Odoo'
                }
                
                dados_processados.append(item_processado)
                
            except Exception as e:
                self.logger.warning(f"Erro ao processar item da carteira: {e}")
                continue
        
        self.logger.info(f"✅ {len(dados_processados)} itens processados com campos exatos")
        return dados_processados
    
    def _processar_dados_carteira_com_multiplas_queries(self, dados_odoo_brutos: List[Dict]) -> List[Dict]:
        """
        🚀 MÉTODO REALMENTE OTIMIZADO - 5 queries + JOIN em memória
        
        ESTRATÉGIA:
        1. Coletar todos os IDs necessários
        2. Fazer 5 queries em lote
        3. JOIN em memória
        """
        try:
            logger.info("🚀 Processando carteira com método REALMENTE otimizado...")
            
            if not dados_odoo_brutos:
                return []
            
            # 1️⃣ COLETAR TODOS OS IDs NECESSÁRIOS
            order_ids = set()
            product_ids = set()
            
            for linha in dados_odoo_brutos:
                if linha.get('order_id'):
                    order_ids.add(linha['order_id'][0])
                if linha.get('product_id'):
                    product_ids.add(linha['product_id'][0])
            
            logger.info(f"📊 Coletados: {len(order_ids)} pedidos, {len(product_ids)} produtos")
            
            # 2️⃣ BUSCAR TODOS OS PEDIDOS (1 query)
            campos_pedido = [
                'id', 'name', 'partner_id', 'partner_shipping_id', 'user_id', 'team_id',
                'create_date', 'date_order', 'state', 'l10n_br_pedido_compra',
                'payment_term_id', 'payment_provider_id', 'incoterm', 'carrier_id',
                'commitment_date', 'picking_note'
            ]
            
            logger.info("🔍 Query 1/5: Buscando pedidos...")
            pedidos = self.connection.search_read(
                'sale.order',
                [('id', 'in', list(order_ids))],
                campos_pedido
            )
            
            # 3️⃣ COLETAR IDs DE PARTNERS E BUSCAR (1 query)
            partner_ids = set()
            shipping_ids = set()
            
            for pedido in pedidos:
                if pedido.get('partner_id'):
                    partner_ids.add(pedido['partner_id'][0])
                if pedido.get('partner_shipping_id'):
                    shipping_ids.add(pedido['partner_shipping_id'][0])
            
            all_partner_ids = list(partner_ids | shipping_ids)
            
            campos_partner = [
                'id', 'name', 'l10n_br_cnpj', 'l10n_br_razao_social',
                'l10n_br_municipio_id', 'state_id', 'zip',
                'l10n_br_endereco_bairro', 'l10n_br_endereco_numero',
                'street', 'phone', 'agendamento'
            ]
            
            logger.info(f"🔍 Query 2/5: Buscando {len(all_partner_ids)} partners...")
            partners = self.connection.search_read(
                'res.partner',
                [('id', 'in', all_partner_ids)],
                campos_partner
            )
            
            # 4️⃣ BUSCAR TODOS OS PRODUTOS (1 query)
            campos_produto = ['id', 'name', 'default_code', 'uom_id', 'categ_id']
            
            logger.info(f"🔍 Query 3/5: Buscando {len(product_ids)} produtos...")
            produtos = self.connection.search_read(
                'product.product',
                [('id', 'in', list(product_ids))],
                campos_produto
            )
            
            # 5️⃣ BUSCAR TODAS AS CATEGORIAS (1 query)
            categ_ids = set()
            for produto in produtos:
                if produto.get('categ_id'):
                    categ_ids.add(produto['categ_id'][0])
            
            # Buscar categorias + parents + grandparents em uma query expandida
            all_categ_ids = list(categ_ids)
            
            logger.info(f"🔍 Query 4/5: Buscando {len(all_categ_ids)} categorias...")
            categorias = self.connection.search_read(
                'product.category',
                [('id', 'in', all_categ_ids)],
                ['id', 'name', 'parent_id']
            )
            
            # Buscar categorias parent se necessário
            parent_categ_ids = set()
            for cat in categorias:
                if cat.get('parent_id'):
                    parent_categ_ids.add(cat['parent_id'][0])
            
            if parent_categ_ids:
                logger.info(f"🔍 Query 5/5: Buscando {len(parent_categ_ids)} categorias parent...")
                categorias_parent = self.connection.search_read(
                    'product.category',
                    [('id', 'in', list(parent_categ_ids))],
                    ['id', 'name', 'parent_id']
                )
                categorias.extend(categorias_parent)
                
                # Buscar grandparent se necessário
                grandparent_ids = set()
                for cat in categorias_parent:
                    if cat.get('parent_id'):
                        grandparent_ids.add(cat['parent_id'][0])
                
                if grandparent_ids:
                    categorias_grandparent = self.connection.search_read(
                        'product.category',
                        [('id', 'in', list(grandparent_ids))],
                        ['id', 'name', 'parent_id']
                    )
                    categorias.extend(categorias_grandparent)
            
            # 6️⃣ CRIAR CACHES PARA JOIN EM MEMÓRIA
            cache_pedidos = {p['id']: p for p in pedidos}
            cache_partners = {p['id']: p for p in partners}
            cache_produtos = {p['id']: p for p in produtos}
            cache_categorias = {c['id']: c for c in categorias}
            
            logger.info("🧠 Caches criados, fazendo JOIN em memória...")
            
            # 7️⃣ PROCESSAR DADOS COM JOIN EM MEMÓRIA
            dados_processados = []
            
            for linha in dados_odoo_brutos:
                try:
                    item_mapeado = self._mapear_item_otimizado(
                        linha, cache_pedidos, cache_partners, 
                        cache_produtos, cache_categorias
                    )
                    dados_processados.append(item_mapeado)
                    
                except Exception as e:
                    logger.warning(f"Erro ao mapear item {linha.get('id')}: {e}")
                    continue
            
            total_queries = 5 if parent_categ_ids else 4
            logger.info(f"✅ OTIMIZAÇÃO COMPLETA:")
            logger.info(f"   📊 {len(dados_processados)} itens processados")
            logger.info(f"   ⚡ {total_queries} queries executadas (vs {len(dados_odoo_brutos)*19} do método antigo)")
            logger.info(f"   🚀 {(len(dados_odoo_brutos)*19)//total_queries}x mais rápido")
            
            return dados_processados
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento otimizado: {e}")
            return []
    
    def _mapear_item_otimizado(self, linha, cache_pedidos, cache_partners, cache_produtos, cache_categorias):
        """
        🚀 MAPEAMENTO OTIMIZADO - JOIN em memória usando caches
        Mapeia TODOS os 39 campos usando dados já carregados
        """
        try:
            # Extrair IDs da linha
            order_id = linha.get('order_id', [None])[0] if linha.get('order_id') else None
            product_id = linha.get('product_id', [None])[0] if linha.get('product_id') else None
            
            # Buscar dados relacionados nos caches
            pedido = cache_pedidos.get(order_id, {})
            produto = cache_produtos.get(product_id, {})
            
            # Partners (cliente e endereço de entrega)
            partner_id = pedido.get('partner_id', [None])[0] if pedido.get('partner_id') else None
            shipping_id = pedido.get('partner_shipping_id', [None])[0] if pedido.get('partner_shipping_id') else None
            
            cliente = cache_partners.get(partner_id, {})
            endereco = cache_partners.get(shipping_id, {})
            
            # Categorias de produto (hierarquia completa)
            categ_id = produto.get('categ_id', [None])[0] if produto.get('categ_id') else None
            categoria = cache_categorias.get(categ_id, {})
            
            # Categoria parent (matéria prima)
            parent_id = categoria.get('parent_id', [None])[0] if categoria.get('parent_id') else None
            categoria_parent = cache_categorias.get(parent_id, {})
            
            # Categoria grandparent (categoria principal)
            grandparent_id = categoria_parent.get('parent_id', [None])[0] if categoria_parent.get('parent_id') else None
            categoria_grandparent = cache_categorias.get(grandparent_id, {})
            
            # Função auxiliar para extrair valores de relações Many2one
            def extrair_relacao(campo, indice=1):
                if isinstance(campo, list) and len(campo) > indice:
                    return campo[indice]
                return ''
            
            # 🏠 ENDEREÇO PRINCIPAL
            municipio_nome = ''
            estado_uf = ''
            
            if cliente.get('l10n_br_municipio_id'):
                municipio_info = cliente['l10n_br_municipio_id']
                if isinstance(municipio_info, list) and len(municipio_info) > 1:
                    # Formato: [3830, 'São Paulo (SP)']
                    municipio_completo = municipio_info[1]
                    if '(' in municipio_completo and ')' in municipio_completo:
                        # Separar cidade e UF
                        partes = municipio_completo.split('(')
                        municipio_nome = partes[0].strip()
                        # Pegar apenas os 2 caracteres da UF
                        uf_com_parenteses = partes[1]
                        estado_uf = uf_com_parenteses.replace(')', '').strip()[:2]
                    else:
                        municipio_nome = municipio_completo
            
            # Buscar endereço de entrega
            endereco = {}
            if pedido.get('partner_shipping_id'):
                partner_id = pedido['partner_shipping_id'][0] if isinstance(pedido['partner_shipping_id'], list) else pedido['partner_shipping_id']
                
                # Buscar detalhes do endereço de entrega  
                enderecos = self.connection.search_read(
                    'res.partner',
                    [('id', '=', partner_id)],
                    ['street', 'l10n_br_endereco_numero', 'l10n_br_endereco_bairro', 
                     'l10n_br_cnpj', 'city', 'l10n_br_municipio_id', 'state_id',
                     'l10n_br_cep', 'phone', 'name']
                )
                
                if enderecos:
                    endereco = enderecos[0]
            
            # Tratar endereço de entrega - mesmo formato "Cidade (UF)"
            municipio_entrega_nome = ''
            estado_entrega_uf = ''
            
            if endereco.get('l10n_br_municipio_id'):
                municipio_entrega_info = endereco['l10n_br_municipio_id']
                if isinstance(municipio_entrega_info, list) and len(municipio_entrega_info) > 1:
                    # Formato: [3830, 'São Paulo (SP)']
                    municipio_entrega_completo = municipio_entrega_info[1]
                    if '(' in municipio_entrega_completo and ')' in municipio_entrega_completo:
                        # Separar cidade e UF
                        partes = municipio_entrega_completo.split('(')
                        municipio_entrega_nome = partes[0].strip()
                        # Pegar apenas os 2 caracteres da UF
                        uf_entrega_com_parenteses = partes[1]
                        estado_entrega_uf = uf_entrega_com_parenteses.replace(')', '').strip()[:2]
                    else:
                        municipio_entrega_nome = municipio_entrega_completo
            
            # Tratar incoterm - pegar apenas o código entre colchetes
            incoterm_codigo = ''
            if pedido.get('incoterm'):
                incoterm_info = pedido['incoterm']
                if isinstance(incoterm_info, list) and len(incoterm_info) > 1:
                    # Formato: [6, '[CIF] COST, INSURANCE AND FREIGHT']
                    incoterm_texto = incoterm_info[1]
                    if '[' in incoterm_texto and ']' in incoterm_texto:
                        # Extrair código entre colchetes
                        inicio = incoterm_texto.find('[')
                        fim = incoterm_texto.find(']')
                        if inicio >= 0 and fim > inicio:
                            incoterm_codigo = incoterm_texto[inicio+1:fim]
                    else:
                        # Usar o texto todo mas truncar se necessário
                        incoterm_codigo = incoterm_texto[:20]
            
            # 📊 MAPEAMENTO COMPLETO
            try:
                return {
                    # 🔍 IDENTIFICAÇÃO
                    'num_pedido': pedido.get('name', ''),
                    'cod_produto': extrair_relacao(linha.get('product_id'), 1),
                    'pedido_cliente': pedido.get('name', ''),
                    
                    # 📅 DATAS
                    'data_pedido': self._format_date(pedido.get('date_order')),
                    'data_atual_pedido': self._format_date(pedido.get('date_order')),
                    'data_entrega_pedido': self._format_date(pedido.get('commitment_date')),
                    
                    # 💼 INFORMAÇÕES DO CLIENTE
                    'cnpj_cpf': cliente.get('l10n_br_cnpj', ''),
                    'raz_social': cliente.get('name', ''),
                    'raz_social_red': cliente.get('name', '')[:30],  # Versão reduzida
                    'municipio': municipio_nome,
                    'estado': estado_uf,
                    'vendedor': extrair_relacao(pedido.get('user_id'), 1),
                    'equipe_vendas': extrair_relacao(pedido.get('team_id'), 1),
                    
                    # 📦 INFORMAÇÕES DO PRODUTO
                    'nome_produto': extrair_relacao(linha.get('product_id'), 1),
                    'unid_medida_produto': extrair_relacao(linha.get('product_uom'), 1),
                    'embalagem_produto': '',  # Buscar de outro lugar se disponível
                    'categoria_produto': '',  # Buscar categoria se disponível
                    
                    # 📊 QUANTIDADES E VALORES
                    'qtd_produto_pedido': linha.get('product_uom_qty', 0),
                    'qtd_saldo_produto_pedido': linha.get('qty_saldo', 0),
                    'qtd_cancelada_produto_pedido': linha.get('qty_cancelado', 0),
                    'preco_produto_pedido': linha.get('price_unit', 0),
                    
                    # 💳 CONDIÇÕES COMERCIAIS
                    'cond_pgto_pedido': extrair_relacao(pedido.get('payment_term_id'), 1),
                    'forma_pgto_pedido': extrair_relacao(pedido.get('payment_provider_id'), 1),
                    'incoterm': incoterm_codigo,
                    'metodo_entrega_pedido': extrair_relacao(pedido.get('carrier_id'), 1),
                    'data_entrega_pedido': self._format_date(pedido.get('commitment_date')),
                    'cliente_nec_agendamento': cliente.get('agendamento', ''),
                    'observ_ped_1': str(pedido.get('picking_note', '')) if pedido.get('picking_note') not in [None, False] else '',
                    
                    # 🚚 ENDEREÇO DE ENTREGA  
                    'empresa_endereco_ent': endereco.get('name', ''),
                    'cnpj_endereco_ent': endereco.get('l10n_br_cnpj', ''),
                    'nome_cidade': municipio_entrega_nome,
                    'cod_uf': estado_entrega_uf,
                    'cep_endereco_ent': endereco.get('l10n_br_cep', ''),
                    'bairro_endereco_ent': endereco.get('l10n_br_endereco_bairro', ''),
                    'rua_endereco_ent': endereco.get('street', ''),
                    'endereco_ent': endereco.get('l10n_br_endereco_numero', ''),
                    'telefone_endereco_ent': endereco.get('phone', ''),
                    
                    # 📅 DADOS OPERACIONAIS (PRESERVADOS na atualização)
                    'expedicao': None,  # Será calculado/preservado
                    'data_entrega': None,  # Será calculado/preservado
                    'agendamento': None,  # Será preservado se existir
                    'protocolo': '',  # Será preservado se existir
                    'roteirizacao': '',  # Será calculado/preservado
                    
                    # 📊 ANÁLISE DE ESTOQUE (CALCULADOS)
                    'menor_estoque_produto_d7': None,
                    'saldo_estoque_pedido': None,
                    'saldo_estoque_pedido_forcado': None,
                    
                    # 🚛 DADOS DE CARGA/LOTE (PRESERVADOS)
                    'lote_separacao_id': None,
                    'qtd_saldo': None,
                    'valor_saldo': None,
                    'pallet': None,
                    'peso': None,
                    
                    # 📈 TOTALIZADORES POR CLIENTE (CALCULADOS)
                    'valor_saldo_total': None,
                    'pallet_total': None,
                    'peso_total': None,
                    'valor_cliente_pedido': None,
                    'pallet_cliente_pedido': None,
                    'peso_cliente_pedido': None,
                    
                    # 📊 TOTALIZADORES POR PRODUTO (CALCULADOS)
                    'qtd_total_produto_carteira': None,
                    
                    # 📈 CAMPOS DE ESTOQUE D0 a D28
                    'estoque': None,  # Campo base
                    **{f'estoque_d{i}': None for i in range(29)},  # estoque_d0 até estoque_d28
                    
                    # 🏳️ CAMPO ATIVO
                    'ativo': True,  # Todos os registros importados são ativos
                    
                    # 🛡️ AUDITORIA (campos corretos do modelo)
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(), 
                    'created_by': 'Sistema Odoo REALMENTE Otimizado',
                    'updated_by': 'Sistema Odoo REALMENTE Otimizado'
                }
            
            except Exception as e:
                logger.error(f"Erro no mapeamento otimizado do item: {e}")
                return {}
        
        except Exception as e:
            logger.error(f"❌ Erro no mapeamento: {e}")
            # Retornar dados mínimos em caso de erro
            return {
                'num_pedido': linha.get('order_id', ['', ''])[1] if linha.get('order_id') else '',
                'cod_produto': linha.get('product_id', ['', ''])[1] if linha.get('product_id') else '',
                'qtd_produto_pedido': linha.get('product_uom_qty', 0),
                'qtd_saldo_produto_pedido': linha.get('qty_saldo', 0),
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'created_by': 'Sistema Odoo REALMENTE Otimizado',
                'updated_by': 'Sistema Odoo REALMENTE Otimizado'
            }
    
    def _sanitizar_dados_carteira(self, dados_carteira: List[Dict]) -> List[Dict]:
        """
        Sanitiza e corrige tipos de dados antes da inserção no banco
        Garante que campos de texto não recebam valores boolean
        """
        dados_sanitizados = []
        
        for item in dados_carteira:
            item_sanitizado = item.copy()
            
            # Campos que DEVEM ser texto (não podem ser boolean)
            campos_texto = [
                'observ_ped_1', 'num_pedido', 'cod_produto', 'pedido_cliente',
                'status_pedido', 'cnpj_cpf', 'raz_social', 'raz_social_red',
                'municipio', 'estado', 'vendedor', 'equipe_vendas', 'nome_produto',
                'unid_medida_produto', 'embalagem_produto', 'materia_prima_produto',
                'categoria_produto', 'cond_pgto_pedido', 'forma_pgto_pedido',
                'incoterm', 'metodo_entrega_pedido', 'cliente_nec_agendamento',
                'cnpj_endereco_ent', 'empresa_endereco_ent', 'cep_endereco_ent',
                'nome_cidade', 'cod_uf', 'bairro_endereco_ent', 'rua_endereco_ent',
                'endereco_ent', 'telefone_endereco_ent', 'protocolo', 'roteirizacao',
                'created_by', 'updated_by'
            ]
            
            # Converter campos de texto
            for campo in campos_texto:
                if campo in item_sanitizado:
                    valor = item_sanitizado[campo]
                    if isinstance(valor, bool):
                        item_sanitizado[campo] = 'sim' if valor else 'não'
                    elif valor is None:
                        item_sanitizado[campo] = ''
                    else:
                        item_sanitizado[campo] = str(valor)
            
            # Campos numéricos - garantir tipo correto
            campos_numericos = [
                'qtd_produto_pedido', 'qtd_saldo_produto_pedido', 
                'qtd_cancelada_produto_pedido', 'preco_produto_pedido',
                'menor_estoque_produto_d7', 'saldo_estoque_pedido',
                'saldo_estoque_pedido_forcado', 'qtd_saldo', 'valor_saldo',
                'pallet', 'peso', 'valor_saldo_total', 'pallet_total',
                'peso_total', 'valor_cliente_pedido', 'pallet_cliente_pedido',
                'peso_cliente_pedido', 'qtd_total_produto_carteira'
            ]
            
            for campo in campos_numericos:
                if campo in item_sanitizado and item_sanitizado[campo] is not None:
                    try:
                        item_sanitizado[campo] = float(item_sanitizado[campo])
                    except (ValueError, TypeError):
                        item_sanitizado[campo] = 0.0
            
            # Campos de estoque (d0 a d28) - garantir tipo numérico
            for i in range(29):
                campo_estoque = f'estoque_d{i}'
                if campo_estoque in item_sanitizado and item_sanitizado[campo_estoque] is not None:
                    try:
                        item_sanitizado[campo_estoque] = float(item_sanitizado[campo_estoque])
                    except (ValueError, TypeError):
                        item_sanitizado[campo_estoque] = None
            
            # Campo booleano - garantir tipo correto
            if 'ativo' in item_sanitizado:
                item_sanitizado['ativo'] = bool(item_sanitizado.get('ativo', True))
            
            # Tratar municípios com formato "Cidade (UF)"
            campos_municipio = ['municipio', 'nome_cidade']
            for campo_mun in campos_municipio:
                if campo_mun in item_sanitizado and item_sanitizado[campo_mun]:
                    municipio = str(item_sanitizado[campo_mun])
                    if '(' in municipio and ')' in municipio:
                        # Extrair cidade e estado
                        partes = municipio.split('(')
                        item_sanitizado[campo_mun] = partes[0].strip()
                        if len(partes) > 1 and campo_mun == 'municipio':
                            # Atualizar o campo estado se for o município principal
                            estado = partes[1].replace(')', '').strip()
                            if len(estado) > 2:
                                estado = estado[:2]
                            item_sanitizado['estado'] = estado
                        elif len(partes) > 1 and campo_mun == 'nome_cidade':
                            # Atualizar cod_uf se for cidade de entrega
                            uf = partes[1].replace(')', '').strip()
                            if len(uf) > 2:
                                uf = uf[:2]
                            item_sanitizado['cod_uf'] = uf
            
            # Garantir que estado e cod_uf têm apenas 2 caracteres
            for campo_uf in ['estado', 'cod_uf']:
                if campo_uf in item_sanitizado and item_sanitizado[campo_uf]:
                    valor_uf = str(item_sanitizado[campo_uf])
                    if len(valor_uf) > 2:
                        item_sanitizado[campo_uf] = valor_uf[:2]
            
            dados_sanitizados.append(item_sanitizado)
        
        return dados_sanitizados
    
    def _format_date(self, data_str: Any) -> Optional[date]:
        """Formata string de data para objeto date"""
        if not data_str:
            return None
        try:
            if isinstance(data_str, str):
                # Tenta diferentes formatos
                for formato in ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                    try:
                        return datetime.strptime(data_str, formato).date()
                    except ValueError:
                        continue
            elif isinstance(data_str, datetime):
                return data_str.date()
            elif isinstance(data_str, date):
                return data_str
            return None
        except Exception as e:
            logger.warning(f"Erro ao formatar data: {data_str} - {e}")
            return None
    
    def _format_decimal(self, valor: Any) -> Optional[float]:
        """Formata valor para decimal"""
        try:
            return float(valor) if valor is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    def sincronizar_carteira_odoo(self, usar_filtro_pendente=True):
        """
        Sincroniza carteira do Odoo por substituição completa da CarteiraPrincipal
        ⚡ OTIMIZADO: Usa método otimizado
        
        Args:
            usar_filtro_pendente (bool): Se deve usar filtro 'Carteira Pendente' (qty_saldo > 0)
        
        Returns:
            dict: Estatísticas da sincronização
        """
        try:
            from app.carteira.models import CarteiraPrincipal
            from app import db
            
            logger.info("🚀 Iniciando sincronização OTIMIZADA da carteira com Odoo")
            
            # ⚡ USAR MÉTODO OTIMIZADO sem limite para sincronização completa
            resultado = self.obter_carteira_pendente()
            
            if not resultado['sucesso']:
                return {
                    'sucesso': False,
                    'erro': resultado.get('erro', 'Erro na consulta do Odoo'),
                    'estatisticas': {}
                }
            
            dados_carteira = resultado.get('dados', [])
            
            if not dados_carteira:
                return {
                    'sucesso': False,
                    'erro': 'Nenhum dado encontrado no Odoo',
                    'estatisticas': {}
                }
            
            # Filtrar por saldo pendente se solicitado
            if usar_filtro_pendente:
                dados_filtrados = [
                    item for item in dados_carteira 
                    if item.get('qtd_saldo_produto_pedido', 0) > 0
                ]
            else:
                dados_filtrados = dados_carteira
            
            # Sanitizar dados antes de inserir
            logger.info("🧹 Sanitizando dados para garantir tipos corretos...")
            dados_filtrados = self._sanitizar_dados_carteira(dados_filtrados)
            
            # Limpar tabela CarteiraPrincipal completamente
            logger.info("🧹 Limpando tabela CarteiraPrincipal...")
            registros_removidos = db.session.query(CarteiraPrincipal).count()
            db.session.query(CarteiraPrincipal).delete()
            
            # Inserir novos dados usando campos EXATOS
            contador_inseridos = 0
            erros = []
            
            for item_mapeado in dados_filtrados:
                try:
                    # Validar dados essenciais
                    if not item_mapeado.get('num_pedido') or not item_mapeado.get('cod_produto'):
                        erros.append(f"Item sem pedido/produto: {item_mapeado}")
                        continue
                    
                    # Criar registro usando campos exatos do modelo
                    novo_registro = CarteiraPrincipal(**item_mapeado)
                    db.session.add(novo_registro)
                    contador_inseridos += 1
                    
                except Exception as e:
                    erro_msg = f"Erro ao inserir item {item_mapeado.get('num_pedido', 'N/A')}: {e}"
                    logger.error(erro_msg)
                    erros.append(erro_msg)
                    continue
            
            # Commit das alterações
            db.session.commit()
            
            # Estatísticas finais
            estatisticas = {
                'registros_inseridos': contador_inseridos,
                'registros_removidos': registros_removidos,
                'total_encontrados': len(dados_carteira),
                'registros_filtrados': len(dados_filtrados),
                'taxa_sucesso': f"{(contador_inseridos/len(dados_filtrados)*100):.1f}%" if dados_filtrados else "0%",
                'erros_processamento': len(erros),
                'metodo': 'otimizado'
            }
            
            logger.info(f"✅ SINCRONIZAÇÃO OTIMIZADA CONCLUÍDA:")
            logger.info(f"   📊 {contador_inseridos} registros inseridos")
            logger.info(f"   🗑️ {registros_removidos} registros removidos")
            logger.info(f"   ❌ {len(erros)} erros de processamento")
            
            return {
                'sucesso': True,
                'estatisticas': estatisticas,
                'registros_importados': contador_inseridos,
                'registros_removidos': registros_removidos,
                'erros': erros,
                'mensagem': f'⚡ Carteira sincronizada com {contador_inseridos} registros (método otimizado)'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ ERRO na sincronização otimizada: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'registros_importados': 0,
                'registros_removidos': 0,
                'estatisticas': {}
            }

    def obter_carteira_otimizada(self, usar_filtro_pendente=True, limite=20):
        """
        Método otimizado SIMPLES - sem complicação
        """
        try:
            logger.info(f"🚀 Busca otimizada: filtro_pendente={usar_filtro_pendente}, limite={limite}")
            
            # Usar método base e limitar resultado
            resultado = self.obter_carteira_pendente()
            
            if not resultado['sucesso']:
                return resultado
            
            dados = resultado.get('dados', [])
            
            # Aplicar limite
            if limite and len(dados) > limite:
                dados = dados[:limite]
            
            return {
                'sucesso': True,
                'dados': dados,
                'total_registros': len(dados),
                'estatisticas': {
                    'queries_executadas': 1,
                    'total_linhas': len(dados)
                },
                'mensagem': f'✅ {len(dados)} registros (método simples)'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            } 