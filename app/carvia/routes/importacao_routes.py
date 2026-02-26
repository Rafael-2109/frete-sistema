"""
Rotas de Importacao CarVia — Upload PDF/XML, parsing, matching
"""

import logging
from flask import render_template, request, flash, redirect, url_for, session, jsonify
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)


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

            # Ler conteudo dos arquivos
            arquivos_bytes = []
            for f in arquivos:
                if f.filename:
                    conteudo = f.read()
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

            # Armazenar resultado na sessao para review
            session['carvia_importacao'] = resultado
            session['carvia_importacao_arquivos'] = [
                (nome, None) for nome, _ in arquivos_bytes
            ]

            return render_template(
                'carvia/importar_resultado.html',
                resultado=resultado,
            )

        return render_template('carvia/importar.html')

    @bp.route('/importar/confirmar', methods=['POST'])
    @login_required
    def importar_confirmar():
        """Confirma a importacao e salva no banco"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        resultado = session.get('carvia_importacao')
        if not resultado:
            flash('Nenhuma importacao pendente. Faca o upload novamente.', 'warning')
            return redirect(url_for('carvia.importar'))

        from app.carvia.services.importacao_service import ImportacaoService
        service = ImportacaoService()

        resultado_salvo = service.salvar_importacao(
            nfs_data=resultado.get('nfs_parseadas', []),
            ctes_data=resultado.get('ctes_parseados', []),
            matches=resultado.get('matches', {}),
            criado_por=current_user.email,
        )

        # Limpar sessao
        session.pop('carvia_importacao', None)
        session.pop('carvia_importacao_arquivos', None)

        if resultado_salvo.get('sucesso'):
            flash(
                f'Importacao concluida: {resultado_salvo["nfs_criadas"]} NFs, '
                f'{resultado_salvo["operacoes_criadas"]} operacoes criadas.',
                'success'
            )
            if resultado_salvo.get('erros'):
                for erro in resultado_salvo['erros']:
                    flash(erro, 'warning')
        else:
            flash('Erro na importacao. Verifique os detalhes.', 'danger')
            for erro in resultado_salvo.get('erros', []):
                flash(erro, 'danger')

        return redirect(url_for('carvia.listar_operacoes'))
