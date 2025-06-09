from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf.csrf import validate_csrf, CSRFError
from sqlalchemy import literal, and_

from app import db
import pandas as pd
from datetime import timedelta, datetime

from app.tabelas.forms import TabelaFreteForm, ImportarTabelaFreteForm
from app.tabelas.models import TabelaFrete, HistoricoTabelaFrete
from app.transportadoras.models import Transportadora
from app.localidades.models import Cidade
from app.utils.utils_frete import float_or_none
from app.utils.ufs import UF_LIST
from app.vinculos.models import CidadeAtendida

tabelas_bp = Blueprint('tabelas', __name__, url_prefix='/tabelas')

@tabelas_bp.route('/tabelas_frete', methods=['GET', 'POST'])
@login_required
def cadastrar_tabela_frete():
    form = TabelaFreteForm()
    form.transportadora.choices = [(t.id, t.razao_social) for t in Transportadora.query.all()]
    form.uf_origem.choices = UF_LIST
    form.uf_destino.choices = UF_LIST

    if form.validate_on_submit():
        nova = TabelaFrete(
            transportadora_id=form.transportadora.data,
            uf_origem=form.uf_origem.data,
            uf_destino=form.uf_destino.data,
            nome_tabela=form.nome_tabela.data.upper(),
            tipo_carga=form.tipo_carga.data,
            modalidade=form.modalidade.data.upper(),
            valor_kg=float_or_none(form.valor_kg.data),
            frete_minimo_peso=float_or_none(form.frete_minimo_peso.data),
            percentual_valor=float_or_none(form.percentual_valor.data),
            frete_minimo_valor=float_or_none(form.frete_minimo_valor.data),
            percentual_gris=float_or_none(form.percentual_gris.data),
            percentual_adv=float_or_none(form.percentual_adv.data),
            percentual_rca=float_or_none(form.percentual_rca.data),
            pedagio_por_100kg=float_or_none(form.pedagio_por_100kg.data),
            valor_despacho=float_or_none(form.valor_despacho.data),
            valor_cte=float_or_none(form.valor_cte.data),
            valor_tas=float_or_none(form.valor_tas.data),
            icms_incluso=form.icms_incluso.data,
            criado_por=current_user.nome
        )
        db.session.add(nova)

        historico = HistoricoTabelaFrete(
            transportadora_id=form.transportadora.data,
            uf_origem=form.uf_origem.data,
            uf_destino=form.uf_destino.data,
            nome_tabela=form.nome_tabela.data.upper(),
            tipo_carga=form.tipo_carga.data,
            modalidade=form.modalidade.data.upper(),
            valor_kg=float_or_none(form.valor_kg.data),
            frete_minimo_peso=float_or_none(form.frete_minimo_peso.data),
            percentual_valor=float_or_none(form.percentual_valor.data),
            frete_minimo_valor=float_or_none(form.frete_minimo_valor.data),
            percentual_gris=float_or_none(form.percentual_gris.data),
            percentual_adv=float_or_none(form.percentual_adv.data),
            percentual_rca=float_or_none(form.percentual_rca.data),
            pedagio_por_100kg=float_or_none(form.pedagio_por_100kg.data),
            valor_despacho=float_or_none(form.valor_despacho.data),
            valor_cte=float_or_none(form.valor_cte.data),
            valor_tas=float_or_none(form.valor_tas.data),
            icms_incluso=form.icms_incluso.data,
            criado_por=current_user.nome
        )
        db.session.add(historico)

        db.session.commit()
        flash('Tabela de frete cadastrada com sucesso!', 'success')
        return redirect(url_for('tabelas.cadastrar_tabela_frete'))

    tabelas = TabelaFrete.query.all()
    return render_template('tabelas/tabelas_frete.html', form=form, tabelas=tabelas)


# Ajuste conforme suas choices reais do sistema
TIPOS_CARGA_VALIDOS = ['FRACIONADA', 'DIRETA']
MODALIDADES_VALIDAS = ['FRETE VALOR', 'FRETE PESO','FIORINO', 'VAN/HR', 'IVECO', '3/4', 'TOCO', 'TRUCK', 'CARRETA']

