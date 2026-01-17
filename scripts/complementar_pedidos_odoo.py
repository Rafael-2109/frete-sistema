"""
Script para complementar pedidos no Odoo com itens faltantes

Uso:
    source .venv/bin/activate
    python scripts/complementar_pedidos_odoo.py diagnostico
    python scripts/complementar_pedidos_odoo.py executar --dry-run
    python scripts/complementar_pedidos_odoo.py executar

Cenários tratados:
1. Filial já inserida + item faltante → Adiciona linha ao pedido existente
2. Filial não inserida → Cria novo pedido completo
3. Item já existe no pedido → Pula (não duplica)
"""

import sys
import os
import argparse
from typing import Dict, List, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db # noqa: E402
from app.pedidos.integracao_odoo.models import RegistroPedidoOdoo, PedidoImportacaoTemp # noqa: E402
from app.pedidos.integracao_odoo.service import get_odoo_service # noqa: E402


def diagnostico_pedido(importacao_id: int) -> Dict[str, Any]:
    """
    Analisa uma importação e identifica o que está faltando

    Args:
        importacao_id: ID do PedidoImportacaoTemp

    Returns:
        Dict com diagnóstico completo
    """
    app = create_app()
    with app.app_context():
        # Busca registro de importação
        importacao = db.session.get(PedidoImportacaoTemp,importacao_id) if importacao_id else None
        if not importacao:
            return {'erro': f'Importação {importacao_id} não encontrada'}

        resultado = {
            'importacao_id': importacao_id,
            'rede': importacao.rede,
            'numero_documento': importacao.numero_documento,
            'total_filiais_pdf': len(importacao.dados_filiais) if importacao.dados_filiais else 0,
            'filiais_inseridas': [],
            'filiais_faltantes': [],
            'itens_faltantes_por_filial': {}
        }

        if not importacao.dados_filiais:
            return {'erro': 'Sem dados de filiais no registro'}

        # Para cada filial no PDF
        for filial in importacao.dados_filiais:
            cnpj = filial.get('cnpj')

            # Verifica se foi inserida no Odoo
            registro = db.session.query(RegistroPedidoOdoo).filter_by(
                rede=importacao.rede,
                numero_documento=importacao.numero_documento,
                cnpj_cliente=cnpj,
                status_odoo='SUCESSO'
            ).first()

            if registro:
                resultado['filiais_inseridas'].append({
                    'cnpj': cnpj,
                    'nome': filial.get('nome_cliente'),
                    'odoo_order_id': registro.odoo_order_id,
                    'odoo_order_name': registro.odoo_order_name,
                    'itens_inseridos': len(registro.dados_documento) if registro.dados_documento else 0,
                    'itens_pdf': len(filial.get('itens', []))
                })

                # Verifica itens faltantes
                itens_inseridos = set()
                if registro.dados_documento:
                    for item in registro.dados_documento:
                        cod = item.get('nosso_codigo') or item.get('codigo_rede')
                        if cod:
                            itens_inseridos.add(str(cod))

                itens_faltantes = []
                for item in filial.get('itens', []):
                    cod = item.get('nosso_codigo') or item.get('codigo_rede')
                    if cod and str(cod) not in itens_inseridos:
                        itens_faltantes.append({
                            'codigo': cod,
                            'descricao': item.get('descricao') or item.get('nossa_descricao'),
                            'quantidade': item.get('quantidade'),
                            'preco': item.get('preco_final') or item.get('preco_documento')
                        })

                if itens_faltantes:
                    resultado['itens_faltantes_por_filial'][cnpj] = {
                        'odoo_order_id': registro.odoo_order_id,
                        'odoo_order_name': registro.odoo_order_name,
                        'itens': itens_faltantes
                    }
            else:
                resultado['filiais_faltantes'].append({
                    'cnpj': cnpj,
                    'nome': filial.get('nome_cliente'),
                    'itens': len(filial.get('itens', []))
                })

        return resultado


