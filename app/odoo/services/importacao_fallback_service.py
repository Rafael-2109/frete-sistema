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

logger = logging.getLogger(__name__)


class ImportacaoFallbackService:
    """
    Serviço para importação manual de pedidos e faturamentos do Odoo

    Funciona como fallback quando a sincronização automática não importou.
    """

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
                    'timestamp': datetime.now()
                }

            num_pedido = num_pedido.strip().upper()

            # Verificar se o pedido existe no Odoo
            pedido_odoo = self._verificar_pedido_odoo(num_pedido)

            if not pedido_odoo:
                return {
                    'sucesso': False,
                    'mensagem': f'Pedido {num_pedido} não encontrado no Odoo',
                    'timestamp': datetime.now()
                }

            if pedido_odoo.get('cancelado'):
                return {
                    'sucesso': False,
                    'mensagem': f'Pedido {num_pedido} está cancelado no Odoo',
                    'dados_odoo': pedido_odoo,
                    'timestamp': datetime.now()
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
                    'timestamp': datetime.now()
                }
            else:
                return {
                    'sucesso': False,
                    'mensagem': f'Erro ao importar pedido: {resultado.get("mensagem", "Erro desconhecido")}',
                    'erro': resultado.get('erro'),
                    'tempo_execucao': round(tempo_total, 2),
                    'timestamp': datetime.now()
                }

        except Exception as e:
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.error(f"❌ Erro ao importar pedido {num_pedido}: {e}")

            return {
                'sucesso': False,
                'mensagem': f'Erro ao importar pedido: {str(e)}',
                'erro': str(e),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': datetime.now()
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
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d') if data_fim else datetime.now()
            except ValueError as e:
                return {
                    'sucesso': False,
                    'mensagem': f'Formato de data inválido. Use YYYY-MM-DD. Erro: {str(e)}',
                    'timestamp': datetime.now()
                }

            # Buscar pedidos no Odoo no período
            pedidos = self._buscar_pedidos_por_data(data_inicio, data_fim or datetime.now().strftime('%Y-%m-%d'))

            if not pedidos:
                return {
                    'sucesso': True,
                    'mensagem': f'Nenhum pedido encontrado no período {data_inicio} a {data_fim}',
                    'total_encontrados': 0,
                    'timestamp': datetime.now()
                }

            logger.info(f"✅ Encontrados {len(pedidos)} pedidos no período")

            # Extrair números dos pedidos
            numeros_pedidos = [p.get('name') for p in pedidos if p.get('name')]

            if not numeros_pedidos:
                return {
                    'sucesso': False,
                    'mensagem': 'Nenhum pedido válido encontrado no período',
                    'timestamp': datetime.now()
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
                'timestamp': datetime.now()
            }

        except Exception as e:
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.error(f"❌ Erro ao importar pedidos por data: {e}")

            return {
                'sucesso': False,
                'mensagem': f'Erro ao importar pedidos: {str(e)}',
                'erro': str(e),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': datetime.now()
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
            # Domain com filtros de tipo de pedido
            domain = [
                ('create_date', '>=', f'{data_inicio} 00:00:00'),
                ('create_date', '<=', f'{data_fim} 23:59:59'),
                ('state', 'in', ['draft', 'sent', 'sale']),
                '|', '|', '|', '|',
                ('l10n_br_tipo_pedido', '=', 'venda'),
                ('l10n_br_tipo_pedido', '=', 'bonificacao'),
                ('l10n_br_tipo_pedido', '=', 'industrializacao'),
                ('l10n_br_tipo_pedido', '=', 'exportacao'),
                ('l10n_br_tipo_pedido', '=', 'venda-industrializacao')
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
                    'timestamp': datetime.now()
                }

            numero_nf = numero_nf.strip()

            # Buscar NF no Odoo
            nf_odoo = self._buscar_nf_odoo(numero_nf)

            if not nf_odoo:
                return {
                    'sucesso': False,
                    'mensagem': f'NF {numero_nf} não encontrada no Odoo',
                    'timestamp': datetime.now()
                }

            logger.info(f"✅ NF {numero_nf} encontrada no Odoo. Iniciando importação...")

            # Importar linhas da NF
            resultado = self._processar_importacao_nf(nf_odoo)

            tempo_total = (datetime.now() - inicio).total_seconds()

            return {
                'sucesso': resultado.get('sucesso', False),
                'mensagem': resultado.get('mensagem', ''),
                'dados_nf': nf_odoo,
                'itens_importados': resultado.get('itens_importados', 0),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': datetime.now()
            }

        except Exception as e:
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.error(f"❌ Erro ao importar NF {numero_nf}: {e}")

            return {
                'sucesso': False,
                'mensagem': f'Erro ao importar NF: {str(e)}',
                'erro': str(e),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': datetime.now()
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
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d') if data_fim else datetime.now()
            except ValueError as e:
                return {
                    'sucesso': False,
                    'mensagem': f'Formato de data inválido. Use YYYY-MM-DD. Erro: {str(e)}',
                    'timestamp': datetime.now()
                }

            # Buscar NFs no período
            nfs = self._buscar_nfs_por_periodo(data_inicio, data_fim or datetime.now().strftime('%Y-%m-%d'))

            if not nfs:
                return {
                    'sucesso': True,
                    'mensagem': f'Nenhuma NF encontrada no período {data_inicio} a {data_fim}',
                    'total_encontradas': 0,
                    'timestamp': datetime.now()
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
                'timestamp': datetime.now()
            }

        except Exception as e:
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.error(f"❌ Erro ao importar faturamento por período: {e}")

            return {
                'sucesso': False,
                'mensagem': f'Erro ao importar faturamento: {str(e)}',
                'erro': str(e),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': datetime.now()
            }

    def _buscar_nf_odoo(self, numero_nf: str) -> Optional[Dict]:
        """
        Busca uma NF específica no Odoo.
        """
        try:
            # Buscar account.move pelo número da NF
            nfs = self.connection.search_read(
                'account.move',
                [
                    ('l10n_br_numero_nota_fiscal', '=', numero_nf),
                    ('move_type', '=', 'out_invoice'),  # Apenas NFs de saída
                    '|', '|', '|', '|',
                    ('l10n_br_tipo_pedido', '=', 'venda'),
                    ('l10n_br_tipo_pedido', '=', 'bonificacao'),
                    ('l10n_br_tipo_pedido', '=', 'industrializacao'),
                    ('l10n_br_tipo_pedido', '=', 'exportacao'),
                    ('l10n_br_tipo_pedido', '=', 'venda-industrializacao')
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
            domain = [
                ('invoice_date', '>=', data_inicio),
                ('invoice_date', '<=', data_fim),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('l10n_br_numero_nota_fiscal', '!=', False),
                '|', '|', '|', '|',
                ('l10n_br_tipo_pedido', '=', 'venda'),
                ('l10n_br_tipo_pedido', '=', 'bonificacao'),
                ('l10n_br_tipo_pedido', '=', 'industrializacao'),
                ('l10n_br_tipo_pedido', '=', 'exportacao'),
                ('l10n_br_tipo_pedido', '=', 'venda-industrializacao')
            ]

            nfs = self.connection.search_read(
                'account.move',
                domain,
                fields=['id', 'name', 'l10n_br_numero_nota_fiscal', 'state',
                        'l10n_br_tipo_pedido', 'partner_id', 'amount_total',
                        'invoice_date', 'invoice_origin'],
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
                    'origem': nf.get('invoice_origin')
                })

            return resultado

        except Exception as e:
            logger.error(f"❌ Erro ao buscar NFs por período: {e}")
            return []

    def _processar_importacao_nf(self, nf_dados: Dict) -> Dict[str, Any]:
        """
        Processa a importação de uma NF específica para o sistema local.

        FLUXO COMPLETO:
        1. Insere em FaturamentoProduto
        2. Insere em RelatorioFaturamentoImportado
        3. Atualiza saldos na CarteiraPrincipal
        4. Processa match com Separacao/Embarque via ProcessadorFaturamento
        """
        try:
            from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
            from app.odoo.utils.carteira_mapper import CarteiraMapper

            numero_nf = nf_dados.get('numero_nf')
            move_id = nf_dados.get('id')

            logger.info(f"📝 Processando importação da NF {numero_nf}...")

            # Verificar se NF já existe no sistema
            nf_existente = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).first()
            if nf_existente:
                logger.info(f"⚠️ NF {numero_nf} já existe no sistema")
                return {
                    'sucesso': True,
                    'mensagem': f'NF {numero_nf} já existe no sistema',
                    'itens_importados': 0
                }

            # Buscar linhas detalhadas da NF
            linhas = self.connection.search_read(
                'account.move.line',
                [
                    ('move_id', '=', move_id),
                    ('product_id', '!=', False)
                ],
                fields=[
                    'product_id', 'quantity', 'price_unit', 'price_total',
                    'l10n_br_icms_valor', 'l10n_br_icmsst_valor',
                    'l10n_br_pis_valor', 'l10n_br_cofins_valor'
                ]
            )

            if not linhas:
                logger.warning(f"⚠️ NF {numero_nf} não tem linhas de produto")
                return {
                    'sucesso': False,
                    'mensagem': f'NF {numero_nf} não tem linhas de produto',
                    'itens_importados': 0
                }

            # Buscar dados adicionais da NF
            nf_completa = self.connection.search_read(
                'account.move',
                [('id', '=', move_id)],
                fields=[
                    'partner_id', 'l10n_br_numero_nota_fiscal', 'invoice_date',
                    'invoice_origin', 'l10n_br_total_nfe', 'state'
                ],
                limit=1
            )

            if not nf_completa:
                return {
                    'sucesso': False,
                    'mensagem': f'NF {numero_nf} não encontrada para importação',
                    'itens_importados': 0
                }

            nf_info = nf_completa[0]
            origem = nf_info.get('invoice_origin', '')

            # Mapear dados do cliente
            mapper = CarteiraMapper()
            cliente_info = {}

            if nf_info.get('partner_id'):
                partner_id = nf_info['partner_id'][0] if isinstance(nf_info['partner_id'], list) else nf_info['partner_id']
                cliente_info = mapper._buscar_dados_parceiro(partner_id) or {}

            # Importar cada linha - coletar cod_produto para atualização de saldos
            itens_importados = 0
            produtos_importados = set()
            valor_total_nf = 0

            for linha in linhas:
                try:
                    product_id = linha.get('product_id')
                    if isinstance(product_id, list):
                        prod_id = product_id[0]
                        prod_nome = product_id[1]
                    else:
                        prod_id = product_id
                        prod_nome = ''

                    # Buscar código do produto
                    produto_info = self.connection.read(
                        'product.product',
                        [prod_id],
                        ['default_code']
                    )

                    cod_produto = produto_info[0].get('default_code', '') if produto_info else ''

                    # Criar registro de faturamento
                    faturamento = FaturamentoProduto(
                        numero_nf=numero_nf,
                        cod_produto=cod_produto,
                        nome_produto=prod_nome[:255] if prod_nome else '',
                        qtd_produto_faturado=linha.get('quantity', 0),
                        preco_produto=linha.get('price_unit', 0),
                        valor_total=linha.get('price_total', 0),
                        data_nf=nf_info.get('invoice_date'),
                        origem=origem,
                        cnpj_cpf=cliente_info.get('cnpj', ''),
                        raz_social=cliente_info.get('razao_social', ''),
                        status_nf='Ativa',
                        icms=linha.get('l10n_br_icms_valor', 0),
                        icms_st=linha.get('l10n_br_icmsst_valor', 0),
                        pis=linha.get('l10n_br_pis_valor', 0),
                        cofins=linha.get('l10n_br_cofins_valor', 0)
                    )

                    db.session.add(faturamento)
                    itens_importados += 1
                    produtos_importados.add(cod_produto)
                    valor_total_nf += float(linha.get('price_total', 0) or 0)

                except Exception as e:
                    logger.error(f"❌ Erro ao importar linha da NF {numero_nf}: {e}")

            # Inserir em RelatorioFaturamentoImportado (necessário para ProcessadorFaturamento)
            relatorio_existente = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
            if not relatorio_existente:
                relatorio = RelatorioFaturamentoImportado(
                    numero_nf=numero_nf,
                    data_fatura=nf_info.get('invoice_date'),
                    cnpj_cliente=cliente_info.get('cnpj', ''),
                    nome_cliente=cliente_info.get('razao_social', ''),
                    valor_total=valor_total_nf,
                    origem=origem,
                    ativo=True
                )
                db.session.add(relatorio)
                logger.info(f"📋 RelatorioFaturamentoImportado criado para NF {numero_nf}")

            db.session.commit()
            logger.info(f"✅ NF {numero_nf} importada: {itens_importados} itens")

            # ============================================================
            # PROCESSAMENTO COMPLETO: Atualizar saldos e sincronizar
            # ============================================================
            try:
                # 1. Atualizar saldos na CarteiraPrincipal
                if origem and produtos_importados:
                    logger.info(f"📊 Atualizando saldos da carteira para pedido {origem}...")
                    pedidos_afetados = {origem: produtos_importados}
                    self.faturamento_service._atualizar_saldos_carteira(pedidos_afetados)
                    logger.info(f"✅ Saldos atualizados para {len(produtos_importados)} produtos")

                # 2. Processar match com Separacao e Embarque
                logger.info(f"🔄 Processando match com Separacao/Embarque...")
                from app.faturamento.services.processar_faturamento import ProcessadorFaturamento
                processador = ProcessadorFaturamento()
                resultado_proc = processador.processar_nfs_importadas(
                    usuario='Fallback Import',
                    limpar_inconsistencias=False,
                    nfs_especificas=[numero_nf]
                )

                if resultado_proc:
                    logger.info(f"✅ Processamento completo: {resultado_proc.get('processadas', 0)} NFs, "
                              f"{resultado_proc.get('movimentacoes_criadas', 0)} movimentações")

            except Exception as e:
                logger.warning(f"⚠️ Processamento pós-importação falhou (NF foi importada): {e}")
                # NF foi importada, processamento pode ser feito depois pela sincronização regular

            return {
                'sucesso': True,
                'mensagem': f'NF {numero_nf} importada e processada com sucesso',
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
