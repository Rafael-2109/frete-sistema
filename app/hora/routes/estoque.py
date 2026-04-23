"""Rotas de Estoque HORA: KPIs, listagem chassi-a-chassi, historico de moto."""
from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for

from app.hora.decorators import require_hora_perm
from app.hora.models import HoraLoja, HoraModelo, HoraMoto
from app.hora.routes import hora_bp
from app.hora.services import estoque_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids,
    usuario_tem_acesso_a_loja,
)


@hora_bp.route('/estoque')
@require_hora_perm('estoque', 'ver')
def estoque_lista():
    permitidas = lojas_permitidas_ids()
    loja_id_str = (request.args.get('loja_id') or '').strip()
    modelo_id_str = (request.args.get('modelo_id') or '').strip()
    cor = (request.args.get('cor') or '').strip() or None

    loja_id = int(loja_id_str) if loja_id_str.isdigit() else None
    modelo_id = int(modelo_id_str) if modelo_id_str.isdigit() else None

    if loja_id and not usuario_tem_acesso_a_loja(loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.estoque_lista'))

    incluir_avariadas = request.args.get('incluir_avariadas', '1') == '1'
    incluir_faltando_peca = request.args.get('incluir_faltando_peca', '1') == '1'

    motos = estoque_service.listar_estoque(
        loja_id=loja_id,
        modelo_id=modelo_id,
        cor=cor,
        incluir_avariadas=incluir_avariadas,
        incluir_faltando_peca=incluir_faltando_peca,
        lojas_permitidas_ids=permitidas,
    )
    kpis_loja = estoque_service.kpis_estoque_por_loja(
        lojas_permitidas_ids=permitidas,
    )
    kpis_modelo = estoque_service.kpis_estoque_por_modelo(
        loja_id=loja_id,
        lojas_permitidas_ids=permitidas,
    )

    lojas_q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        if not permitidas:
            lojas = []
        else:
            lojas_q = lojas_q.filter(HoraLoja.id.in_(permitidas))
            lojas = lojas_q.order_by(HoraLoja.nome).all()
    else:
        lojas = lojas_q.order_by(HoraLoja.nome).all()

    modelos = HoraModelo.query.filter_by(ativo=True).order_by(HoraModelo.nome_modelo).all()

    return render_template(
        'hora/estoque_lista.html',
        motos=motos,
        kpis_loja=kpis_loja,
        kpis_modelo=kpis_modelo,
        lojas=lojas,
        modelos=modelos,
        filtro_loja_id=loja_id,
        filtro_modelo_id=modelo_id,
        filtro_cor=cor,
        incluir_avariadas=incluir_avariadas,
        incluir_faltando_peca=incluir_faltando_peca,
    )


@hora_bp.route('/estoque/chassi/<numero_chassi>')
@require_hora_perm('estoque', 'ver')
def estoque_chassi_detalhe(numero_chassi: str):
    chassi = numero_chassi.strip().upper()
    moto = HoraMoto.query.get_or_404(chassi)
    eventos = estoque_service.historico_chassi(chassi)
    # Se o ultimo evento esta em loja especifica, valida acesso
    if eventos:
        ult_loja = eventos[0]['loja_id']
        if ult_loja and not usuario_tem_acesso_a_loja(ult_loja):
            flash('Acesso negado a loja desse chassi.', 'danger')
            return redirect(url_for('hora.estoque_lista'))
    return render_template(
        'hora/estoque_chassi_detalhe.html',
        moto=moto,
        eventos=eventos,
    )
