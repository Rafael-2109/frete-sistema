"""
Service para lógica de agrupamento de pedidos da carteira

OTIMIZAÇÕES (2026-03-15):
- E1: Batch queries para rotas, subrotas e separações (3 queries vs ~5N)
- I1: Soma direta de valor_saldo (sem divisão/multiplicação redundante)
- I2: Popula expedicao/agendamento no dados_separacao
- I3: Removido campo expedicao_original inconsistente do fallback
"""

from collections import defaultdict
from sqlalchemy import func, and_, exists
from app import db
from app.carteira.models import CarteiraPrincipal, SaldoStandby
from app.separacao.models import Separacao
from app.producao.models import CadastroPalletizacao
from app.localidades.models import CadastroRota, CadastroSubRota
from app.utils.string_utils import remover_acentos
import logging

logger = logging.getLogger(__name__)


class AgrupamentoService:
    """Service responsável por agrupar pedidos da carteira"""

    def obter_pedidos_agrupados(self):
        """
        Obtém pedidos agrupados por num_pedido com agregações.
        Retorna lista de dicionários com dados enriquecidos.

        OTIMIZADO: Usa batch queries para rotas, subrotas e separações
        (3 queries extras no total vs ~5 por pedido antes).
        """
        try:
            # Buscar pedidos agrupados base
            pedidos_agrupados = self._query_agrupamento_base()

            if not pedidos_agrupados:
                return []

            # Coletar identificadores únicos para batch loading
            all_num_pedidos = [p.num_pedido for p in pedidos_agrupados]
            all_ufs = set(p.cod_uf for p in pedidos_agrupados if p.cod_uf)

            # Batch load: 3 queries no total (vs ~5 por pedido antes)
            rotas_map = self._carregar_rotas_batch(all_ufs)
            subrotas_lookup = self._carregar_subrotas_batch(all_ufs)
            separacoes_map = self._carregar_separacoes_batch(all_num_pedidos)

            # Importar GrupoEmpresarial uma vez
            from app.portal.utils.grupo_empresarial import GrupoEmpresarial

            # Enriquecer com lookups em memória
            pedidos_enriquecidos = []
            for pedido in pedidos_agrupados:
                pedido_enriquecido = self._enriquecer_pedido_batch(
                    pedido, rotas_map, subrotas_lookup, separacoes_map, GrupoEmpresarial
                )
                pedidos_enriquecidos.append(pedido_enriquecido)

            # Ordenar após enriquecimento para usar rotas calculadas
            def get_rota_para_ordenacao(pedido):
                """Retorna a rota considerando incoterm FOB/RED como rota especial"""
                incoterm = pedido.get('incoterm', 'CIF')
                if incoterm == 'FOB':
                    return 'FOB'
                elif incoterm == 'RED':
                    return 'RED'
                return pedido.get('rota') or 'ZZZZZ'

            pedidos_ordenados = sorted(pedidos_enriquecidos,
                key=lambda p: (
                    get_rota_para_ordenacao(p),     # 1. Rota/Incoterm (nulls no final)
                    p.get('sub_rota') or 'ZZZZZ',  # 2. Sub-rota (nulls no final)
                    p.get('cnpj_cpf') or 'ZZZZZ'   # 3. CNPJ (nulls no final)
                )
            )

            return pedidos_ordenados

        except Exception as e:
            logger.error(f"Erro ao obter pedidos agrupados: {e}")
            return []

    def _query_agrupamento_base(self):
        """
        Query principal de agrupamento conforme especificação

        IMPORTANTE: Esta query filtra apenas para EXIBIÇÃO no workspace.
        Pedidos com qtd_saldo_produto_pedido = 0 NÃO são deletados do banco,
        apenas não aparecem na listagem do workspace/carteira agrupada.
        """
        # NOTA: Campos expedicao, agendamento, protocolo, agendamento_confirmado,
        # rota, sub_rota, separacao_lote_id foram REMOVIDOS de CarteiraPrincipal
        # Esses dados agora vêm apenas de Separacao
        return db.session.query(
            # Campos base do agrupamento
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.vendedor,
            CarteiraPrincipal.equipe_vendas,
            CarteiraPrincipal.data_pedido,
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.data_entrega_pedido,
            CarteiraPrincipal.observ_ped_1,
            CarteiraPrincipal.status_pedido,
            CarteiraPrincipal.pedido_cliente,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.incoterm,
            CarteiraPrincipal.forma_agendamento,
            CarteiraPrincipal.importante,
            CarteiraPrincipal.tags_pedido,

            # Agregacoes
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido *
                    CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido *
                    CadastroPalletizacao.peso_bruto).label('peso_total'),
            func.sum(
                func.coalesce(
                    CarteiraPrincipal.qtd_saldo_produto_pedido /
                    func.nullif(CadastroPalletizacao.palletizacao, 0),
                    0
                )
            ).label('pallet_total'),
            func.count(CarteiraPrincipal.id).label('total_itens')

        ).outerjoin(
            CadastroPalletizacao,
            and_(
                CarteiraPrincipal.cod_produto == CadastroPalletizacao.cod_produto,
                CadastroPalletizacao.ativo == True
            )
        ).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0,
            ~exists().where(
                and_(
                    SaldoStandby.num_pedido == CarteiraPrincipal.num_pedido,
                    SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
                )
            )
        ).group_by(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.vendedor,
            CarteiraPrincipal.equipe_vendas,
            CarteiraPrincipal.data_pedido,
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.data_entrega_pedido,
            CarteiraPrincipal.observ_ped_1,
            CarteiraPrincipal.status_pedido,
            CarteiraPrincipal.pedido_cliente,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.incoterm,
            CarteiraPrincipal.forma_agendamento,
            CarteiraPrincipal.importante,
            CarteiraPrincipal.tags_pedido
        ).order_by(
            CarteiraPrincipal.cod_uf.asc().nullslast(),
            CarteiraPrincipal.nome_cidade.asc().nullslast(),
            CarteiraPrincipal.cnpj_cpf.asc().nullslast()
        ).all()

    # ─── Batch loading methods (FIX E1) ───────────────────────────

    def _carregar_rotas_batch(self, ufs):
        """Carrega todas as rotas ativas em 1 query -> dict {cod_uf: rota}"""
        if not ufs:
            return {}
        try:
            rotas = CadastroRota.query.filter(
                CadastroRota.cod_uf.in_(ufs),
                CadastroRota.ativa == True
            ).all()
            return {r.cod_uf: r.rota for r in rotas}
        except Exception as e:
            logger.warning(f"Erro ao carregar rotas em batch: {e}")
            return {}

    def _carregar_subrotas_batch(self, ufs):
        """
        Carrega todas as subrotas ativas em 1 query.
        Retorna dict {cod_uf: [(nome_normalizado, sub_rota)]} para lookup via substring.
        Usa remover_acentos() para normalizar nomes e garantir match accent-safe.
        """
        if not ufs:
            return {}
        try:
            subrotas = CadastroSubRota.query.filter(
                CadastroSubRota.cod_uf.in_(ufs),
                CadastroSubRota.ativa == True
            ).all()

            lookup = defaultdict(list)
            for sr in subrotas:
                nome_normalizado = remover_acentos(sr.nome_cidade) if sr.nome_cidade else ''
                lookup[sr.cod_uf].append((nome_normalizado, sr.sub_rota))
            return dict(lookup)
        except Exception as e:
            logger.warning(f"Erro ao carregar subrotas em batch: {e}")
            return {}

    def _buscar_subrota_em_memoria(self, subrotas_lookup, cod_uf, nome_cidade):
        """Busca subrota em memoria com normalizacao accent-safe"""
        if not cod_uf or not nome_cidade:
            return None
        nome_normalizado = remover_acentos(nome_cidade)
        candidates = subrotas_lookup.get(cod_uf, [])
        for sr_nome, sr_valor in candidates:
            if nome_normalizado in sr_nome:
                return sr_valor
        return None

    def _carregar_separacoes_batch(self, num_pedidos):
        """
        Carrega todas separacoes ativas (sincronizado_nf=False) em 1 query.
        Retorna dict {num_pedido: [separacoes]} ordenado por id asc.
        """
        if not num_pedidos:
            return {}
        try:
            separacoes = db.session.query(Separacao).filter(
                Separacao.num_pedido.in_(num_pedidos),
                Separacao.sincronizado_nf == False
            ).order_by(Separacao.id.asc()).all()

            agrupado = defaultdict(list)
            for sep in separacoes:
                agrupado[sep.num_pedido].append(sep)
            return dict(agrupado)
        except Exception as e:
            logger.warning(f"Erro ao carregar separacoes em batch: {e}")
            return {}

    # ─── Processing methods ───────────────────────────────────────

    def _processar_separacoes(self, separacoes_pedido):
        """
        Processa lista de separacoes de um pedido (ja carregadas em batch).
        Retorna (qtd_separacoes, valor_separacoes, dados_separacao, primeira_sep_agendamento)

        Fixes:
        - I1: Soma valor_saldo diretamente (sem divisao/multiplicacao redundante)
        - I2: Popula expedicao e agendamento no dados_separacao
        """
        dados_vazio = {
            'tem_protocolo': False,
            'agendamento_confirmado': False,
            'separacao_lote_id': None,
            'expedicao': None,
            'agendamento': None,
            'protocolo': None
        }

        if not separacoes_pedido:
            return 0, 0, dados_vazio, None

        # Contar lotes unicos
        lotes_unicos = set(
            sep.separacao_lote_id for sep in separacoes_pedido
            if sep.separacao_lote_id
        )
        qtd_separacoes = len(lotes_unicos)

        # Calcular valor e buscar dados
        valor_separacoes = 0
        dados_separacao = {
            'tem_protocolo': False,
            'agendamento_confirmado': False,
            'separacao_lote_id': None,
            'expedicao': None,
            'agendamento': None,
            'protocolo': None
        }

        for sep in separacoes_pedido:
            # FIX I1: Soma direta sem divisao/multiplicacao redundante
            # Antes: valor_unit = valor_saldo/qtd_saldo; total += qtd_saldo * valor_unit
            # Isso e matematicamente identico a somar valor_saldo, mas acumula erros float
            valor_separacoes += float(sep.valor_saldo or 0)

            # FIX I2: Capturar ultimo expedicao/agendamento nao-nulo
            if sep.expedicao:
                dados_separacao['expedicao'] = sep.expedicao
            if sep.agendamento:
                dados_separacao['agendamento'] = sep.agendamento

            # Verificar protocolo
            if sep.protocolo:
                dados_separacao['tem_protocolo'] = True
                dados_separacao['separacao_lote_id'] = sep.separacao_lote_id
                dados_separacao['protocolo'] = sep.protocolo

                if sep.agendamento_confirmado:
                    dados_separacao['agendamento_confirmado'] = True

        # Primeira separacao (menor id) - lista ja ordenada por id asc
        primeira_sep_agendamento = (
            separacoes_pedido[0].agendamento
            if separacoes_pedido[0].agendamento else None
        )

        return qtd_separacoes, valor_separacoes, dados_separacao, primeira_sep_agendamento

    def _enriquecer_pedido_batch(self, pedido, rotas_map, subrotas_lookup,
                                 separacoes_map, GrupoEmpresarial):
        """Enriquece pedido usando lookups em memoria (sem queries individuais)"""
        try:
            # Separacoes do pedido (pre-carregadas)
            separacoes_pedido = separacoes_map.get(pedido.num_pedido, [])
            qtd_separacoes, valor_separacoes, dados_separacao, primeira_sep_agendamento = \
                self._processar_separacoes(separacoes_pedido)

            # Calcular saldo restante
            valor_pedido = float(pedido.valor_total) if pedido.valor_total else 0
            valor_saldo_restante = valor_pedido - float(valor_separacoes)
            totalmente_separado = valor_saldo_restante <= 0.01

            # Dados de separacao
            protocolo_final = dados_separacao.get('protocolo') if dados_separacao.get('tem_protocolo') else None
            agendamento_confirmado_final = dados_separacao.get('agendamento_confirmado', False)
            expedicao_final = dados_separacao.get('expedicao')      # FIX I2: agora populado
            agendamento_final = dados_separacao.get('agendamento')  # FIX I2: agora populado

            # Rotas via lookup em memoria (0 queries)
            rota_calculada = rotas_map.get(pedido.cod_uf) if pedido.cod_uf else None
            sub_rota_calculada = self._buscar_subrota_em_memoria(
                subrotas_lookup, pedido.cod_uf, pedido.nome_cidade
            )

            # Grupo do cliente (in-memory, sem query)
            grupo_cliente = 'outros'
            if pedido.cnpj_cpf:
                grupo = GrupoEmpresarial.identificar_grupo(pedido.cnpj_cpf)
                if grupo == 'atacadao':
                    grupo_cliente = 'atacadao'
                elif grupo == 'assai':
                    grupo_cliente = 'sendas'

            return {
                'num_pedido': pedido.num_pedido,
                'vendedor': pedido.vendedor,
                'equipe_vendas': pedido.equipe_vendas,
                'data_pedido': pedido.data_pedido,
                'cnpj_cpf': pedido.cnpj_cpf,
                'raz_social_red': pedido.raz_social_red,
                'rota': rota_calculada,
                'sub_rota': sub_rota_calculada,
                'expedicao': expedicao_final,
                'data_entrega_pedido': pedido.data_entrega_pedido,
                'observ_ped_1': pedido.observ_ped_1,
                'status_pedido': pedido.status_pedido,
                'pedido_cliente': pedido.pedido_cliente,
                'cod_uf': pedido.cod_uf,
                'nome_cidade': pedido.nome_cidade,
                'incoterm': pedido.incoterm,
                'protocolo': protocolo_final,
                'agendamento': agendamento_final,
                'agendamento_confirmado': agendamento_confirmado_final,
                'forma_agendamento': pedido.forma_agendamento,
                'valor_total': valor_pedido,
                'peso_total': float(pedido.peso_total) if pedido.peso_total else 0,
                'pallet_total': float(pedido.pallet_total) if pedido.pallet_total else 0,
                'total_itens': pedido.total_itens,
                'valor_separacoes': float(valor_separacoes),
                'valor_saldo_restante': valor_saldo_restante,
                'qtd_separacoes': qtd_separacoes,
                'totalmente_separado': totalmente_separado,
                'tem_protocolo_separacao': dados_separacao.get('tem_protocolo', False),
                'separacao_lote_id': dados_separacao.get('separacao_lote_id'),
                'grupo_cliente': grupo_cliente,
                'importante': pedido.importante,
                'agendamento_primeira_separacao': primeira_sep_agendamento,
                'tags_pedido': pedido.tags_pedido
            }

        except Exception as e:
            logger.warning(f"Erro ao enriquecer pedido {pedido.num_pedido}: {e}")
            return self._criar_pedido_basico(
                pedido, rotas_map, subrotas_lookup, GrupoEmpresarial
            )

    def _criar_pedido_basico(self, pedido, rotas_map=None, subrotas_lookup=None,
                              GrupoEmpresarial=None):
        """Cria estrutura basica de pedido em caso de erro (FIX I3: sem expedicao_original)"""
        # Usar batch maps se disponiveis, senao faz query individual (fallback)
        if rotas_map is not None:
            rota_calculada = rotas_map.get(pedido.cod_uf) if pedido.cod_uf else None
        else:
            from app.carteira.utils.separacao_utils import buscar_rota_por_uf
            rota_calculada = buscar_rota_por_uf(pedido.cod_uf) if pedido.cod_uf else None

        if subrotas_lookup is not None:
            sub_rota_calculada = self._buscar_subrota_em_memoria(
                subrotas_lookup, pedido.cod_uf, pedido.nome_cidade
            )
        else:
            from app.carteira.utils.separacao_utils import buscar_sub_rota_por_uf_cidade
            sub_rota_calculada = buscar_sub_rota_por_uf_cidade(
                pedido.cod_uf, pedido.nome_cidade
            ) if pedido.cod_uf and pedido.nome_cidade else None

        grupo_cliente = 'outros'
        if pedido.cnpj_cpf:
            if GrupoEmpresarial is None:
                from app.portal.utils.grupo_empresarial import GrupoEmpresarial
            grupo = GrupoEmpresarial.identificar_grupo(pedido.cnpj_cpf)
            if grupo == 'atacadao':
                grupo_cliente = 'atacadao'
            elif grupo == 'assai':
                grupo_cliente = 'sendas'

        # FIX I3: Estrutura identica ao retorno normal (sem 'expedicao_original')
        return {
            'num_pedido': pedido.num_pedido,
            'vendedor': pedido.vendedor,
            'equipe_vendas': pedido.equipe_vendas,
            'data_pedido': pedido.data_pedido,
            'cnpj_cpf': pedido.cnpj_cpf,
            'raz_social_red': pedido.raz_social_red,
            'rota': rota_calculada,
            'sub_rota': sub_rota_calculada,
            'expedicao': None,
            'data_entrega_pedido': pedido.data_entrega_pedido,
            'observ_ped_1': pedido.observ_ped_1,
            'status_pedido': pedido.status_pedido,
            'pedido_cliente': pedido.pedido_cliente,
            'cod_uf': pedido.cod_uf,
            'nome_cidade': pedido.nome_cidade,
            'incoterm': pedido.incoterm,
            'protocolo': None,
            'agendamento': None,
            'agendamento_confirmado': False,
            'forma_agendamento': pedido.forma_agendamento,
            'valor_total': float(pedido.valor_total) if pedido.valor_total else 0,
            'peso_total': float(pedido.peso_total) if pedido.peso_total else 0,
            'pallet_total': float(pedido.pallet_total) if pedido.pallet_total else 0,
            'total_itens': pedido.total_itens,
            'valor_separacoes': 0,
            'valor_saldo_restante': float(pedido.valor_total) if pedido.valor_total else 0,
            'qtd_separacoes': 0,
            'totalmente_separado': False,
            'tem_protocolo_separacao': False,
            'separacao_lote_id': None,
            'grupo_cliente': grupo_cliente,
            'importante': pedido.importante if hasattr(pedido, 'importante') else False,
            'agendamento_primeira_separacao': None,
            'tags_pedido': pedido.tags_pedido if hasattr(pedido, 'tags_pedido') else None
        }
