import os
import tempfile
from datetime import datetime
from flask import Blueprint, render_template, redirect, flash, request, jsonify
from flask_login import login_required
from app.utils.lote_utils import gerar_lote_id
from app import db
from app.separacao.models import Separacao
from app.separacao.forms import ImportarExcelForm

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
    import pandas as pd  # Lazy import
    import numpy as np  # Lazy import
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
    import pandas as pd  # Lazy import
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
    import pandas as pd  # Lazy import
    if pd.isna(valor):
        return None
    s = str(valor).strip()
    return s if s not in ['nan', 'NaN', 'None', ''] else None


@separacao_bp.route('/importar', methods=['GET', 'POST'])
def importar():
    import pandas as pd  # Lazy import

    form = ImportarExcelForm()
    if form.validate_on_submit():
        arquivo = form.arquivo_excel.data
        
        try:
            # 📖 Ler o arquivo UMA vez no início para evitar problemas de arquivo fechado
            arquivo.seek(0)  # Garantir que estamos no início do arquivo
            file_content = arquivo.read()
            arquivo.seek(0)  # Voltar ao início para o save_file
            
            # 🌐 Usar sistema S3 para salvar arquivo
            storage = get_file_storage()
            
            # Passar o arquivo original para o storage (ele sabe lidar com FileStorage)
            file_path = storage.save_file(
                file=arquivo,
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

            # 🎯 Dicionário para mapear (num_pedido, expedicao) → separacao_lote_id
            # Cada combinação única de pedido + data de expedição recebe seu próprio lote
            lotes_por_pedido_expedicao = {}

            for i, row in df.iterrows():

                # Exemplo: se QTD_SALDO for int, mas às vezes vem com pontos/virgula
                qtd_saldo = parse_int_br(row.get('QTD_SALDO'))
                if qtd_saldo is None:
                    qtd_saldo = 0  # se quiser forçar 0 caso não parse

                try:
                    # ✅ EXTRAIR num_pedido e expedicao ANTES de criar a Separacao
                    num_pedido_str = parse_str(row.get('NUM_PEDIDO'))
                    data_expedicao_obj = parse_date(row.get('EXPEDIÇÃO'))

                    # Criar chave única: "PEDIDO123_2025-01-15" ou "PEDIDO123_sem_data"
                    chave_lote = f"{num_pedido_str}_{data_expedicao_obj if data_expedicao_obj else 'sem_data'}"

                    # Se ainda não existe lote para essa combinação, criar um novo
                    if chave_lote not in lotes_por_pedido_expedicao:
                        lotes_por_pedido_expedicao[chave_lote] = gerar_lote_id()
                        print(f"✅ Novo lote criado: {lotes_por_pedido_expedicao[chave_lote]} para {chave_lote}")

                    # Obter o lote_id correto para essa combinação
                    lote_id = lotes_por_pedido_expedicao[chave_lote]

                    # Truncar observ_ped_1 se for maior que 700 caracteres
                    observ_ped_1_value = parse_str(row.get('OBSERV_PED_1'))
                    if observ_ped_1_value is not None and len(observ_ped_1_value) > 700:
                        original_length = len(observ_ped_1_value)
                        observ_ped_1_value = observ_ped_1_value[:700]
                        print(f"⚠️ Linha {i}: Campo observ_ped_1 truncado de {original_length} para 700 caracteres")

                    pedido = Separacao(
                        num_pedido=num_pedido_str,
                        data_pedido=parse_date(row.get('DATA_PEDIDO')),
                        cnpj_cpf=parse_str(row.get('CNPJ_CPF')),
                        raz_social_red=parse_str(row.get('RAZ_SOCIAL_RED')),
                        nome_cidade=parse_str(row.get('NOME_CIDADE')),
                        cod_uf=parse_str(row.get('COD_UF')),
                        cod_produto=parse_str(row.get('COD_PRODUTO')),
                        nome_produto=parse_str(row.get('NOME_PRODUTO')),

                        qtd_saldo=qtd_saldo,
                        valor_saldo=parse_float_br(row.get('VALOR_SALDO')),
                        pallet=parse_float_br(row.get('PALLET')),
                        peso=parse_float_br(row.get('PESO')),

                        rota=parse_str(row.get('ROTA')),
                        sub_rota=parse_str(row.get('SUB-ROTA')),
                        observ_ped_1=observ_ped_1_value,
                        roteirizacao=parse_str(row.get('ROTEIRIZAÇÃO')),

                        expedicao=data_expedicao_obj,
                        agendamento=parse_date(row.get('AGENDAMENTO')),
                        protocolo=parse_str(row.get('PROTOCOLO')),
                        separacao_lote_id=lote_id  # ✅ Agora usa o lote específico da combinação
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

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erro ao importar: {e}", "danger")
            return redirect(request.url)

    return render_template('separacao/importar.html', form=form)


@separacao_bp.route('/listar')
def listar():
    # Construir query base com filtros
    query = Separacao.query

    # Aplicar filtros da requisição
    if num_pedido := request.args.get('num_pedido'):
        query = query.filter(Separacao.num_pedido.ilike(f'%{num_pedido}%'))

    if cnpj_cpf := request.args.get('cnpj_cpf'):
        query = query.filter(Separacao.cnpj_cpf.ilike(f'%{cnpj_cpf}%'))

    if data_ini := request.args.get('data_ini'):
        try:
            data_ini_parsed = datetime.strptime(data_ini, '%Y-%m-%d').date()
            query = query.filter(Separacao.data_pedido >= data_ini_parsed)
        except ValueError:
            pass

    if data_fim := request.args.get('data_fim'):
        try:
            data_fim_parsed = datetime.strptime(data_fim, '%Y-%m-%d').date()
            query = query.filter(Separacao.data_pedido <= data_fim_parsed)
        except ValueError:
            pass

    # Aplicar ordenação
    sort = request.args.get('sort', 'id')
    direction = request.args.get('direction', 'desc')

    # Mapa de colunas ordenáveis
    sortable_columns = {
        'id': Separacao.id,
        'num_pedido': Separacao.num_pedido,
        'cnpj_cpf': Separacao.cnpj_cpf,
        'raz_social_red': Separacao.raz_social_red,
        'nome_cidade': Separacao.nome_cidade,
        'cod_uf': Separacao.cod_uf,
        'data_pedido': Separacao.data_pedido,
        'expedicao': Separacao.expedicao,
        'agendamento': Separacao.agendamento,
        'cod_produto': Separacao.cod_produto,
        'nome_produto': Separacao.nome_produto,
        'qtd_saldo': Separacao.qtd_saldo,
        'valor_saldo': Separacao.valor_saldo,
        'pallet': Separacao.pallet,
        'peso': Separacao.peso
    }

    if sort in sortable_columns:
        coluna = sortable_columns[sort]
        if direction == 'desc':
            coluna = coluna.desc()
        query = query.order_by(coluna)
    else:
        query = query.order_by(Separacao.id.desc())

    # Paginação com 200 itens por página
    page = request.args.get('page', 1, type=int)
    per_page = 200
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

    # Processar status para cada item da página atual
    separacoes_com_status = []
    for separacao in paginacao.items:
        # Proteção: verifica se a property existe e funciona
        try:
            # Status vem direto da property status_calculado da Separação
            status = separacao.status_calculado if hasattr(separacao, 'status_calculado') else None

            # Fallback caso a property não funcione
            if not status:
                if separacao.status == 'PREVISAO':
                    status = 'PREVISAO'
                elif getattr(separacao, 'nf_cd', False):
                    status = 'NF no CD'
                elif separacao.sincronizado_nf or (separacao.numero_nf and str(separacao.numero_nf).strip()):
                    status = 'FATURADO'
                elif separacao.cotacao_id:
                    status = 'COTADO'
                else:
                    status = 'ABERTO'

            separacao.status_pedido = status
            separacao.pode_excluir = status == 'ABERTO'

        except Exception as e:
            # Fallback final em caso de erro
            separacao.status_pedido = separacao.status or 'ABERTO'
            separacao.pode_excluir = True

        separacoes_com_status.append(separacao)

    return render_template("separacao/listar.html",
                           pedidos=separacoes_com_status,
                           paginacao=paginacao)


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
            if status_pedido == 'FATURADO' or status_pedido == 'COTADO' or status_pedido == 'EMBARCADO':
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
            if status_pedido == 'FATURADO' or status_pedido == 'COTADO' or status_pedido == 'EMBARCADO':
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
