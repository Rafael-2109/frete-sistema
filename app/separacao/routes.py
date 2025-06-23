import os
import numpy as np
import pandas as pd
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from werkzeug.utils import secure_filename

from app import db
from app.separacao.models import Separacao
from app.separacao.forms import ImportarExcelForm
from app.utils.localizacao import LocalizacaoService

# 🌐 Importar sistema de arquivos S3
from app.utils.file_storage import get_file_storage

separacao_bp = Blueprint('separacao', __name__, url_prefix='/separacao')

# Pasta para compatibilidade com arquivos antigos
UPLOAD_FOLDER = 'uploads/separacao'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def parse_float_br(valor):
    """
    Tenta tratar tanto o caso em que o Excel realmente traz
    vírgula como decimal (ex. "3.580,45"),
    quanto o caso em que o Excel traz ponto decimal (ex. "371.64").

    Se não conseguir, retorna None.
    """
    if pd.isna(valor) or valor in ['nan', '', None, np.nan]:
        return None

    valor_str = str(valor).strip()
    # Remove "R$" e espaços
    valor_str = valor_str.replace('R$','').replace('$','').replace(' ','')
    
    # CASO 1: se encontrar vírgula, assumimos que '.' são apenas milhar
    if ',' in valor_str:
        # remove todos os '.'
        valor_str = valor_str.replace('.', '')
        # troca última vírgula por ponto
        idx = valor_str.rfind(',')
        if idx != -1:
            valor_str = valor_str[:idx] + '.' + valor_str[idx+1:]
    else:
        # CASO 2: não tem vírgula => provavelmente "371.64"
        # aqui não removemos nada, pois esse '.' deve ser decimal
        # se você achar que pode vir "3.580" (milhar + decimal?), aí teria que heurística extra.
        pass

    # Agora tenta converter
    try:
        return float(valor_str)
    except ValueError:
        return None



def parse_int_br(valor):
    """
    Converte algo tipo "3.580" ou "3.580,00" em int (3580).
    Se não conseguir, retorna None
    """
    f = parse_float_br(valor)
    if f is None:
        return None
    return int(round(f))


def parse_date(valor):
    """
    Tenta converter algo no Excel (data ou string) para datetime.date.
    Se não conseguir, retorna None
    """
    if pd.isna(valor):
        return None
    dt = pd.to_datetime(valor, errors='coerce')
    if dt is pd.NaT:
        return None
    return dt.date()


def parse_str(valor):
    """
    Converte para string 'segura' ou None se vazio
    """
    if pd.isna(valor):
        return None
    s = str(valor).strip()
    return s if s not in ['nan', 'NaN', 'None', ''] else None


