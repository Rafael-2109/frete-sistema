"""Rotas de configuracao — CRUD categorias, regras, membros, exclusoes."""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app import db
from app.pessoal import pode_acessar_pessoal
from app.pessoal.models import (
    PessoalCategoria, PessoalRegraCategorizacao, PessoalMembro,
    PessoalExclusaoEmpresa, PessoalConta,
)
from app.pessoal.services.aprendizado_service import (
    despropagar_regra, normalizar_padrao,
    propagar_regra_para_pendentes, contar_matches_por_regra,
)
from app.utils.timezone import agora_utc_naive

configuracao_bp = Blueprint('pessoal_configuracao', __name__)


@configuracao_bp.route('/configuracao')
@login_required
def index():
    """Pagina de configuracao — categorias, regras, membros, exclusoes."""
    if not pode_acessar_pessoal(current_user):
        return 'Acesso restrito.', 403

    categorias = PessoalCategoria.query.order_by(
        PessoalCategoria.grupo, PessoalCategoria.nome
    ).all()
    regras = PessoalRegraCategorizacao.query.order_by(
        PessoalRegraCategorizacao.tipo_regra,
        PessoalRegraCategorizacao.padrao_historico,
    ).all()
    membros = PessoalMembro.query.order_by(PessoalMembro.nome).all()
    exclusoes = PessoalExclusaoEmpresa.query.order_by(PessoalExclusaoEmpresa.padrao).all()
    contas = PessoalConta.query.order_by(PessoalConta.nome).all()

    # Contar pendentes que cada regra PADRAO matcharia (para coluna "Match")
    contagem_match = contar_matches_por_regra(regras)

    return render_template(
        'pessoal/configuracao.html',
        categorias=categorias,
        regras=regras,
        membros=membros,
        exclusoes=exclusoes,
        contas=contas,
        contagem_match=contagem_match,
    )