@tabelas_bp.route('/importar_tabela_frete', methods=['GET', 'POST'])
@login_required
def importar_tabela_frete():
    form = ImportarTabelaFreteForm()
    
    if form.validate_on_submit():
        arquivo = form.arquivo.data
        if not arquivo:
            flash('Nenhum arquivo selecionado', 'error')
            return render_template('tabelas/importar_tabela_frete.html', form=form)

        # Processa o arquivo Excel
        sucesso = 0
        erros = 0
        vinculos_criados = 0
        
        try:
            df = pd.read_excel(arquivo)

            colunas_obrigatorias = [
                'ATIVO', 'CÓD. TRANSP', 'DESTINO', 'NOME TABELA',
                'CARGA', 'FRETE', 'INC.', 'ORIGEM'
            ]

            for coluna in colunas_obrigatorias:
                if coluna not in df.columns:
                    flash(f'Coluna obrigatória ausente: {coluna}', 'danger')
                    return redirect(request.url)

            for index, row in df.iterrows():
                if str(row['ATIVO']).strip().upper() != 'A':
                    continue  # Ignorar tabelas inativas

                cnpj = str(row['CÓD. TRANSP']).strip()
                uf_destino = str(row['DESTINO']).strip()
                nome_tabela = str(row['NOME TABELA']).strip()

                transportadora = Transportadora.query.filter_by(cnpj=cnpj).first()
                if not transportadora:
                    erros += 1
                    flash(f"Transportadora {cnpj} não cadastrada (linha {index+2}). Por favor, cadastre a transportadora primeiro.", "danger")
                    continue

                vinculo_existente = CidadeAtendida.query.filter_by(
                    transportadora_id=transportadora.id,
                    uf=uf_destino,
                    nome_tabela=nome_tabela
                ).first()

                # Se o vínculo não existe, vamos criar
                if not vinculo_existente:
                    # Busca uma cidade qualquer do UF para vincular (geralmente a capital)
                    cidade = Cidade.query.filter_by(uf=uf_destino).first()
                    if not cidade:
                        erros += 1
                        flash(f"UF {uf_destino} não encontrada no banco de dados (linha {index+2})", "danger")
                        continue
                        
                    vinculo = CidadeAtendida(
                        transportadora_id=transportadora.id,
                        cidade_id=cidade.id,
                        codigo_ibge=cidade.codigo_ibge,
                        uf=uf_destino,
                        nome_tabela=nome_tabela,
                        lead_time=1  # valor padrão
                    )
                    db.session.add(vinculo)
                    vinculos_criados += 1

                tipo_carga = str(row['CARGA']).upper()
                modalidade = str(row['FRETE']).upper()

                # Mapear claramente para choices válidas
                modalidades_validas = {
                    'FRETE PESO': 'FRETE PESO',
                    'FRETE VALOR': 'FRETE VALOR',
                    'FIORINO': 'FIORINO',
                    'VAN/HR': 'VAN/HR',
                    'IVECO': 'IVECO',
                    '3/4': '3/4',
                    'TOCO': 'TOCO',
                    'TRUCK': 'TRUCK',
                    'CARRETA': 'CARRETA'
                }

                if modalidade not in modalidades_validas:
                    erros += 1
                    flash(f"Modalidade inválida '{modalidade}' (linha {index+2})", "danger")
                    continue

                modalidade = modalidades_validas[modalidade]

                if tipo_carga not in TIPOS_CARGA_VALIDOS:
                    erros += 1
                    flash(f"Tipo carga inválido '{tipo_carga}' (linha {index+2})", "danger")
                    continue

                tabela_frete = TabelaFrete.query.filter_by(
                    transportadora_id=transportadora.id,
                    uf_origem=row['ORIGEM'],
                    uf_destino=uf_destino,
                    nome_tabela=nome_tabela,
                    modalidade=modalidade
                ).first()

                if tabela_frete:
                    tabela_frete.frete_minimo_valor = round(float(row.get('VALOR') or 0), 2)
                    tabela_frete.frete_minimo_peso = round(float(row.get('PESO') or 0), 2)
                    tabela_frete.valor_kg = round(float(row.get('FRETE PESO') or 0), 6)
                    tabela_frete.percentual_valor = round(float(row.get('FRETE VALOR') or 0) * 100, 4)
                    tabela_frete.percentual_gris = round(float(row.get('GRIS') or 0) * 100, 4)
                    tabela_frete.percentual_adv = round(float(row.get('ADV') or 0) * 100, 4)
                    tabela_frete.percentual_rca = round(float(row.get('RCA SEGURO FLUVIAL %') or 0) * 100, 4)
                    tabela_frete.valor_despacho = round(float(row.get('DESPACHO / CTE / TAS') or 0), 2)
                    tabela_frete.valor_cte = round(float(row.get('CTE') or 0), 2)
                    tabela_frete.valor_tas = round(float(row.get('TAS') or 0), 2)
                    tabela_frete.pedagio_por_100kg = round(float(row.get('PEDAGIO FRAÇÃO 100 KGS') or 0), 2)
                    tabela_frete.icms_incluso = True if str(row.get('INC.')).strip().upper() == 'S' else False
                    tabela_frete.criado_por = current_user.nome    
                else:
                    tabela_frete = TabelaFrete(
                        transportadora_id=transportadora.id,
                        uf_origem=str(row['ORIGEM']).strip(),
                        uf_destino=uf_destino,
                        nome_tabela=nome_tabela,
                        tipo_carga=tipo_carga,
                        modalidade=modalidade,
                        frete_minimo_valor=round(float(row.get('VALOR') or 0), 2),
                        frete_minimo_peso=round(float(row.get('PESO') or 0), 2),
                        valor_kg=round(float(row.get('FRETE PESO') or 0), 6),
                        percentual_valor=round(float(row.get('FRETE VALOR') or 0) * 100, 4),
                        percentual_gris=round(float(row.get('GRIS') or 0) * 100, 4),
                        percentual_adv=round(float(row.get('ADV') or 0) * 100, 4),
                        percentual_rca=round(float(row.get('RCA SEGURO FLUVIAL %') or 0) * 100, 4),
                        valor_despacho=round(float(row.get('DESPACHO / CTE / TAS') or 0), 2),
                        valor_cte=round(float(row.get('CTE') or 0), 2),
                        valor_tas=round(float(row.get('TAS') or 0), 2),
                        pedagio_por_100kg=round(float(row.get('PEDAGIO FRAÇÃO 100 KGS') or 0), 2),
                        icms_incluso=True if str(row.get('INC.')).strip().upper() == 'S' else False,
                        criado_por=current_user.nome
                    )
                    db.session.add(tabela_frete)

                historico = HistoricoTabelaFrete(
                    transportadora_id=transportadora.id,
                    uf_origem=str(row['ORIGEM']).strip(),
                    uf_destino=uf_destino,
                    nome_tabela=nome_tabela,
                    tipo_carga=tipo_carga,
                    modalidade=modalidade,
                    frete_minimo_valor=round(float(row.get('VALOR') or 0), 2),
                    frete_minimo_peso=round(float(row.get('PESO') or 0), 2),
                    valor_kg=round(float(row.get('FRETE PESO') or 0), 6),
                    percentual_valor=round(float(row.get('FRETE VALOR') or 0) * 100, 4),
                    percentual_gris=round(float(row.get('GRIS') or 0) * 100, 4),
                    percentual_adv=round(float(row.get('ADV') or 0) * 100, 4),
                    percentual_rca=round(float(row.get('RCA SEGURO FLUVIAL %') or 0) * 100, 4),
                    valor_despacho=round(float(row.get('DESPACHO / CTE / TAS') or 0), 2),
                    valor_cte=round(float(row.get('CTE') or 0), 2),
                    valor_tas=round(float(row.get('TAS') or 0), 2),
                    pedagio_por_100kg=round(float(row.get('PEDAGIO FRAÇÃO 100 KGS') or 0), 2),
                    icms_incluso=True if str(row.get('INC.')).strip().upper() == 'S' else False,
                    criado_por=current_user.nome
                )
                db.session.add(historico)
                sucesso += 1

            db.session.commit()
            
            if vinculos_criados > 0:
                flash(f"Foram criados {vinculos_criados} novos vínculos automaticamente", "info")
                
            flash(f"Importação finalizada com sucesso: {sucesso} inseridos/atualizados, Erros: {erros}", "info")
            
            return redirect(url_for('tabelas.listar_todas_tabelas'))
            
        except Exception as e:
            flash(f"Erro ao processar arquivo: {str(e)}", "error")
            return render_template('tabelas/importar_tabela_frete.html', form=form)

    return render_template('tabelas/importar_tabela_frete.html', form=form)

