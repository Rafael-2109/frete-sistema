"""
Rotas de Importacao CarVia — Upload PDF/XML, parsing, matching
"""

import logging
import os
import uuid as uuid_mod
from flask import render_template, request, flash, redirect, url_for, session, send_file, Response
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)

# GAP-11: TTL de 1 hora para dados de importacao no Redis
_IMPORTACAO_TTL = 3600


def _importacao_redis_key(user_id, chave_uuid):
    """Gera chave Redis para dados de importacao."""
    return f'carvia:importacao:{user_id}:{chave_uuid}'


def _salvar_importacao_temp(user_id, resultado, chave_uuid=None):
    """Salva resultado de importacao no Redis (preferencia) ou session (fallback).

    Args:
        user_id: ID do usuario
        resultado: dict com dados parseados
        chave_uuid: UUID existente para update parcial (se None, gera novo)

    Returns:
        str: UUID da chave usada
    """
    if chave_uuid is None:
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

    # ------------------------------------------------------------------ #
    #  API: Edicao do preview pre-importacao (muta dados no Redis)
    # ------------------------------------------------------------------ #

    @bp.route('/api/importacao/editar-item', methods=['POST'])
    @login_required
    def api_importacao_editar_item():
        """Edita um campo de um item no preview de importacao (Redis)."""
        data = request.get_json()
        if not data:
            return {'sucesso': False, 'erro': 'Body JSON obrigatorio.'}, 400

        chave = data.get('importacao_chave')
        tipo = data.get('tipo')  # 'nf', 'cte', 'fatura'
        indice = data.get('indice')
        campo = data.get('campo')
        valor = data.get('valor')

        if not all([chave, tipo is not None, indice is not None, campo]):
            return {'sucesso': False, 'erro': 'Campos obrigatorios: importacao_chave, tipo, indice, campo, valor.'}, 400

        # Mapear tipo para chave no resultado
        tipo_key_map = {
            'nf': 'nfs_parseadas',
            'cte': 'ctes_parseados',
            'fatura': 'faturas_parseadas',
        }
        lista_key = tipo_key_map.get(tipo)
        if not lista_key:
            return {'sucesso': False, 'erro': f'Tipo invalido: {tipo}'}, 400

        resultado = _obter_importacao_temp(current_user.id, chave)
        if not resultado:
            return {'sucesso': False, 'erro': 'Importacao nao encontrada ou expirada.'}, 404

        items = resultado.get(lista_key, [])
        if indice < 0 or indice >= len(items):
            return {'sucesso': False, 'erro': f'Indice {indice} fora do range.'}, 400

        # Atualizar campo — suporte a dot-notation (ex: "emitente.cnpj")
        if '.' in campo:
            parts = campo.split('.')
            target = items[indice]
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = valor
        else:
            items[indice][campo] = valor
        resultado[lista_key] = items

        # Salvar de volta no Redis com a mesma chave
        _salvar_importacao_temp(current_user.id, resultado, chave_uuid=chave)

        logger.info(
            f"[IMPORT-EDIT] {current_user.email}: {tipo}[{indice}].{campo} = {valor!r}"
        )

        return {'sucesso': True, 'valor_atualizado': valor}

    @bp.route('/api/importacao/remover-item', methods=['POST'])
    @login_required
    def api_importacao_remover_item():
        """Remove um item da lista no preview de importacao (Redis)."""
        data = request.get_json()
        if not data:
            return {'sucesso': False, 'erro': 'Body JSON obrigatorio.'}, 400

        chave = data.get('importacao_chave')
        tipo = data.get('tipo')
        indice = data.get('indice')

        if not all([chave, tipo is not None, indice is not None]):
            return {'sucesso': False, 'erro': 'Campos obrigatorios: importacao_chave, tipo, indice.'}, 400

        tipo_key_map = {
            'nf': 'nfs_parseadas',
            'cte': 'ctes_parseados',
            'fatura': 'faturas_parseadas',
        }
        lista_key = tipo_key_map.get(tipo)
        if not lista_key:
            return {'sucesso': False, 'erro': f'Tipo invalido: {tipo}'}, 400

        resultado = _obter_importacao_temp(current_user.id, chave)
        if not resultado:
            return {'sucesso': False, 'erro': 'Importacao nao encontrada ou expirada.'}, 404

        items = resultado.get(lista_key, [])
        if indice < 0 or indice >= len(items):
            return {'sucesso': False, 'erro': f'Indice {indice} fora do range.'}, 400

        removed = items.pop(indice)
        resultado[lista_key] = items

        _salvar_importacao_temp(current_user.id, resultado, chave_uuid=chave)

        logger.info(
            f"[IMPORT-EDIT] {current_user.email}: removeu {tipo}[{indice}] "
            f"({removed.get('numero_nf') or removed.get('cte_numero') or removed.get('numero_fatura')})"
        )

        return {'sucesso': True, 'restantes': len(items)}

    @bp.route('/api/importacao/reclassificar-cte', methods=['POST'])
    @login_required
    def api_importacao_reclassificar_cte():
        """Altera classificacao de um CTe (CTE_CARVIA ↔ CTE_SUBCONTRATO)."""
        data = request.get_json()
        if not data:
            return {'sucesso': False, 'erro': 'Body JSON obrigatorio.'}, 400

        chave = data.get('importacao_chave')
        indice = data.get('indice')
        nova_classificacao = data.get('nova_classificacao')

        if not all([chave, indice is not None, nova_classificacao]):
            return {'sucesso': False, 'erro': 'Campos obrigatorios: importacao_chave, indice, nova_classificacao.'}, 400

        if nova_classificacao not in ('CTE_CARVIA', 'CTE_SUBCONTRATO'):
            return {'sucesso': False, 'erro': 'Classificacao deve ser CTE_CARVIA ou CTE_SUBCONTRATO.'}, 400

        resultado = _obter_importacao_temp(current_user.id, chave)
        if not resultado:
            return {'sucesso': False, 'erro': 'Importacao nao encontrada ou expirada.'}, 404

        ctes = resultado.get('ctes_parseados', [])
        if indice < 0 or indice >= len(ctes):
            return {'sucesso': False, 'erro': f'Indice {indice} fora do range.'}, 400

        old_class = ctes[indice].get('classificacao')
        ctes[indice]['classificacao'] = nova_classificacao
        resultado['ctes_parseados'] = ctes

        _salvar_importacao_temp(current_user.id, resultado, chave_uuid=chave)

        logger.info(
            f"[IMPORT-EDIT] {current_user.email}: CTe[{indice}] "
            f"{old_class} -> {nova_classificacao}"
        )

        return {'sucesso': True}

    @bp.route('/api/importacao/reclassificar-fatura', methods=['POST'])
    @login_required
    def api_importacao_reclassificar_fatura():
        """Altera tipo/destino de uma fatura (CLIENTE ↔ TRANSPORTADORA)."""
        data = request.get_json()
        if not data:
            return {'sucesso': False, 'erro': 'Body JSON obrigatorio.'}, 400

        chave = data.get('importacao_chave')
        indice = data.get('indice')
        novo_tipo = data.get('novo_tipo')

        if not all([chave, indice is not None, novo_tipo]):
            return {'sucesso': False, 'erro': 'Campos obrigatorios: importacao_chave, indice, novo_tipo.'}, 400

        if novo_tipo not in ('CLIENTE', 'TRANSPORTADORA'):
            return {'sucesso': False, 'erro': 'Tipo deve ser CLIENTE ou TRANSPORTADORA.'}, 400

        resultado = _obter_importacao_temp(current_user.id, chave)
        if not resultado:
            return {'sucesso': False, 'erro': 'Importacao nao encontrada ou expirada.'}, 404

        faturas = resultado.get('faturas_parseadas', [])
        if indice < 0 or indice >= len(faturas):
            return {'sucesso': False, 'erro': f'Indice {indice} fora do range.'}, 400

        old_tipo = faturas[indice].get('tipo_destino')
        faturas[indice]['tipo_destino'] = novo_tipo
        resultado['faturas_parseadas'] = faturas

        _salvar_importacao_temp(current_user.id, resultado, chave_uuid=chave)

        logger.info(
            f"[IMPORT-EDIT] {current_user.email}: Fatura[{indice}] "
            f"tipo {old_tipo} -> {novo_tipo}"
        )

        return {'sucesso': True}

    # ------------------------------------------------------------------ #
    #  API: Edicao de sub-itens (itens NF, itens fatura)
    # ------------------------------------------------------------------ #

    @bp.route('/api/importacao/editar-item-detalhe', methods=['POST'])
    @login_required
    def api_importacao_editar_item_detalhe():
        """Edita um campo de um sub-item (ex: itens de NF, itens de fatura)."""
        data = request.get_json()
        if not data:
            return {'sucesso': False, 'erro': 'Body JSON obrigatorio.'}, 400

        chave = data.get('importacao_chave')
        tipo = data.get('tipo')  # 'nf' ou 'fatura'
        indice = data.get('indice')
        sub_tipo = data.get('sub_tipo')  # 'itens' ou 'itens_detalhe'
        sub_indice = data.get('sub_indice')
        campo = data.get('campo')
        valor = data.get('valor')

        if not all([chave, tipo, indice is not None, sub_tipo, sub_indice is not None, campo]):
            return {'sucesso': False, 'erro': 'Campos obrigatorios faltando.'}, 400

        tipo_key_map = {'nf': 'nfs_parseadas', 'fatura': 'faturas_parseadas'}
        lista_key = tipo_key_map.get(tipo)
        if not lista_key:
            return {'sucesso': False, 'erro': f'Tipo invalido: {tipo}'}, 400

        resultado = _obter_importacao_temp(current_user.id, chave)
        if not resultado:
            return {'sucesso': False, 'erro': 'Importacao nao encontrada ou expirada.'}, 404

        items = resultado.get(lista_key, [])
        if indice < 0 or indice >= len(items):
            return {'sucesso': False, 'erro': f'Indice {indice} fora do range.'}, 400

        sub_items = items[indice].get(sub_tipo, [])
        if sub_indice < 0 or sub_indice >= len(sub_items):
            return {'sucesso': False, 'erro': f'Sub-indice {sub_indice} fora do range.'}, 400

        sub_items[sub_indice][campo] = valor
        items[indice][sub_tipo] = sub_items
        resultado[lista_key] = items

        _salvar_importacao_temp(current_user.id, resultado, chave_uuid=chave)

        logger.info(
            f"[IMPORT-EDIT] {current_user.email}: {tipo}[{indice}].{sub_tipo}[{sub_indice}].{campo} = {valor!r}"
        )
        return {'sucesso': True, 'valor_atualizado': valor}

    @bp.route('/api/importacao/adicionar-item-detalhe', methods=['POST'])
    @login_required
    def api_importacao_adicionar_item_detalhe():
        """Adiciona um sub-item vazio (ex: novo item de NF)."""
        data = request.get_json()
        if not data:
            return {'sucesso': False, 'erro': 'Body JSON obrigatorio.'}, 400

        chave = data.get('importacao_chave')
        tipo = data.get('tipo')
        indice = data.get('indice')
        sub_tipo = data.get('sub_tipo')

        if not all([chave, tipo, indice is not None, sub_tipo]):
            return {'sucesso': False, 'erro': 'Campos obrigatorios faltando.'}, 400

        tipo_key_map = {'nf': 'nfs_parseadas', 'fatura': 'faturas_parseadas'}
        lista_key = tipo_key_map.get(tipo)
        if not lista_key:
            return {'sucesso': False, 'erro': f'Tipo invalido: {tipo}'}, 400

        resultado = _obter_importacao_temp(current_user.id, chave)
        if not resultado:
            return {'sucesso': False, 'erro': 'Importacao nao encontrada ou expirada.'}, 404

        items = resultado.get(lista_key, [])
        if indice < 0 or indice >= len(items):
            return {'sucesso': False, 'erro': f'Indice {indice} fora do range.'}, 400

        if sub_tipo not in items[indice]:
            items[indice][sub_tipo] = []

        items[indice][sub_tipo].append({})
        novo_sub_indice = len(items[indice][sub_tipo]) - 1
        resultado[lista_key] = items

        _salvar_importacao_temp(current_user.id, resultado, chave_uuid=chave)

        logger.info(
            f"[IMPORT-EDIT] {current_user.email}: adicionou {tipo}[{indice}].{sub_tipo}[{novo_sub_indice}]"
        )
        return {'sucesso': True, 'sub_indice': novo_sub_indice}

    @bp.route('/api/importacao/remover-item-detalhe', methods=['POST'])
    @login_required
    def api_importacao_remover_item_detalhe():
        """Remove um sub-item (ex: item de NF)."""
        data = request.get_json()
        if not data:
            return {'sucesso': False, 'erro': 'Body JSON obrigatorio.'}, 400

        chave = data.get('importacao_chave')
        tipo = data.get('tipo')
        indice = data.get('indice')
        sub_tipo = data.get('sub_tipo')
        sub_indice = data.get('sub_indice')

        if not all([chave, tipo, indice is not None, sub_tipo, sub_indice is not None]):
            return {'sucesso': False, 'erro': 'Campos obrigatorios faltando.'}, 400

        tipo_key_map = {'nf': 'nfs_parseadas', 'fatura': 'faturas_parseadas'}
        lista_key = tipo_key_map.get(tipo)
        if not lista_key:
            return {'sucesso': False, 'erro': f'Tipo invalido: {tipo}'}, 400

        resultado = _obter_importacao_temp(current_user.id, chave)
        if not resultado:
            return {'sucesso': False, 'erro': 'Importacao nao encontrada ou expirada.'}, 404

        items = resultado.get(lista_key, [])
        if indice < 0 or indice >= len(items):
            return {'sucesso': False, 'erro': f'Indice {indice} fora do range.'}, 400

        sub_items = items[indice].get(sub_tipo, [])
        if sub_indice < 0 or sub_indice >= len(sub_items):
            return {'sucesso': False, 'erro': f'Sub-indice {sub_indice} fora do range.'}, 400

        sub_items.pop(sub_indice)
        items[indice][sub_tipo] = sub_items
        resultado[lista_key] = items

        _salvar_importacao_temp(current_user.id, resultado, chave_uuid=chave)

        logger.info(
            f"[IMPORT-EDIT] {current_user.email}: removeu {tipo}[{indice}].{sub_tipo}[{sub_indice}]"
        )
        return {'sucesso': True, 'restantes': len(sub_items)}

    # ------------------------------------------------------------------ #
    #  API: Viewer de documento fonte (PDF/XML)
    # ------------------------------------------------------------------ #

    @bp.route('/api/importacao/documento')
    @login_required
    def api_importacao_documento():
        """Retorna o arquivo PDF/XML original para visualizacao no preview."""
        chave = request.args.get('importacao_chave')
        tipo = request.args.get('tipo')  # 'nf', 'cte', 'fatura'
        indice = request.args.get('indice', type=int)

        if not all([chave, tipo, indice is not None]):
            return {'sucesso': False, 'erro': 'Parametros obrigatorios: importacao_chave, tipo, indice.'}, 400

        tipo_key_map = {
            'nf': 'nfs_parseadas',
            'cte': 'ctes_parseados',
            'fatura': 'faturas_parseadas',
        }
        lista_key = tipo_key_map.get(tipo)
        if not lista_key:
            return {'sucesso': False, 'erro': f'Tipo invalido: {tipo}'}, 400

        resultado = _obter_importacao_temp(current_user.id, chave)
        if not resultado:
            return {'sucesso': False, 'erro': 'Importacao nao encontrada ou expirada.'}, 404

        items = resultado.get(lista_key, [])
        if indice < 0 or indice >= len(items):
            return {'sucesso': False, 'erro': f'Indice {indice} fora do range.'}, 400

        item = items[indice]

        # Tentar obter path do documento (varios nomes de campo possiveis)
        path = (
            item.get('cte_pdf_path')
            or item.get('arquivo_pdf_path')
            or item.get('arquivo_xml_path')
            or item.get('cte_xml_path')
        )

        if not path:
            return {'sucesso': False, 'erro': 'Documento fonte nao disponivel para este item.'}, 404

        # Se e um path S3 (comeca com http), redirecionar para presigned URL
        if path.startswith('http'):
            return redirect(path)

        # Path local — servir arquivo
        if os.path.exists(path):
            mimetype = 'application/pdf' if path.lower().endswith('.pdf') else 'text/xml'
            return send_file(
                path,
                mimetype=mimetype,
                as_attachment=False,
                download_name=os.path.basename(path),
            )

        # Tentar via FileStorage (S3)
        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()
            url = storage.get_presigned_url(path, expires_in=300)
            if url:
                return redirect(url)
        except Exception as e:
            logger.warning(f"Falha ao obter presigned URL para {path}: {e}")

        return {'sucesso': False, 'erro': 'Arquivo nao encontrado.'}, 404

    # ------------------------------------------------------------------ #
    #  Rotas originais
    # ------------------------------------------------------------------ #

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
            from app.carvia.services.parsers.importacao_service import ImportacaoService
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

        from app.carvia.services.parsers.importacao_service import ImportacaoService
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
            nfs_reut = resultado_salvo.get('nfs_reutilizadas', 0)
            if nfs_reut:
                partes.append(f'{nfs_reut} NFs ja existentes')
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
