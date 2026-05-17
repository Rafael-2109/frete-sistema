import os

from flask import jsonify, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import LojaForm
from app.motos_assai.models.loja import AssaiLoja
from app.motos_assai.services import (
    listar_lojas, criar_loja, atualizar_loja, get_loja, LojaJaExisteError,
    geocodar_loja, GeocodingError,
)


@motos_assai_bp.route('/lojas')
@login_required
@require_motos_assai
def lojas_lista():
    busca = request.args.get('q', '').strip() or None
    somente_ativas = request.args.get('ativas') == '1'
    lojas = listar_lojas(somente_ativas=somente_ativas, busca=busca)
    return render_template('motos_assai/lojas/lista.html',
                           lojas=lojas, busca=busca, somente_ativas=somente_ativas)


@motos_assai_bp.route('/lojas/nova', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def lojas_nova():
    form = LojaForm()
    if form.validate_on_submit():
        try:
            loja = criar_loja({
                'numero': form.numero.data.strip(),
                'nome': form.nome.data.strip(),
                'razao_social': form.razao_social.data.strip(),
                'cnpj': form.cnpj.data.strip(),
                'ie': form.ie.data.strip() if form.ie.data else None,
                'endereco': form.endereco.data.strip() if form.endereco.data else None,
                'bairro': form.bairro.data.strip() if form.bairro.data else None,
                'cep': form.cep.data.strip() if form.cep.data else None,
                'cidade': form.cidade.data.strip() if form.cidade.data else None,
                'uf': form.uf.data,
                'regional': form.regional.data.strip() if form.regional.data else None,
                'ativo': form.ativo.data,
            }, operador_id=current_user.id)
            flash(f'Loja {loja.numero} criada.', 'success')
            return redirect(url_for('motos_assai.lojas_detalhe', loja_id=loja.id))
        except LojaJaExisteError as e:
            flash(str(e), 'danger')
    return render_template('motos_assai/lojas/form.html', form=form, modo='nova')


@motos_assai_bp.route('/lojas/<int:loja_id>')
@login_required
@require_motos_assai
def lojas_detalhe(loja_id):
    loja = get_loja(loja_id)
    return render_template('motos_assai/lojas/detalhe.html', loja=loja)


@motos_assai_bp.route('/lojas/<int:loja_id>/editar', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def lojas_editar(loja_id):
    loja = get_loja(loja_id)
    form = LojaForm(obj=loja)
    if form.validate_on_submit():
        atualizar_loja(loja_id, {
            'nome': form.nome.data.strip(),
            'razao_social': form.razao_social.data.strip(),
            'cnpj': form.cnpj.data.strip(),
            'ie': form.ie.data.strip() if form.ie.data else None,
            'endereco': form.endereco.data.strip() if form.endereco.data else None,
            'bairro': form.bairro.data.strip() if form.bairro.data else None,
            'cep': form.cep.data.strip() if form.cep.data else None,
            'cidade': form.cidade.data.strip() if form.cidade.data else None,
            'uf': form.uf.data,
            'regional': form.regional.data.strip() if form.regional.data else None,
            'ativo': form.ativo.data,
        }, operador_id=current_user.id)
        flash(f'Loja {loja.numero} atualizada.', 'success')
        return redirect(url_for('motos_assai.lojas_detalhe', loja_id=loja_id))
    return render_template('motos_assai/lojas/form.html', form=form, loja=loja, modo='editar')


@motos_assai_bp.route('/lojas/mapa')
@login_required
@require_motos_assai
def lojas_mapa():
    """Renderiza mapa com todas as lojas (Google Maps se chave; Leaflet fallback)."""
    lojas = AssaiLoja.query.filter_by(ativo=True).order_by(AssaiLoja.nome).all()
    google_key = os.getenv('GOOGLE_MAPS_API_KEY', '').strip()

    lojas_json = [
        {
            'id': l.id,
            'numero': l.numero,
            'apelido': l.nome,
            'cnpj': l.cnpj,
            'endereco': ', '.join(filter(None, [
                l.endereco,
                l.bairro,
                l.cidade,
                l.uf,
            ])),
            'lat': float(l.latitude) if l.latitude is not None else None,
            'lng': float(l.longitude) if l.longitude is not None else None,
            'regional': l.regional,
        }
        for l in lojas
    ]

    return render_template(
        'motos_assai/lojas/mapa.html',
        lojas=lojas,
        lojas_json=lojas_json,
        google_key=google_key,
        tem_google=bool(google_key),
    )


@motos_assai_bp.route('/lojas/<int:loja_id>/geocodar', methods=['POST'])
@login_required
@require_motos_assai
def lojas_geocodar(loja_id: int):
    """AJAX: forca geocoding da loja e retorna novas coords."""
    loja = AssaiLoja.query.get_or_404(loja_id)
    forcar = request.args.get('forcar') == '1'
    try:
        coords = geocodar_loja(loja, forcar=forcar)
        if coords is None:
            return jsonify({
                'ok': False,
                'error': 'Endereco insuficiente. Preencha endereco, cidade e UF.',
            }), 400
        lat, lng = coords
        return jsonify({
            'ok': True,
            'lat': float(lat),
            'lng': float(lng),
            'provider': loja.geocoding_provider,
        })
    except GeocodingError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 502
