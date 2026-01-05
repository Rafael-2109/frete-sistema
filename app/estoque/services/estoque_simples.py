"""
Serviço de Estoque Simplificado - Queries Diretas com Cache Otimizado
Performance garantida < 50ms por consulta
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import logging
import time

from sqlalchemy import func
from flask import current_app
from app import db
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
from app.separacao.models import Separacao
from app.producao.models import ProgramacaoProducao

logger = logging.getLogger(__name__)

# 🚀 OTIMIZAÇÃO: Cache global com TTL de 10 segundos (reduzido de 30s)
_cache_ttl = {}  # {chave: timestamp}
_cache_data = {}  # {chave: dados}


class ServicoEstoqueSimples:
    """
    Serviço único para todos os cálculos de estoque.
    Com cache TTL de 10s para otimizar performance (balanceando freshness vs performance).
    """

    @staticmethod
    def _get_cache(chave: str, ttl_seconds: int = 10):
        """Obter valor do cache se ainda válido (TTL padrão: 10s)"""
        if chave in _cache_ttl:
            idade = time.time() - _cache_ttl[chave]
            if idade < ttl_seconds:
                return _cache_data.get(chave)
            else:
                # Limpar cache expirado
                del _cache_ttl[chave]
                if chave in _cache_data:
                    del _cache_data[chave]
        return None

    @staticmethod
    def _set_cache(chave: str, valor: Any):
        """Salvar valor no cache"""
        _cache_ttl[chave] = time.time()
        _cache_data[chave] = valor

    @staticmethod
    def _invalidar_cache_produto(cod_produto: str):
        """Invalida TODOS os caches de um produto específico"""
        chaves_para_remover = []
        for chave in _cache_ttl.keys():
            if chave.startswith(f"projecao_{cod_produto}_"):
                chaves_para_remover.append(chave)

        for chave in chaves_para_remover:
            del _cache_ttl[chave]
            if chave in _cache_data:
                del _cache_data[chave]

        if chaves_para_remover:
            logger.info(f"🗑️ Cache invalidado para produto {cod_produto}: {len(chaves_para_remover)} entrada(s)")

    @staticmethod
    def calcular_estoque_atual(cod_produto: str) -> float:
        """
        Calcula estoque atual baseado em MovimentacaoEstoque.
        IMPORTANTE: qtd_movimentacao já vem com sinal correto:
        - Entradas: valores positivos
        - Saídas: valores negativos
        
        Performance esperada: < 10ms
        """
        try:
            # Obter códigos unificados (considera todos os códigos relacionados)
            # Se não houver unificação, retorna apenas o código original
            codigos = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
            
            # Query simples: apenas SOMA pois valores já têm sinal correto
            # Considera apenas registros ativos (cancelados têm ativo=False)
            resultado = db.session.query(
                func.sum(MovimentacaoEstoque.qtd_movimentacao).label('estoque_atual')
            ).filter(
                MovimentacaoEstoque.cod_produto.in_(codigos),
                MovimentacaoEstoque.ativo == True
            ).scalar()
            
            return float(resultado or 0)
            
        except Exception as e:
            logger.error(f"Erro ao calcular estoque atual para {cod_produto}: {e}")
            return 0
    
    @staticmethod
    def calcular_saidas_previstas(
        cod_produto: str,
        data_inicio: date,
        data_fim: date
    ) -> Dict[date, float]:
        """
        Calcula saídas previstas por dia baseado em Separacao.
        Considera apenas sincronizado_nf = False (não faturadas).
        IMPORTANTE: Agora inclui itens ATRASADOS (expedicao < hoje).
        Retorna dicionário {data: quantidade}.

        Performance esperada: < 20ms
        """
        try:
            # Obter códigos unificados
            codigos = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
            hoje = date.today()

            # Query para itens ATRASADOS (expedicao < hoje) ou SEM DATA (expedicao NULL)
            # Estes serão agrupados como saída para HOJE
            atrasados = db.session.query(
                func.sum(Separacao.qtd_saldo).label('quantidade')
            ).filter(
                Separacao.cod_produto.in_(codigos),
                Separacao.sincronizado_nf == False,  # Apenas não sincronizados
                db.or_(
                    Separacao.expedicao < hoje,  # ATRASADOS
                    Separacao.expedicao is None   # SEM DATA
                )
            ).scalar()

            # Query otimizada com GROUP BY para itens futuros
            resultados = db.session.query(
                Separacao.expedicao.label('data'),
                func.sum(Separacao.qtd_saldo).label('quantidade')
            ).filter(
                Separacao.cod_produto.in_(codigos),
                Separacao.sincronizado_nf == False,  # Apenas não sincronizados
                Separacao.expedicao >= data_inicio,
                Separacao.expedicao <= data_fim
            ).group_by(
                Separacao.expedicao
            ).all()
            
            # Converter para dicionário
            saidas = {}

            # Adicionar itens ATRASADOS como saída para HOJE
            if atrasados and float(atrasados) > 0:
                # Acumular com saídas já existentes para hoje
                if hoje in saidas:
                    saidas[hoje] += float(atrasados)
                else:
                    saidas[hoje] = float(atrasados)
                logger.info(f"[ESTOQUE] Produto {cod_produto}: {float(atrasados):.2f} unidades ATRASADAS/SEM DATA adicionadas para hoje")

            # Processar resultados normais, ACUMULANDO valores para a mesma data
            for resultado in resultados:
                if resultado.data and resultado.quantidade:
                    # IMPORTANTE: Acumular valores em vez de sobrescrever
                    if resultado.data in saidas:
                        saidas[resultado.data] += float(resultado.quantidade)
                    else:
                        saidas[resultado.data] = float(resultado.quantidade)

            return saidas
            
        except Exception as e:
            logger.error(f"Erro ao calcular saídas previstas para {cod_produto}: {e}")
            return {}
    
    @staticmethod
    def calcular_entradas_previstas(
        cod_produto: str,
        data_inicio: date,
        data_fim: date,
        entrada_em_d_plus_1: bool = False
    ) -> Dict[date, float]:
        """
        Calcula entradas previstas por dia baseado em ProgramacaoProducao.
        Retorna dicionário {data: quantidade}.

        Args:
            entrada_em_d_plus_1: Se True, programação entra no estoque em D+1 (dia seguinte à data_programacao)
                                Se False (default), entra em D+0 (mesma data)

        Performance esperada: < 20ms
        """
        try:
            # Obter códigos unificados
            codigos = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)

            # Query otimizada com GROUP BY
            resultados = db.session.query(
                func.date(ProgramacaoProducao.data_programacao).label('data'),
                func.sum(ProgramacaoProducao.qtd_programada).label('quantidade')
            ).filter(
                ProgramacaoProducao.cod_produto.in_(codigos),
                func.date(ProgramacaoProducao.data_programacao) >= data_inicio,
                func.date(ProgramacaoProducao.data_programacao) <= data_fim
            ).group_by(
                func.date(ProgramacaoProducao.data_programacao)
            ).all()

            # Converter para dicionário
            entradas = {}
            for resultado in resultados:
                if resultado.data and resultado.quantidade:
                    # ✅ APLICAR D+1 SE SOLICITADO
                    if entrada_em_d_plus_1:
                        data_entrada = resultado.data + timedelta(days=1)
                    else:
                        data_entrada = resultado.data

                    entradas[data_entrada] = float(resultado.quantidade)

            return entradas

        except Exception as e:
            logger.error(f"Erro ao calcular entradas previstas para {cod_produto}: {e}")
            return {}
    
    @staticmethod
    def calcular_projecao(cod_produto: str, dias: int = 28, entrada_em_d_plus_1: bool = False) -> Dict[str, Any]:
        """
        Calcula projeção completa de estoque para N dias.
        Combina estoque atual + entradas - saídas dia a dia.

        Args:
            entrada_em_d_plus_1: Se True, programação entra no estoque em D+1 (apenas Carteira Simples)

        🚀 OTIMIZAÇÃO: Cache de 30s para reduzir queries repetidas
        Performance esperada: < 50ms total (3 queries) ou < 1ms (cache hit)
        """
        try:
            # 🚀 OTIMIZAÇÃO: Verificar cache primeiro (incluir entrada_em_d_plus_1 na chave)
            chave_cache = f"projecao_{cod_produto}_{dias}_d1_{entrada_em_d_plus_1}"
            cached = ServicoEstoqueSimples._get_cache(chave_cache, ttl_seconds=30)
            if cached is not None:
                logger.debug(f"✅ Cache HIT para {cod_produto} (projeção {dias} dias, D+1={entrada_em_d_plus_1})")
                return cached
            hoje = date.today()
            data_fim = hoje + timedelta(days=dias)

            # 1. Estoque atual (1 query)
            estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

            # 2. Movimentações futuras (2 queries)
            saidas = ServicoEstoqueSimples.calcular_saidas_previstas(
                cod_produto, hoje, data_fim
            )
            entradas = ServicoEstoqueSimples.calcular_entradas_previstas(
                cod_produto, hoje, data_fim,
                entrada_em_d_plus_1=entrada_em_d_plus_1  # ✅ PROPAGAR PARÂMETRO
            )
            
            # 3. Montar projeção dia a dia (em memória, sem query)
            projecao = []
            saldo = estoque_atual
            menor_estoque = estoque_atual
            dia_ruptura = None
            
            for dia in range(dias + 1):
                data = hoje + timedelta(days=dia)
                
                # Obter movimentações do dia
                entrada_dia = entradas.get(data, 0)
                saida_dia = saidas.get(data, 0)
                
                # Calcular novo saldo
                if dia == 0:
                    # D0: aplica saídas no estoque inicial
                    saldo_inicial = estoque_atual
                    saldo_sem_producao = saldo_inicial - saida_dia  # SALDO = Est. Inicial - Saídas
                    saldo_final = saldo_sem_producao + entrada_dia  # Est. Final = Saldo + Produção
                else:
                    # D+N: saldo inicial é o final do dia anterior
                    saldo_inicial = projecao[dia-1]['saldo_final']  # Pegar saldo_final do dia anterior
                    saldo_sem_producao = saldo_inicial - saida_dia  # SALDO = Est. Inicial - Saídas
                    saldo_final = saldo_sem_producao + entrada_dia  # Est. Final = Saldo + Produção
                
                # Atualizar menor estoque e dia de ruptura
                if saldo_final < menor_estoque:
                    menor_estoque = saldo_final
                
                if saldo_final < 0 and dia_ruptura is None:
                    dia_ruptura = data
                
                # Adicionar à projeção
                projecao.append({
                    'dia': dia,
                    'data': data.isoformat(),
                    'saldo_inicial': saldo_inicial,
                    'entrada': entrada_dia,
                    'saida': saida_dia,
                    'saldo': saldo_sem_producao,  # NOVO: Saldo sem produção
                    'saldo_final': saldo_final
                })
                
                # Atualizar saldo para próximo dia
                saldo = saldo_final
            
            # Calcular métricas importantes
            menor_estoque_d7 = min(
                [p['saldo_final'] for p in projecao[:8]],  # D0 até D7
                default=estoque_atual
            )

            resultado = {
                'cod_produto': cod_produto,
                'estoque_atual': estoque_atual,
                'menor_estoque_d7': menor_estoque_d7,
                'menor_estoque_d28': menor_estoque,
                'dia_ruptura': dia_ruptura.isoformat() if dia_ruptura else None,
                'projecao': projecao
            }

            # 🚀 OTIMIZAÇÃO: Salvar no cache
            ServicoEstoqueSimples._set_cache(chave_cache, resultado)

            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao calcular projeção para {cod_produto}: {e}")
            return {
                'cod_produto': cod_produto,
                'estoque_atual': 0,
                'menor_estoque_d7': 0,
                'menor_estoque_d28': 0,
                'dia_ruptura': None,
                'projecao': []
            }
    
    @staticmethod
    def calcular_multiplos_produtos(
        cod_produtos: List[str],
        dias: int = 7,
        entrada_em_d_plus_1: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calcula projeção para múltiplos produtos em paralelo.
        Otimizado para workspace e dashboards.

        Args:
            entrada_em_d_plus_1: Se True, programação entra no estoque em D+1 (apenas Carteira Simples)

        Performance esperada: < 200ms para 10 produtos
        """
        resultados = {}

        # Verificar se temos contexto Flask ativo
        try:
            # Se temos contexto, capturar para usar nas threads
            app = current_app._get_current_object()

            def calcular_com_contexto(cod_produto, dias, entrada_em_d_plus_1):
                """Executa cálculo com contexto Flask"""
                with app.app_context():
                    return ServicoEstoqueSimples.calcular_projecao(
                        cod_produto, dias, entrada_em_d_plus_1=entrada_em_d_plus_1
                    )
            
            # Usar ThreadPoolExecutor para paralelizar
            with ThreadPoolExecutor(max_workers=min(len(cod_produtos), 10)) as executor:
                futures = {
                    cod: executor.submit(calcular_com_contexto, cod, dias, entrada_em_d_plus_1)
                    for cod in cod_produtos
                }

                for cod, future in futures.items():
                    try:
                        resultados[cod] = future.result(timeout=1)  # Timeout de 1s por produto
                    except Exception as e:
                        logger.error(f"Erro ao calcular estoque para {cod}: {e}")
                        resultados[cod] = {
                            'cod_produto': cod,
                            'estoque_atual': 0,
                            'menor_estoque_d7': 0,
                            'erro': str(e)
                        }
        except RuntimeError:
            # Sem contexto Flask, executar sequencialmente
            logger.warning("Executando cálculos sequencialmente (sem contexto Flask)")
            for cod in cod_produtos:
                try:
                    resultados[cod] = ServicoEstoqueSimples.calcular_projecao(
                        cod, dias, entrada_em_d_plus_1=entrada_em_d_plus_1
                    )
                except Exception as e:
                    logger.error(f"Erro ao calcular estoque para {cod}: {e}")
                    resultados[cod] = {
                        'cod_produto': cod,
                        'estoque_atual': 0,
                        'menor_estoque_d7': 0,
                        'erro': str(e)
                    }
        
        return resultados
    
    @staticmethod
    def get_produtos_ruptura(dias_limite: int = 7) -> List[Dict[str, Any]]:
        """
        Retorna produtos com ruptura prevista nos próximos N dias.
        Query otimizada para dashboard de ruptura.
        
        Performance esperada: < 100ms
        """
        try:
            hoje = date.today()
            data_limite = hoje + timedelta(days=dias_limite)
            
            # 1. Buscar produtos únicos que têm movimentação
            produtos = db.session.query(
                MovimentacaoEstoque.cod_produto.distinct()
            ).filter(
                MovimentacaoEstoque.ativo == True
            ).all()
            
            produtos_ruptura = []
            
            # 2. Para cada produto, verificar ruptura
            # (futuramente pode ser otimizado com query mais complexa)
            for (cod_produto,) in produtos:
                projecao = ServicoEstoqueSimples.calcular_projecao(
                    cod_produto, 
                    dias_limite
                )
                
                if projecao.get('dia_ruptura'):
                    dia_ruptura = date.fromisoformat(projecao['dia_ruptura'])
                    if dia_ruptura <= data_limite:
                        produtos_ruptura.append({
                            'cod_produto': cod_produto,
                            'estoque_atual': projecao['estoque_atual'],
                            'menor_estoque_d7': projecao['menor_estoque_d7'],
                            'dia_ruptura': projecao['dia_ruptura'],
                            'dias_ate_ruptura': (dia_ruptura - hoje).days
                        })
            
            # Ordenar por dias até ruptura
            produtos_ruptura.sort(key=lambda x: x['dias_ate_ruptura'])
            
            return produtos_ruptura
            
        except Exception as e:
            logger.error(f"Erro ao buscar produtos com ruptura: {e}")
            return []
    
    @staticmethod
    def validar_disponibilidade(
        cod_produto: str, 
        quantidade: float, 
        data_necessaria: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Valida se há estoque disponível para uma quantidade em uma data.
        Útil para validações de separação e pedidos.
        
        Performance esperada: < 30ms
        """
        try:
            if data_necessaria is None:
                data_necessaria = date.today()
            
            # Se for hoje, verificar estoque atual
            if data_necessaria == date.today():
                estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)
                
                return {
                    'disponivel': estoque_atual >= quantidade,
                    'estoque_disponivel': estoque_atual,
                    'quantidade_solicitada': quantidade,
                    'falta': max(0, quantidade - estoque_atual)
                }
            
            # Se for futuro, calcular projeção até a data
            dias = (data_necessaria - date.today()).days
            projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, dias)
            
            # Buscar saldo na data específica
            for dia_proj in projecao['projecao']:
                if dia_proj['data'] == data_necessaria.isoformat():
                    estoque_na_data = dia_proj['saldo_final']
                    
                    return {
                        'disponivel': estoque_na_data >= quantidade,
                        'estoque_disponivel': estoque_na_data,
                        'quantidade_solicitada': quantidade,
                        'falta': max(0, quantidade - estoque_na_data),
                        'data': data_necessaria.isoformat()
                    }
            
            return {
                'disponivel': False,
                'erro': 'Data fora do período de projeção'
            }
            
        except Exception as e:
            logger.error(f"Erro ao validar disponibilidade: {e}")
            return {
                'disponivel': False,
                'erro': str(e)
            }
    
    @staticmethod
    def get_projecao_completa(cod_produto: str, dias: int = 28) -> Dict[str, Any]:
        """
        Método de compatibilidade com ServicoEstoqueTempoReal.
        Mantém a mesma interface para facilitar migração.
        SEMPRE retorna um dicionário válido, mesmo em caso de erro.
        """
        try:
            projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, dias)
            
            # DEBUG
            logger.info(f"[DEBUG get_projecao_completa] Produto {cod_produto}:")
            if projecao:
                logger.info(f"  - estoque_atual: {projecao.get('estoque_atual', 'NONE')}")
                logger.info(f"  - menor_estoque_d7: {projecao.get('menor_estoque_d7', 'NONE')}")
                logger.info(f"  - projecao tem {len(projecao.get('projecao', []))} dias")
                if projecao.get('projecao'):
                    primeiro_dia = projecao['projecao'][0] if projecao['projecao'] else {}
                    logger.info(f"  - D0 entrada: {primeiro_dia.get('entrada', 'NONE')}")
                    logger.info(f"  - D0 saldo_final: {primeiro_dia.get('saldo_final', 'NONE')}")
            else:
                logger.info(f"  - projecao é None ou vazio")
            
            # Adaptar formato para compatibilidade
            if projecao and projecao.get('projecao'):
                # Converter projecao para formato DETALHADO esperado pelo frontend
                projecao_formatada = []
                for dia in projecao['projecao']:
                    if isinstance(dia, dict):
                        # Calcular saldo se não existir
                        estoque_inicial = dia.get('saldo_inicial', 0)
                        saidas = dia.get('saida', 0)
                        saldo = dia.get('saldo', estoque_inicial - saidas)  # Usar 'saldo' se existir, senão calcular
                        
                        projecao_formatada.append({
                            'dia': dia.get('dia', 0),
                            'data': dia.get('data', ''),
                            'estoque_inicial': estoque_inicial,
                            'saldo_inicial': estoque_inicial,  # Adicionar ambos os nomes
                            'saidas': saidas,
                            'saida': saidas,  # Adicionar ambos os nomes
                            'saldo': saldo,  # INCLUIR campo saldo
                            'producao': dia.get('entrada', 0),
                            'entrada': dia.get('entrada', 0),  # Manter entrada também
                            'estoque_final': dia.get('saldo_final', 0),
                            'saldo_final': dia.get('saldo_final', 0)  # Adicionar ambos os nomes
                        })
                
                # Buscar nome do produto de CadastroPalletizacao
                from app.producao.models import CadastroPalletizacao
                produto_cadastro = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
                nome_produto = produto_cadastro.nome_produto if produto_cadastro else f"Produto {cod_produto}"
                
                return {
                    'cod_produto': cod_produto,
                    'nome_produto': nome_produto,  # Adicionar nome do produto
                    'estoque_atual': projecao.get('estoque_atual', 0),
                    'estoque_d0': projecao.get('estoque_atual', 0),
                    'menor_estoque_d7': projecao.get('menor_estoque_d7', 0),
                    'dia_ruptura': projecao.get('dia_ruptura'),
                    'projecao': projecao_formatada,  # Array com objetos detalhados
                    'projecao_detalhada': projecao.get('projecao', [])  # Dados completos originais
                }
            
            # Se não tem projeção válida, retornar estrutura vazia mas válida
            # Buscar nome do produto de CadastroPalletizacao
            from app.producao.models import CadastroPalletizacao
            produto_cadastro = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
            nome_produto = produto_cadastro.nome_produto if produto_cadastro else f"Produto {cod_produto}"
            
            return {
                'cod_produto': cod_produto,
                'nome_produto': nome_produto,  # Adicionar nome do produto
                'estoque_atual': 0,
                'estoque_d0': 0,
                'menor_estoque_d7': 0,
                'dia_ruptura': None,
                'projecao': [],
                'projecao_detalhada': []
            }
            
        except Exception as e:
            logger.error(f"Erro em get_projecao_completa para {cod_produto}: {e}")
            # SEMPRE retornar dicionário válido
            return {
                'cod_produto': cod_produto,
                'estoque_atual': 0,
                'estoque_d0': 0,
                'menor_estoque_d7': 0,
                'dia_ruptura': None,
                'projecao': [],
                'projecao_detalhada': []
            }

    # ==============================================
    # 🚀 MÉTODOS BATCH OTIMIZADOS (OTIMIZAÇÃO CARTEIRA SIMPLES)
    # ==============================================

    @staticmethod
    def calcular_estoque_batch(
        codigos_produtos: List[str],
        data_fim: date,
        mapa_unificacao: Dict[str, List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calcula estoque atual + entradas previstas para TODOS os produtos em batch.
        USA queries agregadas para máxima performance.

        SEGURANÇA: Dados frescos do banco, não cache.

        Args:
            codigos_produtos: Lista de códigos de produtos
            data_fim: Data limite para entradas previstas
            mapa_unificacao: Mapa de códigos unificados (opcional, será calculado se não fornecido)

        Returns:
            Dict[cod_produto] -> {estoque_atual, programacao: [{data, qtd}]}

        Performance esperada: < 100ms para 200 produtos (vs ~2s com N queries)
        """
        if not codigos_produtos:
            return {}

        try:
            hoje = date.today()

            # Se mapa_unificacao não fornecido, calcular em batch
            if mapa_unificacao is None:
                mapa_unificacao = UnificacaoCodigos.get_todos_codigos_relacionados_batch(codigos_produtos)

            # Expandir todos os códigos (incluindo unificados)
            todos_codigos = set()
            for cod, relacionados in mapa_unificacao.items():
                todos_codigos.update(relacionados)
            todos_codigos = list(todos_codigos)

            if not todos_codigos:
                return {}

            # ==============================================
            # QUERY 1: Estoque atual em batch
            # ==============================================
            resultados_estoque = db.session.query(
                MovimentacaoEstoque.cod_produto,
                func.sum(MovimentacaoEstoque.qtd_movimentacao).label('estoque')
            ).filter(
                MovimentacaoEstoque.cod_produto.in_(todos_codigos),
                MovimentacaoEstoque.ativo == True
            ).group_by(
                MovimentacaoEstoque.cod_produto
            ).all()

            estoque_por_codigo = {str(r.cod_produto): float(r.estoque or 0) for r in resultados_estoque}

            # ==============================================
            # QUERY 2: Entradas previstas (programação) em batch
            # ==============================================
            resultados_programacao = db.session.query(
                ProgramacaoProducao.cod_produto,
                func.date(ProgramacaoProducao.data_programacao).label('data'),
                func.sum(ProgramacaoProducao.qtd_programada).label('quantidade')
            ).filter(
                ProgramacaoProducao.cod_produto.in_(todos_codigos),
                func.date(ProgramacaoProducao.data_programacao) >= hoje,
                func.date(ProgramacaoProducao.data_programacao) <= data_fim
            ).group_by(
                ProgramacaoProducao.cod_produto,
                func.date(ProgramacaoProducao.data_programacao)
            ).all()

            # Agrupar programação por código
            programacao_por_codigo = {}
            for r in resultados_programacao:
                cod = str(r.cod_produto)
                if cod not in programacao_por_codigo:
                    programacao_por_codigo[cod] = []
                if r.data and r.quantidade:
                    programacao_por_codigo[cod].append({
                        'data': r.data.isoformat() if hasattr(r.data, 'isoformat') else str(r.data),
                        'qtd': float(r.quantidade)
                    })

            # ==============================================
            # AGREGAR resultados para produtos originais (somando unificados)
            # ==============================================
            resultado_final = {}

            for cod_original in codigos_produtos:
                codigos_relacionados = mapa_unificacao.get(cod_original, [cod_original])

                # Somar estoque de todos os códigos relacionados
                estoque_total = sum(
                    estoque_por_codigo.get(str(cod), 0) for cod in codigos_relacionados
                )

                # Agregar programação de todos os códigos relacionados
                programacao_agregada = {}
                for cod_rel in codigos_relacionados:
                    for prog in programacao_por_codigo.get(str(cod_rel), []):
                        data_str = prog['data']
                        if data_str in programacao_agregada:
                            programacao_agregada[data_str] += prog['qtd']
                        else:
                            programacao_agregada[data_str] = prog['qtd']

                # Converter para formato esperado pelo frontend
                programacao_lista = [
                    {'data': data, 'qtd': qtd}
                    for data, qtd in sorted(programacao_agregada.items())
                    if qtd > 0
                ]

                resultado_final[cod_original] = {
                    'estoque_atual': estoque_total,
                    'programacao': programacao_lista
                }

            logger.info(f"✅ calcular_estoque_batch: {len(codigos_produtos)} produtos processados em batch")
            return resultado_final

        except Exception as e:
            logger.error(f"Erro em calcular_estoque_batch: {e}")
            # Retornar dicionário vazio para cada produto em caso de erro
            return {cod: {'estoque_atual': 0, 'programacao': []} for cod in codigos_produtos}