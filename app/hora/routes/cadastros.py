"""Rotas de cadastro: lojas e modelos."""
from __future__ import annotations

import os

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from app.hora.decorators import require_lojas as login_required

from app import db
from app.hora.models import HoraLoja
from app.hora.routes import hora_bp
from app.hora.services import cadastro_service
from app.hora.services.receitaws_service import consultar_cnpj, ReceitaWSError
from app.hora.services.geocoding_service import geocodar_loja, GeocodingError


# ----------------------------- Lojas -----------------------------

@hora_bp.route('/lojas')
@login_required
def lojas_lista():
    lojas = cadastro_service.listar_lojas(apenas_ativas=False)
    return render_template('hora/lojas_lista.html', lojas=lojas)


@hora_bp.route('/lojas/novo', methods=['GET', 'POST'])
@login_required
def lojas_novo():
    if request.method == 'POST':
        try:
            dados_receita = None
            # Se houver payload serializado do autopreenchimento, usa.
            if request.form.get('receita_payload'):
                import json
                try:
                    raw = json.loads(request.form['receita_payload'])
                    # Converte string ISO de data_abertura de volta para date.
                    if raw.get('data_abertura'):
                        from datetime import date
                        try:
                            raw['data_abertura'] = date.fromisoformat(raw['data_abertura'])
                        except (ValueError, TypeError):
                            raw['data_abertura'] = None
                    dados_receita = raw
                except (ValueError, TypeError):
                    dados_receita = None

            cadastro_service.criar_loja(
                cnpj=request.form['cnpj'],
                nome=request.form.get('razao_social') or request.form.get('apelido') or None,
                apelido=request.form.get('apelido') or None,
                endereco=request.form.get('endereco') or None,
                cidade=request.form.get('cidade') or None,
                uf=request.form.get('uf') or None,
                dados_receita=dados_receita,
            )
            flash('Loja cadastrada com sucesso.', 'success')
            return redirect(url_for('hora.lojas_lista'))
        except ValueError as exc:
            flash(f'Erro: {exc}', 'danger')

    return render_template('hora/lojas_novo.html')


@hora_bp.route('/lojas/<int:loja_id>')
@login_required
def lojas_detalhe(loja_id: int):
    """Tela de detalhe com todas as infos da loja + mini-mapa + metadados."""
    loja = HoraLoja.query.get_or_404(loja_id)
    google_key = os.getenv('GOOGLE_MAPS_API_KEY', '').strip()

    # Estatísticas agregadas (opcional — mostra atividade da loja no módulo HORA)
    from app.hora.models import HoraRecebimento, HoraVenda, HoraMotoEvento
    stats = {
        'recebimentos_total': HoraRecebimento.query.filter_by(loja_id=loja.id).count(),
        'vendas_total': HoraVenda.query.filter_by(loja_id=loja.id).count(),
        'eventos_motos': HoraMotoEvento.query.filter_by(loja_id=loja.id).count(),
    }

    return render_template(
        'hora/lojas_detalhe.html',
        loja=loja,
        stats=stats,
        google_key=google_key,
        tem_google=bool(google_key),
    )


@hora_bp.route('/lojas/<int:loja_id>/atualizar-receita', methods=['POST'])
@login_required
def lojas_atualizar_receita(loja_id: int):
    """Re-consulta ReceitaWS e atualiza campos fiscais/endereço da loja existente."""
    from app.utils.timezone import agora_utc_naive
    loja = HoraLoja.query.get_or_404(loja_id)
    try:
        dados = consultar_cnpj(loja.cnpj)
    except ReceitaWSError as exc:
        flash(f'Erro ao consultar Receita: {exc}', 'danger')
        return redirect(url_for('hora.lojas_detalhe', loja_id=loja.id))

    loja.razao_social = dados.get('razao_social') or loja.razao_social
    loja.nome_fantasia = dados.get('nome_fantasia') or loja.nome_fantasia
    loja.situacao_cadastral = dados.get('situacao_cadastral')
    loja.data_abertura = dados.get('data_abertura')
    loja.porte = dados.get('porte')
    loja.natureza_juridica = dados.get('natureza_juridica')
    loja.atividade_principal = dados.get('atividade_principal')
    loja.logradouro = dados.get('logradouro')
    loja.numero = dados.get('numero')
    loja.complemento = dados.get('complemento')
    loja.bairro = dados.get('bairro')
    loja.cep = dados.get('cep')
    loja.cidade = dados.get('cidade') or loja.cidade
    loja.uf = dados.get('uf') or loja.uf
    loja.telefone = dados.get('telefone')
    loja.email = dados.get('email')
    loja.receitaws_consultado_em = agora_utc_naive()
    # Invalida geocode — endereço pode ter mudado
    loja.latitude = None
    loja.longitude = None
    loja.geocodado_em = None
    db.session.commit()
    flash('Dados atualizados da Receita. Geocoding invalidado — geocodifique novamente.', 'success')
    return redirect(url_for('hora.lojas_detalhe', loja_id=loja.id))


