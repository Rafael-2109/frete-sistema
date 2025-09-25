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
# float_or_none removido - usando converter_valor_brasileiro de valores_brasileiros
from app.utils.ufs import UF_LIST
from app.vinculos.models import CidadeAtendida

tabelas_bp = Blueprint('tabelas', __name__, url_prefix='/tabelas')

# Registrar filtros de formatação brasileira para o template
@tabelas_bp.app_template_filter('valor_br')
def valor_br_filter(value, decimais=2):
    """Filtro Jinja2 para formatar valores no padrão brasileiro"""
    if value is None or value == '':
        return 'R$ 0,00'
    
    try:
        valor_float = float(value)
        if decimais == 0:
            return f"R$ {valor_float:,.0f}".replace(',', '.')
        else:
            valor_formatado = f"{valor_float:,.{decimais}f}"
            valor_formatado = valor_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')
            return f"R$ {valor_formatado}"
    except (ValueError, TypeError):
        return 'R$ 0,00'

@tabelas_bp.app_template_filter('numero_br')
def numero_br_filter(value):
    """Filtro Jinja2 para formatar números no padrão brasileiro"""
    if value is None or value == '':
        return '0,00'
    
    try:
        valor_float = float(value)
        valor_formatado = f"{valor_float:,.2f}"
        valor_formatado = valor_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')
        return valor_formatado
    except (ValueError, TypeError):
        return '0,00'

@tabelas_bp.app_template_filter('peso_br')
def peso_br_filter(value):
    """Filtro Jinja2 para formatar peso no padrão brasileiro"""
    if value is None or value == '':
        return '0,0 kg'
        
    try:
        valor_float = float(value)
        if valor_float >= 1000:
            valor_formatado = f"{valor_float:,.1f}"
            valor_formatado = valor_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')
            return f"{valor_formatado} kg"
        else:
            valor_formatado = f"{valor_float:.1f}".replace('.', ',')
            return f"{valor_formatado} kg"
    except (ValueError, TypeError):
        return '0,0 kg'

