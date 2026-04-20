"""Rotas de orcamento — configuracao de limites mensais por categoria."""
from datetime import date

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.pessoal import pode_acessar_pessoal
from app.pessoal.models import (
    PessoalOrcamento, PessoalCategoria, PessoalTransacao,
)
from app.utils.timezone import agora_utc_naive

orcamento_bp = Blueprint('pessoal_orcamento', __name__)

# Grupos excluidos do orcamento (nao sao despesas)
GRUPOS_EXCLUIDOS = {'Receitas'}


def _parse_ano_mes(mes_str):
    """Converte 'YYYY-MM' para date(YYYY, MM, 1). Fallback: mes atual."""
    try:
        partes = mes_str.split('-')
        return date(int(partes[0]), int(partes[1]), 1)
    except (ValueError, IndexError, AttributeError):
        hoje = date.today()
        return date(hoje.year, hoje.month, 1)


@orcamento_bp.route('/orcamento')
@login_required
def index():
    """Pagina de configuracao de orcamento mensal."""
    if not pode_acessar_pessoal(current_user):
        return 'Acesso restrito.', 403

    return render_template('pessoal/orcamento.html')


@orcamento_bp.route('/api/orcamento', methods=['GET'])
@login_required
def obter_orcamento():
    """Retorna orcamento do mes + gastos atuais e do mes anterior para contexto."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    ano_mes = _parse_ano_mes(request.args.get('mes'))

    # Mes anterior
    if ano_mes.month == 1:
        mes_anterior = date(ano_mes.year - 1, 12, 1)
    else:
        mes_anterior = date(ano_mes.year, ano_mes.month - 1, 1)

    # Proximo mes (para range de datas)
    if ano_mes.month == 12:
        proximo_mes = date(ano_mes.year + 1, 1, 1)
    else:
        proximo_mes = date(ano_mes.year, ano_mes.month + 1, 1)

    # Proximo do anterior
    proximo_anterior = ano_mes  # o proximo do anterior e o atual

    # Orcamentos do mes
    orcamentos = PessoalOrcamento.query.filter_by(ano_mes=ano_mes).all()
    limite_global = None
    limites_categoria = {}
    for orc in orcamentos:
        if orc.categoria_id is None:
            limite_global = float(orc.valor_limite)
        else:
            limites_categoria[orc.categoria_id] = float(orc.valor_limite)

    # Gastos do mes atual por categoria
    gastos_atual = dict(
        db.session.query(
            PessoalTransacao.categoria_id,
            func.sum(PessoalTransacao.valor),
        ).filter(
            PessoalTransacao.tipo == 'debito',
            PessoalTransacao.excluir_relatorio.is_(False),
            PessoalTransacao.data >= ano_mes,
            PessoalTransacao.data < proximo_mes,
        ).group_by(PessoalTransacao.categoria_id).all()
    )

    # Gastos do mes anterior por categoria
    gastos_anterior = dict(
        db.session.query(
            PessoalTransacao.categoria_id,
            func.sum(PessoalTransacao.valor),
        ).filter(
            PessoalTransacao.tipo == 'debito',
            PessoalTransacao.excluir_relatorio.is_(False),
            PessoalTransacao.data >= mes_anterior,
            PessoalTransacao.data < proximo_anterior,
        ).group_by(PessoalTransacao.categoria_id).all()
    )

    # Categorias ativas (excluindo grupo Receitas)
    categorias = PessoalCategoria.query.filter(
        PessoalCategoria.ativa.is_(True),
        ~PessoalCategoria.grupo.in_(GRUPOS_EXCLUIDOS),
    ).order_by(PessoalCategoria.grupo, PessoalCategoria.nome).all()

    categorias_payload = [{
        'id': cat.id,
        'nome': cat.nome,
        'grupo': cat.grupo,
        'icone': cat.icone,
        'gasto_atual': float(gastos_atual.get(cat.id, 0) or 0),
        'gasto_anterior': float(gastos_anterior.get(cat.id, 0) or 0),
        'limite': limites_categoria.get(cat.id),
    } for cat in categorias]

    # Adiciona linha sintetica "A definir" (despesas sem categoria)
    gasto_atual_sem_cat = float(gastos_atual.get(None, 0) or 0)
    gasto_anterior_sem_cat = float(gastos_anterior.get(None, 0) or 0)
    if gasto_atual_sem_cat > 0 or gasto_anterior_sem_cat > 0:
        categorias_payload.append({
            'id': None,
            'nome': 'A definir',
            'grupo': 'A definir',
            'icone': 'fa-question-circle',
            'gasto_atual': gasto_atual_sem_cat,
            'gasto_anterior': gasto_anterior_sem_cat,
            'limite': None,
        })

    resultado = {
        'sucesso': True,
        'ano_mes': ano_mes.isoformat(),
        'limite_global': limite_global,
        'categorias': categorias_payload,
    }

    return jsonify(resultado)


@orcamento_bp.route('/api/orcamento', methods=['POST'])
@login_required
def salvar_orcamento():
    """Salva orcamento do mes (batch upsert: global + categorias)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json()
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'Dados invalidos.'}), 400

    ano_mes = _parse_ano_mes(dados.get('ano_mes'))
    limite_global = dados.get('limite_global')
    limites = dados.get('limites', [])  # [{categoria_id, valor_limite}, ...]

    try:
        agora = agora_utc_naive()

        # Upsert limite global
        if limite_global is not None and limite_global != '' and float(limite_global) > 0:
            orc_global = PessoalOrcamento.query.filter_by(
                ano_mes=ano_mes, categoria_id=None,
            ).first()
            if orc_global:
                orc_global.valor_limite = float(limite_global)
                orc_global.atualizado_em = agora
            else:
                db.session.add(PessoalOrcamento(
                    ano_mes=ano_mes, categoria_id=None,
                    valor_limite=float(limite_global),
                ))
        else:
            # Remover limite global se vazio
            PessoalOrcamento.query.filter_by(
                ano_mes=ano_mes, categoria_id=None,
            ).delete()

        # Upsert limites por categoria
        for item in limites:
            cat_id = item.get('categoria_id')
            valor = item.get('valor_limite')

            if not cat_id:
                continue

            if valor is not None and valor != '' and float(valor) > 0:
                orc = PessoalOrcamento.query.filter_by(
                    ano_mes=ano_mes, categoria_id=cat_id,
                ).first()
                if orc:
                    orc.valor_limite = float(valor)
                    orc.atualizado_em = agora
                else:
                    db.session.add(PessoalOrcamento(
                        ano_mes=ano_mes, categoria_id=cat_id,
                        valor_limite=float(valor),
                    ))
            else:
                # Remover limite se vazio
                PessoalOrcamento.query.filter_by(
                    ano_mes=ano_mes, categoria_id=cat_id,
                ).delete()

        db.session.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Orcamento salvo com sucesso.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@orcamento_bp.route('/api/orcamento/copiar', methods=['POST'])
