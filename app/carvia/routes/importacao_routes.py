"""
Rotas de Importacao CarVia — Upload PDF/XML, parsing, matching
"""

import logging
import uuid as uuid_mod
from flask import render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)

# GAP-11: TTL de 1 hora para dados de importacao no Redis
_IMPORTACAO_TTL = 3600


def _importacao_redis_key(user_id, chave_uuid):
    """Gera chave Redis para dados de importacao."""
    return f'carvia:importacao:{user_id}:{chave_uuid}'


def _salvar_importacao_temp(user_id, resultado):
    """Salva resultado de importacao no Redis (preferencia) ou session (fallback).

    Returns:
        str: UUID da chave usada
    """
    chave_uuid = str(uuid_mod.uuid4())

    from app.utils.redis_cache import redis_cache
    if redis_cache.disponivel:
        redis_key = _importacao_redis_key(user_id, chave_uuid)
        salvo = redis_cache.set(redis_key, resultado, ttl=_IMPORTACAO_TTL)
        if salvo:
            logger.info(f"Importacao salva no Redis: {redis_key} (TTL={_IMPORTACAO_TTL}s)")
            return chave_uuid

    # Fallback: session Flask (limitada a ~4KB cookie)
    logger.warning("Redis indisponivel, usando session Flask para importacao (fallback)")
    session['carvia_importacao'] = resultado
    return chave_uuid


def _obter_importacao_temp(user_id, chave_uuid):
    """Recupera resultado de importacao do Redis ou session.

    Returns:
        dict ou None
    """
    from app.utils.redis_cache import redis_cache
    if redis_cache.disponivel:
        redis_key = _importacao_redis_key(user_id, chave_uuid)
        resultado = redis_cache.get(redis_key)
        if resultado:
            return resultado

    # Fallback: session Flask
    return session.get('carvia_importacao')


def _limpar_importacao_temp(user_id, chave_uuid):
    """Remove dados de importacao do Redis e session."""
    from app.utils.redis_cache import redis_cache
    if redis_cache.disponivel:
        redis_key = _importacao_redis_key(user_id, chave_uuid)
        redis_cache.delete(redis_key)

    session.pop('carvia_importacao', None)
    session.pop('carvia_importacao_arquivos', None)


def register_importacao_routes(bp):

    @bp.route('/importar', methods=['GET', 'POST'])
    @login_required
    def importar():
        """Tela de upload multi-arquivo (NFs + CTes)"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            arquivos = request.files.getlist('arquivos')
            if not arquivos or all(f.filename == '' for f in arquivos):
                flash('Nenhum arquivo selecionado.', 'warning')
                return redirect(url_for('carvia.importar'))

            # GAP-12: Validar extensao e tamanho dos arquivos
            _EXTENSOES_PERMITIDAS = {'.pdf', '.xml'}
            _MAX_TAMANHO_BYTES = 50 * 1024 * 1024  # 50MB

            arquivos_bytes = []
            for f in arquivos:
                if not f.filename:
                    continue

                # Validar extensao
                ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
                if f'.{ext}' not in _EXTENSOES_PERMITIDAS:
                    flash(
                        f'Arquivo "{f.filename}" ignorado: extensao .{ext} nao permitida '
                        f'(aceitos: {", ".join(sorted(_EXTENSOES_PERMITIDAS))}).',
                        'warning',
                    )
                    continue

                conteudo = f.read()

                # Validar tamanho
                if len(conteudo) > _MAX_TAMANHO_BYTES:
                    flash(
                        f'Arquivo "{f.filename}" ignorado: {len(conteudo) / 1024 / 1024:.1f}MB '
                        f'excede limite de {_MAX_TAMANHO_BYTES / 1024 / 1024:.0f}MB.',
                        'warning',
                    )
                    continue

                arquivos_bytes.append((f.filename, conteudo))

            if not arquivos_bytes:
                flash('Nenhum arquivo valido.', 'warning')
                return redirect(url_for('carvia.importar'))

            # Processar com ImportacaoService
            from app.carvia.services.importacao_service import ImportacaoService
            service = ImportacaoService()
            resultado = service.processar_arquivos(
                arquivos_bytes,
                criado_por=current_user.email,
            )

            # GAP-11: Armazenar resultado no Redis (com fallback session)
            chave_uuid = _salvar_importacao_temp(current_user.id, resultado)

            return render_template(
                'carvia/importar_resultado.html',
                resultado=resultado,
                importacao_chave=chave_uuid,
            )

        return render_template('carvia/importar.html')

    @bp.route('/importar/confirmar', methods=['POST'])
    @login_required
    def importar_confirmar():
        """Confirma a importacao e salva no banco"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        # GAP-11: Recuperar dados do Redis usando chave do form
        chave_uuid = request.form.get('importacao_chave', '')
        resultado = _obter_importacao_temp(current_user.id, chave_uuid)
        if not resultado:
            flash('Nenhuma importacao pendente ou sessao expirada. Faca o upload novamente.', 'warning')
            return redirect(url_for('carvia.importar'))

        from app.carvia.services.importacao_service import ImportacaoService
        service = ImportacaoService()

        resultado_salvo = service.salvar_importacao(
            nfs_data=resultado.get('nfs_parseadas', []),
            ctes_data=resultado.get('ctes_parseados', []),
            matches=resultado.get('matches', {}),
            criado_por=current_user.email,
            faturas_data=resultado.get('faturas_parseadas', []),
        )

        # GAP-11: Limpar dados temporarios (Redis + session)
        _limpar_importacao_temp(current_user.id, chave_uuid)

        if resultado_salvo.get('sucesso'):
            partes = [
                f'{resultado_salvo["nfs_criadas"]} NFs',
                f'{resultado_salvo["operacoes_criadas"]} CTes CarVia',
            ]
            subs = resultado_salvo.get('subcontratos_criados', 0)
            if subs:
                partes.append(f'{subs} CTes Subcontrato')
            fats = resultado_salvo.get('faturas_criadas', 0)
            if fats:
                partes.append(f'{fats} Faturas')
            nfs_sem_cte = resultado_salvo.get('nfs_sem_cte', 0)
            if nfs_sem_cte:
                partes.append(f'{nfs_sem_cte} NFs aguardando CTe')
            flash(
                f'Importacao concluida: {", ".join(partes)}.',
                'success'
            )
            if resultado_salvo.get('erros'):
                for erro in resultado_salvo['erros']:
                    flash(erro, 'warning')
        else:
            flash('Erro na importacao. Verifique os detalhes.', 'danger')
            for erro in resultado_salvo.get('erros', []):
                flash(erro, 'danger')

        # Redirect inteligente:
        # - Se criou operacoes -> listagem de operacoes
        # - Se criou faturas (sem operacoes) -> listagem de faturas (cliente por padrao)
        # - Se so NFs -> listagem de NFs
        if resultado_salvo.get('operacoes_criadas', 0) > 0:
            return redirect(url_for('carvia.listar_operacoes'))
        elif resultado_salvo.get('faturas_criadas', 0) > 0:
            return redirect(url_for('carvia.listar_faturas_cliente'))
        else:
            return redirect(url_for('carvia.listar_nfs'))
