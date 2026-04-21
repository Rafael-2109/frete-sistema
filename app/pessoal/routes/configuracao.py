"""Rotas de configuracao — CRUD categorias, regras, membros, exclusoes."""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.pessoal import pode_acessar_pessoal
from app.pessoal.models import (
    PessoalCategoria, PessoalRegraCategorizacao, PessoalMembro,
    PessoalConta, PessoalTransacao,
)
from app.pessoal.services.aprendizado_service import (
    despropagar_regra, normalizar_padrao,
    propagar_regra_para_pendentes, contar_matches_por_regra,
    desvincular_manuais_da_regra, propagar_regra_forcado,
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
    contas = PessoalConta.query.order_by(PessoalConta.nome).all()

    # Contar pendentes que cada regra PADRAO matcharia (para coluna "Match")
    contagem_match = contar_matches_por_regra(regras)

    # Qtd e valor total por categoria (historico, exclui transacoes fora do relatorio)
    agregados_raw = db.session.query(
        PessoalTransacao.categoria_id,
        func.count(PessoalTransacao.id),
        func.sum(PessoalTransacao.valor),
    ).filter(
        PessoalTransacao.excluir_relatorio.is_(False),
    ).group_by(PessoalTransacao.categoria_id).all()

    # Numero de meses distintos com movimento valido no historico (base para media/mes)
    # Usamos o conjunto total do historico para consistencia entre categorias — assim
    # uma categoria que aparece em poucos meses nao distorce a comparacao.
    num_meses = db.session.query(
        func.count(func.distinct(func.date_trunc('month', PessoalTransacao.data)))
    ).filter(
        PessoalTransacao.excluir_relatorio.is_(False),
    ).scalar() or 1
    # Protecao contra divisao por zero (scalar() pode retornar 0 se nao houver transacoes)
    if num_meses <= 0:
        num_meses = 1

    agregados = {
        cat_id: {
            'qtd': int(qtd or 0),
            'total': float(total or 0),
            'media_mes': float(total or 0) / num_meses,
        }
        for cat_id, qtd, total in agregados_raw
    }

    # Agregados por grupo (soma dos valores das categorias que compoem o grupo).
    # Iteramos `categorias` para manter ordem estavel (mesma do render).
    grupos_agregados = {}
    for cat in categorias:
        ag = agregados.get(cat.id, {'qtd': 0, 'total': 0.0, 'media_mes': 0.0})
        if cat.grupo not in grupos_agregados:
            grupos_agregados[cat.grupo] = {'qtd': 0, 'total': 0.0, 'media_mes': 0.0}
        grupos_agregados[cat.grupo]['qtd'] += ag['qtd']
        grupos_agregados[cat.grupo]['total'] += ag['total']
    # media_mes do grupo = total do grupo / num_meses (mesma base das categorias)
    for g in grupos_agregados:
        grupos_agregados[g]['media_mes'] = grupos_agregados[g]['total'] / num_meses

    return render_template(
        'pessoal/configuracao.html',
        categorias=categorias,
        regras=regras,
        membros=membros,
        contas=contas,
        contagem_match=contagem_match,
        agregados=agregados,
        grupos_agregados=grupos_agregados,
        num_meses=num_meses,
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
        # Invalida cache de IDs do grupo 'Desconsiderar' (grupo pode ter mudado)
        from app.pessoal.services.categorizacao_service import invalidar_cache_desconsiderar
        invalidar_cache_desconsiderar()
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


@configuracao_bp.route('/api/categorias/<int:cat_id>/vinculos', methods=['GET'])
@login_required
def vinculos_categoria(cat_id):
    """Conta vinculos da categoria em todas as tabelas que a referenciam.

    Usado pelos modais de migrar/remover categoria para preview.
    """
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    cat = db.session.get(PessoalCategoria, cat_id)
    if not cat:
        return jsonify({'sucesso': False, 'mensagem': 'Categoria nao encontrada.'}), 404

    from app.pessoal.services.migracao_service import contar_vinculos
    return jsonify({
        'sucesso': True,
        'categoria': cat.to_dict(),
        'vinculos': contar_vinculos(cat_id),
    })


@configuracao_bp.route('/api/categorias/<int:cat_id>', methods=['DELETE'])
@login_required
def excluir_categoria(cat_id):
    """Remove categoria. Se houver vinculos, exige escolha via body JSON.

    Body JSON:
        {} ou sem body -> verifica vinculos; se houver, retorna 409 com contagem.
        {"modo": "migrar", "destino_id": int} -> migra vinculos para destino e deleta.
        {"modo": "null"}                       -> seta NULL nos vinculos e deleta.
        {"modo": "direto"}                     -> deleta direto (falha se houver vinculos).
    """
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    cat = db.session.get(PessoalCategoria, cat_id)
    if not cat:
        return jsonify({'sucesso': False, 'mensagem': 'Categoria nao encontrada.'}), 404

    from app.pessoal.services.migracao_service import contar_vinculos, migrar_categoria
    vinculos = contar_vinculos(cat_id)
    tem_vinculos = any(vinculos[k] > 0 for k in ('regras', 'transacoes', 'orcamentos', 'grupos_analise'))

    dados = request.get_json(silent=True) or {}
    modo = dados.get('modo')
    destino_id = dados.get('destino_id')
    if destino_id in ('', 'null', 0):
        destino_id = None

    # Se tem vinculos e nao foi escolhido um modo, exigir escolha
    if tem_vinculos and not modo:
        return jsonify({
            'sucesso': False,
            'exige_escolha': True,
            'mensagem': 'Categoria tem vinculos — escolha migrar ou deixar sem categoria.',
            'vinculos': vinculos,
            'categoria': cat.to_dict(),
        }), 409

    try:
        # Aplicar modo escolhido (commit=False -> tudo em uma transacao com o delete)
        if modo == 'migrar':
            if destino_id is None:
                return jsonify({'sucesso': False, 'mensagem': 'Informe destino_id para modo=migrar.'}), 400
            try:
                destino_id = int(destino_id)
            except (TypeError, ValueError):
                return jsonify({'sucesso': False, 'mensagem': 'destino_id invalido.'}), 400
            migrar_categoria(cat_id, destino_id, commit=False)
        elif modo == 'null':
            if tem_vinculos:
                migrar_categoria(cat_id, None, commit=False)
        elif modo == 'direto':
            if tem_vinculos:
                return jsonify({
                    'sucesso': False,
                    'mensagem': 'Categoria tem vinculos — nao pode deletar direto.',
                    'vinculos': vinculos,
                }), 409

        db.session.delete(cat)
        db.session.commit()

        # Invalidar cache apos commit bem-sucedido
        from app.pessoal.services.categorizacao_service import invalidar_cache_desconsiderar
        invalidar_cache_desconsiderar()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Categoria "{cat.grupo} / {cat.nome}" removida.',
            'vinculos_tratados': vinculos,
        })
    except ValueError as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@configuracao_bp.route('/api/categorias/<int:origem_id>/migrar', methods=['POST'])
