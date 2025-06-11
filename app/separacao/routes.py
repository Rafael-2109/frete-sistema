import os
import numpy as np
import pandas as pd
from flask import Blueprint, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename

from app import db
from app.separacao.models import Separacao
from app.separacao.forms import ImportarExcelForm

separacao_bp = Blueprint('separacao', __name__, url_prefix='/separacao')

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
        nome_seguro = secure_filename(arquivo.filename)
        caminho_arquivo = os.path.join(UPLOAD_FOLDER, nome_seguro)
        arquivo.save(caminho_arquivo)

        try:
            df = pd.read_excel(caminho_arquivo)

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
            flash('Importação realizada com sucesso!', 'success')

            # Ao fim, em vez de voltar pra 'separacao.listar', 
            # chamamos direto o gerar_resumo:
            return redirect(url_for('pedidos.gerar_resumo'))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao importar: {e}", "danger")

        finally:
            os.remove(caminho_arquivo)

    return render_template('separacao/importar.html', form=form)


@separacao_bp.route('/listar')
def listar():
    pedidos = Separacao.query.order_by(Separacao.id.desc()).all()
    return render_template("separacao/listar.html", pedidos=pedidos)

