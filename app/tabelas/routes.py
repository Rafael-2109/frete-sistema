from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf.csrf import validate_csrf, CSRFError
from sqlalchemy import literal, and_

from app import db
import pandas as pd
from datetime import datetime

from app.tabelas.forms import TabelaFreteForm, ImportarTabelaFreteForm, GerarTemplateFreteForm
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
MODALIDADES_VALIDAS = ['FRETE VALOR', 'FRETE PESO','FIORINO', 'VAN/HR', 'MASTER', 'IVECO', '3/4', 'TOCO', 'TRUCK', 'CARRETA']

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
        rejeitadas_sem_vinculo = []
        
        try:
            # 📖 Ler o arquivo UMA vez para evitar problemas de arquivo fechado
            import io
            file_content = arquivo.read()
            df = pd.read_excel(io.BytesIO(file_content))
            
            # ✅ LIMPEZA PRÉVIA: Substitui valores NaN por 0 em campos numéricos
            campos_numericos = ['VALOR', 'PESO', 'FRETE PESO', 'FRETE VALOR', 'GRIS', 'ADV', 
                              'RCA SEGURO FLUVIAL %', 'DESPACHO / CTE / TAS', 'CTE', 'TAS', 
                              'PEDAGIO FRAÇÃO 100 KGS']
            for campo in campos_numericos:
                if campo in df.columns:
                    df[campo] = df[campo].fillna(0)
                    # Substitui valores 'nan' como string também
                    df[campo] = df[campo].replace(['nan', 'NaN', 'None', 'null', ''], 0)

            colunas_obrigatorias = [
                'ATIVO', 'CÓD. TRANSP', 'DESTINO', 'NOME TABELA',
                'CARGA', 'FRETE', 'INC.', 'ORIGEM'
            ]

            for coluna in colunas_obrigatorias:
                if coluna not in df.columns:
                    flash(f'Coluna obrigatória ausente: {coluna}', 'danger')
                    return redirect(request.url)

            for index, row in df.iterrows():
                print(f"📊 Processando linha {index + 2}: {dict(row)}")
                
                if str(row['ATIVO']).strip().upper() != 'A':
                    print(f"⏭️ Linha {index + 2} ignorada - ATIVO = {row['ATIVO']}")
                    continue  # Ignorar tabelas inativas

                cnpj = str(row['CÓD. TRANSP']).strip()
                uf_destino = str(row['DESTINO']).strip()
                nome_tabela = str(row['NOME TABELA']).strip()
                
                print(f"🔍 Dados extraídos - CNPJ: {cnpj}, UF: {uf_destino}, Tabela: '{nome_tabela}'")

                transportadora = Transportadora.query.filter_by(cnpj=cnpj).first()
                if not transportadora:
                    erros += 1
                    print(f"❌ Transportadora {cnpj} não encontrada (linha {index+2})")
                    flash(f"Transportadora {cnpj} não cadastrada (linha {index+2}). Por favor, cadastre a transportadora primeiro.", "danger")
                    continue
                
                print(f"✅ Transportadora encontrada: {transportadora.razao_social}")

                # ✅ VALIDAÇÃO: Verifica vínculos apenas se NOME TABELA estiver preenchido
                # Se NOME TABELA estiver vazio, permite importação (template)
                if nome_tabela:  # Só valida vínculos se nome da tabela estiver preenchido
                    vinculo_existente = CidadeAtendida.query.filter_by(
                        transportadora_id=transportadora.id,
                        uf=uf_destino,
                        nome_tabela=nome_tabela
                    ).first()

                    if not vinculo_existente:
                        # ❌ REJEITA: Tabela sem vínculo correspondente
                        rejeitadas_sem_vinculo.append({
                            'linha': index + 2,
                            'transportadora': transportadora.razao_social,
                            'uf_destino': uf_destino,
                            'nome_tabela': nome_tabela,
                            'modalidade': str(row['FRETE']).upper()
                        })
                        continue  # Pula esta linha - NÃO importa
                else:
                    # Template sem nome de tabela - gera nome automático
                    nome_tabela = f"TEMPLATE_{transportadora.razao_social}_{uf_destino}_{modalidade}"
                    print(f"📋 Template detectado - gerando nome automático: {nome_tabela}")

                tipo_carga = str(row['CARGA']).upper()
                modalidade = str(row['FRETE']).upper()

                # Mapear claramente para choices válidas
                modalidades_validas = {
                    'FRETE PESO': 'FRETE PESO',
                    'FRETE VALOR': 'FRETE VALOR',
                    'FIORINO': 'FIORINO',
                    'VAN/HR': 'VAN/HR',
                    'MASTER': 'MASTER',
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

                # Função para limpar valores nan/vazios
                def limpar_valor(valor):
                    if pd.isna(valor) or str(valor).lower() in ['nan', 'none', '', 'null']:
                        return 0
                    try:
                        return float(valor)
                    except (ValueError, TypeError):
                        return 0

                tabela_frete = TabelaFrete.query.filter_by(
                    transportadora_id=transportadora.id,
                    uf_origem=row['ORIGEM'],
                    uf_destino=uf_destino,
                    nome_tabela=nome_tabela,
                    modalidade=modalidade
                ).first()

                if tabela_frete:
                    
                    tabela_frete.frete_minimo_valor = round(limpar_valor(row.get('VALOR')), 2)
                    tabela_frete.frete_minimo_peso = round(limpar_valor(row.get('PESO')), 2)
                    tabela_frete.valor_kg = round(limpar_valor(row.get('FRETE PESO')), 6)
                    tabela_frete.percentual_valor = round(limpar_valor(row.get('FRETE VALOR')) * 100, 4)
                    tabela_frete.percentual_gris = round(limpar_valor(row.get('GRIS')) * 100, 4)
                    tabela_frete.percentual_adv = round(limpar_valor(row.get('ADV')) * 100, 4)
                    tabela_frete.percentual_rca = round(limpar_valor(row.get('RCA SEGURO FLUVIAL %')) * 100, 4)
                    tabela_frete.valor_despacho = round(limpar_valor(row.get('DESPACHO / CTE / TAS')), 2)
                    tabela_frete.valor_cte = round(limpar_valor(row.get('CTE')), 2)
                    tabela_frete.valor_tas = round(limpar_valor(row.get('TAS')), 2)
                    tabela_frete.pedagio_por_100kg = round(limpar_valor(row.get('PEDAGIO FRAÇÃO 100 KGS')), 2)
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
                        frete_minimo_valor=round(limpar_valor(row.get('VALOR')), 2),
                        frete_minimo_peso=round(limpar_valor(row.get('PESO')), 2),
                        valor_kg=round(limpar_valor(row.get('FRETE PESO')), 6),
                        percentual_valor=round(limpar_valor(row.get('FRETE VALOR')) * 100, 4),
                        percentual_gris=round(limpar_valor(row.get('GRIS')) * 100, 4),
                        percentual_adv=round(limpar_valor(row.get('ADV')) * 100, 4),
                        percentual_rca=round(limpar_valor(row.get('RCA SEGURO FLUVIAL %')) * 100, 4),
                        valor_despacho=round(limpar_valor(row.get('DESPACHO / CTE / TAS')), 2),
                        valor_cte=round(limpar_valor(row.get('CTE')), 2),
                        valor_tas=round(limpar_valor(row.get('TAS')), 2),
                        pedagio_por_100kg=round(limpar_valor(row.get('PEDAGIO FRAÇÃO 100 KGS')), 2),
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
                    frete_minimo_valor=round(limpar_valor(row.get('VALOR')), 2),
                    frete_minimo_peso=round(limpar_valor(row.get('PESO')), 2),
                    valor_kg=round(limpar_valor(row.get('FRETE PESO')), 6),
                    percentual_valor=round(limpar_valor(row.get('FRETE VALOR')) * 100, 4),
                    percentual_gris=round(limpar_valor(row.get('GRIS')) * 100, 4),
                    percentual_adv=round(limpar_valor(row.get('ADV')) * 100, 4),
                    percentual_rca=round(limpar_valor(row.get('RCA SEGURO FLUVIAL %')) * 100, 4),
                    valor_despacho=round(limpar_valor(row.get('DESPACHO / CTE / TAS')), 2),
                    valor_cte=round(limpar_valor(row.get('CTE')), 2),
                    valor_tas=round(limpar_valor(row.get('TAS')), 2),
                    pedagio_por_100kg=round(limpar_valor(row.get('PEDAGIO FRAÇÃO 100 KGS')), 2),
                    icms_incluso=True if str(row.get('INC.')).strip().upper() == 'S' else False,
                    criado_por=current_user.nome
                )
                db.session.add(historico)
                sucesso += 1
                print(f"✅ Tabela criada/atualizada com sucesso (linha {index + 2})")

            db.session.commit()
            print(f"💾 Commit realizado - {sucesso} tabelas processadas")
            
            # Relatório final da importação
            if rejeitadas_sem_vinculo:
                flash(f"❌ {len(rejeitadas_sem_vinculo)} tabela(s) REJEITADA(S) por não terem vínculos correspondentes:", "danger")
                for rejeitada in rejeitadas_sem_vinculo[:10]:  # Mostra apenas as primeiras 5
                    flash(f"• Linha {rejeitada['linha']}: {rejeitada['transportadora']} → {rejeitada['uf_destino']} → {rejeitada['nome_tabela']} → {rejeitada['modalidade']}", "warning")
                if len(rejeitadas_sem_vinculo) > 10:
                    flash(f"... e mais {len(rejeitadas_sem_vinculo) - 10} tabela(s). Importe os vínculos primeiro!", "warning")
            
            flash(f"Importação finalizada: {sucesso} inseridos/atualizados, {erros} erros, {len(rejeitadas_sem_vinculo)} rejeitadas", "info")
            
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
    modalidades = ['FRETE PESO', 'FRETE VALOR', 'FIORINO', 'VAN/HR', 'MASTER', 'IVECO', '3/4', 'TOCO', 'TRUCK', 'CARRETA']

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
    try:
        from app.utils.logging_config import log_performance, log_database_query
        import time
        
        start_time = time.time()
    except ImportError:
        pass
    transportadoras = Transportadora.query.order_by(Transportadora.razao_social).all()
    uf_list = UF_LIST  # seu array/lista de (UF, NomeUF)
    modalidades = ['FRETE PESO', 'FRETE VALOR', 'FIORINO', 'VAN/HR', 'MASTER', 'IVECO', '3/4', 'TOCO', 'TRUCK', 'CARRETA']

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
        # Filtra tabelas que atendem à cidade através dos vínculos
        from app.vinculos.models import CidadeAtendida
        from app.localidades.models import Cidade
        
        # Subconsulta para encontrar tabelas que atendem a cidade especificada
        subquery_cidades = db.session.query(CidadeAtendida.nome_tabela, CidadeAtendida.transportadora_id).join(
            Cidade, CidadeAtendida.cidade_id == Cidade.id
        ).filter(
            Cidade.nome.ilike(f"%{cidade}%")
        ).distinct().subquery()
        
        # Aplica o filtro na query principal
        query = query.filter(
            db.session.query(literal(True)).filter(
                and_(
                    subquery_cidades.c.transportadora_id == TabelaFrete.transportadora_id,
                    subquery_cidades.c.nome_tabela == TabelaFrete.nome_tabela
                )
            ).exists()
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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        tabela = TabelaFrete.query.get_or_404(tabela_id)
        logger.info(f"🔍 Editando tabela ID: {tabela_id} - {tabela.nome_tabela}")
    except Exception as e:
        logger.error(f"❌ Erro ao buscar tabela {tabela_id}: {str(e)}")
        flash(f'Erro ao buscar tabela: {str(e)}', 'error')
        return redirect(url_for('tabelas.listar_todas_tabelas'))

    if request.method == 'POST':
        form = TabelaFreteForm()
    else:
        form = TabelaFreteForm(obj=tabela)

    form.transportadora.choices = [(t.id, t.razao_social) for t in Transportadora.query.all()]
    form.uf_origem.choices = UF_LIST
    form.uf_destino.choices = UF_LIST

    if form.validate_on_submit():
        try:
            logger.info(f"📝 Iniciando atualização da tabela {tabela_id}")
            
            # Função para sanitizar strings e evitar problemas de encoding
            def sanitize_string(value):
                if value is None:
                    return None
                try:
                    # Converte para string e remove caracteres problemáticos
                    str_value = str(value).encode('utf-8', errors='ignore').decode('utf-8')
                    return str_value.strip()
                except (UnicodeDecodeError, UnicodeEncodeError) as e:
                    logger.warning(f"⚠️ Problema de encoding corrigido em: {value}")
                    return str(value).encode('ascii', errors='ignore').decode('ascii')
            
            # Função para conversão segura de float
            def safe_float(value):
                if not value or value == '':
                    return 0.0
                try:
                    return float(str(value).replace(',', '.'))
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ Valor numérico inválido: {value}, usando 0.0")
                    return 0.0
            
            # Atualizar campos com sanitização
            tabela.transportadora_id = form.transportadora.data
            tabela.uf_origem = sanitize_string(form.uf_origem.data)
            tabela.uf_destino = sanitize_string(form.uf_destino.data)
            tabela.nome_tabela = sanitize_string(form.nome_tabela.data)
            tabela.tipo_carga = sanitize_string(form.tipo_carga.data)
            tabela.modalidade = sanitize_string(form.modalidade.data)

            # Atualizar campos numéricos com validação
            tabela.valor_kg = safe_float(form.valor_kg.data)
            tabela.frete_minimo_peso = safe_float(form.frete_minimo_peso.data)
            tabela.percentual_valor = safe_float(form.percentual_valor.data)
            tabela.frete_minimo_valor = safe_float(form.frete_minimo_valor.data)
            tabela.percentual_gris = safe_float(form.percentual_gris.data)
            tabela.percentual_adv = safe_float(form.percentual_adv.data)
            tabela.percentual_rca = safe_float(form.percentual_rca.data)
            tabela.pedagio_por_100kg = safe_float(form.pedagio_por_100kg.data)
            tabela.valor_despacho = safe_float(form.valor_despacho.data)
            tabela.valor_cte = safe_float(form.valor_cte.data)
            tabela.valor_tas = safe_float(form.valor_tas.data)

            tabela.icms_incluso = form.icms_incluso.data
            tabela.criado_por = sanitize_string(current_user.nome)

            logger.info(f"💾 Salvando alterações da tabela {tabela_id}")
            db.session.commit()
            
            logger.info(f"✅ Tabela {tabela_id} atualizada com sucesso")
            flash('Tabela atualizada com sucesso!', 'success')
            return redirect(url_for('tabelas.listar_todas_tabelas'))
            
        except UnicodeDecodeError as e:
            logger.error(f"❌ Erro de encoding UTF-8 na tabela {tabela_id}: {str(e)}")
            db.session.rollback()
            flash(f'Erro de codificação: Verifique se não há caracteres especiais nos dados. Detalhes: {str(e)}', 'error')
            
        except ValueError as e:
            logger.error(f"❌ Erro de valor na tabela {tabela_id}: {str(e)}")
            db.session.rollback()
            flash(f'Erro nos valores numéricos: {str(e)}', 'error')
            
        except Exception as e:
            logger.error(f"❌ Erro inesperado na atualização da tabela {tabela_id}: {str(e)}")
            db.session.rollback()
            flash(f'Erro inesperado ao atualizar tabela: {str(e)}', 'error')

    form.transportadora.data = tabela.transportadora_id
    
    try:
        tabelas = TabelaFrete.query.all()
    except Exception as e:
        logger.error(f"❌ Erro ao listar tabelas: {str(e)}")
        tabelas = []
        flash(f'Aviso: Não foi possível carregar a lista de tabelas: {str(e)}', 'warning')

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


@tabelas_bp.route('/gerar_template_frete', methods=['GET', 'POST'])
@login_required
def gerar_template_frete():
    """Gera um template Excel pré-preenchido para importação de tabelas de frete"""
    form = GerarTemplateFreteForm()
    
    # Preenche as opções do formulário
    form.transportadora.choices = [(t.id, t.razao_social) for t in Transportadora.query.all()]
    form.uf_origem.choices = UF_LIST
    form.uf_destino.choices = UF_LIST
    
    if form.validate_on_submit():
        try:
            from flask import make_response
            import io
            
            # Busca dados da transportadora
            transportadora = Transportadora.query.get(form.transportadora.data)
            if not transportadora:
                flash('Transportadora não encontrada', 'error')
                return render_template('tabelas/gerar_template_frete.html', form=form)
            
            # Cria DataFrame com as colunas necessárias
            colunas = [
                'ATIVO', 'CÓD. TRANSP', 'ORIGEM', 'DESTINO', 'NOME TABELA',
                'CARGA', 'FRETE', 'INC.', 'VALOR', 'PESO', 'FRETE PESO', 
                'FRETE VALOR', 'GRIS', 'ADV', 'RCA SEGURO FLUVIAL %',
                'DESPACHO / CTE / TAS', 'CTE', 'TAS', 'PEDAGIO FRAÇÃO 100 KGS'
            ]
            
            # Cria dados pré-preenchidos
            dados = []
            for i in range(form.quantidade_linhas.data):
                linha = {
                    'ATIVO': 'A',
                    'CÓD. TRANSP': transportadora.cnpj,
                    'ORIGEM': form.uf_origem.data,
                    'DESTINO': form.uf_destino.data,
                    'NOME TABELA': '',  # Usuário deve preencher
                     'CARGA': form.tipo_carga.data,
                     'FRETE': form.modalidade.data,
                     'INC.': form.icms_incluso.data,
                     'VALOR': 0,
                    'PESO': 0,
                    'FRETE PESO': 0,
                    'FRETE VALOR': 0,
                    'GRIS': 0,
                    'ADV': 0,
                    'RCA SEGURO FLUVIAL %': 0,
                    'DESPACHO / CTE / TAS': 0,
                    'CTE': 0,
                    'TAS': 0,
                    'PEDAGIO FRAÇÃO 100 KGS': 0
                }
                dados.append(linha)
            
            # Cria DataFrame
            df = pd.DataFrame(dados, columns=colunas)
            
            # Cria arquivo Excel em memória
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Tabela_Frete', index=False)
                
                # Acessa a planilha para formatação
                worksheet = writer.sheets['Tabela_Frete']
                
                # Ajusta largura das colunas
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Congela primeira linha (cabeçalho)
                worksheet.freeze_panes = 'A2'
            
            output.seek(0)
            
            # Nome do arquivo (sanitizado)
            nome_transportadora = transportadora.razao_social.replace(' ', '_').replace('/', '_').replace('\\', '_')
            modalidade_sanitizada = form.modalidade.data.replace('/', '_').replace('\\', '_')
            nome_arquivo = f"template_frete_{nome_transportadora}_{form.uf_origem.data}_{form.uf_destino.data}_{form.tipo_carga.data}_{modalidade_sanitizada}.xlsx"
            
            # Cria resposta para download
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
            
            # Log para debug
            print(f"📊 Template gerado: {nome_arquivo}")
            print(f"📋 Dados: {form.quantidade_linhas.data} linhas, Transportadora: {transportadora.razao_social}")
            print(f"🔧 Configurações: {form.tipo_carga.data}, {form.modalidade.data}, ICMS: {form.icms_incluso.data}")
            
            flash(f'✅ Template gerado com sucesso! {form.quantidade_linhas.data} linhas pré-preenchidas.', 'success')
            return response
            
        except Exception as e:
            print(f"❌ Erro ao gerar template: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Erro ao gerar template: {str(e)}', 'error')
            return render_template('tabelas/gerar_template_frete.html', form=form)
    
    # Se chegou aqui, o formulário não foi validado
    if form.errors:
        print(f"❌ Erros de validação do formulário: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Erro no campo {field}: {error}', 'error')
    
    return render_template('tabelas/gerar_template_frete.html', form=form)






