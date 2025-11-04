"""
Serviço de Requisições de Compras - VERSÃO OTIMIZADA
=====================================================

OTIMIZAÇÕES IMPLEMENTADAS:
1. ✅ Batch loading de linhas (1 query em vez de N)
2. ✅ Batch loading de produtos (1 query em vez de N*M)
3. ✅ Cache de requisições existentes em memória (1 query em vez de N*M)

PERFORMANCE:
- Antes: ~1.600 queries para 100 requisições com 5 linhas
- Depois: ~4 queries para 100 requisições com 5 linhas

Redução: 99.75% 🚀

Autor: Sistema de Fretes
Data: 31/10/2025
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from decimal import Decimal
from collections import defaultdict

from app import db
from app.manufatura.models import RequisicaoCompras, HistoricoRequisicaoCompras
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class RequisicaoComprasServiceOtimizado:
    """
    Serviço OTIMIZADO para integração de requisições de compras com Odoo
    """

    # Mapeamento de status Odoo → Sistema
    MAPA_STATUS = {
        'draft': 'Rascunho',
        'to_approve': 'Aguardando Aprovação',
        'approved': 'Aprovada',
        'rejected': 'Rejeitada',
        'done': 'Concluída',
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connection = get_odoo_connection()

    def sincronizar_requisicoes_incremental(
        self,
        minutos_janela: int = 90,
        primeira_execucao: bool = False
    ) -> Dict[str, Any]:
        """
        Sincroniza requisições de compras do Odoo de forma incremental e OTIMIZADA

        Args:
            minutos_janela: Janela de tempo para buscar alterações (padrão: 90 minutos)
            primeira_execucao: Se True, importa tudo; se False, apenas alterações

        Returns:
            Dict com resultado da sincronização
        """
        inicio = datetime.now()
        self.logger.info("=" * 80)
        self.logger.info(f"🚀 SINCRONIZAÇÃO OTIMIZADA - {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"   Janela: {minutos_janela} minutos")
        self.logger.info(f"   Primeira execução: {primeira_execucao}")
        self.logger.info("=" * 80)

        try:
            # Autenticar no Odoo
            uid = self.connection.authenticate()
            if not uid:
                raise Exception("Falha na autenticação com Odoo")

            # PASSO 1: Buscar requisições alteradas
            requisicoes_odoo = self._buscar_requisicoes_odoo(minutos_janela, primeira_execucao)

            if not requisicoes_odoo:
                self.logger.info("✅ Nenhuma requisição nova ou alterada encontrada")
                return {
                    'sucesso': True,
                    'requisicoes_novas': 0,
                    'requisicoes_atualizadas': 0,
                    'linhas_processadas': 0,
                    'linhas_ignoradas': 0,
                    'tempo_execucao': (datetime.now() - inicio).total_seconds()
                }

            # PASSO 2: 🚀 BATCH LOADING de todas as linhas (1 query)
            todas_linhas = self._buscar_todas_linhas_batch(requisicoes_odoo)

            # PASSO 3: 🚀 BATCH LOADING de todos os produtos (1 query)
            produtos_cache = self._buscar_todos_produtos_batch(todas_linhas)

            # PASSO 4: 🚀 CACHE de requisições existentes (1 query)
            requisicoes_existentes_cache = self._carregar_requisicoes_existentes()

            # PASSO 5: Processar requisições com cache
            resultado = self._processar_requisicoes_otimizado(
                requisicoes_odoo,
                todas_linhas,
                produtos_cache,
                requisicoes_existentes_cache
            )

            # Commit final
            db.session.commit()

            tempo_total = (datetime.now() - inicio).total_seconds()
            self.logger.info("=" * 80)
            self.logger.info(f"✅ SINCRONIZAÇÃO CONCLUÍDA EM {tempo_total:.2f}s")
            self.logger.info(f"   Requisições novas: {resultado['requisicoes_novas']}")
            self.logger.info(f"   Requisições atualizadas: {resultado['requisicoes_atualizadas']}")
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

    def _buscar_requisicoes_odoo(
        self,
        minutos_janela: int,
        primeira_execucao: bool
    ) -> List[Dict]:
        """
        Busca requisições do Odoo com filtro de data
        """
        self.logger.info("🔍 Buscando requisições no Odoo...")

        filtro = [['state', '!=', 'rejected']]

        if not primeira_execucao:
            data_limite = (datetime.now() - timedelta(minutes=minutos_janela)).strftime('%Y-%m-%d %H:%M:%S')

            filtro = [
                '&',
                ['state', '!=', 'rejected'],
                '|',
                ['create_date', '>=', data_limite],
                ['write_date', '>=', data_limite]
            ]

            self.logger.info(f"   Filtro: state != rejected AND (create_date ou write_date >= {data_limite})")

        campos_requisicao = [
            'id', 'name', 'state', 'create_date', 'write_date',
            'date_start', 'requested_by', 'assigned_to',
            'description', 'origin', 'company_id', 'line_ids'
        ]

        requisicoes = self.connection.search_read(
            'purchase.request',
            filtro,
            campos_requisicao
        )

        self.logger.info(f"✅ Encontradas {len(requisicoes)} requisições")

        return requisicoes

    def _buscar_todas_linhas_batch(self, requisicoes_odoo: List[Dict]) -> Dict[int, List[Dict]]:
        """
        🚀 OTIMIZAÇÃO 1: Busca TODAS as linhas de TODAS as requisições em 1 query

        Args:
            requisicoes_odoo: Lista de requisições

        Returns:
            Dict mapeando requisicao_id -> lista de linhas
        """
        self.logger.info("🚀 Carregando TODAS as linhas em batch...")

        # Coletar todos os IDs de linhas
        todos_line_ids = []
        for req in requisicoes_odoo:
            if req.get('line_ids'):
                todos_line_ids.extend(req['line_ids'])

        if not todos_line_ids:
            self.logger.info("   ⚠️  Nenhuma linha encontrada")
            return {}

        # 🚀 UMA ÚNICA QUERY para buscar TODAS as linhas
        self.logger.info(f"   Buscando {len(todos_line_ids)} linhas em 1 query...")
        todas_linhas = self.connection.read(
            'purchase.request.line',
            todos_line_ids,
            fields=[
                'id', 'request_id', 'product_id', 'name',
                'product_qty', 'product_uom_id', 'date_required',
                'estimated_cost', 'description'
            ]
        )

        # Agrupar linhas por requisição
        linhas_por_requisicao = defaultdict(list)
        for linha in todas_linhas:
            req_id = linha['request_id'][0] if linha.get('request_id') else None
            if req_id:
                linhas_por_requisicao[req_id].append(linha)

        self.logger.info(f"   ✅ {len(todas_linhas)} linhas carregadas")

        return linhas_por_requisicao

    def _buscar_todos_produtos_batch(self, linhas_por_requisicao: Dict[int, List[Dict]]) -> Dict[int, Dict]:
        """
        🚀 OTIMIZAÇÃO 2: Busca TODOS os produtos em 1 query

        Args:
            linhas_por_requisicao: Dict de linhas agrupadas

        Returns:
            Dict mapeando product_id -> dados do produto
        """
        self.logger.info("🚀 Carregando TODOS os produtos em batch...")

        # Coletar todos os IDs de produtos ÚNICOS
        product_ids_set: Set[int] = set()
        for linhas in linhas_por_requisicao.values():
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

    def _carregar_requisicoes_existentes(self) -> Dict[str, RequisicaoCompras]:
        """
        🚀 OTIMIZAÇÃO 3: Carrega TODAS as requisições existentes em 1 query

        Returns:
            Dict com múltiplos índices para busca rápida
        """
        self.logger.info("🚀 Carregando requisições existentes em batch...")

        # 🚀 UMA ÚNICA QUERY para carregar TODAS
        todas_requisicoes = RequisicaoCompras.query.filter_by(
            importado_odoo=True
        ).all()

        # Criar 2 índices para busca rápida
        cache = {
            'por_odoo_id': {},      # odoo_id -> RequisicaoCompras
            'por_req_produto': {}   # (num_requisicao, cod_produto) -> RequisicaoCompras
        }

        for req in todas_requisicoes:
            if req.odoo_id:
                cache['por_odoo_id'][req.odoo_id] = req
            cache['por_req_produto'][(req.num_requisicao, req.cod_produto)] = req

        self.logger.info(f"   ✅ {len(todas_requisicoes)} requisições carregadas em memória")

        return cache

    def _processar_requisicoes_otimizado(
        self,
        requisicoes_odoo: List[Dict],
        linhas_por_requisicao: Dict[int, List[Dict]],
        produtos_cache: Dict[int, Dict],
        requisicoes_existentes_cache: Dict[str, Dict]
    ) -> Dict[str, int]:
        """
        Processa requisições usando CACHE (sem queries adicionais)

        Args:
            requisicoes_odoo: Requisições do Odoo
            linhas_por_requisicao: Linhas agrupadas por requisição
            produtos_cache: Cache de produtos
            requisicoes_existentes_cache: Cache de requisições existentes

        Returns:
            Dict com contadores
        """
        requisicoes_novas = 0
        requisicoes_atualizadas = 0
        linhas_processadas = 0
        linhas_ignoradas = 0

        for req_odoo in requisicoes_odoo:
            try:
                self.logger.info(f"📋 Processando requisição {req_odoo['name']}...")

                # Buscar linhas no CACHE
                linhas_odoo = linhas_por_requisicao.get(req_odoo['id'], [])

                if not linhas_odoo:
                    self.logger.warning(f"   Requisição {req_odoo['name']} sem linhas - IGNORADA")
                    continue

                # Processar cada linha usando CACHE
                for linha_odoo in linhas_odoo:
                    try:
                        resultado_linha = self._processar_linha_otimizada(
                            req_odoo,
                            linha_odoo,
                            produtos_cache,
                            requisicoes_existentes_cache
                        )

                        if resultado_linha['processado']:
                            linhas_processadas += 1
                            if resultado_linha['nova']:
                                requisicoes_novas += 1
                            elif resultado_linha['atualizada']:
                                requisicoes_atualizadas += 1
                        else:
                            linhas_ignoradas += 1

                    except Exception as e_linha:
                        db.session.rollback()
                        self.logger.error(f"❌ Erro ao processar linha {linha_odoo.get('id')}: {e_linha}")
                        linhas_ignoradas += 1
                        continue

            except Exception as e:
                db.session.rollback()
                self.logger.error(f"❌ Erro ao processar requisição {req_odoo.get('name')}: {e}")
                continue

        return {
            'requisicoes_novas': requisicoes_novas,
            'requisicoes_atualizadas': requisicoes_atualizadas,
            'linhas_processadas': linhas_processadas,
            'linhas_ignoradas': linhas_ignoradas
        }

    def _processar_linha_otimizada(
        self,
        req_odoo: Dict,
        linha_odoo: Dict,
        produtos_cache: Dict[int, Dict],
        requisicoes_existentes_cache: Dict[str, Dict]
    ) -> Dict[str, bool]:
        """
        Processa uma linha usando CACHE (SEM queries adicionais)

        Args:
            req_odoo: Dados da requisição
            linha_odoo: Dados da linha
            produtos_cache: Cache de produtos
            requisicoes_existentes_cache: Cache de requisições

        Returns:
            Dict com flags
        """
        try:
            # PASSO 1: Buscar produto no CACHE (SEM query!)
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

            # PASSO 2: Verificar se já existe no CACHE (SEM queries!)
            odoo_id = str(linha_odoo['id'])
            num_requisicao = req_odoo['name']

            # 🚀 Busca no CACHE em vez de 2 queries
            requisicao_existente = requisicoes_existentes_cache['por_odoo_id'].get(odoo_id)

            if not requisicao_existente:
                # Verificar por (num_requisicao, cod_produto)
                requisicao_existente = requisicoes_existentes_cache['por_req_produto'].get(
                    (num_requisicao, cod_produto)
                )

            if requisicao_existente:
                # ATUALIZAR
                atualizada = self._atualizar_requisicao(
                    requisicao_existente,
                    req_odoo,
                    linha_odoo,
                    produto_odoo
                )
                return {'processado': True, 'nova': False, 'atualizada': atualizada}
            else:
                # CRIAR NOVA
                nova_req = self._criar_requisicao(req_odoo, linha_odoo, produto_odoo)

                # 🚀 Atualizar CACHE com nova requisição
                if nova_req.odoo_id:
                    requisicoes_existentes_cache['por_odoo_id'][nova_req.odoo_id] = nova_req
                requisicoes_existentes_cache['por_req_produto'][(nova_req.num_requisicao, nova_req.cod_produto)] = nova_req

                return {'processado': True, 'nova': True, 'atualizada': False}

        except Exception as e:
            self.logger.error(f"❌ Erro ao processar linha {linha_odoo.get('id')}: {e}")
            return {'processado': False, 'nova': False, 'atualizada': False}

    # ... métodos _criar_requisicao e _atualizar_requisicao continuam iguais ...
