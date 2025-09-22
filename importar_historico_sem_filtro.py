#!/usr/bin/env python3
"""
Script de Importação Histórica do Odoo - Versão SEM FILTRO
===========================================================

Versão especial que busca TODOS os pedidos do período, sem aplicar
nenhum filtro de saldo pendente.

Autor: Sistema de Importação
Data: 21/09/2025
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import argparse
from decimal import Decimal

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'importacao_historica_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ImportadorSemFiltro:
    """
    Importador que ignora filtros de saldo pendente
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.estatisticas = {
            'faturamento': {},
            'carteira': {},
            'alertas': [],
            'pedidos_saldo_positivo': []
        }

        from app import create_app, db
        self.app = create_app()
        self.db = db

        logger.info(f"🚀 Importador SEM FILTRO inicializado - Modo: {'DRY RUN' if dry_run else 'PRODUÇÃO'}")

    def executar_importacao_completa(self) -> Dict[str, Any]:
        """
        Executa importação completa sem filtros
        """
        with self.app.app_context():
            try:
                logger.info("="*80)
                logger.info("📊 IMPORTAÇÃO HISTÓRICA SEM FILTROS")
                logger.info(f"⚙️ Modo: {'DRY RUN (simulação)' if self.dry_run else 'PRODUÇÃO (gravação real)'}")
                logger.info("="*80)

                # FASE 1: Importar Faturamento
                logger.info("\n📦 FASE 1: IMPORTANDO FATURAMENTO (72 HORAS)")
                resultado_faturamento = self._importar_faturamento_72h()
                self.estatisticas['faturamento'] = resultado_faturamento

                if not resultado_faturamento.get('sucesso'):
                    logger.error("❌ Falha na importação do faturamento")
                    return self.estatisticas

                # FASE 2: Importar Carteira SEM FILTROS
                logger.info("\n📋 FASE 2: IMPORTANDO CARTEIRA (01/07 a 21/09) - SEM FILTROS")
                resultado_carteira = self._importar_carteira_sem_filtro()
                self.estatisticas['carteira'] = resultado_carteira

                if not resultado_carteira.get('sucesso'):
                    logger.error("❌ Falha na importação da carteira")
                    return self.estatisticas

                # FASE 3: Relatório Final
                self._gerar_relatorio_final()

                return self.estatisticas

            except Exception as e:
                logger.error(f"❌ ERRO CRÍTICO: {e}")
                import traceback
                traceback.print_exc()
                self.estatisticas['erro_critico'] = str(e)
                return self.estatisticas

    def _importar_faturamento_72h(self) -> Dict[str, Any]:
        """
        Importa faturamento das últimas 72 horas
        """
        try:
            from app.odoo.services.faturamento_service import FaturamentoService

            logger.info("🔄 Iniciando importação de faturamento...")
            minutos_72h = 72 * 60

            service = FaturamentoService()

            if self.dry_run:
                logger.info("🔍 MODO DRY RUN: Analisando dados...")

                resultado = service.obter_faturamento_otimizado(
                    usar_filtro_postado=True,
                    limite=0,
                    modo_incremental=True,
                    minutos_janela=minutos_72h,
                    minutos_status=minutos_72h
                )

                if resultado['sucesso']:
                    dados = resultado.get('dados', [])
                    nfs_unicas = len(set(item.get('numero_nf') for item in dados))

                    logger.info(f"📊 Análise Faturamento:")
                    logger.info(f"   - Total registros: {len(dados)}")
                    logger.info(f"   - NFs únicas: {nfs_unicas}")

                    return {
                        'sucesso': True,
                        'modo': 'dry_run',
                        'total_registros': len(dados),
                        'nfs_unicas': nfs_unicas
                    }
                else:
                    return {'sucesso': False, 'erro': resultado.get('erro')}

            else:
                logger.info("⚡ MODO PRODUÇÃO: Sincronizando...")

                resultado = service.sincronizar_faturamento_incremental(
                    minutos_janela=minutos_72h,
                    primeira_execucao=False,
                    minutos_status=minutos_72h
                )

                if resultado.get('sucesso'):
                    logger.info(f"✅ Faturamento sincronizado:")
                    logger.info(f"   - Novos: {resultado.get('registros_novos', 0)}")
                    logger.info(f"   - Atualizados: {resultado.get('registros_atualizados', 0)}")

                return resultado

        except Exception as e:
            logger.error(f"❌ Erro ao importar faturamento: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def _importar_carteira_sem_filtro(self) -> Dict[str, Any]:
        """
        Importa carteira SEM APLICAR FILTRO de saldo pendente
        """
        try:
            from app.odoo.utils.connection import get_odoo_connection
            from app.carteira.models import CarteiraPrincipal
            from app.faturamento.models import FaturamentoProduto
            from sqlalchemy import func

            logger.info("🔄 Buscando TODOS os pedidos do período (sem filtros)...")

            data_inicio = '2025-07-10'
            data_fim = '2025-09-21'

            # Conectar direto ao Odoo para evitar filtros
            connection = get_odoo_connection()
            if not connection:
                return {'sucesso': False, 'erro': 'Conexão Odoo indisponível'}

            # Pedidos específicos para IGNORAR (problemas conhecidos)
            pedidos_ignorar = ['VCD2518963', 'VCD2519460']

            # Buscar TODOS os pedidos CRIADOS no período, sem filtrar por saldo
            # MAS filtrar apenas Venda e Bonificação
            # E excluir pedidos problemáticos
            # IMPORTANTE: Usar create_date para buscar pedidos CRIADOS no período
            domain = [
                ('order_id.create_date', '>=', data_inicio),
                ('order_id.create_date', '<=', data_fim),
                ('order_id.state', 'in', ['draft', 'sent', 'sale', 'done']),
                ('order_id.name', 'not in', pedidos_ignorar),  # Excluir pedidos problemáticos
                '|',  # OR entre tipos de pedido
                ('order_id.l10n_br_tipo_pedido', '=', 'venda'),
                ('order_id.l10n_br_tipo_pedido', '=', 'bonificacao')
            ]

            logger.info(f"📅 Período: {data_inicio} até {data_fim}")
            logger.info("🔍 Buscando no Odoo SEM FILTRO de saldo...")
            logger.info("✅ Filtrando apenas pedidos de Venda e Bonificação")
            logger.info(f"⚠️ Ignorando pedidos problemáticos: {', '.join(pedidos_ignorar)}")

            # Buscar dados diretamente
            campos = ['id', 'order_id', 'product_id', 'product_uom_qty',
                     'qty_saldo', 'qty_cancelado', 'price_unit']

            dados_brutos = connection.search_read('sale.order.line', domain, campos)
            logger.info(f"✅ {len(dados_brutos)} linhas encontradas no Odoo")

            if self.dry_run:
                # Modo DRY RUN - apenas analisar
                pedidos_unicos = set()
                produtos_unicos = set()
                itens_para_inserir = []
                itens_para_atualizar = []

                from app.odoo.services.carteira_service import CarteiraService
                service = CarteiraService()

                # Processar dados com múltiplas queries
                dados_processados = service._processar_dados_carteira_com_multiplas_queries(dados_brutos)

                logger.info(f"📊 {len(dados_processados)} registros processados")

                for item in dados_processados:
                    num_pedido = item.get('num_pedido')
                    cod_produto = item.get('cod_produto')

                    # Ignorar pedidos problemáticos também no processamento
                    if num_pedido in pedidos_ignorar:
                        continue

                    pedidos_unicos.add(num_pedido)
                    produtos_unicos.add(cod_produto)

                    # Verificar se existe
                    existe = self.db.session.query(CarteiraPrincipal.id).filter_by(
                        num_pedido=num_pedido,
                        cod_produto=cod_produto
                    ).first()

                    if not existe:
                        itens_para_inserir.append((num_pedido, cod_produto))

                        # Calcular saldo
                        qtd_produto = float(item.get('qtd_produto_pedido', 0))

                        qtd_faturada = self.db.session.query(
                            func.sum(FaturamentoProduto.qtd_produto_faturado)
                        ).filter(
                            FaturamentoProduto.origem == num_pedido,
                            FaturamentoProduto.cod_produto == cod_produto,
                            FaturamentoProduto.status_nf != 'Cancelado'
                        ).scalar() or 0

                        saldo = qtd_produto - float(qtd_faturada)

                        if saldo > 0:
                            self.estatisticas['pedidos_saldo_positivo'].append({
                                'num_pedido': num_pedido,
                                'cod_produto': cod_produto,
                                'qtd_produto': qtd_produto,
                                'qtd_faturada': float(qtd_faturada),
                                'saldo': saldo
                            })
                    else:
                        itens_para_atualizar.append((num_pedido, cod_produto))

                logger.info(f"📊 Análise DRY RUN:")
                logger.info(f"   - Total registros: {len(dados_processados)}")
                logger.info(f"   - Pedidos únicos: {len(pedidos_unicos)}")
                logger.info(f"   - Produtos únicos: {len(produtos_unicos)}")
                logger.info(f"   - Itens NOVOS: {len(itens_para_inserir)}")
                logger.info(f"   - Itens EXISTENTES: {len(itens_para_atualizar)}")

                if self.estatisticas['pedidos_saldo_positivo']:
                    logger.warning(f"⚠️ {len(self.estatisticas['pedidos_saldo_positivo'])} itens com saldo > 0")

                    for i, item in enumerate(self.estatisticas['pedidos_saldo_positivo'][:20], 1):
                        logger.warning(f"   {i}. {item['num_pedido']}/{item['cod_produto']}: "
                                     f"Saldo = {item['saldo']:.2f}")

                return {
                    'sucesso': True,
                    'modo': 'dry_run',
                    'total_registros': len(dados_processados),
                    'pedidos_unicos': len(pedidos_unicos),
                    'produtos_unicos': len(produtos_unicos),
                    'itens_novos': len(itens_para_inserir),
                    'itens_existentes': len(itens_para_atualizar),
                    'itens_com_saldo_positivo': len(self.estatisticas['pedidos_saldo_positivo'])
                }

            else:
                # MODO PRODUÇÃO
                logger.info("⚡ MODO PRODUÇÃO: Processando e gravando...")

                from app.odoo.services.carteira_service import CarteiraService
                service = CarteiraService()

                # Processar dados
                dados_processados = service._processar_dados_carteira_com_multiplas_queries(dados_brutos)
                logger.info(f"📊 {len(dados_processados)} registros processados")

                # Filtrar pedidos problemáticos ANTES de processar
                dados_filtrados = []
                pedidos_removidos = 0
                for item in dados_processados:
                    if item.get('num_pedido') not in pedidos_ignorar:
                        dados_filtrados.append(item)
                    else:
                        pedidos_removidos += 1

                if pedidos_removidos > 0:
                    logger.info(f"⚠️ {pedidos_removidos} itens de pedidos problemáticos removidos")

                dados_processados = dados_filtrados

                # Garantir cadastros de palletização
                logger.info("📦 Garantindo cadastros de palletização...")
                resultado_pallet = service._garantir_cadastro_palletizacao_completo(dados_processados)
                logger.info(f"   - Cadastros criados: {resultado_pallet.get('criados', 0)}")
                logger.info(f"   - Cadastros atualizados: {resultado_pallet.get('atualizados', 0)}")

                # Sanitizar dados
                logger.info("🧹 Sanitizando dados...")
                dados_sanitizados = service._sanitizar_dados_carteira(dados_processados)

                # Processar UPSERT manual
                novos = 0
                atualizados = 0
                erros = 0

                logger.info("💾 Gravando no banco...")

                for item in dados_sanitizados:
                    try:
                        num_pedido = item['num_pedido']
                        cod_produto = item['cod_produto']

                        # Verificar se existe
                        registro = self.db.session.query(CarteiraPrincipal).filter_by(
                            num_pedido=num_pedido,
                            cod_produto=cod_produto
                        ).first()

                        if registro:
                            # Atualizar
                            for campo, valor in item.items():
                                if hasattr(registro, campo) and campo not in ['id', 'created_at']:
                                    setattr(registro, campo, valor)
                            atualizados += 1
                        else:
                            # Inserir novo
                            novo_registro = CarteiraPrincipal(**item)
                            self.db.session.add(novo_registro)
                            novos += 1

                        # Commit a cada 100 registros
                        if (novos + atualizados) % 100 == 0:
                            self.db.session.commit()
                            logger.info(f"   💾 {novos + atualizados} registros processados...")

                    except Exception as e:
                        logger.error(f"Erro ao processar {num_pedido}/{cod_produto}: {e}")
                        erros += 1
                        self.db.session.rollback()

                # Commit final
                self.db.session.commit()

                logger.info(f"✅ Carteira sincronizada:")
                logger.info(f"   - Novos: {novos}")
                logger.info(f"   - Atualizados: {atualizados}")
                logger.info(f"   - Erros: {erros}")

                # Recalcular saldos
                logger.info("🔄 Recalculando saldos...")
                self._recalcular_saldos_importados(dados_processados)

                return {
                    'sucesso': True,
                    'modo': 'producao',
                    'novos': novos,
                    'atualizados': atualizados,
                    'erros': erros,
                    'total_processados': novos + atualizados
                }

        except Exception as e:
            logger.error(f"❌ Erro na importação: {e}")
            import traceback
            traceback.print_exc()
            return {'sucesso': False, 'erro': str(e)}

    def _recalcular_saldos_importados(self, dados_importados):
        """
        Recalcula qtd_saldo_produto_pedido para todos os pedidos importados
        """
        try:
            from app.carteira.models import CarteiraPrincipal
            from app.faturamento.models import FaturamentoProduto
            from sqlalchemy import func

            logger.info("🔄 Recalculando saldos dos pedidos importados...")

            # Pedidos para ignorar
            pedidos_ignorar = ['VCD2518963', 'VCD2519460']

            pedidos_processados = set()
            saldos_positivos = []

            for item in dados_importados:
                num_pedido = item.get('num_pedido')
                cod_produto = item.get('cod_produto')

                # Ignorar pedidos problemáticos no recálculo
                if num_pedido in pedidos_ignorar:
                    continue

                if (num_pedido, cod_produto) in pedidos_processados:
                    continue

                pedidos_processados.add((num_pedido, cod_produto))

                # Buscar registro
                registro = self.db.session.query(CarteiraPrincipal).filter_by(
                    num_pedido=num_pedido,
                    cod_produto=cod_produto
                ).first()

                if registro:
                    # Calcular saldo real
                    qtd_produto = float(registro.qtd_produto_pedido or 0)

                    # Buscar faturamento
                    qtd_faturada = self.db.session.query(
                        func.sum(FaturamentoProduto.qtd_produto_faturado)
                    ).filter(
                        FaturamentoProduto.origem == num_pedido,
                        FaturamentoProduto.cod_produto == cod_produto,
                        FaturamentoProduto.status_nf != 'Cancelado'
                    ).scalar() or 0

                    qtd_faturada = float(qtd_faturada)
                    saldo_calculado = qtd_produto - qtd_faturada

                    # Atualizar saldo
                    registro.qtd_saldo_produto_pedido = saldo_calculado
                    registro.updated_at = datetime.now()
                    registro.updated_by = 'RecalculoImportacao'

                    if saldo_calculado > 0:
                        saldos_positivos.append({
                            'num_pedido': num_pedido,
                            'cod_produto': cod_produto,
                            'saldo': saldo_calculado
                        })

            # Commit
            self.db.session.commit()

            logger.info(f"✅ {len(pedidos_processados)} saldos recalculados")

            if saldos_positivos:
                logger.warning(f"⚠️ {len(saldos_positivos)} pedidos com saldo > 0 após recálculo")
                for item in saldos_positivos[:20]:
                    logger.warning(f"   - {item['num_pedido']}/{item['cod_produto']}: {item['saldo']:.2f}")

            self.estatisticas['pedidos_saldo_positivo'] = saldos_positivos

        except Exception as e:
            logger.error(f"Erro ao recalcular saldos: {e}")
            self.db.session.rollback()

    def _gerar_relatorio_final(self):
        """
        Gera relatório final
        """
        logger.info("\n" + "="*80)
        logger.info("📊 RELATÓRIO FINAL - IMPORTAÇÃO SEM FILTROS")
        logger.info("="*80)

        modo = "DRY RUN" if self.dry_run else "PRODUÇÃO"
        logger.info(f"Modo: {modo}")

        # Faturamento
        fat = self.estatisticas.get('faturamento', {})
        if fat.get('sucesso'):
            logger.info("\n📦 FATURAMENTO:")
            if self.dry_run:
                logger.info(f"   ✅ {fat.get('total_registros', 0)} registros encontrados")
            else:
                logger.info(f"   ✅ Novos: {fat.get('registros_novos', 0)}")
                logger.info(f"   📝 Atualizados: {fat.get('registros_atualizados', 0)}")

        # Carteira
        cart = self.estatisticas.get('carteira', {})
        if cart.get('sucesso'):
            logger.info("\n📋 CARTEIRA (SEM FILTROS):")
            if self.dry_run:
                logger.info(f"   ✅ Total: {cart.get('total_registros', 0)}")
                logger.info(f"   🆕 Novos: {cart.get('itens_novos', 0)}")
                logger.info(f"   📝 Existentes: {cart.get('itens_existentes', 0)}")

                if cart.get('itens_com_saldo_positivo'):
                    logger.warning(f"   ⚠️ Com saldo > 0: {cart.get('itens_com_saldo_positivo')}")
            else:
                logger.info(f"   ✅ Novos: {cart.get('novos', 0)}")
                logger.info(f"   📝 Atualizados: {cart.get('atualizados', 0)}")

        # Alertas sobre saldos
        if self.estatisticas.get('pedidos_saldo_positivo'):
            total = len(self.estatisticas['pedidos_saldo_positivo'])
            logger.warning(f"\n⚠️ ATENÇÃO: {total} pedidos com saldo > 0")
            logger.info("Isso pode indicar pedidos reais pendentes ou faturamento incompleto")

        logger.info("\n" + "="*80)
        logger.info("✅ PROCESSO FINALIZADO")
        logger.info("="*80)


def main():
    parser = argparse.ArgumentParser(description='Importador Histórico SEM FILTROS')
    parser.add_argument('--producao', action='store_true', help='Modo produção')
    parser.add_argument('--confirmar', action='store_true', help='Confirmar produção')

    args = parser.parse_args()
    dry_run = not args.producao

    if args.producao and not args.confirmar:
        print("⚠️  MODO PRODUÇÃO - Confirme com 'SIM': ")
        if input() != 'SIM':
            print("Cancelado")
            return

    importador = ImportadorSemFiltro(dry_run=dry_run)
    resultado = importador.executar_importacao_completa()

    if resultado.get('erro_critico'):
        sys.exit(1)

    fat_ok = resultado.get('faturamento', {}).get('sucesso', False)
    cart_ok = resultado.get('carteira', {}).get('sucesso', False)

    sys.exit(0 if (fat_ok and cart_ok) else 1)


if __name__ == "__main__":
    main()