@login_required
def migrar_categoria_route(origem_id):
    """Migra todos os vinculos de uma categoria para outra (ou para NULL).

    Body JSON:
        {"destino_id": int|null}  - None/null => seta NULL em todos os vinculos
    """
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}
    destino_id = dados.get('destino_id')
    # normalizar: strings vazias/"null" -> None
    if destino_id in ('', 'null', 0):
        destino_id = None
    if destino_id is not None:
        try:
            destino_id = int(destino_id)
        except (TypeError, ValueError):
            return jsonify({'sucesso': False, 'mensagem': 'destino_id invalido.'}), 400

    from app.pessoal.services.migracao_service import migrar_categoria
    try:
        updates = migrar_categoria(origem_id, destino_id)
        total = updates['regras'] + updates['transacoes'] + updates['orcamentos']
        msg = f'{total} vinculos migrados.'
        if updates.get('grupos_analise_removidos'):
            msg += f' {updates["grupos_analise_removidos"]} entrada(s) N:N removidas.'
        return jsonify({'sucesso': True, 'mensagem': msg, 'updates': updates})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


# =============================================================================
# CRUD REGRAS
# =============================================================================
def _regra_payload(regra):
    """Payload enriquecido de uma regra para refresh dinamico da UI.

    Inclui metadados da categoria e match_count atualizado (0 ou preview de pendentes).
    """
    cat = db.session.get(PessoalCategoria, regra.categoria_id) if regra.categoria_id else None
    contagem = contar_matches_por_regra([regra])
    return {
        'id': regra.id,
        'padrao_historico': regra.padrao_historico,
        'tipo_regra': regra.tipo_regra,
        'categoria_id': regra.categoria_id,
        'categoria_grupo': cat.grupo if cat else None,
        'categoria_nome': cat.nome if cat else None,
        'categoria_label': f"{cat.grupo} / {cat.nome}" if cat else None,
        'cpf_cnpj_padrao': regra.cpf_cnpj_padrao,
        'valor_min': float(regra.valor_min) if regra.valor_min is not None else None,
        'valor_max': float(regra.valor_max) if regra.valor_max is not None else None,
        'vezes_usado': regra.vezes_usado or 0,
        'confianca': float(regra.confianca) if regra.confianca else 100,
        'origem': regra.origem,
        'ativo': regra.ativo,
        'match_count': contagem.get(regra.id, 0),
        'categorias_restritas_ids': regra.get_categorias_restritas(),
    }


