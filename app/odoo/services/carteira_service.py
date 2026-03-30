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
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime, date

from app import db
from app.utils.timezone import agora_utc_naive, odoo_para_local
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.carteira_mapper import CarteiraMapper
from app.custeio.models import CustoConsiderado

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

    def _processar_cancelamento_pedido(self, num_pedido: str) -> bool:
        """
        Processa o cancelamento de um pedido de forma atômica.

        Ações executadas:
        1. Busca separações vinculadas ao pedido
        2. Para cada separação vinculada a EmbarqueItem:
           - Cancela o EmbarqueItem (status='cancelado')
        3. EXCLUI todas as Separacao do pedido
        4. EXCLUI todos os itens da CarteiraPrincipal do pedido
        5. Remove PreSeparacaoItem se existirem

        Args:
            num_pedido: Número do pedido a ser cancelado

        Returns:
            bool: True se processamento foi bem sucedido
        """
        try:
            logger.info(f"🔄 Processando cancelamento do pedido {num_pedido}")

            from app.carteira.models import CarteiraPrincipal
            from app.separacao.models import Separacao
            from app.embarques.models import EmbarqueItem

            # 1. Buscar separações do pedido
            separacoes = Separacao.query.filter_by(num_pedido=num_pedido).all()

            logger.info(f"   📦 Encontradas {len(separacoes)} separações")

            # 2. Para cada separação, verificar se está em EmbarqueItem
            embarques_cancelados = 0

            for separacao in separacoes:
                if separacao.separacao_lote_id:
                    # Buscar EmbarqueItem vinculado
                    embarque_itens = EmbarqueItem.query.filter_by(
                        separacao_lote_id=separacao.separacao_lote_id
                    ).all()

                    for embarque_item in embarque_itens:
                        # Cancelar EmbarqueItem
                        embarque_item.status = 'cancelado'
                        embarques_cancelados += 1
                        logger.info(f"      🚫 EmbarqueItem cancelado: embarque_id={embarque_item.embarque_id}, "
                                  f"lote={separacao.separacao_lote_id}")

            if embarques_cancelados > 0:
                logger.info(f"   ✅ {embarques_cancelados} itens de embarque cancelados")

            # 3. EXCLUIR todas as Separacao do pedido (incluindo faturadas)
            separacoes_excluidas = Separacao.query.filter_by(
                num_pedido=num_pedido
            ).delete(synchronize_session=False)

            if separacoes_excluidas > 0:
                logger.info(f"   ✅ {separacoes_excluidas} separações EXCLUÍDAS")

            # 4. EXCLUIR itens da CarteiraPrincipal
            itens_excluidos = CarteiraPrincipal.query.filter_by(
                num_pedido=num_pedido
            ).delete(synchronize_session=False)

            if itens_excluidos > 0:
                logger.info(f"   ✅ {itens_excluidos} itens da carteira EXCLUÍDOS")

            # 4.5 EXCLUIR SaldoStandby do pedido
            from app.carteira.models import SaldoStandby
            standby_excluidos = SaldoStandby.query.filter_by(
                num_pedido=num_pedido
            ).delete(synchronize_session=False)
            if standby_excluidos > 0:
                logger.info(f"   ✅ {standby_excluidos} itens de SaldoStandby EXCLUÍDOS")

            # 5. Remover PreSeparacaoItem se existirem (modelo deprecated mas pode ter dados antigos)
            try:
                from app.carteira.models import PreSeparacaoItem
                presep_removidos = PreSeparacaoItem.query.filter_by(
                    num_pedido=num_pedido
                ).delete(synchronize_session=False)

                if presep_removidos > 0:
                    logger.info(f"   ✅ {presep_removidos} pré-separações EXCLUÍDAS")
            except Exception as e:
                # Se PreSeparacaoItem não existir, ignorar
                pass

            # 6. Log de auditoria
            logger.info(f"✅ CANCELAMENTO COMPLETO: Pedido {num_pedido} EXCLUÍDO DO SISTEMA")
            logger.info(f"   - EmbarqueItens cancelados: {embarques_cancelados}")
            logger.info(f"   - Separações excluídas: {separacoes_excluidas}")
            logger.info(f"   - Itens carteira excluídos: {itens_excluidos}")

            # Commit das alterações
            db.session.commit()

            return True

        except Exception as e:
            logger.error(f"❌ Erro ao processar cancelamento do pedido {num_pedido}: {e}")
            db.session.rollback()
            return False

    def verificar_pedidos_excluidos_odoo(self) -> Dict[str, Any]:
        """
        🔍 VERIFICAÇÃO OTIMIZADA DE PEDIDOS EXCLUÍDOS DO ODOO

        Busca pedidos pendentes na CarteiraPrincipal e verifica se ainda existem no Odoo.
        Se não existirem, processa a exclusão completa.

        OTIMIZAÇÕES:
        1. Query única para pegar pedidos pendentes com saldo > 0
        2. Filtra apenas pedidos do Odoo (VSC, VCD, VFB)
        3. Busca em LOTE no Odoo (100 pedidos por vez) - MUITO MAIS RÁPIDO
        4. Exclui apenas os que não foram encontrados

        PERFORMANCE ESTIMADA:
        - 50 pedidos: ~1-2 segundos
        - 200 pedidos: ~3-5 segundos
        - 500 pedidos: ~8-12 segundos
        - 1000 pedidos: ~15-20 segundos

        Returns:
            Dict com estatísticas da verificação:
            {
                'sucesso': bool,
                'pedidos_verificados': int,
                'pedidos_excluidos': int,
                'pedidos_nao_encontrados': List[str],
                'tempo_execucao': float
            }
        """
        from datetime import datetime
        from app.carteira.models import CarteiraPrincipal
        from sqlalchemy import distinct

        inicio = datetime.now()

        try:
            logger.info("🔍 INICIANDO VERIFICAÇÃO DE PEDIDOS EXCLUÍDOS DO ODOO")

            # ETAPA 1: Buscar pedidos PENDENTES e ÚNICOS (query otimizada)
            logger.info("📊 Buscando pedidos pendentes com saldo > 0...")

            pedidos_pendentes = db.session.query(
                distinct(CarteiraPrincipal.num_pedido)
            ).filter(
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).all()

            # Converter para lista simples
            pedidos_pendentes = [p[0] for p in pedidos_pendentes]

            # Filtrar APENAS pedidos do Odoo
            pedidos_odoo = [p for p in pedidos_pendentes if self.is_pedido_odoo(p)]

            total_pendentes = len(pedidos_pendentes)
            total_odoo = len(pedidos_odoo)

            logger.info(f"   ✅ {total_pendentes} pedidos pendentes encontrados")
            logger.info(f"   ✅ {total_odoo} pedidos do Odoo para verificar")

            if total_odoo == 0:
                logger.info("   ℹ️ Nenhum pedido do Odoo para verificar")
                return {
                    'sucesso': True,
                    'pedidos_verificados': 0,
                    'pedidos_excluidos': 0,
                    'pedidos_nao_encontrados': [],
                    'tempo_execucao': (datetime.now() - inicio).total_seconds()
                }

            # ETAPA 2: Verificar em LOTE no Odoo (muito mais rápido!)
            logger.info(f"🔍 Verificando existência de {total_odoo} pedidos no Odoo (em lotes)...")

            pedidos_nao_encontrados = []
            lote_size = 100  # Buscar 100 pedidos por vez

            for i in range(0, len(pedidos_odoo), lote_size):
                lote = pedidos_odoo[i:i + lote_size]
                lote_num = (i // lote_size) + 1
                total_lotes = (len(pedidos_odoo) + lote_size - 1) // lote_size

                logger.info(f"   📦 Verificando lote {lote_num}/{total_lotes} ({len(lote)} pedidos)...")

                # Busca otimizada: apenas ID e name
                domain = [('name', 'in', lote)]

                try:
                    pedidos_encontrados = self.connection.search_read(
                        model='sale.order',
                        domain=domain,
                        fields=['name', 'state'],  # Apenas campos mínimos
                        limit=len(lote) + 10  # Segurança
                    )

                    # Pegar apenas os nomes dos pedidos encontrados (e NÃO cancelados)
                    nomes_encontrados = {
                        p['name'] for p in pedidos_encontrados
                        if p.get('state') != 'cancel'
                    }

                    # Identificar os que NÃO foram encontrados ou estão cancelados
                    nao_encontrados_lote = [p for p in lote if p not in nomes_encontrados]

                    if nao_encontrados_lote:
                        logger.warning(f"      ⚠️ {len(nao_encontrados_lote)} pedidos NÃO encontrados ou cancelados neste lote")
                        pedidos_nao_encontrados.extend(nao_encontrados_lote)
                    else:
                        logger.info(f"      ✅ Todos os {len(lote)} pedidos do lote encontrados no Odoo")

                except Exception as e:
                    logger.error(f"      ❌ Erro ao verificar lote {lote_num}: {e}")
                    # Continuar com próximo lote mesmo em caso de erro
                    continue

            # ETAPA 3: Processar exclusões
            total_excluidos = 0

            if pedidos_nao_encontrados:
                logger.warning(f"🚨 {len(pedidos_nao_encontrados)} pedidos NÃO encontrados no Odoo - processando exclusão...")

                for num_pedido in pedidos_nao_encontrados:
                    try:
                        logger.info(f"   🗑️ Excluindo pedido {num_pedido}...")
                        sucesso = self._processar_cancelamento_pedido(num_pedido)

                        if sucesso:
                            total_excluidos += 1

                    except Exception as e:
                        logger.error(f"   ❌ Erro ao excluir pedido {num_pedido}: {e}")

                logger.info(f"✅ {total_excluidos}/{len(pedidos_nao_encontrados)} pedidos excluídos com sucesso")
            else:
                logger.info("✅ Todos os pedidos pendentes existem no Odoo - nenhuma exclusão necessária")

            tempo_total = (datetime.now() - inicio).total_seconds()

            logger.info("=" * 80)
            logger.info(f"✅ VERIFICAÇÃO CONCLUÍDA em {tempo_total:.2f}s")
            logger.info(f"   Pedidos verificados: {total_odoo}")
            logger.info(f"   Pedidos excluídos: {total_excluidos}")
            logger.info("=" * 80)

            return {
                'sucesso': True,
                'pedidos_verificados': total_odoo,
                'pedidos_excluidos': total_excluidos,
                'pedidos_nao_encontrados': pedidos_nao_encontrados,
                'tempo_execucao': tempo_total
            }

        except Exception as e:
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.error(f"❌ Erro na verificação de pedidos excluídos: {e}")
            logger.error(traceback.format_exc())

            return {
                'sucesso': False,
                'erro': str(e),
                'tempo_execucao': tempo_total
            }

    def obter_carteira_pendente(self, data_inicio=None, data_fim=None, pedidos_especificos=None,
                               modo_incremental=False, minutos_janela=70):
        """
        Obter carteira pendente do Odoo com filtro combinado inteligente

        Args:
            data_inicio: Data início para filtro
            data_fim: Data fim para filtro
            pedidos_especificos: Lista de pedidos específicos
            modo_incremental: Se True, busca por write_date sem filtrar qty_saldo
            minutos_janela: Janela de tempo em minutos para modo incremental
        """
        logger.info("Buscando carteira pendente do Odoo com filtro inteligente...")
        
        try:
            # Conectar ao Odoo
            if not self.connection:
                return {
                    'sucesso': False,
                    'erro': 'Conexão com Odoo não disponível',
                    'dados': []
                }
            
            # OTIMIZAÇÃO: Em modo incremental, não precisa buscar pedidos existentes
            from app.carteira.models import CarteiraPrincipal
            from app import db

            pedidos_na_carteira = set()

            # Em modo incremental, o write_date já garante que pegamos o que precisa
            if not modo_incremental:
                logger.info("📋 Coletando pedidos existentes na carteira para filtro...")

                for pedido in db.session.query(CarteiraPrincipal.num_pedido).distinct().all():
                    if pedido[0] and self.is_pedido_odoo(pedido[0]):
                        pedidos_na_carteira.add(pedido[0])

                logger.info(f"✅ {len(pedidos_na_carteira)} pedidos Odoo existentes serão incluídos no filtro")
            else:
                logger.info("🚀 Modo incremental: pulando busca de pedidos existentes (otimização)")

            # Montar domain baseado no modo
            if modo_incremental:
                # MODO INCREMENTAL: busca por write_date OU date_order se fornecida
                from app.utils.timezone import agora_utc
                from datetime import timedelta

                # Se tem data_inicio/fim, usar create_date para importação histórica
                if data_inicio or data_fim:
                    domain = [
                        '&',  # AND entre os filtros
                        ('order_id.state', 'in', ['draft', 'sent', 'sale', 'done']),
                        '|',  # OR entre tipos de pedido
                        '|',
                        '|',
                        '|',
                        ('order_id.l10n_br_tipo_pedido', '=', 'venda'),
                        ('order_id.l10n_br_tipo_pedido', '=', 'bonificacao'),
                        ('order_id.l10n_br_tipo_pedido', '=', 'industrializacao'),
                        ('order_id.l10n_br_tipo_pedido', '=', 'exportacao'),
                        ('order_id.l10n_br_tipo_pedido', '=', 'venda-industrializacao')
                        # NÃO filtrar por qty_saldo > 0!
                    ]
                    logger.info("🔄 MODO INCREMENTAL COM DATAS: usando create_date para importação histórica")
                    logger.info("   ✅ Filtrando apenas pedidos de Venda e Bonificação")
                else:
                    # Modo incremental normal: usar write_date
                    # 🆕 INCLUIR pedidos cancelados para detectar cancelamentos
                    data_corte = agora_utc() - timedelta(minutes=minutos_janela)
                    momento_atual = agora_utc()

                    domain = [
                        '&',  # AND entre todos os filtros
                        ('order_id.write_date', '>=', data_corte.isoformat()),
                        ('order_id.write_date', '<=', momento_atual.isoformat()),
                        ('order_id.state', 'in', ['draft', 'sent', 'sale', 'cancel']),  # 🆕 INCLUIR 'cancel'
                        '|',  # OR entre tipos de pedido
                        '|',
                        '|',
                        '|',
                        ('order_id.l10n_br_tipo_pedido', '=', 'venda'),
                        ('order_id.l10n_br_tipo_pedido', '=', 'bonificacao'),
                        ('order_id.l10n_br_tipo_pedido', '=', 'industrializacao'),
                        ('order_id.l10n_br_tipo_pedido', '=', 'exportacao'),
                        ('order_id.l10n_br_tipo_pedido', '=', 'venda-industrializacao')
                        # NÃO filtrar por qty_saldo > 0!
                    ]
                    logger.info(f"🔄 MODO INCREMENTAL: buscando alterações dos últimos {minutos_janela} minutos")
                    logger.info(f"📅 Data corte UTC: {data_corte.isoformat()}")
                    logger.info("   🆕 INCLUINDO pedidos cancelados para detectar cancelamentos")

                    # Incluir pedidos em SaldoStandby ativo para garantir atualização
                    # mesmo fora da janela de write_date (bug: pedidos cancelados no Odoo
                    # mas com standby ativo nunca eram re-consultados)
                    try:
                        from app.utils.database_helpers import ensure_connection
                        ensure_connection()
                        from app.carteira.models import SaldoStandby
                        pedidos_standby = db.session.query(
                            SaldoStandby.num_pedido
                        ).filter(
                            SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
                        ).distinct().all()

                        if pedidos_standby:
                            nomes_standby = [p.num_pedido for p in pedidos_standby]
                            # FIX: Reconstruir domain com OR correto em notação polonesa
                            # A versão anterior ('|' + domain + [standby]) quebrava o domain:
                            # o '|' consumia apenas 2 operandos, e (name IN standby) ficava
                            # como AND no topo — restringindo TUDO a apenas pedidos standby.
                            #
                            # Correto: ((write_date ∈ janela) OR (name ∈ standby))
                            #          AND state AND tipo_pedido
                            domain = [
                                '|',  # OR entre janela temporal e standby
                                '&',  # AND das duas condições de write_date
                                ('order_id.write_date', '>=', data_corte.isoformat()),
                                ('order_id.write_date', '<=', momento_atual.isoformat()),
                                ('order_id.name', 'in', nomes_standby),
                                # Resto: AND implícito no topo
                                ('order_id.state', 'in', ['draft', 'sent', 'sale', 'cancel']),
                                '|', '|', '|', '|',
                                ('order_id.l10n_br_tipo_pedido', '=', 'venda'),
                                ('order_id.l10n_br_tipo_pedido', '=', 'bonificacao'),
                                ('order_id.l10n_br_tipo_pedido', '=', 'industrializacao'),
                                ('order_id.l10n_br_tipo_pedido', '=', 'exportacao'),
                                ('order_id.l10n_br_tipo_pedido', '=', 'venda-industrializacao')
                            ]
                            logger.info(f"   📋 Domain com SaldoStandby: {len(nomes_standby)} pedidos standby, {len(domain)} condições no domain")
                    except Exception as e:
                        logger.warning(f"⚠️ Não foi possível incluir pedidos standby: {e}")
                        # Degradação graceful — sync continua sem os standby
            elif pedidos_na_carteira:
                # MODO TRADICIONAL com pedidos existentes: usar filtro OR
                domain = [
                    '&',  # AND entre TODOS os filtros
                    ('order_id.state', 'in', ['draft', 'sent', 'sale', 'invoiced']),  # Status válido sempre
                    '|',  # OR entre tipos de pedido
                    '|',
                    '|',
                    '|',
                    ('order_id.l10n_br_tipo_pedido', '=', 'venda'),
                    ('order_id.l10n_br_tipo_pedido', '=', 'bonificacao'),
                    ('order_id.l10n_br_tipo_pedido', '=', 'industrializacao'),
                    ('order_id.l10n_br_tipo_pedido', '=', 'exportacao'),
                    ('order_id.l10n_br_tipo_pedido', '=', 'venda-industrializacao'),
                    '|',  # OR entre as duas condições abaixo
                    ('qty_saldo', '>', 0),  # Novos pedidos com saldo
                    ('order_id.name', 'in', list(pedidos_na_carteira))  # OU pedidos já existentes
                ]
                logger.info("🔍 Usando filtro combinado: (qty_saldo > 0) OU (pedidos existentes)")
                logger.info("   ✅ Filtrando apenas pedidos de Venda e Bonificação")
            else:
                # MODO TRADICIONAL carteira vazia: apenas qty_saldo > 0
                domain = [
                    '&',  # AND entre todos os filtros
                    ('qty_saldo', '>', 0),  # Carteira pendente
                    ('order_id.state', 'in', ['draft', 'sent', 'sale']),  # Status válido
                    '|',  # OR entre tipos de pedido
                    '|',
                    '|',
                    '|',
                    ('order_id.l10n_br_tipo_pedido', '=', 'venda'),
                    ('order_id.l10n_br_tipo_pedido', '=', 'bonificacao'),
                    ('order_id.l10n_br_tipo_pedido', '=', 'industrializacao'),
                    ('order_id.l10n_br_tipo_pedido', '=', 'exportacao'),
                    ('order_id.l10n_br_tipo_pedido', '=', 'venda-industrializacao')
                ]
                logger.info("🔍 Carteira vazia - usando apenas filtro qty_saldo > 0")
                logger.info("   ✅ Filtrando apenas pedidos de Venda e Bonificação")
            
            # Adicionar filtros opcionais de data se fornecidos
            # IMPORTANTE: Usar create_date para buscar pedidos CRIADOS no período
            # FILTRO ADICIONAL: Não buscar pedidos criados antes de 15/07/2025
            data_corte_minima = '2025-07-15'

            # ⚠️ REGRA: Se pedidos_especificos fornecido, NÃO aplicar filtro de data automático
            if pedidos_especificos:
                # Quando pedidos específicos são fornecidos, filtrar APENAS por eles
                domain.append(('order_id.name', 'in', pedidos_especificos))
                logger.info(f"🎯 Filtrando APENAS {len(pedidos_especificos)} pedido(s) específico(s): {pedidos_especificos}")
            else:
                # Aplicar o filtro de data mínima APENAS quando não há pedidos específicos
                if data_inicio:
                    # Se data_inicio for posterior a 15/07/2025, usar data_inicio
                    # Senão, usar 15/07/2025
                    if data_inicio >= data_corte_minima:
                        domain.append(('order_id.create_date', '>=', data_inicio))
                    else:
                        logger.warning(f"Data início {data_inicio} anterior a {data_corte_minima}, usando data de corte mínima")
                        domain.append(('order_id.create_date', '>=', data_corte_minima))
                else:
                    # Sem data_inicio especificada, aplicar data de corte mínima
                    domain.append(('order_id.create_date', '>=', data_corte_minima))
                    logger.info(f"Aplicando filtro automático: create_date >= {data_corte_minima}")

                if data_fim:
                    domain.append(('order_id.create_date', '<=', data_fim))
            
            # Campos básicos necessários (incluindo impostos da linha)
            campos_basicos = [
                'id', 'order_id', 'product_id', 'product_uom', 'product_uom_qty',
                'qty_saldo', 'qty_cancelado', 'price_unit',
                # Impostos da linha
                'l10n_br_icms_valor', 'l10n_br_icmsst_valor',
                'l10n_br_pis_valor', 'l10n_br_cofins_valor'
            ]
            
            logger.info("📡 Executando query no Odoo com filtro inteligente...")
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
                'commitment_date', 'picking_note', 'tag_ids', 'write_date'
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
            carrier_partner_ids = set()  # OTIMIZAÇÃO: IDs de transportadoras para REDESPACHO

            # Primeiro, coletar IDs de transportadoras que podem ser usadas em REDESPACHO
            carrier_ids_to_fetch = set()
            for pedido in pedidos:
                if pedido.get('partner_id'):
                    partner_ids.add(pedido['partner_id'][0])
                if pedido.get('partner_shipping_id'):
                    shipping_ids.add(pedido['partner_shipping_id'][0])

                # OTIMIZAÇÃO: Detectar pedidos com REDESPACHO e coletar carrier_id
                if pedido.get('incoterm') and pedido.get('carrier_id'):
                    incoterm_texto = str(pedido.get('incoterm', ''))
                    if 'RED' in incoterm_texto.upper() or 'REDESPACHO' in incoterm_texto.upper():
                        carrier_id = pedido['carrier_id'][0] if isinstance(pedido['carrier_id'], list) else pedido['carrier_id']
                        carrier_ids_to_fetch.add(carrier_id)

            # Se houver carriers para buscar, fazer query adicional para obter os partner_ids
            cache_carriers = {}  # {carrier_id: carrier_dict} — passado ao mapper para evitar N+1
            if carrier_ids_to_fetch:
                logger.info(f"🚚 Detectados {len(carrier_ids_to_fetch)} pedidos com REDESPACHO")
                carrier_data = self.connection.search_read(
                    'delivery.carrier',
                    [('id', 'in', list(carrier_ids_to_fetch))],
                    ['id', 'name', 'l10n_br_partner_id']
                )
                for carrier in (carrier_data or []):
                    cache_carriers[carrier['id']] = carrier
                    if carrier.get('l10n_br_partner_id'):
                        partner_id = carrier['l10n_br_partner_id'][0] if isinstance(carrier['l10n_br_partner_id'], list) else carrier['l10n_br_partner_id']
                        carrier_partner_ids.add(partner_id)

            # Combinar todos os partner IDs (incluindo transportadoras)
            all_partner_ids = list(partner_ids | shipping_ids | carrier_partner_ids)
            
            campos_partner = [
                'id', 'name', 'l10n_br_cnpj', 'l10n_br_razao_social',
                'l10n_br_municipio_id', 'state_id', 'zip',
                'l10n_br_endereco_bairro', 'l10n_br_endereco_numero',
                'street', 'phone', 'agendamento',
                # Desconto contratual
                'x_studio_desconto_contratual', 'x_studio_desconto'
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
                        cache_produtos, cache_categorias,
                        cache_carriers=cache_carriers
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
    
    def _mapear_item_otimizado(self, linha, cache_pedidos, cache_partners, cache_produtos, cache_categorias, cache_carriers=None):
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
            
            # 🚛 LÓGICA ESPECIAL PARA REDESPACHO
            # Se o incoterm for REDESPACHO, usar endereço da transportadora
            if pedido.get('incoterm') and pedido.get('carrier_id'):
                incoterm_info = pedido['incoterm']
                incoterm_texto = ''
                
                # Extrair texto do incoterm
                if isinstance(incoterm_info, list) and len(incoterm_info) > 1:
                    incoterm_texto = incoterm_info[1].upper()
                elif isinstance(incoterm_info, str):
                    incoterm_texto = incoterm_info.upper()
                
                # Verificar se é REDESPACHO
                if 'RED' in incoterm_texto or 'REDESPACHO' in incoterm_texto:
                    carrier_id = pedido['carrier_id'][0] if isinstance(pedido['carrier_id'], list) else pedido['carrier_id']
                    
                    # Buscar dados da transportadora (cache batch em vez de N+1)
                    try:
                        # Usar cache batch construído em _processar_dados_carteira_com_multiplas_queries
                        if cache_carriers and carrier_id in cache_carriers:
                            carrier_data = [cache_carriers[carrier_id]]
                        else:
                            # Fallback: chamada individual se cache indisponível
                            carrier_data = self.connection.search_read(
                                'delivery.carrier',
                                [('id', '=', carrier_id)],
                                ['id', 'name', 'l10n_br_partner_id']
                            )
                        
                        if carrier_data and carrier_data[0].get('l10n_br_partner_id'):
                            # Pegar o ID do parceiro da transportadora
                            transportadora_partner_id = carrier_data[0]['l10n_br_partner_id'][0] if isinstance(carrier_data[0]['l10n_br_partner_id'], list) else carrier_data[0]['l10n_br_partner_id']
                            
                            # OTIMIZAÇÃO: Usar apenas cache (já buscamos todos os partners no batch)
                            endereco = cache_partners.get(transportadora_partner_id, {})

                            if endereco:
                                # Log detalhado do endereço substituído
                                municipio = endereco.get('l10n_br_municipio_id', ['', ''])[1] if isinstance(endereco.get('l10n_br_municipio_id'), list) else ''
                                logger.info(f"   📍 Endereço REDESPACHO (cache): {municipio} - {endereco.get('street', 'N/A')}")
                            else:
                                # Se não estiver no cache, usar endereço padrão (evitar query adicional)
                                logger.warning(f"⚠️ Partner da transportadora {transportadora_partner_id} não encontrado no cache")
                        else:
                            logger.warning(f"⚠️ Transportadora {carrier_id} não possui l10n_br_partner_id configurado")
                            
                    except Exception as e:
                        logger.error(f"❌ Erro ao buscar endereço da transportadora: {e}")
            
            # Se não é REDESPACHO ou não conseguiu o endereço da transportadora, usar o padrão
            if not endereco and pedido.get('partner_shipping_id'):
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

                    # 💰 IMPOSTOS DA LINHA (Odoo sale.order.line)
                    'icms_valor': linha.get('l10n_br_icms_valor', 0) or 0,
                    'icmsst_valor': linha.get('l10n_br_icmsst_valor', 0) or 0,
                    'pis_valor': linha.get('l10n_br_pis_valor', 0) or 0,
                    'cofins_valor': linha.get('l10n_br_cofins_valor', 0) or 0,

                    # 🏷️ DESCONTO CONTRATUAL (Odoo res.partner)
                    'desconto_contratual': cliente.get('x_studio_desconto_contratual', False) or False,
                    'desconto_percentual': cliente.get('x_studio_desconto', 0) or 0,

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
                    # FALLBACK para nome_cidade: usa municipio_entrega ou municipio do cliente
                    'nome_cidade': municipio_entrega_nome or municipio_nome or '',
                    # FALLBACK para cod_uf: usa estado_entrega ou estado do cliente
                    'cod_uf': estado_entrega_uf or estado_uf or 'SP',  # Default SP se tudo falhar
                    'cep_endereco_ent': endereco.get('zip', ''),  # CEP usa campo 'zip'
                    'bairro_endereco_ent': endereco.get('l10n_br_endereco_bairro', ''),
                    'rua_endereco_ent': endereco.get('street', ''),
                    'endereco_ent': endereco.get('l10n_br_endereco_numero', ''),
                    'telefone_endereco_ent': endereco.get('phone', ''),
                    
                    # 📅 DADOS OPERACIONAIS
                    # NOTA: Campos de agendamento/expedição/carga foram movidos para Separacao
                    # CarteiraPrincipal contém apenas dados do pedido original do Odoo

                    # 🏷️ TAGS DO PEDIDO (ODOO)
                    'tags_pedido': self._processar_tags_pedido(pedido.get('tag_ids', [])),

                    # 🏳️ CAMPO ATIVO
                    'ativo': True,  # Todos os registros importados são ativos

                    # 🔄 SINCRONIZAÇÃO INCREMENTAL
                    'odoo_write_date': pedido.get('write_date'),  # write_date do Odoo
                    'ultima_sync': agora_utc_naive(),  # momento da sincronização

                    # 🛡️ AUDITORIA (campos corretos do modelo)
                    'created_at': agora_utc_naive(),
                    'updated_at': agora_utc_naive(),
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
                'created_at': agora_utc_naive(),
                'updated_at': agora_utc_naive(),
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
                'num_pedido', 'cod_produto', 'status_pedido',
                'metodo_entrega_pedido', 'forma_agendamento'
            ]
            
            for campo in campos_varchar50:
                if campo in item_sanitizado and item_sanitizado[campo]:
                    valor = str(item_sanitizado[campo])
                    if len(valor) > 50:
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
                        item_sanitizado[campo] = valor[:20]
            
            # Campos que DEVEM ser texto (não podem ser boolean)
            # NOTA: Campos protocolo, roteirizacao foram movidos para Separacao
            campos_texto = [
                'observ_ped_1', 'num_pedido', 'cod_produto', 'pedido_cliente',
                'status_pedido', 'cnpj_cpf', 'raz_social', 'raz_social_red',
                'municipio', 'estado', 'vendedor', 'equipe_vendas', 'nome_produto',
                'unid_medida_produto', 'embalagem_produto', 'materia_prima_produto',
                'categoria_produto', 'cond_pgto_pedido', 'forma_pgto_pedido',
                'incoterm', 'metodo_entrega_pedido', 'cliente_nec_agendamento',
                'cnpj_endereco_ent', 'empresa_endereco_ent', 'cep_endereco_ent',
                'nome_cidade', 'cod_uf', 'bairro_endereco_ent', 'rua_endereco_ent',
                'endereco_ent', 'telefone_endereco_ent', 'forma_agendamento',
                'created_by', 'updated_by'
            ]
            
            # Campos boolean-like onde "sim"/"não" é valor válido
            # Demais campos: False do Odoo XML-RPC = campo vazio, converter para ''
            campos_boolean_like = {'cliente_nec_agendamento'}

            # Converter campos de texto
            for campo in campos_texto:
                if campo in item_sanitizado:
                    valor = item_sanitizado[campo]
                    if isinstance(valor, bool):
                        if campo in campos_boolean_like:
                            item_sanitizado[campo] = 'sim' if valor else 'não'
                        else:
                            # Odoo retorna False para campos vazios via XML-RPC
                            item_sanitizado[campo] = ''
                    elif valor is None:
                        item_sanitizado[campo] = ''
                    else:
                        item_sanitizado[campo] = str(valor)
            
            # Campos numéricos - garantir tipo correto
            # NOTA: Campos de estoque, separação, totalizadores foram movidos para Separacao
            campos_numericos = [
                'qtd_produto_pedido', 'qtd_saldo_produto_pedido',
                'qtd_cancelada_produto_pedido', 'preco_produto_pedido',
                # Campos de impostos
                'icms_valor', 'icmsst_valor', 'pis_valor', 'cofins_valor',
                'desconto_percentual'
            ]

            for campo in campos_numericos:
                if campo in item_sanitizado and item_sanitizado[campo] is not None:
                    try:
                        item_sanitizado[campo] = float(item_sanitizado[campo])
                    except (ValueError, TypeError):
                        item_sanitizado[campo] = 0.0

            # Campos booleanos - garantir tipo correto
            if 'ativo' in item_sanitizado:
                item_sanitizado['ativo'] = bool(item_sanitizado.get('ativo', True))
            if 'desconto_contratual' in item_sanitizado:
                item_sanitizado['desconto_contratual'] = bool(item_sanitizado.get('desconto_contratual', False))

            # 🔧 FALLBACK CRÍTICO: Garantir que cod_uf e nome_cidade NUNCA sejam NULL
            if not item_sanitizado.get('cod_uf') or item_sanitizado.get('cod_uf') == '':
                # Tentar pegar do estado
                if item_sanitizado.get('estado'):
                    item_sanitizado['cod_uf'] = item_sanitizado['estado'][:2]
                else:
                    # Default para SP se tudo falhar
                    item_sanitizado['cod_uf'] = 'SP'
                    logger.warning(f"⚠️ cod_uf vazio para {item_sanitizado.get('num_pedido')} - usando SP como default")

            if not item_sanitizado.get('nome_cidade') or item_sanitizado.get('nome_cidade') == '':
                # Tentar pegar do municipio
                if item_sanitizado.get('municipio'):
                    item_sanitizado['nome_cidade'] = item_sanitizado['municipio']
                else:
                    # Default vazio é aceitável para cidade
                    item_sanitizado['nome_cidade'] = ''

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
                        item_sanitizado[campo] = valor_uf[:2]
            
            # ⚠️ CAMPOS COM LIMITE DE 10 CARACTERES
            campos_varchar10 = ['cliente_nec_agendamento', 'cep_endereco_ent']
            
            for campo in campos_varchar10:
                if campo in item_sanitizado and item_sanitizado[campo]:
                    valor = str(item_sanitizado[campo])
                    if len(valor) > 10:
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
                        item_sanitizado[campo] = valor[:100]
            
            dados_sanitizados.append(item_sanitizado)
        
        return dados_sanitizados
    
    def _format_date(self, data_str: Any) -> Optional[date]:
        """
        Formata string de data para objeto date.
        Datas com hora (datetime do Odoo) sao convertidas de UTC para Brasil
        antes de extrair a data, para evitar que registros criados entre 21h-23:59 BRT
        (que sao 00h-02:59 UTC do dia seguinte) fiquem com data errada.
        """
        if not data_str:
            return None
        try:
            if isinstance(data_str, str):
                # Tenta formato datetime primeiro (Odoo retorna UTC)
                if ' ' in data_str and ':' in data_str:
                    try:
                        dt_brasil = odoo_para_local(data_str)
                        if dt_brasil:
                            return dt_brasil.date()
                    except Exception:
                        pass
                # Tenta formatos date-only (sem conversao de timezone)
                for formato in ['%Y-%m-%d', '%d/%m/%Y']:
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

    def _obter_snapshot_custo(self, cod_produto: str, cache_custos: Dict = None) -> Dict[str, Any]:
        """
        Obtém snapshot do custo considerado atual para um produto.

        Usado durante inserção de novos itens na CarteiraPrincipal para
        capturar o custo vigente no momento da entrada do pedido.

        Args:
            cod_produto: Código do produto
            cache_custos: Dict opcional com custos pre-carregados em batch {cod_produto: CustoConsiderado}

        Returns:
            Dict com campos de snapshot ou dict vazio se não encontrar custo
        """
        try:
            # Usar cache batch se disponível (evita N+1)
            if cache_custos is not None:
                custo = cache_custos.get(cod_produto)
            else:
                custo = CustoConsiderado.query.filter_by(
                    cod_produto=cod_produto,
                    custo_atual=True
                ).first()

            if custo:
                return {
                    'custo_unitario_snapshot': float(custo.custo_considerado) if custo.custo_considerado else None,
                    'custo_tipo_snapshot': custo.tipo_custo_selecionado,
                    'custo_vigencia_snapshot': custo.vigencia_inicio,
                    'custo_producao_snapshot': float(custo.custo_producao) if custo.custo_producao else None
                }
        except Exception as e:
            logger.debug(f"Erro ao obter snapshot de custo para {cod_produto}: {e}")

        return {}

    def _calcular_margem_bruta(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula margem bruta e liquida com base no snapshot de custo e preco de venda.

        MELHORIAS v2:
        - Percentual de perda sobre custo (ParametroCusteio.PERCENTUAL_PERDA)
        - Comissao por regras (RegraComissao - soma das aplicaveis)
        - Tratamento especial para bonificacao (forma_pgto = 'SEM PAGAMENTO')

        Formulas VENDA NORMAL:
        custo_material_com_perda = custo_unitario * (1 + percentual_perda/100)
        custo_producao_com_perda = custo_producao * (1 + percentual_perda/100) if custo_producao else 0.0
        comissao_valor = preco * comissao_percentual / 100
        margem_bruta = preco - icms - pis - cofins - custo_material_com_perda - desconto - frete - custo_financeiro - comissao
        margem_liquida = margem_bruta - custo_operacao - custo_producao_com_perda

        Formulas BONIFICACAO (forma_pgto = 'SEM PAGAMENTO'):
        margem_bruta = -custo_material_com_perda - icms - frete - custo_financeiro
        (NAO inclui: comissao, desconto contratual, pis/cofins)

        Args:
            item: Dict com dados do item (deve conter snapshot ja preenchido)

        Returns:
            Dict com campos de margem calculados
        """
        from app.custeio.models import CustoFrete, ParametroCusteio, RegraComissao

        resultado = {}

        try:
            preco = item.get('preco_produto_pedido')
            custo_unitario = item.get('custo_unitario_snapshot')
            qtd = item.get('qtd_produto_pedido')

            # Precisa de preco, custo e quantidade para calcular
            if preco is None or custo_unitario is None or qtd is None:
                return resultado

            preco = float(preco)
            custo_unitario = float(custo_unitario)
            qtd = float(qtd)

            if preco <= 0 or qtd <= 0:
                return resultado

            # ============================================
            # PARAMETROS GLOBAIS
            # ============================================
            percentual_perda = ParametroCusteio.obter_valor('PERCENTUAL_PERDA', 0.0)
            custo_financeiro_percentual = ParametroCusteio.obter_valor('CUSTO_FINANCEIRO_PERCENTUAL', 0.0)
            custo_operacao_percentual = ParametroCusteio.obter_valor('CUSTO_OPERACAO_PERCENTUAL', 0.0)

            # ============================================
            # CUSTO DE PRODUCAO (snapshot)
            # ============================================
            custo_producao = item.get('custo_producao_snapshot')
            custo_producao = float(custo_producao) if custo_producao else 0.0

            # ============================================
            # CUSTOS COM PERDA (separados)
            # Material entra na margem bruta
            # Producao entra apenas na margem liquida
            # ============================================
            custo_material_com_perda = custo_unitario * (1 + percentual_perda / 100)
            custo_producao_com_perda = custo_producao * (1 + percentual_perda / 100) if custo_producao else 0.0

            # ============================================
            # IMPOSTOS POR UNIDADE
            # ============================================
            icms_valor = item.get('icms_valor')
            pis_valor = item.get('pis_valor')
            cofins_valor = item.get('cofins_valor')

            icms_unit = float(icms_valor) / qtd if icms_valor else 0.0
            pis_unit = float(pis_valor) / qtd if pis_valor else 0.0
            cofins_unit = float(cofins_valor) / qtd if cofins_valor else 0.0

            # ============================================
            # FRETE (percentual sobre preco)
            # ============================================
            incoterm = item.get('incoterm') or ''
            cod_uf = item.get('cod_uf') or ''

            frete_percentual = 0.0
            if incoterm and cod_uf:
                frete_percentual = CustoFrete.buscar_percentual_vigente(incoterm, cod_uf)
            frete_valor = (frete_percentual / 100) * preco

            # ============================================
            # CUSTO FINANCEIRO (percentual sobre preco)
            # ============================================
            custo_financeiro_valor = (custo_financeiro_percentual / 100) * preco

            # ============================================
            # VERIFICAR SE E BONIFICACAO
            # ============================================
            forma_pgto = item.get('forma_pgto_pedido') or ''
            eh_bonificacao = forma_pgto.upper() == 'SEM PAGAMENTO'

            if eh_bonificacao:
                # ============================================
                # MARGEM BRUTA PARA BONIFICACAO
                # NAO inclui: comissao, desconto contratual, PIS/COFINS
                # Custo producao entra apenas na margem liquida
                # ============================================
                margem_bruta = -custo_material_com_perda - icms_unit - custo_financeiro_valor - frete_valor

                # Comissao zerada para bonificacao
                comissao_percentual = 0.0

            else:
                # ============================================
                # DESCONTO CONTRATUAL
                # ============================================
                desconto_percentual_valor = item.get('desconto_percentual')
                desconto_valor = (float(desconto_percentual_valor) / 100) * preco if desconto_percentual_valor else 0.0

                # ============================================
                # COMISSAO (soma das regras aplicaveis)
                # ============================================
                cnpj = item.get('cnpj_cpf') or ''
                raz_social_red = item.get('raz_social_red') or ''
                cod_produto = item.get('cod_produto') or ''
                vendedor = item.get('vendedor') or ''
                equipe = item.get('equipe_vendas') or ''

                comissao_percentual = RegraComissao.calcular_comissao_total(
                    cnpj=cnpj,
                    raz_social_red=raz_social_red,
                    cod_produto=cod_produto,
                    cod_uf=cod_uf,
                    vendedor=vendedor,
                    equipe=equipe
                )
                comissao_valor = (comissao_percentual / 100) * preco

                # ============================================
                # MARGEM BRUTA NORMAL
                # Custo producao entra apenas na margem liquida
                # ============================================
                margem_bruta = (preco - icms_unit - pis_unit - cofins_unit -
                               custo_material_com_perda - desconto_valor -
                               frete_valor - custo_financeiro_valor - comissao_valor)

            margem_bruta_percentual = (margem_bruta / preco * 100) if preco > 0 else 0.0

            # ============================================
            # CUSTO OPERACAO (percentual sobre preco)
            # ============================================
            custo_operacao_valor = (custo_operacao_percentual / 100) * preco

            # ============================================
            # MARGEM LIQUIDA (mesma formula para ambos)
            # Inclui custo de producao com perda
            # ============================================
            margem_liquida = margem_bruta - custo_operacao_valor - custo_producao_com_perda
            margem_liquida_percentual = (margem_liquida / preco * 100) if preco > 0 else 0.0

            resultado = {
                'margem_bruta': round(margem_bruta, 2),
                'margem_bruta_percentual': round(margem_bruta_percentual, 2),
                'margem_liquida': round(margem_liquida, 2),
                'margem_liquida_percentual': round(margem_liquida_percentual, 2),
                'comissao_percentual': round(comissao_percentual, 2),
                # SNAPSHOT DE PARAMETROS (rastreabilidade)
                'frete_percentual_snapshot': round(frete_percentual, 2),
                'custo_financeiro_pct_snapshot': round(custo_financeiro_percentual, 2),
                'custo_operacao_pct_snapshot': round(custo_operacao_percentual, 2),
                'percentual_perda_snapshot': round(percentual_perda, 2)
            }

        except Exception as e:
            logger.debug(f"Erro ao calcular margem: {e}")

        return resultado

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

    def _processar_tags_pedido(self, tag_ids: list, cache_tags: dict = None) -> str:
        """
        🏷️ PROCESSAR TAGS DO PEDIDO

        Busca detalhes das tags no Odoo e retorna JSON formatado

        Args:
            tag_ids: Lista de IDs de tags [1, 2, 3]
            cache_tags: Cache de tags já buscadas (opcional)

        Returns:
            String JSON com tags: '[{"name": "VIP", "color": 5}]' ou None
        """
        import json

        if not tag_ids or not isinstance(tag_ids, list) or len(tag_ids) == 0:
            return None #type: ignore

        try:
            # Se não há cache, criar um vazio
            if cache_tags is None:
                cache_tags = {}

            tags_processadas = []
            tags_para_buscar = []

            # Verificar quais tags já estão no cache
            for tag_id in tag_ids:
                if tag_id in cache_tags:
                    tags_processadas.append(cache_tags[tag_id])
                else:
                    tags_para_buscar.append(tag_id)

            # Buscar tags que não estão no cache
            if tags_para_buscar and self.connection:
                tags_odoo = self.connection.read(
                    'crm.tag',
                    tags_para_buscar,
                    ['id', 'name', 'color']
                )

                for tag in tags_odoo:
                    tag_info = {
                        'name': tag.get('name', ''),
                        'color': tag.get('color', 0)
                    }
                    tags_processadas.append(tag_info)
                    cache_tags[tag['id']] = tag_info  # Adicionar ao cache

            # Retornar JSON se houver tags
            if tags_processadas:
                return json.dumps(tags_processadas, ensure_ascii=False)

            return None #type: ignore

        except Exception as e:
            logger.warning(f"⚠️ Erro ao processar tags: {e}")
            return None #type: ignore

    def _verificar_produto_no_odoo(self, num_pedido: str, cod_produto: str) -> bool:
        """
        🔍 VERIFICAR SE PRODUTO EXISTE NO PEDIDO DO ODOO

        Confirma se um produto ainda existe em um pedido no Odoo.
        Usado para evitar falsos positivos ao deletar produtos.

        Args:
            num_pedido: Número do pedido (ex: VCD2563863)
            cod_produto: Código do produto (ex: 4210176)

        Returns:
            True se produto existe no Odoo, False se foi excluído
        """
        try:
            if not self.connection:
                logger.error("Conexão com Odoo não disponível para verificação")
                return True  # Em caso de erro, assumir que existe (segurança)

            # Buscar linhas do pedido no Odoo que tenham este produto
            linhas = self.connection.search_read(
                'sale.order.line',
                [
                    ('order_id.name', '=', num_pedido),
                    ('product_id.default_code', '=', cod_produto)
                ],
                ['id', 'product_id', 'product_uom_qty']
            )

            existe = len(linhas) > 0
            logger.debug(f"Produto {num_pedido}/{cod_produto} existe no Odoo: {existe}")
            return existe

        except Exception as e:
            logger.error(f"Erro ao verificar produto no Odoo: {num_pedido}/{cod_produto} - {e}")
            return True  # Em caso de erro, assumir que existe (segurança)

    # 🔧 MÉTODOS AUXILIARES CRÍTICOS PARA OPERAÇÃO COMPLETA
    
    # FUNÇÕES REMOVIDAS: 
    # - _verificar_riscos_pre_sincronizacao
    # - _criar_backup_pre_separacoes  
    # Motivo: PreSeparacaoItem foi substituído por Separacao com status='PREVISAO'
    # e não há mais necessidade de verificar riscos de separações cotadas
    
    def _garantir_cadastro_palletizacao_completo(self, dados_carteira: List[Dict]) -> Dict[str, Any]:
        """
        📦 GARANTIR CADASTRO DE PALLETIZAÇÃO PARA TODOS OS PRODUTOS
        
        Esta função garante que TODOS os produtos da carteira tenham um CadastroPalletizacao
        ANTES de processar a importação. Isso evita problemas de produtos não aparecerem
        na carteira agrupada por falta de cadastro.
        
        ESTRATÉGIA:
        1. Coletar todos os produtos únicos dos dados
        2. Verificar quais produtos já têm cadastro
        3. Criar cadastros faltantes com valores padrão
        4. Atualizar nomes de produtos desatualizados
        5. Garantir que todos estejam ativos
        
        Args:
            dados_carteira: Lista de dicionários com dados da carteira
            
        Returns:
            Dict com estatísticas: criados, atualizados, ja_existentes, erros
        """
        from app.producao.models import CadastroPalletizacao
        
        resultado = {
            'criados': 0,
            'atualizados': 0,
            'ja_existentes': 0,
            'erros': 0,
            'produtos_processados': set(),
            'produtos_com_erro': []
        }
        
        try:
            logger.info(f"📦 Iniciando garantia de CadastroPalletizacao para {len(dados_carteira)} registros")
            
            # 1. COLETAR PRODUTOS ÚNICOS
            produtos_unicos = {}
            for item in dados_carteira:
                cod_produto = item.get('cod_produto')
                nome_produto = item.get('nome_produto', '')
                
                if not cod_produto:
                    continue
                    
                # Guardar o nome mais recente/completo
                if cod_produto not in produtos_unicos or len(nome_produto) > len(produtos_unicos[cod_produto]):
                    produtos_unicos[cod_produto] = nome_produto
            
            logger.info(f"📊 {len(produtos_unicos)} produtos únicos identificados")
            
            # 2. VERIFICAR CADASTROS EXISTENTES EM LOTE
            produtos_existentes = set()
            cadastros_existentes = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.cod_produto.in_(list(produtos_unicos.keys()))
            ).all()
            
            # Processar cadastros existentes
            for cadastro in cadastros_existentes:
                produtos_existentes.add(cadastro.cod_produto)
                resultado['produtos_processados'].add(cadastro.cod_produto)
                
                mudancas = False
                
                # Verificar se precisa atualizar o nome
                nome_novo = produtos_unicos[cadastro.cod_produto]
                if nome_novo and (not cadastro.nome_produto or len(nome_novo) > len(cadastro.nome_produto)):
                    logger.debug(f"   📝 Atualizando nome: {cadastro.cod_produto} - '{cadastro.nome_produto}' -> '{nome_novo}'")
                    cadastro.nome_produto = nome_novo
                    mudancas = True
                
                # Garantir que está ativo
                if not cadastro.ativo:
                    logger.info(f"   ✅ Ativando cadastro: {cadastro.cod_produto}")
                    cadastro.ativo = True
                    mudancas = True
                
                # Garantir valores mínimos
                if not cadastro.palletizacao or cadastro.palletizacao <= 0:
                    cadastro.palletizacao = 1.0
                    mudancas = True
                    
                if not cadastro.peso_bruto or cadastro.peso_bruto <= 0:
                    cadastro.peso_bruto = 1.0
                    mudancas = True
                
                if mudancas:
                    resultado['atualizados'] += 1
                else:
                    resultado['ja_existentes'] += 1
            
            # 3. CRIAR CADASTROS FALTANTES
            produtos_faltantes = set(produtos_unicos.keys()) - produtos_existentes
            
            if produtos_faltantes:
                logger.info(f"📝 Criando {len(produtos_faltantes)} cadastros de palletização faltantes...")
                
                for cod_produto in produtos_faltantes:
                    try:
                        nome_produto = produtos_unicos[cod_produto] or f"Produto {cod_produto}"
                        
                        novo_cadastro = CadastroPalletizacao(
                            cod_produto=cod_produto,
                            nome_produto=nome_produto,
                            palletizacao=1.0,  # Valor padrão seguro
                            peso_bruto=1.0,    # Valor padrão seguro
                            ativo=True,
                            # Campos opcionais com valores padrão
                            altura_cm=0,
                            largura_cm=0,
                            comprimento_cm=0
                        )
                        
                        # Adicionar campos created_by/updated_by se existirem no modelo
                        if hasattr(CadastroPalletizacao, 'created_by'):
                            novo_cadastro.created_by = 'ImportacaoOdoo'
                        if hasattr(CadastroPalletizacao, 'updated_by'):
                            novo_cadastro.updated_by = 'ImportacaoOdoo'
                        
                        db.session.add(novo_cadastro)
                        resultado['criados'] += 1
                        resultado['produtos_processados'].add(cod_produto)
                        
                        if resultado['criados'] <= 10:  # Log primeiros 10
                            logger.info(f"   ✅ Criado: {cod_produto} - {nome_produto[:50]}")
                        
                    except Exception as e:
                        logger.error(f"   ❌ Erro ao criar cadastro para {cod_produto}: {e}")
                        resultado['erros'] += 1
                        resultado['produtos_com_erro'].append({
                            'cod_produto': cod_produto,
                            'erro': str(e)
                        })
            
            # 4. COMMIT DAS ALTERAÇÕES
            if resultado['criados'] > 0 or resultado['atualizados'] > 0:
                try:
                    db.session.commit()
                    logger.info(f"✅ Cadastros de palletização salvos com sucesso")
                except Exception as e:
                    logger.error(f"❌ Erro ao salvar cadastros de palletização: {e}")
                    db.session.rollback()
                    resultado['erros'] += resultado['criados'] + resultado['atualizados']
                    resultado['criados'] = 0
                    resultado['atualizados'] = 0
                    raise
            
            # 5. VERIFICAÇÃO FINAL
            total_esperado = len(produtos_unicos)
            total_processado = len(resultado['produtos_processados'])
            
            if total_processado < total_esperado:
                produtos_nao_processados = set(produtos_unicos.keys()) - resultado['produtos_processados']
                logger.warning(f"⚠️ {len(produtos_nao_processados)} produtos não foram processados: {list(produtos_nao_processados)[:10]}")
            
            # Log de produtos com erro
            if resultado['produtos_com_erro']:
                logger.error(f"❌ Produtos com erro de criação:")
                for erro in resultado['produtos_com_erro'][:5]:
                    logger.error(f"   - {erro['cod_produto']}: {erro['erro']}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro crítico em _garantir_cadastro_palletizacao_completo: {e}")
            return resultado
    
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
                'timestamp': agora_utc_naive()
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
    
    
    def sincronizar_carteira_odoo_com_gestao_quantidades(
        self,
        usar_filtro_pendente=True,
        modo_incremental=False,
        minutos_janela=70,
        primeira_execucao=False,
        pedidos_especificos=None
    ):
        """
        🚀 SINCRONIZAÇÃO INTELIGENTE COM GESTÃO DE QUANTIDADES

        Versão completa que substitui sincronizar_carteira_odoo() com todas as
        funcionalidades originais MAIS gestão inteligente de quantidades.

        FLUXO COMPLETO:
        1. Carrega estado atual em memória
        2. Busca dados novos do Odoo
        3. Calcula diferenças (reduções/aumentos/novos/removidos)
        4. Aplica mudanças respeitando hierarquia
        5. Substitui carteira com dados atualizados
        6. Verificação pós-sincronização com alertas

        Args:
            usar_filtro_pendente (bool): Se True, filtra apenas itens com saldo > 0
            modo_incremental (bool): Se True, busca apenas registros alterados no período
            minutos_janela (int): Janela de tempo em minutos para modo incremental
            pedidos_especificos (list): Lista de números de pedidos específicos para sincronizar

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
            
            # Inicializar variáveis que eram preenchidas pelas etapas removidas
            alertas_pre_sync = {'alertas_criticos': []}  # Não verificamos mais riscos pré-sync
            # backup_result removido - não fazemos mais backup de pré-separações
            
            # FASE 1: ANÁLISE - Carregar estado atual em memória e calcular saldos
            logger.info("📊 Fase 1: Analisando estado atual da carteira e calculando saldos...")
            
            # Importar modelos necessários para cálculo
            from app.faturamento.models import FaturamentoProduto
            from app.separacao.models import Separacao
            from sqlalchemy import func
            from app.utils.database_helpers import retry_on_ssl_error, ensure_connection

            # 🚀 OTIMIZAÇÃO: Buscar TODOS os dados em apenas 3 queries!
            
            # OTIMIZAÇÃO: Filtrar por pedidos_especificos ou modo incremental
            if pedidos_especificos:
                # Modo fallback/específico: carregar apenas os pedidos solicitados
                logger.info(f"   ⚡ Modo específico: carregando apenas {len(pedidos_especificos)} pedidos...")
                todos_itens = CarteiraPrincipal.query.filter(
                    CarteiraPrincipal.num_pedido.in_(pedidos_especificos)
                ).all()
                logger.info(f"   ✅ {len(todos_itens)} itens carregados (apenas pedidos específicos)")
            elif modo_incremental:
                # Primeiro precisamos saber quais pedidos serão afetados
                # Mas ainda não temos os dados do Odoo aqui, então faremos isso depois
                logger.info("   ⚡ Modo incremental: otimização de carga será aplicada após buscar dados do Odoo")
                todos_itens = []  # Será preenchido depois
            else:
                # Modo completo: carregar toda a carteira em memória
                logger.info("   📦 Carregando carteira atual...")
                todos_itens = CarteiraPrincipal.query.all()
                logger.info(f"   ✅ {len(todos_itens)} itens carregados")

            # Query 2: Buscar faturamentos (filtrado se pedidos_especificos)
            if pedidos_especificos:
                logger.info(f"   📦 Carregando faturamentos para {len(pedidos_especificos)} pedidos...")
            else:
                logger.info("   📦 Carregando todos os faturamentos...")

            @retry_on_ssl_error(max_retries=3)
            def buscar_todos_faturamentos():
                query = db.session.query(
                    FaturamentoProduto.origem,
                    FaturamentoProduto.cod_produto,
                    func.sum(FaturamentoProduto.qtd_produto_faturado).label('qtd_faturada')
                ).filter(
                    FaturamentoProduto.status_nf != 'Cancelado'
                )
                # Filtrar por pedidos específicos se fornecido
                if pedidos_especificos:
                    query = query.filter(FaturamentoProduto.origem.in_(pedidos_especificos))
                return query.group_by(
                    FaturamentoProduto.origem,
                    FaturamentoProduto.cod_produto
                ).all()

            faturamentos = buscar_todos_faturamentos()
            faturamentos_dict = {(f.origem, f.cod_produto): float(f.qtd_faturada or 0) for f in faturamentos}
            logger.info(f"   ✅ {len(faturamentos_dict)} faturamentos carregados")

            # Query 3: Buscar separações não sincronizadas (filtrado se pedidos_especificos)
            if pedidos_especificos:
                logger.info(f"   📦 Carregando separações para {len(pedidos_especificos)} pedidos...")
            else:
                logger.info("   📦 Carregando todas as separações não sincronizadas...")

            @retry_on_ssl_error(max_retries=3)
            def buscar_todas_separacoes():
                query = db.session.query(
                    Separacao.num_pedido,
                    Separacao.cod_produto,
                    func.sum(Separacao.qtd_saldo).label('qtd_em_separacao')
                ).filter(
                    Separacao.sincronizado_nf == False
                )
                # Filtrar por pedidos específicos se fornecido
                if pedidos_especificos:
                    query = query.filter(Separacao.num_pedido.in_(pedidos_especificos))
                return query.group_by(
                    Separacao.num_pedido,
                    Separacao.cod_produto
                ).all()

            separacoes = buscar_todas_separacoes()
            separacoes_dict = {(s.num_pedido, s.cod_produto): float(s.qtd_em_separacao or 0) for s in separacoes}
            logger.info(f"   ✅ {len(separacoes_dict)} separações carregadas")
            
            # Criar índice do estado atual usando campos CORRETOS
            carteira_atual = {}
            carteira_nao_odoo = {}  # Guardar pedidos não-Odoo separadamente
            saldos_calculados_antes = {}  # Guardar saldos calculados ANTES da importação
            registros_atuais = 0
            registros_nao_odoo = 0
            pedidos_odoo_obsoletos = 0  # Contagem de registros obsoletos mantidos
            
            # Processar todos os itens usando dados em memória (ZERO queries!)
            logger.info("   🔄 Processando cálculos em memória...")
            for item in todos_itens:
                chave = (item.num_pedido, item.cod_produto)
                
                # Buscar valores dos dicionários em memória
                qtd_faturada = faturamentos_dict.get(chave, 0)
                qtd_em_separacao = separacoes_dict.get(chave, 0)
                
                qtd_produto = float(item.qtd_produto_pedido or 0)
                qtd_cancelada = float(item.qtd_cancelada_produto_pedido or 0)
                # NÃO subtrair qtd_cancelada - Odoo já descontou de qtd_produto
                qtd_saldo_calculado = qtd_produto - qtd_faturada
                saldo_livre = qtd_saldo_calculado - qtd_em_separacao
                
                dados_item = {
                    'qtd_saldo_anterior': float(item.qtd_saldo_produto_pedido or 0),  # Valor antigo do banco
                    'qtd_saldo_calculado': qtd_saldo_calculado,  # Novo valor calculado
                    'qtd_total': qtd_produto,
                    'qtd_cancelada': qtd_cancelada,
                    'qtd_faturada': float(qtd_faturada),
                    'qtd_em_separacao': float(qtd_em_separacao),
                    'saldo_livre': saldo_livre,
                    # NOTA: separacao_lote_id foi movido para Separacao (não existe mais em CarteiraPrincipal)
                    'id': item.id
                }
                
                # Guardar saldo calculado para comparação posterior
                saldos_calculados_antes[chave] = qtd_saldo_calculado
                
                # Separar pedidos por origem
                if self.is_pedido_odoo(item.num_pedido):
                    carteira_atual[chave] = dados_item
                    registros_atuais += 1
                else:
                    carteira_nao_odoo[chave] = dados_item
                    registros_nao_odoo += 1
            
            logger.info(f"✅ {registros_atuais} registros Odoo indexados com saldos calculados")
            logger.info(f"🛡️ {registros_nao_odoo} registros não-Odoo protegidos")
            
            # FASE 2: BUSCAR DADOS NOVOS DO ODOO
            logger.info("🔄 Fase 2: Buscando dados atualizados do Odoo...")

            janela = 48*60 if primeira_execucao else minutos_janela

            resultado_odoo = self.obter_carteira_pendente(
                modo_incremental=modo_incremental,
                minutos_janela=janela,
                pedidos_especificos=pedidos_especificos
            )

            if not resultado_odoo['sucesso']:
                return {
                    'sucesso': False,
                    'erro': resultado_odoo.get('erro', 'Erro ao buscar dados do Odoo'),
                    'estatisticas': {}
                }

            dados_novos = resultado_odoo.get('dados', [])

            # OTIMIZAÇÃO: Em modo incremental, agora que temos os dados, carregar apenas pedidos afetados
            if modo_incremental and not todos_itens:
                pedidos_afetados = {item['num_pedido'] for item in dados_novos}

                if pedidos_afetados:
                    logger.info(f"   ⚡ Modo incremental: carregando apenas {len(pedidos_afetados)} pedidos afetados...")

                    # Garantir conexão antes das queries incrementais
                    ensure_connection()

                    @retry_on_ssl_error(max_retries=3, backoff_factor=1.0)
                    def buscar_carteira_incremental():
                        """Busca carteira incremental com retry para evitar SSL timeout"""
                        return CarteiraPrincipal.query.filter(
                            CarteiraPrincipal.num_pedido.in_(list(pedidos_afetados))
                        ).all()

                    todos_itens = buscar_carteira_incremental()
                    logger.info(f"   ✅ {len(todos_itens)} itens carregados (apenas afetados)")

                    # Reprocessar faturamentos e separações apenas para pedidos afetados
                    @retry_on_ssl_error(max_retries=3, backoff_factor=1.0)
                    def buscar_faturamentos_incremental():
                        """Busca faturamentos incremental com retry para evitar SSL timeout"""
                        return db.session.query(
                            FaturamentoProduto.origem,
                            FaturamentoProduto.cod_produto,
                            func.sum(FaturamentoProduto.qtd_produto_faturado).label('qtd_faturada')
                        ).filter(
                            FaturamentoProduto.origem.in_(list(pedidos_afetados)),
                            FaturamentoProduto.status_nf != 'Cancelado'
                        ).group_by(
                            FaturamentoProduto.origem,
                            FaturamentoProduto.cod_produto
                        ).all()

                    faturamentos = buscar_faturamentos_incremental()
                    faturamentos_dict = {(f.origem, f.cod_produto): float(f.qtd_faturada or 0) for f in faturamentos}

                    @retry_on_ssl_error(max_retries=3, backoff_factor=1.0)
                    def buscar_separacoes_incremental():
                        """Busca separações incremental com retry para evitar SSL timeout"""
                        return db.session.query(
                            Separacao.num_pedido,
                            Separacao.cod_produto,
                            func.sum(Separacao.qtd_saldo).label('qtd_em_separacao')
                        ).filter(
                            Separacao.num_pedido.in_(list(pedidos_afetados)),
                            Separacao.sincronizado_nf == False
                        ).group_by(
                            Separacao.num_pedido,
                            Separacao.cod_produto
                        ).all()

                    separacoes = buscar_separacoes_incremental()
                    separacoes_dict = {(s.num_pedido, s.cod_produto): float(s.qtd_em_separacao or 0) for s in separacoes}
            
            # 🆕 FASE 2.5: DETECTAR E PROCESSAR CANCELAMENTOS
            # Antes de aplicar filtros, separar pedidos cancelados para processamento
            logger.info("🔍 Verificando pedidos cancelados...")

            pedidos_cancelados = []
            dados_ativos = []

            for item in dados_novos:
                status = item.get('status_pedido', '').lower()
                num_pedido = item.get('num_pedido')

                if status == 'cancelado':
                    # Verificar se existe na carteira e não está cancelado
                    chave = (num_pedido, item.get('cod_produto'))
                    item_existente = carteira_atual.get(chave)

                    if item_existente and item_existente.get('status_pedido', '').lower() != 'cancelado':
                        # Mudou para cancelado - processar
                        pedidos_cancelados.append(num_pedido)
                        logger.info(f"🚨 Pedido {num_pedido} foi CANCELADO no Odoo")
                    # Não incluir na lista de dados ativos
                else:
                    dados_ativos.append(item)

            # Processar cancelamentos detectados
            if pedidos_cancelados:
                pedidos_cancelados_unicos = set(pedidos_cancelados)
                logger.info(f"🚨 Processando {len(pedidos_cancelados_unicos)} pedidos cancelados...")

                for num_pedido in pedidos_cancelados_unicos:
                    try:
                        self._processar_cancelamento_pedido(num_pedido)
                    except Exception as e:
                        logger.error(f"❌ Erro ao processar cancelamento do pedido {num_pedido}: {e}")

                logger.info(f"✅ {len(pedidos_cancelados_unicos)} pedidos cancelados processados")

            # Substituir dados_novos apenas com dados ativos
            dados_novos = dados_ativos

            # 🔧 CORREÇÃO: Aplicar APENAS filtro de status aqui
            # O filtro de saldo (usar_filtro_pendente) será aplicado DEPOIS do recálculo de saldo
            # para não descartar itens que têm qty_saldo=0 no Odoo mas saldo > 0 após recálculo
            dados_novos = [
                item for item in dados_novos
                if item.get('status_pedido', '').lower() in ['draft', 'sent', 'sale', 'cotação', 'cotação enviada', 'pedido de venda']
            ]

            logger.info(f"✅ {len(dados_novos)} registros ativos obtidos do Odoo (antes do recálculo de saldo)")
            
            # FASE 3: CALCULAR DIFERENÇAS COM SALDOS CALCULADOS
            logger.info("🔍 Fase 3: Calculando saldos e identificando diferenças...")
            
            # Primeiro, calcular os novos saldos para cada item do Odoo
            saldos_calculados_depois = {}
            alertas_saldo_negativo = []
            
            logger.info("📊 Calculando saldos para itens importados do Odoo...")
            
            # 🚀 SUPER OTIMIZAÇÃO: Uma ÚNICA query para TODOS os faturamentos!
            from app.utils.database_helpers import retry_on_ssl_error, ensure_connection
            
            # Garantir conexão antes de começar
            ensure_connection()
            
            # Coletar APENAS os pedidos únicos (não precisa produto, vamos trazer tudo)
            pedidos_unicos = set()
            for item_novo in dados_novos:
                pedidos_unicos.add(item_novo['num_pedido'])
            
            logger.info(f"🔍 Buscando faturamentos para {len(pedidos_unicos)} pedidos únicos...")
            
            # Uma ÚNICA query super otimizada com retry
            @retry_on_ssl_error(max_retries=3, backoff_factor=1.0)
            def buscar_faturamentos_agrupados():
                """Uma única query para TODOS os faturamentos agrupados"""
                try:
                    # Query única agrupada
                    resultados = db.session.query(
                        FaturamentoProduto.origem,
                        FaturamentoProduto.cod_produto,
                        func.sum(FaturamentoProduto.qtd_produto_faturado).label('qtd_faturada')
                    ).filter(
                        FaturamentoProduto.origem.in_(list(pedidos_unicos)),
                        FaturamentoProduto.status_nf != 'Cancelado'
                    ).group_by(
                        FaturamentoProduto.origem,
                        FaturamentoProduto.cod_produto
                    ).all()
                    
                    # Converter para dicionário
                    faturamentos_dict = {}
                    for row in resultados:
                        chave = (row.origem, row.cod_produto)
                        faturamentos_dict[chave] = float(row.qtd_faturada or 0)
                    
                    return faturamentos_dict
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao buscar faturamentos: {e}")
                    # Tentar reconectar e tentar novamente
                    ensure_connection()
                    raise
            
            # Executar a query única
            try:
                todas_qtds_faturadas = buscar_faturamentos_agrupados()
                logger.info(f"✅ {len(todas_qtds_faturadas)} faturamentos carregados em UMA query!")
                
            except Exception as e:
                logger.error(f"❌ Falha ao buscar faturamentos: {e}")
                todas_qtds_faturadas = {}
            
            # Agora calcular saldos usando as quantidades obtidas (muito rápido, tudo em memória)
            for item_novo in dados_novos:
                chave = (item_novo['num_pedido'], item_novo['cod_produto'])
                
                # Obter quantidades do Odoo
                qtd_produto_nova = float(item_novo.get('qtd_produto_pedido', 0))
                qtd_cancelada_nova = float(item_novo.get('qtd_cancelada_produto_pedido', 0))
                
                # Pegar do cache ou assumir 0 se não faturado
                qtd_faturada = todas_qtds_faturadas.get(chave, 0)
                
                # CALCULAR SALDO: qtd_produto - qtd_faturada
                # NÃO subtrair qtd_cancelada porque o Odoo já moveu/descontou de qtd_produto!
                # Quando cancela, o Odoo faz: qtd_produto -= qtd_cancelada
                qtd_saldo_calculado = qtd_produto_nova - qtd_faturada
                saldos_calculados_depois[chave] = qtd_saldo_calculado
                
                # IMPORTANTE: Adicionar o saldo calculado ao item (substitui qty_saldo do Odoo)
                item_novo['qtd_saldo_produto_pedido'] = qtd_saldo_calculado
                
                # Verificar saldo negativo
                if qtd_saldo_calculado < 0:
                    alertas_saldo_negativo.append({
                        'tipo': 'SALDO_NEGATIVO',
                        'num_pedido': item_novo['num_pedido'],
                        'cod_produto': item_novo['cod_produto'],
                        'qtd_saldo': qtd_saldo_calculado,
                        'qtd_faturada': qtd_faturada,
                        'qtd_produto': qtd_produto_nova,
                        'qtd_cancelada': qtd_cancelada_nova,
                        'mensagem': f'Saldo negativo ({qtd_saldo_calculado:.2f}) - possível NF devolvida ou erro'
                    })
                    logger.warning(f"⚠️ Saldo negativo detectado: {item_novo['num_pedido']}/{item_novo['cod_produto']} = {qtd_saldo_calculado:.2f}")

            # 🔧 CORREÇÃO: Aplicar filtro de saldo APÓS o recálculo (se usar_filtro_pendente=True)
            # Isso garante que itens com qty_saldo=0 no Odoo mas saldo > 0 após recálculo sejam incluídos
            if usar_filtro_pendente:
                dados_antes_filtro = len(dados_novos)
                dados_novos = [
                    item for item in dados_novos
                    if float(item.get('qtd_saldo_produto_pedido', 0)) > 0
                ]
                dados_filtrados = dados_antes_filtro - len(dados_novos)
                if dados_filtrados > 0:
                    logger.info(f"🔍 Filtro de saldo pendente: {dados_filtrados} itens removidos com saldo <= 0 (após recálculo)")
                logger.info(f"✅ {len(dados_novos)} registros após filtro de saldo pendente")

            # Agora comparar saldos CALCULADOS (antes x depois)
            reducoes = []
            aumentos = []
            novos_itens = []
            itens_removidos = set(carteira_atual.keys())
            
            for item_novo in dados_novos:
                chave = (item_novo['num_pedido'], item_novo['cod_produto'])
                qtd_saldo_nova = saldos_calculados_depois[chave]
                
                if chave in carteira_atual:
                    # Item existe - remover da lista de removidos
                    itens_removidos.discard(chave)
                    
                    # Comparar saldos CALCULADOS
                    qtd_saldo_anterior = carteira_atual[chave]['qtd_saldo_calculado']
                    saldo_livre_anterior = carteira_atual[chave]['saldo_livre']
                    qtd_em_separacao = carteira_atual[chave]['qtd_em_separacao']
                    
                    if abs(qtd_saldo_nova - qtd_saldo_anterior) > 0.01:  # Diferença significativa
                        if qtd_saldo_nova < qtd_saldo_anterior:
                            # REDUÇÃO detectada
                            reducoes.append({
                                'num_pedido': item_novo['num_pedido'],
                                'cod_produto': item_novo['cod_produto'],
                                'qtd_reduzida': qtd_saldo_anterior - qtd_saldo_nova,
                                'qtd_saldo_anterior': qtd_saldo_anterior,
                                'qtd_saldo_nova': qtd_saldo_nova,
                                'saldo_livre_anterior': saldo_livre_anterior,
                                'qtd_em_separacao': qtd_em_separacao
                            })
                            
                        elif qtd_saldo_nova > qtd_saldo_anterior:
                            # AUMENTO detectado
                            aumentos.append({
                                'num_pedido': item_novo['num_pedido'],
                                'cod_produto': item_novo['cod_produto'],
                                'qtd_aumentada': qtd_saldo_nova - qtd_saldo_anterior,
                                'qtd_saldo_anterior': qtd_saldo_anterior,
                                'qtd_saldo_nova': qtd_saldo_nova,
                                'saldo_livre_anterior': saldo_livre_anterior,
                                'qtd_em_separacao': qtd_em_separacao
                            })
                else:
                    # NOVO item
                    novos_itens.append(item_novo)
            
            logger.info(f"📊 Diferenças identificadas:")
            logger.info(f"   📉 {len(reducoes)} reduções")
            logger.info(f"   📈 {len(aumentos)} aumentos")
            logger.info(f"   ➕ {len(novos_itens)} novos itens")
            logger.info(f"   ➖ {len(itens_removidos)} itens removidos")
            if alertas_saldo_negativo:
                logger.warning(f"   ⚠️ {len(alertas_saldo_negativo)} itens com saldo negativo (NF devolvida?)")
            
            # FASE 3.2: GARANTIR CADASTRO DE PALLETIZAÇÃO PARA TODOS OS PRODUTOS
            logger.info("📦 Fase 3.2: Garantindo CadastroPalletizacao para todos os produtos...")
            resultado_palletizacao = self._garantir_cadastro_palletizacao_completo(dados_novos)
            logger.info(f"✅ CadastroPalletizacao garantido:")
            logger.info(f"   - {resultado_palletizacao['criados']} produtos criados")
            logger.info(f"   - {resultado_palletizacao['atualizados']} produtos atualizados") 
            logger.info(f"   - {resultado_palletizacao['ja_existentes']} já existentes")
            if resultado_palletizacao['erros'] > 0:
                logger.error(f"   - ❌ {resultado_palletizacao['erros']} erros ao criar cadastros")
            
            # FASE 3.5: PROCESSAR PEDIDOS ALTERADOS COM NOVO SERVIÇO UNIFICADO
            
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
            # Garantir conexão antes do loop de verificação de separações
            if itens_removidos:
                ensure_connection()

            for num_pedido, _ in itens_removidos:
                # CORREÇÃO: Verificar diretamente na tabela Separacao com sincronizado_nf=False
                # em vez de usar a VIEW Pedido que ignora status='PREVISAO'

                # Buscar separações não sincronizadas (não faturadas)
                try:
                    separacoes_nao_sincronizadas = Separacao.query.filter_by(
                        num_pedido=num_pedido,
                        sincronizado_nf=False  # CRÍTICO: apenas não sincronizadas
                    ).all()

                    if separacoes_nao_sincronizadas:
                        # Tem separações não faturadas, pode processar
                        pedidos_com_alteracoes.add(num_pedido)

                        # Log detalhado dos status encontrados
                        status_encontrados = set()
                        for sep in separacoes_nao_sincronizadas:
                            status_encontrados.add(sep.status)

                        status_str = ', '.join(sorted(status_encontrados))
                        logger.info(f"✅ Pedido {num_pedido} removido da carteira - será processado "
                                  f"({len(separacoes_nao_sincronizadas)} separações não sincronizadas com status: {status_str})")
                    else:
                        # Verificar se existem separações sincronizadas (já faturadas)
                        separacoes_sincronizadas = Separacao.query.filter_by(
                            num_pedido=num_pedido,
                            sincronizado_nf=True
                        ).first()

                        if separacoes_sincronizadas:
                            logger.warning(f"🛡️ PROTEÇÃO: Pedido {num_pedido} removido mas NÃO será processado "
                                         f"(todas as separações já sincronizadas/faturadas)")
                        else:
                            logger.info(f"ℹ️ Pedido {num_pedido} removido - sem separações para processar")

                except Exception as e:
                    logger.error(f"❌ Erro ao verificar separações do pedido {num_pedido}: {e}")
                    # Tentar reconectar para o próximo pedido
                    try:
                        ensure_connection()
                    except Exception:
                        pass
                    # Em caso de erro, não adicionar para processamento por segurança
                    continue
            
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
            
            # FASE 7: ATUALIZAR CARTEIRA (Delete + Insert)
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
            
            # 🎯 CORREÇÃO: Buscar registros APENAS dos pedidos que vieram na sincronização
            # Evita falsos positivos ao comparar com pedidos que não foram sincronizados
            pedidos_na_sincronizacao = set(item['num_pedido'] for item in dados_novos if item.get('num_pedido'))

            registros_odoo_existentes = {}
            if pedidos_na_sincronizacao:
                # Garantir conexão antes da query
                ensure_connection()

                @retry_on_ssl_error(max_retries=3, backoff_factor=1.0)
                def buscar_registros_existentes():
                    """Busca registros existentes com retry para evitar SSL timeout"""
                    return db.session.query(CarteiraPrincipal).filter(
                        CarteiraPrincipal.num_pedido.in_(list(pedidos_na_sincronizacao))
                    ).all()

                # Buscar APENAS produtos dos pedidos que vieram na sincronização atual
                for item in buscar_registros_existentes():
                    chave = (item.num_pedido, item.cod_produto)
                    registros_odoo_existentes[chave] = item

            logger.info(f"📊 {len(registros_odoo_existentes)} registros encontrados para {len(pedidos_na_sincronizacao)} pedidos sincronizados")

            # Criar conjunto de chaves dos novos dados para controle
            chaves_novos_dados = set()
            for item in dados_novos:
                if item.get('num_pedido') and item.get('cod_produto'):
                    chaves_novos_dados.add((item['num_pedido'], item['cod_produto']))

            # 🔍 VERIFICAR E REMOVER PRODUTOS EXCLUÍDOS DO ODOO
            produtos_suspeitos = []
            for chave, registro in registros_odoo_existentes.items():
                if chave not in chaves_novos_dados:
                    # Produto existe no banco mas NÃO veio na sincronização
                    produtos_suspeitos.append((chave, registro))

            if produtos_suspeitos:
                logger.info(f"🔍 {len(produtos_suspeitos)} produtos não vieram na sincronização. Verificando no Odoo...")
                contador_removidos = 0
                contador_mantidos = 0

                # BATCH: Verificar todos os produtos suspeitos de uma vez
                # em vez de 1 chamada Odoo por produto (N+1)
                pedidos_suspeitos = list(set(chave[0] for chave in [c for c, _ in produtos_suspeitos]))
                produtos_existentes_odoo = set()
                if pedidos_suspeitos:
                    try:
                        linhas_odoo = self.connection.execute_kw(
                            'sale.order.line', 'search_read',
                            [[
                                ['order_id.name', 'in', pedidos_suspeitos],
                                ['product_qty', '>', 0]
                            ]],
                            {'fields': ['order_id', 'product_id'], 'limit': 5000},
                            timeout_override=180
                        )
                        for l in (linhas_odoo or []):
                            order_name = l.get('order_id', [0, ''])[1] if isinstance(l.get('order_id'), list) else ''
                            product_code = l.get('product_id', [0, ''])[1] if isinstance(l.get('product_id'), list) else ''
                            # Extrair default_code do product display name: "[CODE] Name"
                            if product_code and '[' in product_code and ']' in product_code:
                                code = product_code.split(']')[0].replace('[', '').strip()
                                produtos_existentes_odoo.add((order_name, code))
                        logger.info(
                            f"   [BATCH] Verificados {len(linhas_odoo or [])} linhas Odoo "
                            f"(1 query vs {len(produtos_suspeitos)} N+1)"
                        )
                    except Exception as e:
                        logger.error(f"❌ Erro no batch de verificação: {e}. Usando fallback individual.")
                        # Fallback: usar método individual se batch falhar
                        for chave, registro in produtos_suspeitos:
                            num_pedido, cod_produto = chave
                            if self._verificar_produto_no_odoo(num_pedido, cod_produto):
                                produtos_existentes_odoo.add(chave)

                for chave, registro in produtos_suspeitos:
                    num_pedido, cod_produto = chave

                    try:
                        existe_no_odoo = chave in produtos_existentes_odoo

                        if not existe_no_odoo:
                            # ✅ CONFIRMADO: Produto foi excluído do pedido no Odoo
                            logger.info(f"   ✅ Removendo produto excluído do Odoo: {num_pedido}/{cod_produto}")
                            db.session.delete(registro)
                            contador_removidos += 1
                        else:
                            # ⚠️ FALSO POSITIVO: Produto existe no Odoo mas não veio na sincronização
                            logger.error(f"   ❌ ALERTA: Produto {num_pedido}/{cod_produto} existe no Odoo mas não veio na sinc (possível erro de conexão/timeout)")
                            contador_mantidos += 1

                    except Exception as e:
                        logger.error(f"   ❌ Erro ao verificar produto {num_pedido}/{cod_produto} no Odoo: {e}")
                        # Em caso de erro, manter o produto (segurança)
                        contador_mantidos += 1

                if contador_removidos > 0:
                    logger.info(f"🗑️  Total de produtos removidos: {contador_removidos}")
                if contador_mantidos > 0:
                    logger.warning(f"⚠️  Total de produtos mantidos (falsos positivos ou erros): {contador_mantidos}")
            else:
                logger.info("✅ Todos os produtos da sincronização estão atualizados")
            
            # UPSERT: Atualizar existentes ou inserir novos COM COMMITS INCREMENTAIS
            contador_inseridos = 0
            contador_atualizados = 0
            erros_insercao = []
            
            # Importar helper para commits com retry
            from app.utils.database_retry import commit_with_retry
            
            # 🚀 SUPER OTIMIZAÇÃO: Processar TUDO de uma vez, UM ÚNICO COMMIT!
            logger.info(f"🔄 Processando {len(dados_novos)} registros em operação única otimizada...")

            # BATCH: Pre-carregar custos vigentes para TODOS os produtos novos
            # Substitui N queries individuais por 1 query batch
            from app.custeio.models import CustoConsiderado
            produtos_para_inserir = set()
            for item in dados_novos:
                chave = (item.get('num_pedido'), item.get('cod_produto'))
                if chave not in registros_odoo_existentes and item.get('cod_produto'):
                    produtos_para_inserir.add(item['cod_produto'])

            cache_custos = {}
            if produtos_para_inserir:
                custos_vigentes = CustoConsiderado.query.filter(
                    CustoConsiderado.cod_produto.in_(list(produtos_para_inserir)),
                    CustoConsiderado.custo_atual == True
                ).all()
                cache_custos = {c.cod_produto: c for c in custos_vigentes}
                logger.info(
                    f"   [BATCH] Custos carregados: {len(cache_custos)} produtos "
                    f"(1 query vs {len(produtos_para_inserir)} N+1)"
                )

            # Inicializar contador (removido da otimização mas pode ser referenciado em outro lugar)
            contador_lote = 0
            registros_para_inserir = []

            # Processar todos os dados de uma vez
            for item in dados_novos:
                # Validar dados essenciais
                if not item.get('num_pedido') or not item.get('cod_produto'):
                    erros_insercao.append(f"Item sem pedido/produto: {item}")
                    continue
                
                chave = (item['num_pedido'], item['cod_produto'])
                
                if chave in registros_odoo_existentes:
                    # ATUALIZAR - Fazer inline, sem loops
                    registro_existente = registros_odoo_existentes[chave]
                    for key, value in item.items():
                        if hasattr(registro_existente, key) and key != 'id':
                            setattr(registro_existente, key, value)
                    contador_atualizados += 1
                else:
                    # INSERIR - Aplicar fallback para campos vazios ANTES de criar
                    # Garantir que cod_uf e nome_cidade tenham valores
                    if not item.get('cod_uf') and item.get('estado'):
                        item['cod_uf'] = item['estado']
                    if not item.get('nome_cidade') and item.get('municipio'):
                        item['nome_cidade'] = item['municipio']

                    # SNAPSHOT DE CUSTO - Usar cache batch (carregado acima)
                    snapshot = self._obter_snapshot_custo(item.get('cod_produto'), cache_custos=cache_custos)
                    if snapshot:
                        item.update(snapshot)
                        # CALCULAR MARGEM - Após capturar snapshot
                        margem = self._calcular_margem_bruta(item)
                        if margem:
                            item.update(margem)

                    # INSERIR - Criar registro com tratamento de erro
                    try:
                        novo_registro = CarteiraPrincipal(**item)
                        db.session.add(novo_registro)
                        contador_inseridos += 1
                    except Exception as e:
                        logger.error(f"❌ Erro ao criar registro para {item.get('num_pedido')}/{item.get('cod_produto')}: {e}")
                        erros_insercao.append(f"{item.get('num_pedido')}/{item.get('cod_produto')}: {str(e)[:100]}")
                        continue
            
            # UM ÚNICO COMMIT para TUDO!
            logger.info(f"   💾 Salvando {contador_inseridos} inserções e {contador_atualizados} atualizações...")
            
            try:
                if commit_with_retry(db.session, max_retries=3):
                    logger.info(f"   ✅ SUCESSO! Todos os registros salvos em UM commit!")
                else:
                    logger.error(f"   ❌ Falha ao salvar registros")
                    db.session.rollback()
            except Exception as e:
                logger.error(f"   ❌ Erro no commit único: {e}")
                try:
                    db.session.rollback()
                except Exception as e:
                    logger.error(f"   ❌ Erro no rollback: {e}")
                    pass
            
            
            logger.info(f"✅ {contador_inseridos} novos registros inseridos")
            logger.info(f"🔄 {contador_atualizados} registros atualizados")

            # Reportar erros se houver
            if erros_insercao:
                logger.warning(f"⚠️ {len(erros_insercao)} erros de inserção:")
                for erro in erros_insercao[:10]:  # Mostrar apenas os 10 primeiros
                    logger.error(f"   - {erro}")
            
            # FASE 8: COMMIT FINAL (já feito incrementalmente)
            logger.info("💾 Fase 8: Todas as alterações já salvas incrementalmente")
            
            # recomposicao_result removido - não recompomos mais pré-separações
            
            # FASE 9: ATUALIZAR DADOS DE SEPARAÇÃO/PEDIDO
            logger.info("🔄 Fase 9: Atualizando dados de Separação/Pedido...")
            try:
                from app.carteira.services.atualizar_dados_service import AtualizarDadosService
                atualizador = AtualizarDadosService()
                resultado_atualizacao = atualizador.atualizar_dados_pos_sincronizacao()
                
                if resultado_atualizacao.get('sucesso'):
                    logger.info(f"✅ Dados atualizados: {resultado_atualizacao.get('total_pedidos_atualizados', 0)} pedidos, "
                               f"{resultado_atualizacao.get('total_separacoes_atualizadas', 0)} separações")
                else:
                    logger.warning(f"⚠️ Atualização de dados com problemas: {resultado_atualizacao.get('erro')}")
            except Exception as e:
                logger.error(f"❌ Erro ao atualizar dados de Separação/Pedido: {str(e)}")
                # Não interromper o fluxo principal
            
            # FASE 10: VERIFICAÇÃO PÓS-SINCRONIZAÇÃO E ALERTAS
            logger.info("🔍 Fase 10: Verificação pós-sincronização...")
            alertas_pos_sync = self._verificar_alertas_pos_sincronizacao(dados_novos, alertas_pre_sync)
            
            # FASE 10.5: LIMPEZA AUTOMÁTICA DE SALDO STANDBY
            logger.info("🧹 Fase 10.5: Limpeza automática de SaldoStandby...")
            try:
                from app.carteira.models import SaldoStandby

                # 🎯 OBJETIVO: Remover automaticamente itens de Standby quando:
                # 1. O produto foi zerado no Odoo (qtd_saldo_produto_pedido = 0)
                # 2. O pedido foi cancelado/removido completamente do Odoo
                # 3. Apenas itens com status ATIVO, BLOQ. COML., SALDO (não mexer em CONFIRMADO)

                # Buscar todos os itens em SaldoStandby que estão ativos
                itens_standby_ativos = SaldoStandby.query.filter(
                    SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
                ).all()

                logger.info(f"   📊 Verificando {len(itens_standby_ativos)} itens em SaldoStandby...")

                # BATCH: Buscar TODOS os itens relevantes da CarteiraPrincipal de uma vez
                # Substitui N queries individuais (1 por item standby) por 1 query batch
                pedidos_standby = list(set(s.num_pedido for s in itens_standby_ativos))
                produtos_standby = list(set(s.cod_produto for s in itens_standby_ativos))
                carteira_standby_items = CarteiraPrincipal.query.filter(
                    CarteiraPrincipal.num_pedido.in_(pedidos_standby),
                    CarteiraPrincipal.cod_produto.in_(produtos_standby)
                ).all() if pedidos_standby else []
                carteira_standby_cache = {
                    (item.num_pedido, item.cod_produto): item
                    for item in carteira_standby_items
                }
                logger.info(
                    f"   [BATCH] Carregados {len(carteira_standby_items)} itens carteira "
                    f"(1 query vs {len(itens_standby_ativos)} N+1)"
                )

                contador_itens_zerados = 0
                contador_pedidos_cancelados = 0
                itens_removidos = []

                for item_standby in itens_standby_ativos:
                    # O(1) lookup em vez de query individual
                    item_carteira = carteira_standby_cache.get(
                        (item_standby.num_pedido, item_standby.cod_produto)
                    )

                    if not item_carteira:
                        # CASO 1: Item não existe mais na CarteiraPrincipal (pedido cancelado/produto removido)
                        logger.info(f"   ❌ Removendo do Standby: {item_standby.num_pedido}/{item_standby.cod_produto} "
                                  f"(não existe mais na CarteiraPrincipal)")
                        db.session.delete(item_standby)
                        contador_pedidos_cancelados += 1
                        itens_removidos.append({
                            'pedido': item_standby.num_pedido,
                            'produto': item_standby.cod_produto,
                            'motivo': 'PEDIDO_CANCELADO_OU_PRODUTO_REMOVIDO'
                        })

                    elif float(item_carteira.qtd_saldo_produto_pedido or 0) <= 0.001:
                        # CASO 2: Item existe mas saldo foi zerado no Odoo
                        logger.info(f"   🔄 Removendo do Standby: {item_standby.num_pedido}/{item_standby.cod_produto} "
                                  f"(saldo zerado no Odoo: {item_carteira.qtd_saldo_produto_pedido})")
                        db.session.delete(item_standby)
                        contador_itens_zerados += 1
                        itens_removidos.append({
                            'pedido': item_standby.num_pedido,
                            'produto': item_standby.cod_produto,
                            'motivo': 'SALDO_ZERADO_ODOO',
                            'qtd_saldo': float(item_carteira.qtd_saldo_produto_pedido)
                        })

                # Commit das exclusões
                if contador_itens_zerados > 0 or contador_pedidos_cancelados > 0:
                    db.session.commit()
                    logger.info(f"   ✅ Limpeza concluída:")
                    logger.info(f"      🔄 {contador_itens_zerados} itens zerados removidos")
                    logger.info(f"      ❌ {contador_pedidos_cancelados} itens de pedidos cancelados removidos")
                    logger.info(f"      📊 Total: {len(itens_removidos)} itens removidos do SaldoStandby")
                else:
                    logger.info("   ✅ Nenhum item para remover de SaldoStandby")

            except Exception as e:
                logger.error(f"   ❌ Erro ao limpar SaldoStandby: {e}")
                db.session.rollback()
            
            # FASE 10.6: VERIFICAÇÃO E ATUALIZAÇÃO DE CONTATOS AGENDAMENTO
            logger.info("📞 Fase 10.6: Verificação de Contatos de Agendamento...")
            try:
                from app.cadastros_agendamento.models import ContatoAgendamento

                # 🔍 DIAGNÓSTICO: Buscar clientes que necessitam agendamento
                # ✅ CORREÇÃO: Usar upper() para case-insensitive
                clientes_necessitam_agendamento = CarteiraPrincipal.query.filter(
                    db.func.upper(CarteiraPrincipal.cliente_nec_agendamento) == 'SIM'
                ).with_entities(CarteiraPrincipal.cnpj_cpf).distinct().all()

                # 🔍 LOG DIAGNÓSTICO
                logger.info(f"   📊 Encontrados {len(clientes_necessitam_agendamento)} clientes que necessitam agendamento")

                contador_contatos_criados = 0
                contador_contatos_atualizados = 0
                contador_cnpjs_vazios = 0
                contador_ja_existentes = 0

                for (cnpj,) in clientes_necessitam_agendamento:
                    if not cnpj or not cnpj.strip():
                        contador_cnpjs_vazios += 1
                        logger.debug(f"   ⚠️ CNPJ vazio/None encontrado - pulando")
                        continue

                    # Verificar se existe ContatoAgendamento para este CNPJ
                    contato_existente = ContatoAgendamento.query.filter_by(cnpj=cnpj).first()

                    if not contato_existente:
                        # Criar novo registro com forma=ODOO
                        try:
                            novo_contato = ContatoAgendamento(
                                cnpj=cnpj,
                                forma='ODOO',
                                contato='Importado do Odoo',
                                observacao='Cliente necessita agendamento - Configurado automaticamente na importação',
                                atualizado_em=agora_utc_naive()
                            )
                            db.session.add(novo_contato)
                            contador_contatos_criados += 1
                            logger.info(f"   ➕ Criado ContatoAgendamento para CNPJ {cnpj}")
                        except Exception as e:
                            logger.error(f"   ❌ Erro ao criar ContatoAgendamento para CNPJ {cnpj}: {e}")
                            raise  # Re-lança para ser capturado pelo try externo

                    elif contato_existente.forma == 'SEM AGENDAMENTO':
                        # Atualizar para forma=ODOO se estava como SEM AGENDAMENTO
                        contato_existente.forma = 'ODOO'
                        contato_existente.contato = 'Importado do Odoo'
                        contato_existente.observacao = 'Atualizado de SEM AGENDAMENTO para ODOO na importação'
                        contato_existente.atualizado_em = agora_utc_naive()
                        contador_contatos_atualizados += 1
                        logger.info(f"   🔄 Atualizado ContatoAgendamento para CNPJ {cnpj} de 'SEM AGENDAMENTO' para 'ODOO'")

                    else:
                        # Já existe com outra forma (Portal, Telefone, ODOO, etc), mantém como está
                        contador_ja_existentes += 1
                        logger.debug(f"   ✓ CNPJ {cnpj} já tem ContatoAgendamento (forma={contato_existente.forma}) - mantido")

                # 🔍 LOG DIAGNÓSTICO DETALHADO
                logger.info(f"   📊 Resumo processamento:")
                logger.info(f"      - Total clientes com agendamento: {len(clientes_necessitam_agendamento)}")
                logger.info(f"      - CNPJs vazios/None: {contador_cnpjs_vazios}")
                logger.info(f"      - Contatos criados: {contador_contatos_criados}")
                logger.info(f"      - Contatos atualizados: {contador_contatos_atualizados}")
                logger.info(f"      - Já existentes (mantidos): {contador_ja_existentes}")

                if contador_contatos_criados > 0 or contador_contatos_atualizados > 0:
                    db.session.commit()
                    logger.info(f"   ✅ Commit realizado: {contador_contatos_criados} criados, {contador_contatos_atualizados} atualizados")
                else:
                    logger.info("   ✅ Nenhuma alteração necessária em ContatoAgendamento")

            except Exception as e:
                logger.error(f"   ❌ ERRO CRÍTICO ao verificar Contatos de Agendamento: {e}")
                logger.error(f"   ❌ Tipo do erro: {type(e).__name__}")
                logger.error(f"   ❌ Traceback: {traceback.format_exc()}")
                db.session.rollback()
            
            # FASE 10.7: ATUALIZAR FORMA_AGENDAMENTO NA CARTEIRA
            logger.info("📝 Fase 10.7: Atualizando forma de agendamento na carteira...")
            try:
                from app.cadastros_agendamento.models import ContatoAgendamento
                
                # Buscar todos os contatos de agendamento
                contatos_agendamento = {c.cnpj: c.forma for c in ContatoAgendamento.query.all()}
                
                # Atualizar CarteiraPrincipal com a forma de agendamento
                contador_atualizados_forma = 0
                registros_carteira = CarteiraPrincipal.query.filter(
                    CarteiraPrincipal.cnpj_cpf.in_(list(contatos_agendamento.keys()))
                ).all()
                
                for registro in registros_carteira:
                    forma = contatos_agendamento.get(registro.cnpj_cpf)
                    if forma and registro.forma_agendamento != forma:
                        registro.forma_agendamento = forma
                        contador_atualizados_forma += 1
                
                # Limpar forma_agendamento para clientes sem ContatoAgendamento
                registros_sem_contato = CarteiraPrincipal.query.filter(
                    ~CarteiraPrincipal.cnpj_cpf.in_(list(contatos_agendamento.keys())),
                    CarteiraPrincipal.forma_agendamento.isnot(None)
                ).all()
                
                for registro in registros_sem_contato:
                    registro.forma_agendamento = None
                    contador_atualizados_forma += 1
                
                if contador_atualizados_forma > 0:
                    db.session.commit()
                    logger.info(f"   ✅ {contador_atualizados_forma} registros atualizados com forma de agendamento")
                else:
                    logger.info("   ✅ Forma de agendamento já está atualizada em todos os registros")
                    
            except Exception as e:
                logger.warning(f"   ⚠️ Erro ao atualizar forma de agendamento: {e}")
                db.session.rollback()
            
            # FASE 11: ESTATÍSTICAS FINAIS
            fim_operacao = datetime.now()
            tempo_total = (fim_operacao - inicio_operacao).total_seconds()
            
            # Contar alterações bem-sucedidas
            alteracoes_sucesso = [a for a in alteracoes_aplicadas if 'erro' not in a]
            alteracoes_erro = [a for a in alteracoes_aplicadas if 'erro' in a]
            
            # Estatísticas completas compatíveis com função original
            estatisticas_completas = {
                'registros_inseridos': contador_inseridos,
                'registros_atualizados': contador_atualizados,
                'registros_removidos': 0,  # Não removemos mais para preservar histórico
                'registros_nao_odoo_preservados': registros_nao_odoo,
                'total_encontrados': len(resultado_odoo.get('dados', [])),
                'registros_filtrados': len(dados_novos),
                'taxa_sucesso': f"{((contador_inseridos + contador_atualizados)/len(dados_novos)*100):.1f}%" if dados_novos else "0%",
                'erros_processamento': len(erros_insercao),
                'metodo': 'operacional_completo_com_upsert',
                
                # Dados operacionais específicos
                'tempo_execucao_segundos': round(tempo_total, 2),
                # Campos removidos - não fazemos mais backup/recomposição de pré-separações
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
            logger.info(f"   📋 {pedidos_odoo_obsoletos} registros obsoletos mantidos para histórico")
            logger.info(f"   🛡️ {registros_nao_odoo} registros não-Odoo preservados")
            # Linha removida - não fazemos mais backup de pré-separações
            logger.info(f"   📉 {estatisticas_completas['reducoes_aplicadas']} reduções aplicadas")
            logger.info(f"   📈 {estatisticas_completas['aumentos_aplicados']} aumentos aplicados")
            logger.info(f"   ➖ {estatisticas_completas['remocoes_aplicadas']} remoções processadas")
            logger.info(f"   ➕ {len(novos_itens)} novos itens")
            # Linha removida - não recompomos mais pré-separações
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
                'registros_removidos': 0,  # Não removemos mais para preservar histórico
                'registros_nao_odoo_preservados': registros_nao_odoo,
                'erros': erros_insercao,
                
                # Dados operacionais para interface
                'alertas_pre_sync': alertas_pre_sync,
                'alertas_pos_sync': alertas_pos_sync,
                # Campos removidos - não fazemos mais backup/recomposição
                'tempo_execucao': tempo_total,
                
                # Dados específicos da gestão de quantidades
                'alteracoes_aplicadas': alteracoes_aplicadas,
                'gestao_quantidades_ativa': True,
                
                'mensagem': f'✅ Sincronização operacional completa: {contador_inseridos} registros importados, {len(alteracoes_sucesso)} mudanças de quantidade processadas'
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