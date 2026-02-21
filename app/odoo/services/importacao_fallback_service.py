"""
Serviço de Importação Fallback do Odoo
======================================

Permite importar pedidos e faturamentos do Odoo de forma manual,
mesmo que não existam no sistema local.

CASOS DE USO:
1. Pedido não importado pela sincronização automática
2. Faturamento não importado
3. Reimportação após correção de filtros

Autor: Sistema de Fretes
Data: 2026-01-06
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app import db
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.services.carteira_service import CarteiraService
from app.odoo.services.faturamento_service import FaturamentoService
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class ImportacaoFallbackService:
    """
    Serviço para importação manual de pedidos e faturamentos do Odoo

    Funciona como fallback quando a sincronização automática não importou.
    """

    # Critérios de negócio compartilhados com sync normal (faturamento_service.py:1309-1319)
    # Devem ser IDÊNTICOS aos usados na sincronização incremental
    DOMAIN_TIPO_PEDIDO_FATURAMENTO = [
        '|', '|', '|', '|',
        ('l10n_br_tipo_pedido', '=', 'venda'),
        ('l10n_br_tipo_pedido', '=', 'bonificacao'),
        ('l10n_br_tipo_pedido', '=', 'industrializacao'),
        ('l10n_br_tipo_pedido', '=', 'exportacao'),
        ('l10n_br_tipo_pedido', '=', 'venda-industrializacao'),
    ]

    # Mesmo critério para sale.order (mesmos tipos de pedido)
    DOMAIN_TIPO_PEDIDO_CARTEIRA = [
        '|', '|', '|', '|',
        ('l10n_br_tipo_pedido', '=', 'venda'),
        ('l10n_br_tipo_pedido', '=', 'bonificacao'),
        ('l10n_br_tipo_pedido', '=', 'industrializacao'),
        ('l10n_br_tipo_pedido', '=', 'exportacao'),
        ('l10n_br_tipo_pedido', '=', 'venda-industrializacao'),
    ]

    def __init__(self):
        self.connection = get_odoo_connection()
        self.carteira_service = CarteiraService()
        self.faturamento_service = FaturamentoService()

    # =========================================================================
    # IMPORTAÇÃO DE PEDIDOS
    # =========================================================================

    def importar_pedido_por_numero(self, num_pedido: str) -> Dict[str, Any]:
        """
        Importa um pedido específico do Odoo para o sistema local.

        Funciona mesmo se o pedido NÃO existir no sistema local.
        Usa o CarteiraService.sincronizar_carteira_odoo_com_gestao_quantidades
        com o parâmetro pedidos_especificos.

        Args:
            num_pedido: Número do pedido (ex: VFB2500432, VCD123456)

        Returns:
            Dict com resultado da importação
        """
        inicio = datetime.now()

        try:
            logger.info(f"📥 Iniciando importação fallback do pedido {num_pedido}")

            # Validar formato do pedido
            if not num_pedido or len(num_pedido.strip()) == 0:
                return {
                    'sucesso': False,
                    'mensagem': 'Número do pedido não pode ser vazio',
                    'timestamp': agora_utc_naive()
                }

            num_pedido = num_pedido.strip().upper()

            # Verificar se o pedido existe no Odoo
            pedido_odoo = self._verificar_pedido_odoo(num_pedido)

            if not pedido_odoo:
                return {
                    'sucesso': False,
                    'mensagem': f'Pedido {num_pedido} não encontrado no Odoo',
                    'timestamp': agora_utc_naive()
                }

            if pedido_odoo.get('cancelado'):
                return {
                    'sucesso': False,
                    'mensagem': f'Pedido {num_pedido} está cancelado no Odoo',
                    'dados_odoo': pedido_odoo,
                    'timestamp': agora_utc_naive()
                }

            # Importar usando CarteiraService
            logger.info(f"✅ Pedido {num_pedido} encontrado no Odoo. Iniciando importação...")

            resultado = self.carteira_service.sincronizar_carteira_odoo_com_gestao_quantidades(
                pedidos_especificos=[num_pedido]
            )

            tempo_total = (datetime.now() - inicio).total_seconds()

            if resultado.get('sucesso'):
                return {
                    'sucesso': True,
                    'mensagem': f'Pedido {num_pedido} importado com sucesso',
                    'dados_odoo': pedido_odoo,
                    'estatisticas': resultado.get('estatisticas', {}),
                    'tempo_execucao': round(tempo_total, 2),
                    'timestamp': agora_utc_naive()
                }
            else:
                return {
                    'sucesso': False,
                    'mensagem': f'Erro ao importar pedido: {resultado.get("mensagem", "Erro desconhecido")}',
                    'erro': resultado.get('erro'),
                    'tempo_execucao': round(tempo_total, 2),
                    'timestamp': agora_utc_naive()
                }

        except Exception as e:
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.error(f"❌ Erro ao importar pedido {num_pedido}: {e}")

            return {
                'sucesso': False,
                'mensagem': f'Erro ao importar pedido: {str(e)}',
                'erro': str(e),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': agora_utc_naive()
            }

    def importar_pedidos_por_data(self, data_inicio: str, data_fim: str = None) -> Dict[str, Any]:
        """
        Importa pedidos do Odoo criados em um período específico.

        Args:
            data_inicio: Data inicial (formato YYYY-MM-DD)
            data_fim: Data final (formato YYYY-MM-DD), se None usa data atual

        Returns:
            Dict com resultado da importação
        """
        inicio = datetime.now()

        try:
            logger.info(f"📥 Iniciando importação fallback de pedidos por data: {data_inicio} a {data_fim}")

            # Validar datas
            try:
                dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d') if data_fim else agora_utc_naive()
            except ValueError as e:
                return {
                    'sucesso': False,
                    'mensagem': f'Formato de data inválido. Use YYYY-MM-DD. Erro: {str(e)}',
                    'timestamp': agora_utc_naive()
                }

            # Buscar pedidos no Odoo no período
            pedidos = self._buscar_pedidos_por_data(data_inicio, data_fim or agora_utc_naive().strftime('%Y-%m-%d'))

            if not pedidos:
                return {
                    'sucesso': True,
                    'mensagem': f'Nenhum pedido encontrado no período {data_inicio} a {data_fim}',
                    'total_encontrados': 0,
                    'timestamp': agora_utc_naive()
                }

            logger.info(f"✅ Encontrados {len(pedidos)} pedidos no período")

            # Extrair números dos pedidos
            numeros_pedidos = [p.get('name') for p in pedidos if p.get('name')]

            if not numeros_pedidos:
                return {
                    'sucesso': False,
                    'mensagem': 'Nenhum pedido válido encontrado no período',
                    'timestamp': agora_utc_naive()
                }

            # Importar usando CarteiraService
            resultado = self.carteira_service.sincronizar_carteira_odoo_com_gestao_quantidades(
                pedidos_especificos=numeros_pedidos
            )

            tempo_total = (datetime.now() - inicio).total_seconds()

            return {
                'sucesso': resultado.get('sucesso', False),
                'mensagem': f'{len(numeros_pedidos)} pedidos processados',
                'pedidos_encontrados': numeros_pedidos,
                'total_encontrados': len(numeros_pedidos),
                'estatisticas': resultado.get('estatisticas', {}),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': agora_utc_naive()
            }

        except Exception as e:
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.error(f"❌ Erro ao importar pedidos por data: {e}")

            return {
                'sucesso': False,
                'mensagem': f'Erro ao importar pedidos: {str(e)}',
                'erro': str(e),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': agora_utc_naive()
            }

    def _verificar_pedido_odoo(self, num_pedido: str) -> Optional[Dict]:
        """
        Verifica se um pedido existe no Odoo e retorna seus dados básicos.
        """
        try:
            pedidos = self.connection.search_read(
                'sale.order',
                [('name', '=', num_pedido)],
                fields=['id', 'name', 'state', 'l10n_br_tipo_pedido', 'partner_id',
                        'amount_total', 'create_date', 'company_id'],
                limit=1
            )

            if not pedidos:
                return None

            pedido = pedidos[0]

            # Buscar linhas
            linhas = self.connection.search_read(
                'sale.order.line',
                [('order_id', '=', pedido['id'])],
                fields=['product_id', 'product_uom_qty', 'qty_saldo'],
                limit=100
            )

            return {
                'id': pedido.get('id'),
                'name': pedido.get('name'),
                'state': pedido.get('state'),
                'tipo_pedido': pedido.get('l10n_br_tipo_pedido'),
                'cliente': pedido.get('partner_id'),
                'valor_total': pedido.get('amount_total'),
                'data_criacao': pedido.get('create_date'),
                'empresa': pedido.get('company_id'),
                'total_linhas': len(linhas),
                'cancelado': pedido.get('state') == 'cancel'
            }

        except Exception as e:
            logger.error(f"❌ Erro ao verificar pedido {num_pedido} no Odoo: {e}")
            return None

    def _buscar_pedidos_por_data(self, data_inicio: str, data_fim: str) -> List[Dict]:
        """
        Busca pedidos no Odoo criados em um período específico.
        """
        try:
            # Domain com filtros de tipo de pedido (constante compartilhada)
            domain = [
                ('create_date', '>=', f'{data_inicio} 00:00:00'),
                ('create_date', '<=', f'{data_fim} 23:59:59'),
                ('state', 'in', ['draft', 'sent', 'sale']),
                *self.DOMAIN_TIPO_PEDIDO_CARTEIRA,
            ]

            pedidos = self.connection.search_read(
                'sale.order',
                domain,
                fields=['id', 'name', 'state', 'l10n_br_tipo_pedido', 'partner_id',
                        'amount_total', 'create_date'],
                limit=500
            )

            return pedidos or []

        except Exception as e:
            logger.error(f"❌ Erro ao buscar pedidos por data: {e}")
            return []

    # =========================================================================
    # IMPORTAÇÃO DE FATURAMENTO
    # =========================================================================

    def importar_faturamento_por_nf(self, numero_nf: str) -> Dict[str, Any]:
        """
        Importa uma NF específica do Odoo para o sistema local.

        Args:
            numero_nf: Número da nota fiscal

        Returns:
            Dict com resultado da importação
        """
        inicio = datetime.now()

        try:
            logger.info(f"📥 Iniciando importação fallback da NF {numero_nf}")

            if not numero_nf or len(numero_nf.strip()) == 0:
                return {
                    'sucesso': False,
                    'mensagem': 'Número da NF não pode ser vazio',
                    'timestamp': agora_utc_naive()
                }

            numero_nf = numero_nf.strip()

            # Buscar NF no Odoo
            nf_odoo = self._buscar_nf_odoo(numero_nf)

            if not nf_odoo:
                return {
                    'sucesso': False,
                    'mensagem': f'NF {numero_nf} não encontrada no Odoo',
                    'timestamp': agora_utc_naive()
                }

            # Tratar NF cancelada (alinhado com sync normal: faturamento_service.py:756-761)
            if nf_odoo.get('state') == 'cancel':
                from app.faturamento.models import FaturamentoProduto
                existe_local = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).first()

                if existe_local:
                    logger.info(f"🚨 NF {numero_nf} cancelada no Odoo — processando cancelamento local")
                    self.faturamento_service._processar_cancelamento_nf(numero_nf)
                    db.session.commit()
                    tempo_total = (datetime.now() - inicio).total_seconds()
                    return {
                        'sucesso': True,
                        'mensagem': f'NF {numero_nf} cancelada localmente (estava cancelada no Odoo)',
                        'dados_nf': nf_odoo,
                        'itens_importados': 0,
                        'cancelada': True,
                        'tempo_execucao': round(tempo_total, 2),
                        'timestamp': agora_utc_naive()
                    }
                else:
                    tempo_total = (datetime.now() - inicio).total_seconds()
                    return {
                        'sucesso': False,
                        'mensagem': f'NF {numero_nf} está cancelada no Odoo e não existe localmente',
                        'dados_nf': nf_odoo,
                        'itens_importados': 0,
                        'cancelada': True,
                        'tempo_execucao': round(tempo_total, 2),
                        'timestamp': agora_utc_naive()
                    }

            logger.info(f"✅ NF {numero_nf} encontrada no Odoo (state={nf_odoo.get('state')}). Iniciando importação...")

            # Importar linhas da NF (apenas posted)
            resultado = self._processar_importacao_nf(nf_odoo)

            tempo_total = (datetime.now() - inicio).total_seconds()

            return {
                'sucesso': resultado.get('sucesso', False),
                'mensagem': resultado.get('mensagem', ''),
                'dados_nf': nf_odoo,
                'itens_importados': resultado.get('itens_importados', 0),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': agora_utc_naive()
            }

        except Exception as e:
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.error(f"❌ Erro ao importar NF {numero_nf}: {e}")

            return {
                'sucesso': False,
                'mensagem': f'Erro ao importar NF: {str(e)}',
                'erro': str(e),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': agora_utc_naive()
            }

    def importar_faturamento_por_periodo(self, data_inicio: str, data_fim: str = None) -> Dict[str, Any]:
        """
        Importa NFs do Odoo emitidas em um período específico.

        Args:
            data_inicio: Data inicial (formato YYYY-MM-DD)
            data_fim: Data final (formato YYYY-MM-DD), se None usa data atual

        Returns:
            Dict com resultado da importação
        """
        inicio = datetime.now()

        try:
            logger.info(f"📥 Iniciando importação fallback de faturamento: {data_inicio} a {data_fim}")

            # Validar datas
            try:
                dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d') if data_fim else agora_utc_naive()
            except ValueError as e:
                return {
                    'sucesso': False,
                    'mensagem': f'Formato de data inválido. Use YYYY-MM-DD. Erro: {str(e)}',
                    'timestamp': agora_utc_naive()
                }

            # Buscar NFs no período
            nfs = self._buscar_nfs_por_periodo(data_inicio, data_fim or agora_utc_naive().strftime('%Y-%m-%d'))

            if not nfs:
                return {
                    'sucesso': True,
                    'mensagem': f'Nenhuma NF encontrada no período {data_inicio} a {data_fim}',
                    'total_encontradas': 0,
                    'timestamp': agora_utc_naive()
                }

            logger.info(f"✅ Encontradas {len(nfs)} NFs no período")

            # Processar cada NF
            total_importadas = 0
            total_erros = 0
            nfs_processadas = []

            for nf in nfs:
                try:
                    resultado = self._processar_importacao_nf(nf)
                    if resultado.get('sucesso'):
                        total_importadas += 1
                        nfs_processadas.append(nf.get('numero_nf'))
                    else:
                        total_erros += 1
                except Exception as e:
                    total_erros += 1
                    logger.error(f"❌ Erro ao processar NF {nf.get('numero_nf')}: {e}")

            tempo_total = (datetime.now() - inicio).total_seconds()

            return {
                'sucesso': True,
                'mensagem': f'{total_importadas} NFs importadas, {total_erros} erros',
                'total_encontradas': len(nfs),
                'total_importadas': total_importadas,
                'total_erros': total_erros,
                'nfs_processadas': nfs_processadas,
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': agora_utc_naive()
            }

        except Exception as e:
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.error(f"❌ Erro ao importar faturamento por período: {e}")

            return {
                'sucesso': False,
                'mensagem': f'Erro ao importar faturamento: {str(e)}',
                'erro': str(e),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': agora_utc_naive()
            }

    def importar_faturamento_por_periodo_batch(self, data_inicio: str, data_fim: str = None) -> Dict[str, Any]:
        """
        Importa NFs do Odoo por período usando processamento batch (otimizado).

        Performance: ~4 chamadas Odoo total vs 4N+1 do método sequencial.

        Fluxo:
        1. Busca NFs no período — 1 call Odoo (campos ampliados, elimina O2)
        2. Filtra NFs já existentes no DB — 1 query bulk IN (elimina O3)
        3. Busca dados complementares em batch — 3 calls Odoo (elimina O1)
        4. Insere FaturamentoProduto + RelatorioFaturamentoImportado em bulk (elimina O5)
        5. Pós-processamento batch: saldos + matching — 1 chamada cada (elimina O4)

        Args:
            data_inicio: Data inicial (formato YYYY-MM-DD)
            data_fim: Data final (formato YYYY-MM-DD), se None usa data atual

        Returns:
            Dict com resultado da importação (mesmo formato de importar_faturamento_por_periodo)
        """
        inicio = datetime.now()

        try:
            logger.info(f"📥 Importação BATCH de faturamento: {data_inicio} a {data_fim}")

            # Validar datas
            try:
                datetime.strptime(data_inicio, '%Y-%m-%d')
                if data_fim:
                    datetime.strptime(data_fim, '%Y-%m-%d')
            except ValueError as e:
                return {
                    'sucesso': False,
                    'mensagem': f'Formato de data inválido. Use YYYY-MM-DD. Erro: {str(e)}',
                    'timestamp': agora_utc_naive()
                }

            # ============================================================
            # FASE 1: Buscar NFs no período (1 chamada Odoo)
            # ============================================================
            nfs = self._buscar_nfs_por_periodo(
                data_inicio,
                data_fim or agora_utc_naive().strftime('%Y-%m-%d')
            )

            if not nfs:
                return {
                    'sucesso': True,
                    'mensagem': f'Nenhuma NF encontrada no período {data_inicio} a {data_fim}',
                    'total_encontradas': 0,
                    'total_importadas': 0,
                    'total_erros': 0,
                    'nfs_processadas': [],
                    'tempo_execucao': round((datetime.now() - inicio).total_seconds(), 2),
                    'timestamp': agora_utc_naive()
                }

            logger.info(f"✅ {len(nfs)} NFs encontradas no período")

            # ============================================================
            # FASE 2: Separar NFs por estado + existência local
            # Alinhado com sync normal (faturamento_service.py:756-764)
            # ============================================================
            from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado

            numeros_nf = [nf['numero_nf'] for nf in nfs if nf.get('numero_nf')]

            nfs_existentes_set = set(
                row[0] for row in db.session.query(FaturamentoProduto.numero_nf)
                .filter(FaturamentoProduto.numero_nf.in_(numeros_nf))
                .distinct().all()
            )

            # Separar por estado e existência:
            # 1. NFs posted que NÃO existem localmente → importar
            # 2. NFs canceladas que EXISTEM localmente → processar cancelamento
            # 3. NFs canceladas que NÃO existem → ignorar (não importar NF cancelada)
            nfs_novas = [
                nf for nf in nfs
                if nf.get('numero_nf')
                and nf['numero_nf'] not in nfs_existentes_set
                and nf.get('state') != 'cancel'  # Não importar NF cancelada que não existe localmente
            ]

            nfs_para_cancelar = [
                nf for nf in nfs
                if nf.get('numero_nf')
                and nf['numero_nf'] in nfs_existentes_set
                and nf.get('state') == 'cancel'
            ]

            nfs_cancel_sem_local = len([
                nf for nf in nfs
                if nf.get('state') == 'cancel'
                and nf.get('numero_nf')
                and nf['numero_nf'] not in nfs_existentes_set
            ])

            logger.info(
                f"📊 {len(nfs_existentes_set)} NFs já existem, "
                f"{len(nfs_novas)} novas para importar, "
                f"{len(nfs_para_cancelar)} para cancelar, "
                f"{nfs_cancel_sem_local} canceladas sem registro local (ignoradas)"
            )

            if not nfs_novas and not nfs_para_cancelar:
                return {
                    'sucesso': True,
                    'mensagem': f'Todas as {len(nfs)} NFs do período já existem no sistema'
                               + (f' ({nfs_cancel_sem_local} canceladas ignoradas)' if nfs_cancel_sem_local else ''),
                    'total_encontradas': len(nfs),
                    'total_importadas': 0,
                    'total_ja_existentes': len(nfs_existentes_set),
                    'total_canceladas': 0,
                    'total_ignoradas_cancel': nfs_cancel_sem_local,
                    'total_erros': 0,
                    'nfs_processadas': [],
                    'tempo_execucao': round((datetime.now() - inicio).total_seconds(), 2),
                    'timestamp': agora_utc_naive()
                }

            # ============================================================
            # FASE 3: Buscar dados complementares em batch (3 chamadas Odoo)
            # ============================================================
            caches = self._buscar_dados_batch_odoo(nfs_novas)
            cache_parceiros = caches['parceiros']
            cache_linhas = caches['linhas']
            cache_produtos = caches['produtos']

            # ============================================================
            # FASE 4: Processar NFs e montar registros para bulk insert
            # ============================================================
            registros_faturamento = []
            registros_relatorio = []
            pedidos_afetados = {}  # {origem: set(cod_produtos)} para saldos
            nfs_processadas = []
            total_erros = 0
            agora = agora_utc_naive()

            # Check quais RelatorioFaturamentoImportado já existem (bulk)
            relatorios_existentes = set(
                row[0] for row in db.session.query(RelatorioFaturamentoImportado.numero_nf)
                .filter(RelatorioFaturamentoImportado.numero_nf.in_(
                    [nf['numero_nf'] for nf in nfs_novas]
                )).all()
            )

            for nf in nfs_novas:
                try:
                    numero_nf = nf['numero_nf']
                    move_id = nf['id']
                    origem = nf.get('origem') or ''

                    # Status mapeado (mesma lógica de faturamento_service._mapear_status)
                    status_nf = self.faturamento_service._mapear_status(nf.get('state', ''))

                    # Extrair vendedor/equipe/incoterm de many2one (do Passo 1)
                    vendedor = self._extrair_many2one_nome(nf.get('invoice_user_id'))
                    equipe_vendas = self._extrair_many2one_nome(nf.get('team_id'))
                    incoterm = self._extrair_many2one_nome(nf.get('invoice_incoterm_id'))

                    # Dados do parceiro (do cache batch)
                    partner_id = None
                    partner_raw = nf.get('cliente')
                    if partner_raw and isinstance(partner_raw, list):
                        partner_id = partner_raw[0]
                    elif partner_raw and partner_raw is not False:
                        partner_id = partner_raw

                    cliente_info = cache_parceiros.get(partner_id, {
                        'cnpj_cliente': '', 'nome_cliente': '',
                        'municipio': '', 'estado': ''
                    })

                    # Linhas desta NF (do cache batch)
                    linhas = cache_linhas.get(move_id, [])
                    if not linhas:
                        logger.warning(f"⚠️ NF {numero_nf} sem linhas de produto no cache")
                        total_erros += 1
                        continue

                    # Processar linhas → registros FaturamentoProduto
                    valor_total_nf = 0.0
                    peso_total_nf = 0.0
                    produtos_desta_nf = set()

                    for linha in linhas:
                        product_id = linha.get('product_id')
                        if isinstance(product_id, list):
                            prod_id = product_id[0]
                            prod_nome = product_id[1] or ''
                        else:
                            prod_id = product_id
                            prod_nome = ''

                        prod_info = cache_produtos.get(prod_id, {})
                        cod_produto = prod_info.get('default_code', '')
                        peso_unitario = prod_info.get('weight', 0)
                        qtd = float(linha.get('quantity', 0) or 0)
                        peso_linha = peso_unitario * qtd
                        preco = float(linha.get('price_unit', 0) or 0)
                        valor = float(linha.get('price_total', 0) or 0)

                        # bulk_insert_mappings não chama __init__: setar TODOS os campos obrigatórios
                        registros_faturamento.append({
                            'numero_nf': numero_nf,
                            'data_fatura': nf.get('data_emissao'),
                            'cnpj_cliente': cliente_info.get('cnpj_cliente', ''),
                            'nome_cliente': cliente_info.get('nome_cliente', ''),
                            'municipio': cliente_info.get('municipio', ''),
                            'estado': cliente_info.get('estado', ''),
                            'vendedor': vendedor,
                            'equipe_vendas': equipe_vendas,
                            'incoterm': incoterm,
                            'cod_produto': cod_produto,
                            'nome_produto': (prod_nome[:200] if prod_nome else ''),
                            'qtd_produto_faturado': qtd,
                            'preco_produto_faturado': preco,
                            'valor_produto_faturado': valor,
                            'peso_unitario_produto': peso_unitario,
                            'peso_total': peso_linha,
                            'origem': origem,
                            'status_nf': status_nf,
                            'revertida': False,
                            'created_at': agora,
                            'updated_at': agora,
                            'created_by': 'Fallback Import Batch',
                        })

                        if cod_produto:
                            produtos_desta_nf.add(cod_produto)
                        valor_total_nf += valor
                        peso_total_nf += peso_linha

                    # RelatorioFaturamentoImportado (se não existe)
                    if numero_nf not in relatorios_existentes:
                        registros_relatorio.append({
                            'numero_nf': numero_nf,
                            'data_fatura': nf.get('data_emissao'),
                            'cnpj_cliente': cliente_info.get('cnpj_cliente', ''),
                            'nome_cliente': cliente_info.get('nome_cliente', ''),
                            'municipio': cliente_info.get('municipio', ''),
                            'estado': cliente_info.get('estado', ''),
                            'valor_total': valor_total_nf,
                            'peso_bruto': peso_total_nf,
                            'origem': origem,
                            'vendedor': vendedor,
                            'equipe_vendas': equipe_vendas,
                            'incoterm': incoterm,
                            'ativo': True,
                            'criado_em': agora,
                        })

                    nfs_processadas.append(numero_nf)

                    # Acumular pedidos afetados para atualização de saldos
                    if origem and produtos_desta_nf:
                        if origem not in pedidos_afetados:
                            pedidos_afetados[origem] = set()
                        pedidos_afetados[origem].update(produtos_desta_nf)

                except Exception as e:
                    total_erros += 1
                    logger.error(f"❌ Erro ao processar NF {nf.get('numero_nf')}: {e}")

            # ============================================================
            # FASE 5a: Bulk insert + commit (P5/P7: antes do pós-processamento)
            # ============================================================
            if registros_faturamento:
                db.session.bulk_insert_mappings(FaturamentoProduto, registros_faturamento)
                logger.info(f"📝 {len(registros_faturamento)} linhas FaturamentoProduto inseridas (bulk)")

            if registros_relatorio:
                db.session.bulk_insert_mappings(RelatorioFaturamentoImportado, registros_relatorio)
                logger.info(f"📋 {len(registros_relatorio)} RelatorioFaturamentoImportado inseridos (bulk)")

            db.session.commit()
            logger.info(f"✅ Commit: {len(nfs_processadas)} NFs importadas")

            # ============================================================
            # FASE 5b: Processar cancelamentos (alinhado com faturamento_service.py:756-761)
            # NFs canceladas no Odoo que EXISTEM localmente → marcar como canceladas
            # ============================================================
            total_canceladas = 0
            total_ignoradas_cancel = nfs_cancel_sem_local  # Canceladas sem registro local

            for nf in nfs_para_cancelar:
                try:
                    numero_nf_cancel = nf['numero_nf']
                    self.faturamento_service._processar_cancelamento_nf(numero_nf_cancel)
                    total_canceladas += 1
                    logger.info(f"🚨 NF {numero_nf_cancel} cancelada via fallback")
                except Exception as e:
                    total_erros += 1
                    logger.error(f"❌ Erro ao cancelar NF {nf.get('numero_nf')}: {e}")

            if total_canceladas > 0:
                db.session.commit()
                logger.info(f"✅ Commit: {total_canceladas} NFs canceladas")

            # ============================================================
            # FASE 6: Pós-processamento batch (saldos + matching)
            # ============================================================
            try:
                # 6a. Atualizar saldos carteira — 1 chamada para TODOS os pedidos
                if pedidos_afetados:
                    logger.info(f"📊 Atualizando saldos para {len(pedidos_afetados)} pedidos...")
                    self.faturamento_service._atualizar_saldos_carteira(pedidos_afetados)
                    logger.info(f"✅ Saldos atualizados")

                # 6b. ProcessadorFaturamento — 1 chamada para TODAS as NFs
                if nfs_processadas:
                    logger.info(f"🔄 Processando match para {len(nfs_processadas)} NFs...")
                    from app.faturamento.services.processar_faturamento import ProcessadorFaturamento
                    processador = ProcessadorFaturamento()
                    resultado_proc = processador.processar_nfs_importadas(
                        usuario='Fallback Import Batch',
                        nfs_especificas=nfs_processadas
                    )
                    if resultado_proc:
                        logger.info(
                            f"✅ Processamento: {resultado_proc.get('processadas', 0)} NFs, "
                            f"{resultado_proc.get('movimentacoes_criadas', 0)} movimentações"
                        )
            except Exception as e:
                logger.warning(
                    f"⚠️ Pós-processamento falhou (NFs já importadas, "
                    f"serão processadas na sync regular): {e}"
                )

            tempo_total = (datetime.now() - inicio).total_seconds()

            # Montar mensagem resumo
            partes_msg = []
            if nfs_processadas:
                partes_msg.append(f'{len(nfs_processadas)} NFs importadas')
            if total_canceladas:
                partes_msg.append(f'{total_canceladas} canceladas')
            if total_erros:
                partes_msg.append(f'{total_erros} erros')
            if not partes_msg:
                partes_msg.append('Nenhuma NF nova para processar')

            return {
                'sucesso': True,
                'mensagem': ', '.join(partes_msg),
                'total_encontradas': len(nfs),
                'total_importadas': len(nfs_processadas),
                'total_ja_existentes': len(nfs_existentes_set),
                'total_canceladas': total_canceladas,
                'total_ignoradas_cancel': total_ignoradas_cancel,
                'total_erros': total_erros,
                'nfs_processadas': nfs_processadas,
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': agora_utc_naive()
            }

        except Exception as e:
            db.session.rollback()
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.error(f"❌ Erro na importação batch: {e}")

            return {
                'sucesso': False,
                'mensagem': f'Erro ao importar faturamento: {str(e)}',
                'erro': str(e),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': agora_utc_naive()
            }

    def _buscar_nf_odoo(self, numero_nf: str) -> Optional[Dict]:
        """
        Busca uma NF específica no Odoo.
        """
        try:
            # Buscar account.move pelo número da NF
            # Alinhado com sync normal: posted + cancel (draft não faz sentido no fallback)
            nfs = self.connection.search_read(
                'account.move',
                [
                    ('l10n_br_numero_nota_fiscal', '=', numero_nf),
                    ('move_type', '=', 'out_invoice'),
                    ('state', 'in', ['posted', 'cancel']),
                    *self.DOMAIN_TIPO_PEDIDO_FATURAMENTO,
                ],
                fields=['id', 'name', 'l10n_br_numero_nota_fiscal', 'state',
                        'l10n_br_tipo_pedido', 'partner_id', 'amount_total',
                        'invoice_date', 'invoice_origin'],
                limit=1
            )

            if not nfs:
                return None

            nf = nfs[0]

            # Buscar linhas da NF
            linhas = self.connection.search_read(
                'account.move.line',
                [
                    ('move_id', '=', nf['id']),
                    ('product_id', '!=', False)
                ],
                fields=['product_id', 'quantity', 'price_unit', 'price_total'],
                limit=100
            )

            return {
                'id': nf.get('id'),
                'name': nf.get('name'),
                'numero_nf': nf.get('l10n_br_numero_nota_fiscal'),
                'state': nf.get('state'),
                'tipo_pedido': nf.get('l10n_br_tipo_pedido'),
                'cliente': nf.get('partner_id'),
                'valor_total': nf.get('amount_total'),
                'data_emissao': nf.get('invoice_date'),
                'origem': nf.get('invoice_origin'),
                'total_linhas': len(linhas),
                'linhas': linhas
            }

        except Exception as e:
            logger.error(f"❌ Erro ao buscar NF {numero_nf} no Odoo: {e}")
            return None

    def _buscar_nfs_por_periodo(self, data_inicio: str, data_fim: str) -> List[Dict]:
        """
        Busca NFs no Odoo emitidas em um período específico.
        """
        try:
            # Alinhado com sync normal (faturamento_service.py:1304-1319):
            # - posted + cancel (draft não faz sentido no fallback por invoice_date)
            # - move_type e numero_nf mantidos como segurança extra
            domain = [
                ('invoice_date', '>=', data_inicio),
                ('invoice_date', '<=', data_fim),
                ('move_type', '=', 'out_invoice'),
                ('state', 'in', ['posted', 'cancel']),
                ('l10n_br_numero_nota_fiscal', '!=', False),
                *self.DOMAIN_TIPO_PEDIDO_FATURAMENTO,
            ]

            nfs = self.connection.search_read(
                'account.move',
                domain,
                fields=['id', 'name', 'l10n_br_numero_nota_fiscal', 'state',
                        'l10n_br_tipo_pedido', 'partner_id', 'amount_total',
                        'invoice_date', 'invoice_origin',
                        # Campos adicionais para batch (elimina re-query O2)
                        'invoice_user_id', 'team_id', 'invoice_incoterm_id'],
                limit=500
            )

            # Formatar resultado
            resultado = []
            for nf in nfs or []:
                resultado.append({
                    'id': nf.get('id'),
                    'numero_nf': nf.get('l10n_br_numero_nota_fiscal'),
                    'state': nf.get('state'),
                    'tipo_pedido': nf.get('l10n_br_tipo_pedido'),
                    'cliente': nf.get('partner_id'),
                    'valor_total': nf.get('amount_total'),
                    'data_emissao': nf.get('invoice_date'),
                    'origem': nf.get('invoice_origin'),
                    # Campos many2one raw do Odoo (para batch, elimina O2)
                    'invoice_user_id': nf.get('invoice_user_id'),
                    'team_id': nf.get('team_id'),
                    'invoice_incoterm_id': nf.get('invoice_incoterm_id'),
                })

            return resultado

        except Exception as e:
            logger.error(f"❌ Erro ao buscar NFs por período: {e}")
            return []

    @staticmethod
    def _extrair_many2one_nome(valor) -> str:
        """Extrai nome de campo many2one do Odoo ([id, name] ou False)."""
        if valor and isinstance(valor, list) and len(valor) > 1:
            return valor[1] or ''
        return ''

    def _buscar_dados_batch_odoo(self, nfs: List[Dict]) -> Dict[str, Dict]:
        """
        Busca dados complementares de TODAS as NFs em batch (Padrão P4 — Batch Fan-Out).

        3 queries batch em vez de 3N queries individuais.

        Args:
            nfs: Lista de dicts retornados por _buscar_nfs_por_periodo
                 (deve conter 'id' como move_id e 'cliente' como partner_id raw)

        Returns:
            Dict com 3 caches:
            - 'parceiros': {partner_id: {cnpj_cliente, nome_cliente, municipio, estado}}
            - 'linhas': {move_id: [linhas_account_move_line]}
            - 'produtos': {product_id: {default_code, weight}}
        """
        move_ids = [nf['id'] for nf in nfs]

        # Coletar partner_ids únicos (many2one: [id, name] ou False)
        partner_ids = set()
        for nf in nfs:
            pid = nf.get('cliente')
            if pid and isinstance(pid, list):
                partner_ids.add(pid[0])
            elif pid and pid is not False:
                partner_ids.add(pid)

        # ------------------------------------------------------------------
        # Query 1: Todas as linhas de produto de TODAS as NFs
        # ------------------------------------------------------------------
        logger.info(f"📦 Batch: buscando linhas de {len(move_ids)} NFs...")
        linhas_raw = self.connection.search_read(
            'account.move.line',
            [('move_id', 'in', move_ids), ('product_id', '!=', False)],
            fields=['move_id', 'product_id', 'quantity', 'price_unit', 'price_total']
        )

        # Indexar linhas por move_id + coletar product_ids
        cache_linhas: Dict[int, List[Dict]] = {}
        product_ids = set()
        for linha in linhas_raw or []:
            mid = linha.get('move_id')
            if isinstance(mid, list):
                mid = mid[0]
            cache_linhas.setdefault(mid, []).append(linha)

            pid = linha.get('product_id')
            if isinstance(pid, list):
                product_ids.add(pid[0])
            elif pid and pid is not False:
                product_ids.add(pid)

        logger.info(
            f"📦 Batch: {len(linhas_raw or [])} linhas, "
            f"{len(product_ids)} produtos únicos"
        )

        # ------------------------------------------------------------------
        # Query 2: Todos os parceiros (clientes)
        # ------------------------------------------------------------------
        cache_parceiros: Dict[int, Dict] = {}
        if partner_ids:
            logger.info(f"👤 Batch: buscando {len(partner_ids)} parceiros...")
            try:
                parceiros_raw = self.connection.read(
                    'res.partner', list(partner_ids),
                    ['name', 'l10n_br_cnpj', 'l10n_br_municipio_id', 'state_id']
                )
                for p in parceiros_raw or []:
                    info = {
                        'cnpj_cliente': (p.get('l10n_br_cnpj') or '').strip(),
                        'nome_cliente': (p.get('name') or '').strip(),
                        'municipio': '',
                        'estado': ''
                    }

                    # Município: many2one → [id, "Cidade (UF)"]
                    # Mesma lógica de parse que faturamento_mapper (linhas 289-296)
                    mun_raw = p.get('l10n_br_municipio_id')
                    if mun_raw and isinstance(mun_raw, list) and len(mun_raw) > 1:
                        nome_mun = mun_raw[1] or ''
                        if '(' in nome_mun and ')' in nome_mun:
                            partes = nome_mun.split('(')
                            info['municipio'] = partes[0].strip()
                            info['estado'] = partes[1].replace(')', '').strip()
                        else:
                            info['municipio'] = nome_mun.strip()

                    # Fallback UF via state_id se município não tinha "(UF)"
                    if not info['estado']:
                        state_raw = p.get('state_id')
                        if state_raw and isinstance(state_raw, list) and len(state_raw) > 1:
                            uf_name = state_raw[1] or ''
                            if len(uf_name) == 2:
                                info['estado'] = uf_name

                    cache_parceiros[p['id']] = info
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar parceiros em batch: {e}")

        # ------------------------------------------------------------------
        # Query 3: Todos os produtos
        # ------------------------------------------------------------------
        cache_produtos: Dict[int, Dict] = {}
        if product_ids:
            logger.info(f"📦 Batch: buscando {len(product_ids)} produtos...")
            try:
                produtos_raw = self.connection.read(
                    'product.product', list(product_ids), ['default_code', 'weight']
                )
                for p in produtos_raw or []:
                    cache_produtos[p['id']] = {
                        'default_code': p.get('default_code') or '',
                        'weight': float(p.get('weight') or 0)
                    }
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar produtos em batch: {e}")

        return {
            'parceiros': cache_parceiros,
            'linhas': cache_linhas,
            'produtos': cache_produtos,
        }

    def _processar_importacao_nf(self, nf_dados: Dict) -> Dict[str, Any]:
        """
        Processa a importação de uma NF específica para o sistema local.

        FLUXO COMPLETO (alinhado com faturamento_service.sincronizar_faturamento_incremental):
        1. Busca TODOS os dados do Odoo (NF, parceiro, produtos em batch)
        2. Insere em FaturamentoProduto com TODOS os campos (status mapeado, municipio, vendedor, etc.)
        3. Insere em RelatorioFaturamentoImportado (necessário para ProcessadorFaturamento)
        4. Atualiza saldos na CarteiraPrincipal via _atualizar_saldos_carteira()
        5. Processa match com Separacao/Embarque via ProcessadorFaturamento
        """
        try:
            from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado

            numero_nf = nf_dados.get('numero_nf')
            move_id = nf_dados.get('id')

            logger.info(f"📝 Processando importação da NF {numero_nf}...")

            # Verificar se NF já existe no sistema
            nf_existente = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).first()
            if nf_existente:
                logger.info(f"⚠️ NF {numero_nf} já existe no sistema (status={nf_existente.status_nf})")
                return {
                    'sucesso': True,
                    'mensagem': f'NF {numero_nf} já existe no sistema (status: {nf_existente.status_nf})',
                    'itens_importados': 0
                }

            # ============================================================
            # FASE 1: Buscar TODOS os dados do Odoo
            # ============================================================

            # 1a. Dados completos da NF (move) — inclui vendedor, equipe, incoterm
            nf_completa = self.connection.search_read(
                'account.move',
                [('id', '=', move_id)],
                fields=[
                    'partner_id', 'l10n_br_numero_nota_fiscal', 'invoice_date',
                    'invoice_origin', 'l10n_br_total_nfe', 'state',
                    'invoice_user_id', 'team_id', 'invoice_incoterm_id'
                ],
                limit=1
            )

            if not nf_completa:
                return {
                    'sucesso': False,
                    'mensagem': f'NF {numero_nf} não encontrada no Odoo',
                    'itens_importados': 0
                }

            nf_info = nf_completa[0]
            origem = nf_info.get('invoice_origin', '')

            # Mapear status do Odoo → status do sistema (mesma lógica de faturamento_service._mapear_status)
            status_nf = self.faturamento_service._mapear_status(nf_info.get('state', ''))

            # Extrair vendedor/equipe/incoterm de campos many2one [id, name]
            vendedor = ''
            m2o = nf_info.get('invoice_user_id')
            if m2o and isinstance(m2o, list) and len(m2o) > 1:
                vendedor = m2o[1] or ''

            equipe_vendas = ''
            m2o = nf_info.get('team_id')
            if m2o and isinstance(m2o, list) and len(m2o) > 1:
                equipe_vendas = m2o[1] or ''

            incoterm = ''
            m2o = nf_info.get('invoice_incoterm_id')
            if m2o and isinstance(m2o, list) and len(m2o) > 1:
                incoterm = m2o[1] or ''

            # 1b. Dados do parceiro (cliente) — inclui município e UF
            cliente_info = {
                'cnpj_cliente': '', 'nome_cliente': '',
                'municipio': '', 'estado': ''
            }

            if nf_info.get('partner_id'):
                partner_id = nf_info['partner_id'][0] if isinstance(nf_info['partner_id'], list) else nf_info['partner_id']
                try:
                    parceiro = self.connection.read(
                        'res.partner', [partner_id],
                        ['name', 'l10n_br_cnpj', 'l10n_br_municipio_id', 'state_id']
                    )
                    if parceiro:
                        p = parceiro[0]
                        cliente_info['cnpj_cliente'] = (p.get('l10n_br_cnpj') or '').strip()
                        cliente_info['nome_cliente'] = (p.get('name') or '').strip()

                        # Município: many2one → [id, "Cidade (UF)"]
                        # Mesma lógica de parse que faturamento_mapper (linhas 289-296)
                        mun_raw = p.get('l10n_br_municipio_id')
                        if mun_raw and isinstance(mun_raw, list) and len(mun_raw) > 1:
                            nome_mun = mun_raw[1] or ''
                            if '(' in nome_mun and ')' in nome_mun:
                                partes = nome_mun.split('(')
                                cliente_info['municipio'] = partes[0].strip()
                                cliente_info['estado'] = partes[1].replace(')', '').strip()
                            else:
                                cliente_info['municipio'] = nome_mun.strip()

                        # Fallback UF via state_id se município não tinha "(UF)"
                        if not cliente_info['estado']:
                            state_raw = p.get('state_id')
                            if state_raw and isinstance(state_raw, list) and len(state_raw) > 1:
                                uf_name = state_raw[1] or ''
                                if len(uf_name) == 2:
                                    cliente_info['estado'] = uf_name
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao buscar dados do parceiro {partner_id}: {e}")

            # 1c. Linhas de produto da NF
            linhas = self.connection.search_read(
                'account.move.line',
                [
                    ('move_id', '=', move_id),
                    ('product_id', '!=', False)
                ],
                fields=['product_id', 'quantity', 'price_unit', 'price_total']
            )

            if not linhas:
                logger.warning(f"⚠️ NF {numero_nf} não tem linhas de produto")
                return {
                    'sucesso': False,
                    'mensagem': f'NF {numero_nf} não tem linhas de produto',
                    'itens_importados': 0
                }

            # 1d. Buscar códigos e pesos de TODOS os produtos em BATCH (elimina N+1)
            product_ids = set()
            for linha in linhas:
                pid = linha.get('product_id')
                if isinstance(pid, list):
                    product_ids.add(pid[0])
                elif pid:
                    product_ids.add(pid)

            produtos_cache = {}  # {product_id: {'default_code': str, 'weight': float}}
            if product_ids:
                try:
                    produtos_odoo = self.connection.read(
                        'product.product', list(product_ids), ['default_code', 'weight']
                    )
                    for p in (produtos_odoo or []):
                        produtos_cache[p['id']] = {
                            'default_code': p.get('default_code') or '',
                            'weight': float(p.get('weight') or 0)
                        }
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao buscar produtos em batch: {e}")

            # ============================================================
            # FASE 2: Gravar FaturamentoProduto (todos os campos)
            # ============================================================
            itens_importados = 0
            produtos_importados = set()
            valor_total_nf = 0
            peso_total_nf = 0

            for linha in linhas:
                try:
                    product_id = linha.get('product_id')
                    if isinstance(product_id, list):
                        prod_id = product_id[0]
                        prod_nome = product_id[1] or ''
                    else:
                        prod_id = product_id
                        prod_nome = ''

                    prod_info = produtos_cache.get(prod_id, {})
                    cod_produto = prod_info.get('default_code', '')
                    peso_unitario = prod_info.get('weight', 0)
                    qtd = float(linha.get('quantity', 0) or 0)
                    peso_linha = peso_unitario * qtd

                    faturamento = FaturamentoProduto(
                        numero_nf=numero_nf,
                        data_fatura=nf_info.get('invoice_date'),
                        cnpj_cliente=cliente_info['cnpj_cliente'],
                        nome_cliente=cliente_info['nome_cliente'],
                        municipio=cliente_info['municipio'],
                        estado=cliente_info['estado'],
                        vendedor=vendedor,
                        equipe_vendas=equipe_vendas,
                        incoterm=incoterm,
                        cod_produto=cod_produto,
                        nome_produto=prod_nome[:200] if prod_nome else '',
                        qtd_produto_faturado=qtd,
                        preco_produto_faturado=linha.get('price_unit', 0),
                        valor_produto_faturado=linha.get('price_total', 0),
                        peso_unitario_produto=peso_unitario,
                        peso_total=peso_linha,
                        origem=origem,
                        status_nf=status_nf,
                        created_by='Fallback Import',
                    )

                    db.session.add(faturamento)
                    itens_importados += 1
                    if cod_produto:
                        produtos_importados.add(cod_produto)
                    valor_total_nf += float(linha.get('price_total', 0) or 0)
                    peso_total_nf += peso_linha

                except Exception as e:
                    logger.error(f"❌ Erro ao importar linha da NF {numero_nf}: {e}")

            # ============================================================
            # FASE 3: Gravar RelatorioFaturamentoImportado (todos os campos)
            # ============================================================
            relatorio_existente = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
            if not relatorio_existente:
                relatorio = RelatorioFaturamentoImportado(
                    numero_nf=numero_nf,
                    data_fatura=nf_info.get('invoice_date'),
                    cnpj_cliente=cliente_info['cnpj_cliente'],
                    nome_cliente=cliente_info['nome_cliente'],
                    municipio=cliente_info['municipio'],
                    estado=cliente_info['estado'],
                    valor_total=valor_total_nf,
                    peso_bruto=peso_total_nf,
                    origem=origem,
                    vendedor=vendedor,
                    equipe_vendas=equipe_vendas,
                    incoterm=incoterm,
                    ativo=True
                )
                db.session.add(relatorio)
                logger.info(f"📋 RelatorioFaturamentoImportado criado para NF {numero_nf}")

            # P5: Commit ANTES do processamento longo (libera conexão DB)
            db.session.commit()
            logger.info(f"✅ NF {numero_nf} importada: {itens_importados} itens (status={status_nf})")

            # ============================================================
            # FASE 4: Pós-processamento (saldos + matching)
            # ============================================================
            try:
                # 4a. Atualizar saldos na CarteiraPrincipal
                if origem and produtos_importados:
                    logger.info(f"📊 Atualizando saldos da carteira para pedido {origem}...")
                    pedidos_afetados = {origem: produtos_importados}
                    self.faturamento_service._atualizar_saldos_carteira(pedidos_afetados)
                    logger.info(f"✅ Saldos atualizados para {len(produtos_importados)} produtos")

                # 4b. Processar match com Separacao/Embarque via ProcessadorFaturamento
                logger.info(f"🔄 Processando match com Separacao/Embarque...")
                from app.faturamento.services.processar_faturamento import ProcessadorFaturamento
                processador = ProcessadorFaturamento()
                resultado_proc = processador.processar_nfs_importadas(
                    usuario='Fallback Import',
                    nfs_especificas=[numero_nf]
                )

                if resultado_proc:
                    logger.info(
                        f"✅ Processamento completo: {resultado_proc.get('processadas', 0)} NFs, "
                        f"{resultado_proc.get('movimentacoes_criadas', 0)} movimentações"
                    )

            except Exception as e:
                logger.warning(
                    f"⚠️ Processamento pós-importação falhou (NF já importada, "
                    f"será processada na sync regular): {e}"
                )

            return {
                'sucesso': True,
                'mensagem': f'NF {numero_nf} importada e processada com sucesso '
                            f'({itens_importados} itens, status={status_nf})',
                'itens_importados': itens_importados
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao processar NF: {e}")
            return {
                'sucesso': False,
                'mensagem': str(e),
                'itens_importados': 0
            }
