"""
Script para Importação Específica de Pedido ou Nota Fiscal do Odoo
===================================================================

Permite importar um pedido ou NF específica do Odoo para o sistema,
respeitando toda a lógica existente em carteira_service.py e faturamento_service.py

Uso:
    # Importar pedido
    python scripts/importar_pedido_nf_especifico.py --pedido VSC01234

    # Importar NF
    python scripts/importar_pedido_nf_especifico.py --nf 12345

    # Modo verboso
    python scripts/importar_pedido_nf_especifico.py --pedido VSC01234 --verbose

Autor: Sistema de Fretes
Data: 2025-01-10
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.odoo.services.carteira_service import CarteiraService
from app.odoo.services.faturamento_service import FaturamentoService
from app.faturamento.services.processar_faturamento import ProcessadorFaturamento
from app.faturamento.models import RelatorioFaturamentoImportado
from app.carteira.models import CarteiraPrincipal

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImportadorPedidoNFEspecifico:
    """Importador de pedido ou NF específica do Odoo"""

    def __init__(self, verbose=False):
        self.app = create_app()
        self.carteira_service = CarteiraService()
        self.faturamento_service = FaturamentoService()
        self.processador_faturamento = ProcessadorFaturamento()

        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger('app.odoo').setLevel(logging.DEBUG)
            logging.getLogger('app.faturamento').setLevel(logging.DEBUG)

    def importar_pedido(self, numero_pedido: str) -> dict:
        """
        Importa um pedido específico do Odoo

        Args:
            numero_pedido: Número do pedido (ex: VSC01234)

        Returns:
            dict: Resultado da importação
        """
        with self.app.app_context():
            logger.info("=" * 80)
            logger.info(f"🔍 IMPORTANDO PEDIDO ESPECÍFICO: {numero_pedido}")
            logger.info("=" * 80)

            try:
                # 1. Verificar se pedido já existe
                existe = CarteiraPrincipal.query.filter_by(num_pedido=numero_pedido).first()
                if existe:
                    logger.warning(f"⚠️ Pedido {numero_pedido} já existe na carteira!")
                    logger.info("ℹ️ O script irá atualizar os dados existentes...")

                # 2. Buscar pedido no Odoo
                logger.info(f"📡 Buscando pedido {numero_pedido} no Odoo...")
                resultado = self.carteira_service.obter_carteira_pendente(
                    pedidos_especificos=[numero_pedido]
                )

                if not resultado['sucesso']:
                    return {
                        'sucesso': False,
                        'erro': resultado.get('erro', 'Erro ao buscar pedido no Odoo'),
                        'pedido': numero_pedido
                    }

                if not resultado['dados']:
                    return {
                        'sucesso': False,
                        'erro': f'Pedido {numero_pedido} não encontrado no Odoo',
                        'pedido': numero_pedido,
                        'mensagem': 'Verifique se o número está correto e se o pedido está ativo no Odoo'
                    }

                total_linhas = len(resultado['dados'])
                logger.info(f"✅ Pedido encontrado! Total de linhas: {total_linhas}")

                # 3. Sincronizar com o sistema
                logger.info(f"🔄 Sincronizando {total_linhas} linhas do pedido...")
                resultado_sync = self.carteira_service.sincronizar_carteira_odoo_com_gestao_quantidades(
                    dados_novos=resultado['dados'],
                    usuario='Script Importação Manual'
                )

                # 4. Preparar resultado
                return {
                    'sucesso': True,
                    'pedido': numero_pedido,
                    'total_linhas': total_linhas,
                    'novos': resultado_sync.get('novos', 0),
                    'atualizados': resultado_sync.get('atualizados', 0),
                    'cancelados': resultado_sync.get('cancelados', 0),
                    'mensagem': f'Pedido {numero_pedido} importado com sucesso!'
                }

            except Exception as e:
                logger.error(f"❌ Erro ao importar pedido: {str(e)}", exc_info=True)
                db.session.rollback()
                return {
                    'sucesso': False,
                    'erro': str(e),
                    'pedido': numero_pedido
                }

    def importar_nf(self, numero_nf: str) -> dict:
        """
        Importa uma NF específica do Odoo

        Args:
            numero_nf: Número da nota fiscal

        Returns:
            dict: Resultado da importação
        """
        with self.app.app_context():
            logger.info("=" * 80)
            logger.info(f"🔍 IMPORTANDO NOTA FISCAL ESPECÍFICA: {numero_nf}")
            logger.info("=" * 80)

            try:
                # 1. Verificar se NF já existe
                existe = RelatorioFaturamentoImportado.query.filter_by(
                    numero_nf=numero_nf,
                    ativo=True
                ).first()

                if existe:
                    logger.warning(f"⚠️ NF {numero_nf} já existe no sistema!")
                    logger.info("ℹ️ O script irá atualizar os dados existentes...")

                # 2. Buscar NF no Odoo
                logger.info(f"📡 Buscando NF {numero_nf} no Odoo...")

                # Buscar faturamento incremental para essa NF específica
                # O método obter_faturamento_otimizado não tem filtro por NF específica
                # então vamos buscar em modo incremental e filtrar depois
                resultado = self.faturamento_service.sincronizar_faturamento_incremental(
                    primeira_execucao=False,
                    minutos_status=43200  # 30 dias para garantir que pegue a NF
                )

                if not resultado.get('sucesso', False):
                    return {
                        'sucesso': False,
                        'erro': resultado.get('erro', 'Erro ao buscar NF no Odoo'),
                        'nf': numero_nf
                    }

                # 3. Verificar se NF foi importada
                nf_importada = RelatorioFaturamentoImportado.query.filter_by(
                    numero_nf=numero_nf,
                    ativo=True
                ).first()

                if not nf_importada:
                    return {
                        'sucesso': False,
                        'erro': f'NF {numero_nf} não encontrada no Odoo ou não foi importada',
                        'nf': numero_nf,
                        'mensagem': 'Verifique se o número está correto e se a NF está ativa no Odoo'
                    }

                logger.info(f"✅ NF {numero_nf} importada com sucesso!")

                # 4. Processar NF com ProcessadorFaturamento
                logger.info(f"🔄 Processando NF {numero_nf} (criando movimentações de estoque)...")
                resultado_proc = self.processador_faturamento.processar_nfs_importadas(
                    usuario='Script Importação Manual',
                    limpar_inconsistencias=False,
                    nfs_especificas=[numero_nf]
                )

                # 5. Preparar resultado
                return {
                    'sucesso': True,
                    'nf': numero_nf,
                    'processadas': resultado_proc.get('processadas', 0),
                    'movimentacoes_criadas': resultado_proc.get('movimentacoes_criadas', 0),
                    'embarque_items_atualizados': resultado_proc.get('embarque_items_atualizados', 0),
                    'erros': resultado_proc.get('erros', []),
                    'mensagem': f'NF {numero_nf} importada e processada com sucesso!'
                }

            except Exception as e:
                logger.error(f"❌ Erro ao importar NF: {str(e)}", exc_info=True)
                db.session.rollback()
                return {
                    'sucesso': False,
                    'erro': str(e),
                    'nf': numero_nf
                }

    def exibir_resultado(self, resultado: dict, tipo: str):
        """Exibe resultado formatado da importação"""
        print("\n" + "=" * 80)

        if resultado['sucesso']:
            print(f"✅ {tipo.upper()} IMPORTADO(A) COM SUCESSO!")
            print("=" * 80)

            if tipo == 'pedido':
                print(f"📋 Pedido: {resultado['pedido']}")
                print(f"📊 Total de linhas: {resultado['total_linhas']}")
                print(f"🆕 Novos: {resultado['novos']}")
                print(f"🔄 Atualizados: {resultado['atualizados']}")
                print(f"❌ Cancelados: {resultado['cancelados']}")
            else:  # NF
                print(f"📄 NF: {resultado['nf']}")
                print(f"✅ Processadas: {resultado['processadas']}")
                print(f"📦 Movimentações criadas: {resultado['movimentacoes_criadas']}")
                print(f"🚚 EmbarqueItems atualizados: {resultado['embarque_items_atualizados']}")

                if resultado.get('erros'):
                    print(f"\n⚠️ Erros encontrados: {len(resultado['erros'])}")
                    for erro in resultado['erros'][:5]:  # Mostrar apenas 5 primeiros
                        print(f"   - {erro}")

            print("\n" + resultado['mensagem'])
        else:
            print(f"❌ ERRO AO IMPORTAR {tipo.upper()}")
            print("=" * 80)

            if tipo == 'pedido':
                print(f"📋 Pedido: {resultado['pedido']}")
            else:
                print(f"📄 NF: {resultado['nf']}")

            print(f"\n❌ Erro: {resultado['erro']}")

            if resultado.get('mensagem'):
                print(f"\nℹ️ {resultado['mensagem']}")

        print("=" * 80 + "\n")


def main():
    """Função principal do script"""
    parser = argparse.ArgumentParser(
        description='Importa pedido ou NF específica do Odoo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Importar pedido
  python scripts/importar_pedido_nf_especifico.py --pedido VSC01234

  # Importar NF
  python scripts/importar_pedido_nf_especifico.py --nf 12345

  # Modo verboso (mais detalhes)
  python scripts/importar_pedido_nf_especifico.py --pedido VSC01234 --verbose

  # Importar múltiplos pedidos
  python scripts/importar_pedido_nf_especifico.py --pedido VSC01234 VSC01235 VSC01236
        """
    )

    parser.add_argument(
        '--pedido',
        nargs='+',
        help='Número(s) do(s) pedido(s) a importar (ex: VSC01234)'
    )

    parser.add_argument(
        '--nf',
        nargs='+',
        help='Número(s) da(s) NF(s) a importar (ex: 12345)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Modo verboso (exibe mais detalhes)'
    )

    args = parser.parse_args()

    # Validar argumentos
    if not args.pedido and not args.nf:
        parser.error("É necessário especificar --pedido ou --nf")

    if args.pedido and args.nf:
        parser.error("Especifique apenas --pedido OU --nf, não ambos")

    # Executar importação
    importador = ImportadorPedidoNFEspecifico(verbose=args.verbose)

    if args.pedido:
        for numero_pedido in args.pedido:
            resultado = importador.importar_pedido(numero_pedido)
            importador.exibir_resultado(resultado, 'pedido')

    if args.nf:
        for numero_nf in args.nf:
            resultado = importador.importar_nf(numero_nf)
            importador.exibir_resultado(resultado, 'nf')


if __name__ == '__main__':
    main()