def complementar_pedido_existente(order_id: int, itens: List[Dict], dry_run: bool = True) -> Dict:
    """
    Adiciona itens a um pedido existente no Odoo

    Args:
        order_id: ID do sale.order no Odoo
        itens: Lista de itens a adicionar
        dry_run: Se True, apenas simula

    Returns:
        Dict com resultado
    """
    service = get_odoo_service()

    # Prepara linhas
    order_lines = []
    erros = []

    for item in itens:
        cod_produto = item.get('nosso_codigo') or item.get('codigo')
        if not cod_produto:
            erros.append(f"Item sem código: {item}")
            continue

        product_id = service.buscar_produto_por_codigo(cod_produto)
        if not product_id:
            erros.append(f"Produto não encontrado no Odoo: {cod_produto}")
            continue

        quantidade = float(item.get('quantidade', 0))
        preco = float(item.get('preco') or item.get('preco_final', 0))

        if quantidade <= 0 or preco <= 0:
            erros.append(f"Quantidade/preço inválido para {cod_produto}")
            continue

        line_data = {
            'product_id': product_id,
            'product_uom_qty': quantidade,
            'price_unit': preco,
            'l10n_br_compra_indcom': 'com',
        }
        order_lines.append((0, 0, line_data))

    if not order_lines:
        return {
            'sucesso': False,
            'mensagem': 'Nenhum item válido para adicionar',
            'erros': erros
        }

    if dry_run:
        return {
            'sucesso': True,
            'mensagem': f'[DRY-RUN] Adicionaria {len(order_lines)} itens ao pedido {order_id}',
            'itens': [line[2]['product_id'] for line in order_lines],
            'erros': erros
        }

    # Executa adição de linhas
    try:
        service._execute('sale.order', 'write', [order_id], {
            'order_line': order_lines
        })
        return {
            'sucesso': True,
            'mensagem': f'Adicionados {len(order_lines)} itens ao pedido {order_id}',
            'erros': erros
        }
    except Exception as e:
        return {
            'sucesso': False,
            'mensagem': f'Erro ao adicionar itens: {e}',
            'erros': erros
        }


def criar_pedido_faltante(
    cnpj: str,
    itens: List[Dict],
    rede: str,
    numero_documento: str,
    numero_pedido_cliente: str,
    usuario: str,
    dry_run: bool = True
) -> Dict:
    """
    Cria pedido para filial que não foi inserida

    Args:
        cnpj: CNPJ da filial
        itens: Lista de itens
        rede: Nome da rede
        numero_documento: Número do documento
        numero_pedido_cliente: Número do pedido do cliente
        usuario: Usuário
        dry_run: Se True, apenas simula

    Returns:
        Dict com resultado
    """
    if dry_run:
        return {
            'sucesso': True,
            'mensagem': f'[DRY-RUN] Criaria pedido para {cnpj} com {len(itens)} itens',
            'itens': len(itens)
        }

    service = get_odoo_service()

    # Prepara itens no formato esperado
    itens_formatados = []
    for item in itens:
        itens_formatados.append({
            'nosso_codigo': item.get('nosso_codigo') or item.get('codigo_rede'),
            'quantidade': item.get('quantidade'),
            'preco': item.get('preco_final') or item.get('preco_documento'),
        })

    resultado, registro = service.criar_pedido_e_registrar(
        cnpj_cliente=cnpj,
        itens=itens_formatados,
        rede=rede,
        tipo_documento='PEDIDO',
        numero_documento=numero_documento,
        arquivo_pdf_s3=None,
        usuario=usuario,
        numero_pedido_cliente=numero_pedido_cliente,
        payment_provider_id=30  # Transferência Bancária CD
    )

    return {
        'sucesso': resultado.sucesso,
        'mensagem': resultado.mensagem,
        'order_id': resultado.order_id,
        'order_name': resultado.order_name,
        'erros': resultado.erros
    }


