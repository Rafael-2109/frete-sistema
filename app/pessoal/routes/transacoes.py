"""Rotas de transacoes — listagem, filtros e categorizacao inline."""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, func

from app import db
from app.pessoal import pode_acessar_pessoal
from app.pessoal.models import (
    PessoalTransacao, PessoalCategoria, PessoalConta, PessoalMembro,
)
from app.pessoal.services.aprendizado_service import (
    aprender_de_categorizacao, propagar_para_pendentes, despropagar_regra,
    simular_propagacao, propagar_regra_para_pendentes, propagar_parcelas,
)
from app.utils.timezone import agora_utc_naive

transacoes_bp = Blueprint('pessoal_transacoes', __name__)


@transacoes_bp.route('/transacoes')
@login_required
def listar():
    """Lista transacoes com filtros."""
    if not pode_acessar_pessoal(current_user):
        return 'Acesso restrito.', 403

    # Filtros
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    conta_id = request.args.get('conta_id', type=int)
    categoria_id = request.args.get('categoria_id', type=int)
    membro_id = request.args.get('membro_id', type=int)
    status = request.args.get('status')
    tipo = request.args.get('tipo')
    busca = request.args.get('busca', '').strip()
    excluir_filtradas = request.args.get('excluir_filtradas', '1')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    sort_by = request.args.get('sort_by', 'data')
    sort_order = request.args.get('sort_order', 'desc')

    query = PessoalTransacao.query

    if data_inicio:
        query = query.filter(PessoalTransacao.data >= data_inicio)
    if data_fim:
        query = query.filter(PessoalTransacao.data <= data_fim)
    if conta_id:
        query = query.filter_by(conta_id=conta_id)
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    if membro_id:
        query = query.filter_by(membro_id=membro_id)
    if status:
        query = query.filter_by(status=status)
    if tipo:
        query = query.filter_by(tipo=tipo)
    if busca:
        busca_like = f'%{busca}%'
        query = query.filter(or_(
            PessoalTransacao.historico.ilike(busca_like),
            PessoalTransacao.descricao.ilike(busca_like),
            PessoalTransacao.historico_completo.ilike(busca_like),
        ))
    if excluir_filtradas == '1':
        query = query.filter_by(excluir_relatorio=False)

    # Chave composta: historico_completo (contem historico + descricao normalizado)
    # Sem isso, "Transf Pix" agrupa 1502 transacoes diferentes
    _hist_key = func.coalesce(
        PessoalTransacao.historico_completo, PessoalTransacao.historico,
    )

    # Subquery: count de PENDENTES por historico composto (para sort por similares)
    similares_subq = db.session.query(
        _hist_key.label('hist_key'),
        func.count(PessoalTransacao.id).label('similares_count')
    ).filter_by(
        status='PENDENTE', excluir_relatorio=False,
    ).group_by(_hist_key).subquery()

    # Ordenacao dinamica (server-side — tabela paginada)
    SORT_COLUMNS = {
        'data': PessoalTransacao.data,
        'valor': PessoalTransacao.valor,
        'historico': PessoalTransacao.historico,
        'descricao': PessoalTransacao.descricao,
        'tipo': PessoalTransacao.tipo,
        'status': PessoalTransacao.status,
    }
    if sort_by == 'similares':
        query = query.outerjoin(
            similares_subq,
            _hist_key == similares_subq.c.hist_key,
        )
        sort_col = func.coalesce(similares_subq.c.similares_count, 0)
    else:
        sort_col = SORT_COLUMNS.get(sort_by, PessoalTransacao.data)
    if sort_order == 'asc':
        query = query.order_by(sort_col.asc(), PessoalTransacao.id.asc())
    else:
        query = query.order_by(sort_col.desc(), PessoalTransacao.id.desc())

    # Paginar
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

    # Dados para filtros
    contas = PessoalConta.query.filter_by(ativa=True).order_by(PessoalConta.nome).all()
    categorias = PessoalCategoria.query.filter_by(ativa=True).order_by(
        PessoalCategoria.grupo, PessoalCategoria.nome
    ).all()
    membros = PessoalMembro.query.filter_by(ativo=True).order_by(PessoalMembro.nome).all()

    # Contadores
    total_pendentes = PessoalTransacao.query.filter_by(
        status='PENDENTE', excluir_relatorio=False
    ).count()

    # Contador de similares: quantas PENDENTES tem o mesmo historico composto (1 query)
    pendentes_hist = db.session.query(
        _hist_key, func.count(PessoalTransacao.id)
    ).filter_by(
        status='PENDENTE', excluir_relatorio=False,
    ).group_by(_hist_key).all()
    hist_count = {h: c for h, c in pendentes_hist if h}
    similares_map = {}
    for t in paginacao.items:
        similares_map[t.id] = hist_count.get(
            t.historico_completo or t.historico, 0
        )

    return render_template(
        'pessoal/transacoes.html',
        transacoes=paginacao.items,
        paginacao=paginacao,
        contas=contas,
        categorias=categorias,
        membros=membros,
        total_pendentes=total_pendentes,
        similares_map=similares_map,
        filtros={
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'conta_id': conta_id,
            'categoria_id': categoria_id,
            'membro_id': membro_id,
            'status': status,
            'tipo': tipo,
            'busca': busca,
            'excluir_filtradas': excluir_filtradas,
            'sort_by': sort_by,
            'sort_order': sort_order,
        },
    )