@tabelas_bp.route('/tabelas_frete', methods=['GET', 'POST'])
@login_required
def cadastrar_tabela_frete():
    # Primeiro definir as choices
    transportadoras = [(t.id, t.razao_social) for t in Transportadora.query.all()]
    
    form = TabelaFreteForm()
    # Definir choices ANTES de qualquer validação
    form.transportadora.choices = transportadoras
    form.uf_origem.choices = UF_LIST
    form.uf_destino.choices = UF_LIST

    if request.method == 'POST':
        print(f"DEBUG: POST recebido")
        print(f"DEBUG: form.data ANTES da validação: {form.data}")
        print(f"DEBUG: form.validate(): {form.validate()}")
        print(f"DEBUG: form.errors APÓS validação: {form.errors}")
        print(f"DEBUG: form.transportadora.choices: {form.transportadora.choices[:3]}...")  # Primeiras 3 para não poluir log

    if form.validate_on_submit():
        try:
            from app.utils.tabela_frete_manager import TabelaFreteManager
            from app.utils.valores_brasileiros import converter_valor_brasileiro
            
            # Prepara dados do formulário com conversão de valores brasileiros
            dados_tabela = TabelaFreteManager.preparar_dados_formulario(form, converter_valor_brasileiro)
            
            # Cria TabelaFrete
            nova = TabelaFrete(
                transportadora_id=form.transportadora.data,
                uf_origem=form.uf_origem.data,
                uf_destino=form.uf_destino.data,
                tipo_carga=form.tipo_carga.data,
                criado_por=current_user.nome
            )
            TabelaFreteManager.atribuir_campos_tabela(nova, dados_tabela)
            db.session.add(nova)

            # Cria HistoricoTabelaFrete
            historico = HistoricoTabelaFrete(
                transportadora_id=form.transportadora.data,
                uf_origem=form.uf_origem.data,
                uf_destino=form.uf_destino.data,
                tipo_carga=form.tipo_carga.data,
                criado_por=current_user.nome
            )
            TabelaFreteManager.atribuir_campos_tabela(historico, dados_tabela)
            db.session.add(historico)

            db.session.commit()
            flash('Tabela de frete cadastrada com sucesso!', 'success')
            return redirect(url_for('tabelas.cadastrar_tabela_frete'))
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: Erro ao salvar tabela: {str(e)}")
            flash(f'Erro ao salvar tabela de frete: {str(e)}', 'error')

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
                print(f"📊 Processando linha {index + 2}: {dict(row)}")    # type: ignore # +2 para começar do 1
                
                if str(row['ATIVO']).strip().upper() != 'A':
                    print(f"⏭️ Linha {index + 2} ignorada - ATIVO = {row['ATIVO']}") # +2 para começar do 1 # type: ignore
                    continue  # Ignorar tabelas inativas

                cnpj = str(row['CÓD. TRANSP']).strip()
                uf_destino = str(row['DESTINO']).strip()
                nome_tabela = str(row['NOME TABELA']).strip()
                
                print(f"🔍 Dados extraídos - CNPJ: {cnpj}, UF: {uf_destino}, Tabela: '{nome_tabela}'")

                transportadora = Transportadora.query.filter_by(cnpj=cnpj).first()
                if not transportadora:
                    erros += 1
                    print(f"❌ Transportadora {cnpj} não encontrada (linha {index+2})") # type: ignore
                    flash(f"Transportadora {cnpj} não cadastrada (linha {index+2}). Por favor, cadastre a transportadora primeiro.", "danger") # type: ignore
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
                            'linha': index + 2, # type: ignore
                            'transportadora': transportadora.razao_social,
                            'uf_destino': uf_destino,
                            'nome_tabela': nome_tabela,
                            'modalidade': str(row['FRETE']).upper()
                        })
                        continue  # Pula esta linha - NÃO importa
                else:
                    # Template sem nome de tabela - gera nome automático
                    modalidade = str(row['FRETE']).upper()
                    nome_tabela = f"TEMPLATE_{transportadora.razao_social}_{uf_destino}_{modalidade}" # type: ignore
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
                    flash(f"Modalidade inválida '{modalidade}' (linha {index+2})", "danger") # type: ignore
                    continue

                modalidade = modalidades_validas[modalidade]

                if tipo_carga not in TIPOS_CARGA_VALIDOS:
                    erros += 1
                    flash(f"Tipo carga inválido '{tipo_carga}' (linha {index+2})", "danger") # type: ignore
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

                from app.utils.tabela_frete_manager import TabelaFreteManager
                
                # Prepara dados do CSV
                dados_csv = TabelaFreteManager.preparar_dados_csv(row, limpar_valor)
                dados_csv['modalidade'] = modalidade  # Usa modalidade processada
                dados_csv['nome_tabela'] = nome_tabela  # Usa nome_tabela processado
                
                if tabela_frete:
                    # Atualiza tabela existente
                    TabelaFreteManager.atribuir_campos_tabela(tabela_frete, dados_csv)
                    tabela_frete.criado_por = current_user.nome    
                else:
                    # Cria nova tabela
                    tabela_frete = TabelaFrete(
                        transportadora_id=transportadora.id,
                        uf_origem=str(row['ORIGEM']).strip(),
                        uf_destino=uf_destino,
                        tipo_carga=tipo_carga,
                        criado_por=current_user.nome
                    )
                    TabelaFreteManager.atribuir_campos_tabela(tabela_frete, dados_csv)
                    db.session.add(tabela_frete)

                # Cria histórico
                historico = HistoricoTabelaFrete(
                    transportadora_id=transportadora.id,
                    uf_origem=str(row['ORIGEM']).strip(),
                    uf_destino=uf_destino,
                    tipo_carga=tipo_carga,
                    criado_por=current_user.nome
                )
                TabelaFreteManager.atribuir_campos_tabela(historico, dados_csv)
                db.session.add(historico)
                sucesso += 1
                print(f"✅ Tabela criada/atualizada com sucesso (linha {index + 2})") # type: ignore

            db.session.commit()
            print(f"💾 Commit realizado - {sucesso} tabelas processadas")
            
            # Relatório final da importação
            if rejeitadas_sem_vinculo:
                flash(f"❌ {len(rejeitadas_sem_vinculo)} tabela(s) REJEITADA(S) por não terem vínculos correspondentes:", "danger")
                for rejeitada in rejeitadas_sem_vinculo[:10]:  # Mostra apenas as primeiras 5
                    flash(f"• Linha {rejeitada['linha']}: {rejeitada['transportadora']} → {rejeitada['uf_destino']} → {rejeitada['nome_tabela']} → {rejeitada['modalidade']}", "warning") # type: ignore
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
        'transportadora': Transportadora.razao_social,
        'uf_origem': HistoricoTabelaFrete.uf_origem,
        'uf_destino': HistoricoTabelaFrete.uf_destino,
        'nome_tabela': HistoricoTabelaFrete.nome_tabela,
        'tipo_carga': HistoricoTabelaFrete.tipo_carga,
        'modalidade': HistoricoTabelaFrete.modalidade,
        'frete_minimo_valor': HistoricoTabelaFrete.frete_minimo_valor,
        'frete_minimo_peso': HistoricoTabelaFrete.frete_minimo_peso,
        'valor_kg': HistoricoTabelaFrete.valor_kg,
        'percentual_valor': HistoricoTabelaFrete.percentual_valor,
        'percentual_gris': HistoricoTabelaFrete.percentual_gris,
        'percentual_adv': HistoricoTabelaFrete.percentual_adv,
        'percentual_rca': HistoricoTabelaFrete.percentual_rca,
        'valor_despacho': HistoricoTabelaFrete.valor_despacho,
        'valor_cte': HistoricoTabelaFrete.valor_cte,
        'valor_tas': HistoricoTabelaFrete.valor_tas,
        'pedagio_por_100kg': HistoricoTabelaFrete.pedagio_por_100kg,
        'icms_incluso': HistoricoTabelaFrete.icms_incluso,
        'criado_por': HistoricoTabelaFrete.criado_por,
        'criado_em': HistoricoTabelaFrete.criado_em
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
        'transportadora': Transportadora.razao_social,
        'uf_origem': TabelaFrete.uf_origem,
        'uf_destino': TabelaFrete.uf_destino,
        'nome_tabela': TabelaFrete.nome_tabela,
        'tipo_carga': TabelaFrete.tipo_carga,
        'modalidade': TabelaFrete.modalidade,
        'frete_minimo_valor': TabelaFrete.frete_minimo_valor,
        'frete_minimo_peso': TabelaFrete.frete_minimo_peso,
        'valor_kg': TabelaFrete.valor_kg,
        'percentual_valor': TabelaFrete.percentual_valor,
        'percentual_gris': TabelaFrete.percentual_gris,
        'percentual_adv': TabelaFrete.percentual_adv,
        'percentual_rca': TabelaFrete.percentual_rca,
        'valor_despacho': TabelaFrete.valor_despacho,
        'valor_cte': TabelaFrete.valor_cte,
        'valor_tas': TabelaFrete.valor_tas,
        'pedagio_por_100kg': TabelaFrete.pedagio_por_100kg,
        'icms_incluso': TabelaFrete.icms_incluso,
        'gris_minimo': TabelaFrete.gris_minimo,
        'adv_minimo': TabelaFrete.adv_minimo,
        'icms_proprio': TabelaFrete.icms_proprio,
        'criado_por': TabelaFrete.criado_por,
        'criado_em': TabelaFrete.criado_em
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
        # Setar o ID para validação customizada funcionar corretamente na edição
        form.id.data = str(tabela_id)
    else:
        # Importar função de formatação
        from app.utils.valores_brasileiros import formatar_valor_brasileiro

        # Criar formulário sem preencher automaticamente
        form = TabelaFreteForm()
        form.id.data = str(tabela_id)

        # Preencher campos básicos
        form.transportadora.data = tabela.transportadora_id
        form.uf_origem.data = tabela.uf_origem
        form.uf_destino.data = tabela.uf_destino
        form.nome_tabela.data = tabela.nome_tabela
        form.tipo_carga.data = tabela.tipo_carga
        form.modalidade.data = tabela.modalidade
        form.icms_incluso.data = tabela.icms_incluso

        # Formatar e preencher campos numéricos no padrão brasileiro
        # Campos de valor com 2 casas decimais
        form.valor_kg.data = formatar_valor_brasileiro(tabela.valor_kg, 4) if tabela.valor_kg else ''
        form.frete_minimo_peso.data = formatar_valor_brasileiro(tabela.frete_minimo_peso, 2) if tabela.frete_minimo_peso else ''
        form.frete_minimo_valor.data = formatar_valor_brasileiro(tabela.frete_minimo_valor, 2) if tabela.frete_minimo_valor else ''

        # Campos de percentual
        form.percentual_valor.data = formatar_valor_brasileiro(tabela.percentual_valor, 2) if tabela.percentual_valor else ''
        form.percentual_gris.data = formatar_valor_brasileiro(tabela.percentual_gris, 2) if tabela.percentual_gris else ''
        form.percentual_adv.data = formatar_valor_brasileiro(tabela.percentual_adv, 2) if tabela.percentual_adv else ''
        form.percentual_rca.data = formatar_valor_brasileiro(tabela.percentual_rca, 2) if tabela.percentual_rca else ''

        # Campos de valor mínimo
        form.gris_minimo.data = formatar_valor_brasileiro(tabela.gris_minimo, 2) if tabela.gris_minimo else ''
        form.adv_minimo.data = formatar_valor_brasileiro(tabela.adv_minimo, 2) if tabela.adv_minimo else ''

        # Campos de taxas
        form.valor_despacho.data = formatar_valor_brasileiro(tabela.valor_despacho, 2) if tabela.valor_despacho else ''
        form.valor_cte.data = formatar_valor_brasileiro(tabela.valor_cte, 2) if tabela.valor_cte else ''
        form.valor_tas.data = formatar_valor_brasileiro(tabela.valor_tas, 2) if tabela.valor_tas else ''
        form.pedagio_por_100kg.data = formatar_valor_brasileiro(tabela.pedagio_por_100kg, 2) if tabela.pedagio_por_100kg else ''

        # ICMS próprio
        form.icms_proprio.data = formatar_valor_brasileiro(tabela.icms_proprio, 2) if tabela.icms_proprio else ''

    # Sempre definir as choices ANTES da validação
    form.transportadora.choices = [(t.id, t.razao_social) for t in Transportadora.query.all()]
    form.uf_origem.choices = UF_LIST
    form.uf_destino.choices = UF_LIST
    
    # Debug
    if request.method == 'POST':
        logger.info(f"📋 POST recebido para edição - form.validate(): {form.validate()}")
        logger.info(f"📋 form.errors: {form.errors}")
        logger.info(f"📋 form.data: {form.data}")

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
            
            # Importa funções de conversão de valores brasileiros
            from app.utils.valores_brasileiros import converter_valor_brasileiro
            
            from app.utils.tabela_frete_manager import TabelaFreteManager
            
            # Atualizar campos básicos com sanitização
            tabela.transportadora_id = form.transportadora.data
            tabela.uf_origem = sanitize_string(form.uf_origem.data)
            tabela.uf_destino = sanitize_string(form.uf_destino.data)
            tabela.tipo_carga = sanitize_string(form.tipo_carga.data)
            tabela.criado_por = sanitize_string(current_user.nome)
            
            # Prepara e atribui campos de frete usando TabelaFreteManager com conversão brasileira
            dados_tabela = TabelaFreteManager.preparar_dados_formulario(form, converter_valor_brasileiro)
            # Aplica sanitização no nome_tabela e modalidade
            if 'nome_tabela' in dados_tabela:
                dados_tabela['nome_tabela'] = sanitize_string(dados_tabela['nome_tabela'])
            if 'modalidade' in dados_tabela:
                dados_tabela['modalidade'] = sanitize_string(dados_tabela['modalidade'])
            
            TabelaFreteManager.atribuir_campos_tabela(tabela, dados_tabela)

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
                'FRETE VALOR', 'GRIS', 'GRIS MINIMO', 'ADV', 'ADV MINIMO', 'RCA SEGURO FLUVIAL %',
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
                    'GRIS MINIMO': 0,
                    'ADV': 0,
                    'ADV MINIMO': 0,
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
                        except Exception as e:
                            print(f"Erro ao ajustar largura da coluna {column_letter}: {str(e)}")
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

