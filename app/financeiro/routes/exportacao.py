"""
Rotas de Exportação de Relatórios Financeiros
Hub centralizado para exportação de dados do módulo financeiro.

Tipos de exportação disponíveis:
- Extrato de Recebimentos (entrada)
- Extrato de Pagamentos (saída)
- Contas a Receber (simples)
- Contas a Pagar
- Recebimento Enriquecido (mantido na rota original)
"""

from flask import render_template, request, send_file, jsonify, redirect, url_for
from flask_login import login_required
from datetime import datetime, date
from io import BytesIO
import pandas as pd
from sqlalchemy import or_, exists

from app import db
from app.financeiro.routes import financeiro_bp


# ========================================
# HUB DE EXPORTAÇÃO
# ========================================

@financeiro_bp.route('/exportar')
@login_required
def exportar_hub():
    """
    Hub Central de Exportação de Relatórios Financeiros.
    Exibe cards para cada tipo de exportação disponível.
    """
    return render_template('financeiro/exportar_hub.html')


@financeiro_bp.route('/exportar/download')
@login_required
def exportar_relatorio():
    """
    Rota unificada para exportação de relatórios em Excel.

    Query Params:
        tipo: recebimentos | pagamentos | contas-receber | contas-pagar
        data_de: Data inicial (YYYY-MM-DD)
        data_ate: Data final (YYYY-MM-DD)
        status: Status para filtro (específico de cada tipo)

    Returns:
        Arquivo Excel (.xlsx) para download
    """
    tipo = request.args.get('tipo', 'contas-receber')
    data_de = request.args.get('data_de')
    data_ate = request.args.get('data_ate')
    status = request.args.get('status')

    # Converter datas
    data_inicio = None
    data_fim = None

    if data_de:
        try:
            data_inicio = datetime.strptime(data_de, '%Y-%m-%d').date()
        except ValueError:
            pass

    if data_ate:
        try:
            data_fim = datetime.strptime(data_ate, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Direcionar para o exportador correto
    if tipo == 'recebimentos':
        return _exportar_extrato_recebimentos(data_inicio, data_fim, status)
    elif tipo == 'pagamentos':
        return _exportar_extrato_pagamentos(data_inicio, data_fim, status)
    elif tipo == 'contas-receber':
        return _exportar_contas_receber(data_inicio, data_fim, status)
    elif tipo == 'contas-pagar':
        return _exportar_contas_pagar(data_inicio, data_fim, status)
    else:
        return jsonify({'error': f'Tipo de exportação inválido: {tipo}'}), 400


# ========================================
# EXPORTADORES ESPECÍFICOS
# ========================================

def _exportar_extrato_recebimentos(data_inicio: date = None, data_fim: date = None, status: str = None):
    """
    Exporta linhas de extrato de recebimentos (entrada).

    Filtra por:
    - data_transacao (se informado)
    - status do item (se informado)
    """
    from app.financeiro.models import ExtratoItem, ExtratoLote

    # Query base: itens de lotes de entrada
    query = ExtratoItem.query.join(ExtratoLote).filter(
        ExtratoLote.tipo_transacao == 'entrada'
    )

    # Filtro de data
    if data_inicio:
        query = query.filter(ExtratoItem.data_transacao >= data_inicio)
    if data_fim:
        query = query.filter(ExtratoItem.data_transacao <= data_fim)

    # Filtro de status
    if status:
        query = query.filter(ExtratoItem.status == status)

    # Ordenar por data
    query = query.order_by(ExtratoItem.data_transacao.desc())

    # Buscar dados
    itens = query.all()

    # Montar DataFrame
    dados = []
    for item in itens:
        dados.append({
            'ID': item.id,
            'Lote': item.lote.nome if item.lote else '',
            'Data Transação': item.data_transacao.strftime('%d/%m/%Y') if item.data_transacao else '',
            'Valor': item.valor or 0,
            'Tipo Transação': item.tipo_transacao or '',
            'Nome Pagador': item.nome_pagador or '',
            'CNPJ Pagador': item.cnpj_pagador or '',
            'Payment Ref': item.payment_ref or '',
            'Journal': item.journal_code or '',
            'Status Match': item.status_match or '',
            'Status': item.status or '',
            'Título NF': item.titulo_nf or '',
            'Título Parcela': item.titulo_parcela or '',
            'Título Valor': item.titulo_valor or '',
            'Título Cliente': item.titulo_cliente or '',
            'Match Score': item.match_score or '',
            'Match Critério': item.match_criterio or '',
            'Aprovado': 'Sim' if item.aprovado else 'Não',
            'Mensagem': item.mensagem or '',
            'Criado Em': item.criado_em.strftime('%d/%m/%Y %H:%M') if item.criado_em else '',
        })

    # Criar Excel
    df = pd.DataFrame(dados)
    output = _gerar_excel(df, 'Extrato Recebimentos')

    filename = f'extrato_recebimentos_{date.today().strftime("%Y-%m-%d")}.xlsx'
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


def _exportar_extrato_pagamentos(data_inicio: date = None, data_fim: date = None, status: str = None):
    """
    Exporta linhas de extrato de pagamentos (saída).

    Filtra por:
    - data_transacao (se informado)
    - status do item (se informado)
    """
    from app.financeiro.models import ExtratoItem, ExtratoLote

    # Query base: itens de lotes de saída
    query = ExtratoItem.query.join(ExtratoLote).filter(
        ExtratoLote.tipo_transacao == 'saida'
    )

    # Filtro de data
    if data_inicio:
        query = query.filter(ExtratoItem.data_transacao >= data_inicio)
    if data_fim:
        query = query.filter(ExtratoItem.data_transacao <= data_fim)

    # Filtro de status
    if status:
        query = query.filter(ExtratoItem.status == status)

    # Ordenar por data
    query = query.order_by(ExtratoItem.data_transacao.desc())

    # Buscar dados
    itens = query.all()

    # Montar DataFrame
    dados = []
    for item in itens:
        dados.append({
            'ID': item.id,
            'Lote': item.lote.nome if item.lote else '',
            'Data Transação': item.data_transacao.strftime('%d/%m/%Y') if item.data_transacao else '',
            'Valor': abs(item.valor) if item.valor else 0,  # Valor absoluto para pagamentos
            'Tipo Transação': item.tipo_transacao or '',
            'Nome Pagador': item.nome_pagador or '',
            'CNPJ Pagador': item.cnpj_pagador or '',
            'Payment Ref': item.payment_ref or '',
            'Journal': item.journal_code or '',
            'Status Match': item.status_match or '',
            'Status': item.status or '',
            'Título NF': item.titulo_nf or '',
            'Título Parcela': item.titulo_parcela or '',
            'Título Valor': item.titulo_valor or '',
            'Título Fornecedor': item.titulo_cliente or '',  # Para pagamentos, é fornecedor
            'Match Score': item.match_score or '',
            'Match Critério': item.match_criterio or '',
            'Aprovado': 'Sim' if item.aprovado else 'Não',
            'Mensagem': item.mensagem or '',
            'Criado Em': item.criado_em.strftime('%d/%m/%Y %H:%M') if item.criado_em else '',
        })

    # Criar Excel
    df = pd.DataFrame(dados)
    output = _gerar_excel(df, 'Extrato Pagamentos')

    filename = f'extrato_pagamentos_{date.today().strftime("%Y-%m-%d")}.xlsx'
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


def _exportar_contas_receber(data_inicio: date = None, data_fim: date = None, status: str = None):
    """
    Exporta contas a receber SEM enriquecimento.
    Dados puros da tabela contas_a_receber.

    Filtra por:
    - vencimento (se informado)
    - status calculado: aberto, pago, vencido, cancelado
    """
    from app.financeiro.models import ContasAReceber
    from app.faturamento.models import FaturamentoProduto

    # Query base
    query = ContasAReceber.query

    # Filtro de data (vencimento)
    if data_inicio:
        query = query.filter(ContasAReceber.vencimento >= data_inicio)
    if data_fim:
        query = query.filter(ContasAReceber.vencimento <= data_fim)

    # Filtro de status
    if status:
        hoje = date.today()

        # Subquery para verificar NF cancelada
        nf_cancelada_subquery = exists().where(
            FaturamentoProduto.numero_nf == ContasAReceber.titulo_nf,
            FaturamentoProduto.status_nf == 'Cancelado'
        )

        if status == 'aberto':
            query = query.filter(
                ContasAReceber.parcela_paga == False,
                ~nf_cancelada_subquery,
                or_(ContasAReceber.vencimento >= hoje, ContasAReceber.vencimento.is_(None))
            )
        elif status == 'pago':
            query = query.filter(ContasAReceber.parcela_paga == True)
        elif status == 'vencido':
            query = query.filter(
                ContasAReceber.parcela_paga == False,
                ~nf_cancelada_subquery,
                ContasAReceber.vencimento < hoje
            )
        elif status == 'cancelado':
            query = query.filter(nf_cancelada_subquery)

    # Ordenar por vencimento
    query = query.order_by(ContasAReceber.vencimento.asc().nullslast())

    # Buscar dados
    contas = query.all()

    # Montar DataFrame
    dados = []
    for conta in contas:
        dados.append({
            'ID': conta.id,
            'Empresa': conta.empresa_nome,
            'NF': conta.titulo_nf,
            'Parcela': conta.parcela,
            'CNPJ': conta.cnpj,
            'Razão Social': conta.raz_social,
            'Nome Fantasia': conta.raz_social_red,
            'UF': conta.uf_cliente,
            'Emissão': conta.emissao.strftime('%d/%m/%Y') if conta.emissao else '',
            'Vencimento': conta.vencimento.strftime('%d/%m/%Y') if conta.vencimento else '',
            'Valor Original': conta.valor_original or 0,
            'Desconto %': conta.desconto_percentual or 0,
            'Desconto R$': conta.desconto or 0,
            'Valor Título': conta.valor_titulo or 0,
            'Tipo Título': conta.tipo_titulo or '',
            'Pago': 'Sim' if conta.parcela_paga else 'Não',
            'Status Odoo': conta.status_pagamento_odoo or '',
            'Lib. Antecipação': conta.liberacao_prevista_antecipacao.strftime('%d/%m/%Y') if conta.liberacao_prevista_antecipacao else '',
            'Observação': conta.observacao or '',
            'Última Sincronização': conta.ultima_sincronizacao.strftime('%d/%m/%Y %H:%M') if conta.ultima_sincronizacao else '',
        })

    # Criar Excel
    df = pd.DataFrame(dados)
    output = _gerar_excel(df, 'Contas a Receber')

    filename = f'contas_receber_{date.today().strftime("%Y-%m-%d")}.xlsx'
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


def _exportar_contas_pagar(data_inicio: date = None, data_fim: date = None, status: str = None):
    """
    Exporta contas a pagar.

    Filtra por:
    - vencimento (se informado)
    - status_sistema: PENDENTE, PROGRAMADO, PAGO, CONTESTADO
    """
    from app.financeiro.models import ContasAPagar

    # Query base
    query = ContasAPagar.query

    # Filtro de data (vencimento)
    if data_inicio:
        query = query.filter(ContasAPagar.vencimento >= data_inicio)
    if data_fim:
        query = query.filter(ContasAPagar.vencimento <= data_fim)

    # Filtro de status
    if status:
        if status == 'PAGO':
            # PAGO pode ser status_sistema OU parcela_paga do Odoo
            query = query.filter(
                or_(
                    ContasAPagar.status_sistema == 'PAGO',
                    ContasAPagar.parcela_paga == True
                )
            )
        else:
            query = query.filter(ContasAPagar.status_sistema == status)

    # Ordenar por vencimento
    query = query.order_by(ContasAPagar.vencimento.asc().nullslast())

    # Buscar dados
    contas = query.all()

    # Montar DataFrame
    dados = []
    for conta in contas:
        dados.append({
            'ID': conta.id,
            'Empresa': conta.empresa_nome,
            'NF': conta.titulo_nf,
            'Parcela': conta.parcela,
            'CNPJ': conta.cnpj,
            'Razão Social': conta.raz_social,
            'Nome Fantasia': conta.raz_social_red,
            'Emissão': conta.emissao.strftime('%d/%m/%Y') if conta.emissao else '',
            'Vencimento': conta.vencimento.strftime('%d/%m/%Y') if conta.vencimento else '',
            'Valor Original': conta.valor_original or 0,
            'Valor Residual': conta.valor_residual or 0,
            'Pago Odoo': 'Sim' if conta.parcela_paga else 'Não',
            'Reconciliado': 'Sim' if conta.reconciliado else 'Não',
            'Status Sistema': conta.status_sistema or '',
            'Data Programada': conta.data_programada.strftime('%d/%m/%Y') if conta.data_programada else '',
            'Dias Vencidos': conta.dias_vencidos,
            'Status Vencimento': conta.status_vencimento,
            'Observação': conta.observacao or '',
            'Alerta': 'Sim' if conta.alerta else 'Não',
            'Última Sincronização': conta.ultima_sincronizacao.strftime('%d/%m/%Y %H:%M') if conta.ultima_sincronizacao else '',
        })

    # Criar Excel
    df = pd.DataFrame(dados)
    output = _gerar_excel(df, 'Contas a Pagar')

    filename = f'contas_pagar_{date.today().strftime("%Y-%m-%d")}.xlsx'
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


# ========================================
# FUNÇÕES AUXILIARES
# ========================================

def _gerar_excel(df: pd.DataFrame, sheet_name: str) -> BytesIO:
    """
    Gera arquivo Excel formatado a partir de DataFrame.

    Args:
        df: DataFrame com os dados
        sheet_name: Nome da aba

    Returns:
        BytesIO com o arquivo Excel
    """
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        # Ajustar largura das colunas
        worksheet = writer.sheets[sheet_name]
        for column in worksheet.columns:
            column_letter = column[0].column_letter
            max_length = 0
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

    output.seek(0)
    return output