def executar_complementacao(importacao_id: int, dry_run: bool = True, usuario: str = 'sistema'):
    """
    Executa complementação de pedidos

    Args:
        importacao_id: ID da importação
        dry_run: Se True, apenas simula
        usuario: Usuário para auditoria
    """
    app = create_app()
    with app.app_context():
        print(f"\n{'='*60}")
        print(f"COMPLEMENTAÇÃO DE PEDIDOS - {'SIMULAÇÃO' if dry_run else 'EXECUÇÃO'}")
        print(f"{'='*60}\n")

        # Diagnóstico
        diag = diagnostico_pedido(importacao_id)

        if 'erro' in diag:
            print(f"❌ Erro: {diag['erro']}")
            return

        print(f"📄 Documento: {diag['rede']} / {diag['numero_documento']}")
        print(f"📊 Total filiais no PDF: {diag['total_filiais_pdf']}")
        print(f"✅ Filiais já inseridas: {len(diag['filiais_inseridas'])}")
        print(f"❌ Filiais faltantes: {len(diag['filiais_faltantes'])}")
        print(f"⚠️  Filiais com itens faltantes: {len(diag['itens_faltantes_por_filial'])}")

        # Busca dados da importação para pegar numero_pedido_cliente
        importacao = db.session.get(PedidoImportacaoTemp,importacao_id) if importacao_id else None

        # 1. Complementar pedidos existentes com itens faltantes
        if diag['itens_faltantes_por_filial']:
            print(f"\n{'─'*40}")
            print("ETAPA 1: COMPLEMENTAR PEDIDOS EXISTENTES")
            print(f"{'─'*40}")

            for cnpj, info in diag['itens_faltantes_por_filial'].items():
                print(f"\n📦 Pedido {info['odoo_order_name']} (ID: {info['odoo_order_id']})")
                print(f"   CNPJ: {cnpj}")
                print(f"   Itens faltantes: {len(info['itens'])}")

                for item in info['itens']:
                    print(f"      - {item['codigo']}: {item['descricao']} (Qtd: {item['quantidade']}, R$ {item['preco']})")

                resultado = complementar_pedido_existente(
                    order_id=info['odoo_order_id'],
                    itens=info['itens'],
                    dry_run=dry_run
                )

                status = "✅" if resultado['sucesso'] else "❌"
                print(f"   {status} {resultado['mensagem']}")
                if resultado.get('erros'):
                    for erro in resultado['erros']:
                        print(f"      ⚠️ {erro}")

        # 2. Criar pedidos para filiais faltantes
        if diag['filiais_faltantes']:
            print(f"\n{'─'*40}")
            print("ETAPA 2: CRIAR PEDIDOS PARA FILIAIS FALTANTES")
            print(f"{'─'*40}")

            for filial_info in diag['filiais_faltantes']:
                cnpj = filial_info['cnpj']
                print(f"\n📦 Nova filial: {filial_info['nome']}")
                print(f"   CNPJ: {cnpj}")
                print(f"   Itens: {filial_info['itens']}")

                # Busca dados completos da filial
                filial_data = None
                for f in importacao.dados_filiais:
                    if f.get('cnpj') == cnpj:
                        filial_data = f
                        break

                if not filial_data:
                    print(f"   ❌ Dados da filial não encontrados")
                    continue

                resultado = criar_pedido_faltante(
                    cnpj=cnpj,
                    itens=filial_data.get('itens', []),
                    rede=importacao.rede,
                    numero_documento=importacao.numero_documento,
                    numero_pedido_cliente=filial_data.get('numero_pedido_cliente'),
                    usuario=usuario,
                    dry_run=dry_run
                )

                status = "✅" if resultado['sucesso'] else "❌"
                print(f"   {status} {resultado['mensagem']}")
                if resultado.get('order_name'):
                    print(f"   📋 Pedido criado: {resultado['order_name']}")
                if resultado.get('erros'):
                    for erro in resultado['erros']:
                        print(f"      ⚠️ {erro}")

        print(f"\n{'='*60}")
        if dry_run:
            print("⚠️  SIMULAÇÃO CONCLUÍDA - Nenhuma alteração foi feita")
            print("   Para executar de verdade, use: --execute")
        else:
            print("✅ EXECUÇÃO CONCLUÍDA")
        print(f"{'='*60}\n")


def listar_importacoes():
    """Lista importações recentes"""
    app = create_app()
    with app.app_context():
        importacoes = db.session.query(PedidoImportacaoTemp).filter(
            PedidoImportacaoTemp.status.in_(['LANCADO', 'ERRO'])
        ).order_by(PedidoImportacaoTemp.criado_em.desc()).limit(10).all()

        print("\n📋 IMPORTAÇÕES RECENTES:")
        print("-" * 80)
        print(f"{'ID':<5} {'Rede':<12} {'Documento':<15} {'Status':<10} {'Filiais':<8} {'Data'}")
        print("-" * 80)

        for imp in importacoes:
            num_filiais = len(imp.dados_filiais) if imp.dados_filiais else 0
            print(f"{imp.id:<5} {imp.rede:<12} {imp.numero_documento or '-':<15} {imp.status:<10} {num_filiais:<8} {imp.criado_em.strftime('%d/%m %H:%M')}")

        print("-" * 80)
        print("\nUse: python scripts/complementar_pedidos_odoo.py diagnostico <ID>")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Complementar pedidos no Odoo')
    parser.add_argument('comando', choices=['listar', 'diagnostico', 'executar'],
                        help='Comando a executar')
    parser.add_argument('importacao_id', type=int, nargs='?',
                        help='ID da importação')
    parser.add_argument('--execute', action='store_true',
                        help='Executar de verdade (sem dry-run)')
    parser.add_argument('--usuario', default='sistema',
                        help='Usuário para auditoria')

    args = parser.parse_args()

    if args.comando == 'listar':
        listar_importacoes()

    elif args.comando == 'diagnostico':
        if not args.importacao_id:
            print("❌ Informe o ID da importação")
            listar_importacoes()
            sys.exit(1)

        app = create_app()
        with app.app_context():
            resultado = diagnostico_pedido(args.importacao_id)
            import json
            print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))

    elif args.comando == 'executar':
        if not args.importacao_id:
            print("❌ Informe o ID da importação")
            listar_importacoes()
            sys.exit(1)

        executar_complementacao(
            importacao_id=args.importacao_id,
            dry_run=not args.execute,
            usuario=args.usuario
        )
