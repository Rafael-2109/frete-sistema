from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from flask_login import login_required
from sqlalchemy import literal, and_
from app import db
from app.vinculos.forms import UploadVinculoForm
from app.vinculos.forms import ConfirmarImportacaoForm
from app.vinculos.forms import EditarVinculoForm
from app.vinculos.forms import ConsultaVinculoForm
from app.vinculos.models import CidadeAtendida
from app.transportadoras.models import Transportadora
from app.localidades.models import Cidade
from app.tabelas.models import TabelaFrete
from app.utils.importacao.utils_importacao import salvar_temp, limpar_temp
from app.utils.importacao.importar_vinculos_web import validar_vinculos
import io
import openpyxl
import math
from datetime import datetime
from flask import jsonify


def _safe_int_or_none(valor):
    """Converte valor para int ou None, tratando nan/NaN."""
    if valor is None:
        return None
    if isinstance(valor, float):
        if math.isnan(valor):
            return None
        return int(valor)
    if isinstance(valor, str) and valor.lower() in ('nan', 'none', ''):
        return None
    try:
        return int(valor)
    except (ValueError, TypeError):
        return None

vinculos_bp = Blueprint('vinculos', __name__, url_prefix='/vinculos')

@vinculos_bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar_vinculos():
    upload_form = UploadVinculoForm()
    confirmar_form = ConfirmarImportacaoForm()

    preview = False
    validos = []
    invalidos = []

    if upload_form.validate_on_submit():
        arquivo = upload_form.arquivo.data
        caminho = None
        
        try:
            caminho = salvar_temp(arquivo)
            linhas = validar_vinculos(caminho)

            for linha in linhas:
                if linha.get('erro'):
                    invalidos.append(linha)
                else:
                    validos.append(linha)

            session['vinculos_validos'] = validos
            session['vinculos_invalidos'] = invalidos

            preview = True
            
        except Exception as e:
            flash(f'Erro ao processar arquivo: {str(e)}', 'danger')
        finally:
            # 🗑️ Limpar arquivo temporário
            if caminho:
                limpar_temp(caminho)

    return render_template(
        'vinculo/importar_vinculos.html',
        upload_form=upload_form,
        confirmar_form=confirmar_form,
        validos=session.get('vinculos_validos', []),
        invalidos=session.get('vinculos_invalidos', []),
        preview=preview
    )

# Confirmação da Importação
@vinculos_bp.route('/confirmar_importacao', methods=['GET', 'POST'])
@login_required
def confirmar_importacao_vinculos():
    # Tratar GET - redirecionar com mensagem
    if request.method == 'GET':
        flash("Acesse através do processo de importação.", "warning")
        return redirect(url_for('vinculos.importar_vinculos'))
    
    dados_validos = session.get('vinculos_validos', [])

    if not dados_validos:
        flash("Nenhum dado válido para importar. Corrija os erros e tente novamente.", "danger")
        return redirect(url_for('vinculos.importar_vinculos'))

    total_importados = 0

    for linha in dados_validos:
        # Validar e limpar campo UF
        uf_value = linha.get('uf', '').strip()
        if uf_value in ['', 'nan', 'NaN', 'null', 'None'] or len(uf_value) > 2:
            continue  # Pular linha com UF inválida
            
        novo = CidadeAtendida(
            cidade_id=linha['cidade_id'],
            transportadora_id=linha['transportadora_id'],
            codigo_ibge=linha['codigo_ibge'],
            uf=uf_value,
            nome_tabela=linha['nome_tabela'].upper(),  # ✅ NORMALIZADO PARA MAIÚSCULA
            lead_time=_safe_int_or_none(linha['lead_time'])  # Trata nan/NaN do pandas
        )
        db.session.add(novo)
        total_importados += 1

    db.session.commit()

    # Limpa a sessão
    session.pop('vinculos_validos', None)
    session.pop('vinculos_invalidos', None)

    flash(f'{total_importados} vínculos importados com sucesso!', 'success')
    return redirect(url_for('vinculos.consulta_vinculos'))


