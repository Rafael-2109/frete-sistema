"""
Rotas de Importacao Excel + Download de Template — Entidades de Configuracao CarVia
====================================================================================
Cobre: CarviaModeloMoto, CarviaCidadeAtendida, CarviaTabelaFrete
"""

import logging
from io import BytesIO

from flask import flash, redirect, request, send_file, url_for
from flask_login import current_user, login_required

logger = logging.getLogger(__name__)

# Definicoes de templates para download
_TEMPLATES = {
    'modelos-moto': {
        'columns': [
            'Nome', 'Comprimento (cm)', 'Largura (cm)', 'Altura (cm)',
            'Categoria', 'Regex Pattern', 'Ativo',
        ],
        'sheet': 'Modelos Moto',
        'filename': 'template_modelos_moto',
    },
    'cidades-atendidas': {
        'columns': [
            'Codigo IBGE', 'Nome Cidade', 'UF Origem', 'UF Destino',
            'Nome Tabela', 'Lead Time (dias)', 'Ativo',
        ],
        'sheet': 'Cidades Atendidas',
        'filename': 'template_cidades_atendidas',
    },
    'tabelas-frete': {
        'columns': [
            'UF Origem', 'UF Destino', 'Nome Tabela', 'Tipo Carga',
            'Modalidade', 'Grupo Cliente', 'R$/kg', 'Frete Min Peso',
            '% Valor', 'Frete Min Valor', '% GRIS', 'GRIS Min',
            '% ADV', 'ADV Min', '% RCA', 'Pedagio/100kg',
            'Despacho', 'CTe', 'TAS', 'ICMS Incluso',
            'ICMS Proprio %', 'Ativo',
        ],
        'sheet': 'Tabelas Frete',
        'filename': 'template_tabelas_frete',
        # Segunda aba para precos por categoria de moto
        'sheet2_columns': [
            'Nome Tabela', 'UF Origem', 'UF Destino', 'Tipo Carga',
            'Modalidade', 'Grupo Cliente', 'Categoria Moto',
            'Valor Unitario', 'Ativo',
        ],
        'sheet2_name': 'Precos Moto',
    },
}


def _check_access():
    """Retorna True se acesso NEGADO."""
    return not getattr(current_user, 'sistema_carvia', False)


def _validar_upload(redirect_url: str):
    """Valida presenca e extensao do arquivo. Retorna (arquivo, None) ou (None, redirect)."""
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado.', 'warning')
        return None, redirect(redirect_url)

    arquivo = request.files['arquivo']
    if not arquivo.filename or not arquivo.filename.lower().endswith('.xlsx'):
        flash('Use apenas arquivo .xlsx.', 'warning')
        return None, redirect(redirect_url)

    return arquivo, None


def _processar_importacao(service_method, arquivo, criado_por, redirect_url):
    """Executa importacao via service e redireciona com flash."""
    try:
        resultado = service_method(arquivo, criado_por)

        partes = []
        if resultado['inseridos']:
            partes.append(f"{resultado['inseridos']} inseridos")
        if resultado['atualizados']:
            partes.append(f"{resultado['atualizados']} atualizados")
        if resultado['erros']:
            partes.append(f"{resultado['erros']} erros")

        msg = f"Importacao concluida: {', '.join(partes) if partes else 'nenhuma alteracao'}."
        level = 'success' if resultado['erros'] == 0 else 'warning'
        flash(msg, level)

        # Mostrar ate 5 detalhes de erro
        for err in resultado.get('detalhes_erros', [])[:5]:
            flash(err, 'danger')

    except ValueError as e:
        flash(f'Erro na planilha: {e}', 'danger')
    except Exception as e:
        logger.error("Erro ao importar: %s", e)
        flash(f'Erro na importacao: {e}', 'danger')

    return redirect(redirect_url)


def register_importacao_config_routes(bp):

    # ==================================================================
    # Download de Template (Excel vazio com colunas corretas)
    # ==================================================================

    @bp.route('/configuracoes/importar/template/<entity>')  # type: ignore
    @login_required
    def baixar_template_importacao(entity):  # type: ignore
        """Gera Excel vazio com colunas corretas para importacao."""
        if _check_access():
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        import pandas as pd

        tmpl = _TEMPLATES.get(entity)
        if not tmpl:
            flash('Template nao encontrado.', 'danger')
            return redirect(url_for('carvia.listar_modelos_moto'))

        df = pd.DataFrame(columns=tmpl['columns'])
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=tmpl['sheet'])
            # Segunda aba (ex: Precos Moto para tabelas-frete)
            if 'sheet2_columns' in tmpl:
                df2 = pd.DataFrame(columns=tmpl['sheet2_columns'])
                df2.to_excel(writer, index=False, sheet_name=tmpl['sheet2_name'])
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"{tmpl['filename']}.xlsx",
        )

    # ==================================================================
    # Importar Modelos de Moto
    # ==================================================================

    @bp.route('/configuracoes/importar/modelos-moto', methods=['POST'])  # type: ignore
    @login_required
    def importar_modelos_moto():  # type: ignore
        """Importa CarviaModeloMoto via upload Excel (UPSERT)."""
        if _check_access():
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        redirect_url = url_for('carvia.listar_modelos_moto')
        arquivo, err_redirect = _validar_upload(redirect_url)
        if err_redirect:
            return err_redirect

        from app.carvia.services.importacao_config_service import ImportacaoConfigService

        svc = ImportacaoConfigService()
        return _processar_importacao(
            svc.importar_modelos_moto, arquivo, current_user.email, redirect_url,
        )

    # ==================================================================
    # Importar Cidades Atendidas
    # ==================================================================

    @bp.route('/configuracoes/importar/cidades-atendidas', methods=['POST'])  # type: ignore
    @login_required
    def importar_cidades_atendidas():  # type: ignore
        """Importa CarviaCidadeAtendida via upload Excel (UPSERT)."""
        if _check_access():
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        redirect_url = url_for('carvia.listar_cidades_carvia')
        arquivo, err_redirect = _validar_upload(redirect_url)
        if err_redirect:
            return err_redirect

        from app.carvia.services.importacao_config_service import ImportacaoConfigService

        svc = ImportacaoConfigService()
        return _processar_importacao(
            svc.importar_cidades_atendidas, arquivo, current_user.email, redirect_url,
        )

    # ==================================================================
    # Importar Tabelas de Frete
    # ==================================================================

    @bp.route('/configuracoes/importar/tabelas-frete', methods=['POST'])  # type: ignore
    @login_required
    def importar_tabelas_frete():  # type: ignore
        """Importa CarviaTabelaFrete via upload Excel (UPSERT)."""
        if _check_access():
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        redirect_url = url_for('carvia.listar_tabelas_carvia')
        arquivo, err_redirect = _validar_upload(redirect_url)
        if err_redirect:
            return err_redirect

        from app.carvia.services.importacao_config_service import ImportacaoConfigService

        svc = ImportacaoConfigService()
        return _processar_importacao(
            svc.importar_tabelas_frete, arquivo, current_user.email, redirect_url,
        )