@login_required
def copiar_orcamento():
    """Copia orcamento de um mes para outro."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json()
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'Dados invalidos.'}), 400

    mes_origem = _parse_ano_mes(dados.get('mes_origem'))
    mes_destino = _parse_ano_mes(dados.get('mes_destino'))

    if mes_origem == mes_destino:
        return jsonify({'sucesso': False, 'mensagem': 'Mes origem e destino iguais.'}), 400

    try:
        orcamentos_origem = PessoalOrcamento.query.filter_by(ano_mes=mes_origem).all()

        if not orcamentos_origem:
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum orcamento no mes de origem.'}), 404

        copiados = 0
        for orc in orcamentos_origem:
            # Verificar se ja existe no destino
            existente = PessoalOrcamento.query.filter_by(
                ano_mes=mes_destino, categoria_id=orc.categoria_id,
            ).first()

            if existente:
                existente.valor_limite = orc.valor_limite
                existente.atualizado_em = agora_utc_naive()
            else:
                db.session.add(PessoalOrcamento(
                    ano_mes=mes_destino,
                    categoria_id=orc.categoria_id,
                    valor_limite=orc.valor_limite,
                ))
            copiados += 1

        db.session.commit()
        return jsonify({
            'sucesso': True,
            'mensagem': f'{copiados} limites copiados de {mes_origem.strftime("%m/%Y")} para {mes_destino.strftime("%m/%Y")}.',
            'copiados': copiados,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500