@vinculos_bp.route('/consulta', methods=['GET'])
@login_required
def consulta_vinculos():
    form = ConsultaVinculoForm()
    editar_form = EditarVinculoForm()
    filtros = {}

    query = CidadeAtendida.query.join(Transportadora).join(Cidade)

    if request.args.get('razao_social'):
        filtros['razao_social'] = request.args.get('razao_social')
        query = query.filter(Transportadora.razao_social.ilike(f"%{filtros['razao_social']}%"))

    if request.args.get('cnpj'):
        filtros['cnpj'] = request.args.get('cnpj')
        query = query.filter(Transportadora.cnpj.ilike(f"%{filtros['cnpj']}%"))

    if request.args.get('uf'):
        filtros['uf'] = request.args.get('uf')
        query = query.filter(Cidade.uf.ilike(f"%{filtros['uf']}%"))

    if request.args.get('cidade'):
        filtros['cidade'] = request.args.get('cidade')
        query = query.filter(Cidade.nome.ilike(f"%{filtros['cidade']}%"))

    if request.args.get('codigo_ibge'):
        filtros['codigo_ibge'] = request.args.get('codigo_ibge')
        query = query.filter(Cidade.codigo_ibge.ilike(f"%{filtros['codigo_ibge']}%"))

    if request.args.get('nome_tabela'):
        filtros['nome_tabela'] = request.args.get('nome_tabela')
        query = query.filter(CidadeAtendida.nome_tabela.ilike(f"%{filtros['nome_tabela']}%"))

    # Filtro por status
    status = request.args.get('status')
    apenas_orfaos = request.args.get('apenas_orfaos')
    
    if status:
        filtros['status'] = status
        
        if status == 'orfao':
            # Vínculos órfãos - que não têm tabela correspondente
            query = query.filter(
                ~db.session.query(
                    literal(True)
                ).filter(
                    and_(
                        TabelaFrete.transportadora_id == CidadeAtendida.transportadora_id,
                        TabelaFrete.nome_tabela == CidadeAtendida.nome_tabela
                    )
                ).exists()
            )
        
        elif status == 'ok':
            # Vínculos OK - que têm tabela correspondente na mesma transportadora
            query = query.filter(
                db.session.query(
                    literal(True)
                ).filter(
                    and_(
                        TabelaFrete.transportadora_id == CidadeAtendida.transportadora_id,
                        TabelaFrete.nome_tabela == CidadeAtendida.nome_tabela
                    )
                ).exists()
            )
        
        elif status == 'transportadora_errada':
            # Vínculos que têm tabela mas em transportadora diferente
            from app.tabelas.models import TabelaFrete
            query = query.filter(
                # Não tem tabela na mesma transportadora
                ~db.session.query(literal(True)).filter(
                    and_(
                        TabelaFrete.transportadora_id == CidadeAtendida.transportadora_id,
                        TabelaFrete.nome_tabela == CidadeAtendida.nome_tabela
                    )
                ).exists(),
                # Mas tem tabela em transportadora diferente
                db.session.query(literal(True)).filter(
                    and_(
                        TabelaFrete.nome_tabela == CidadeAtendida.nome_tabela,
                        TabelaFrete.transportadora_id != CidadeAtendida.transportadora_id
                    )
                ).exists()
            )
        
        elif status == 'grupo_empresarial':
            # Filtra vínculos que são de grupo empresarial
            # Como a lógica é complexa, vamos fazer uma abordagem simples
            # que funciona com a propriedade do modelo
            pass  # Por enquanto, não filtra nada para mostrar todos
    
    # Filtro apenas órfãos
    if apenas_orfaos:
        filtros['apenas_orfaos'] = True
        query = query.filter(
            ~db.session.query(
                literal(True)
            ).filter(
                and_(
                    TabelaFrete.transportadora_id == CidadeAtendida.transportadora_id,
                    TabelaFrete.nome_tabela == CidadeAtendida.nome_tabela
                )
            ).exists()
        )

    # Aplica a paginação apenas para exibição
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Ordena a query antes de paginar
    query = query.order_by(CidadeAtendida.id)
    
    # Aplica a paginação
    paginacao = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Armazena todos os IDs filtrados na sessão (sem paginação)
    session['vinculos_filtrados'] = [v.id for v in query.all()]

    return render_template(
        'vinculo/consulta_vinculos.html',
        form=form,
        editar_form=editar_form,
        registros=paginacao.items,
        filtros=filtros,
        paginacao=paginacao
    )

