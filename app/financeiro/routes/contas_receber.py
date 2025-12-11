"""
Rotas de Contas a Receber
Hub, Listagem, Exportação (Excel/JSON), Sincronização e Status
"""

from flask import render_template, request, redirect, flash, url_for, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from io import BytesIO
import pandas as pd
from sqlalchemy import func, or_, exists

from app import db
from app.financeiro.routes import financeiro_bp


# ========================================
# HUB E LISTAGEM
# ========================================

@financeiro_bp.route('/contas-receber')
@login_required
def contas_receber_hub():
    """
    HUB Central de Contas a Receber
    Página inicial com links para listagem e exportação
    """
    return render_template('financeiro/contas_receber_hub.html')


@financeiro_bp.route('/contas-receber/listar')
@login_required
def listar_contas_receber():
    """
    Listagem de Contas a Receber com paginação e filtros.
    Paginação: 200 registros por página.
    """
    from app.financeiro.models import ContasAReceber
    from app.faturamento.models import FaturamentoProduto
    from app.monitoramento.models import EntregaMonitorada

    # Parâmetros de paginação
    page = request.args.get('page', 1, type=int)
    per_page = 200

    # Parâmetros de ordenação
    sort = request.args.get('sort', 'vencimento')
    direction = request.args.get('direction', 'asc')

    # Parâmetros de filtro
    empresa = request.args.get('empresa', '', type=str)
    titulo_nf = request.args.get('titulo_nf', '', type=str)
    cnpj = request.args.get('cnpj', '', type=str)
    cliente = request.args.get('cliente', '', type=str)
    uf = request.args.get('uf', '', type=str)
    status = request.args.get('status', '', type=str)
    venc_de = request.args.get('venc_de', '', type=str)
    venc_ate = request.args.get('venc_ate', '', type=str)
    vendedor = request.args.get('vendedor', '', type=str)
    transportadora = request.args.get('transportadora', '', type=str)
    canhoto = request.args.get('canhoto', '', type=str)
    data_lembrete = request.args.get('data_lembrete', '', type=str)

    # Query base
    query = ContasAReceber.query

    # Aplicar filtros
    if empresa:
        query = query.filter(ContasAReceber.empresa == int(empresa))

    if titulo_nf:
        query = query.filter(ContasAReceber.titulo_nf.ilike(f'%{titulo_nf}%'))

    if cnpj:
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
        query = query.filter(ContasAReceber.cnpj.ilike(f'%{cnpj_limpo}%'))

    if cliente:
        query = query.filter(or_(
            ContasAReceber.raz_social.ilike(f'%{cliente}%'),
            ContasAReceber.raz_social_red.ilike(f'%{cliente}%')
        ))

    if uf:
        query = query.filter(ContasAReceber.uf_cliente == uf)

    if status:
        hoje = date.today()

        # Subquery para verificar NF cancelada via FaturamentoProduto.status_nf = 'Cancelado'
        nf_cancelada_subquery = exists().where(
            FaturamentoProduto.numero_nf == ContasAReceber.titulo_nf,
            FaturamentoProduto.status_nf == 'Cancelado'
        )

        if status == 'aberto':
            query = query.filter(
                ContasAReceber.parcela_paga == False,
                ~nf_cancelada_subquery,  # NF NÃO cancelada
                or_(ContasAReceber.vencimento >= hoje, ContasAReceber.vencimento.is_(None))
            )
        elif status == 'pago':
            query = query.filter(ContasAReceber.parcela_paga == True)
        elif status == 'vencido':
            query = query.filter(
                ContasAReceber.parcela_paga == False,
                ~nf_cancelada_subquery,  # NF NÃO cancelada
                ContasAReceber.vencimento < hoje
            )
        elif status == 'cancelado':
            query = query.filter(nf_cancelada_subquery)  # NF cancelada

    if venc_de:
        try:
            data_de = datetime.strptime(venc_de, '%Y-%m-%d').date()
            query = query.filter(ContasAReceber.vencimento >= data_de)
        except ValueError:
            pass

    if venc_ate:
        try:
            data_ate = datetime.strptime(venc_ate, '%Y-%m-%d').date()
            query = query.filter(ContasAReceber.vencimento <= data_ate)
        except ValueError:
            pass

    # Filtro por data de lembrete (usado pelos badges de lembrete)
    if data_lembrete:
        try:
            data_lemb = datetime.strptime(data_lembrete, '%Y-%m-%d').date()
            query = query.filter(ContasAReceber.data_lembrete == data_lemb)
        except ValueError:
            pass

    # Filtros que usam dados de EntregaMonitorada (via join)
    if vendedor or transportadora or canhoto:
        query = query.outerjoin(
            EntregaMonitorada,
            ContasAReceber.entrega_monitorada_id == EntregaMonitorada.id
        )

        if vendedor:
            query = query.filter(EntregaMonitorada.vendedor.ilike(f'%{vendedor}%'))

        if transportadora:
            query = query.filter(EntregaMonitorada.transportadora.ilike(f'%{transportadora}%'))

        if canhoto:
            if canhoto == 'com':
                query = query.filter(EntregaMonitorada.canhoto_arquivo.isnot(None))
            elif canhoto == 'sem':
                query = query.filter(
                    or_(
                        EntregaMonitorada.canhoto_arquivo.is_(None),
                        ContasAReceber.entrega_monitorada_id.is_(None)
                    )
                )

    # Aplicar ordenação
    sort_column = getattr(ContasAReceber, sort, ContasAReceber.vencimento)
    if direction == 'desc':
        query = query.order_by(sort_column.desc().nullslast())
    else:
        query = query.order_by(sort_column.asc().nullsfirst())

    # Paginar
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)
    contas = paginacao.items

    # Calcular totais da página
    valor_total = sum(c.valor_titulo or 0 for c in contas)
    hoje = date.today()
    vencidos = sum(1 for c in contas if c.vencimento and c.vencimento < hoje and not c.parcela_paga)
    pagos = sum(1 for c in contas if c.parcela_paga)

    # Buscar UFs disponíveis para filtro
    ufs_disponiveis = db.session.query(ContasAReceber.uf_cliente).distinct().filter(
        ContasAReceber.uf_cliente.isnot(None)
    ).order_by(ContasAReceber.uf_cliente).all()
    ufs_disponiveis = [u[0] for u in ufs_disponiveis if u[0]]

    return render_template(
        'financeiro/listar_contas_receber.html',
        contas=contas,
        paginacao=paginacao,
        sort=sort,
        direction=direction,
        hoje=hoje,
        valor_total=valor_total,
        vencidos=vencidos,
        pagos=pagos,
        ufs_disponiveis=ufs_disponiveis
    )