@transacoes_bp.route('/transacoes/pendentes')
@login_required
def pendentes():
    """Lista apenas transacoes pendentes para categorizacao rapida."""
    if not pode_acessar_pessoal(current_user):
        return 'Acesso restrito.', 403

    return listar()  # Reusa com filtro de status


@transacoes_bp.route('/api/categorizar', methods=['POST'])
@login_required
def categorizar():
    """Categoriza uma transacao manualmente (AJAX)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json()
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'Dados invalidos.'}), 400

    transacao_id = dados.get('transacao_id')
    categoria_id = dados.get('categoria_id')
    membro_id = dados.get('membro_id')
    criar_regra = dados.get('criar_regra', True)
    tipo_regra = dados.get('tipo_regra', 'PADRAO')  # PADRAO | RELATIVO
    padrao_historico = dados.get('padrao_historico')  # padrao editado pelo usuario

    # F1 / F4 (opcionais) vindos do modal de categorizacao
    cpf_cnpj_padrao = dados.get('cpf_cnpj_padrao')

    def _parse_valor(raw):
        if raw is None or raw == '' or raw == 0:
            return None
        try:
            v = float(raw)
            return v if v > 0 else None
        except (TypeError, ValueError):
            return None

    valor_min = _parse_valor(dados.get('valor_min'))
    valor_max = _parse_valor(dados.get('valor_max'))

    if not transacao_id or not categoria_id:
        return jsonify({'sucesso': False, 'mensagem': 'transacao_id e categoria_id obrigatorios.'}), 400

    if tipo_regra not in ('PADRAO', 'RELATIVO'):
        return jsonify({'sucesso': False, 'mensagem': 'tipo_regra deve ser PADRAO ou RELATIVO.'}), 400

    if valor_min is not None and valor_max is not None and valor_min > valor_max:
        return jsonify({
            'sucesso': False,
            'mensagem': 'valor_min nao pode ser maior que valor_max.',
        }), 400

    transacao = db.session.get(PessoalTransacao, transacao_id)
    if not transacao:
        return jsonify({'sucesso': False, 'mensagem': 'Transacao nao encontrada.'}), 404

    try:
        transacao.categoria_id = categoria_id
        transacao.categorizacao_auto = False
        transacao.status = 'CATEGORIZADO'
        transacao.categorizado_em = agora_utc_naive()
        transacao.categorizado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        if membro_id:
            transacao.membro_id = membro_id
            transacao.membro_auto = False

        # Aprender regra e linkar na transacao
        regra = None
        if criar_regra:
            regra = aprender_de_categorizacao(
                transacao_id, categoria_id, membro_id,
                tipo_regra=tipo_regra, padrao_historico=padrao_historico,
                cpf_cnpj_padrao=cpf_cnpj_padrao,
                valor_min=valor_min, valor_max=valor_max,
            )
            if regra:
                transacao.regra_id = regra.id

        # F2: propagar categoria para outras parcelas da mesma compra
        parcelas_propagadas = propagar_parcelas(transacao)

        # Propagar para transacoes PENDENTES similares
        # Regras RELATIVO nao propagam (usuario deve escolher)
        # Usa propagacao targetada (2 queries) vs pipeline completo (3*N queries)
        # padrao_override: usa padrao editado pelo usuario (consistente com Preview)
        propagados_info = {'propagados': 0, 'total_pendentes': 0}
        if regra and regra.tipo_regra == 'PADRAO':
            propagados_info = propagar_regra_para_pendentes(
                regra, padrao_override=padrao_historico,
            )

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Transacao categorizada com sucesso.',
            'transacao': transacao.to_dict(),
            'regra_criada': regra.to_dict() if regra else None,
            'propagados': propagados_info['propagados'],
            'parcelas_propagadas': parcelas_propagadas,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@transacoes_bp.route('/api/preview-propagacao', methods=['POST'])
@login_required
def preview_propagacao():
    """Preview de quais transacoes PENDENTES seriam auto-categorizadas (dry-run)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    try:
        dados = request.get_json() or {}
        padrao_historico = dados.get('padrao_historico')
        afetadas = simular_propagacao(padrao_historico=padrao_historico)
        return jsonify({
            'sucesso': True,
            'transacoes': afetadas,
            'total': len(afetadas),
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@transacoes_bp.route('/api/descategorizar', methods=['POST'])
@login_required
def descategorizar():
    """Descategoriza uma transacao e propaga o reset (AJAX)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json()
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'Dados invalidos.'}), 400

    transacao_id = dados.get('transacao_id')
    if not transacao_id:
        return jsonify({'sucesso': False, 'mensagem': 'transacao_id obrigatorio.'}), 400

    transacao = db.session.get(PessoalTransacao, transacao_id)
    if not transacao:
        return jsonify({'sucesso': False, 'mensagem': 'Transacao nao encontrada.'}), 404

    try:
        afetadas = 0

        # Se transacao tem regra_id e foi manual: despropagar regra
        if transacao.regra_id and not transacao.categorizacao_auto:
            afetadas = despropagar_regra(transacao.regra_id)

        # Resetar a transacao atual para PENDENTE
        transacao.categoria_id = None
        transacao.regra_id = None
        transacao.categorizacao_auto = False
        transacao.categorizacao_confianca = None
        transacao.status = 'PENDENTE'
        transacao.categorizado_em = None
        transacao.categorizado_por = None

        # Re-rodar pipeline em pendentes (inclui esta + as resetadas)
        propagados_info = propagar_para_pendentes()

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Transacao descategorizada.',
            'transacao': transacao.to_dict(),
            'afetadas': afetadas,
            'propagados': propagados_info['propagados'],
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@transacoes_bp.route('/api/categorizar-lote', methods=['POST'])
@login_required
def categorizar_lote():
    """Categoriza multiplas transacoes de uma vez (AJAX)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json()
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'Dados invalidos.'}), 400

    ids = dados.get('ids', [])
    categoria_id = dados.get('categoria_id')
    membro_id = dados.get('membro_id')

    if not ids or not categoria_id:
        return jsonify({'sucesso': False, 'mensagem': 'ids e categoria_id obrigatorios.'}), 400

    try:
        atualizados = 0
        parcelas_propagadas = 0
        for tid in ids:
            transacao = db.session.get(PessoalTransacao, tid)
            if transacao:
                transacao.categoria_id = categoria_id
                transacao.categorizacao_auto = False
                transacao.status = 'CATEGORIZADO'
                transacao.categorizado_em = agora_utc_naive()
                transacao.categorizado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
                if membro_id:
                    transacao.membro_id = membro_id
                    transacao.membro_auto = False
                # Aprender regra para a primeira do lote
                if atualizados == 0:
                    aprender_de_categorizacao(tid, categoria_id, membro_id)
                # F2: propagar para outras parcelas da mesma compra
                parcelas_propagadas += propagar_parcelas(transacao)
                atualizados += 1

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': f'{atualizados} transacoes categorizadas.',
            'atualizados': atualizados,
            'parcelas_propagadas': parcelas_propagadas,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500