@tabelas_bp.route('/exportar_tabelas', methods=['GET', 'POST'])
@login_required
def exportar_tabelas():
    """Exporta as tabelas filtradas para Excel"""
    try:
        from flask import make_response
        import io
        from app.utils.valores_brasileiros import formatar_valor_brasileiro
        
        # Constrói a mesma query da listagem
        query = TabelaFrete.query.join(Transportadora)
        
        # Aplica os mesmos filtros da listagem
        transportadora_id = request.args.get('transportadora', type=int)
        uf_destino = request.args.get('uf_destino', '')
        cidade = request.args.get('cidade', '')
        nome_tabela = request.args.get('nome_tabela', '')
        tipo_carga = request.args.get('tipo_carga', '')
        modalidade = request.args.get('modalidade', '')
        status = request.args.get('status', '')
        apenas_orfas = request.args.get('apenas_orfas', '')
        
        if transportadora_id:
            query = query.filter(TabelaFrete.transportadora_id == transportadora_id)
        
        if uf_destino:
            query = query.filter(TabelaFrete.uf_destino == uf_destino)
        
        if cidade:
            from app.vinculos.models import CidadeAtendida
            subquery_cidades = db.session.query(CidadeAtendida.nome_tabela, CidadeAtendida.transportadora_id).join(
                Cidade, CidadeAtendida.cidade_id == Cidade.id
            ).filter(
                Cidade.nome.ilike(f"%{cidade}%")
            ).distinct().subquery()
            
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
        
        # Filtros de status/órfãs
        if status or apenas_orfas:
            from app.vinculos.models import CidadeAtendida
            
            if apenas_orfas or status == 'orfa':
                query = query.filter(
                    ~db.session.query(literal(True)).filter(
                        and_(
                            CidadeAtendida.transportadora_id == TabelaFrete.transportadora_id,
                            CidadeAtendida.nome_tabela == TabelaFrete.nome_tabela
                        )
                    ).exists()
                )
            elif status == 'ok':
                query = query.filter(
                    db.session.query(literal(True)).filter(
                        and_(
                            CidadeAtendida.transportadora_id == TabelaFrete.transportadora_id,
                            CidadeAtendida.nome_tabela == TabelaFrete.nome_tabela
                        )
                    ).exists()
                )
            elif status == 'grupo_empresarial':
                query = query.filter(
                    ~db.session.query(literal(True)).filter(
                        and_(
                            CidadeAtendida.transportadora_id == TabelaFrete.transportadora_id,
                            CidadeAtendida.nome_tabela == TabelaFrete.nome_tabela
                        )
                    ).exists(),
                    db.session.query(literal(True)).filter(
                        and_(
                            CidadeAtendida.nome_tabela == TabelaFrete.nome_tabela,
                            CidadeAtendida.transportadora_id != TabelaFrete.transportadora_id
                        )
                    ).exists()
                )
        
        # Aplica ordenação
        query = query.order_by(
            Transportadora.razao_social,
            TabelaFrete.uf_origem,
            TabelaFrete.uf_destino,
            TabelaFrete.nome_tabela,
            TabelaFrete.modalidade
        )
        
        # Busca todas as tabelas (sem paginação para exportação)
        tabelas = query.all()
        
        # Cria DataFrame para exportação
        dados = []
        for tabela in tabelas:
            dados.append({
                'Transportadora': tabela.transportadora.razao_social,
                'CNPJ': tabela.transportadora.cnpj,
                'UF Origem': tabela.uf_origem,
                'UF Destino': tabela.uf_destino,
                'Nome Tabela': tabela.nome_tabela,
                'Tipo Carga': tabela.tipo_carga,
                'Modalidade': tabela.modalidade,
                'Frete Mín. Valor (R$)': formatar_valor_brasileiro(tabela.frete_minimo_valor),
                'Frete Mín. Peso (kg)': formatar_valor_brasileiro(tabela.frete_minimo_peso),
                'Valor/kg (R$)': formatar_valor_brasileiro(tabela.valor_kg, 4),
                '% Sobre Valor': formatar_valor_brasileiro(tabela.percentual_valor),
                '% GRIS': formatar_valor_brasileiro(tabela.percentual_gris),
                'GRIS Mín. (R$)': formatar_valor_brasileiro(tabela.gris_minimo) if tabela.gris_minimo else '',
                '% ADV': formatar_valor_brasileiro(tabela.percentual_adv),
                'ADV Mín. (R$)': formatar_valor_brasileiro(tabela.adv_minimo) if tabela.adv_minimo else '',
                '% RCA': formatar_valor_brasileiro(tabela.percentual_rca),
                'Despacho (R$)': formatar_valor_brasileiro(tabela.valor_despacho),
                'CTE (R$)': formatar_valor_brasileiro(tabela.valor_cte),
                'TAS (R$)': formatar_valor_brasileiro(tabela.valor_tas),
                'Pedágio/100kg (R$)': formatar_valor_brasileiro(tabela.pedagio_por_100kg),
                'ICMS Incluso': 'Sim' if tabela.icms_incluso else 'Não',
                '% ICMS Próprio': formatar_valor_brasileiro(tabela.icms_proprio) if tabela.icms_proprio else '',
                'Criado Por': tabela.criado_por,
                'Criado Em': tabela.criado_em.strftime('%d/%m/%Y %H:%M') if tabela.criado_em else ''
            })
        
        # Cria DataFrame
        df = pd.DataFrame(dados)
        
        # Cria arquivo Excel em memória
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Tabelas_Frete', index=False)
            
            # Acessa a planilha para formatação
            worksheet = writer.sheets['Tabelas_Frete']
            
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
        
        # Nome do arquivo com data/hora
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"tabelas_frete_{timestamp}.xlsx"
        
        # Cria resposta para download
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
        
        flash(f'✅ Exportação concluída! {len(tabelas)} tabelas exportadas.', 'success')
        return response
        
    except Exception as e:
        print(f"❌ Erro ao exportar tabelas: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao exportar tabelas: {str(e)}', 'error')
        return redirect(url_for('tabelas.listar_todas_tabelas'))
