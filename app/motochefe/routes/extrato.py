"""
Rotas de Extrato Financeiro - MotoChefe
Movimentações consolidadas (recebimentos e pagamentos)
"""
from flask import render_template, request, send_file
from flask_login import login_required
from datetime import datetime, date, timedelta
from decimal import Decimal
from io import BytesIO
import pandas as pd

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models import ClienteMoto, VendedorMoto, TransportadoraMoto
from app.motochefe.services.extrato_financeiro_service import (
    obter_movimentacoes_financeiras,
    calcular_saldo_acumulado
)


@motochefe_bp.route('/extrato-financeiro')
@login_required
@requer_motochefe
def extrato_financeiro():
    """
    Extrato consolidado de movimentações financeiras
    Mostra TODOS os recebimentos e pagamentos realizados
    """
    # Filtros
    data_inicial = request.args.get('data_inicial')
    data_final = request.args.get('data_final')
    tipo_movimentacao = request.args.get('tipo')  # 'RECEBIMENTO' ou 'PAGAMENTO'
    cliente_id = request.args.get('cliente_id', type=int)
    fornecedor = request.args.get('fornecedor')
    vendedor_id = request.args.get('vendedor_id', type=int)
    transportadora_id = request.args.get('transportadora_id', type=int)

    # Paginação
    page = request.args.get('page', 1, type=int)
    per_page = 100

    # Valores padrão para datas (últimos 30 dias)
    if not data_inicial:
        data_inicial = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not data_final:
        # ✅ CORREÇÃO: Usar dia seguinte para incluir registros de hoje com timezone UTC
        data_final = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')

    # Buscar movimentações
    movimentacoes = obter_movimentacoes_financeiras(
        data_inicial=data_inicial,
        data_final=data_final,
        cliente_id=cliente_id,
        fornecedor=fornecedor,
        vendedor_id=vendedor_id,
        transportadora_id=transportadora_id,
        tipo_movimentacao=tipo_movimentacao
    )

    # Calcular saldo acumulado
    movimentacoes = calcular_saldo_acumulado(movimentacoes)

    # Paginação manual
    total = len(movimentacoes)
    inicio = (page - 1) * per_page
    fim = inicio + per_page
    movimentacoes_paginadas = movimentacoes[inicio:fim]

    # Totais (IMPORTANTE: inicializar com Decimal para preservar casas decimais)
    total_recebimentos = sum(
        (m['valor'] for m in movimentacoes if m['tipo'] == 'RECEBIMENTO'),
        Decimal('0')
    )
    total_pagamentos = abs(sum(
        (m['valor'] for m in movimentacoes if m['tipo'] == 'PAGAMENTO'),
        Decimal('0')
    ))
    saldo_periodo = total_recebimentos - total_pagamentos

    # Entidades para filtros
    clientes = ClienteMoto.query.filter_by(ativo=True).order_by(ClienteMoto.cliente).all()
    vendedores = VendedorMoto.query.filter_by(ativo=True).order_by(VendedorMoto.vendedor).all()
    transportadoras = TransportadoraMoto.query.filter_by(ativo=True).order_by(TransportadoraMoto.transportadora).all()

    return render_template('motochefe/financeiro/extrato.html',
                         movimentacoes=movimentacoes_paginadas,
                         total=total,
                         page=page,
                         per_page=per_page,
                         total_pages=(total + per_page - 1) // per_page,
                         data_inicial=data_inicial,
                         data_final=data_final,
                         tipo_movimentacao=tipo_movimentacao,
                         cliente_id=cliente_id,
                         fornecedor=fornecedor,
                         vendedor_id=vendedor_id,
                         transportadora_id=transportadora_id,
                         total_recebimentos=total_recebimentos,
                         total_pagamentos=total_pagamentos,
                         saldo_periodo=saldo_periodo,
                         clientes=clientes,
                         vendedores=vendedores,
                         transportadoras=transportadoras)


@motochefe_bp.route('/extrato-financeiro/exportar')
@login_required
@requer_motochefe
def exportar_extrato():
    """Exporta extrato financeiro para Excel com dados detalhados"""
    # Mesmos filtros da listagem
    data_inicial = request.args.get('data_inicial')
    data_final = request.args.get('data_final')
    tipo_movimentacao = request.args.get('tipo')
    cliente_id = request.args.get('cliente_id', type=int)
    fornecedor = request.args.get('fornecedor')
    vendedor_id = request.args.get('vendedor_id', type=int)
    transportadora_id = request.args.get('transportadora_id', type=int)

    # Buscar movimentações
    movimentacoes = obter_movimentacoes_financeiras(
        data_inicial=data_inicial,
        data_final=data_final,
        cliente_id=cliente_id,
        fornecedor=fornecedor,
        vendedor_id=vendedor_id,
        transportadora_id=transportadora_id,
        tipo_movimentacao=tipo_movimentacao
    )

    # Calcular saldo acumulado
    movimentacoes = calcular_saldo_acumulado(movimentacoes)

    # Preparar dados para Excel (Opção B - Detalhado)
    dados_excel = []
    for mov in movimentacoes:
        dados_excel.append({
            'Data': mov['data_movimentacao'].strftime('%d/%m/%Y') if mov['data_movimentacao'] else '',
            'Tipo': mov['tipo'],
            'Categoria': mov['categoria'],
            'Descrição': mov['descricao'],
            'Cliente/Fornecedor': mov['cliente_fornecedor'],
            'Valor': float(abs(mov['valor'])),
            'Saldo Acumulado': float(mov['saldo_acumulado']),
            'Pedido': mov['numero_pedido'] or '',
            'NF': mov['numero_nf'] or '',
            'Chassi': mov['numero_chassi'] or '',
            'Embarque': mov['numero_embarque'] or '',
        })

    # Criar DataFrame
    df = pd.DataFrame(dados_excel)

    # Criar Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Extrato Financeiro', index=False)

        # Formatar
        workbook = writer.book
        worksheet = writer.sheets['Extrato Financeiro']

        # Formato de moeda
        money_fmt = workbook.add_format({'num_format': 'R$ #,##0.00'})
        worksheet.set_column('F:G', 15, money_fmt)

        # Larguras das colunas
        worksheet.set_column('A:A', 12)  # Data
        worksheet.set_column('B:C', 15)  # Tipo, Categoria
        worksheet.set_column('D:D', 50)  # Descrição
        worksheet.set_column('E:E', 30)  # Cliente/Fornecedor

    output.seek(0)

    filename = f'extrato_financeiro_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