@separacao_bp.route('/importar', methods=['GET', 'POST'])
def importar():
    form = ImportarExcelForm()
    if form.validate_on_submit():
        arquivo = form.arquivo_excel.data
        
        try:
            # 📖 Ler o arquivo UMA vez no início para evitar problemas de arquivo fechado
            import tempfile
            import io
            
            file_content = arquivo.read()
            
            # 🌐 Usar sistema S3 para salvar arquivo usando BytesIO
            storage = get_file_storage()
            file_like = io.BytesIO(file_content)
            file_like.filename = arquivo.filename  # Preservar nome original
            
            file_path = storage.save_file(
                file=file_like,
                folder='separacao',
                allowed_extensions=['xlsx', 'xls']
            )
            
            if not file_path:
                flash('❌ Erro ao salvar arquivo no sistema!', 'danger')
                return redirect(request.url)
            
            # 📁 Para processamento, salvar temporariamente local usando os mesmos bytes
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_filepath = temp_file.name

            # Processar arquivo Excel
            df = pd.read_excel(temp_filepath)

            for i, row in df.iterrows():

                # Exemplo: se QTD_SALDO for int, mas às vezes vem com pontos/virgula
                qtd_saldo = parse_int_br(row.get('QTD_SALDO'))
                if qtd_saldo is None:
                    qtd_saldo = 0  # se quiser forçar 0 caso não parse

                try:
                    pedido = Separacao(
                        num_pedido      = parse_str(row.get('NUM_PEDIDO')),
                        data_pedido     = parse_date(row.get('DATA_PEDIDO')),
                        cnpj_cpf        = parse_str(row.get('CNPJ_CPF')),
                        raz_social_red  = parse_str(row.get('RAZ_SOCIAL_RED')),
                        nome_cidade     = parse_str(row.get('NOME_CIDADE')),
                        cod_uf          = parse_str(row.get('COD_UF')),
                        cod_produto     = parse_str(row.get('COD_PRODUTO')),
                        nome_produto    = parse_str(row.get('NOME_PRODUTO')),

                        qtd_saldo       = qtd_saldo,
                        valor_saldo     = parse_float_br(row.get('VALOR_SALDO')),
                        pallet          = parse_float_br(row.get('PALLET')),
                        peso            = parse_float_br(row.get('PESO')),

                        rota            = parse_str(row.get('ROTA')),
                        sub_rota        = parse_str(row.get('SUB-ROTA')),
                        observ_ped_1    = parse_str(row.get('OBSERV_PED_1')),
                        roteirizacao    = parse_str(row.get('ROTEIRIZAÇÃO')),

                        expedicao       = parse_date(row.get('EXPEDIÇÃO')),
                        agendamento     = parse_date(row.get('AGENDAMENTO')),
                        protocolo       = parse_str(row.get('PROTOCOLO')),
                    )
                    db.session.add(pedido)
                    db.session.flush()  # tenta inserir/validar já

                except Exception as e:
                    print(f"*** ERRO na linha {i}: {e}")
                    db.session.rollback()

            db.session.commit()
            
            # 🗑️ Remover arquivo temporário
            os.unlink(temp_filepath)
            
            flash('✅ Importação realizada com sucesso!', 'success')
            flash('📁 Arquivo salvo no sistema de armazenamento.', 'info')

            # Ao fim, em vez de voltar pra 'separacao.listar', 
            # chamamos direto o gerar_resumo:
            return redirect(url_for('pedidos.gerar_resumo'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erro ao importar: {e}", "danger")
            return redirect(request.url)

    return render_template('separacao/importar.html', form=form)


@separacao_bp.route('/listar')
def listar():
    from app.pedidos.models import Pedido
    
    separacoes = Separacao.query.order_by(Separacao.id.desc()).all()
    
    # Enriquece as separações com informações do pedido relacionado
    separacoes_com_status = []
    for separacao in separacoes:
        # Busca o pedido correspondente
        pedido = Pedido.query.filter_by(
            separacao_lote_id=separacao.separacao_lote_id
        ).first()
        
        # Adiciona informações do status
        separacao.pedido_relacionado = pedido
        separacao.status_pedido = pedido.status_calculado if pedido else 'SEM PEDIDO'
        separacao.pode_excluir = pedido.status_calculado == 'ABERTO' if pedido else False
        
        separacoes_com_status.append(separacao)
    
    return render_template("separacao/listar.html", pedidos=separacoes_com_status)


@separacao_bp.route('/excluir/<int:separacao_id>', methods=['POST'])
@login_required
def excluir_separacao(separacao_id):
    """Exclui uma separação específica - apenas se o pedido estiver com status 'Aberto'"""
    try:
        separacao = Separacao.query.get_or_404(separacao_id)
        
        # Verifica se existe um pedido correspondente e seu status
        from app.pedidos.models import Pedido
        pedido = Pedido.query.filter_by(
            separacao_lote_id=separacao.separacao_lote_id
        ).first()
        
        if pedido:
            status_pedido = pedido.status_calculado
            if status_pedido != 'ABERTO':
                return jsonify({
                    'success': False, 
                    'message': f'Não é possível excluir! Pedido {separacao.num_pedido} está com status "{status_pedido}". Apenas pedidos com status "ABERTO" podem ter separações excluídas.'
                }), 400
        
        # Salva informações para log
        num_pedido = separacao.num_pedido
        lote_id = separacao.separacao_lote_id
        
        db.session.delete(separacao)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Separação ID {separacao_id} (Pedido: {num_pedido}) excluída com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': f'Erro ao excluir separação: {str(e)}'
        }), 500


@separacao_bp.route('/excluir_lote/<lote_id>', methods=['POST'])
@login_required
def excluir_lote_separacao(lote_id):
    """Exclui todas as separações de um lote específico - apenas se o pedido estiver com status 'Aberto'"""
    try:
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
        
        if not separacoes:
            return jsonify({
                'success': False, 
                'message': f'Nenhuma separação encontrada para o lote {lote_id}'
            }), 404
        
        # Verifica se existe um pedido correspondente e seu status
        from app.pedidos.models import Pedido
        primeira_separacao = separacoes[0]
        pedido = Pedido.query.filter_by(
            separacao_lote_id=primeira_separacao.separacao_lote_id
        ).first()
        
        if pedido:
            status_pedido = pedido.status_calculado
            if status_pedido != 'ABERTO':
                return jsonify({
                    'success': False, 
                    'message': f'Não é possível excluir! Pedido {primeira_separacao.num_pedido} está com status "{status_pedido}". Apenas pedidos com status "ABERTO" podem ter separações excluídas.'
                }), 400
        
        count = len(separacoes)
        num_pedido = primeira_separacao.num_pedido
        
        # Exclui todas as separações do lote
        for separacao in separacoes:
            db.session.delete(separacao)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Lote {lote_id} excluído com sucesso! ({count} itens do pedido {num_pedido})'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': f'Erro ao excluir lote: {str(e)}'
        }), 500




