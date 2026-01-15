"""
Script para importar histórico de pedidos do Odoo para HistoricoPedidos
=========================================================================

Importa pedidos confirmados (não cancelados) do Odoo para a tabela
HistoricoPedidos, seguindo a mesma lógica do carteira_service.py

Autor: Sistema de Fretes
Data: 2025-10-27
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.manufatura.models import HistoricoPedidos, GrupoEmpresarial
from app.odoo.utils.connection import get_odoo_connection
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def identificar_grupo_por_cnpj(cnpj):
    """
    Identifica grupo empresarial pelo prefixo do CNPJ (8 primeiros dígitos)
    Retorna 'GERAL' se não pertencer a nenhum grupo
    """
    if not cnpj:
        return 'GERAL'

    # Remove caracteres não numéricos
    cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj)))

    # Pega os 8 primeiros dígitos (prefixo)
    if len(cnpj_limpo) < 8:
        return 'GERAL'

    prefixo_cnpj = cnpj_limpo[:8]

    # Busca diretamente pelo prefixo
    grupo = GrupoEmpresarial.query.filter_by(
        prefixo_cnpj=prefixo_cnpj,
        ativo=True
    ).first()

    if grupo:
        return grupo.nome_grupo

    return 'GERAL'


def importar_historico_odoo(data_inicio=None, data_fim='2025-06-30', lote=500):
    """
    Importa pedidos do Odoo para HistoricoPedidos

    Args:
        data_inicio: Data inicial (None = sem limite)
        data_fim: Data final (padrão: 30/06/2025)
        lote: Tamanho do lote para processamento (padrão: 500)
    """
    try:
        logger.info("="*70)
        logger.info("🚀 INICIANDO IMPORTAÇÃO DE HISTÓRICO DO ODOO")
        logger.info("="*70)

        # Conecta ao Odoo
        connection = get_odoo_connection()
        if not connection.authenticate():
            logger.error("❌ Falha na autenticação com Odoo")
            return False

        logger.info("✅ Conectado ao Odoo com sucesso")

        # Monta filtro de data
        domain = [
            ('state', 'in', ['sale', 'done']),  # Apenas pedidos confirmados (NÃO CANCELADOS)
            ('date_order', '<=', data_fim)  # Até data final
        ]

        if data_inicio:
            domain.append(('date_order', '>=', data_inicio))

        logger.info(f"📅 Período: {data_inicio or 'início'} até {data_fim}")
        logger.info(f"🔎 Buscando pedidos confirmados (state in ['sale', 'done'])...")

        # Busca pedidos
        pedidos = connection.search_read(
            model='sale.order',
            domain=domain,
            fields=['id', 'name', 'partner_id', 'date_order', 'order_line']
        )

        logger.info(f"✅ Encontrados {len(pedidos)} pedidos")

        if not pedidos:
            logger.warning("⚠️ Nenhum pedido encontrado para importar")
            return True

        # Processa pedidos em lotes
        total_inseridos = 0
        total_atualizados = 0
        total_erros = 0

        for idx, pedido in enumerate(pedidos, 1):
            try:
                num_pedido = pedido.get('name')
                partner_id = pedido.get('partner_id', [None])[0] if pedido.get('partner_id') else None
                data_pedido_str = pedido.get('date_order')
                order_line_ids = pedido.get('order_line', [])

                if not order_line_ids:
                    logger.debug(f"   Pedido {num_pedido} sem linhas, pulando...")
                    continue

                # Converte data
                data_pedido = datetime.strptime(data_pedido_str, '%Y-%m-%d %H:%M:%S').date()

                # Busca dados do cliente
                cliente = connection.read(
                    model='res.partner',
                    ids=[partner_id],
                    fields=['name', 'l10n_br_cnpj', 'l10n_br_razao_social', 'l10n_br_municipio_id', 'state_id']
                )

                if not cliente:
                    logger.debug(f"   Cliente não encontrado para pedido {num_pedido}")
                    continue

                cliente_dados = cliente[0]
                cnpj_cliente = cliente_dados.get('l10n_br_cnpj', '').replace('.', '').replace('/', '').replace('-', '')
                raz_social = cliente_dados.get('l10n_br_razao_social') or cliente_dados.get('name', '')

                # Extrair município e UF
                municipio_nome = ''
                estado_uf = ''
                if cliente_dados.get('l10n_br_municipio_id'):
                    municipio_info = cliente_dados['l10n_br_municipio_id']
                    if isinstance(municipio_info, list) and len(municipio_info) > 1:
                        municipio_completo = municipio_info[1]
                        if '(' in municipio_completo and ')' in municipio_completo:
                            partes = municipio_completo.split('(')
                            municipio_nome = partes[0].strip()
                            uf_com_parenteses = partes[1]
                            estado_uf = uf_com_parenteses.replace(')', '').strip()[:2]

                # Identifica grupo empresarial
                nome_grupo = identificar_grupo_por_cnpj(cnpj_cliente)

                # Busca linhas do pedido
                linhas = connection.read(
                    model='sale.order.line',
                    ids=order_line_ids,
                    fields=[
                        'product_id', 'product_uom_qty', 'price_unit', 'name'
                    ]
                )

                # Coleta todos os product_ids para buscar em lote
                product_ids = []
                for linha in linhas:
                    product_id = linha.get('product_id', [None])[0] if linha.get('product_id') else None
                    if product_id:
                        product_ids.append(product_id)

                if not product_ids:
                    continue

                # Busca todos os produtos em uma única query
                produtos = connection.read(
                    model='product.product',
                    ids=product_ids,
                    fields=['id', 'default_code']
                )

                # Cria cache de produtos
                cache_produtos = {p['id']: p.get('default_code') for p in produtos}

                # Processa cada linha do pedido
                for linha in linhas:
                    product_id = linha.get('product_id', [None])[0] if linha.get('product_id') else None

                    if not product_id:
                        continue

                    cod_produto = cache_produtos.get(product_id)
                    nome_produto = linha.get('name')
                    qtd_produto = float(linha.get('product_uom_qty', 0))
                    preco_produto = float(linha.get('price_unit', 0))
                    valor_produto = qtd_produto * preco_produto

                    if not cod_produto or qtd_produto <= 0:
                        continue

                    # Verifica se já existe
                    historico_existe = HistoricoPedidos.query.filter_by(
                        num_pedido=num_pedido,
                        cod_produto=cod_produto
                    ).first()

                    if historico_existe:
                        # Atualiza existente
                        historico_existe.data_pedido = data_pedido
                        historico_existe.cnpj_cliente = cnpj_cliente
                        historico_existe.raz_social_red = raz_social[:255]
                        historico_existe.nome_grupo = nome_grupo
                        historico_existe.nome_cidade = municipio_nome[:100]
                        historico_existe.cod_uf = estado_uf
                        historico_existe.nome_produto = nome_produto[:255] if nome_produto else None
                        historico_existe.qtd_produto_pedido = qtd_produto
                        historico_existe.preco_produto_pedido = preco_produto
                        historico_existe.valor_produto_pedido = valor_produto
                        total_atualizados += 1
                    else:
                        # Insere novo
                        historico = HistoricoPedidos(
                            num_pedido=num_pedido,
                            data_pedido=data_pedido,
                            cnpj_cliente=cnpj_cliente,
                            raz_social_red=raz_social[:255],
                            nome_grupo=nome_grupo,
                            nome_cidade=municipio_nome[:100],
                            cod_uf=estado_uf,
                            cod_produto=cod_produto,
                            nome_produto=nome_produto[:255] if nome_produto else None,
                            qtd_produto_pedido=qtd_produto,
                            preco_produto_pedido=preco_produto,
                            valor_produto_pedido=valor_produto
                        )
                        db.session.add(historico)
                        total_inseridos += 1

                # Commit a cada lote
                if idx % lote == 0:
                    db.session.commit()
                    logger.info(f"   💾 Processados {idx}/{len(pedidos)} pedidos (Inseridos: {total_inseridos}, Atualizados: {total_atualizados})")

            except Exception as e:
                logger.error(f"   ❌ Erro ao processar pedido {pedido.get('name')}: {e}")
                total_erros += 1
                db.session.rollback()
                continue

        # Commit final
        db.session.commit()

        logger.info("="*70)
        logger.info("✅ IMPORTAÇÃO CONCLUÍDA!")
        logger.info(f"   📊 Total de pedidos processados: {len(pedidos)}")
        logger.info(f"   ➕ Registros inseridos: {total_inseridos}")
        logger.info(f"   🔄 Registros atualizados: {total_atualizados}")
        logger.info(f"   ❌ Erros: {total_erros}")
        logger.info("="*70)

        return True

    except Exception as e:
        logger.error(f"❌ Erro na importação: {e}", exc_info=True)
        db.session.rollback()
        return False


if __name__ == '__main__':
    app = create_app()

    with app.app_context():
        # TESTE: Importa apenas pedidos de junho/2025 para validar
        sucesso = importar_historico_odoo(
            data_inicio='2025-06-01',  # Apenas junho/2025 para teste
            data_fim='2025-06-30',  # Até 30/06/2025
            lote=50  # Commit a cada 50 pedidos
        )

        if sucesso:
            logger.info("\n✅ Script executado com sucesso!")
            logger.info("💡 Para importar todo histórico, altere data_inicio=None")
        else:
            logger.error("\n❌ Falha na execução do script")
            sys.exit(1)
