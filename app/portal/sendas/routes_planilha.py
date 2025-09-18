"""
Rotas para importar planilha modelo do Portal Sendas
Etapa 1 - Recepção da planilha modelo
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import tempfile
from app.portal.sendas.parser_planilha import processar_planilha_modelo
import logging

logger = logging.getLogger(__name__)

bp_planilha_sendas = Blueprint('planilha_sendas', __name__, url_prefix='/portal/sendas')

@bp_planilha_sendas.route('/importar-planilha-modelo', methods=['POST'])
@login_required
def importar_planilha_modelo():
    """
    Rota para importar planilha modelo baixada do portal Sendas
    O usuário faz upload do arquivo XLSX e o sistema armazena no banco
    """
    try:
        # Verificar se arquivo foi enviado
        if 'arquivo' not in request.files:
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['arquivo']

        # Verificar se arquivo foi selecionado
        if arquivo.filename == '':
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo selecionado'}), 400

        # Verificar extensão
        if not arquivo.filename.lower().endswith('.xlsx'):
            return jsonify({'sucesso': False, 'mensagem': 'Arquivo deve ser XLSX'}), 400

        # Salvar arquivo temporariamente
        filename = secure_filename(arquivo.filename)
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)
        arquivo.save(filepath)

        # Processar planilha
        usuario = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
        resultado = processar_planilha_modelo(filepath, usuario)

        # Remover arquivo temporário
        try:
            os.remove(filepath)
        except Exception as e:
            logger.error(f"Erro ao remover arquivo temporário: {str(e)}")
            pass

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro ao importar planilha modelo: {str(e)}")
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500