@configuracao_bp.route('/api/regras/<int:regra_id>', methods=['GET'])
@login_required
def buscar_regra(regra_id):
    """Retorna payload enriquecido de uma regra (para refresh da UI)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403
    regra = db.session.get(PessoalRegraCategorizacao, regra_id)
    if not regra:
        return jsonify({'sucesso': False, 'mensagem': 'Regra nao encontrada.'}), 404
    return jsonify({'sucesso': True, 'regra': _regra_payload(regra)})



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

    # F1: CPF/CNPJ (opcional) — normaliza para so digitos
    cpf_cnpj_raw = (dados.get('cpf_cnpj_padrao') or '').strip()
    cpf_cnpj_padrao = ''.join(ch for ch in cpf_cnpj_raw if ch.isdigit()) or None
    if cpf_cnpj_padrao and len(cpf_cnpj_padrao) not in (11, 14):
        return jsonify({
            'sucesso': False,
            'mensagem': 'CPF/CNPJ deve ter 11 ou 14 digitos.',
        }), 400

    # F4: Range de valor (opcional)
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
    if valor_min is not None and valor_max is not None and valor_min > valor_max:
        return jsonify({
            'sucesso': False,
            'mensagem': 'valor_min nao pode ser maior que valor_max.',
        }), 400

    # Precisa ter padrao textual OU CPF/CNPJ
    if not padrao and not cpf_cnpj_padrao:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Informe padrao textual ou CPF/CNPJ.',
        }), 400

    # Normalizar padrao antes de salvar (consistencia com matching)
    if padrao:
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
            cpf_anterior = regra.cpf_cnpj_padrao
            vmin_anterior = regra.valor_min
            vmax_anterior = regra.valor_max

            # Atualizar campos
            regra.padrao_historico = padrao
            regra.tipo_regra = tipo_regra
            regra.categoria_id = categoria_id if tipo_regra == 'PADRAO' else None
            regra.set_categorias_restritas(categorias_restritas if tipo_regra == 'RELATIVO' else [])
            regra.cpf_cnpj_padrao = cpf_cnpj_padrao
            regra.valor_min = valor_min
            regra.valor_max = valor_max
            regra.atualizado_em = agora_utc_naive()

            # Detectar se precisa repropagar
            mudou_padrao = (padrao != padrao_anterior)
            mudou_categoria = (categoria_id != categoria_anterior)
            mudou_tipo = (tipo_anterior != tipo_regra)
            mudou_cpf = (cpf_cnpj_padrao != cpf_anterior)
            mudou_valor = (valor_min != (float(vmin_anterior) if vmin_anterior is not None else None)
                           or valor_max != (float(vmax_anterior) if vmax_anterior is not None else None))

            needs_repropagation = (
                (tipo_anterior == 'PADRAO' and mudou_tipo) or  # PADRAO→RELATIVO
                (tipo_regra == 'PADRAO' and (mudou_padrao or mudou_categoria or mudou_cpf or mudou_valor))
            )

            if needs_repropagation:
                afetadas = despropagar_regra(regra.id)
                # Flush pendente antes do bulk UPDATE de desvincular_manuais_da_regra:
                # despropagar_regra mexe em ORM objects (sem flush); desvincular emite
                # SQL direto com synchronize_session=False — sem flush explicito, o bulk
                # executaria contra estado pre-flush.
                if mudou_categoria and tipo_regra == 'PADRAO':
                    db.session.flush()
                    desvincular_manuais_da_regra(regra.id)
                if tipo_regra == 'PADRAO':
                    propagados_info = propagar_regra_para_pendentes(regra)
        else:
            # Nova regra
            regra = PessoalRegraCategorizacao(
                padrao_historico=padrao,
                tipo_regra=tipo_regra,
                categoria_id=categoria_id if tipo_regra == 'PADRAO' else None,
                cpf_cnpj_padrao=cpf_cnpj_padrao,
                valor_min=valor_min,
                valor_max=valor_max,
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

        resp = {'sucesso': True, 'regra': _regra_payload(regra)}
        if afetadas > 0:
            resp['afetadas'] = afetadas
        if propagados_info:
            resp['propagados'] = propagados_info['propagados']
        return jsonify(resp)

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@configuracao_bp.route('/api/regras/<int:regra_id>/transacoes', methods=['GET'])
@login_required
def transacoes_por_regra(regra_id):
    """Lista transacoes vinculadas a uma regra (regra_id = <esta>).

    Ordena por data DESC. Limita a 500 registros para evitar payloads gigantes.
    """
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    regra = db.session.get(PessoalRegraCategorizacao, regra_id)
    if not regra:
        return jsonify({'sucesso': False, 'mensagem': 'Regra nao encontrada.'}), 404

    transacoes = db.session.query(PessoalTransacao).filter_by(
        regra_id=regra_id,
    ).order_by(PessoalTransacao.data.desc(), PessoalTransacao.id.desc()).limit(500).all()

    # Load categorias atuais
    cat_ids = {t.categoria_id for t in transacoes if t.categoria_id}
    cats = {c.id: c for c in PessoalCategoria.query.filter(PessoalCategoria.id.in_(cat_ids)).all()} if cat_ids else {}

    return jsonify({
        'sucesso': True,
        'regra': regra.to_dict(),
        'total': len(transacoes),
        'transacoes': [{
            'id': t.id,
            'data': t.data.strftime('%Y-%m-%d') if t.data else None,
            'historico': t.historico,
            'descricao': t.descricao,
            'valor': float(t.valor) if t.valor is not None else None,
            'tipo': t.tipo,
            'status': t.status,
            'categoria_id': t.categoria_id,
            'categoria_label': (
                f"{cats[t.categoria_id].grupo} / {cats[t.categoria_id].nome}"
                if t.categoria_id in cats else None
            ),
            'categorizacao_auto': t.categorizacao_auto,
            'excluir_relatorio': t.excluir_relatorio,
            'divergente': t.categoria_id != regra.categoria_id,
        } for t in transacoes],
    })


@configuracao_bp.route('/api/transacoes/<int:transacao_id>/regras-aplicaveis', methods=['GET'])
@login_required
def regras_aplicaveis_transacao(transacao_id):
    """Retorna regras PADRAO ativas aplicaveis a uma transacao.

    Replica a ordem do pipeline em `categorizacao_service.categorizar_transacao`:
    1. F1 (CPF/CNPJ exato)
    2. PADRAO substring (ordenado por comprimento DESC)
    3. Fuzzy >= 85
    Marca a top-level (primeira que o pipeline aplicaria).
    """
    from rapidfuzz import fuzz
    from app.pessoal.services.aprendizado_service import _normalizar
    from app.pessoal.services.categorizacao_service import _valor_no_range

    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    t = db.session.get(PessoalTransacao, transacao_id)
    if not t:
        return jsonify({'sucesso': False, 'mensagem': 'Transacao nao encontrada.'}), 404

    historico = _normalizar(t.historico_completo or t.historico or '')

    regras_padrao = PessoalRegraCategorizacao.query.filter_by(
        tipo_regra='PADRAO', ativo=True,
    ).order_by(
        db.func.length(PessoalRegraCategorizacao.padrao_historico).desc(),
        PessoalRegraCategorizacao.confianca.desc(),
        PessoalRegraCategorizacao.vezes_usado.desc(),
    ).all()

    aplicaveis = []
    top_level_id = None

    # Layer 1 F1: CPF/CNPJ
    if t.cpf_cnpj_parte:
        for r in regras_padrao:
            if (r.cpf_cnpj_padrao and r.cpf_cnpj_padrao == t.cpf_cnpj_parte
                    and _valor_no_range(t.valor, r.valor_min, r.valor_max)):
                aplicaveis.append({'regra_id': r.id, 'layer': 'F1-CPF', 'score': 100.0})
                if top_level_id is None:
                    top_level_id = r.id

    # Layer 1: substring
    for r in regras_padrao:
        padrao_norm = _normalizar(r.padrao_historico or '')
        if (padrao_norm and padrao_norm in historico
                and _valor_no_range(t.valor, r.valor_min, r.valor_max)):
            if not any(a['regra_id'] == r.id for a in aplicaveis):
                aplicaveis.append({'regra_id': r.id, 'layer': 'PADRAO-substring', 'score': 100.0})
            if top_level_id is None:
                top_level_id = r.id

    # Layer 2: fuzzy
    for r in regras_padrao:
        padrao_norm = _normalizar(r.padrao_historico or '')
        if not padrao_norm or not _valor_no_range(t.valor, r.valor_min, r.valor_max):
            continue
        score = fuzz.token_set_ratio(padrao_norm, historico)
        if score >= 85 and not any(a['regra_id'] == r.id for a in aplicaveis):
            aplicaveis.append({'regra_id': r.id, 'layer': 'PADRAO-fuzzy', 'score': float(score)})
            # NAO altera top_level_id aqui — fuzzy e usada apenas na AUSENCIA de substring match

    # Load metadata das regras aplicaveis
    regra_ids = [a['regra_id'] for a in aplicaveis]
    regras_map = {r.id: r for r in regras_padrao if r.id in regra_ids}

    # Enrich
    out = []
    cat_ids = {regras_map[rid].categoria_id for rid in regra_ids if regras_map[rid].categoria_id}
    cats = {c.id: c for c in PessoalCategoria.query.filter(PessoalCategoria.id.in_(cat_ids)).all()} if cat_ids else {}
    for a in aplicaveis:
        r = regras_map[a['regra_id']]
        cat = cats.get(r.categoria_id) if r.categoria_id else None
        out.append({
            'regra_id': r.id,
            'padrao_historico': r.padrao_historico,
            'categoria_id': r.categoria_id,
            'categoria_label': f"{cat.grupo} / {cat.nome}" if cat else None,
            'cpf_cnpj_padrao': r.cpf_cnpj_padrao,
            'valor_min': float(r.valor_min) if r.valor_min is not None else None,
            'valor_max': float(r.valor_max) if r.valor_max is not None else None,
            'origem': r.origem,
            'vezes_usado': r.vezes_usado,
            'layer': a['layer'],
            'score': a['score'],
            'is_top_level': (r.id == top_level_id),
            'is_atual': (r.id == t.regra_id),
        })

    return jsonify({
        'sucesso': True,
        'transacao': {
            'id': t.id,
            'data': t.data.strftime('%Y-%m-%d') if t.data else None,
            'historico': t.historico,
            'descricao': t.descricao,
            'historico_completo': t.historico_completo,
            'valor': float(t.valor) if t.valor is not None else None,
            'cpf_cnpj_parte': t.cpf_cnpj_parte,
            'regra_id_atual': t.regra_id,
            'categoria_id_atual': t.categoria_id,
        },
        'top_level_regra_id': top_level_id,
        'aplicaveis': out,
    })


@configuracao_bp.route('/api/regras/<int:regra_id>/propagar', methods=['POST'])
@login_required
def propagar_regra(regra_id):
    """Propagacao FORCADA de uma regra PADRAO.

    Re-aplica a regra em TODAS as transacoes vinculadas (regra_id=<esta>), inclusive
    as que foram categorizadas manualmente por esta mesma regra, e propaga para
    pendentes que matcham o padrao.

    NAO sobrescreve regras top-level: transacoes com outra regra (regra_id != esta)
    ou categorizadas manualmente sem regra (regra_id=NULL, auto=False) sao preservadas.
    """
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    regra = db.session.get(PessoalRegraCategorizacao, regra_id)
    if not regra:
        return jsonify({'sucesso': False, 'mensagem': 'Regra nao encontrada.'}), 404
    if regra.tipo_regra != 'PADRAO':
        return jsonify({
            'sucesso': False,
            'mensagem': 'Propagacao forcada disponivel apenas para regras do tipo PADRAO.',
        }), 400
    if not regra.ativo:
        return jsonify({'sucesso': False, 'mensagem': 'Regra inativa — ative antes de propagar.'}), 400
    if not regra.categoria_id:
        return jsonify({'sucesso': False, 'mensagem': 'Regra sem categoria — salve a regra com categoria antes.'}), 400

    try:
        resultado = propagar_regra_forcado(regra)
        db.session.commit()

        partes = []
        if resultado['reatribuidas_vinculadas']:
            partes.append(f"{resultado['reatribuidas_vinculadas']} vinculadas re-atribuidas")
        if resultado['propagados_pendentes']:
            partes.append(f"{resultado['propagados_pendentes']} pendentes propagadas")
        if not partes:
            partes.append('nenhuma transacao afetada')
        protegidas = resultado['protegidas_outras_regras'] + resultado['protegidas_manuais_sem_regra']
        if protegidas:
            partes.append(f"{protegidas} preservadas (top-level)")

        return jsonify({
            'sucesso': True,
            'mensagem': 'Propagacao concluida: ' + ', '.join(partes) + '.',
            'resultado': resultado,
            'regra': _regra_payload(regra),
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@configuracao_bp.route('/api/regras/<int:regra_id>', methods=['DELETE'])
@login_required
def excluir_regra(regra_id):
    """Desativar regra — despropaga transacoes auto-categorizadas por ela antes de desativar."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    regra = db.session.get(PessoalRegraCategorizacao, regra_id)
    if not regra:
        return jsonify({'sucesso': False, 'mensagem': 'Regra nao encontrada.'}), 404

    try:
        # Despropagar transacoes que foram auto-categorizadas por esta regra (voltam a PENDENTE)
        afetadas = despropagar_regra(regra_id)
        regra.ativo = False
        regra.atualizado_em = agora_utc_naive()
        db.session.commit()
        msg = 'Regra desativada.'
        if afetadas:
            msg += f' {afetadas} transacoes voltaram para PENDENTE.'
        return jsonify({'sucesso': True, 'mensagem': msg, 'afetadas': afetadas})
    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


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