# ========================================
# EXPORTAÇÃO
# ========================================

@financeiro_bp.route('/contas-receber/exportar')
@login_required
def contas_receber_exportar():
    """
    Página de Exportação de Contas a Receber
    Exibe interface para exportação de relatório (Excel/JSON)
    """
    data_ontem = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    return render_template(
        'financeiro/contas_receber.html',
        data_ontem=data_ontem
    )


@financeiro_bp.route('/contas-receber/exportar-excel')
@login_required
def exportar_contas_receber_excel():
    """
    Exporta relatório de Contas a Receber em Excel
    RESPEITA OS FILTROS APLICADOS NA LISTAGEM
    """
    try:
        from app.financeiro.models import ContasAReceber
        from app.faturamento.models import FaturamentoProduto
        from app.monitoramento.models import EntregaMonitorada

        # Obter parâmetros de filtro (mesmos da listagem)
        empresa = request.args.get('empresa', type=int)
        titulo_nf = request.args.get('titulo_nf')
        cnpj = request.args.get('cnpj')
        cliente = request.args.get('cliente')
        uf = request.args.get('uf')
        status = request.args.get('status')
        venc_de = request.args.get('venc_de')
        venc_ate = request.args.get('venc_ate')
        vendedor = request.args.get('vendedor')
        transportadora = request.args.get('transportadora')
        canhoto = request.args.get('canhoto')

        # Query base
        query = ContasAReceber.query

        # Aplicar filtros (mesma lógica da listagem)
        if empresa:
            query = query.filter(ContasAReceber.empresa == empresa)

        if titulo_nf:
            query = query.filter(ContasAReceber.titulo_nf.ilike(f'%{titulo_nf}%'))

        if cnpj:
            query = query.filter(ContasAReceber.cnpj.ilike(f'%{cnpj}%'))

        if cliente:
            query = query.filter(or_(
                ContasAReceber.raz_social.ilike(f'%{cliente}%'),
                ContasAReceber.raz_social_red.ilike(f'%{cliente}%')
            ))

        if uf:
            query = query.filter(ContasAReceber.uf_cliente == uf)

        if status:
            hoje = date.today()
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

        if venc_de:
            try:
                data_de = datetime.strptime(venc_de, '%Y-%m-%d').date()
                query = query.filter(ContasAReceber.vencimento >= data_de)
            except ValueError:
                pass

        if venc_ate:
            try:
                data_ate = datetime.strptime(venc_ate, '%Y-%m-%d').date()
                query = query.filter(ContasAReceber.vencimento <= data_ate)
            except ValueError:
                pass

        if vendedor or transportadora or canhoto:
            query = query.outerjoin(
                EntregaMonitorada,
                ContasAReceber.entrega_monitorada_id == EntregaMonitorada.id
            )

            if vendedor:
                query = query.filter(EntregaMonitorada.vendedor.ilike(f'%{vendedor}%'))

            if transportadora:
                query = query.filter(EntregaMonitorada.transportadora.ilike(f'%{transportadora}%'))

            if canhoto:
                if canhoto == 'com':
                    query = query.filter(EntregaMonitorada.canhoto_arquivo.isnot(None))
                elif canhoto == 'sem':
                    query = query.filter(
                        or_(
                            EntregaMonitorada.canhoto_arquivo.is_(None),
                            ContasAReceber.entrega_monitorada_id.is_(None)
                        )
                    )

        # Ordenar por vencimento
        query = query.order_by(ContasAReceber.vencimento.asc().nullslast())

        # Executar query (sem paginação para Excel)
        contas = query.all()

        # Montar dados para DataFrame
        dados = []
        for conta in contas:
            em = conta.entrega_monitorada
            total_abat = (conta.desconto or 0) + sum(ab.valor or 0 for ab in conta.abatimentos.all())
            saldo = (conta.valor_titulo or 0) - total_abat

            dados.append({
                'Empresa': conta.empresa_nome,
                'NF': conta.titulo_nf,
                'Parcela': conta.parcela,
                'CNPJ': conta.cnpj,
                'Cliente': conta.raz_social_red or conta.raz_social,
                'UF': conta.uf_cliente,
                'Emissão': conta.emissao.strftime('%d/%m/%Y') if conta.emissao else '',
                'Vencimento': conta.vencimento.strftime('%d/%m/%Y') if conta.vencimento else '',
                'Lib. Antecipação': conta.liberacao_prevista_antecipacao.strftime('%d/%m/%Y') if conta.liberacao_prevista_antecipacao else '',
                'Valor Original': conta.valor_original or 0,
                'Desconto': conta.desconto or 0,
                'Valor Título': conta.valor_titulo or 0,
                'Abatimentos': total_abat,
                'Saldo': saldo,
                'Confirmação': conta.confirmacao_tipo.tipo if conta.confirmacao_tipo else 'ABERTO',
                'Ação Necessária': conta.acao_necessaria_tipo.tipo if conta.acao_necessaria_tipo else '',
                'Obs. Ação': conta.obs_acao_necessaria or '',
                'Data Lembrete': conta.data_lembrete.strftime('%d/%m/%Y') if conta.data_lembrete else '',
                'Status Entrega': em.status_finalizacao if em else '',
                'Previsão Entrega': em.data_entrega_prevista.strftime('%d/%m/%Y') if em and em.data_entrega_prevista else '',
                'Transportadora': em.transportadora if em else '',
                'Vendedor': em.vendedor if em else '',
                'Canhoto': 'Sim' if em and em.possui_canhoto else 'Não',
                'Pago': 'Sim' if conta.parcela_paga else 'Não',
                'Cancelado': 'Sim' if conta.nf_cancelada else 'Não',
                'Observação': conta.observacao or ''
            })

        # Criar DataFrame
        df = pd.DataFrame(dados)

        # Gerar Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Contas a Receber')

            # Formatar colunas
            worksheet = writer.sheets['Contas a Receber']
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

        # Nome do arquivo
        filename = f'contas_receber_{date.today().strftime("%Y-%m-%d")}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        flash(f'Erro ao exportar relatório: {str(e)}', 'danger')
        return redirect(url_for('financeiro.listar_contas_receber'))


