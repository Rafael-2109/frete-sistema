"""
Serviço de Pedidos de Compras - VERSÃO OTIMIZADA
=================================================

OTIMIZAÇÕES IMPLEMENTADAS:
1. ✅ Batch loading de linhas (1 query em vez de N)
2. ✅ Batch loading de produtos (1 query em vez de N*M)
3. ✅ Cache de pedidos existentes em memória (1 query em vez de N*M)

PERFORMANCE:
- Antes: ~2.000 queries para 100 pedidos com 5 linhas
- Depois: ~4 queries para 100 pedidos com 5 linhas

Redução: 99.8% 🚀

Autor: Sistema de Fretes
Data: 01/11/2025
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from decimal import Decimal
from collections import defaultdict

from app import db
from app.manufatura.models import PedidoCompras
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class PedidoComprasServiceOtimizado:
    """
    Serviço OTIMIZADO para integração de pedidos de compras com Odoo
    """

    # Mapeamento de status Odoo → Sistema
    MAPA_STATUS = {
        'draft': 'Rascunho',
        'sent': 'Enviado',
        'to approve': 'Aguardando Aprovação',
        'purchase': 'Aprovado',
        'done': 'Concluído',
        'cancel': 'Cancelado',
    }

    # ✅ TIPOS DE PEDIDO RELEVANTES (apenas materiais armazenáveis)
    # Exclui: transferências, remessas, serviços (exceto industrialização), operações temporárias
    TIPOS_RELEVANTES = {
        'compra',                   # Compra normal - PRINCIPAL
        'importacao',               # Importação
        'comp-importacao',          # Complementar de importação
        'devolucao',                # Devolução de cliente
        'devolucao_compra',         # Devolução de venda
        'industrializacao',         # Retorno de industrialização
        'serv-industrializacao',    # Serviço de industrialização (produção terceirizada)
        'ent-bonificacao',          # Bonificação (brinde)
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connection = get_odoo_connection()

    def sincronizar_pedidos_incremental(
        self,
        minutos_janela: int = 90,
        primeira_execucao: bool = False
    ) -> Dict[str, Any]:
        """
        Sincroniza pedidos de compras do Odoo de forma incremental e OTIMIZADA

        Args:
            minutos_janela: Janela de tempo para buscar alterações (padrão: 90 minutos)
            primeira_execucao: Se True, importa tudo; se False, apenas alterações

        Returns:
            Dict com resultado da sincronização
        """
        inicio = datetime.now()
        self.logger.info("=" * 80)
        self.logger.info(f"🚀 SINCRONIZAÇÃO PEDIDOS DE COMPRA - {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"   Janela: {minutos_janela} minutos")
        self.logger.info(f"   Primeira execução: {primeira_execucao}")
        self.logger.info("=" * 80)

        try:
            # Autenticar no Odoo
            uid = self.connection.authenticate()
            if not uid:
                raise Exception("Falha na autenticação com Odoo")

            # PASSO 1: Buscar pedidos alterados
            pedidos_odoo = self._buscar_pedidos_odoo(minutos_janela, primeira_execucao)

            if not pedidos_odoo:
                self.logger.info("✅ Nenhum pedido novo ou alterado encontrado")
                return {
                    'sucesso': True,
                    'pedidos_novos': 0,
                    'pedidos_atualizados': 0,
                    'linhas_processadas': 0,
                    'linhas_ignoradas': 0,
                    'tempo_execucao': (datetime.now() - inicio).total_seconds()
                }

            # PASSO 2: 🚀 BATCH LOADING de todas as linhas (1 query)
            todas_linhas = self._buscar_todas_linhas_batch(pedidos_odoo)

            # PASSO 3: 🚀 BATCH LOADING de todos os produtos (1 query)
            produtos_cache = self._buscar_todos_produtos_batch(todas_linhas)

            # PASSO 4: 🚀 CACHE de pedidos existentes (1 query)
            pedidos_existentes_cache = self._carregar_pedidos_existentes()

            # PASSO 5: Processar pedidos com cache
            resultado = self._processar_pedidos_otimizado(
                pedidos_odoo,
                todas_linhas,
                produtos_cache,
                pedidos_existentes_cache
            )

            # PASSO 6: 🗑️ Detectar pedidos EXCLUÍDOS do Odoo (marcar como cancelados)
            pedidos_cancelados_exclusao = self._detectar_pedidos_excluidos(
                pedidos_odoo,
                minutos_janela
            )
            resultado['pedidos_cancelados_exclusao'] = pedidos_cancelados_exclusao

            # Commit final
            db.session.commit()

            tempo_total = (datetime.now() - inicio).total_seconds()
            self.logger.info("=" * 80)
            self.logger.info(f"✅ SINCRONIZAÇÃO CONCLUÍDA EM {tempo_total:.2f}s")
            self.logger.info(f"   Pedidos novos: {resultado['pedidos_novos']}")
            self.logger.info(f"   Pedidos atualizados: {resultado['pedidos_atualizados']}")
            self.logger.info(f"   Pedidos cancelados (exclusão): {resultado['pedidos_cancelados_exclusao']}")
            self.logger.info(f"   Linhas processadas: {resultado['linhas_processadas']}")
            self.logger.info(f"   Linhas ignoradas: {resultado['linhas_ignoradas']}")
            self.logger.info("=" * 80)

            return {
                'sucesso': True,
                **resultado,
                'tempo_execucao': tempo_total
            }

        except Exception as e:
            db.session.rollback()
            self.logger.error(f"❌ Erro na sincronização: {e}")
            import traceback
            traceback.print_exc()

            return {
                'sucesso': False,
                'erro': str(e),
                'tempo_execucao': (datetime.now() - inicio).total_seconds()
            }

    def _buscar_pedidos_odoo(
        self,
        minutos_janela: int,
        primeira_execucao: bool
    ) -> List[Dict]:
        """
        Busca pedidos de compra do Odoo com filtro de data

        SEMPRE aplica filtro de janela temporal para evitar buscar
        todo o histórico do Odoo (causa timeout SSL)
        """
        self.logger.info("🔍 Buscando pedidos de compra no Odoo...")

        # Calcular data limite baseado na janela
        data_limite = (datetime.now() - timedelta(minutes=minutos_janela)).strftime('%Y-%m-%d %H:%M:%S')

        # ✅ IMPORTAR TODOS (incluindo cancelados) para sincronizar status
        # Filtro: (create_date OR write_date >= data_limite)
        filtro = [
            '|',
            ['create_date', '>=', data_limite],
            ['write_date', '>=', data_limite]
        ]

        self.logger.info(f"   Filtro: create_date OU write_date >= {data_limite} (incluindo cancelados)")

        campos_pedido = [
            'id', 'name', 'state', 'create_date', 'write_date',
            'date_order', 'date_planned', 'partner_id', 'company_id',
            'order_line', 'currency_id', 'amount_total', 'notes',
            'l10n_br_tipo_pedido'  # ✅ ADICIONADO: Tipo de pedido (Brasil)
        ]

        pedidos = self.connection.search_read(
            'purchase.order',
            filtro,
            campos_pedido
        )

        self.logger.info(f"✅ Encontrados {len(pedidos)} pedidos")

        return pedidos

    def _buscar_todas_linhas_batch(self, pedidos_odoo: List[Dict]) -> Dict[int, List[Dict]]:
        """
        🚀 OTIMIZAÇÃO 1: Busca TODAS as linhas de TODOS os pedidos em 1 query

        Args:
            pedidos_odoo: Lista de pedidos

        Returns:
            Dict mapeando pedido_id -> lista de linhas
        """
        self.logger.info("🚀 Carregando TODAS as linhas em batch...")

        # Coletar todos os IDs de linhas
        todos_line_ids = []
        for pedido in pedidos_odoo:
            if pedido.get('order_line'):
                todos_line_ids.extend(pedido['order_line'])

        if not todos_line_ids:
            self.logger.info("   ⚠️  Nenhuma linha encontrada")
            return {}

        # 🚀 UMA ÚNICA QUERY para buscar TODAS as linhas
        self.logger.info(f"   Buscando {len(todos_line_ids)} linhas em 1 query...")
        todas_linhas = self.connection.read(
            'purchase.order.line',
            todos_line_ids,
            fields=[
                'id', 'order_id', 'product_id', 'name',
                'product_qty', 'qty_received', 'product_uom', 'date_planned',  # ✅ ADICIONADO qty_received
                'price_unit', 'price_subtotal', 'price_total',
                'taxes_id', 'state'
            ]
        )

        # Agrupar linhas por pedido
        linhas_por_pedido = defaultdict(list)
        for linha in todas_linhas:
            pedido_id = linha['order_id'][0] if linha.get('order_id') else None
            if pedido_id:
                linhas_por_pedido[pedido_id].append(linha)

        self.logger.info(f"   ✅ {len(todas_linhas)} linhas carregadas")

        return linhas_por_pedido

    def _buscar_todos_produtos_batch(self, linhas_por_pedido: Dict[int, List[Dict]]) -> Dict[int, Dict]:
        """
        🚀 OTIMIZAÇÃO 2: Busca TODOS os produtos em 1 query

        Args:
            linhas_por_pedido: Dict de linhas agrupadas

        Returns:
            Dict mapeando product_id -> dados do produto
        """
        self.logger.info("🚀 Carregando TODOS os produtos em batch...")

        # Coletar todos os IDs de produtos ÚNICOS
        product_ids_set: Set[int] = set()
        for linhas in linhas_por_pedido.values():
            for linha in linhas:
                if linha.get('product_id'):
                    product_ids_set.add(linha['product_id'][0])

        if not product_ids_set:
            self.logger.info("   ⚠️  Nenhum produto encontrado")
            return {}

        product_ids = list(product_ids_set)

        # 🚀 UMA ÚNICA QUERY para buscar TODOS os produtos
        self.logger.info(f"   Buscando {len(product_ids)} produtos em 1 query...")
        todos_produtos = self.connection.read(
            'product.product',
            product_ids,
            fields=['id', 'default_code', 'name', 'detailed_type']
        )

        # Criar dicionário de cache
        produtos_cache = {produto['id']: produto for produto in todos_produtos}

        self.logger.info(f"   ✅ {len(produtos_cache)} produtos carregados")

        return produtos_cache

    def _carregar_pedidos_existentes(self) -> Dict[str, PedidoCompras]:
        """
        🚀 OTIMIZAÇÃO 3: Carrega TODOS os pedidos existentes em 1 query

        Returns:
            Dict com múltiplos índices para busca rápida
        """
        self.logger.info("🚀 Carregando pedidos existentes em batch...")

        # 🚀 UMA ÚNICA QUERY para carregar TODOS
        todos_pedidos = PedidoCompras.query.filter_by(
            importado_odoo=True
        ).all()

        # ✅ CORRIGIDO: Criar índice por chave composta (num_pedido, cod_produto)
        cache = {
            'por_odoo_id': {},           # odoo_id -> PedidoCompras (para compatibilidade)
            'por_chave_composta': {}     # "num_pedido|cod_produto" -> PedidoCompras
        }

        for pedido in todos_pedidos:
            if pedido.odoo_id:
                cache['por_odoo_id'][pedido.odoo_id] = pedido
            # Criar chave composta usando constraint real do banco
            chave = f"{pedido.num_pedido}|{pedido.cod_produto}"
            cache['por_chave_composta'][chave] = pedido

        self.logger.info(f"   ✅ {len(todos_pedidos)} pedidos carregados em memória")

        return cache

    def _processar_pedidos_otimizado(
        self,
        pedidos_odoo: List[Dict],
        linhas_por_pedido: Dict[int, List[Dict]],
        produtos_cache: Dict[int, Dict],
        pedidos_existentes_cache: Dict[str, Dict]
    ) -> Dict[str, int]:
        """
        Processa pedidos usando CACHE (sem queries adicionais)
        """
        pedidos_novos = 0
        pedidos_atualizados = 0
        linhas_processadas = 0
        linhas_ignoradas = 0

        for pedido_odoo in pedidos_odoo:
            try:
                self.logger.info(f"📋 Processando pedido {pedido_odoo['name']}...")

                # Buscar linhas no CACHE
                linhas_odoo = linhas_por_pedido.get(pedido_odoo['id'], [])

                if not linhas_odoo:
                    self.logger.warning(f"   Pedido {pedido_odoo['name']} sem linhas - IGNORADO")
                    continue

                # Processar cada linha usando CACHE
                for linha_odoo in linhas_odoo:
                    try:
                        resultado_linha = self._processar_linha_otimizada(
                            pedido_odoo,
                            linha_odoo,
                            produtos_cache,
                            pedidos_existentes_cache
                        )

                        if resultado_linha['processado']:
                            linhas_processadas += 1
                            if resultado_linha['nova']:
                                pedidos_novos += 1
                            elif resultado_linha['atualizada']:
                                pedidos_atualizados += 1
                        else:
                            linhas_ignoradas += 1

                    except Exception as e_linha:
                        db.session.rollback()
                        self.logger.error(f"❌ Erro ao processar linha {linha_odoo.get('id')}: {e_linha}")
                        linhas_ignoradas += 1
                        continue

            except Exception as e:
                db.session.rollback()
                self.logger.error(f"❌ Erro ao processar pedido {pedido_odoo.get('name')}: {e}")
                continue

        return {
            'pedidos_novos': pedidos_novos,
            'pedidos_atualizados': pedidos_atualizados,
            'linhas_processadas': linhas_processadas,
            'linhas_ignoradas': linhas_ignoradas
        }

    def _processar_linha_otimizada(
        self,
        pedido_odoo: Dict,
        linha_odoo: Dict,
        produtos_cache: Dict[int, Dict],
        pedidos_existentes_cache: Dict[str, Dict]
    ) -> Dict[str, bool]:
        """
        Processa uma linha de pedido usando CACHE (SEM queries adicionais)
        """
        try:
            # ✅ PASSO 0: Verificar tipo de pedido (filtrar apenas relevantes)
            tipo_pedido = pedido_odoo.get('l10n_br_tipo_pedido')

            if tipo_pedido and tipo_pedido not in self.TIPOS_RELEVANTES:
                self.logger.info(
                    f"   Pedido {pedido_odoo['name']} tipo '{tipo_pedido}' "
                    f"não é relevante para estoque - IGNORADA"
                )
                return {'processado': False, 'nova': False, 'atualizada': False}

            # PASSO 1: Buscar produto no CACHE
            product_id_odoo = linha_odoo['product_id'][0] if linha_odoo.get('product_id') else None

            if not product_id_odoo:
                self.logger.warning(f"   Linha {linha_odoo['id']} sem product_id - IGNORADA")
                return {'processado': False, 'nova': False, 'atualizada': False}

            # 🚀 Busca no CACHE em vez de query
            produto_odoo = produtos_cache.get(product_id_odoo)

            if not produto_odoo:
                self.logger.warning(f"   Produto {product_id_odoo} não encontrado no cache - IGNORADA")
                return {'processado': False, 'nova': False, 'atualizada': False}

            # Validar detailed_type
            if produto_odoo.get('detailed_type') != 'product':
                self.logger.info(
                    f"   Produto {product_id_odoo} não é armazenável "
                    f"(detailed_type={produto_odoo.get('detailed_type')}) - IGNORADA"
                )
                return {'processado': False, 'nova': False, 'atualizada': False}

            cod_produto = produto_odoo.get('default_code')
            if not cod_produto:
                self.logger.warning(f"   Produto {product_id_odoo} sem default_code - IGNORADA")
                return {'processado': False, 'nova': False, 'atualizada': False}

            # PASSO 2: Verificar se já existe no CACHE
            # ✅ CORRIGIDO: Usar ID do PEDIDO + cod_produto (constraint real)
            odoo_id_pedido = str(pedido_odoo['id'])
            num_pedido = pedido_odoo['name']

            # Criar chave composta para busca
            chave_composta = f"{num_pedido}|{cod_produto}"

            # 🚀 Busca no CACHE por chave composta
            pedido_existente = pedidos_existentes_cache['por_chave_composta'].get(chave_composta)

            if pedido_existente:
                # ATUALIZAR
                atualizada = self._atualizar_pedido(
                    pedido_existente,
                    pedido_odoo,
                    linha_odoo,
                    produto_odoo
                )
                return {'processado': True, 'nova': False, 'atualizada': atualizada}
            else:
                # CRIAR NOVO
                novo_pedido = self._criar_pedido(pedido_odoo, linha_odoo, produto_odoo)

                # 🚀 Atualizar CACHE com novo pedido usando chave composta
                if novo_pedido.odoo_id:
                    pedidos_existentes_cache['por_odoo_id'][novo_pedido.odoo_id] = novo_pedido
                chave_nova = f"{novo_pedido.num_pedido}|{novo_pedido.cod_produto}"
                pedidos_existentes_cache['por_chave_composta'][chave_nova] = novo_pedido

                return {'processado': True, 'nova': True, 'atualizada': False}

        except Exception as e:
            self.logger.error(f"❌ Erro ao processar linha {linha_odoo.get('id')}: {e}")
            return {'processado': False, 'nova': False, 'atualizada': False}

    def _criar_pedido(
        self,
        pedido_odoo: Dict,
        linha_odoo: Dict,
        produto_odoo: Dict
    ) -> PedidoCompras:
        """
        Cria um novo pedido de compra
        """
        # Extrair dados do fornecedor
        partner_id = pedido_odoo.get('partner_id')
        cnpj_fornecedor = None
        raz_social = None

        if partner_id:
            # TODO: Buscar CNPJ do fornecedor (cache de parceiros)
            raz_social = partner_id[1] if len(partner_id) > 1 else None

        # Converter datas
        data_pedido_criacao = None
        if pedido_odoo.get('date_order'):
            data_pedido_criacao = datetime.strptime(
                pedido_odoo['date_order'], '%Y-%m-%d %H:%M:%S'
            ).date()

        data_pedido_previsao = None
        if linha_odoo.get('date_planned'):
            data_pedido_previsao = datetime.strptime(
                linha_odoo['date_planned'], '%Y-%m-%d %H:%M:%S'
            ).date()

        # Criar objeto
        novo_pedido = PedidoCompras(
            # Identificação
            num_pedido=pedido_odoo['name'],
            odoo_id=str(linha_odoo['id']),

            # Fornecedor
            cnpj_fornecedor=cnpj_fornecedor,
            raz_social=raz_social,

            # Produto
            cod_produto=produto_odoo['default_code'],
            nome_produto=produto_odoo['name'],

            # Quantidades e preços
            qtd_produto_pedido=Decimal(str(linha_odoo.get('product_qty', 0))),
            qtd_recebida=Decimal(str(linha_odoo.get('qty_received', 0))),  # ✅ NOVO
            preco_produto_pedido=Decimal(str(linha_odoo.get('price_unit', 0))),

            # Datas
            data_pedido_criacao=data_pedido_criacao,
            data_pedido_previsao=data_pedido_previsao,

            # Status do Odoo (✅ NOVO)
            status_odoo=pedido_odoo.get('state'),

            # ✅ Tipo de pedido (l10n_br_tipo_pedido)
            tipo_pedido=pedido_odoo.get('l10n_br_tipo_pedido'),

            # Controle
            importado_odoo=True
        )

        db.session.add(novo_pedido)
        db.session.flush()

        self.logger.info(f"   ✅ Criado: {novo_pedido.num_pedido} - {novo_pedido.cod_produto}")

        return novo_pedido

    def _atualizar_pedido(
        self,
        pedido_existente: PedidoCompras,
        pedido_odoo: Dict,
        linha_odoo: Dict,
        produto_odoo: Dict
    ) -> bool:
        """
        Atualiza um pedido existente se houver mudanças
        """
        alterado = False

        # Verificar mudanças em quantidade
        nova_qtd = Decimal(str(linha_odoo.get('product_qty', 0)))
        if pedido_existente.qtd_produto_pedido != nova_qtd:
            pedido_existente.qtd_produto_pedido = nova_qtd
            alterado = True

        # ✅ Verificar mudanças em quantidade recebida
        nova_qtd_recebida = Decimal(str(linha_odoo.get('qty_received', 0)))
        if pedido_existente.qtd_recebida != nova_qtd_recebida:
            pedido_existente.qtd_recebida = nova_qtd_recebida
            alterado = True

        # Verificar mudanças em preço
        novo_preco = Decimal(str(linha_odoo.get('price_unit', 0)))
        if pedido_existente.preco_produto_pedido != novo_preco:
            pedido_existente.preco_produto_pedido = novo_preco
            alterado = True

        # ✅ Verificar mudança de status (incluindo cancelamento)
        novo_status = pedido_odoo.get('state')
        if pedido_existente.status_odoo != novo_status:
            pedido_existente.status_odoo = novo_status
            alterado = True
            if novo_status == 'cancel':
                self.logger.warning(f"   ⚠️  Pedido {pedido_existente.num_pedido} CANCELADO no Odoo")

        # ✅ Verificar mudança de tipo de pedido
        novo_tipo = pedido_odoo.get('l10n_br_tipo_pedido')
        if pedido_existente.tipo_pedido != novo_tipo:
            pedido_existente.tipo_pedido = novo_tipo
            alterado = True

        if alterado:
            db.session.flush()
            self.logger.info(f"   ✅ Atualizado: {pedido_existente.num_pedido}")

        return alterado

    def _detectar_pedidos_excluidos(
        self,
        pedidos_odoo: List[Dict],
        minutos_janela: int
    ) -> int:
        """
        Detecta pedidos que existem no sistema mas foram EXCLUÍDOS do Odoo
        Marca como cancelados (status_odoo='cancel')

        Lógica:
        1. Busca pedidos do sistema que foram modificados na janela de tempo
        2. Verifica se ainda existem no Odoo
        3. Se NÃO existir mais, marca como cancelado
        """
        try:
            self.logger.info("🗑️  Detectando pedidos excluídos do Odoo...")

            # Buscar pedidos do sistema que foram modificados recentemente
            # (podem ter sido excluídos do Odoo)
            data_limite = datetime.now() - timedelta(minutes=minutos_janela)

            pedidos_sistema = PedidoCompras.query.filter(
                PedidoCompras.importado_odoo == True,
                PedidoCompras.odoo_id.isnot(None),  # ✅ CORRIGIDO: E711
                PedidoCompras.status_odoo != 'cancel',  # Só verificar os que não estão cancelados
                PedidoCompras.criado_em >= data_limite  # Apenas da janela de tempo
            ).all()

            if not pedidos_sistema:
                self.logger.info("   ✅ Nenhum pedido para verificar")
                return 0

            self.logger.info(f"   🔍 Verificando {len(pedidos_sistema)} pedidos...")

            # Coletar IDs das linhas que existem no Odoo
            ids_odoo_encontrados = set()
            for pedido in pedidos_odoo:
                if pedido.get('order_line'):
                    ids_odoo_encontrados.update(pedido['order_line'])

            # Marcar como cancelados os que NÃO foram encontrados
            cancelados = 0
            for pedido_sistema in pedidos_sistema:
                odoo_id_int = int(pedido_sistema.odoo_id)

                if odoo_id_int not in ids_odoo_encontrados:
                    # Não existe mais no Odoo → marcar como cancelado
                    pedido_sistema.status_odoo = 'cancel'
                    cancelados += 1
                    self.logger.warning(
                        f"   ⚠️  Pedido {pedido_sistema.num_pedido} (linha {pedido_sistema.odoo_id}) "
                        f"EXCLUÍDO do Odoo → marcado como cancelado"
                    )

            if cancelados > 0:
                db.session.flush()
                self.logger.info(f"   ✅ {cancelados} pedidos marcados como cancelados (exclusão)")
            else:
                self.logger.info("   ✅ Todos os pedidos ainda existem no Odoo")

            return cancelados

        except Exception as e:
            self.logger.error(f"❌ Erro ao detectar pedidos excluídos: {e}")
            return 0
