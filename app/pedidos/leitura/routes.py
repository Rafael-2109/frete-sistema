"""
Rotas para leitura e processamento de PDFs de pedidos
"""

from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename
import os
import tempfile
from datetime import datetime

from .processor import PedidoProcessor

bp = Blueprint('leitura_pedidos', __name__, url_prefix='/pedidos/leitura')

ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/')
@login_required
def index():
    """Página principal da leitura de pedidos"""
    return render_template('pedidos/leitura/index.html')


@bp.route('/upload', methods=['POST'])
@login_required
def upload():
    """Upload e processamento de PDF"""
    try:
        # Verifica se arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Tipo de arquivo não permitido. Use PDF'}), 400
        
        # Salva arquivo temporário
        filename = secure_filename(file.filename)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"pedido_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")
        file.save(temp_path)
        
        try:
            # Processa arquivo
            processor = PedidoProcessor()
            
            # Obtém formato do formulário ou usa auto-detecção
            formato = request.form.get('formato', 'auto')
            
            result = processor.process_file(
                temp_path,
                formato=formato,
                validate=True,
                save_to_db=False  # Por enquanto não salva no banco
            )
            
            # Remove arquivo temporário
            os.remove(temp_path)
            
            if result['success']:
                # Salva dados na sessão para download posterior
                session_key = f"pedido_data_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Converte Decimal para float para serialização JSON
                data_serializable = []
                for item in result['data']:
                    item_clean = {}
                    for k, v in item.items():
                        if hasattr(v, 'quantize'):  # É Decimal
                            item_clean[k] = float(v)
                        else:
                            item_clean[k] = v
                    data_serializable.append(item_clean)
                
                # Armazena temporariamente (em produção, usar Redis ou similar)
                from flask import session
                session[session_key] = {
                    'data': data_serializable,
                    'filename': filename,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Debug: imprime o summary para verificar
                print(f"Summary gerado: {result.get('summary', {})}")
                
                response_data = {
                    'success': True,
                    'summary': result.get('summary', {}),
                    'data': data_serializable,
                    'session_key': session_key,
                    'warnings': result.get('warnings', []),
                    'errors': result.get('errors', [])
                }
                
                return jsonify(response_data)
            else:
                return jsonify({
                    'success': False,
                    'errors': result.get('errors', ['Erro ao processar arquivo'])
                }), 400
                
        except Exception as e:
            # Remove arquivo temporário em caso de erro
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro ao processar arquivo: {str(e)}'
        }), 500


@bp.route('/export/<format>/<session_key>')
@login_required
def export(format, session_key):
    """Exporta dados processados para Excel ou CSV"""
    try:
        from flask import session
        
        # Recupera dados da sessão
        if session_key not in session:
            flash('Dados não encontrados. Por favor, processe o arquivo novamente.', 'warning')
            return redirect(url_for('leitura_pedidos.index'))
        
        pedido_data = session[session_key]
        data = pedido_data['data']
        original_filename = pedido_data['filename'].rsplit('.', 1)[0]
        
        if not data:
            flash('Sem dados para exportar', 'warning')
            return redirect(url_for('leitura_pedidos.index'))
        
        # Cria arquivo temporário para export
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        processor = PedidoProcessor()
        
        if format == 'excel':
            output_path = os.path.join(temp_dir, f"{original_filename}_processado_{timestamp}.xlsx")
            processor.export_to_excel(data, output_path)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif format == 'csv':
            output_path = os.path.join(temp_dir, f"{original_filename}_processado_{timestamp}.csv")
            processor.export_to_csv(data, output_path)
            mimetype = 'text/csv'
        else:
            flash('Formato de exportação inválido', 'danger')
            return redirect(url_for('leitura_pedidos.index'))
        
        # Envia arquivo para download
        return send_file(
            output_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=os.path.basename(output_path)
        )
        
    except Exception as e:
        flash(f'Erro ao exportar dados: {str(e)}', 'danger')
        return redirect(url_for('leitura_pedidos.index'))


@bp.route('/test')
@login_required
def test():
    """Página de teste com arquivo de exemplo"""
    # Testa com o arquivo fornecido
    test_file = '/mnt/c/Users/rafael.nascimento/Downloads/PROPOSTA NACOM (2).pdf'
    
    if os.path.exists(test_file):
        processor = PedidoProcessor()
        result = processor.process_file(test_file, formato='atacadao', validate=True)
        
        return render_template('pedidos/leitura/test.html', result=result)
    else:
        flash('Arquivo de teste não encontrado', 'warning')
        return redirect(url_for('leitura_pedidos.index'))