@financeiro_bp.route('/contas-receber/exportar-json')
def exportar_contas_receber_json():
    """
    API PÚBLICA: Exporta relatório de Contas a Receber em JSON
    Para uso com Power Query do Excel ou outras ferramentas

    NOTA: Rota pública (sem @login_required) para permitir acesso via Power Query
    """
    try:
        from app.financeiro.services.contas_receber_service import ContasReceberService

        # Obter data de filtro (se fornecida)
        data_param = request.args.get('data')
        data_inicio = None

        if data_param:
            try:
                data_inicio = datetime.strptime(data_param, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Criar serviço
        service = ContasReceberService()

        # Gerar JSON
        dados = service.exportar_json(data_inicio)

        # Retornar DIRETAMENTE a lista de dados (sem wrapper)
        # Isso facilita o Power Query do Excel
        response = jsonify(dados)

        # Adicionar headers CORS
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET')

        return response

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========================================
# SINCRONIZAÇÃO E STATUS
# ========================================

@financeiro_bp.route('/contas-receber/sincronizar-odoo', methods=['POST'])
@login_required
def sincronizar_contas_receber_odoo():
    """
    Sincronização manual de Contas a Receber com Odoo.

    Parâmetros (JSON body ou form data):
        data_inicio: Data inicial (YYYY-MM-DD) - opcional, default: D-7
        data_fim: Data final (YYYY-MM-DD) - opcional
        dias: Quantidade de dias retroativos - alternativa a data_inicio

    Uso:
        - Botão "Sincronizar com Odoo" na interface de Contas a Receber
        - POST /financeiro/contas-receber/sincronizar-odoo
        - Body: {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
    """
    try:
        from app.financeiro.services.sincronizacao_contas_receber_service import SincronizacaoContasReceberService
        from datetime import datetime, timedelta

        # Obter parâmetros (aceita JSON ou form data)
        data = request.get_json(silent=True) or {}

        # Parâmetros de data
        data_inicio_str = data.get('data_inicio') or request.form.get('data_inicio')
        data_fim_str = data.get('data_fim') or request.form.get('data_fim')
        dias = data.get('dias') or request.form.get('dias')

        # Converter datas
        data_inicio = None
        data_fim = None

        if data_inicio_str:
            try:
                data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Formato de data_inicio inválido: {data_inicio_str}. Use YYYY-MM-DD'
                }), 400

        if data_fim_str:
            try:
                data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Formato de data_fim inválido: {data_fim_str}. Use YYYY-MM-DD'
                }), 400

        # Se informou dias, calcular data_inicio
        if dias and not data_inicio:
            try:
                dias = int(dias)
                data_inicio = date.today() - timedelta(days=dias)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Parâmetro dias inválido: {dias}'
                }), 400

        # Criar serviço e executar sincronização
        service = SincronizacaoContasReceberService()

        # Se tem data_inicio ou data_fim, usar sincronizar() diretamente
        if data_inicio or data_fim:
            resultado = service.sincronizar(data_inicio=data_inicio, data_fim=data_fim)
        else:
            # Fallback: sincronização padrão (7 dias)
            resultado = service.sincronizar_manual(dias=7)

        if resultado.get('sucesso'):
            return jsonify({
                'success': True,
                'message': 'Sincronização concluída com sucesso!',
                'periodo': resultado.get('periodo', 'Últimos 7 dias'),
                'novos': resultado.get('novos', 0),
                'atualizados': resultado.get('atualizados', 0),
                'enriquecidos': resultado.get('enriquecidos', 0),
                'snapshots': resultado.get('snapshots_criados', 0),
                'erros': resultado.get('erros', 0)
            })
        else:
            return jsonify({
                'success': False,
                'error': resultado.get('erro', 'Erro desconhecido na sincronização')
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/contas-receber/status')
@login_required
def status_contas_receber():
    """
    Retorna estatísticas da tabela contas_a_receber
    """
    try:
        from app.financeiro.models import ContasAReceber, ContasAReceberSnapshot

        total = ContasAReceber.query.count()
        por_empresa = db.session.query(
            ContasAReceber.empresa,
            func.count(ContasAReceber.id)
        ).group_by(ContasAReceber.empresa).all()

        ultima_sync = db.session.query(
            func.max(ContasAReceber.ultima_sincronizacao)
        ).scalar()

        total_snapshots = ContasAReceberSnapshot.query.count()

        empresas = {
            1: 'NACOM GOYA - FB',
            2: 'NACOM GOYA - SC',
            3: 'NACOM GOYA - CD'
        }

        return jsonify({
            'success': True,
            'total': total,
            'por_empresa': [
                {'empresa': empresas.get(e, f'Empresa {e}'), 'total': t}
                for e, t in por_empresa
            ],
            'ultima_sincronizacao': ultima_sync.isoformat() if ultima_sync else None,
            'total_snapshots': total_snapshots
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