# =============================================================================
# CRUD CATEGORIAS
# =============================================================================
@configuracao_bp.route('/api/categorias', methods=['POST'])
@login_required
def salvar_categoria():
    """Criar ou atualizar categoria."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json()
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'Dados invalidos.'}), 400

    cat_id = dados.get('id')
    nome = dados.get('nome', '').strip()
    grupo = dados.get('grupo', '').strip()
    icone = dados.get('icone', '').strip()

    if not nome or not grupo:
        return jsonify({'sucesso': False, 'mensagem': 'Nome e grupo obrigatorios.'}), 400

    try:
        if cat_id:
            cat = db.session.get(PessoalCategoria, cat_id)
            if not cat:
                return jsonify({'sucesso': False, 'mensagem': 'Categoria nao encontrada.'}), 404
            cat.nome = nome
            cat.grupo = grupo
            cat.icone = icone
        else:
            cat = PessoalCategoria(nome=nome, grupo=grupo, icone=icone)
            db.session.add(cat)

        db.session.commit()
        return jsonify({'sucesso': True, 'categoria': cat.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@configuracao_bp.route('/api/categorias/<int:cat_id>/toggle', methods=['PATCH'])
@login_required
def toggle_categoria(cat_id):
    """Toggle ativa/inativa de categoria."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    cat = db.session.get(PessoalCategoria, cat_id)
    if not cat:
        return jsonify({'sucesso': False, 'mensagem': 'Categoria nao encontrada.'}), 404

    try:
        cat.ativa = not cat.ativa
        db.session.commit()
        return jsonify({
            'sucesso': True,
            'mensagem': f'Categoria {"ativada" if cat.ativa else "desativada"}.',
            'categoria': cat.to_dict(),
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


# =============================================================================
# CRUD REGRAS
# =============================================================================
@configuracao_bp.route('/api/regras', methods=['POST'])
@login_required
def salvar_regra():
    """Criar ou atualizar regra de categorizacao."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json()
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'Dados invalidos.'}), 400

    regra_id = dados.get('id')
    padrao = dados.get('padrao_historico', '').strip()
    tipo_regra = dados.get('tipo_regra', 'PADRAO')
    categoria_id = dados.get('categoria_id')
    categorias_restritas = dados.get('categorias_restritas_ids', [])

    if not padrao:
        return jsonify({'sucesso': False, 'mensagem': 'Padrao obrigatorio.'}), 400

    # Normalizar padrao antes de salvar (consistencia com matching)
    padrao = normalizar_padrao(padrao)

    try:
        afetadas = 0
        propagados_info = None

        if regra_id:
            regra = db.session.get(PessoalRegraCategorizacao, regra_id)
            if not regra:
                return jsonify({'sucesso': False, 'mensagem': 'Regra nao encontrada.'}), 404

            # Guardar estado anterior para detectar mudancas
            tipo_anterior = regra.tipo_regra
            padrao_anterior = regra.padrao_historico
            categoria_anterior = regra.categoria_id

            # Atualizar campos
            regra.padrao_historico = padrao
            regra.tipo_regra = tipo_regra
            regra.categoria_id = categoria_id if tipo_regra == 'PADRAO' else None
            regra.set_categorias_restritas(categorias_restritas if tipo_regra == 'RELATIVO' else [])
            regra.atualizado_em = agora_utc_naive()

            # Detectar se precisa repropagar
            mudou_padrao = (padrao != padrao_anterior)
            mudou_categoria = (categoria_id != categoria_anterior)
            mudou_tipo = (tipo_anterior != tipo_regra)

            needs_repropagation = (
                (tipo_anterior == 'PADRAO' and mudou_tipo) or  # PADRAO→RELATIVO
                (tipo_regra == 'PADRAO' and (mudou_padrao or mudou_categoria))  # Padrao/Categoria editados
            )

            if needs_repropagation:
                afetadas = despropagar_regra(regra.id)
                if tipo_regra == 'PADRAO':
                    # Usa propagacao targetada (2 queries) vs full pipeline (3*N queries)
                    propagados_info = propagar_regra_para_pendentes(regra)
        else:
            # Nova regra
            regra = PessoalRegraCategorizacao(
                padrao_historico=padrao,
                tipo_regra=tipo_regra,
                categoria_id=categoria_id if tipo_regra == 'PADRAO' else None,
                origem='manual',
            )
            if tipo_regra == 'RELATIVO':
                regra.set_categorias_restritas(categorias_restritas)
            db.session.add(regra)
            db.session.flush()  # regra.id disponivel para propagacao

            # Propagar regra nova PADRAO para pendentes (targetada: 2 queries)
            if tipo_regra == 'PADRAO':
                propagados_info = propagar_regra_para_pendentes(regra)

        db.session.commit()

        resp = {'sucesso': True, 'regra': regra.to_dict()}
        if afetadas > 0:
            resp['afetadas'] = afetadas
        if propagados_info:
            resp['propagados'] = propagados_info['propagados']
        return jsonify(resp)

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@configuracao_bp.route('/api/regras/<int:regra_id>', methods=['DELETE'])
@login_required
def excluir_regra(regra_id):
    """Desativar regra."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    regra = db.session.get(PessoalRegraCategorizacao, regra_id)
    if not regra:
        return jsonify({'sucesso': False, 'mensagem': 'Regra nao encontrada.'}), 404

    regra.ativo = False
    regra.atualizado_em = agora_utc_naive()
    db.session.commit()
    return jsonify({'sucesso': True, 'mensagem': 'Regra desativada.'})


# =============================================================================
# CRUD MEMBROS
# =============================================================================
@configuracao_bp.route('/api/membros', methods=['POST'])
@login_required
def salvar_membro():
    """Criar ou atualizar membro."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json()
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'Dados invalidos.'}), 400

    membro_id = dados.get('id')
    nome = dados.get('nome', '').strip()
    nome_completo = dados.get('nome_completo', '').strip()
    papel = dados.get('papel', '').strip()

    if not nome:
        return jsonify({'sucesso': False, 'mensagem': 'Nome obrigatorio.'}), 400

    try:
        if membro_id:
            membro = db.session.get(PessoalMembro, membro_id)
            if not membro:
                return jsonify({'sucesso': False, 'mensagem': 'Membro nao encontrado.'}), 404
            membro.nome = nome
            membro.nome_completo = nome_completo
            membro.papel = papel
        else:
            membro = PessoalMembro(nome=nome, nome_completo=nome_completo, papel=papel)
            db.session.add(membro)

        db.session.commit()
        return jsonify({'sucesso': True, 'membro': membro.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


# =============================================================================
# CRUD EXCLUSOES EMPRESA
# =============================================================================
@configuracao_bp.route('/api/exclusoes', methods=['POST'])
@login_required
def salvar_exclusao():
    """Criar ou atualizar exclusao empresa."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json()
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'Dados invalidos.'}), 400

    excl_id = dados.get('id')
    padrao = dados.get('padrao', '').strip()
    descricao = dados.get('descricao', '').strip()

    if not padrao:
        return jsonify({'sucesso': False, 'mensagem': 'Padrao obrigatorio.'}), 400

    try:
        if excl_id:
            excl = db.session.get(PessoalExclusaoEmpresa, excl_id)
            if not excl:
                return jsonify({'sucesso': False, 'mensagem': 'Exclusao nao encontrada.'}), 404
            excl.padrao = padrao
            excl.descricao = descricao
        else:
            excl = PessoalExclusaoEmpresa(padrao=padrao, descricao=descricao)
            db.session.add(excl)

        db.session.commit()
        return jsonify({'sucesso': True, 'exclusao': excl.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500