@hora_bp.route('/lojas/<int:loja_id>/toggle-ativa', methods=['POST'])
@login_required
def lojas_toggle_ativa(loja_id: int):
    """Ativa/desativa loja."""
    loja = HoraLoja.query.get_or_404(loja_id)
    loja.ativa = not loja.ativa
    db.session.commit()
    flash(f'Loja {"ativada" if loja.ativa else "desativada"}.', 'success')
    return redirect(url_for('hora.lojas_detalhe', loja_id=loja.id))


@hora_bp.route('/lojas/<int:loja_id>/editar-apelido', methods=['POST'])
@login_required
def lojas_editar_apelido(loja_id: int):
    """AJAX inline edit do apelido + campos manuais simples."""
    loja = HoraLoja.query.get_or_404(loja_id)
    apelido = (request.form.get('apelido') or '').strip() or None
    loja.apelido = apelido
    db.session.commit()
    if request.is_json or request.headers.get('Accept') == 'application/json':
        return jsonify({'ok': True, 'apelido': apelido or ''})
    flash('Apelido atualizado.', 'success')
    return redirect(url_for('hora.lojas_lista'))


@hora_bp.route('/lojas/mapa')
@login_required
def lojas_mapa():
    """Renderiza mapa com todas as lojas (Google Maps se chave; Leaflet fallback)."""
    lojas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.nome).all()
    google_key = os.getenv('GOOGLE_MAPS_API_KEY', '').strip()

    # Serializa para JSON (apenas o necessário para o JS)
    lojas_json = [
        {
            'id': l.id,
            'apelido': l.apelido or l.nome_fantasia or l.razao_social or l.nome,
            'cnpj': l.cnpj,
            'endereco': ', '.join(filter(None, [
                l.logradouro,
                l.numero,
                l.bairro,
                l.cidade,
                l.uf,
            ])),
            'lat': float(l.latitude) if l.latitude is not None else None,
            'lng': float(l.longitude) if l.longitude is not None else None,
            'telefone': l.telefone,
        }
        for l in lojas
    ]

    return render_template(
        'hora/lojas_mapa.html',
        lojas=lojas,
        lojas_json=lojas_json,
        google_key=google_key,
        tem_google=bool(google_key),
    )


@hora_bp.route('/lojas/<int:loja_id>/geocodar', methods=['POST'])
@login_required
def lojas_geocodar(loja_id: int):
    """AJAX: força geocoding da loja e retorna novas coords."""
    loja = HoraLoja.query.get_or_404(loja_id)
    forcar = request.args.get('forcar') == '1'
    try:
        coords = geocodar_loja(loja, forcar=forcar)
        if coords is None:
            return jsonify({
                'ok': False,
                'mensagem': 'Endereço insuficiente. Preencha logradouro, cidade e UF.',
            }), 400
        lat, lng = coords
        return jsonify({
            'ok': True,
            'lat': float(lat),
            'lng': float(lng),
            'provider': loja.geocoding_provider,
        })
    except GeocodingError as exc:
        return jsonify({'ok': False, 'mensagem': str(exc)}), 502


@hora_bp.route('/lojas/consultar-cnpj')
@login_required
def lojas_consultar_cnpj():
    """Endpoint AJAX: consulta ReceitaWS e retorna JSON.

    Query param: ?cnpj=XX.XXX.XXX/XXXX-XX ou dígitos.
    Retorna: {ok: bool, dados: {...} | mensagem: str}
    """
    cnpj = request.args.get('cnpj', '').strip()
    if not cnpj:
        return jsonify({'ok': False, 'mensagem': 'Informe um CNPJ.'}), 400
    try:
        dados = consultar_cnpj(cnpj)
        # Serializa data_abertura como ISO para round-trip no form.
        if dados.get('data_abertura'):
            dados['data_abertura'] = dados['data_abertura'].isoformat()
        return jsonify({'ok': True, 'dados': dados})
    except ReceitaWSError as exc:
        return jsonify({'ok': False, 'mensagem': str(exc)}), 502
    except Exception as exc:  # pragma: no cover
        import logging
        logging.exception('Erro inesperado em consultar-cnpj')
        return jsonify({'ok': False, 'mensagem': f'Erro inesperado: {exc}'}), 500


# ----------------------------- Modelos -----------------------------

@hora_bp.route('/modelos')
@login_required
def modelos_lista():
    modelos = cadastro_service.listar_modelos(apenas_ativos=False)
    return render_template('hora/modelos_lista.html', modelos=modelos)


@hora_bp.route('/modelos/novo', methods=['GET', 'POST'])
@login_required
def modelos_novo():
    if request.method == 'POST':
        try:
            cadastro_service.criar_modelo(
                nome_modelo=request.form['nome_modelo'],
                potencia_motor=request.form.get('potencia_motor') or None,
                descricao=request.form.get('descricao') or None,
            )
            flash('Modelo cadastrado com sucesso.', 'success')
            return redirect(url_for('hora.modelos_lista'))
        except ValueError as exc:
            flash(f'Erro: {exc}', 'danger')

    return render_template('hora/modelos_novo.html')
