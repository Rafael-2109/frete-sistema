"""
Serviço de Requisições de Compras - Integração Odoo
====================================================

Importa requisições de compras do Odoo (purchase.request) e rastreia alterações.

Características:
- Sincronização incremental (90 minutos)
- Rastreamento de alterações em campos mapeados
- Filtro por detailed_type='product' (produtos armazenáveis)
- Histórico completo de mudanças

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


class RequisicaoComprasService:
    """
    Serviço para integração de requisições de compras com Odoo
    """

    # Mapeamento de campos Odoo → Sistema
    CAMPOS_MAPEADOS = {
        'num_requisicao': 'name',
        'data_requisicao_criacao': 'create_date',
        'usuario_requisicao_criacao': 'requested_by',
        'data_requisicao_solicitada': 'date_start',  # Data de entrega solicitada
        'cod_produto': 'product_id.default_code',  # Via query adicional
        'nome_produto': 'product_id.name',  # Via query adicional
        'qtd_produto_requisicao': 'product_qty',
        'lead_time_requisicao': 'CALCULADO',  # Dias entre date_start e date_required
        'status': 'state',
        'observacoes_odoo': 'description',
    }

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
        Sincroniza requisições de compras do Odoo de forma incremental

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
            resultado = self._processar_requisicoes(
                requisicoes_odoo,
                todas_linhas,
                produtos_cache,
                requisicoes_existentes_cache
            )

            # PASSO 6: 🗑️ Detectar requisições EXCLUÍDAS do Odoo (marcar como rejeitadas)
            requisicoes_canceladas_exclusao = self._detectar_requisicoes_excluidas(
                requisicoes_odoo,
                minutos_janela
            )
            resultado['requisicoes_canceladas_exclusao'] = requisicoes_canceladas_exclusao

            # Commit final
            db.session.commit()

            tempo_total = (datetime.now() - inicio).total_seconds()
            self.logger.info("=" * 80)
            self.logger.info(f"✅ SINCRONIZAÇÃO CONCLUÍDA EM {tempo_total:.2f}s")
            self.logger.info(f"   Requisições novas: {resultado['requisicoes_novas']}")
            self.logger.info(f"   Requisições atualizadas: {resultado['requisicoes_atualizadas']}")
            self.logger.info(f"   Requisições canceladas (exclusão): {resultado['requisicoes_canceladas_exclusao']}")
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

        Args:
            minutos_janela: Janela de tempo em minutos
            primeira_execucao: Se True, busca tudo

        Returns:
            Lista de requisições do Odoo
        """
        self.logger.info("🔍 Buscando requisições no Odoo...")

        # Montar filtro de data
        # ✅ IMPORTAR TODOS (incluindo rejeitadas) para sincronizar status
        data_limite = (datetime.now() - timedelta(minutes=minutos_janela)).strftime('%Y-%m-%d %H:%M:%S')

        filtro = [
            '|',
            ['create_date', '>=', data_limite],
            ['write_date', '>=', data_limite]
        ]

        self.logger.info(f"   Filtro: create_date OU write_date >= {data_limite} (incluindo rejeitadas)")

        # Campos da requisição
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
        🚀 OTIMIZAÇÃO: Busca TODAS as linhas de TODAS as requisições em 1 query

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
                'estimated_cost', 'description', 'purchase_state'  # ✅ ADICIONADO
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
        🚀 OTIMIZAÇÃO: Busca TODOS os produtos em 1 query

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
        self.logger.info(f"   Buscando {len(product_ids)} produtos únicos em 1 query...")
        todos_produtos = self.connection.read(
            'product.product',
            product_ids,
            fields=['id', 'default_code', 'name', 'detailed_type']
        )

        # Criar dicionário de cache
        produtos_cache = {produto['id']: produto for produto in todos_produtos}

        self.logger.info(f"   ✅ {len(produtos_cache)} produtos carregados")

        return produtos_cache

    def _carregar_requisicoes_existentes(self) -> Dict[str, Dict]:
        """
        🚀 OTIMIZAÇÃO: Carrega TODAS as requisições existentes em 1 query

        Returns:
            Dict com múltiplos índices para busca rápida:
            - 'por_odoo_id': {odoo_id: RequisicaoCompras}
            - 'por_req_produto_empresa': {(num_requisicao, cod_produto, company_id): RequisicaoCompras}
        """
        self.logger.info("🚀 Carregando requisições existentes em batch...")

        # 🚀 UMA ÚNICA QUERY para carregar TODAS
        todas_requisicoes = RequisicaoCompras.query.filter_by(
            importado_odoo=True
        ).all()

        # ✅ ATUALIZADO: Criar 2 índices para busca rápida O(1) incluindo company_id
        cache = {
            'por_odoo_id': {},      # odoo_id -> RequisicaoCompras
            'por_req_produto_empresa': {}   # (num_requisicao, cod_produto, company_id) -> RequisicaoCompras
        }

        for req in todas_requisicoes:
            if req.odoo_id:
                cache['por_odoo_id'][req.odoo_id] = req
            # ✅ ATUALIZADO: Incluir company_id na chave
            cache['por_req_produto_empresa'][(req.num_requisicao, req.cod_produto, req.company_id)] = req

        self.logger.info(f"   ✅ {len(todas_requisicoes)} requisições carregadas em memória")

        return cache

    def _processar_requisicoes(
        self,
        requisicoes_odoo: List[Dict],
        linhas_por_requisicao: Dict[int, List[Dict]],
        produtos_cache: Dict[int, Dict],
        requisicoes_existentes_cache: Dict[str, Dict]
    ) -> Dict[str, int]:
        """
        🚀 OTIMIZADO: Processa requisições usando CACHE (sem queries adicionais)

        Args:
            requisicoes_odoo: Lista de requisições brutas do Odoo
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

                # 🚀 Buscar linhas no CACHE (em vez de query)
                linhas_odoo = linhas_por_requisicao.get(req_odoo['id'], [])

                if not linhas_odoo:
                    self.logger.warning(f"   Requisição {req_odoo['name']} sem linhas - IGNORADA")
                    continue

                # Processar cada linha usando CACHE
                for linha_odoo in linhas_odoo:
                    try:
                        resultado_linha = self._processar_linha_requisicao(
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
                        # 🔴 ROLLBACK em caso de erro na linha
                        db.session.rollback()
                        self.logger.error(f"❌ Erro ao processar linha {linha_odoo.get('id')}: {e_linha}")
                        linhas_ignoradas += 1
                        continue

            except Exception as e:
                # 🔴 ROLLBACK em caso de erro na requisição
                db.session.rollback()
                self.logger.error(f"❌ Erro ao processar requisição {req_odoo.get('name')}: {e}")
                continue

        return {
            'requisicoes_novas': requisicoes_novas,
            'requisicoes_atualizadas': requisicoes_atualizadas,
            'linhas_processadas': linhas_processadas,
            'linhas_ignoradas': linhas_ignoradas
        }

    def _processar_linha_requisicao(
        self,
        req_odoo: Dict,
        linha_odoo: Dict,
        produtos_cache: Dict[int, Dict],
        requisicoes_existentes_cache: Dict[str, Dict]
    ) -> Dict[str, bool]:
        """
        🚀 OTIMIZADO: Processa uma linha usando CACHE (SEM queries adicionais)

        Args:
            req_odoo: Dados da requisição pai
            linha_odoo: Dados da linha
            produtos_cache: Cache de produtos
            requisicoes_existentes_cache: Cache de requisições existentes

        Returns:
            Dict com flags de processamento
        """
        try:
            # PASSO 1: 🚀 Buscar produto no CACHE (sem query!)
            product_id_odoo = linha_odoo['product_id'][0] if linha_odoo.get('product_id') else None

            if not product_id_odoo:
                self.logger.warning(f"   Linha {linha_odoo['id']} sem product_id - IGNORADA")
                return {'processado': False, 'nova': False, 'atualizada': False}

            # 🚀 Busca no CACHE em vez de query
            produto_odoo = produtos_cache.get(product_id_odoo)

            if not produto_odoo:
                self.logger.warning(f"   Produto {product_id_odoo} não encontrado no cache - IGNORADA")
                return {'processado': False, 'nova': False, 'atualizada': False}

            # VALIDAR: detailed_type = 'product'
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

            # PASSO 2: 🚀 Verificar se já existe no CACHE (sem queries!)
            odoo_id = str(linha_odoo['id'])
            num_requisicao = req_odoo['name']

            # ✅ NOVO: Extrair company_id do Odoo
            company_name = None
            if req_odoo.get('company_id'):
                company_name = req_odoo['company_id'][1] if len(req_odoo['company_id']) > 1 else None

            # 🚀 Busca no CACHE em vez de 2 queries
            requisicao_existente = requisicoes_existentes_cache['por_odoo_id'].get(odoo_id)

            if not requisicao_existente:
                # ✅ ATUALIZADO: Verificar por (num_requisicao, cod_produto, company_id)
                requisicao_existente = requisicoes_existentes_cache['por_req_produto_empresa'].get(
                    (num_requisicao, cod_produto, company_name)
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
                # ✅ ATUALIZADO: Incluir company_id na chave do cache
                requisicoes_existentes_cache['por_req_produto_empresa'][(nova_req.num_requisicao, nova_req.cod_produto, nova_req.company_id)] = nova_req

                return {'processado': True, 'nova': True, 'atualizada': False}

        except Exception as e:
            self.logger.error(f"❌ Erro ao processar linha {linha_odoo.get('id')}: {e}")
            return {'processado': False, 'nova': False, 'atualizada': False}

    def _criar_requisicao(
        self,
        req_odoo: Dict,
        linha_odoo: Dict,
        produto_odoo: Dict
    ) -> RequisicaoCompras:
        """
        Cria nova requisição de compras

        Args:
            req_odoo: Dados da requisição pai
            linha_odoo: Dados da linha
            produto_odoo: Dados do produto

        Returns:
            RequisicaoCompras criada
        """
        # Extrair dados
        cod_produto = produto_odoo['default_code']
        nome_produto = produto_odoo['name']
        num_requisicao = req_odoo['name']

        # ✅ NOVO: Extrair company_id (nome da empresa)
        company_name = None
        if req_odoo.get('company_id'):
            company_name = req_odoo['company_id'][1] if len(req_odoo['company_id']) > 1 else None

        # 🔴 VERIFICAÇÃO ADICIONAL: Checar se já existe por (num_requisicao + cod_produto + company_id)
        requisicao_duplicada = RequisicaoCompras.query.filter_by(
            num_requisicao=num_requisicao,
            cod_produto=cod_produto,
            company_id=company_name
        ).first()

        if requisicao_duplicada:
            self.logger.warning(
                f"   ⚠️  Requisição duplicada encontrada: {num_requisicao} + {cod_produto} "
                f"(ID existente: {requisicao_duplicada.id}) - PULANDO"
            )
            return requisicao_duplicada

        # Processar datas
        data_requisicao_criacao = datetime.strptime(
            req_odoo['create_date'], '%Y-%m-%d %H:%M:%S'
        ).date()

        data_requisicao_solicitada = None
        if req_odoo.get('date_start'):
            data_requisicao_solicitada = datetime.strptime(
                req_odoo['date_start'], '%Y-%m-%d'
            ).date()

        # ✅ CORRIGIDO: Extrair data_necessidade (date_required do Odoo)
        data_necessidade = None
        lead_time_requisicao = None
        if linha_odoo.get('date_required'):
            data_necessidade = datetime.strptime(linha_odoo['date_required'], '%Y-%m-%d').date()

            # Calcular lead_time se tiver data_requisicao_solicitada
            if data_requisicao_solicitada:
                lead_time_requisicao = (data_necessidade - data_requisicao_solicitada).days

        # Status
        status = self.MAPA_STATUS.get(req_odoo['state'], 'Pendente')

        # ✅ NOVO: Extrair purchase_state
        purchase_state = linha_odoo.get('purchase_state')

        # Criar objeto
        requisicao = RequisicaoCompras(
            num_requisicao=num_requisicao,
            company_id=company_name,  # ✅ NOVO: Empresa compradora
            data_requisicao_criacao=data_requisicao_criacao,
            usuario_requisicao_criacao=req_odoo['requested_by'][1] if req_odoo.get('requested_by') else None,
            data_requisicao_solicitada=data_requisicao_solicitada,
            cod_produto=cod_produto,
            nome_produto=nome_produto,
            qtd_produto_requisicao=Decimal(str(linha_odoo['product_qty'])),
            data_necessidade=data_necessidade,  # ✅ ADICIONADO
            purchase_state=purchase_state,  # ✅ ADICIONADO
            lead_time_requisicao=lead_time_requisicao,
            lead_time_previsto=None,  # Será preenchido quando houver pedido
            qtd_produto_sem_requisicao=Decimal('0'),
            status=status,
            observacoes_odoo=req_odoo.get('description') if req_odoo.get('description') != False else None,
            importado_odoo=True,
            odoo_id=str(linha_odoo['id']),
            requisicao_odoo_id=str(req_odoo['id']),
        )

        db.session.add(requisicao)

        try:
            db.session.flush()  # Para ter o ID
        except Exception as e:
            db.session.rollback()  # 🔴 ROLLBACK em caso de erro
            self.logger.error(f"❌ Erro ao criar requisição {num_requisicao} + {cod_produto}: {e}")
            raise

        # Criar snapshot completo no histórico (CRIAÇÃO)
        write_date = req_odoo.get('write_date')
        write_date_dt = datetime.strptime(write_date, '%Y-%m-%d %H:%M:%S') if write_date else None

        historico = HistoricoRequisicaoCompras(
            # Controle
            requisicao_id=requisicao.id,
            operacao='CRIAR',
            alterado_por='Odoo',
            write_date_odoo=write_date_dt,

            # Snapshot completo - TODOS os campos
            num_requisicao=requisicao.num_requisicao,
            company_id=requisicao.company_id,  # ✅ NOVO
            data_requisicao_criacao=requisicao.data_requisicao_criacao,
            usuario_requisicao_criacao=requisicao.usuario_requisicao_criacao,
            lead_time_requisicao=requisicao.lead_time_requisicao,
            lead_time_previsto=requisicao.lead_time_previsto,
            data_requisicao_solicitada=requisicao.data_requisicao_solicitada,
            cod_produto=requisicao.cod_produto,
            nome_produto=requisicao.nome_produto,
            qtd_produto_requisicao=requisicao.qtd_produto_requisicao,
            qtd_produto_sem_requisicao=requisicao.qtd_produto_sem_requisicao,
            necessidade=requisicao.necessidade,
            data_necessidade=requisicao.data_necessidade,
            status=requisicao.status,
            importado_odoo=requisicao.importado_odoo,
            odoo_id=requisicao.odoo_id,
            requisicao_odoo_id=requisicao.requisicao_odoo_id,
            status_requisicao=requisicao.status_requisicao,
            data_envio_odoo=requisicao.data_envio_odoo,
            data_confirmacao_odoo=requisicao.data_confirmacao_odoo,
            observacoes_odoo=requisicao.observacoes_odoo,
            criado_em=requisicao.criado_em
        )

        db.session.add(historico)

        self.logger.info(f"   ✅ Requisição {requisicao.num_requisicao} CRIADA - Produto: {cod_produto}")

        return requisicao

    def _atualizar_requisicao(
        self,
        requisicao_existente: RequisicaoCompras,
        req_odoo: Dict,
        linha_odoo: Dict,
        produto_odoo: Dict
    ) -> bool:
        """
        Atualiza requisição existente e registra mudanças

        Args:
            requisicao_existente: Requisição no banco
            req_odoo: Dados atuais do Odoo (requisição pai)
            linha_odoo: Dados atuais do Odoo (linha)
            produto_odoo: Dados do produto

        Returns:
            True se houve alteração, False caso contrário
        """
        alteracoes = []

        # ✅ CORRIGIDO: Calcular data_necessidade para comparação
        data_necessidade_nova = None
        if linha_odoo.get('date_required'):
            data_necessidade_nova = datetime.strptime(linha_odoo['date_required'], '%Y-%m-%d').date()

        # ✅ NOVO: purchase_state
        purchase_state_novo = linha_odoo.get('purchase_state')

        # Comparar campos mapeados
        campos_para_comparar = {
            'qtd_produto_requisicao': Decimal(str(linha_odoo['product_qty'])),
            'status': self.MAPA_STATUS.get(req_odoo['state'], 'Pendente'),
            'observacoes_odoo': req_odoo.get('description') if req_odoo.get('description') != False else None,
            'data_necessidade': data_necessidade_nova,  # ✅ ADICIONADO
            'purchase_state': purchase_state_novo,  # ✅ ADICIONADO
        }

        # Verificar mudanças
        for campo, novo_valor in campos_para_comparar.items():
            valor_atual = getattr(requisicao_existente, campo)

            # Normalizar para comparação
            if isinstance(valor_atual, Decimal) and not isinstance(novo_valor, Decimal):
                novo_valor = Decimal(str(novo_valor)) if novo_valor is not None else None

            if valor_atual != novo_valor:
                alteracoes.append({
                    'campo': campo,
                    'valor_antes': str(valor_atual),
                    'valor_depois': str(novo_valor)
                })

                # Atualizar campo
                setattr(requisicao_existente, campo, novo_valor)

        if not alteracoes:
            self.logger.debug(f"   Requisição {requisicao_existente.num_requisicao} sem alterações")
            return False

        # Gravar snapshot completo no histórico (após alteração)
        write_date = req_odoo.get('write_date')
        write_date_dt = datetime.strptime(write_date, '%Y-%m-%d %H:%M:%S') if write_date else None

        historico = HistoricoRequisicaoCompras(
            # Controle
            requisicao_id=requisicao_existente.id,
            operacao='EDITAR',
            alterado_por='Odoo',
            write_date_odoo=write_date_dt,

            # Snapshot completo - TODOS os campos (estado APÓS alteração)
            num_requisicao=requisicao_existente.num_requisicao,
            company_id=requisicao_existente.company_id,  # ✅ NOVO
            data_requisicao_criacao=requisicao_existente.data_requisicao_criacao,
            usuario_requisicao_criacao=requisicao_existente.usuario_requisicao_criacao,
            lead_time_requisicao=requisicao_existente.lead_time_requisicao,
            lead_time_previsto=requisicao_existente.lead_time_previsto,
            data_requisicao_solicitada=requisicao_existente.data_requisicao_solicitada,
            cod_produto=requisicao_existente.cod_produto,
            nome_produto=requisicao_existente.nome_produto,
            qtd_produto_requisicao=requisicao_existente.qtd_produto_requisicao,
            qtd_produto_sem_requisicao=requisicao_existente.qtd_produto_sem_requisicao,
            necessidade=requisicao_existente.necessidade,
            data_necessidade=requisicao_existente.data_necessidade,
            status=requisicao_existente.status,
            importado_odoo=requisicao_existente.importado_odoo,
            odoo_id=requisicao_existente.odoo_id,
            requisicao_odoo_id=requisicao_existente.requisicao_odoo_id,
            status_requisicao=requisicao_existente.status_requisicao,
            data_envio_odoo=requisicao_existente.data_envio_odoo,
            data_confirmacao_odoo=requisicao_existente.data_confirmacao_odoo,
            observacoes_odoo=requisicao_existente.observacoes_odoo,
            criado_em=requisicao_existente.criado_em
        )

        db.session.add(historico)

        self.logger.info(f"   📝 Requisição {requisicao_existente.num_requisicao} ATUALIZADA - {len(alteracoes)} mudanças")
        for alteracao in alteracoes:
            self.logger.info(f"      {alteracao['campo']}: {alteracao['valor_antes']} → {alteracao['valor_depois']}")

        return True

    def _detectar_requisicoes_excluidas(
        self,
        requisicoes_odoo: List[Dict],
        minutos_janela: int
    ) -> int:
        """
        Detecta requisições que existem no sistema mas foram EXCLUÍDAS do Odoo
        Marca como rejeitadas (status_requisicao='rejected')

        Lógica:
        1. Busca requisições do sistema modificadas na janela de tempo
        2. Verifica se ainda existem no Odoo
        3. Se NÃO existir mais, marca como rejeitada (equivalente a cancelado)
        """
        try:
            self.logger.info("🗑️  Detectando requisições excluídas do Odoo...")

            # Buscar requisições do sistema que foram modificadas recentemente
            data_limite = datetime.now() - timedelta(minutes=minutos_janela)

            requisicoes_sistema = RequisicaoCompras.query.filter(
                RequisicaoCompras.importado_odoo == True,
                RequisicaoCompras.odoo_id.isnot(None),  # ✅ CORRIGIDO: E711
                RequisicaoCompras.status_requisicao != 'rejected',  # Só verificar as que não estão rejeitadas
                RequisicaoCompras.criado_em >= data_limite  # Apenas da janela de tempo
            ).all()

            if not requisicoes_sistema:
                self.logger.info("   ✅ Nenhuma requisição para verificar")
                return 0

            self.logger.info(f"   🔍 Verificando {len(requisicoes_sistema)} requisições...")

            # Coletar IDs das requisições que existem no Odoo
            ids_odoo_encontrados = set()
            for req in requisicoes_odoo:
                ids_odoo_encontrados.add(str(req['id']))

            # Buscar TODAS as linhas das requisições encontradas
            if ids_odoo_encontrados:
                try:
                    linhas_requisicoes = self.connection.search_read(
                        'purchase.request.line',
                        [['request_id', 'in', list(ids_odoo_encontrados)]],
                        ['id']
                    )
                    ids_linhas_encontradas = {str(linha['id']) for linha in linhas_requisicoes}
                except Exception as e:
                    self.logger.error(f"   ❌ Erro ao buscar linhas: {e}")
                    ids_linhas_encontradas = set()
            else:
                ids_linhas_encontradas = set()

            # Marcar como rejeitadas as que NÃO foram encontradas
            cancelados = 0
            for req_sistema in requisicoes_sistema:
                if req_sistema.odoo_id not in ids_linhas_encontradas:
                    # Não existe mais no Odoo → marcar como rejeitada
                    req_sistema.status_requisicao = 'rejected'
                    cancelados += 1
                    self.logger.warning(
                        f"   ⚠️  Requisição {req_sistema.num_requisicao} (linha {req_sistema.odoo_id}) "
                        f"EXCLUÍDA do Odoo → marcada como rejeitada"
                    )

            if cancelados > 0:
                db.session.flush()
                self.logger.info(f"   ✅ {cancelados} requisições marcadas como rejeitadas (exclusão)")
            else:
                self.logger.info("   ✅ Todas as requisições ainda existem no Odoo")

            return cancelados

        except Exception as e:
            self.logger.error(f"❌ Erro ao detectar requisições excluídas: {e}")
            return 0
