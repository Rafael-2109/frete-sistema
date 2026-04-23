"""Rotas de Estoque HORA: KPIs, listagem chassi-a-chassi, rastreamento de moto."""
from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for

from app import db
from app.hora.decorators import require_hora_perm
from app.hora.models import HoraLoja, HoraMoto
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
    incluir_fora_estoque = request.args.get('incluir_fora_estoque', '0') == '1'

    motos = estoque_service.listar_estoque(
        loja_id=loja_id,
        modelo_id=modelo_id,
        cor=cor,
        incluir_avariadas=incluir_avariadas,
        incluir_faltando_peca=incluir_faltando_peca,
        incluir_fora_estoque=incluir_fora_estoque,
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

    opcoes = estoque_service.opcoes_filtro_estoque(lojas_permitidas_ids=permitidas)

    return render_template(
        'hora/estoque_lista.html',
        motos=motos,
        kpis_loja=kpis_loja,
        kpis_modelo=kpis_modelo,
        lojas=lojas,
        modelos=opcoes['modelos'],
        cores=opcoes['cores'],
        filtro_loja_id=loja_id,
        filtro_modelo_id=modelo_id,
        filtro_cor=cor,
        incluir_avariadas=incluir_avariadas,
        incluir_faltando_peca=incluir_faltando_peca,
        incluir_fora_estoque=incluir_fora_estoque,
    )


@hora_bp.route('/estoque/chassi/<numero_chassi>')
@require_hora_perm('estoque', 'ver')
def estoque_chassi_detalhe(numero_chassi: str):
    from app.hora.models import HoraMotoEvento

    chassi = numero_chassi.strip().upper()
    moto = HoraMoto.query.get_or_404(chassi)

    rastreio = estoque_service.rastreamento_completo(chassi)

    # Autorizacao: usuario deve ter acesso a ALGUMA loja pela qual este chassi
    # ja passou. Admin (lojas_permitidas_ids() is None) sempre passa.
    permitidas = lojas_permitidas_ids()
    if permitidas is not None:
        if not permitidas:
            flash('Sem acesso a nenhuma loja.', 'danger')
            return redirect(url_for('hora.estoque_lista'))
        tem_vinculo = (
            db.session.query(HoraMotoEvento.id)
            .filter(
                HoraMotoEvento.numero_chassi == chassi,
                HoraMotoEvento.loja_id.in_(permitidas),
            )
            .first()
        )
        if not tem_vinculo:
            flash('Acesso negado a esse chassi.', 'danger')
            return redirect(url_for('hora.estoque_lista'))

    return render_template(
        'hora/estoque_chassi_detalhe.html',
        moto=moto,
        rastreio=rastreio,
    )
