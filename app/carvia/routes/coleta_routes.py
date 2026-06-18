"""Rotas das Coletas CarVia ("papel de pao") — stream 3 do redesign.

CRUD do cabecalho + linhas (NFs rascunho), vinculo a NF real (com sugestao por numero),
marcar coletada (cria despesa a conciliar), cancelar/reabrir. Toda a regra vive no
CarviaColetaService; aqui so HTTP + flash + CSRF global.
"""
import logging
from datetime import date

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def _parse_decimal(valor_str):
    """Converte entrada monetaria BR/US para float; '' -> None.

    Regras (evita o bug "1.500" -> 1.5):
    - virgula presente  -> virgula e o decimal; pontos sao milhar  ("1.500,00" -> 1500.0)
    - so ponto, 1 ocorrencia, exatamente 2 casas depois -> decimal  ("10.50"   -> 10.5)
    - demais casos com ponto -> pontos sao separador de milhar       ("1.500"   -> 1500.0)
    """
    valor_str = (valor_str or '').strip()
    if not valor_str:
        return None
    if ',' in valor_str:
        return float(valor_str.replace('.', '').replace(',', '.'))
    if '.' in valor_str:
        if valor_str.count('.') == 1 and len(valor_str.rsplit('.', 1)[1]) == 2:
            return float(valor_str)            # decimal real: 10.50
        return float(valor_str.replace('.', ''))  # milhar BR: 1.500 / 1.234.567
    return float(valor_str)


def _parse_int(valor_str):
    valor_str = (valor_str or '').strip()
    return int(valor_str) if valor_str.isdigit() else None


def _parse_date(valor_str):
    valor_str = (valor_str or '').strip()
    return date.fromisoformat(valor_str) if valor_str else None