@tabelas_bp.route('/historico_tabelas', methods=['GET'])
@login_required
def historico_tabelas():
    transportadoras = Transportadora.query.order_by(Transportadora.razao_social).all()
    uf_list = UF_LIST  # seu array/lista de (UF, NomeUF)
    modalidades = ['FRETE PESO', 'FRETE VALOR', 'FIORINO', 'VAN/HR', 'IVECO', '3/4', 'TOCO', 'TRUCK', 'CARRETA']

    # ==========================
    # 1) Captura filtros
    # ==========================
    transportadora_id = request.args.get('transportadora', type=int)
    uf_destino = request.args.get('uf_destino', '')
    cidade = request.args.get('cidade', '')
    nome_tabela = request.args.get('nome_tabela', '')
    tipo_carga = request.args.get('tipo_carga', '')
    modalidade = request.args.get('modalidade', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')

    # Monta um dicionário só pra passar ao template (opcional)
    filtros = {
        'transportadora': transportadora_id,
        'uf_destino': uf_destino,
        'cidade': cidade,
        'nome_tabela': nome_tabela,
        'tipo_carga': tipo_carga,
        'modalidade': modalidade,
        'data_inicio': data_inicio,
        'data_fim': data_fim
    }

    # ==========================
    # 2) Monta Query
    # ==========================
    query = db.session.query(HistoricoTabelaFrete).join(Transportadora)  # se seu model possui .transportadora

    # Aplica filtros
    if transportadora_id:
        query = query.filter(HistoricoTabelaFrete.transportadora_id == transportadora_id)

    if uf_destino:
        query = query.filter(HistoricoTabelaFrete.uf_destino == uf_destino)

    if cidade:
        # Se quiser filtrar cidade, depende de como seu model relaciona
        # Exemplo: query = query.filter(HistoricoTabelaFrete.cidade_destino.ilike(f"%{cidade}%"))
        pass

    if nome_tabela:
        query = query.filter(HistoricoTabelaFrete.nome_tabela.ilike(f"%{nome_tabela}%"))

    if tipo_carga:
        query = query.filter(HistoricoTabelaFrete.tipo_carga == tipo_carga)

    if modalidade:
        query = query.filter(HistoricoTabelaFrete.modalidade == modalidade)

    if data_inicio:
        # converter em datetime/date
        dt = datetime.strptime(data_inicio, "%d-%m-%Y")
        query = query.filter(HistoricoTabelaFrete.criado_em >= dt)

    if data_fim:
        dtf = datetime.strptime(data_fim, "%d-%m-%Y")
        # Se quiser incluir o dia inteiro, acrescente 23:59:59
        dtf = dtf.replace(hour=23, minute=59, second=59)
        query = query.filter(HistoricoTabelaFrete.criado_em <= dtf)

    # ==========================
    # 3) Ordenação (sorting)
    # ==========================
    sort = request.args.get('sort', '')
    direction = request.args.get('direction', 'asc')

    # Mapeia 'nome_coluna' => model.coluna
    sortable_columns = {
        'transportadora':     Transportadora.razao_social,
        'uf_origem':          HistoricoTabelaFrete.uf_origem,
        'uf_destino':         HistoricoTabelaFrete.uf_destino,
        'nome_tabela':        HistoricoTabelaFrete.nome_tabela,
        'tipo_carga':         HistoricoTabelaFrete.tipo_carga,
        'modalidade':         HistoricoTabelaFrete.modalidade,
        'frete_minimo_valor': HistoricoTabelaFrete.frete_minimo_valor,
        'frete_minimo_peso':  HistoricoTabelaFrete.frete_minimo_peso,
        'valor_kg':           HistoricoTabelaFrete.valor_kg,
        'percentual_valor':   HistoricoTabelaFrete.percentual_valor,
        'percentual_gris':    HistoricoTabelaFrete.percentual_gris,
        'percentual_adv':     HistoricoTabelaFrete.percentual_adv,
        'percentual_rca':     HistoricoTabelaFrete.percentual_rca,
        'valor_despacho':     HistoricoTabelaFrete.valor_despacho,
        'valor_cte':          HistoricoTabelaFrete.valor_cte,
        'valor_tas':          HistoricoTabelaFrete.valor_tas,
        'pedagio_por_100kg':  HistoricoTabelaFrete.pedagio_por_100kg,
        'icms_incluso':       HistoricoTabelaFrete.icms_incluso,
        'criado_por':         HistoricoTabelaFrete.criado_por,
        'criado_em':          HistoricoTabelaFrete.criado_em
    }

    if sort in sortable_columns:
        col = sortable_columns[sort]
        if direction == 'desc':
            query = query.order_by(col.desc())
        else:
            query = query.order_by(col.asc())
    else:
        # Ordenação padrão se nada for passado
        query = query.order_by(HistoricoTabelaFrete.criado_em.desc())

    # ==========================
    # 4) Paginação
    # ==========================
    page = request.args.get('page', 1, type=int)
    per_page = 20
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

    # ==========================
    # 5) Renderiza Template
    # ==========================
    return render_template(
        'tabelas/historico_tabelas.html',
        historicos=paginacao.items,  # os registros da página atual
        paginacao=paginacao,         # objeto paginate
        transportadoras=transportadoras,
        uf_list=uf_list,
        modalidades=modalidades,
        filtros=filtros,
        sort=sort,
        direction=direction
    )



@tabelas_bp.route('/listar_todas_tabelas', methods=['GET'])
@login_required
def listar_todas_tabelas():
    transportadoras = Transportadora.query.order_by(Transportadora.razao_social).all()
    uf_list = UF_LIST  # seu array/lista de (UF, NomeUF)
    modalidades = ['FRETE PESO', 'FRETE VALOR', 'FIORINO', 'VAN/HR', 'IVECO', '3/4', 'TOCO', 'TRUCK', 'CARRETA']

    query = TabelaFrete.query.join(Transportadora)

    # 1) FILTROS
    transportadora_id = request.args.get('transportadora', type=int)
    uf_destino = request.args.get('uf_destino', '')
    cidade = request.args.get('cidade', '')
    nome_tabela = request.args.get('nome_tabela', '')
    tipo_carga = request.args.get('tipo_carga', '')
    modalidade = request.args.get('modalidade', '')

    if transportadora_id:
        query = query.filter(TabelaFrete.transportadora_id == transportadora_id)

    if uf_destino:
        query = query.filter(TabelaFrete.uf_destino == uf_destino)

    if cidade:
        # Exemplo: filtra via join com CidadeAtendida, etc. Ajuste se for necessário
        query = query.join(CidadeAtendida).join(Cidade).filter(
            Cidade.nome.ilike(f"%{cidade}%"),
            TabelaFrete.nome_tabela == CidadeAtendida.nome_tabela,
            TabelaFrete.uf_destino == CidadeAtendida.uf
        )

    if nome_tabela:
        query = query.filter(TabelaFrete.nome_tabela.ilike(f"%{nome_tabela}%"))

    if tipo_carga:
        query = query.filter(TabelaFrete.tipo_carga == tipo_carga)

    if modalidade:
        query = query.filter(TabelaFrete.modalidade == modalidade)

    # 🔥 FILTROS DE STATUS 
    status = request.args.get('status', '')
    apenas_orfas = request.args.get('apenas_orfas', '')
    
    # Se tiver filtro de status ou apenas órfãs, aplicamos a lógica
    if status or apenas_orfas:
        from app.vinculos.models import CidadeAtendida
        
        # Se apenas órfãs foi marcado, filtra apenas tabelas órfãs
        if apenas_orfas:
            # Subconsulta para encontrar tabelas que TÊM vínculos
            subquery_com_vinculos = db.session.query(CidadeAtendida.transportadora_id, CidadeAtendida.nome_tabela).distinct()
            
            # Aplica filtro para tabelas que NÃO estão na subconsulta (órfãs)
            query = query.filter(
                ~db.session.query(
                    literal(True)
                ).filter(
                    and_(
                        CidadeAtendida.transportadora_id == TabelaFrete.transportadora_id,
                        CidadeAtendida.nome_tabela == TabelaFrete.nome_tabela
                    )
                ).exists()
            )
        
        elif status == 'orfa':
            # Mesmo filtro para status órfã específico
            query = query.filter(
                ~db.session.query(
                    literal(True)
                ).filter(
                    and_(
                        CidadeAtendida.transportadora_id == TabelaFrete.transportadora_id,
                        CidadeAtendida.nome_tabela == TabelaFrete.nome_tabela
                    )
                ).exists()
            )
        
        elif status == 'ok':
            # Tabelas que TÊM vínculos na mesma transportadora
            query = query.filter(
                db.session.query(
                    literal(True)
                ).filter(
                    and_(
                        CidadeAtendida.transportadora_id == TabelaFrete.transportadora_id,
                        CidadeAtendida.nome_tabela == TabelaFrete.nome_tabela
                    )
                ).exists()
            )
        
        elif status == 'grupo_empresarial':
            # Filtra tabelas que têm vínculos em transportadoras de grupo empresarial
            # Lógica: tabela que NÃO tem vínculo na mesma transportadora
            # MAS tem vínculo em transportadora diferente (grupo empresarial)
            
            query = query.filter(
                # Não tem vínculo na mesma transportadora
                ~db.session.query(literal(True)).filter(
                    and_(
                        CidadeAtendida.transportadora_id == TabelaFrete.transportadora_id,
                        CidadeAtendida.nome_tabela == TabelaFrete.nome_tabela
                    )
                ).exists(),
                # Mas tem vínculo em transportadora diferente
                db.session.query(literal(True)).filter(
                    and_(
                        CidadeAtendida.nome_tabela == TabelaFrete.nome_tabela,
                        CidadeAtendida.transportadora_id != TabelaFrete.transportadora_id
                    )
                ).exists()
            )

    # 2) ORDENAÇÃO (sort)
    sort = request.args.get('sort', '')
    direction = request.args.get('direction', 'asc')

    # Mapeia colunas
    sortable_columns = {
        'transportadora':     Transportadora.razao_social,
        'uf_origem':          TabelaFrete.uf_origem,
        'uf_destino':         TabelaFrete.uf_destino,
        'nome_tabela':        TabelaFrete.nome_tabela,
        'tipo_carga':         TabelaFrete.tipo_carga,
        'modalidade':         TabelaFrete.modalidade,
        'frete_minimo_valor': TabelaFrete.frete_minimo_valor,
        'frete_minimo_peso':  TabelaFrete.frete_minimo_peso,
        'valor_kg':           TabelaFrete.valor_kg,
        'percentual_valor':   TabelaFrete.percentual_valor,
        'percentual_gris':    TabelaFrete.percentual_gris,
        'percentual_adv':     TabelaFrete.percentual_adv,
        'percentual_rca':     TabelaFrete.percentual_rca,
        'valor_despacho':     TabelaFrete.valor_despacho,
        'valor_cte':          TabelaFrete.valor_cte,
        'valor_tas':          TabelaFrete.valor_tas,
        'pedagio_por_100kg':  TabelaFrete.pedagio_por_100kg,
        'icms_incluso':       TabelaFrete.icms_incluso,
        'criado_por':         TabelaFrete.criado_por,
        'criado_em':          TabelaFrete.criado_em
    }

    if sort in sortable_columns:
        col = sortable_columns[sort]
        if direction == 'desc':
            query = query.order_by(col.desc())
        else:
            query = query.order_by(col.asc())
    else:
        # Padrão
        query = query.order_by(Transportadora.razao_social,
                               TabelaFrete.uf_origem,
                               TabelaFrete.uf_destino,
                               TabelaFrete.nome_tabela,
                               TabelaFrete.modalidade)

    # 3) PAGINAÇÃO
    page = request.args.get('page', 1, type=int)
    per_page = 20
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

    # 4) RENDER
    return render_template(
        'tabelas/listar_todas_tabelas.html',
        paginacao=paginacao,
        tabelas=paginacao.items,
        transportadoras=transportadoras,
        uf_list=uf_list,
        modalidades=modalidades,
        sort=sort,
        direction=direction
    )


@tabelas_bp.route('/editar_tabela_frete/<int:tabela_id>', methods=['GET', 'POST'])
@login_required
def editar_tabela_frete(tabela_id):
    tabela = TabelaFrete.query.get_or_404(tabela_id)

    if request.method == 'POST':
        form = TabelaFreteForm()
    else:
        form = TabelaFreteForm(obj=tabela)

    form.transportadora.choices = [(t.id, t.razao_social) for t in Transportadora.query.all()]
    form.uf_origem.choices = UF_LIST
    form.uf_destino.choices = UF_LIST

    if form.validate_on_submit():
        tabela.transportadora_id = form.transportadora.data
        tabela.uf_origem = form.uf_origem.data
        tabela.uf_destino = form.uf_destino.data
        tabela.nome_tabela = form.nome_tabela.data
        tabela.tipo_carga = form.tipo_carga.data
        tabela.modalidade = form.modalidade.data

        tabela.valor_kg = float(form.valor_kg.data) if form.valor_kg.data else 0.0
        tabela.frete_minimo_peso = float(form.frete_minimo_peso.data) if form.frete_minimo_peso.data else 0.0
        tabela.percentual_valor = float(form.percentual_valor.data) if form.percentual_valor.data else 0.0
        tabela.frete_minimo_valor = float(form.frete_minimo_valor.data) if form.frete_minimo_valor.data else 0.0
        tabela.percentual_gris = float(form.percentual_gris.data) if form.percentual_gris.data else 0.0
        tabela.percentual_adv = float(form.percentual_adv.data) if form.percentual_adv.data else 0.0
        tabela.percentual_rca = float(form.percentual_rca.data) if form.percentual_rca.data else 0.0
        tabela.pedagio_por_100kg = float(form.pedagio_por_100kg.data) if form.pedagio_por_100kg.data else 0.0
        tabela.valor_despacho = float(form.valor_despacho.data) if form.valor_despacho.data else 0.0
        tabela.valor_cte = float(form.valor_cte.data) if form.valor_cte.data else 0.0
        tabela.valor_tas = float(form.valor_tas.data) if form.valor_tas.data else 0.0

        tabela.icms_incluso = form.icms_incluso.data
        tabela.criado_por = current_user.nome

        db.session.commit()
        flash('Tabela atualizada com sucesso!', 'success')
        return redirect(url_for('tabelas.listar_todas_tabelas'))

    form.transportadora.data = tabela.transportadora_id
    tabelas = TabelaFrete.query.all()

    return render_template('tabelas/tabelas_frete.html', form=form, tabela=tabela, tabelas=tabelas)

@tabelas_bp.route('/excluir_tabela/<int:tabela_id>', methods=['POST'])
@login_required
def excluir_tabela(tabela_id):
    print("teste")
    try:
        data = request.get_json()
        validate_csrf(data.get('csrf_token'))
    except CSRFError:
        return jsonify({'success': False, 'message': 'Token CSRF inválido.'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro inesperado: {str(e)}'}), 400

    tabela = TabelaFrete.query.get_or_404(tabela_id)
    try:
        db.session.delete(tabela)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro interno: {e}'}), 500






