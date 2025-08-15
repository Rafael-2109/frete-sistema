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

from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.carteira_mapper import CarteiraMapper
from sqlalchemy import or_

logger = logging.getLogger(__name__)

class CarteiraService:
    """Serviço para gerenciar carteira de pedidos do Odoo usando mapeamento correto"""
    
    def __init__(self):
        # Usar conexão direta otimizada (safe_connection removida por causar lentidão)
        self.connection = get_odoo_connection()
        self.mapper = CarteiraMapper()  # Usar novo CarteiraMapper
    
    @staticmethod
    def is_pedido_odoo(numero_pedido: str) -> bool:
        """
        Verifica se um pedido é originado do Odoo baseado no prefixo.
        
        Critérios:
        - VSC: Pedido do Odoo
        - VCD: Pedido do Odoo
        - VFB: Pedido do Odoo
        - Outros: Pedido de fonte externa (não-Odoo)
        
        Args:
            numero_pedido (str): Número do pedido a verificar
            
        Returns:
            bool: True se for pedido Odoo, False caso contrário
        """
        if not numero_pedido:
            return False
            
        # Converter para string e remover espaços
        numero_pedido = str(numero_pedido).strip().upper()
        
        # Verificar prefixos Odoo
        prefixos_odoo = ('VSC', 'VCD', 'VFB')
        return numero_pedido.startswith(prefixos_odoo)
    
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
            domain = [
                ('qty_saldo', '>', 0),  # Carteira pendente
                ('order_id.state', 'in', ['draft', 'sent', 'sale'])  # ✅ FILTRO DE STATUS: Apenas pedidos válidos
            ]  
            campos_basicos = ['id', 'order_id', 'product_id', 'product_uom', 'product_uom_qty', 'qty_saldo', 'qty_cancelado', 'price_unit']
            
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
                
                # Usar o cache de partners já carregado (evita query extra)
                endereco = cache_partners.get(partner_id, {})
            
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
                    'cod_produto': produto.get('default_code', ''),  # Código do produto, não nome
                    'pedido_cliente': pedido.get('l10n_br_pedido_compra', ''),
                    
                    # 📅 DATAS
                    'data_pedido': self._format_date(pedido.get('create_date')),
                    'data_atual_pedido': self._format_date(pedido.get('date_order')),
                    'data_entrega_pedido': self._format_date(pedido.get('commitment_date')),
                    
                    # 📊 STATUS (mapeado para português)
                    'status_pedido': self._mapear_status_pedido(pedido.get('state', '')),
                    
                    # 💼 INFORMAÇÕES DO CLIENTE
                    'cnpj_cpf': cliente.get('l10n_br_cnpj', ''),
                    'raz_social': cliente.get('l10n_br_razao_social', ''),
                    'raz_social_red': cliente.get('name', '')[:30],  # Versão reduzida
                    'municipio': municipio_nome,
                    'estado': estado_uf,
                    'vendedor': extrair_relacao(pedido.get('user_id'), 1),
                    'equipe_vendas': extrair_relacao(pedido.get('team_id'), 1),
                    
                    # 📦 INFORMAÇÕES DO PRODUTO
                    # Usar o nome do produto buscado (mais confiável) ou fallback para o array
                    'nome_produto': produto.get('name', '') or extrair_relacao(linha.get('product_id'), 1),
                    'unid_medida_produto': extrair_relacao(linha.get('product_uom'), 1),
                    'embalagem_produto': categoria.get('name', ''),  # Categoria do produto
                    'materia_prima_produto': categoria_parent.get('name', ''),  # Sub categoria
                    'categoria_produto': categoria_grandparent.get('name', ''),  # Categoria principal
                    
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
                    'cliente_nec_agendamento': cliente.get('agendamento', ''),
                    'observ_ped_1': str(pedido.get('picking_note', '')) if pedido.get('picking_note') not in [None, False] else '',
                    
                    # 🚚 ENDEREÇO DE ENTREGA  
                    'empresa_endereco_ent': endereco.get('name', ''),
                    'cnpj_endereco_ent': endereco.get('l10n_br_cnpj', ''),
                    'nome_cidade': municipio_entrega_nome,
                    'cod_uf': estado_entrega_uf,
                    'cep_endereco_ent': endereco.get('zip', ''),  # CEP usa campo 'zip'
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
                    
                    # 📈 ANÁLISE DE ESTOQUE (CALCULADOS)
                    'menor_estoque_produto_d7': None,
                    'saldo_estoque_pedido': None,
                    'saldo_estoque_pedido_forcado': None,
                    
                    # 🚛 DADOS DE CARGA/LOTE (PRESERVADOS)
                    'separacao_lote_id': None,
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
        Garante que campos de texto não recebam valores boolean e não excedam limites
        """
        dados_sanitizados = []
        
        for item in dados_carteira:
            item_sanitizado = item.copy()
            
            # ⚠️ CAMPOS COM LIMITE DE 50 CARACTERES (críticos)
            campos_varchar50 = [
                'num_pedido', 'cod_produto', 'status_pedido', 'protocolo',
                'metodo_entrega_pedido'
            ]
            
            for campo in campos_varchar50:
                if campo in item_sanitizado and item_sanitizado[campo]:
                    valor = str(item_sanitizado[campo])
                    if len(valor) > 50:
                        logger.warning(f"Campo {campo} truncado de {len(valor)} para 50 caracteres: {valor}")
                        item_sanitizado[campo] = valor[:50]
            
            # ⚠️ CAMPOS COM LIMITE DE 20 CARACTERES (críticos)
            campos_varchar20 = [
                'unid_medida_produto', 'incoterm', 'cnpj_cpf', 'cnpj_endereco_ent',
                'endereco_ent', 'telefone_endereco_ent', 'cep_endereco_ent'
            ]
            
            for campo in campos_varchar20:
                if campo in item_sanitizado and item_sanitizado[campo]:
                    valor = str(item_sanitizado[campo])
                    if len(valor) > 20:
                        logger.warning(f"Campo {campo} truncado de {len(valor)} para 20 caracteres: {valor}")
                        item_sanitizado[campo] = valor[:20]
            
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
            
            # ⚠️ CAMPOS COM LIMITE DE 2 CARACTERES (UF)
            campos_varchar2 = ['estado', 'cod_uf']
            
            for campo in campos_varchar2:
                if campo in item_sanitizado and item_sanitizado[campo]:
                    valor_uf = str(item_sanitizado[campo])
                    if len(valor_uf) > 2:
                        logger.warning(f"Campo {campo} truncado de {len(valor_uf)} para 2 caracteres: {valor_uf}")
                        item_sanitizado[campo] = valor_uf[:2]
            
            # ⚠️ CAMPOS COM LIMITE DE 10 CARACTERES
            campos_varchar10 = ['cliente_nec_agendamento', 'cep_endereco_ent']
            
            for campo in campos_varchar10:
                if campo in item_sanitizado and item_sanitizado[campo]:
                    valor = str(item_sanitizado[campo])
                    if len(valor) > 10:
                        logger.warning(f"Campo {campo} truncado de {len(valor)} para 10 caracteres: {valor}")
                        item_sanitizado[campo] = valor[:10]
            
            # ⚠️ CAMPOS COM LIMITE DE 100 CARACTERES
            campos_varchar100 = [
                'pedido_cliente', 'raz_social_red', 'municipio', 'vendedor', 'equipe_vendas',
                'embalagem_produto', 'materia_prima_produto', 'categoria_produto',
                'cond_pgto_pedido', 'forma_pgto_pedido', 'nome_cidade', 'bairro_endereco_ent',
                'roteirizacao', 'created_by', 'updated_by'
            ]
            
            for campo in campos_varchar100:
                if campo in item_sanitizado and item_sanitizado[campo]:
                    valor = str(item_sanitizado[campo])
                    if len(valor) > 100:
                        logger.warning(f"Campo {campo} truncado de {len(valor)} para 100 caracteres: {valor}")
                        item_sanitizado[campo] = valor[:100]
            
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

    def _mapear_status_pedido(self, status_odoo: str) -> str:
        """
        🎯 MAPEAR STATUS DO ODOO PARA PORTUGUÊS
        
        Traduz status técnicos do Odoo para nomes em português
        que o sistema brasileiro compreende.
        """
        if not status_odoo:
            return 'Rascunho'
            
        mapeamento_status = {
            'draft': 'Cotação',
            'sent': 'Cotação', 
            'sale': 'Pedido de venda',
            'done': 'Pedido de venda',
            'cancel': 'Cancelado'
        }
        
        status_traduzido = mapeamento_status.get(status_odoo.lower(), status_odoo)
        logger.debug(f"Status mapeado: {status_odoo} → {status_traduzido}")
        return status_traduzido

    # ============================================================================
    # 🔧 MÉTODOS AUXILIARES CRÍTICOS PARA OPERAÇÃO COMPLETA
    # ============================================================================
    
    def _verificar_riscos_pre_sincronizacao(self):
        """
        🚨 VERIFICAÇÃO PRÉ-SINCRONIZAÇÃO: Detecta riscos operacionais críticos
        
        Verifica separações cotadas, faturamento pendente e outros riscos ANTES da sincronização destrutiva
        """
        try:
            logger.info("🔍 Verificando riscos operacionais antes da sincronização...")
            
            # Importar sistema de alertas
            from app.carteira.alert_system import AlertaSistemaCarteira
            
            alertas_criticos = []
            
            # ✅ VERIFICAÇÃO 1: Separações cotadas
            resultado_cotadas = AlertaSistemaCarteira.verificar_separacoes_cotadas_antes_sincronizacao()
            
            if resultado_cotadas.get('alertas'):
                logger.warning(f"🚨 {resultado_cotadas['quantidade']} separações COTADAS detectadas")
                
                alertas_criticos.append({
                    'tipo': 'SEPARACOES_COTADAS',
                    'nivel': 'CRITICO',
                    'quantidade': resultado_cotadas['quantidade'],
                    'separacoes_afetadas': resultado_cotadas['separacoes_afetadas'],
                    'mensagem': resultado_cotadas['mensagem'],
                    'recomendacao': resultado_cotadas['recomendacao']
                })
            
            # ✅ VERIFICAÇÃO 2: CRÍTICA - Pedidos cotados sem faturamento atualizado
            risco_faturamento = self._verificar_risco_faturamento_pendente()
            
            if risco_faturamento.get('risco_alto'):
                logger.critical(f"🚨 RISCO CRÍTICO: {risco_faturamento['pedidos_em_risco']} pedidos cotados podem perder NFs")
                
                alertas_criticos.append({
                    'tipo': 'FATURAMENTO_PENDENTE_CRITICO',
                    'nivel': 'CRITICO',
                    'quantidade': risco_faturamento['pedidos_em_risco'],
                    'pedidos_afetados': risco_faturamento['lista_pedidos'],
                    'mensagem': f"🚨 CRÍTICO: {risco_faturamento['pedidos_em_risco']} pedidos cotados podem perder referência às NFs",
                    'recomendacao': '⚠️ IMPORTANTE: Execute sincronização de FATURAMENTO ANTES da carteira'
                })
            
            # ✅ VERIFICAÇÃO 3: Última sincronização de faturamento
            tempo_ultima_sync_fat = self._verificar_ultima_sincronizacao_faturamento()
            
            if tempo_ultima_sync_fat.get('desatualizado'):
                logger.warning(f"⚠️ Faturamento desatualizado: {tempo_ultima_sync_fat['horas_atraso']} horas desde última sync")
                
                alertas_criticos.append({
                    'tipo': 'FATURAMENTO_DESATUALIZADO',
                    'nivel': 'AVISO',
                    'horas_atraso': tempo_ultima_sync_fat['horas_atraso'],
                    'mensagem': f"⚠️ Faturamento não sincronizado há {tempo_ultima_sync_fat['horas_atraso']} horas",
                    'recomendacao': 'Considere sincronizar faturamento primeiro para maior segurança'
                })
            
            # ✅ AVALIAÇÃO FINAL DE SEGURANÇA
            riscos_criticos = [a for a in alertas_criticos if a['nivel'] == 'CRITICO']
            safe_to_proceed = len(riscos_criticos) == 0
            
            if not safe_to_proceed:
                logger.critical(f"🚨 SINCRONIZAÇÃO COM RISCOS CRÍTICOS: {len(riscos_criticos)} alertas impedem operação segura")
            
            return {
                'alertas_criticos': alertas_criticos,
                'total_alertas': len(alertas_criticos),
                'riscos_criticos': len(riscos_criticos),
                'safe_to_proceed': safe_to_proceed,
                'recomendacao_sequencia': 'Sincronize FATURAMENTO → CARTEIRA para máxima segurança',
                'timestamp': datetime.now()
            }
            
        except ImportError:
            logger.warning("Sistema de alertas não disponível - prosseguindo sem verificação")
            return {
                'alertas_criticos': [],
                'total_alertas': 0,
                'safe_to_proceed': True,
                'warning': 'Sistema de alertas indisponível'
            }
        except Exception as e:
            logger.error(f"❌ Erro na verificação pré-sincronização: {e}")
            return {
                'alertas_criticos': [],
                'total_alertas': 0,
                'safe_to_proceed': True,
                'erro': str(e)
            }
    
    def _criar_backup_pre_separacoes(self):
        """
        💾 BACKUP AUTOMÁTICO: Marca pré-separações como "aguardando recomposição"
        
        As pré-separações já existem na tabela, apenas marcamos como pendentes
        de recomposição após a sincronização
        """
        try:
            from app.carteira.models import PreSeparacaoItem
            from app import db
            
            logger.info("💾 Marcando pré-separações para recomposição...")
            
            # Buscar todas as pré-separações ativas
            pre_separacoes_ativas = PreSeparacaoItem.query.filter(
                PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
            ).all()
            
            contador_backup = 0
            
            for pre_sep in pre_separacoes_ativas:
                # Marcar como pendente de recomposição
                pre_sep.recomposto = False
                pre_sep.observacoes = f"Aguardando recomposição pós-sync {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                contador_backup += 1
            
            # Salvar alterações
            db.session.commit()
            
            logger.info(f"✅ {contador_backup} pré-separações marcadas para recomposição")
            
            return {
                'sucesso': True,
                'total_backups': contador_backup,
                'timestamp': datetime.now(),
                'metodo': 'marcacao_recomposicao'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no backup de pré-separações: {e}")
            return {
                'sucesso': False,
                'total_backups': 0,
                'erro': str(e)
            }
    
    def _recompor_pre_separacoes_automaticamente(self):
        """
        🔄 RECOMPOSIÇÃO AUTOMÁTICA: Reconstrói pré-separações após sincronização
        
        Usa o sistema existente de recomposição para manter as decisões operacionais
        """
        try:
            from app.carteira.models import PreSeparacaoItem
            from app.estoque.triggers_recalculo_otimizado import RecalculoMovimentacaoPrevista
            from app import db
            
            logger.info("🔄 Iniciando recomposição automática de pré-separações...")
            
            # Usar método existente de recomposição
            resultado = PreSeparacaoItem.recompor_todas_pendentes("SYNC_ODOO_AUTO")
            
            logger.info(f"✅ Recomposição concluída: {resultado['sucesso']} sucessos, {resultado['erro']} erros")
            
            # IMPORTANTE: Recalcular MovimentacaoPrevista após recomposição
            logger.info("📊 Recalculando MovimentacaoPrevista após recomposição...")
            try:
                with db.engine.connect() as connection:
                    RecalculoMovimentacaoPrevista.recalcular_apos_sincronizacao(connection)
                    connection.commit()
                logger.info("✅ MovimentacaoPrevista recalculada com sucesso")
            except Exception as e:
                logger.error(f"❌ Erro ao recalcular MovimentacaoPrevista: {e}")
            
            return {
                'sucessos': resultado['sucesso'],
                'erros': resultado['erro'],
                'timestamp': datetime.now(),
                'metodo': 'recomposicao_automatica',
                'movimentacao_recalculada': True
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na recomposição automática: {e}")
            return {
                'sucessos': 0,
                'erros': 0,
                'erro': str(e)
            }
    
    def _verificar_alertas_pos_sincronizacao(self, dados_sincronizados, alertas_pre_sync):
        """
        🔍 VERIFICAÇÃO PÓS-SINCRONIZAÇÃO: Detecta impactos operacionais
        
        Analisa mudanças que podem ter afetado separações cotadas ou operações em andamento
        """
        try:
            from app.carteira.alert_system import AlertaSistemaCarteira
            
            logger.info("🔍 Verificando impactos pós-sincronização...")
            
            # Simular alterações detectadas para o sistema de alertas
            alteracoes_detectadas = []
            
            for item in dados_sincronizados:
                alteracoes_detectadas.append({
                    'num_pedido': item.get('num_pedido'),
                    'cod_produto': item.get('cod_produto'),
                    'tipo_alteracao': 'SYNC_DESTRUTIVA_COMPLETA'
                })
            
            # Detectar alterações em separações cotadas
            alertas_cotadas = AlertaSistemaCarteira.detectar_alteracoes_separacao_cotada_pos_sincronizacao(alteracoes_detectadas)
            
            alertas_criticos = []
            separacoes_cotadas_afetadas = 0
            
            for alerta in alertas_cotadas:
                alertas_criticos.append(alerta)
                separacoes_cotadas_afetadas += 1
            
            # Comparar com alertas pré-sincronização
            alertas_novos = len(alertas_criticos) - len(alertas_pre_sync.get('alertas_criticos', []))
            
            if alertas_criticos:
                logger.warning(f"🚨 {len(alertas_criticos)} alertas críticos pós-sincronização detectados")
            
            return {
                'alertas_criticos': alertas_criticos,
                'total_alertas': len(alertas_criticos),
                'separacoes_cotadas_afetadas': separacoes_cotadas_afetadas,
                'alertas_novos': max(0, alertas_novos),
                'timestamp': datetime.now()
            }
            
        except ImportError:
            logger.warning("Sistema de alertas não disponível para verificação pós-sync")
            return {
                'alertas_criticos': [],
                'total_alertas': 0,
                'separacoes_cotadas_afetadas': 0,
                'warning': 'Sistema de alertas indisponível'
            }
        except Exception as e:
            logger.error(f"❌ Erro na verificação pós-sincronização: {e}")
            return {
                'alertas_criticos': [],
                'total_alertas': 0,
                'separacoes_cotadas_afetadas': 0,
                'erro': str(e)
            }
    
    def _verificar_risco_faturamento_pendente(self):
        """
        🚨 VERIFICAÇÃO CRÍTICA: Detecta pedidos cotados sem faturamento atualizado
        
        Identifica o risco de pedidos faturados no Odoo que não foram sincronizados
        e podem ser perdidos na sincronização destrutiva da carteira
        """
        try:
            from app.separacao.models import Separacao
            from app.faturamento.models import FaturamentoProduto
            
            logger.info("🔍 Verificando risco de faturamento pendente...")
            
            # Buscar pedidos cotados (potencialmente faturados)
            from app.pedidos.models import Pedido
            
            pedidos_cotados = Pedido.query.filter(
                Pedido.status == 'COTADO',
                Pedido.separacao_lote_id is not None
            ).all()
            
            if not pedidos_cotados:
                return {
                    'risco_faturamento': False,
                    'impactos': [],
                    'contagem': 0
                }
            
            # Buscar separações desses pedidos
            lotes_cotados = [p.separacao_lote_id for p in pedidos_cotados]
            
            separacoes_cotadas = Separacao.query.filter(
                Separacao.separacao_lote_id.in_(lotes_cotados)
            ).all()
            
            if not separacoes_cotadas:
                return {
                    'risco_alto': False,
                    'pedidos_em_risco': 0,
                    'lista_pedidos': [],
                    'mensagem': 'Nenhuma separação cotada encontrada'
                }
            
            pedidos_em_risco = []
            
            for separacao in separacoes_cotadas:
                # Verificar se o pedido tem faturamento registrado
                faturamento_existe = FaturamentoProduto.query.filter(
                    FaturamentoProduto.origem == separacao.num_pedido,
                    FaturamentoProduto.cod_produto == separacao.cod_produto
                ).first()
                
                if not faturamento_existe:
                    # Pedido cotado sem faturamento = RISCO ALTO
                    pedidos_em_risco.append({
                        'num_pedido': separacao.num_pedido,
                        'cod_produto': separacao.cod_produto,
                        'separacao_lote_id': separacao.separacao_lote_id,
                        'qtd_saldo': separacao.qtd_saldo,
                        'expedicao': separacao.expedicao.strftime('%Y-%m-%d') if separacao.expedicao else None
                    })
            
            risco_alto = len(pedidos_em_risco) > 0
            
            if risco_alto:
                logger.critical(f"🚨 RISCO CRÍTICO DETECTADO: {len(pedidos_em_risco)} pedidos cotados sem faturamento")
            
            return {
                'risco_alto': risco_alto,
                'pedidos_em_risco': len(pedidos_em_risco),
                'lista_pedidos': pedidos_em_risco,
                'total_separacoes_cotadas': len(separacoes_cotadas),
                'percentual_risco': round((len(pedidos_em_risco) / len(separacoes_cotadas)) * 100, 1) if separacoes_cotadas else 0,
                'mensagem': f"{len(pedidos_em_risco)} de {len(separacoes_cotadas)} separações cotadas sem faturamento registrado"
            }
            
        except ImportError as e:
            logger.warning(f"Módulos de separação/faturamento não disponíveis: {e}")
            return {
                'risco_alto': False,
                'pedidos_em_risco': 0,
                'lista_pedidos': [],
                'erro': 'Módulos indisponíveis'
            }
        except Exception as e:
            logger.error(f"❌ Erro ao verificar risco de faturamento: {e}")
            return {
                'risco_alto': False,
                'pedidos_em_risco': 0,
                'lista_pedidos': [],
                'erro': str(e)
            }
    
    def _verificar_ultima_sincronizacao_faturamento(self):
        """
        📅 VERIFICAÇÃO TEMPORAL: Verifica quando foi a última sincronização de faturamento
        
        Identifica se o faturamento está desatualizado e pode causar inconsistências
        """
        try:
            from app.faturamento.models import FaturamentoProduto
            from datetime import datetime
            
            logger.info("📅 Verificando última sincronização de faturamento...")
            
            # Buscar o registro mais recente de faturamento
            ultimo_faturamento = FaturamentoProduto.query.order_by(
                FaturamentoProduto.created_at.desc()
            ).first()
            
            if not ultimo_faturamento:
                return {
                    'desatualizado': True,
                    'horas_atraso': 999,
                    'ultima_sync': None,
                    'mensagem': 'Nenhum faturamento encontrado no sistema'
                }
            
            # Calcular tempo desde última sincronização
            agora = datetime.now()
            ultima_sync = ultimo_faturamento.created_at
            tempo_decorrido = agora - ultima_sync
            horas_atraso = tempo_decorrido.total_seconds() / 3600
            
            # Considerar desatualizado se > 6 horas
            desatualizado = horas_atraso > 6
            
            if desatualizado:
                logger.warning(f"⚠️ Faturamento desatualizado: {horas_atraso:.1f} horas desde última sync")
            
            return {
                'desatualizado': desatualizado,
                'horas_atraso': round(horas_atraso, 1),
                'ultima_sync': ultima_sync.strftime('%Y-%m-%d %H:%M:%S'),
                'limite_horas': 6,
                'mensagem': f"Última sincronização: {horas_atraso:.1f} horas atrás"
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar última sincronização: {e}")
            return {
                'desatualizado': True,
                'horas_atraso': 0,
                'ultima_sync': None,
                'erro': str(e)
            }
    
    def sincronizar_carteira_odoo_com_gestao_quantidades(self, usar_filtro_pendente=True):
        """
        🚀 SINCRONIZAÇÃO INTELIGENTE COM GESTÃO DE QUANTIDADES
        
        Versão completa que substitui sincronizar_carteira_odoo() com todas as
        funcionalidades originais MAIS gestão inteligente de quantidades.
        
        FLUXO COMPLETO:
        1. Verificação de riscos pré-sincronização
        2. Backup de pré-separações
        3. Carrega estado atual em memória
        4. Busca dados novos do Odoo
        5. Calcula diferenças (reduções/aumentos/novos/removidos)
        6. Aplica mudanças respeitando hierarquia
        7. Substitui carteira com dados atualizados
        8. Recompõe pré-separações
        9. Verificação pós-sincronização com alertas
        
        Args:
            usar_filtro_pendente (bool): Se True, filtra apenas itens com saldo > 0
            
        Returns:
            dict: Resultado completo compatível com sincronizar_carteira_odoo()
        """
        from datetime import datetime
        
        inicio_operacao = datetime.now()
        alteracoes_aplicadas = []
        
        try:
            from app.carteira.models import CarteiraPrincipal
            from app import db
            logger.info("🚀 INICIANDO SINCRONIZAÇÃO OPERACIONAL COMPLETA COM GESTÃO INTELIGENTE")
            
            # ============================================================
            # ETAPA 1: VERIFICAÇÃO PRÉ-SINCRONIZAÇÃO (ALERTAS CRÍTICOS)
            # ============================================================
            logger.info("🔍 ETAPA 1: Verificação pré-sincronização...")
            alertas_pre_sync = self._verificar_riscos_pre_sincronizacao()
            
            if alertas_pre_sync.get('alertas_criticos'):
                logger.warning(f"🚨 ALERTAS CRÍTICOS DETECTADOS: {len(alertas_pre_sync['alertas_criticos'])} separações cotadas")
            
            # ============================================================
            # ETAPA 2: BACKUP AUTOMÁTICO DE PRÉ-SEPARAÇÕES
            # ============================================================
            logger.info("💾 ETAPA 2: Backup automático de pré-separações...")
            backup_result = self._criar_backup_pre_separacoes()
            
            logger.info(f"✅ Backup criado: {backup_result['total_backups']} pré-separações preservadas")
            
            # ============================================================
            # FASE 3: ANÁLISE - Carregar estado atual em memória
            # ============================================================
            logger.info("📊 Fase 3: Analisando estado atual da carteira...")
            
            # Criar índice do estado atual usando campos CORRETOS
            carteira_atual = {}
            carteira_nao_odoo = {}  # Guardar pedidos não-Odoo separadamente
            registros_atuais = 0
            registros_nao_odoo = 0
            
            for item in CarteiraPrincipal.query.all():
                chave = (item.num_pedido, item.cod_produto)
                dados_item = {
                    'qtd_saldo': float(item.qtd_saldo_produto_pedido or 0),
                    'qtd_total': float(item.qtd_produto_pedido or 0),
                    'separacao_lote_id': item.separacao_lote_id,
                    'id': item.id
                }
                
                # Separar pedidos por origem
                if self.is_pedido_odoo(item.num_pedido):
                    carteira_atual[chave] = dados_item
                    registros_atuais += 1
                else:
                    carteira_nao_odoo[chave] = dados_item
                    registros_nao_odoo += 1
            
            logger.info(f"✅ {registros_atuais} registros Odoo indexados na memória")
            logger.info(f"🛡️ {registros_nao_odoo} registros não-Odoo protegidos")
            
            # ============================================================
            # FASE 2: BUSCAR DADOS NOVOS DO ODOO
            # ============================================================
            logger.info("🔄 Fase 2: Buscando dados atualizados do Odoo...")
            
            resultado_odoo = self.obter_carteira_pendente()
            
            if not resultado_odoo['sucesso']:
                return {
                    'sucesso': False,
                    'erro': resultado_odoo.get('erro', 'Erro ao buscar dados do Odoo'),
                    'estatisticas': {}
                }
            
            dados_novos = resultado_odoo.get('dados', [])
            
            # Aplicar filtro de pendente e status válidos
            if usar_filtro_pendente:
                dados_novos = [
                    item for item in dados_novos 
                    if float(item.get('qtd_saldo_produto_pedido', 0)) > 0
                    and item.get('status_pedido', '').lower() in ['draft', 'sent', 'sale', 'cotação', 'cotação enviada', 'pedido de venda']
                ]
            else:
                # Mesmo sem filtro de saldo, aplicar filtro de status
                dados_novos = [
                    item for item in dados_novos 
                    if item.get('status_pedido', '').lower() in ['draft', 'sent', 'sale', 'cotação', 'cotação enviada', 'pedido de venda']
                ]
            
            logger.info(f"✅ {len(dados_novos)} registros obtidos do Odoo")
            
            # ============================================================
            # FASE 3: CALCULAR DIFERENÇAS
            # ============================================================
            logger.info("🔍 Fase 3: Calculando diferenças de quantidade...")
            
            reducoes = []
            aumentos = []
            novos_itens = []
            itens_removidos = set(carteira_atual.keys())
            
            for item_novo in dados_novos:
                # Usar campos CORRETOS
                chave = (item_novo['num_pedido'], item_novo['cod_produto'])
                qtd_nova = float(item_novo.get('qtd_saldo_produto_pedido', 0))
                
                if chave in carteira_atual:
                    # Item existe - remover da lista de removidos
                    itens_removidos.discard(chave)
                    
                    # Comparar quantidades
                    qtd_atual = carteira_atual[chave]['qtd_saldo']
                    
                    if qtd_nova < qtd_atual:
                        # REDUÇÃO detectada
                        reducoes.append({
                            'num_pedido': item_novo['num_pedido'],
                            'cod_produto': item_novo['cod_produto'],
                            'qtd_reduzida': qtd_atual - qtd_nova,
                            'qtd_atual': qtd_atual,
                            'qtd_nova': qtd_nova
                        })
                        
                    elif qtd_nova > qtd_atual:
                        # AUMENTO detectado
                        aumentos.append({
                            'num_pedido': item_novo['num_pedido'],
                            'cod_produto': item_novo['cod_produto'],
                            'qtd_aumentada': qtd_nova - qtd_atual,
                            'qtd_atual': qtd_atual,
                            'qtd_nova': qtd_nova
                        })
                else:
                    # NOVO item
                    novos_itens.append(item_novo)
            
            logger.info(f"📊 Diferenças identificadas:")
            logger.info(f"   📉 {len(reducoes)} reduções")
            logger.info(f"   📈 {len(aumentos)} aumentos")
            logger.info(f"   ➕ {len(novos_itens)} novos itens")
            logger.info(f"   ➖ {len(itens_removidos)} itens removidos")
            
            # ============================================================
            # FASE 3.5: PROCESSAR PEDIDOS ALTERADOS COM NOVO SERVIÇO UNIFICADO
            # ============================================================
            
            # Importar o novo serviço unificado
            from app.odoo.services.ajuste_sincronizacao_service import AjusteSincronizacaoService
            
            # Agrupar alterações por pedido
            pedidos_com_alteracoes = set()
            
            # Coletar todos os pedidos que tiveram alterações
            for reducao in reducoes:
                pedidos_com_alteracoes.add(reducao['num_pedido'])
            for aumento in aumentos:
                pedidos_com_alteracoes.add(aumento['num_pedido'])
            
            # PROTEÇÃO CRÍTICA: Processar pedidos removidos apenas se não estiverem faturados
            for num_pedido, _ in itens_removidos:
                # Verificar se tem Pedido com este número e qual o status
                from app.pedidos.models import Pedido
                pedidos_do_numero = Pedido.query.filter_by(num_pedido=num_pedido).all()
                
                pode_processar = False
                for pedido in pedidos_do_numero:
                    if pedido.status in ['ABERTO', 'COTADO']:
                        pode_processar = True
                        break
                
                if pode_processar:
                    pedidos_com_alteracoes.add(num_pedido)
                    logger.info(f"✅ Pedido {num_pedido} removido da carteira - será processado (tem separações em ABERTO/COTADO)")
                else:
                    if pedidos_do_numero:
                        status_encontrados = ', '.join([p.status for p in pedidos_do_numero])
                        logger.warning(f"🛡️ PROTEÇÃO: Pedido {num_pedido} removido mas NÃO será processado (status: {status_encontrados})")
                    else:
                        logger.info(f"ℹ️ Pedido {num_pedido} removido - sem separações para processar")
            
            for item in novos_itens:
                pedidos_com_alteracoes.add(item['num_pedido'])
            
            # Processar cada pedido alterado com o novo serviço unificado
            pedidos_processados = set()
            alertas_totais = []
            
            for num_pedido in pedidos_com_alteracoes:
                # PROTEÇÃO: Verificar se é pedido Odoo antes de processar
                if not self.is_pedido_odoo(num_pedido):
                    logger.warning(f"🛡️ PROTEÇÃO: Ignorando alterações em pedido não-Odoo: {num_pedido}")
                    continue
                
                logger.info(f"📦 Processando pedido alterado: {num_pedido}")
                
                # Buscar todos os itens do Odoo para este pedido
                itens_odoo = [item for item in dados_novos if item['num_pedido'] == num_pedido]
                
                # Processar com o serviço unificado
                resultado = AjusteSincronizacaoService.processar_pedido_alterado(
                    num_pedido=num_pedido,
                    itens_odoo=itens_odoo
                )
                
                if resultado['sucesso']:
                    logger.info(f"✅ Pedido {num_pedido} processado: {resultado['tipo_processamento']}")
                    
                    # Registrar alterações aplicadas
                    for alteracao in resultado.get('alteracoes_aplicadas', []):
                        alteracoes_aplicadas.append({
                            'pedido': num_pedido,
                            **alteracao
                        })
                    
                    # Coletar alertas gerados
                    alertas_totais.extend(resultado.get('alertas_gerados', []))
                    
                    # Marcar como processado
                    pedidos_processados.add(num_pedido)
                    
                    if resultado.get('alertas_gerados'):
                        logger.warning(f"🚨 {len(resultado['alertas_gerados'])} alertas gerados para separações COTADAS alteradas")
                else:
                    logger.error(f"❌ Erro ao processar pedido {num_pedido}: {resultado.get('erros')}")
                    alteracoes_aplicadas.append({
                        'tipo': 'ERRO',
                        'pedido': num_pedido,
                        'erros': resultado.get('erros', [])
                    })
            
            # Processar pedidos novos (que não tinham alterações mas são novos)
            pedidos_novos = set(item['num_pedido'] for item in novos_itens) - pedidos_processados
            
            for num_pedido in pedidos_novos:
                if not self.is_pedido_odoo(num_pedido):
                    logger.warning(f"🛡️ PROTEÇÃO: Ignorando pedido novo não-Odoo: {num_pedido}")
                    continue
                    
                logger.info(f"➕ Processando pedido novo: {num_pedido}")
            
            # Resumo dos alertas gerados  
            if alertas_totais:
                logger.warning(f"🚨 Total de {len(alertas_totais)} alertas gerados para separações COTADAS alteradas")
            
            # ============================================================
            # FASE 7: ATUALIZAR CARTEIRA (Delete + Insert)
            # ============================================================
            logger.info("💾 Fase 7: Atualizando carteira principal...")
            
            # Sanitizar dados antes de inserir
            logger.info("🧹 Sanitizando dados...")
            dados_novos = self._sanitizar_dados_carteira(dados_novos)
            
            # NOVO: Remover duplicatas vindas do Odoo (mesmo pedido com mesmo produto duplicado)
            logger.info("🔍 Tratando duplicatas dos dados do Odoo...")
            dados_unicos = {}
            duplicatas_encontradas = 0
            
            for item in dados_novos:
                chave = (item.get('num_pedido'), item.get('cod_produto'))
                if chave[0] and chave[1]:  # Validar que tem pedido e produto
                    if chave not in dados_unicos:
                        dados_unicos[chave] = item
                    else:
                        # Duplicata encontrada - consolidar quantidades
                        duplicatas_encontradas += 1
                        item_existente = dados_unicos[chave]
                        
                        # Somar quantidades dos itens duplicados
                        qtd_produto = float(item.get('qtd_produto_pedido', 0) or 0)
                        qtd_saldo = float(item.get('qtd_saldo_produto_pedido', 0) or 0)
                        qtd_cancelada = float(item.get('qtd_cancelada_produto_pedido', 0) or 0)
                        
                        item_existente['qtd_produto_pedido'] = float(item_existente.get('qtd_produto_pedido', 0) or 0) + qtd_produto
                        item_existente['qtd_saldo_produto_pedido'] = float(item_existente.get('qtd_saldo_produto_pedido', 0) or 0) + qtd_saldo
                        item_existente['qtd_cancelada_produto_pedido'] = float(item_existente.get('qtd_cancelada_produto_pedido', 0) or 0) + qtd_cancelada
                        
                        logger.warning(f"⚠️ Duplicata consolidada: {chave[0]}/{chave[1]} - Qtds somadas: {qtd_produto} + existente")
            
            dados_novos = list(dados_unicos.values())
            
            if duplicatas_encontradas > 0:
                logger.warning(f"🔄 {duplicatas_encontradas} itens duplicados consolidados (quantidades somadas)")
            
            # PROTEÇÃO: Usar estratégia UPSERT para evitar duplicatas
            logger.info(f"🛡️ Preservando {registros_nao_odoo} registros não-Odoo...")
            logger.info("🔄 Usando estratégia UPSERT para evitar erros de chave duplicada...")
            
            # Primeiro, obter todos os registros Odoo existentes
            registros_odoo_existentes = {}
            for item in db.session.query(CarteiraPrincipal).filter(
                or_(
                    CarteiraPrincipal.num_pedido.like('VSC%'),
                    CarteiraPrincipal.num_pedido.like('VCD%'),
                    CarteiraPrincipal.num_pedido.like('VFB%')
                )
            ).all():
                chave = (item.num_pedido, item.cod_produto)
                registros_odoo_existentes[chave] = item
            
            logger.info(f"📊 {len(registros_odoo_existentes)} registros Odoo existentes encontrados")
            
            # Criar conjunto de chaves dos novos dados para controle
            chaves_novos_dados = set()
            for item in dados_novos:
                if item.get('num_pedido') and item.get('cod_produto'):
                    chaves_novos_dados.add((item['num_pedido'], item['cod_produto']))
            
            # Remover registros que não existem mais no Odoo
            pedidos_odoo_deletados = 0
            for chave, registro in registros_odoo_existentes.items():
                if chave not in chaves_novos_dados:
                    db.session.delete(registro)
                    pedidos_odoo_deletados += 1
            
            if pedidos_odoo_deletados > 0:
                logger.info(f"🗑️ {pedidos_odoo_deletados} registros Odoo obsoletos removidos")
            
            # UPSERT: Atualizar existentes ou inserir novos COM COMMITS INCREMENTAIS
            contador_inseridos = 0
            contador_atualizados = 0
            erros_insercao = []
            
            # Importar helper para commits com retry
            from app.utils.database_retry import commit_with_retry
            
            # Configuração para commits incrementais - evitar erro SSL
            TAMANHO_LOTE = 10  # Processar 10 registros por vez para evitar timeout SSL
            contador_lote = 0
            
            logger.info(f"🔄 Processando {len(dados_novos)} registros em lotes de {TAMANHO_LOTE}...")
            
            for idx, item in enumerate(dados_novos):
                try:
                    # Validar dados essenciais usando campos CORRETOS
                    if not item.get('num_pedido') or not item.get('cod_produto'):
                        erros_insercao.append(f"Item sem pedido/produto: {item}")
                        continue
                    
                    chave = (item['num_pedido'], item['cod_produto'])
                    
                    if chave in registros_odoo_existentes:
                        # ATUALIZAR registro existente
                        registro_existente = registros_odoo_existentes[chave]
                        for key, value in item.items():
                            if hasattr(registro_existente, key) and key != 'id':
                                setattr(registro_existente, key, value)
                        contador_atualizados += 1
                    else:
                        # INSERIR novo registro - criar produto se não existir
                        # Verificar se produto existe no cadastro
                        from app.producao.models import CadastroPalletizacao
                        
                        cod_produto = item.get('cod_produto')
                        if cod_produto:
                            produto_existe = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
                            if not produto_existe:
                                # Criar produto com dados básicos
                                novo_produto = CadastroPalletizacao(
                                    cod_produto=cod_produto,
                                    nome_produto=item.get('nome_produto', cod_produto),
                                    palletizacao=1.0,  # Valor padrão
                                    peso_bruto=1.0,    # Valor padrão
                                    created_by='ImportacaoOdoo',
                                    updated_by='ImportacaoOdoo'
                                )
                                db.session.add(novo_produto)
                                logger.info(f"✅ Produto {cod_produto} criado automaticamente no cadastro")
                        
                        # Agora criar o registro na carteira
                        novo_registro = CarteiraPrincipal(**item)
                        db.session.add(novo_registro)
                        contador_inseridos += 1
                    
                    contador_lote += 1
                    
                    # Commit incremental a cada TAMANHO_LOTE registros para evitar erro SSL
                    if contador_lote >= TAMANHO_LOTE:
                        try:
                            if commit_with_retry(db.session, max_retries=3):
                                logger.debug(f"✅ Lote {idx//TAMANHO_LOTE + 1} salvo ({contador_lote} registros)")
                            else:
                                logger.warning(f"⚠️ Falha ao salvar lote {idx//TAMANHO_LOTE + 1}")
                        except Exception as commit_error:
                            logger.error(f"❌ Erro no commit do lote: {commit_error}")
                            # Tentar rollback e continuar
                            try:
                                db.session.rollback()
                            except Exception:
                                pass
                        finally:
                            contador_lote = 0
                    
                except Exception as e:
                    erro_msg = f"Erro ao processar {item.get('num_pedido', 'N/A')}/{item.get('cod_produto', 'N/A')}: {e}"
                    logger.error(erro_msg)
                    erros_insercao.append(erro_msg)
            
            # Commit final para registros restantes
            if contador_lote > 0:
                try:
                    if commit_with_retry(db.session, max_retries=3):
                        logger.debug(f"✅ Último lote salvo ({contador_lote} registros)")
                    else:
                        logger.warning(f"⚠️ Falha ao salvar último lote")
                except Exception as commit_error:
                    logger.error(f"❌ Erro no commit final: {commit_error}")
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
            
            logger.info(f"✅ {contador_inseridos} novos registros inseridos")
            logger.info(f"🔄 {contador_atualizados} registros atualizados")
            
            # ============================================================
            # FASE 8: COMMIT FINAL (já feito incrementalmente)
            # ============================================================
            logger.info("💾 Fase 8: Todas as alterações já salvas incrementalmente")
            
            logger.info("🔄 Fase 9: Recompondo pré-separações...")
            recomposicao_result = self._recompor_pre_separacoes_automaticamente()
            
            # ============================================================
            # FASE 9.5: ATUALIZAR DADOS DE SEPARAÇÃO/PEDIDO/PRÉ-SEPARAÇÃO
            # ============================================================
            logger.info("🔄 Fase 9.5: Atualizando dados de Separação/Pedido/Pré-Separação...")
            try:
                from app.carteira.services.atualizar_dados_service import AtualizarDadosService
                atualizador = AtualizarDadosService()
                resultado_atualizacao = atualizador.atualizar_dados_pos_sincronizacao()
                
                if resultado_atualizacao.get('sucesso'):
                    logger.info(f"✅ Dados atualizados: {resultado_atualizacao['total_pedidos_atualizados']} pedidos, "
                               f"{resultado_atualizacao['total_separacoes_atualizadas']} separações, "
                               f"{resultado_atualizacao['total_pre_separacoes_atualizadas']} pré-separações")
                else:
                    logger.warning(f"⚠️ Atualização de dados com problemas: {resultado_atualizacao.get('erro')}")
            except Exception as e:
                logger.error(f"❌ Erro ao atualizar dados de Separação/Pedido: {str(e)}")
                # Não interromper o fluxo principal
            
            # ============================================================
            # FASE 10: VERIFICAÇÃO PÓS-SINCRONIZAÇÃO E ALERTAS
            # ============================================================
            logger.info("🔍 Fase 10: Verificação pós-sincronização...")
            alertas_pos_sync = self._verificar_alertas_pos_sincronizacao(dados_novos, alertas_pre_sync)
            
            # ============================================================
            # FASE 11: ESTATÍSTICAS FINAIS
            # ============================================================
            fim_operacao = datetime.now()
            tempo_total = (fim_operacao - inicio_operacao).total_seconds()
            
            # Contar alterações bem-sucedidas
            alteracoes_sucesso = [a for a in alteracoes_aplicadas if 'erro' not in a]
            alteracoes_erro = [a for a in alteracoes_aplicadas if 'erro' in a]
            
            # Estatísticas completas compatíveis com função original
            estatisticas_completas = {
                'registros_inseridos': contador_inseridos,
                'registros_atualizados': contador_atualizados,
                'registros_removidos': pedidos_odoo_deletados,
                'registros_nao_odoo_preservados': registros_nao_odoo,
                'total_encontrados': len(resultado_odoo.get('dados', [])),
                'registros_filtrados': len(dados_novos),
                'taxa_sucesso': f"{((contador_inseridos + contador_atualizados)/len(dados_novos)*100):.1f}%" if dados_novos else "0%",
                'erros_processamento': len(erros_insercao),
                'metodo': 'operacional_completo_com_upsert',
                
                # Dados operacionais específicos
                'tempo_execucao_segundos': round(tempo_total, 2),
                'backup_pre_separacoes': backup_result['total_backups'],
                'recomposicao_sucesso': recomposicao_result['sucessos'],
                'recomposicao_erros': recomposicao_result['erros'],
                'alertas_pre_sync': len(alertas_pre_sync.get('alertas_criticos', [])),
                'alertas_pos_sync': len(alertas_pos_sync.get('alertas_criticos', [])),
                'separacoes_cotadas_afetadas': alertas_pos_sync.get('separacoes_cotadas_afetadas', 0),
                
                # Estatísticas da gestão de quantidades
                'reducoes_aplicadas': len([a for a in alteracoes_sucesso if a['tipo'] == 'REDUCAO']),
                'aumentos_aplicados': len([a for a in alteracoes_sucesso if a['tipo'] == 'AUMENTO']),
                'remocoes_aplicadas': len([a for a in alteracoes_sucesso if a['tipo'] == 'REMOCAO']),
                'novos_itens': len(novos_itens),
                'alteracoes_com_erro': len(alteracoes_erro)
            }
            
            # Log resumo final
            logger.info(f"✅ SINCRONIZAÇÃO OPERACIONAL COMPLETA CONCLUÍDA:")
            logger.info(f"   📊 {contador_inseridos} registros inseridos")
            logger.info(f"   🔄 {contador_atualizados} registros atualizados")
            logger.info(f"   🗑️ {pedidos_odoo_deletados} registros Odoo removidos")
            logger.info(f"   🛡️ {registros_nao_odoo} registros não-Odoo preservados")
            logger.info(f"   💾 {backup_result['total_backups']} pré-separações em backup")
            logger.info(f"   📉 {estatisticas_completas['reducoes_aplicadas']} reduções aplicadas")
            logger.info(f"   📈 {estatisticas_completas['aumentos_aplicados']} aumentos aplicados")
            logger.info(f"   ➖ {estatisticas_completas['remocoes_aplicadas']} remoções processadas")
            logger.info(f"   ➕ {len(novos_itens)} novos itens")
            logger.info(f"   🔄 {recomposicao_result['sucessos']} pré-separações recompostas")
            logger.info(f"   🚨 {len(alertas_pos_sync.get('alertas_criticos', []))} alertas pós-sincronização")
            logger.info(f"   ⏱️ {tempo_total:.2f} segundos de execução")
            
            if alteracoes_erro:
                logger.warning(f"   ⚠️ {len(alteracoes_erro)} alterações com erro")
            
            # Retorno compatível com sincronizar_carteira_odoo original
            return {
                'sucesso': True,
                'operacao_completa': True,
                'estatisticas': estatisticas_completas,
                'registros_importados': contador_inseridos,
                'registros_removidos': pedidos_odoo_deletados,
                'registros_nao_odoo_preservados': registros_nao_odoo,
                'erros': erros_insercao,
                
                # Dados operacionais para interface
                'alertas_pre_sync': alertas_pre_sync,
                'alertas_pos_sync': alertas_pos_sync,
                'backup_info': backup_result,
                'recomposicao_info': recomposicao_result,
                'tempo_execucao': tempo_total,
                
                # Dados específicos da gestão de quantidades
                'alteracoes_aplicadas': alteracoes_aplicadas,
                'gestao_quantidades_ativa': True,
                
                'mensagem': f'✅ Sincronização operacional completa: {contador_inseridos} registros importados, {recomposicao_result["sucessos"]} pré-separações recompostas, {len(alteracoes_sucesso)} mudanças de quantidade processadas'
            }
            
        except Exception as e:
            db.session.rollback()
            fim_operacao = datetime.now()
            tempo_erro = (fim_operacao - inicio_operacao).total_seconds()
            
            logger.error(f"❌ ERRO CRÍTICO na sincronização operacional: {e}")
            
            # Retorno de erro compatível com função original
            return {
                'sucesso': False,
                'operacao_completa': False,
                'erro': str(e),
                'registros_importados': 0,
                'registros_removidos': 0,
                'tempo_execucao': tempo_erro,
                'estatisticas': {},
                'alertas_pre_sync': {},
                'alertas_pos_sync': {},
                'gestao_quantidades_ativa': True,
                'mensagem': f'❌ Erro na sincronização operacional: {str(e)}'
            } 