def register_coleta_routes(bp):

    def _guard():
        """Acesso CarVia completo (CRUD de coletas, valores)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return False
        return True

    def _guard_recebimento():
        """Acesso ao recebimento por chassi (sistema_carvia OU flag dedicada de operador)."""
        return bool(getattr(current_user, 'pode_acessar_recebimento_carvia', lambda: False)())

    # ----------------------------------------------------------------- listar
    @bp.route('/coletas')  # type: ignore
    @login_required
    def listar_coletas():  # type: ignore
        if not _guard():
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))
        from app.carvia.models.coleta import CarviaColeta

        page = request.args.get('page', 1, type=int)
        status_filtro = request.args.get('status', '')
        local_filtro = request.args.get('local_cd', '')
        busca = request.args.get('busca', '')

        query = CarviaColeta.query
        if status_filtro:
            query = query.filter(CarviaColeta.status == status_filtro)
        if local_filtro:
            query = query.filter(CarviaColeta.local_cd == local_filtro)
        if busca:
            like = f'%{busca}%'
            query = query.filter(db.or_(
                CarviaColeta.contratado_nome.ilike(like),
                CarviaColeta.placa.ilike(like),
                CarviaColeta.observacoes.ilike(like),
            ))
        paginacao = query.order_by(CarviaColeta.criado_em.desc().nullslast(),
                                   CarviaColeta.id.desc()).paginate(page=page, per_page=25, error_out=False)

        from app.carvia.models.coleta import COLETA_STATUSES
        from app.utils.local_cd import LOCAL_CD_CHOICES
        return render_template(
            'carvia/coletas/listar.html',
            coletas=paginacao.items, paginacao=paginacao,
            status_filtro=status_filtro, local_filtro=local_filtro, busca=busca,
            statuses=COLETA_STATUSES, local_cd_choices=LOCAL_CD_CHOICES,
        )

    # ----------------------------------------------------------------- criar
    @bp.route('/coletas/criar', methods=['GET', 'POST'])  # type: ignore
    @login_required
    def criar_coleta():  # type: ignore
        if not _guard():
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))
        from app.carvia.services.documentos.coleta_service import CarviaColetaService, ColetaError
        from app.utils.local_cd import LOCAL_CD_CHOICES

        if request.method == 'POST':
            try:
                transp = request.form.get('transportadora_id', type=int)
                coleta = CarviaColetaService.criar_coleta(
                    contratado_nome=request.form.get('contratado_nome'),
                    transportadora_id=transp or None,
                    placa=request.form.get('placa'),
                    valor_coleta=_parse_decimal(request.form.get('valor_coleta')),
                    local_cd=request.form.get('local_cd'),
                    data_prevista=_parse_date(request.form.get('data_prevista')),
                    data_prevista_chegada=_parse_date(request.form.get('data_prevista_chegada')),
                    observacoes=request.form.get('observacoes'),
                    usuario=current_user.email,
                )
                db.session.commit()
                flash(f'Coleta {coleta.numero_coleta} criada. Adicione as NFs (papel de pao).', 'success')
                return redirect(url_for('carvia.detalhe_coleta', coleta_id=coleta.id))
            except (ColetaError, ValueError) as e:
                db.session.rollback()
                flash(f'Dados invalidos: {e}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f'Erro ao criar coleta: {e}')
                flash(f'Erro: {e}', 'danger')

        return render_template('carvia/coletas/criar.html',
                               transportadoras=_transportadoras(), local_cd_choices=LOCAL_CD_CHOICES)

    # ---------------------------------------------------------------- detalhe
    @bp.route('/coletas/<int:coleta_id>')  # type: ignore
    @login_required
    def detalhe_coleta(coleta_id):  # type: ignore
        if not _guard():
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))
        from app.carvia.models.coleta import CarviaColeta
        from app.utils.local_cd import LOCAL_CD_CHOICES
        coleta = db.session.get(CarviaColeta, coleta_id)
        if coleta is None:
            flash('Coleta nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_coletas'))
        return render_template('carvia/coletas/detalhe.html',
                               coleta=coleta, linhas=coleta.nfs.all(),
                               transportadoras=_transportadoras(), local_cd_choices=LOCAL_CD_CHOICES)

    @bp.route('/coletas/<int:coleta_id>/editar', methods=['POST'])  # type: ignore
    @login_required
    def editar_coleta(coleta_id):  # type: ignore
        return _acao_coleta(coleta_id, _editar_header)

    @bp.route('/coletas/<int:coleta_id>/coletar', methods=['POST'])  # type: ignore
    @login_required
    def coletar_coleta(coleta_id):  # type: ignore
        return _acao_coleta(coleta_id, lambda c, svc: (
            svc.marcar_coletada(c, usuario=current_user.email),
            'Coleta marcada como coletada — despesa gerada para conciliacao.'))

    @bp.route('/coletas/<int:coleta_id>/cancelar', methods=['POST'])  # type: ignore
    @login_required
    def cancelar_coleta(coleta_id):  # type: ignore
        return _acao_coleta(coleta_id, lambda c, svc: (
            svc.cancelar_coleta(c, usuario=current_user.email), 'Coleta cancelada.'))

    @bp.route('/coletas/<int:coleta_id>/reabrir', methods=['POST'])  # type: ignore
    @login_required
    def reabrir_coleta(coleta_id):  # type: ignore
        return _acao_coleta(coleta_id, lambda c, svc: (svc.reabrir(c), 'Coleta reaberta (RASCUNHO).'))

    @bp.route('/coletas/<int:coleta_id>/vincular-lote', methods=['POST'])  # type: ignore
    @login_required
    def vincular_lote_coleta(coleta_id):  # type: ignore
        """Vincula em lote todas as linhas sem vinculo que tenham 1 unica NF real elegivel."""
        def _fn(c, svc):
            vinculadas = svc.vincular_lote(c)
            n = len(vinculadas)
            return (vinculadas, f'{n} NF(s) vinculada(s) automaticamente.' if n
                    else 'Nenhuma NF com match unico para vincular.')
        return _acao_coleta(coleta_id, _fn)

    # ------------------------------------------------------------------ linhas
    @bp.route('/coletas/<int:coleta_id>/linhas', methods=['POST'])  # type: ignore
    @login_required
    def adicionar_linha(coleta_id):  # type: ignore
        if not _guard():
            return _negado()
        from app.carvia.models.coleta import CarviaColeta
        from app.carvia.services.documentos.coleta_service import CarviaColetaService, ColetaError
        coleta = db.session.get(CarviaColeta, coleta_id)
        if coleta is None:
            flash('Coleta nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_coletas'))
        try:
            linha = CarviaColetaService.adicionar_linha(
                coleta,
                numero_nf=request.form.get('numero_nf'),
                nome_cliente_rascunho=request.form.get('nome_cliente_rascunho'),
                cidade_destino=request.form.get('cidade_destino'),
                uf=request.form.get('uf'),
                qtd_motos=_parse_int(request.form.get('qtd_motos')),
                valor_frete=_parse_decimal(request.form.get('valor_frete')),
                vendedor=request.form.get('vendedor'),
                transportadora_embarque=request.form.get('transportadora_embarque'),
                carvia_nf_id=request.form.get('carvia_nf_id', type=int),
                auto_vincular=True,
            )
            db.session.commit()
            flash('NF vinculada e adicionada a coleta.' if linha.carvia_nf_id
                  else 'NF adicionada a coleta.', 'success')
        except (ColetaError, ValueError) as e:
            db.session.rollback()
            flash(str(e), 'warning')
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erro ao adicionar linha: {e}')
            flash(f'Erro: {e}', 'danger')
        return redirect(url_for('carvia.detalhe_coleta', coleta_id=coleta_id))

    @bp.route('/coletas/linhas/<int:linha_id>/editar', methods=['POST'])  # type: ignore
    @login_required
    def editar_linha(linha_id):  # type: ignore
        return _acao_linha(linha_id, lambda ln, svc: (svc.editar_linha(
            ln,
            numero_nf=request.form.get('numero_nf'),
            nome_cliente_rascunho=request.form.get('nome_cliente_rascunho'),
            cidade_destino=request.form.get('cidade_destino'),
            uf=request.form.get('uf'),
            qtd_motos=_parse_int(request.form.get('qtd_motos')),
            valor_frete=_parse_decimal(request.form.get('valor_frete')),
            vendedor=request.form.get('vendedor'),
            transportadora_embarque=request.form.get('transportadora_embarque'),
            auto_vincular=True,
        ), 'Linha atualizada.'))

    @bp.route('/coletas/linhas/<int:linha_id>/remover', methods=['POST'])  # type: ignore
    @login_required
    def remover_linha(linha_id):  # type: ignore
        return _acao_linha(linha_id, lambda ln, svc: (svc.remover_linha(ln), 'Linha removida.'))

    @bp.route('/coletas/linhas/<int:linha_id>/vincular', methods=['POST'])  # type: ignore
    @login_required
    def vincular_linha(linha_id):  # type: ignore
        nf_id = request.form.get('carvia_nf_id', type=int)
        return _acao_linha(linha_id, lambda ln, svc: (
            svc.vincular_nf(ln, nf_id), 'NF vinculada — dados reais consolidados.'))

    @bp.route('/coletas/linhas/<int:linha_id>/desvincular', methods=['POST'])  # type: ignore
    @login_required
    def desvincular_linha(linha_id):  # type: ignore
        return _acao_linha(linha_id, lambda ln, svc: (svc.desvincular_nf(ln), 'NF desvinculada.'))

    @bp.route('/coletas/linhas/<int:linha_id>/sugerir-nf')  # type: ignore
    @login_required
    def sugerir_nf(linha_id):  # type: ignore
        """AJAX: candidatas de CarviaNf por numero_nf normalizado."""
        if not _guard():
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        from app.carvia.models.coleta import CarviaColetaNf
        from app.carvia.services.documentos.coleta_service import CarviaColetaService
        linha = db.session.get(CarviaColetaNf, linha_id)
        if linha is None:
            return jsonify({'success': False, 'message': 'Linha nao encontrada'}), 404
        nfs = CarviaColetaService.sugerir_nf(linha)
        return jsonify({'success': True, 'sugestoes': [
            {'id': nf.id, 'numero_nf': nf.numero_nf,
             'nome_destinatario': nf.nome_destinatario,
             'cnpj_destinatario': nf.cnpj_destinatario,
             'data_emissao': nf.data_emissao.isoformat() if nf.data_emissao else None,
             'valor_total': float(nf.valor_total) if nf.valor_total else None}
            for nf in nfs]})

    @bp.route('/coletas/lookup-nf')  # type: ignore
    @login_required
    def lookup_nf_coleta():  # type: ignore
        """AJAX: estado do match para um numero de NF (preview dinamico ao digitar).

        Retorna {success, status: unico|ambiguo|nenhum, nf?, total?} — usado pelo form de
        adicionar linha para antecipar o vinculo + preencher cliente/cidade/UF.
        """
        if not _guard():
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        from app.carvia.services.documentos.coleta_service import CarviaColetaService
        resultado = CarviaColetaService.lookup_nf(request.args.get('numero'))
        return jsonify({'success': True, **resultado})

    # ------------------------------------------------------- recebimento chassi
    @bp.route('/coletas/recebimento')  # type: ignore
    @login_required
    def listar_recebimentos():  # type: ignore
        """Lista de coletas para o operador de recebimento (sem valores). Acesso por
        sistema_carvia OU pela flag dedicada acesso_recebimento_carvia."""
        if not _guard_recebimento():
            return _negado()
        from app.carvia.models.coleta import CarviaColeta, COLETA_STATUS_CANCELADA
        from app.carvia.services.documentos.coleta_recebimento_service import CarviaColetaRecebimentoService
        from app.utils.local_cd import LOCAL_CD_CHOICES
        page = request.args.get('page', 1, type=int)
        local_filtro = request.args.get('local_cd', '')
        busca = request.args.get('busca', '')
        query = CarviaColeta.query.filter(CarviaColeta.status != COLETA_STATUS_CANCELADA)
        if local_filtro:
            query = query.filter(CarviaColeta.local_cd == local_filtro)
        if busca:
            like = f'%{busca}%'
            query = query.filter(db.or_(
                CarviaColeta.contratado_nome.ilike(like), CarviaColeta.placa.ilike(like)))
        paginacao = query.order_by(CarviaColeta.criado_em.desc().nullslast(),
                                   CarviaColeta.id.desc()).paginate(page=page, per_page=25, error_out=False)
        # status de recebimento por coleta (para badge na lista)
        receb_status = {}
        for c in paginacao.items:
            r = CarviaColetaRecebimentoService._get_recebimento(c)
            receb_status[c.id] = r.status if r else None
        return render_template(
            'carvia/coletas/recebimento_lista.html',
            coletas=paginacao.items, paginacao=paginacao, receb_status=receb_status,
            local_filtro=local_filtro, busca=busca, local_cd_choices=LOCAL_CD_CHOICES,
        )

    @bp.route('/coletas/<int:coleta_id>/recebimento')  # type: ignore
    @login_required
    def recebimento_coleta(coleta_id):  # type: ignore
        if not _guard_recebimento():
            return _negado()
        from app.carvia.models.coleta import CarviaColeta
        from app.carvia.services.documentos.coleta_recebimento_service import CarviaColetaRecebimentoService
        coleta = db.session.get(CarviaColeta, coleta_id)
        if coleta is None:
            flash('Coleta nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_recebimentos'))
        receb = CarviaColetaRecebimentoService._get_recebimento(coleta)
        chassis = receb.chassis.all() if receb else []
        resumo = CarviaColetaRecebimentoService.resumo_por_nf(coleta)
        # operador so-recebimento (sem CarVia completo) volta para a lista de recebimento,
        # nunca para o detalhe da coleta (que expoe valores).
        so_recebimento = not getattr(current_user, 'sistema_carvia', False)
        return render_template('carvia/coletas/recebimento.html',
                               coleta=coleta, recebimento=receb, chassis=chassis, resumo_nf=resumo,
                               so_recebimento=so_recebimento)

    @bp.route('/coletas/<int:coleta_id>/recebimento/chassis-esperados')  # type: ignore
    @login_required
    def chassis_esperados(coleta_id):  # type: ignore
        """AJAX: autocomplete de chassi (esperados ainda nao conferidos)."""
        if not _guard_recebimento():
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        from app.carvia.models.coleta import CarviaColeta
        from app.carvia.services.documentos.coleta_recebimento_service import CarviaColetaRecebimentoService
        coleta = db.session.get(CarviaColeta, coleta_id)
        if coleta is None:
            return jsonify({'success': False, 'message': 'Coleta nao encontrada'}), 404
        sugestoes = CarviaColetaRecebimentoService.chassis_esperados(
            coleta, q=request.args.get('q'))
        return jsonify({'success': True, 'sugestoes': sugestoes})

    @bp.route('/coletas/<int:coleta_id>/recebimento/conferir', methods=['POST'])  # type: ignore
    @login_required
    def conferir_chassi(coleta_id):  # type: ignore
        """AJAX: confere 1 chassi (multipart: chassi, modelo, qr_code_lido, foto opcional)."""
        if not _guard_recebimento():
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        from app.carvia.models.coleta import CarviaColeta
        from app.carvia.services.documentos.coleta_recebimento_service import (
            CarviaColetaRecebimentoService, RecebimentoError)
        coleta = db.session.get(CarviaColeta, coleta_id)
        if coleta is None:
            return jsonify({'success': False, 'message': 'Coleta nao encontrada'}), 404
        chassi = (request.form.get('chassi') or '').strip()
        if not chassi:
            return jsonify({'success': False, 'message': 'Chassi vazio'}), 400
        # Foto SEMPRE opcional
        foto_key = None
        foto = request.files.get('foto')
        if foto and foto.filename:
            try:
                from app.utils.file_storage import get_file_storage
                foto_key = get_file_storage().save_file(
                    foto, f'carvia/recebimento/{coleta_id}',
                    allowed_extensions=['jpg', 'jpeg', 'png', 'webp', 'heic', 'heif'])
            except Exception as e:
                logger.warning(f'Foto recebimento nao salva: {e}')
        try:
            linha = CarviaColetaRecebimentoService.conferir_chassi(
                coleta, chassi,
                modelo=request.form.get('modelo'),
                qr_code_lido=request.form.get('qr_code_lido') in ('1', 'true', 'True', 'on'),
                foto_s3_key=foto_key, usuario=current_user.email)
            db.session.commit()
            return jsonify({
                'success': True,
                'chassi': {'id': linha.id, 'chassi': linha.chassi, 'modelo': linha.modelo,
                           'status': linha.status, 'qr_code_lido': linha.qr_code_lido,
                           'tem_foto': bool(linha.foto_s3_key)},
                'resumo_nf': CarviaColetaRecebimentoService.resumo_por_nf(coleta),
            })
        except RecebimentoError as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erro ao conferir chassi: {e}')
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/coletas/recebimento/chassi/<int:linha_id>/remover', methods=['POST'])  # type: ignore
    @login_required
    def remover_chassi(linha_id):  # type: ignore
        if not _guard_recebimento():
            return _negado()
        from app.carvia.models.coleta_recebimento import CarviaColetaRecebimentoChassi
        from app.carvia.services.documentos.coleta_recebimento_service import (
            CarviaColetaRecebimentoService, RecebimentoError)
        linha = db.session.get(CarviaColetaRecebimentoChassi, linha_id)
        if linha is None:
            flash('Chassi nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_coletas'))
        coleta_id = linha.recebimento.coleta_id
        try:
            CarviaColetaRecebimentoService.remover_chassi(linha)
            db.session.commit()
            flash('Chassi removido.', 'success')
        except RecebimentoError as e:
            db.session.rollback()
            flash(str(e), 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')
        return redirect(url_for('carvia.recebimento_coleta', coleta_id=coleta_id))

    @bp.route('/coletas/<int:coleta_id>/recebimento/finalizar', methods=['POST'])  # type: ignore
    @login_required
    def finalizar_recebimento(coleta_id):  # type: ignore
        return _acao_recebimento(coleta_id, lambda c, svc: (
            svc.finalizar(c, usuario=current_user.email), 'Recebimento finalizado.'))

    @bp.route('/coletas/<int:coleta_id>/recebimento/reabrir', methods=['POST'])  # type: ignore
    @login_required
    def reabrir_recebimento(coleta_id):  # type: ignore
        return _acao_recebimento(coleta_id, lambda c, svc: (svc.reabrir(c), 'Recebimento reaberto.'))

    def _acao_recebimento(coleta_id, fn):
        if not _guard_recebimento():
            return _negado()
        from app.carvia.models.coleta import CarviaColeta
        from app.carvia.services.documentos.coleta_recebimento_service import (
            CarviaColetaRecebimentoService, RecebimentoError)
        coleta = db.session.get(CarviaColeta, coleta_id)
        if coleta is None:
            flash('Coleta nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_coletas'))
        try:
            res = fn(coleta, CarviaColetaRecebimentoService)
            msg = res[1] if isinstance(res, tuple) and len(res) > 1 else 'Operacao concluida.'
            db.session.commit()
            flash(msg, 'success')
        except (RecebimentoError, ValueError) as e:
            db.session.rollback()
            flash(str(e), 'warning')
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erro no recebimento {coleta_id}: {e}')
            flash(f'Erro: {e}', 'danger')
        return redirect(url_for('carvia.recebimento_coleta', coleta_id=coleta_id))

    # ---------------------------------------------------------------- helpers
    def _transportadoras():
        from app.transportadoras.models import Transportadora
        return Transportadora.query.filter_by(ativo=True).order_by(Transportadora.razao_social).all()

    def _negado():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))

    def _editar_header(coleta, svc):
        transp = request.form.get('transportadora_id', type=int)
        svc.editar_coleta(
            coleta,
            contratado_nome=request.form.get('contratado_nome'),
            transportadora_id=transp or None,
            placa=request.form.get('placa'),
            valor_coleta=_parse_decimal(request.form.get('valor_coleta')),
            local_cd=request.form.get('local_cd'),
            data_prevista=_parse_date(request.form.get('data_prevista')),
            data_prevista_chegada=_parse_date(request.form.get('data_prevista_chegada')),
            observacoes=request.form.get('observacoes'),
        )
        return (coleta, 'Coleta atualizada.')

    def _acao_coleta(coleta_id, fn):
        if not _guard():
            return _negado()
        from app.carvia.models.coleta import CarviaColeta
        from app.carvia.services.documentos.coleta_service import CarviaColetaService, ColetaError
        coleta = db.session.get(CarviaColeta, coleta_id)
        if coleta is None:
            flash('Coleta nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_coletas'))
        try:
            res = fn(coleta, CarviaColetaService)
            msg = res[1] if isinstance(res, tuple) and len(res) > 1 else 'Operacao concluida.'
            db.session.commit()
            flash(msg, 'success')
        except (ColetaError, ValueError) as e:
            db.session.rollback()
            flash(str(e), 'warning')
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erro na acao da coleta {coleta_id}: {e}')
            flash(f'Erro: {e}', 'danger')
        return redirect(url_for('carvia.detalhe_coleta', coleta_id=coleta_id))

    def _acao_linha(linha_id, fn):
        if not _guard():
            return _negado()
        from app.carvia.models.coleta import CarviaColetaNf
        from app.carvia.services.documentos.coleta_service import CarviaColetaService, ColetaError
        linha = db.session.get(CarviaColetaNf, linha_id)
        if linha is None:
            flash('Linha nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_coletas'))
        coleta_id = linha.coleta_id
        try:
            res = fn(linha, CarviaColetaService)
            msg = res[1] if isinstance(res, tuple) and len(res) > 1 else 'Operacao concluida.'
            db.session.commit()
            flash(msg, 'success')
        except (ColetaError, ValueError) as e:
            db.session.rollback()
            flash(str(e), 'warning')
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erro na acao da linha {linha_id}: {e}')
            flash(f'Erro: {e}', 'danger')
        return redirect(url_for('carvia.detalhe_coleta', coleta_id=coleta_id))