@vinculos_bp.route('/editar', methods=['POST'])
@login_required
def editar_vinculo():
    from flask import request

    form = EditarVinculoForm()

    if not form.validate_on_submit():
        flash('Erro ao validar o formulário de edição.', 'danger')
        return redirect(url_for('vinculos.consulta_vinculos'))

    vinculo = CidadeAtendida.query.get_or_404(form.vinculo_id.data)

    transportadora = Transportadora.query.filter(
        Transportadora.razao_social.ilike(form.razao_social.data.strip())
    ).first()

    if not transportadora:
        flash(f'🚫 Transportadora "{form.razao_social.data.strip()}" não encontrada.', 'danger')
        return redirect(url_for('vinculos.consulta_vinculos'))

    codigo_ibge = form.codigo_ibge.data.strip()
    uf = form.uf.data.strip().upper()
    cidade_nome = form.cidade.data.strip()

    cidade = Cidade.query.filter_by(codigo_ibge=codigo_ibge).first()

    if not cidade:
        flash(f'🚫 Código IBGE "{codigo_ibge}" não encontrado.', 'danger')
        return redirect(url_for('vinculos.consulta_vinculos'))

    if cidade.uf.upper() != uf or cidade.nome.strip().lower() != cidade_nome.lower():
        flash(f'🚫 UF ou cidade informada não correspondem ao código IBGE {codigo_ibge}. Cidade correta: {cidade.nome}/{cidade.uf}', 'danger')
        return redirect(url_for('vinculos.consulta_vinculos'))

    # Atualizar o vínculo
    vinculo.transportadora_id = transportadora.id
    vinculo.cidade_id = cidade.id
    vinculo.codigo_ibge = cidade.codigo_ibge
    vinculo.uf = cidade.uf
    vinculo.nome_tabela = form.nome_tabela.data.strip().upper()  # ✅ NORMALIZADO PARA MAIÚSCULA

    try:
        vinculo.lead_time = int(form.lead_time.data) if form.lead_time.data else None
    except ValueError:
        vinculo.lead_time = None

    db.session.commit()

    flash(f'✅ Vínculo ID {vinculo.id} atualizado com sucesso!', 'success')
    return redirect(url_for('vinculos.consulta_vinculos'))

@vinculos_bp.route('/exportar_apagar', methods=['POST'])
@login_required
def exportar_apagar_vinculos():
    try:
        # Buscar os IDs filtrados da sessão
        ids_filtrados = session.get('vinculos_filtrados', [])

        if not ids_filtrados:
            flash('Nenhum filtro aplicado ou nenhum vínculo encontrado para exportar.', 'warning')
            return redirect(url_for('vinculos.consulta_vinculos'))

        # Processar em lotes para evitar erro do SQLAlchemy com muitos IDs
        batch_size = 1000
        vinculos = []
        
        for i in range(0, len(ids_filtrados), batch_size):
            batch_ids = ids_filtrados[i:i + batch_size]
            batch_vinculos = CidadeAtendida.query.filter(CidadeAtendida.id.in_(batch_ids)).all()
            vinculos.extend(batch_vinculos)

        if not vinculos:
            flash('Nenhum vínculo encontrado para exportar.', 'warning')
            return redirect(url_for('vinculos.consulta_vinculos'))

        # Gerar o Excel
        output = io.BytesIO()
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(['Transportadora', 'Cidade', 'UF', 'Codigo IBGE', 'Tabela', 'Lead Time'])

        for v in vinculos:
            sheet.append([
                v.transportadora.razao_social,
                v.cidade.nome,
                v.cidade.uf,
                v.cidade.codigo_ibge,
                v.nome_tabela,
                v.lead_time or ''
            ])

        workbook.save(output)
        output.seek(0)

        # Nome do arquivo com data e hora
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_vinculos_{timestamp}.xlsx"

        # Deletar os vínculos em lotes
        for i in range(0, len(ids_filtrados), batch_size):
            batch_ids = ids_filtrados[i:i + batch_size]
            CidadeAtendida.query.filter(CidadeAtendida.id.in_(batch_ids)).delete(synchronize_session=False)
        
        db.session.commit()

        session.pop('vinculos_filtrados', None)

        return send_file(
            output,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro: {str(e)}', 'danger')
        return redirect(url_for('vinculos.consulta_vinculos'))

@vinculos_bp.route('/cidades_por_uf/<uf>')
@login_required
def cidades_por_uf(uf):
    cidades = (
        CidadeAtendida.query
        .join(CidadeAtendida.cidade)
        .filter(CidadeAtendida.uf == uf)
        .with_entities(Cidade.nome)
        .distinct()
        .order_by(Cidade.nome)
        .all()
    )
    nomes_cidades = [cidade.nome for cidade in cidades]
    return jsonify(nomes_cidades)


@vinculos_bp.route('/tabelas_por_transportadora/<int:transportadora_id>')
@login_required
def tabelas_por_transportadora(transportadora_id):
    tabelas = db.session.query(CidadeAtendida.nome_tabela).filter_by(
        transportadora_id=transportadora_id
    ).distinct().order_by(CidadeAtendida.nome_tabela).all()

    nomes_tabelas = [tabela.nome_tabela for tabela in tabelas]
    return jsonify(nomes_tabelas)

# 🚩 Apenas Exportar
@vinculos_bp.route('/exportar_vinculos', methods=['POST'])
@login_required
def exportar_vinculos():
    ids_filtrados = session.get('vinculos_filtrados', [])
    if not ids_filtrados:
        flash('Nenhum vínculo encontrado para exportar.', 'warning')
        return redirect(url_for('vinculos.consulta_vinculos'))

    # Processar em lotes para evitar erro do SQLAlchemy com muitos IDs
    batch_size = 1000
    vinculos = []
    
    for i in range(0, len(ids_filtrados), batch_size):
        batch_ids = ids_filtrados[i:i + batch_size]
        batch_vinculos = CidadeAtendida.query.filter(CidadeAtendida.id.in_(batch_ids)).all()
        vinculos.extend(batch_vinculos)

    if not vinculos:
        flash('Nenhum vínculo encontrado para exportar.', 'warning')
        return redirect(url_for('vinculos.consulta_vinculos'))

    output = io.BytesIO()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(['Transportadora', 'Cidade', 'UF', 'Codigo IBGE', 'Tabela', 'Lead Time'])

    for v in vinculos:
        sheet.append([
            v.transportadora.razao_social,
            v.cidade.nome,
            v.cidade.uf,
            v.cidade.codigo_ibge,
            v.nome_tabela,
            v.lead_time or ''
        ])

    workbook.save(output)
    output.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_vinculos_{timestamp}.xlsx"

    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# 🚩 Apenas Excluir
@vinculos_bp.route('/apagar_vinculos', methods=['POST'])
@login_required
def apagar_vinculos():
    ids_filtrados = session.get('vinculos_filtrados', [])
    if not ids_filtrados:
        flash('Nenhum vínculo encontrado para excluir.', 'warning')
        return redirect(url_for('vinculos.consulta_vinculos'))

    # Processar em lotes para evitar erro do SQLAlchemy com muitos IDs
    batch_size = 1000
    total_excluidos = 0
    
    for i in range(0, len(ids_filtrados), batch_size):
        batch_ids = ids_filtrados[i:i + batch_size]
        count = CidadeAtendida.query.filter(CidadeAtendida.id.in_(batch_ids)).count()
        CidadeAtendida.query.filter(CidadeAtendida.id.in_(batch_ids)).delete(synchronize_session=False)
        total_excluidos += count
    
    db.session.commit()

    if total_excluidos > 0:
        flash(f'{total_excluidos} vínculos excluídos com sucesso!', 'success')
    else:
        flash('Nenhum vínculo encontrado para exclusão.', 'warning')

    session.pop('vinculos_filtrados', None)
    return redirect(url_for('vinculos.consulta_vinculos'))

@vinculos_bp.route('/excluir_vinculo/<int:id>', methods=['POST'])
@login_required
def excluir_vinculo(id):
    vinculo = CidadeAtendida.query.get_or_404(id)

    # Realiza a exclusão
    db.session.delete(vinculo)
    db.session.commit()

    flash(f'Vínculo ID {id} foi excluído com sucesso!', 'success')
    return redirect(url_for('vinculos.consulta_vinculos'))
