from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, session, send_from_directory
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import and_, or_, desc, func
import os
import re
from werkzeug.utils import secure_filename
from app.transportadoras.models import Transportadora
from app.fretes.forms import LancamentoFreteirosForm
from datetime import datetime


from app import db

# 🔒 Importar decoradores de permissão
from app.utils.auth_decorators import require_financeiro, require_admin, require_profiles

from app.embarques.models import Embarque, EmbarqueItem
from app.faturamento.models import RelatorioFaturamentoImportado
from app.fretes.models import (
    FreteLancado, Frete, FaturaFrete, DespesaExtra, 
    ContaCorrenteTransportadora, AprovacaoFrete
)
from app.fretes.forms import (
    FreteForm, FaturaFreteForm, DespesaExtraForm,
    FiltroFretesForm, LancamentoCteForm
)

from app.transportadoras.models import Transportadora

from app.utils.calculadora_frete import calcular_valor_frete_pela_tabela

fretes_bp = Blueprint('fretes', __name__, url_prefix='/fretes')

# =================== ROTAS PARA O NOVO SISTEMA DE FRETES ===================

@fretes_bp.route('/')
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def index():
    """Dashboard principal do sistema de fretes"""
    # Estatísticas gerais
    total_fretes = Frete.query.count()
    fretes_pendentes = Frete.query.filter_by(status='PENDENTE').count()
    aprovacoes_pendentes = AprovacaoFrete.query.filter_by(status='PENDENTE').count()
    faturas_conferir = FaturaFrete.query.filter_by(status_conferencia='PENDENTE').count()
    
    # Fretes que podem precisar de correção nas NFs
    fretes_sem_nfs = Frete.query.filter(
        or_(
            Frete.numeros_nfs.is_(None),
            Frete.numeros_nfs == '',
            Frete.numeros_nfs == 'N/A'
        )
    ).count()
    
    # Fretes recentes
    fretes_recentes = Frete.query.order_by(desc(Frete.criado_em)).limit(10).all()
    
    return render_template('fretes/dashboard.html',
                         total_fretes=total_fretes,
                         fretes_pendentes=fretes_pendentes,
                         aprovacoes_pendentes=aprovacoes_pendentes,
                         faturas_conferir=faturas_conferir,
                         fretes_sem_nfs=fretes_sem_nfs,
                         fretes_recentes=fretes_recentes)

@fretes_bp.route('/listar')
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def listar_fretes():
    """Lista todos os fretes com filtros"""
    from app.transportadoras.models import Transportadora
    from sqlalchemy import cast, String
    
    form = FiltroFretesForm(request.args)
    
    # Popular choices de transportadoras no formulário
    transportadoras = Transportadora.query.all()
    form.transportadora_id.choices = [('', 'Todas as transportadoras')] + [(t.id, t.razao_social) for t in transportadoras]
    
    query = Frete.query
    
    # ✅ CORREÇÃO: Filtro por número do embarque usando cast para string
    if form.embarque_numero.data:
        query = query.join(Embarque).filter(cast(Embarque.numero, String).ilike(f'%{form.embarque_numero.data}%'))
    
    if form.cnpj_cliente.data:
        query = query.filter(Frete.cnpj_cliente.ilike(f'%{form.cnpj_cliente.data}%'))
    
    if form.nome_cliente.data:
        query = query.filter(Frete.nome_cliente.ilike(f'%{form.nome_cliente.data}%'))
    
    if form.numero_cte.data:
        query = query.filter(Frete.numero_cte.ilike(f'%{form.numero_cte.data}%'))
    
    if form.numero_fatura.data:
        query = query.join(FaturaFrete).filter(FaturaFrete.numero_fatura.ilike(f'%{form.numero_fatura.data}%'))
    
    # ✅ NOVO: Filtro por transportadora
    if form.transportadora_id.data:
        try:
            transportadora_id = int(form.transportadora_id.data)
            query = query.filter(Frete.transportadora_id == transportadora_id)
        except (ValueError, TypeError):
            pass
    
    if form.status.data:
        query = query.filter(Frete.status == form.status.data)
    
    if form.data_inicio.data:
        query = query.filter(Frete.criado_em >= form.data_inicio.data)
    
    if form.data_fim.data:
        query = query.filter(Frete.criado_em <= form.data_fim.data)
    
    fretes = query.order_by(desc(Frete.criado_em)).paginate(
        page=request.args.get('page', 1, type=int),
        per_page=50,
        error_out=False
    )
    
    return render_template('fretes/listar_fretes.html', fretes=fretes, form=form)

@fretes_bp.route('/lancar_cte', methods=['GET', 'POST'])
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def lancar_cte():
    """Lançamento de CTe com base na NF - primeiro mostra fretes que contêm a NF"""
    form = LancamentoCteForm()
    embarque_encontrado = None
    fretes_existentes = []  # Fretes já criados que contêm essa NF
    frete_para_processar = None  # Frete selecionado pelo usuário
    
    # Busca faturas disponíveis
    faturas_disponiveis = FaturaFrete.query.filter_by(status_conferencia='PENDENTE').order_by(desc(FaturaFrete.criado_em)).all()
    
    # ✅ CAPTURA FATURA PRÉ-SELECIONADA DO GET (quando vem de /fretes/lancar_cte?fatura_id=4)
    fatura_preselecionada_id = request.args.get('fatura_id', type=int)
    
    if form.validate_on_submit():
        numero_nf = form.numero_nf.data
        fatura_frete_id = request.form.get('fatura_frete_id')
        frete_selecionado_id = request.form.get('frete_selecionado_id')  # ID do frete escolhido pelo usuário
        
        if not fatura_frete_id:
            flash('Selecione uma fatura de frete!', 'error')
            return render_template('fretes/lancar_cte.html', form=form, faturas_disponiveis=faturas_disponiveis, fatura_preselecionada_id=fatura_preselecionada_id)
        
        # Busca NF no faturamento
        nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
        
        if not nf_faturamento:
            flash(f'NF {numero_nf} não encontrada no faturamento!', 'error')
            return render_template('fretes/lancar_cte.html', form=form, faturas_disponiveis=faturas_disponiveis, fatura_preselecionada_id=fatura_preselecionada_id)
        
        # Busca embarque que contém essa NF
        embarque_item = EmbarqueItem.query.filter_by(nota_fiscal=numero_nf).first()
        
        if not embarque_item:
            flash(f'NF {numero_nf} não encontrada em nenhum embarque!', 'error')
            return render_template('fretes/lancar_cte.html', form=form, faturas_disponiveis=faturas_disponiveis, fatura_preselecionada_id=fatura_preselecionada_id)
        
        embarque_encontrado = embarque_item.embarque
        
        # Verifica se a transportadora do embarque é a mesma da fatura
        fatura = FaturaFrete.query.get(fatura_frete_id)
        if fatura.transportadora_id != embarque_encontrado.transportadora_id:
            flash('A transportadora da fatura deve ser a mesma do embarque!', 'error')
            return render_template('fretes/lancar_cte.html', form=form, faturas_disponiveis=faturas_disponiveis, fatura_preselecionada_id=fatura_preselecionada_id)
        
        # ETAPA 1: Busca todos os fretes existentes que contêm essa NF
        fretes_existentes = Frete.query.filter(
            Frete.numeros_nfs.contains(numero_nf)
        ).all()
        
        # Se há um frete selecionado pelo usuário, prepara para processamento
        if frete_selecionado_id:
            frete_para_processar = Frete.query.get(frete_selecionado_id)
            if not frete_para_processar:
                flash('Frete selecionado não encontrado!', 'error')
                return redirect(url_for('fretes.lancar_cte'))
            
            # Verifica se já tem CTe lançado
            if frete_para_processar.numero_cte:
                flash(f'Este frete já possui CTe {frete_para_processar.numero_cte} lançado!', 'warning')
                return redirect(url_for('fretes.visualizar_frete', frete_id=frete_para_processar.id))
        
        # Se não há fretes existentes, verifica se pode criar um novo
        elif not fretes_existentes:
            cnpj_cliente = nf_faturamento.cnpj_cliente
            
            # Verifica se já existe frete para este CNPJ neste embarque
            frete_existente = Frete.query.filter(
                and_(
                    Frete.embarque_id == embarque_encontrado.id,
                    Frete.cnpj_cliente == cnpj_cliente
                )
            ).first()
            
            if frete_existente:
                flash(f'Já existe frete para o CNPJ {cnpj_cliente} no embarque {embarque_encontrado.numero}!', 'warning')
                return redirect(url_for('fretes.visualizar_frete', frete_id=frete_existente.id))
            
            # Pode criar novo frete - redireciona para criação
            flash(f'Nenhum frete encontrado com a NF {numero_nf}. Redirecionando para criação de novo frete...', 'info')
            return redirect(url_for('fretes.criar_novo_frete_por_nf', 
                                  numero_nf=numero_nf, 
                                  fatura_frete_id=fatura_frete_id))
    
    return render_template('fretes/lancar_cte.html', 
                         form=form,
                         embarque_encontrado=embarque_encontrado,
                         fretes_existentes=fretes_existentes,
                         frete_para_processar=frete_para_processar,
                         faturas_disponiveis=faturas_disponiveis,
                         fatura_preselecionada_id=fatura_preselecionada_id)

@fretes_bp.route('/criar_novo_frete_por_nf')
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def criar_novo_frete_por_nf():
    """Cria novo frete baseado em uma NF específica"""
    numero_nf = request.args.get('numero_nf')
    fatura_frete_id = request.args.get('fatura_frete_id')
    
    if not numero_nf or not fatura_frete_id:
        flash('Parâmetros inválidos!', 'error')
        return redirect(url_for('fretes.lancar_cte'))
    
    # Busca NF no faturamento
    nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
    if not nf_faturamento:
        flash(f'NF {numero_nf} não encontrada no faturamento!', 'error')
        return redirect(url_for('fretes.lancar_cte'))
    
    # Busca embarque que contém essa NF
    embarque_item = EmbarqueItem.query.filter_by(nota_fiscal=numero_nf).first()
    if not embarque_item:
        flash(f'NF {numero_nf} não encontrada em nenhum embarque!', 'error')
        return redirect(url_for('fretes.lancar_cte'))
    
    embarque_encontrado = embarque_item.embarque
    cnpj_cliente = nf_faturamento.cnpj_cliente
    
    # Busca todas as NFs do mesmo CNPJ neste embarque
    outras_nfs = RelatorioFaturamentoImportado.query.filter_by(cnpj_cliente=cnpj_cliente).all()
    numeros_nfs_cnpj = [nf.numero_nf for nf in outras_nfs]
    
    itens_embarque_cnpj = EmbarqueItem.query.filter(
        and_(
            EmbarqueItem.embarque_id == embarque_encontrado.id,
            EmbarqueItem.nota_fiscal.in_(numeros_nfs_cnpj)
        )
    ).all()
    
    if not itens_embarque_cnpj:
        flash(f'Nenhuma NF do CNPJ {cnpj_cliente} encontrada no embarque {embarque_encontrado.numero}!', 'error')
        return redirect(url_for('fretes.lancar_cte'))
    
    # Prepara dados para lançamento do frete
    total_peso = sum(float(nf.peso_bruto or 0) for nf in outras_nfs if nf.numero_nf in [item.nota_fiscal for item in itens_embarque_cnpj])
    total_valor = sum(float(nf.valor_total or 0) for nf in outras_nfs if nf.numero_nf in [item.nota_fiscal for item in itens_embarque_cnpj])
    numeros_nfs = ','.join([item.nota_fiscal for item in itens_embarque_cnpj])
    
    frete_data = {
        'embarque': embarque_encontrado,
        'cnpj_cliente': cnpj_cliente,
        'nome_cliente': nf_faturamento.nome_cliente,
        'transportadora_id': embarque_encontrado.transportadora_id,
        'tipo_carga': embarque_encontrado.tipo_carga,
        'peso_total': total_peso,
        'valor_total_nfs': total_valor,
        'quantidade_nfs': len(itens_embarque_cnpj),
        'numeros_nfs': numeros_nfs,
        'itens_embarque': itens_embarque_cnpj,
        'fatura_frete_id': fatura_frete_id
    }
    
    return render_template('fretes/criar_novo_frete.html', 
                         frete_data=frete_data,
                         numero_nf_original=numero_nf)

@fretes_bp.route('/processar_cte_frete_existente', methods=['POST'])
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def processar_cte_frete_existente():
    """Processa lançamento de CTe em frete já existente"""
    try:
        frete_id = request.form.get('frete_id')
        fatura_frete_id = request.form.get('fatura_frete_id')
        
        if not frete_id:
            flash('ID do frete não informado!', 'error')
            return redirect(url_for('fretes.lancar_cte'))
        
        if not fatura_frete_id:
            flash('ID da fatura não informado!', 'error')
            return redirect(url_for('fretes.lancar_cte'))
        
        frete = Frete.query.get_or_404(frete_id)
        fatura = FaturaFrete.query.get_or_404(fatura_frete_id)
        
        # Verifica se já tem CTe lançado
        if frete.numero_cte:
            flash(f'Este frete já possui CTe {frete.numero_cte} lançado!', 'warning')
            return redirect(url_for('fretes.visualizar_frete', frete_id=frete.id))
        
        # ✅ VALIDAÇÃO: Transportadora da fatura deve ser a mesma do frete
        if frete.transportadora_id != fatura.transportadora_id:
            flash(f'❌ Erro: A transportadora da fatura ({fatura.transportadora.razao_social}) é diferente da transportadora do frete ({frete.transportadora.razao_social})!', 'error')
            return redirect(url_for('fretes.lancar_cte', fatura_id=fatura_frete_id))
        
        # ✅ VINCULA A FATURA AO FRETE EXISTENTE
        if not frete.fatura_frete_id:
            frete.fatura_frete_id = fatura_frete_id
            flash(f'✅ Fatura {fatura.numero_fatura} vinculada ao frete #{frete.id}', 'success')
        elif frete.fatura_frete_id != int(fatura_frete_id):
            # Se já tem fatura vinculada mas é diferente, alerta
            fatura_atual = frete.fatura_frete
            flash(f'⚠️ Atenção: Frete já tinha fatura {fatura_atual.numero_fatura} vinculada. Trocando para {fatura.numero_fatura}', 'warning')
            frete.fatura_frete_id = fatura_frete_id
        
        # ✅ PRÉ-PREENCHE VENCIMENTO DA FATURA
        if fatura.vencimento and not frete.vencimento:
            frete.vencimento = fatura.vencimento
            flash(f'📅 Vencimento preenchido automaticamente: {fatura.vencimento.strftime("%d/%m/%Y")}', 'info')
        
        db.session.commit()
        
        # Redireciona para edição do frete para lançar CTe
        flash(f'Frete #{frete.id} selecionado. Agora lance os dados do CTe.', 'info')
        return redirect(url_for('fretes.editar_frete', frete_id=frete.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao processar frete: {str(e)}', 'error')
        return redirect(url_for('fretes.lancar_cte'))

@fretes_bp.route('/processar_lancamento_frete', methods=['POST'])
@login_required
def processar_lancamento_frete():
    """Processa o lançamento efetivo do frete"""
    try:
        # Dados do formulário
        embarque_id = request.form.get('embarque_id')
        cnpj_cliente = request.form.get('cnpj_cliente')
        nome_cliente = request.form.get('nome_cliente')
        transportadora_id = request.form.get('transportadora_id')
        tipo_carga = request.form.get('tipo_carga')
        peso_total = float(request.form.get('peso_total'))
        valor_total_nfs = float(request.form.get('valor_total_nfs'))
        quantidade_nfs = int(request.form.get('quantidade_nfs'))
        numeros_nfs = request.form.get('numeros_nfs')
        fatura_frete_id = request.form.get('fatura_frete_id')
        
        embarque = Embarque.query.get_or_404(embarque_id)
        
        # Pega dados da tabela conforme tipo de carga
        if tipo_carga == 'DIRETA':
            # Para carga direta, dados vêm do embarque
            tabela_dados = {
                'modalidade': embarque.modalidade,
                'nome_tabela': embarque.tabela_nome_tabela,
                'valor_kg': embarque.tabela_valor_kg,
                'percentual_valor': embarque.tabela_percentual_valor,
                'frete_minimo_valor': embarque.tabela_frete_minimo_valor,
                'frete_minimo_peso': embarque.tabela_frete_minimo_peso,
                'icms': embarque.tabela_icms,
                'percentual_gris': embarque.tabela_percentual_gris,
                'pedagio_por_100kg': embarque.tabela_pedagio_por_100kg,
                'valor_tas': embarque.tabela_valor_tas,
                'percentual_adv': embarque.tabela_percentual_adv,
                'percentual_rca': embarque.tabela_percentual_rca,
                'valor_despacho': embarque.tabela_valor_despacho,
                'valor_cte': embarque.tabela_valor_cte,
                'icms_incluso': embarque.tabela_icms_incluso,
                'icms_destino': embarque.icms_destino or 0
            }
        else:
            # Para carga fracionada, dados vêm de qualquer item do CNPJ
            item_referencia = EmbarqueItem.query.filter(
                and_(
                    EmbarqueItem.embarque_id == embarque_id,
                    EmbarqueItem.cnpj_cliente == cnpj_cliente
                )
            ).first()
            
            tabela_dados = {
                'modalidade': item_referencia.modalidade,
                'nome_tabela': item_referencia.tabela_nome_tabela,
                'valor_kg': item_referencia.tabela_valor_kg,
                'percentual_valor': item_referencia.tabela_percentual_valor,
                'frete_minimo_valor': item_referencia.tabela_frete_minimo_valor,
                'frete_minimo_peso': item_referencia.tabela_frete_minimo_peso,
                'icms': item_referencia.tabela_icms,
                'percentual_gris': item_referencia.tabela_percentual_gris,
                'pedagio_por_100kg': item_referencia.tabela_pedagio_por_100kg,
                'valor_tas': item_referencia.tabela_valor_tas,
                'percentual_adv': item_referencia.tabela_percentual_adv,
                'percentual_rca': item_referencia.tabela_percentual_rca,
                'valor_despacho': item_referencia.tabela_valor_despacho,
                'valor_cte': item_referencia.tabela_valor_cte,
                'icms_incluso': item_referencia.tabela_icms_incluso,
                'icms_destino': item_referencia.icms_destino or 0
            }
        
        # Calcula valor cotado usando a tabela
        valor_cotado = calcular_valor_frete_pela_tabela(tabela_dados, peso_total, valor_total_nfs)
        
        # Cria o frete
        novo_frete = Frete(
            embarque_id=embarque_id,
            cnpj_cliente=cnpj_cliente,
            nome_cliente=nome_cliente,
            transportadora_id=transportadora_id,
            tipo_carga=tipo_carga,
            modalidade=tabela_dados['modalidade'],
            uf_destino=embarque.itens[0].uf_destino,  # Pega do primeiro item
            cidade_destino=embarque.itens[0].cidade_destino,
            peso_total=peso_total,
            valor_total_nfs=valor_total_nfs,
            quantidade_nfs=quantidade_nfs,
            numeros_nfs=numeros_nfs,
            # Dados da tabela
            tabela_nome_tabela=tabela_dados['nome_tabela'],
            tabela_valor_kg=tabela_dados['valor_kg'],
            tabela_percentual_valor=tabela_dados['percentual_valor'],
            tabela_frete_minimo_valor=tabela_dados['frete_minimo_valor'],
            tabela_frete_minimo_peso=tabela_dados['frete_minimo_peso'],
            tabela_icms=tabela_dados['icms'],
            tabela_percentual_gris=tabela_dados['percentual_gris'],
            tabela_pedagio_por_100kg=tabela_dados['pedagio_por_100kg'],
            tabela_valor_tas=tabela_dados['valor_tas'],
            tabela_percentual_adv=tabela_dados['percentual_adv'],
            tabela_percentual_rca=tabela_dados['percentual_rca'],
            tabela_valor_despacho=tabela_dados['valor_despacho'],
            tabela_valor_cte=tabela_dados['valor_cte'],
            tabela_icms_incluso=tabela_dados['icms_incluso'],
            tabela_icms_destino=tabela_dados['icms_destino'],
            # Valores
            valor_cotado=valor_cotado,
            valor_considerado=valor_cotado,  # Inicialmente igual ao cotado
            # Fatura
            fatura_frete_id=fatura_frete_id,
            # Controle
            criado_por=current_user.nome,
            lancado_em=datetime.utcnow(),
            lancado_por=current_user.nome
        )
        
        db.session.add(novo_frete)
        db.session.commit()
        
        flash(f'Frete lançado com sucesso! Valor cotado: R$ {valor_cotado:.2f}', 'success')
        return redirect(url_for('fretes.visualizar_frete', frete_id=novo_frete.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao lançar frete: {str(e)}', 'error')
        return redirect(url_for('fretes.lancar_cte'))



@fretes_bp.route('/<int:frete_id>')
@login_required
def visualizar_frete(frete_id):
    """Visualiza detalhes de um frete específico"""
    frete = Frete.query.get_or_404(frete_id)
    despesas_extras = DespesaExtra.query.filter_by(frete_id=frete_id).all()
    movimentacoes_conta = ContaCorrenteTransportadora.query.filter_by(frete_id=frete_id).all()
    
    return render_template('fretes/visualizar_frete.html',
                         frete=frete,
                         despesas_extras=despesas_extras,
                         movimentacoes_conta=movimentacoes_conta)

@fretes_bp.route('/<int:frete_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_frete(frete_id):
    """Edita dados do CTe e valores do frete"""
    frete = Frete.query.get_or_404(frete_id)
    
    # ✅ VALIDAÇÃO: Não permitir lançar CTe sem fatura vinculada
    if not frete.fatura_frete_id:
        flash('❌ Este frete não possui fatura vinculada! Para lançar CTe é obrigatório ter fatura.', 'error')
        flash('💡 Fluxo correto: Fretes → Faturas → Criar Fatura → Lançar CTe através da fatura', 'info')
        flash('🔄 Ou se você já tem uma fatura, use: Fretes → Lançar CTe → Selecione a fatura → Busque pela NF', 'info')
        return redirect(url_for('fretes.visualizar_frete', frete_id=frete.id))
    
    form = FreteForm(obj=frete)
    
    # ✅ CORREÇÃO: Auto-preencher vencimento da fatura
    if frete.fatura_frete and frete.fatura_frete.vencimento and not frete.vencimento:
        frete.vencimento = frete.fatura_frete.vencimento
        form.vencimento.data = frete.fatura_frete.vencimento
    
    if form.validate_on_submit():
        # ✅ FUNÇÃO PARA CONVERTER VALORES COM VÍRGULA
        def converter_valor_brasileiro(valor_str):
            """Converte valor brasileiro (1.234,56) para float"""
            if not valor_str or valor_str.strip() == '':
                return None
            return float(valor_str.replace('.', '').replace(',', '.'))
        
        frete.numero_cte = form.numero_cte.data
        # ✅ REMOVIDO: data_emissao_cte (conforme solicitado)
        frete.vencimento = form.vencimento.data
        
        # ✅ CONVERTENDO VALORES COM VÍRGULA
        frete.valor_cte = converter_valor_brasileiro(form.valor_cte.data)
        frete.valor_considerado = converter_valor_brasileiro(form.valor_considerado.data)
        frete.valor_pago = converter_valor_brasileiro(form.valor_pago.data)
        
        frete.considerar_diferenca = form.considerar_diferenca.data
        frete.observacoes_aprovacao = form.observacoes_aprovacao.data
        
        # Verifica se precisa de aprovação
        requer_aprovacao = False
        motivo_aprovacao = ""
        
        # Regra 1: Diferença entre Valor Considerado e Valor Cotado > R$ 5,00
        if frete.valor_considerado and frete.valor_cotado:
            diferenca_considerado_cotado = abs(frete.valor_considerado - frete.valor_cotado)
            if diferenca_considerado_cotado > 5.00:
                requer_aprovacao = True
                motivo_aprovacao += f"Diferença de R$ {diferenca_considerado_cotado:.2f} entre valor considerado e cotado. "
        
        # Regra 2: Diferença entre Valor Pago e Valor Cotado > R$ 5,00
        if frete.valor_pago and frete.valor_cotado:
            diferenca_pago_cotado = abs(frete.valor_pago - frete.valor_cotado)
            if diferenca_pago_cotado > 5.00:
                requer_aprovacao = True
                motivo_aprovacao += f"Diferença de R$ {diferenca_pago_cotado:.2f} entre valor pago e cotado. "
        
        # ✅ NOVA LÓGICA: Baseada em diferença de R$ 5,00
        if requer_aprovacao:
            frete.requer_aprovacao = True
            frete.status = 'EM_TRATATIVA'  # Novo status
            
            # Remove aprovações antigas
            AprovacaoFrete.query.filter_by(frete_id=frete.id).delete()
            
            # Cria nova solicitação de aprovação
            aprovacao = AprovacaoFrete(
                frete_id=frete.id,
                solicitado_por=current_user.nome,
                motivo_solicitacao=motivo_aprovacao.strip()
            )
            db.session.add(aprovacao)
        else:
            # Se não requer aprovação, marca como lançado
            frete.status = 'LANCADO'
            frete.lancado_em = datetime.utcnow()
            frete.lancado_por = current_user.nome
        
        # ✅ NOVA LÓGICA: Conta corrente baseada na função deve_lancar_conta_corrente
        deve_lancar, motivo = frete.deve_lancar_conta_corrente()
        
        if deve_lancar and frete.valor_pago and frete.valor_considerado:
            diferenca = frete.diferenca_considerado_pago()
            if diferenca != 0:
                # Remove movimentações antigas deste frete
                ContaCorrenteTransportadora.query.filter_by(frete_id=frete.id).delete()
                
                # Cria nova movimentação
                tipo_mov = 'CREDITO' if diferenca > 0 else 'DEBITO'
                descricao = f'Frete {frete.id} - CTe {frete.numero_cte} - {motivo}'
                
                movimentacao = ContaCorrenteTransportadora(
                    transportadora_id=frete.transportadora_id,
                    frete_id=frete.id,
                    tipo_movimentacao=tipo_mov,
                    valor_diferenca=abs(diferenca),
                    valor_credito=diferenca if diferenca > 0 else 0,
                    valor_debito=abs(diferenca) if diferenca < 0 else 0,
                    descricao=descricao,
                    criado_por=current_user.nome
                )
                db.session.add(movimentacao)
        
        db.session.commit()
        flash('Frete atualizado com sucesso!', 'success')
        return redirect(url_for('fretes.visualizar_frete', frete_id=frete.id))
    
    return render_template('fretes/editar_frete.html', form=form, frete=frete)

@fretes_bp.route('/<int:frete_id>/analise_diferencas')
@login_required
def analise_diferencas(frete_id):
    """Mostra análise detalhada das diferenças com dados da tabela"""
    frete = Frete.query.get_or_404(frete_id)
    
    # Dados da tabela usada no cálculo
    tabela_dados = {
        'nome_tabela': frete.tabela_nome_tabela,
        'valor_kg': frete.tabela_valor_kg,
        'percentual_valor': frete.tabela_percentual_valor,
        'frete_minimo_valor': frete.tabela_frete_minimo_valor,
        'frete_minimo_peso': frete.tabela_frete_minimo_peso,
        'icms': frete.tabela_icms,
        'percentual_gris': frete.tabela_percentual_gris,
        'pedagio_por_100kg': frete.tabela_pedagio_por_100kg,
        'valor_tas': frete.tabela_valor_tas,
        'percentual_adv': frete.tabela_percentual_adv,
        'percentual_rca': frete.tabela_percentual_rca,
        'valor_despacho': frete.tabela_valor_despacho,
        'valor_cte': frete.tabela_valor_cte,
        'icms_incluso': frete.tabela_icms_incluso,
        'icms_destino': frete.tabela_icms_destino
    }
    
    # Calcula cada componente do frete separadamente
    peso_real = frete.peso_total
    valor_mercadoria = frete.valor_total_nfs
    
    # ✅ PESO CONSIDERADO (real vs mínimo) - CORRETO conforme calculadora_frete.py
    peso_minimo_tabela = frete.tabela_frete_minimo_peso or 0
    peso_considerado = max(peso_real, peso_minimo_tabela)
    
    # ✅ COMPONENTES BÁSICOS - CORRETO: SOMA peso + valor (não max)
    frete_peso = (peso_considerado * (frete.tabela_valor_kg or 0)) if frete.tabela_valor_kg else 0
    frete_valor = (valor_mercadoria * ((frete.tabela_percentual_valor or 0) / 100)) if frete.tabela_percentual_valor else 0
    
    # ✅ FRETE BASE - CORRETO: SOMA peso + valor conforme calculadora_frete.py linha 143
    frete_base = frete_peso + frete_valor
    
    # ✅ COMPONENTES ADICIONAIS - CORRETO: todos sobre valor da mercadoria conforme calculadora_frete.py
    gris = (valor_mercadoria * ((frete.tabela_percentual_gris or 0) / 100)) if frete.tabela_percentual_gris else 0
    adv = (valor_mercadoria * ((frete.tabela_percentual_adv or 0) / 100)) if frete.tabela_percentual_adv else 0
    rca = (valor_mercadoria * ((frete.tabela_percentual_rca or 0) / 100)) if frete.tabela_percentual_rca else 0
    
    # ✅ PEDÁGIO - CORRETO: por frações de 100kg conforme calculadora_frete.py
    if frete.tabela_pedagio_por_100kg and peso_considerado > 0:
        fracoes_100kg = int((peso_considerado - 1) // 100) + 1  # Arredonda para cima
        pedagio = fracoes_100kg * frete.tabela_pedagio_por_100kg
    else:
        pedagio = 0
    
    # ✅ VALORES FIXOS - CORRETO: conforme calculadora_frete.py
    tas = frete.tabela_valor_tas or 0
    despacho = frete.tabela_valor_despacho or 0
    valor_cte_tabela = frete.tabela_valor_cte or 0
    
    # ✅ TOTAL LÍQUIDO (sem ICMS) - ANTES do valor mínimo
    total_liquido_antes_minimo = frete_base + gris + adv + rca + pedagio + tas + despacho + valor_cte_tabela
    
    # ✅ APLICA VALOR MÍNIMO AO TOTAL LÍQUIDO - CORRETO conforme calculadora_frete.py linha 218
    frete_minimo_valor = frete.tabela_frete_minimo_valor or 0
    total_liquido = max(total_liquido_antes_minimo, frete_minimo_valor)
    ajuste_minimo_valor = total_liquido - total_liquido_antes_minimo if total_liquido > total_liquido_antes_minimo else 0
    
    # ✅ ICMS correto (usando icms_destino) - percentual já está em decimal
    percentual_icms_cotacao = frete.tabela_icms_destino or 0
    
    # Total bruto com ICMS embutido (se houver ICMS)
    if percentual_icms_cotacao > 0:
        # Fórmula: valor_com_icms = valor_sem_icms / (1 - icms_decimal)
        total_bruto_cotacao = total_liquido / (1 - percentual_icms_cotacao)
        valor_icms_cotacao = total_bruto_cotacao - total_liquido
    else:
        total_bruto_cotacao = total_liquido
        valor_icms_cotacao = 0

    
    # ✅ MONTANDO ESTRUTURA CORRETA para o template conforme calculadora_frete.py
    componentes = [
        {
            'nome': 'Peso Considerado',
            'valor_tabela': f'Mín: {peso_minimo_tabela:.2f} kg',
            'valor_usado': f'{peso_real:.2f} kg',
            'formula': f'max({peso_real:.2f}, {peso_minimo_tabela:.2f})',
            'valor_calculado': peso_considerado,
            'unidade': 'kg',
            'tipo': 'peso'
        },
        {
            'nome': 'Frete por Peso',
            'valor_tabela': f'R$ {frete.tabela_valor_kg or 0:.4f}/kg',
            'valor_usado': f'{peso_considerado:.2f} kg' if (frete.tabela_valor_kg or 0) > 0 else '-',
            'formula': f'{peso_considerado:.2f} × {frete.tabela_valor_kg or 0:.4f}' if (frete.tabela_valor_kg or 0) > 0 else '-',
            'valor_calculado': frete_peso,
            'unidade': 'R$',
            'tipo': 'valor'
        },
        {
            'nome': 'Frete por Valor (%)',
            'valor_tabela': f'{frete.tabela_percentual_valor or 0:.2f}%',
            'valor_usado': f'R$ {valor_mercadoria:.2f}' if (frete.tabela_percentual_valor or 0) > 0 else '-',
            'formula': f'{valor_mercadoria:.2f} × {frete.tabela_percentual_valor or 0:.2f}%' if (frete.tabela_percentual_valor or 0) > 0 else '-',
            'valor_calculado': frete_valor,
            'unidade': 'R$',
            'tipo': 'valor'
        },
        {
            'nome': 'Frete Base (SOMA)',
            'valor_tabela': 'Peso + Valor',
            'valor_usado': f'R$ {frete_peso:.2f} + R$ {frete_valor:.2f}',
            'formula': f'{frete_peso:.2f} + {frete_valor:.2f}',
            'valor_calculado': frete_base,
            'unidade': 'R$',
            'tipo': 'subtotal'
        },
        {
            'nome': 'GRIS (% s/ Mercadoria)',
            'valor_tabela': f'{frete.tabela_percentual_gris or 0:.2f}%',
            'valor_usado': f'R$ {valor_mercadoria:.2f}' if (frete.tabela_percentual_gris or 0) > 0 else '-',
            'formula': f'{valor_mercadoria:.2f} × {frete.tabela_percentual_gris or 0:.2f}%' if (frete.tabela_percentual_gris or 0) > 0 else '-',
            'valor_calculado': gris,
            'unidade': 'R$',
            'tipo': 'valor'
        },
        {
            'nome': 'ADV (% s/ Mercadoria)',
            'valor_tabela': f'{frete.tabela_percentual_adv or 0:.2f}%',
            'valor_usado': f'R$ {valor_mercadoria:.2f}' if (frete.tabela_percentual_adv or 0) > 0 else '-',
            'formula': f'{valor_mercadoria:.2f} × {frete.tabela_percentual_adv or 0:.2f}%' if (frete.tabela_percentual_adv or 0) > 0 else '-',
            'valor_calculado': adv,
            'unidade': 'R$',
            'tipo': 'valor'
        },
        {
            'nome': 'RCA (% s/ Mercadoria)',
            'valor_tabela': f'{frete.tabela_percentual_rca or 0:.2f}%',
            'valor_usado': f'R$ {valor_mercadoria:.2f}' if (frete.tabela_percentual_rca or 0) > 0 else '-',
            'formula': f'{valor_mercadoria:.2f} × {frete.tabela_percentual_rca or 0:.2f}%' if (frete.tabela_percentual_rca or 0) > 0 else '-',
            'valor_calculado': rca,
            'unidade': 'R$',
            'tipo': 'valor'
        },
        {
            'nome': 'Pedágio (por fração 100kg)',
            'valor_tabela': f'R$ {frete.tabela_pedagio_por_100kg or 0:.2f}/100kg',
            'valor_usado': f'{peso_considerado:.2f} kg = {fracoes_100kg if frete.tabela_pedagio_por_100kg else 0} frações' if (frete.tabela_pedagio_por_100kg or 0) > 0 else '-',
            'formula': f'{fracoes_100kg if frete.tabela_pedagio_por_100kg else 0} frações × R$ {frete.tabela_pedagio_por_100kg or 0:.2f}' if (frete.tabela_pedagio_por_100kg or 0) > 0 else '-',
            'valor_calculado': pedagio,
            'unidade': 'R$',
            'tipo': 'valor'
        },
        {
            'nome': 'TAS (fixo)',
            'valor_tabela': f'R$ {tas:.2f}',
            'valor_usado': 'Valor fixo' if tas > 0 else '-',
            'formula': 'Valor fixo' if tas > 0 else '-',
            'valor_calculado': tas,
            'unidade': 'R$',
            'tipo': 'valor'
        },
        {
            'nome': 'Despacho (fixo)',
            'valor_tabela': f'R$ {despacho:.2f}',
            'valor_usado': 'Valor fixo' if despacho > 0 else '-',
            'formula': 'Valor fixo' if despacho > 0 else '-',
            'valor_calculado': despacho,
            'unidade': 'R$',
            'tipo': 'valor'
        },
        {
            'nome': 'Valor CTe (fixo)',
            'valor_tabela': f'R$ {valor_cte_tabela:.2f}',
            'valor_usado': 'Valor fixo' if valor_cte_tabela > 0 else '-',
            'formula': 'Valor fixo' if valor_cte_tabela > 0 else '-',
            'valor_calculado': valor_cte_tabela,
            'unidade': 'R$',
            'tipo': 'valor'
        },
        {
            'nome': 'Total Antes Mínimo',
            'valor_tabela': 'Soma componentes',
            'valor_usado': 'Calculado',
            'formula': 'Base + GRIS + ADV + RCA + Pedágio + TAS + Despacho + CTe',
            'valor_calculado': total_liquido_antes_minimo,
            'unidade': 'R$',
            'tipo': 'subtotal'
        },
        {
            'nome': 'Ajuste Valor Mínimo',
            'valor_tabela': f'Mín: R$ {frete_minimo_valor:.2f}',
            'valor_usado': f'R$ {total_liquido_antes_minimo:.2f}',
            'formula': f'max({total_liquido_antes_minimo:.2f}, {frete_minimo_valor:.2f}) - {total_liquido_antes_minimo:.2f}',
            'valor_calculado': ajuste_minimo_valor,
            'unidade': 'R$',
            'tipo': 'ajuste',
            'observacao': 'Ajuste aplicado' if ajuste_minimo_valor > 0 else 'Não aplicado'
        }
    ]
    
    # Resumos
    resumo_cotacao = {
        'total_liquido': total_liquido,
        'percentual_icms': percentual_icms_cotacao,
        'valor_icms': valor_icms_cotacao,
        'total_bruto': total_bruto_cotacao
    }
    
    resumo_cte = {
        'total_liquido': None,  # Para preenchimento manual
        'percentual_icms': None,  # Para preenchimento manual
        'valor_icms': None,  # Calculado automaticamente
        'total_bruto': frete.valor_cte  # Valor informado no CTe
    }
    
    return render_template('fretes/analise_diferencas.html', 
                         frete=frete,
                         tabela_dados=tabela_dados,
                         componentes=componentes,
                         resumo_cotacao=resumo_cotacao,
                         resumo_cte=resumo_cte)

# =================== FATURAS DE FRETE ===================

@fretes_bp.route('/faturas')
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def listar_faturas():
    """Lista faturas de frete"""
    faturas = FaturaFrete.query.order_by(desc(FaturaFrete.criado_em)).paginate(
        page=request.args.get('page', 1, type=int),
        per_page=20,
        error_out=False
    )
    
    return render_template('fretes/listar_faturas.html', faturas=faturas)

@fretes_bp.route('/faturas/nova', methods=['GET', 'POST'])
@login_required
def nova_fatura():
    """Cadastra nova fatura de frete"""
    form = FaturaFreteForm()
    
    if form.validate_on_submit():
        nova_fatura = FaturaFrete(
            transportadora_id=request.form.get('transportadora_id'),
            numero_fatura=form.numero_fatura.data,
            data_emissao=form.data_emissao.data,
            valor_total_fatura=form.valor_total_fatura.data,
            vencimento=form.vencimento.data,
            observacoes_conferencia=form.observacoes_conferencia.data,
            criado_por=current_user.nome
        )
        
        # Upload do arquivo PDF
        if form.arquivo_pdf.data:
            try:
                # 🌐 Usar sistema S3 para salvar PDFs
                from app.utils.file_storage import get_file_storage
                storage = get_file_storage()
                
                file_path = storage.save_file(
                    file=form.arquivo_pdf.data,
                    folder='faturas',
                    allowed_extensions=['pdf']
                )
                
                if file_path:
                    nova_fatura.arquivo_pdf = file_path
                else:
                    flash('❌ Erro ao salvar arquivo PDF da fatura.', 'danger')
                    return render_template('fretes/nova_fatura.html', form=form, transportadoras=transportadoras)
                    
            except Exception as e:
                flash(f'❌ Erro ao salvar PDF: {str(e)}', 'danger')
                return render_template('fretes/nova_fatura.html', form=form, transportadoras=transportadoras)
        
        db.session.add(nova_fatura)
        db.session.commit()
        
        flash('Fatura cadastrada com sucesso!', 'success')
        return redirect(url_for('fretes.listar_faturas'))
    
    transportadoras = Transportadora.query.order_by(Transportadora.razao_social).all()
    return render_template('fretes/nova_fatura.html', form=form, transportadoras=transportadoras)

@fretes_bp.route('/faturas/<int:fatura_id>/conferir')
@login_required
def conferir_fatura(fatura_id):
    """Inicia o processo de conferência de uma fatura"""
    fatura = FaturaFrete.query.get_or_404(fatura_id)
    
    # Busca todos os CTes (fretes) da fatura
    fretes = Frete.query.filter_by(fatura_frete_id=fatura_id).all()
    
    # ✅ CORRIGIDO: Busca despesas extras VINCULADAS A ESTA FATURA pelo número da fatura
    # Busca despesas que têm o número desta fatura nas observações
    despesas_extras = DespesaExtra.query.filter(
        DespesaExtra.observacoes.contains(f'Fatura: {fatura.numero_fatura}')
    ).all()
    
    # ✅ EXPLICAÇÃO: As despesas extras são vinculadas às faturas pelo número da fatura
    # que fica armazenado no campo observacoes no formato "Fatura: NUMERO_FATURA | outras_obs"
    # Isso permite que uma despesa seja vinculada a uma fatura independentemente do frete
    
    # Analisa status dos documentos
    documentos_status = []
    valor_total_cte = 0
    valor_total_considerado = 0
    valor_total_pago = 0
    
    # Analisa CTes
    for frete in fretes:
        # ✅ LÓGICA ORIGINAL RESTRITIVA (CORRIGIDA):
        # CTe é considerado LANÇADO apenas se tem número, valor E valor_pago
        if frete.numero_cte and frete.valor_cte and frete.valor_pago:
            status_doc = 'LANÇADO'
        elif frete.status in ['APROVADO', 'CONFERIDO']:
            status_doc = 'APROVADO'
        else:
            status_doc = 'PENDENTE'
        
        # ✅ DEBUG: Mostra detalhes do CTe
        print(f"  CTe Frete #{frete.id}: numero_cte={frete.numero_cte}, valor_cte={frete.valor_cte}, valor_pago={frete.valor_pago}, status_frete={frete.status} → STATUS: {status_doc}")
        
        documentos_status.append({
            'tipo': 'CTe',
            'numero': frete.numero_cte or f'Frete #{frete.id}',
            'valor_cte': frete.valor_cte or 0,
            'valor_considerado': frete.valor_considerado or 0,
            'valor_pago': frete.valor_pago or 0,
            'status': status_doc,
            'cliente': frete.nome_cliente,
            'frete_id': frete.id
        })
        
        valor_total_cte += frete.valor_cte or 0
        valor_total_considerado += frete.valor_considerado or 0
        valor_total_pago += frete.valor_pago or 0
    
    # Analisa Despesas Extras
    for despesa in despesas_extras:
        # ✅ LÓGICA ORIGINAL RESTRITIVA (CORRIGIDA):
        # Despesa é considerada LANÇADA apenas se tem documento preenchido E está vinculada à fatura
        if (despesa.numero_documento and 
            despesa.numero_documento != 'PENDENTE_FATURA' and 
            despesa.valor_despesa and
            despesa.observacoes and 'Fatura:' in despesa.observacoes):
            status_doc = "LANÇADO"
        else:
            status_doc = "PENDENTE"
        
        # ✅ DEBUG: Mostra detalhes da despesa
        fatura_vinculada = "SIM" if (despesa.observacoes and 'Fatura:' in despesa.observacoes) else "NÃO"
        documento_ok = "SIM" if (despesa.numero_documento and despesa.numero_documento != 'PENDENTE_FATURA') else "NÃO"
        print(f"  Despesa #{despesa.id}: numero_documento={despesa.numero_documento}, valor={despesa.valor_despesa}, fatura_vinculada={fatura_vinculada}, documento_ok={documento_ok} → STATUS: {status_doc}")
        
        # ✅ CORRIGIDO: Identifica se despesa tem fatura vinculada
        cliente_obs = "Despesa Extra"
        if despesa.observacoes and 'Fatura:' in despesa.observacoes:
            try:
                fatura_info = despesa.observacoes.split('Fatura:')[1].split('|')[0].strip()
                cliente_obs = f"Despesa Extra (Fatura: {fatura_info})"
            except:
                cliente_obs = "Despesa Extra"
        
        documentos_status.append({
            'tipo': 'Despesa',
            'numero': despesa.numero_documento or f'Despesa #{despesa.id}',
            'valor_cte': despesa.valor_despesa,
            'valor_considerado': despesa.valor_despesa,
            'valor_pago': despesa.valor_despesa,
            'status': status_doc,
            'cliente': cliente_obs,
            'despesa_id': despesa.id
        })
        
        valor_total_cte += despesa.valor_despesa
        valor_total_considerado += despesa.valor_despesa
        valor_total_pago += despesa.valor_despesa
    
    # ✅ DEBUG: Conta documentos por status para diagnóstico
    status_count = {}
    for doc in documentos_status:
        status = doc['status']
        status_count[status] = status_count.get(status, 0) + 1
    
    # ✅ DEBUG DETALHADO: Log da análise de status
    print(f"\n=== DEBUG CONFERÊNCIA FATURA {fatura.numero_fatura} ===")
    print(f"Total documentos analisados: {len(documentos_status)}")
    print(f"CTes encontrados: {len([d for d in documentos_status if d['tipo'] == 'CTe'])}")
    print(f"Despesas encontradas: {len([d for d in documentos_status if d['tipo'] == 'Despesa'])}")
    print(f"Status count: {status_count}")
    
    # ✅ DEBUG: Lista todos os documentos e seus status
    print("Detalhes dos documentos:")
    for i, doc in enumerate(documentos_status, 1):
        print(f"  {i}. {doc['tipo']} - {doc['numero']} - STATUS: {doc['status']} - Cliente: {doc['cliente']}")
    
    # ✅ DEBUG: Validação detalhada por documento
    print("DEBUG VALIDAÇÃO DETALHADA:")
    for doc in documentos_status:
        status_ok = doc['status'] in ['APROVADO', 'LANÇADO']
        print(f"  - {doc['tipo']} {doc['numero']}: status='{doc['status']}' → Válido: {status_ok}")
    
    # ✅ DEBUG: Validação final
    todos_aprovados_calc = all(doc['status'] in ['APROVADO', 'LANÇADO'] for doc in documentos_status)
    print(f"Todos aprovados (calculado): {todos_aprovados_calc}")
    
    # Se não há documentos, considera como aprovado (fatura vazia)
    if len(documentos_status) == 0:
        print("ATENÇÃO: Fatura sem documentos - considerando como aprovada")
        todos_aprovados_calc = True
    
    print(f"Resultado final todos_aprovados: {todos_aprovados_calc}")
    print("=" * 50)
    
    # Verifica se todos os documentos estão aprovados/lançados
    todos_aprovados = todos_aprovados_calc
    
    # Verifica tolerância de R$ 1,00 entre valor da fatura e valor CTe
    diferenca_fatura_cte = abs(fatura.valor_total_fatura - valor_total_cte)
    fatura_dentro_tolerancia = diferenca_fatura_cte <= 1.00
    
    # ✅ DEBUG: Validação final
    print(f"DEBUG FINAL - Pode aprovar: todos_aprovados={todos_aprovados} AND fatura_dentro_tolerancia={fatura_dentro_tolerancia}")
    print(f"  - Valor fatura: R$ {fatura.valor_total_fatura:.2f}")
    print(f"  - Valor CTe total: R$ {valor_total_cte:.2f}")
    print(f"  - Diferença: R$ {diferenca_fatura_cte:.2f}")
    print(f"  - Pode aprovar: {todos_aprovados and fatura_dentro_tolerancia}")
    
    # Análise de valores
    analise_valores = {
        'valor_fatura': fatura.valor_total_fatura,
        'valor_total_cte': valor_total_cte,
        'valor_total_considerado': valor_total_considerado,
        'valor_total_pago': valor_total_pago,
        'diferenca_fatura_cte': diferenca_fatura_cte,
        'fatura_dentro_tolerancia': fatura_dentro_tolerancia,
        'diferenca_considerado_pago': abs(valor_total_considerado - valor_total_pago)
    }
    
    return render_template('fretes/conferir_fatura.html',
                         fatura=fatura,
                         documentos_status=documentos_status,
                         analise_valores=analise_valores,
                         todos_aprovados=todos_aprovados,
                         pode_aprovar=todos_aprovados and fatura_dentro_tolerancia)

@fretes_bp.route('/faturas/<int:fatura_id>/aprovar_conferencia', methods=['POST'])
@login_required
def aprovar_conferencia_fatura(fatura_id):
    """Aprova a conferência de uma fatura"""
    fatura = FaturaFrete.query.get_or_404(fatura_id)
    
    try:
        valor_final = request.form.get('valor_final')
        observacoes = request.form.get('observacoes', '')
        
        # Converte valor final
        if valor_final:
            valor_final_float = float(valor_final.replace(',', '.'))
        else:
            # Calcula total pago dos documentos
            fretes = Frete.query.filter_by(fatura_frete_id=fatura_id).all()
            despesas_extras = []
            for frete in fretes:
                despesas_extras.extend(frete.despesas_extras)
            
            valor_final_float = sum(f.valor_pago or 0 for f in fretes) + sum(d.valor_despesa for d in despesas_extras)
        
        # Atualiza fatura
        fatura.valor_total_fatura = valor_final_float
        fatura.status_conferencia = 'CONFERIDO'
        fatura.conferido_por = current_user.nome
        fatura.conferido_em = datetime.utcnow()
        fatura.observacoes_conferencia = observacoes
        
        # Bloqueia edição dos fretes e despesas
        fretes = Frete.query.filter_by(fatura_frete_id=fatura_id).all()
        for frete in fretes:
            if frete.status != 'BLOQUEADO':
                frete.status = 'CONFERIDO'
        
        db.session.commit()
        
        flash(f'✅ Fatura {fatura.numero_fatura} conferida com sucesso! Valor atualizado para R$ {valor_final_float:.2f}', 'success')
        return redirect(url_for('fretes.listar_faturas'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao conferir fatura: {str(e)}', 'error')
        return redirect(url_for('fretes.conferir_fatura', fatura_id=fatura_id))

@fretes_bp.route('/faturas/<int:fatura_id>/reabrir', methods=['POST'])
@login_required
def reabrir_fatura(fatura_id):
    """Reabre uma fatura conferida, liberando para edição novamente"""
    fatura = FaturaFrete.query.get_or_404(fatura_id)
    
    try:
        motivo = request.form.get('motivo_reabertura', '')
        
        # ✅ VALIDAÇÃO: Verifica se pode reabrir
        if fatura.status_conferencia != 'CONFERIDO':
            flash('❌ Apenas faturas conferidas podem ser reabertas!', 'error')
            return redirect(url_for('fretes.listar_faturas'))
        
        # ✅ VERIFICA STATUS DOS DOCUMENTOS ANTES DE REABRIR
        fretes = Frete.query.filter_by(fatura_frete_id=fatura_id).all()
        despesas_extras = []
        for frete in fretes:
            despesas_extras.extend(frete.despesas_extras)
        
        # Conta documentos pendentes
        documentos_pendentes = 0
        for frete in fretes:
            if not frete.numero_cte or not frete.valor_cte:
                documentos_pendentes += 1
        
        for despesa in despesas_extras:
            if despesa.numero_documento == 'PENDENTE_FATURA':
                documentos_pendentes += 1
        
        # ⚠️ AVISO se há documentos pendentes (mas permite reabertura)
        if documentos_pendentes > 0:
            flash(f'⚠️ ATENÇÃO: Há {documentos_pendentes} documento(s) pendente(s) nesta fatura. Certifique-se de completar antes de conferir novamente.', 'warning')
        
        # Atualiza status da fatura
        fatura.status_conferencia = 'PENDENTE'
        fatura.observacoes_conferencia = f"REABERTA EM {datetime.now().strftime('%d/%m/%Y %H:%M')} por {current_user.nome} - {motivo}\n\n{fatura.observacoes_conferencia or ''}"
        
        # Libera edição dos fretes
        for frete in fretes:
            if frete.status == 'CONFERIDO':
                frete.status = 'LANCADO'  # Volta ao status anterior
        
        db.session.commit()
        
        flash(f'✅ Fatura {fatura.numero_fatura} reaberta com sucesso! Fretes e despesas liberados para edição.', 'success')
        return redirect(url_for('fretes.listar_faturas'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao reabrir fatura: {str(e)}', 'error')
        return redirect(url_for('fretes.listar_faturas'))

@fretes_bp.route('/faturas/<int:fatura_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_fatura(fatura_id):
    """Edita uma fatura existente"""
    fatura = FaturaFrete.query.get_or_404(fatura_id)
    
    # Verifica se fatura pode ser editada
    if fatura.status_conferencia == 'CONFERIDO':
        flash('❌ Fatura conferida não pode ser editada! Use a opção "Reabrir" primeiro.', 'error')
        return redirect(url_for('fretes.listar_faturas'))
    
    from app.transportadoras.models import Transportadora
    
    if request.method == 'POST':
        try:
            # Atualiza dados da fatura
            fatura.numero_fatura = request.form.get('numero_fatura')
            fatura.data_emissao = datetime.strptime(request.form.get('data_emissao'), '%Y-%m-%d').date()
            fatura.valor_total_fatura = float(request.form.get('valor_total_fatura').replace(',', '.'))
            fatura.vencimento = datetime.strptime(request.form.get('vencimento'), '%Y-%m-%d').date() if request.form.get('vencimento') else None
            fatura.transportadora_id = int(request.form.get('transportadora_id'))
            
            db.session.commit()
            
            flash(f'✅ Fatura {fatura.numero_fatura} atualizada com sucesso!', 'success')
            return redirect(url_for('fretes.listar_faturas'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar fatura: {str(e)}', 'error')
    
    transportadoras = Transportadora.query.all()
    return render_template('fretes/editar_fatura.html', 
                         fatura=fatura, 
                         transportadoras=transportadoras)

@fretes_bp.route('/faturas/<int:fatura_id>/excluir', methods=['POST'])
@login_required
def excluir_fatura(fatura_id):
    """Exclui uma fatura que não possui fretes ou despesas vinculadas"""
    fatura = FaturaFrete.query.get_or_404(fatura_id)
    
    try:
        # Verifica se há fretes vinculados
        fretes_vinculados = Frete.query.filter_by(fatura_frete_id=fatura_id).count()
        if fretes_vinculados > 0:
            flash(f'❌ Não é possível excluir a fatura {fatura.numero_fatura}. Há {fretes_vinculados} frete(s) vinculado(s).', 'error')
            return redirect(url_for('fretes.listar_faturas'))
        
        # Verifica se fatura está conferida
        if fatura.status_conferencia == 'CONFERIDO':
            flash('❌ Fatura conferida não pode ser excluída!', 'error')
            return redirect(url_for('fretes.listar_faturas'))
        
        numero_fatura = fatura.numero_fatura
        db.session.delete(fatura)
        db.session.commit()
        
        flash(f'✅ Fatura {numero_fatura} excluída com sucesso!', 'success')
        return redirect(url_for('fretes.listar_faturas'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir fatura: {str(e)}', 'error')
        return redirect(url_for('fretes.listar_faturas'))

# =================== DESPESAS EXTRAS ===================

@fretes_bp.route('/despesas/nova', methods=['GET', 'POST'])
@login_required
def nova_despesa_extra_por_nf():
    """Novo fluxo: Lançamento de despesa extra buscando frete por NF"""
    if request.method == 'POST':
        numero_nf = request.form.get('numero_nf')
        
        if not numero_nf:
            flash('Digite o número da NF!', 'error')
            return render_template('fretes/nova_despesa_extra_por_nf.html')
        
        # Busca fretes que contêm essa NF
        fretes_encontrados = Frete.query.filter(
            Frete.numeros_nfs.contains(numero_nf)
        ).all()
        
        if not fretes_encontrados:
            flash(f'Nenhum frete encontrado com a NF {numero_nf}!', 'error')
            return render_template('fretes/nova_despesa_extra_por_nf.html')
        
        # Se encontrou fretes, mostra para seleção
        return render_template('fretes/selecionar_frete_despesa.html',
                             fretes=fretes_encontrados,
                             numero_nf=numero_nf)
    
    return render_template('fretes/nova_despesa_extra_por_nf.html')


@fretes_bp.route('/despesas/criar/<int:frete_id>', methods=['GET', 'POST'])
@login_required
def criar_despesa_extra_frete(frete_id):
    """Etapa 2: Criar despesa extra para frete selecionado"""
    frete = Frete.query.get_or_404(frete_id)
    form = DespesaExtraForm()
    
    if form.validate_on_submit():
        despesa = DespesaExtra(
            frete_id=frete_id,
            tipo_despesa=form.tipo_despesa.data,
            setor_responsavel=form.setor_responsavel.data,
            motivo_despesa=form.motivo_despesa.data,
            # ✅ CORRIGIDO: Formulário simplificado não tem tipo_documento
            tipo_documento='PENDENTE_DOCUMENTO',  # Será definido ao vincular fatura
            numero_documento='PENDENTE_FATURA',  # ✅ OBRIGATÓRIO: FATURA PRIMEIRO, DOCUMENTO DEPOIS
            valor_despesa=form.valor_despesa.data,
            vencimento_despesa=None,  # ✅ CORRIGIDO: Formulário simplificado não tem vencimento
            observacoes=form.observacoes.data,
            criado_por=current_user.nome
        )
        
        # Armazena na sessão para confirmar
        session['despesa_data'] = despesa.__dict__
        
        # Redireciona para confirmação/pergunta sobre fatura
        return redirect(url_for('fretes.confirmar_despesa_extra'))
    
    return render_template('fretes/criar_despesa_extra_frete.html', 
                         form=form, frete=frete)


@fretes_bp.route('/despesas/confirmar', methods=['GET', 'POST'])
@login_required
def confirmar_despesa_extra():
    """Etapa 3: Confirma despesa e pergunta sobre fatura"""
    despesa_data = session.get('despesa_data')
    
    if not despesa_data:
        flash('Dados da despesa não encontrados. Reinicie o processo.', 'error')
        return redirect(url_for('fretes.nova_despesa_extra_por_nf'))
    
    frete = Frete.query.get(despesa_data['frete_id'])
    if not frete:
        flash('Frete não encontrado!', 'error')
        return redirect(url_for('fretes.nova_despesa_extra_por_nf'))
    
    if request.method == 'POST':
        tem_fatura = request.form.get('tem_fatura') == 'sim'
        
        if not tem_fatura:
            # Salva despesa sem fatura
            try:
                despesa = DespesaExtra(
                    frete_id=despesa_data['frete_id'],
                    tipo_despesa=despesa_data['tipo_despesa'],
                    setor_responsavel=despesa_data['setor_responsavel'],
                    motivo_despesa=despesa_data['motivo_despesa'],
                    tipo_documento=despesa_data['tipo_documento'],
                    numero_documento=despesa_data['numero_documento'],
                    valor_despesa=despesa_data['valor_despesa'],
                    vencimento_despesa=datetime.fromisoformat(despesa_data['vencimento_despesa']).date() if despesa_data['vencimento_despesa'] else None,
                    observacoes=despesa_data['observacoes'],
                    criado_por=current_user.nome
                )
                
                db.session.add(despesa)
                db.session.commit()
                
                # Limpa dados da sessão
                session.pop('despesa_data', None)
                
                flash('Despesa extra cadastrada com sucesso!', 'success')
                return redirect(url_for('fretes.visualizar_frete', frete_id=frete.id))
                
            except Exception as e:
                flash(f'Erro ao salvar despesa: {str(e)}', 'error')
                return redirect(url_for('fretes.nova_despesa_extra_por_nf'))
        else:
            # Tem fatura - redireciona para seleção
            return redirect(url_for('fretes.selecionar_fatura_despesa'))
    
    # Busca faturas disponíveis da mesma transportadora
    faturas_disponiveis = FaturaFrete.query.filter_by(
        transportadora_id=frete.transportadora_id,
        status_conferencia='PENDENTE'
    ).order_by(desc(FaturaFrete.criado_em)).all()
    
    return render_template('fretes/confirmar_despesa_extra.html',
                         despesa_data=despesa_data,
                         frete=frete,
                         faturas_disponiveis=faturas_disponiveis)


@fretes_bp.route('/despesas/selecionar_fatura', methods=['GET', 'POST'])
@login_required
def selecionar_fatura_despesa():
    """Etapa 4: Seleciona fatura e finaliza despesa"""
    despesa_data = session.get('despesa_data')
    
    if not despesa_data:
        flash('Dados da despesa não encontrados. Reinicie o processo.', 'error')
        return redirect(url_for('fretes.nova_despesa_extra_por_nf'))
    
    frete = Frete.query.get(despesa_data['frete_id'])
    if not frete:
        flash('Frete não encontrado!', 'error')
        return redirect(url_for('fretes.nova_despesa_extra_por_nf'))
    
    faturas_disponiveis = FaturaFrete.query.filter_by(
        transportadora_id=frete.transportadora_id,
        status_conferencia='PENDENTE'
    ).order_by(desc(FaturaFrete.criado_em)).all()
    
    if request.method == 'POST':
        fatura_id = request.form.get('fatura_id')
        tipo_documento_cobranca = request.form.get('tipo_documento_cobranca')
        valor_cobranca = request.form.get('valor_cobranca')
        numero_cte_documento = request.form.get('numero_cte_documento')  # ✅ NOVO CAMPO
        
        if not fatura_id:
            flash('Selecione uma fatura!', 'error')
            return render_template('fretes/selecionar_fatura_despesa.html',
                                 despesa_data=despesa_data,
                                 frete=frete,
                                 faturas_disponiveis=faturas_disponiveis)
        
        try:
            # Busca a fatura selecionada
            fatura = FaturaFrete.query.get(fatura_id)
            if not fatura:
                flash('Fatura não encontrada!', 'error')
                return render_template('fretes/selecionar_fatura_despesa.html',
                                     despesa_data=despesa_data,
                                     frete=frete,
                                     faturas_disponiveis=faturas_disponiveis)
            
            # Converte valor da cobrança
            valor_cobranca_float = float(valor_cobranca.replace(',', '.')) if valor_cobranca else despesa_data['valor_despesa']
            
            # **DEFINE VENCIMENTO: FATURA TEM PRIORIDADE**
            vencimento_final = fatura.vencimento if fatura.vencimento else (
                datetime.fromisoformat(despesa_data['vencimento_despesa']).date() 
                if despesa_data['vencimento_despesa'] else None
            )
            
            # Salva despesa com fatura
            despesa = DespesaExtra(
                frete_id=despesa_data['frete_id'],
                tipo_despesa=despesa_data['tipo_despesa'],
                setor_responsavel=despesa_data['setor_responsavel'],
                motivo_despesa=despesa_data['motivo_despesa'],
                tipo_documento=tipo_documento_cobranca,  # Usa o tipo do documento de cobrança
                numero_documento='PENDENTE_FATURA',  # ✅ DOCUMENTO SERÁ PREENCHIDO APÓS FATURA
                valor_despesa=valor_cobranca_float,  # Usa o valor da cobrança
                vencimento_despesa=vencimento_final,  # **USA VENCIMENTO DA FATURA**
                observacoes=f"Fatura: {fatura.numero_fatura} | {despesa_data['observacoes'] or ''}",
                criado_por=current_user.nome
            )
            
            db.session.add(despesa)
            db.session.commit()
            
            # Limpa dados da sessão
            session.pop('despesa_data', None)
            
            flash('Despesa extra cadastrada com fatura vinculada!', 'success')
            return redirect(url_for('fretes.visualizar_frete', frete_id=frete.id))
            
        except Exception as e:
            flash(f'Erro ao salvar despesa: {str(e)}', 'error')
            return render_template('fretes/selecionar_fatura_despesa.html',
                                 despesa_data=despesa_data,
                                 frete=frete,
                                 faturas_disponiveis=faturas_disponiveis)
    
    return render_template('fretes/selecionar_fatura_despesa.html',
                         despesa_data=despesa_data,
                         frete=frete,
                         faturas_disponiveis=faturas_disponiveis)


@fretes_bp.route('/<int:frete_id>/despesas/nova', methods=['GET', 'POST'])
@login_required
def nova_despesa_extra(frete_id):
    """Adiciona despesa extra ao frete - NÃO vincula automaticamente à fatura do frete"""
    frete = Frete.query.get_or_404(frete_id)
    form = DespesaExtraForm()
    
    if form.validate_on_submit():
        despesa = DespesaExtra(
            frete_id=frete_id,
            tipo_despesa=form.tipo_despesa.data,
            setor_responsavel=form.setor_responsavel.data,
            motivo_despesa=form.motivo_despesa.data,
            # ✅ CORRIGIDO: NÃO vincula automaticamente à fatura
            tipo_documento='PENDENTE_DOCUMENTO',  # Será definido ao vincular fatura MANUALMENTE
            numero_documento='PENDENTE_FATURA',  # ✅ PENDENTE até vinculação manual
            valor_despesa=form.valor_despesa.data,
            vencimento_despesa=None,  # Será definido ao vincular fatura
            observacoes=form.observacoes.data,  # ✅ SEM referência automática à fatura
            criado_por=current_user.nome
        )
        
        db.session.add(despesa)
        db.session.commit()
        
        flash('✅ Despesa extra criada! Para vinculá-la a uma fatura, use "Gerenciar Despesas Extras".', 'success')
        return redirect(url_for('fretes.visualizar_frete', frete_id=frete_id))
    
    return render_template('fretes/nova_despesa_extra.html', form=form, frete=frete)

# =================== CONTA CORRENTE ===================

@fretes_bp.route('/conta_corrente/<int:transportadora_id>')
@login_required
def conta_corrente_transportadora(transportadora_id):
    """Visualiza conta corrente de uma transportadora"""
    transportadora = Transportadora.query.get_or_404(transportadora_id)
    
    movimentacoes = ContaCorrenteTransportadora.query.filter_by(
        transportadora_id=transportadora_id
    ).order_by(desc(ContaCorrenteTransportadora.criado_em)).all()
    
    # Calcula saldos
    total_creditos = sum(m.valor_credito for m in movimentacoes if m.status == 'ATIVO')
    total_debitos = sum(m.valor_debito for m in movimentacoes if m.status == 'ATIVO')
    saldo_atual = total_debitos - total_creditos
    
    return render_template('fretes/conta_corrente.html',
                         transportadora=transportadora,
                         movimentacoes=movimentacoes,
                         total_creditos=total_creditos,
                         total_debitos=total_debitos,
                         saldo_atual=saldo_atual)

# =================== APROVAÇÕES ===================

@fretes_bp.route('/aprovacoes')
@login_required
def listar_aprovacoes():
    """Lista aprovações pendentes"""
    aprovacoes = AprovacaoFrete.query.filter_by(status='PENDENTE').order_by(
        desc(AprovacaoFrete.solicitado_em)
    ).all()
    
    return render_template('fretes/listar_aprovacoes.html', aprovacoes=aprovacoes)

@fretes_bp.route('/aprovacoes/<int:aprovacao_id>', methods=['GET', 'POST'])
@login_required
def processar_aprovacao(aprovacao_id):
    """Processa aprovação de frete - Nova tela com casos A e B"""
    aprovacao = AprovacaoFrete.query.get_or_404(aprovacao_id)
    frete = aprovacao.frete
    
    if request.method == 'POST':
        acao = request.form.get('acao')
        observacoes = request.form.get('observacoes', '')
        lancar_diferenca = request.form.get('lancar_diferenca') == 'on'
        
        if acao == 'APROVAR':
            # Aprova o frete
            aprovacao.status = 'APROVADO'
            aprovacao.aprovador = current_user.nome
            aprovacao.aprovado_em = datetime.utcnow()
            aprovacao.observacoes_aprovacao = observacoes
            
            frete.status = 'APROVADO'
            frete.aprovado_por = current_user.nome
            frete.aprovado_em = datetime.utcnow()
            frete.observacoes_aprovacao = observacoes
            
            # ✅ Se aprovado, verifica se deve lançar diferença na conta corrente
            if lancar_diferenca and frete.valor_pago and frete.valor_considerado:
                diferenca = frete.diferenca_considerado_pago()
                if diferenca != 0:
                    # Remove movimentações antigas
                    ContaCorrenteTransportadora.query.filter_by(frete_id=frete.id).delete()
                    
                    # Cria movimentação aprovada
                    tipo_mov = 'CREDITO' if diferenca > 0 else 'DEBITO'
                    descricao = f'Frete {frete.id} - CTe {frete.numero_cte} - Diferença Aprovada'
                    
                    movimentacao = ContaCorrenteTransportadora(
                        transportadora_id=frete.transportadora_id,
                        frete_id=frete.id,
                        tipo_movimentacao=tipo_mov,
                        valor_diferenca=abs(diferenca),
                        valor_credito=diferenca if diferenca > 0 else 0,
                        valor_debito=abs(diferenca) if diferenca < 0 else 0,
                        descricao=descricao,
                        criado_por=current_user.nome
                    )
                    db.session.add(movimentacao)
            
            flash('Frete aprovado com sucesso!', 'success')
            
        elif acao == 'REJEITAR':
            aprovacao.status = 'REJEITADO'
            aprovacao.aprovador = current_user.nome
            aprovacao.aprovado_em = datetime.utcnow()
            aprovacao.observacoes_aprovacao = observacoes
            
            frete.status = 'REJEITADO'
            frete.observacoes_aprovacao = observacoes
            
            flash('Frete rejeitado!', 'warning')
        
        db.session.commit()
        return redirect(url_for('fretes.listar_aprovacoes'))
    
    # Calcula os dados para exibição dos casos
    caso_a = caso_b = None
    
    if frete.valor_considerado and frete.valor_cotado:
        diff_considerado_cotado = frete.valor_considerado - frete.valor_cotado
        if abs(diff_considerado_cotado) > 5.00:
            caso_a = {
                'valor_considerado': frete.valor_considerado,
                'valor_cotado': frete.valor_cotado,
                'diferenca': diff_considerado_cotado
            }
    
    if frete.valor_pago and frete.valor_considerado:
        diff_pago_considerado = frete.valor_pago - frete.valor_considerado
        if abs(diff_pago_considerado) > 5.00:
            caso_b = {
                'valor_pago': frete.valor_pago,
                'valor_considerado': frete.valor_considerado,
                'diferenca': diff_pago_considerado
            }
    
    return render_template('fretes/processar_aprovacao_nova.html', 
                         aprovacao=aprovacao, 
                         frete=frete,
                         caso_a=caso_a,
                         caso_b=caso_b)

# =================== ROTAS EXISTENTES (COMPATIBILIDADE) ===================

@fretes_bp.route('/antigo/<int:embarque_id>')
@login_required
def visualizar_fretes_lancados(embarque_id):
    embarque = Embarque.query.get_or_404(embarque_id)
    fretes = embarque.fretes_lancados

    total_frete = sum(f.valor_frete for f in fretes)
    total_peso = sum(f.peso for f in fretes)
    total_valor_nf = sum(f.valor_nf for f in fretes)

    return render_template(
        'fretes/visualizar_fretes.html',
        embarque=embarque,
        fretes=fretes,
        total_frete=total_frete,
        total_peso=total_peso,
        total_valor_nf=total_valor_nf
    )

@fretes_bp.route('/buscar', methods=['GET', 'POST'])
@login_required
def buscar_frete():
    if request.method == 'POST':
        nf = request.form.get('nf')
        resultados = FreteLancado.query.filter(FreteLancado.nota_fiscal.ilike(f'%{nf}%')).all()
        return render_template('fretes/buscar_frete.html', resultados=resultados, nf=nf)
    return render_template('fretes/buscar_frete.html')

@fretes_bp.route('/divergencias')
@login_required
def listar_divergencias():
    divergentes = FreteLancado.query.filter(FreteLancado.divergencia.isnot(None)).order_by(FreteLancado.criado_em.desc()).all()
    return render_template('fretes/listar_divergencias.html', fretes=divergentes)

@fretes_bp.route('/<int:id>/editar_divergencia', methods=['GET', 'POST'])
@login_required
def editar_divergencia(id):
    frete = FreteLancado.query.get_or_404(id)

    if request.method == 'POST':
        nova_div = request.form.get('divergencia')
        frete.divergencia = nova_div
        db.session.commit()
        flash("Divergência atualizada com sucesso!", "success")
        return redirect(url_for('fretes.listar_divergencias'))

    return render_template('fretes/editar_divergencia.html', frete=frete)


@fretes_bp.route('/embarques/<int:id>/lancar_fretes', methods=['GET', 'POST'])
@login_required
def lancar_fretes_embarque(id):
    embarque = Embarque.query.get_or_404(id)
    itens = embarque.itens

    if request.method == 'POST':
        for item in itens:
            prefix = f"{item.id}"
            peso = request.form.get(f"peso_{prefix}")
            valor_nf = request.form.get(f"valor_nf_{prefix}")
            transportadora = request.form.get(f"transportadora_{prefix}")
            valor_frete = request.form.get(f"frete_{prefix}")
            modalidade = request.form.get(f"modalidade_{prefix}")
            cte = request.form.get(f"cte_{prefix}")
            vencimento = request.form.get(f"vencimento_{prefix}")
            fatura = request.form.get(f"fatura_{prefix}")
            divergencia = request.form.get(f"divergencia_{prefix}")

            # Apenas salvar se houver valor de frete preenchido
            if valor_frete:
                # Verifica duplicidade (exibe, mas permite)
                existente = FreteLancado.query.filter_by(nota_fiscal=item.nota_fiscal).first()

                frete = FreteLancado(
                    embarque_id=embarque.id,
                    nota_fiscal=item.nota_fiscal,
                    cliente=item.cliente,
                    cidade_destino=item.cidade_destino,
                    uf_destino=item.uf_destino,
                    transportadora_id=transportadora,
                    peso=float(peso) if peso else None,
                    valor_nf=float(valor_nf) if valor_nf else None,
                    valor_frete=float(valor_frete),
                    modalidade=modalidade,
                    cte=cte,
                    vencimento=vencimento if vencimento else None,
                    fatura=fatura,
                    divergencia=divergencia,
                    tipo_carga=embarque.tipo_carga or 'FRACIONADA'
                )
                db.session.add(frete)

        db.session.commit()
        flash("Fretes lançados com sucesso!", "success")
        return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))

    return render_template('fretes/lancar_fretes.html', embarque=embarque, itens=itens)

@fretes_bp.route('/lancar_antigo', methods=['GET', 'POST'])
@login_required
def lancar_frete():
    # Rota simplificada para compatibilidade
    if request.method == 'POST':
        flash('Use o novo sistema de lançamento de CTe em /fretes/lancar_cte', 'info')
        return redirect(url_for('fretes.lancar_cte'))
    
    transportadoras = Transportadora.query.all()
    return render_template('fretes/lancar_frete_antigo.html', transportadoras=transportadoras)

@fretes_bp.route('/simulador_antigo', methods=['GET', 'POST'])
@login_required
def simulador():
    # Rota simplificada para compatibilidade - redireciona para novo sistema
    flash('Simulador movido para o novo sistema. Use as cotações em /cotacao/', 'info')
    return redirect(url_for('fretes.index'))

# =================== FUNÇÕES AUXILIARES PARA GATILHOS ===================

def verificar_cte_existente_para_embarque(embarque_id, cnpj_cliente=None):
    """
    Verifica se já existe CTe lançado para um embarque e CNPJ
    """
    query = Frete.query.filter_by(embarque_id=embarque_id)
    
    if cnpj_cliente:
        query = query.filter_by(cnpj_cliente=cnpj_cliente)
    
    fretes = query.filter(Frete.numero_cte.isnot(None)).all()
    return fretes

def verificar_requisitos_para_lancamento_frete(embarque_id, cnpj_cliente):
    """
    Verifica se um frete pode ser lançado automaticamente
    REQUISITOS RIGOROSOS (TODOS DEVEM SER ATENDIDOS):
    1. TODAS as NFs do embarque devem estar preenchidas
    2. TODAS as NFs do embarque devem estar no faturamento
    3. TODOS os CNPJs devem coincidir entre embarque e faturamento
    4. Não pode já existir frete para este CNPJ/embarque
    """
    # Verifica se já existe frete
    frete_existente = Frete.query.filter(
        and_(
            Frete.embarque_id == embarque_id,
            Frete.cnpj_cliente == cnpj_cliente
        )
    ).first()
    
    if frete_existente:
        return False, f"Já existe frete para CNPJ {cnpj_cliente} no embarque {embarque_id}"
    
    # ✅ CORREÇÃO: Busca APENAS os itens ATIVOS do embarque
    itens_embarque = EmbarqueItem.query.filter_by(embarque_id=embarque_id, status='ativo').all()
    
    if not itens_embarque:
        return False, "Nenhum item ativo encontrado no embarque"
    
    # REQUISITO 1: TODAS as NFs dos itens ATIVOS devem estar preenchidas
    itens_sem_nf = [item for item in itens_embarque if not item.nota_fiscal or item.nota_fiscal.strip() == '']
    if itens_sem_nf:
        return False, f"Existem {len(itens_sem_nf)} item(ns) ativo(s) sem NF preenchida no embarque"
    
    # REQUISITO 2: TODAS as NFs dos itens ATIVOS devem estar no faturamento
    nfs_embarque = [item.nota_fiscal for item in itens_embarque]
    from app.faturamento.models import RelatorioFaturamentoImportado
    
    nfs_faturamento = []
    nfs_nao_encontradas = []
    
    for nf in nfs_embarque:
        nf_fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=nf).first()
        if nf_fat:
            nfs_faturamento.append(nf_fat)
        else:
            nfs_nao_encontradas.append(nf)
    
    if nfs_nao_encontradas:
        return False, f"NFs não encontradas no faturamento: {', '.join(nfs_nao_encontradas)}"
    
    # REQUISITO 3: TODOS os CNPJs dos itens ATIVOS devem coincidir entre embarque e faturamento
    erros_cnpj = []
    
    for item in itens_embarque:
        nf_fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=item.nota_fiscal).first()
        
        if nf_fat:
            # Se o item não tem CNPJ, atualiza com o do faturamento
            if not item.cnpj_cliente:
                item.cnpj_cliente = nf_fat.cnpj_cliente
                db.session.commit()
            
            # Verifica se coincidem
            if item.cnpj_cliente != nf_fat.cnpj_cliente:
                erros_cnpj.append(f"NF {item.nota_fiscal}: Embarque({item.cnpj_cliente}) ≠ Faturamento({nf_fat.cnpj_cliente})")
    
    if erros_cnpj:
        return False, f"CNPJs divergentes: {'; '.join(erros_cnpj)}"
    
    # REQUISITO 4: Verifica se há itens ATIVOS com erro de validação
    itens_com_erro = [item for item in itens_embarque if item.erro_validacao]
    if itens_com_erro:
        return False, f"Existem {len(itens_com_erro)} item(ns) ativo(s) com erro de validação no embarque"
    
    # REQUISITO 5: Verifica se há pelo menos uma NF do CNPJ específico
    itens_cnpj = [item for item in itens_embarque if item.cnpj_cliente == cnpj_cliente]
    if not itens_cnpj:
        return False, f"Nenhuma NF do CNPJ {cnpj_cliente} encontrada no embarque"
    
    return True, f"Todos os requisitos atendidos para CNPJ {cnpj_cliente} ({len(itens_cnpj)} NFs)"

def lancar_frete_automatico(embarque_id, cnpj_cliente, usuario='Sistema'):
    """
    Lança frete automaticamente seguindo as regras específicas:
    
    DIRETA - deverá calcular o frete total do embarque através da tabela gravada no embarque 
    considerando o valor total e peso total dos itens do embarque.
    Ao lançar o frete, deverá ser lançado o valor do frete proporcional ao peso de cada CNPJ.
    
    FRACIONADA - Deverá ser calculado o valor do frete através da tabela contida no item do embarque 
    e considerado o valor e peso total do CNPJ dos itens do embarque.
    
    FOB - Não gera frete automaticamente
    """
    try:
        # Verifica requisitos
        pode_lancar, motivo = verificar_requisitos_para_lancamento_frete(embarque_id, cnpj_cliente)
        if not pode_lancar:
            return False, motivo
        
        embarque = Embarque.query.get(embarque_id)
        if not embarque:
            return False, "Embarque não encontrado"
        
        # ✅ NOVA VALIDAÇÃO: Se transportadora for "FOB - COLETA", não gera frete
        from app.transportadoras.models import Transportadora
        transportadora = Transportadora.query.get(embarque.transportadora_id)
        if transportadora and transportadora.razao_social == "FOB - COLETA":
            return True, f"Embarque FOB - não gera frete automaticamente (Transportadora: {transportadora.razao_social})"
        
        # Busca dados do CNPJ no faturamento
        nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(cnpj_cliente=cnpj_cliente).first()
        if not nf_faturamento:
            return False, "Dados do CNPJ não encontrados no faturamento"
        
        # ✅ CORREÇÃO: Busca itens ATIVOS do embarque para este CNPJ
        itens_embarque_cnpj = []
        for item in embarque.itens:
            if item.status == 'ativo' and item.nota_fiscal:
                nf_fat = RelatorioFaturamentoImportado.query.filter_by(
                    numero_nf=item.nota_fiscal,
                    cnpj_cliente=cnpj_cliente
                ).first()
                if nf_fat:
                    itens_embarque_cnpj.append(item)
        
        if not itens_embarque_cnpj:
            return False, "Nenhuma NF do CNPJ encontrada no embarque"
        
        # Calcula totais das NFs deste CNPJ
        nfs_deste_cnpj = RelatorioFaturamentoImportado.query.filter(
            and_(
                RelatorioFaturamentoImportado.cnpj_cliente == cnpj_cliente,
                RelatorioFaturamentoImportado.numero_nf.in_([item.nota_fiscal for item in itens_embarque_cnpj])
            )
        ).all()
        
        peso_total_cnpj = sum(float(nf.peso_bruto or 0) for nf in nfs_deste_cnpj)
        valor_total_cnpj = sum(float(nf.valor_total or 0) for nf in nfs_deste_cnpj)
        numeros_nfs = ','.join([item.nota_fiscal for item in itens_embarque_cnpj])
        
        # LÓGICA ESPECÍFICA POR TIPO DE CARGA
        if embarque.tipo_carga == 'DIRETA':
            # ========== CARGA DIRETA ==========
            # Calcular frete total do embarque através da tabela do embarque
            # considerando valor total e peso total dos itens do embarque
            
            # Busca dados da tabela do embarque
            tabela_dados = {
                'modalidade': embarque.modalidade,
                'nome_tabela': embarque.tabela_nome_tabela,
                'valor_kg': embarque.tabela_valor_kg,
                'percentual_valor': embarque.tabela_percentual_valor,
                'frete_minimo_valor': embarque.tabela_frete_minimo_valor,
                'frete_minimo_peso': embarque.tabela_frete_minimo_peso,
                'icms': embarque.tabela_icms,
                'percentual_gris': embarque.tabela_percentual_gris,
                'pedagio_por_100kg': embarque.tabela_pedagio_por_100kg,
                'valor_tas': embarque.tabela_valor_tas,
                'percentual_adv': embarque.tabela_percentual_adv,
                'percentual_rca': embarque.tabela_percentual_rca,
                'valor_despacho': embarque.tabela_valor_despacho,
                'valor_cte': embarque.tabela_valor_cte,
                'icms_incluso': embarque.tabela_icms_incluso,
                'icms_destino': embarque.icms_destino or 0
            }
            
            # ✅ CORREÇÃO: Calcula totais do embarque inteiro (apenas itens ATIVOS)
            todas_nfs_embarque = []
            for item in embarque.itens:
                if item.status == 'ativo' and item.nota_fiscal:
                    nf_fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=item.nota_fiscal).first()
                    if nf_fat:
                        todas_nfs_embarque.append(nf_fat)
            
            peso_total_embarque = sum(float(nf.peso_bruto or 0) for nf in todas_nfs_embarque)
            valor_total_embarque = sum(float(nf.valor_total or 0) for nf in todas_nfs_embarque)
            
            # Calcula frete total do embarque
            valor_frete_total_embarque = calcular_valor_frete_pela_tabela(tabela_dados, peso_total_embarque, valor_total_embarque)
            
            # Calcula valor proporcional ao peso do CNPJ
            if peso_total_embarque > 0:
                proporcao_peso = peso_total_cnpj / peso_total_embarque
                valor_cotado = valor_frete_total_embarque * proporcao_peso
            else:
                valor_cotado = 0
                
        else:
            # ========== CARGA FRACIONADA ==========
            # Calcular através da tabela contida no item do embarque
            # considerando valor e peso total do CNPJ dos itens do embarque
            
            # Pega dados da tabela de qualquer item do CNPJ (são iguais)
            item_ref = itens_embarque_cnpj[0]
            tabela_dados = {
                'modalidade': item_ref.modalidade,
                'nome_tabela': item_ref.tabela_nome_tabela,
                'valor_kg': item_ref.tabela_valor_kg,
                'percentual_valor': item_ref.tabela_percentual_valor,
                'frete_minimo_valor': item_ref.tabela_frete_minimo_valor,
                'frete_minimo_peso': item_ref.tabela_frete_minimo_peso,
                'icms': item_ref.tabela_icms,
                'percentual_gris': item_ref.tabela_percentual_gris,
                'pedagio_por_100kg': item_ref.tabela_pedagio_por_100kg,
                'valor_tas': item_ref.tabela_valor_tas,
                'percentual_adv': item_ref.tabela_percentual_adv,
                'percentual_rca': item_ref.tabela_percentual_rca,
                'valor_despacho': item_ref.tabela_valor_despacho,
                'valor_cte': item_ref.tabela_valor_cte,
                'icms_incluso': item_ref.tabela_icms_incluso,
                'icms_destino': item_ref.icms_destino or 0
            }
            
            # Calcula frete usando valor e peso total do CNPJ
            valor_cotado = calcular_valor_frete_pela_tabela(tabela_dados, peso_total_cnpj, valor_total_cnpj)
        
        # Cria o frete
        novo_frete = Frete(
            embarque_id=embarque_id,
            cnpj_cliente=cnpj_cliente,
            nome_cliente=nf_faturamento.nome_cliente,
            transportadora_id=embarque.transportadora_id,
            tipo_carga=embarque.tipo_carga,
            modalidade=tabela_dados['modalidade'],
            uf_destino=itens_embarque_cnpj[0].uf_destino,
            cidade_destino=itens_embarque_cnpj[0].cidade_destino,
            peso_total=peso_total_cnpj,
            valor_total_nfs=valor_total_cnpj,
            quantidade_nfs=len(itens_embarque_cnpj),
            numeros_nfs=numeros_nfs,
            # Dados da tabela
            tabela_nome_tabela=tabela_dados['nome_tabela'],
            tabela_valor_kg=tabela_dados['valor_kg'],
            tabela_percentual_valor=tabela_dados['percentual_valor'],
            tabela_frete_minimo_valor=tabela_dados['frete_minimo_valor'],
            tabela_frete_minimo_peso=tabela_dados['frete_minimo_peso'],
            tabela_icms=tabela_dados['icms'],
            tabela_percentual_gris=tabela_dados['percentual_gris'],
            tabela_pedagio_por_100kg=tabela_dados['pedagio_por_100kg'],
            tabela_valor_tas=tabela_dados['valor_tas'],
            tabela_percentual_adv=tabela_dados['percentual_adv'],
            tabela_percentual_rca=tabela_dados['percentual_rca'],
            tabela_valor_despacho=tabela_dados['valor_despacho'],
            tabela_valor_cte=tabela_dados['valor_cte'],
            tabela_icms_incluso=tabela_dados['icms_incluso'],
            tabela_icms_destino=tabela_dados['icms_destino'],
            # Valores
            valor_cotado=valor_cotado,
            valor_considerado=valor_cotado,
            # Fatura
            fatura_frete_id=None,
            # Controle
            criado_por=usuario,
            lancado_em=datetime.utcnow(),
            lancado_por=usuario
        )
        
        db.session.add(novo_frete)
        db.session.commit()
        
        # Determina o método de cálculo usado
        metodo_calculo = "DIRETA (proporcional ao peso)" if embarque.tipo_carga == 'DIRETA' else "FRACIONADA (por CNPJ)"
        
        return True, f"Frete lançado automaticamente - ID: {novo_frete.id} ({metodo_calculo}) - R$ {valor_cotado:.2f}"
        
    except Exception as e:
        db.session.rollback()
        return False, f"Erro ao lançar frete: {str(e)}"

def cancelar_frete_por_embarque(embarque_id, cnpj_cliente=None, usuario='Sistema'):
    """
    Cancela fretes quando um embarque é cancelado
    """
    try:
        query = Frete.query.filter_by(embarque_id=embarque_id)
        
        if cnpj_cliente:
            query = query.filter_by(cnpj_cliente=cnpj_cliente)
        
        fretes = query.filter(Frete.status != 'CANCELADO').all()
        
        for frete in fretes:
            frete.status = 'CANCELADO'
            # Adiciona observação sobre o cancelamento
            obs_atual = frete.observacoes_aprovacao or ""
            frete.observacoes_aprovacao = f"{obs_atual}\nCancelado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M')} por {usuario} devido ao cancelamento do embarque."
        
        db.session.commit()
        
        return True, f"{len(fretes)} frete(s) cancelado(s)"
        
    except Exception as e:
        db.session.rollback()
        return False, f"Erro ao cancelar fretes: {str(e)}"

# =================== ROTAS PARA INTEGRAÇÃO COM EMBARQUES ===================

@fretes_bp.route('/verificar_cte_embarque/<int:embarque_id>')
@login_required
def verificar_cte_embarque(embarque_id):
    """API para verificar se existem CTes lançados para um embarque"""
    fretes_com_cte = verificar_cte_existente_para_embarque(embarque_id)
    
    if fretes_com_cte:
        dados = []
        for frete in fretes_com_cte:
            dados.append({
                'id': frete.id,
                'cnpj_cliente': frete.cnpj_cliente,
                'nome_cliente': frete.nome_cliente,
                'numero_cte': frete.numero_cte,
                'valor_cte': frete.valor_cte,
                'status': frete.status
            })
        
        return jsonify({
            'tem_cte': True,
            'quantidade': len(fretes_com_cte),
            'fretes': dados,
            'mensagem': f'Existem {len(fretes_com_cte)} frete(s) com CTe lançado para este embarque'
        })
    
    return jsonify({
        'tem_cte': False,
        'quantidade': 0,
        'fretes': [],
        'mensagem': 'Nenhum CTe lançado para este embarque'
    })

# Função removida - cancelamento de embarques é gerenciado pelo módulo embarques
# A verificação de CTe é feita através da rota verificar_cte_embarque

@fretes_bp.route('/gatilho_lancamento', methods=['POST'])
@login_required
def gatilho_lancamento_frete():
    """
    Gatilho manual para lançamento automático de frete
    Pode ser chamado quando NF é adicionada ao embarque ou importada no faturamento
    """
    data = request.get_json()
    embarque_id = data.get('embarque_id')
    cnpj_cliente = data.get('cnpj_cliente')
    
    if not embarque_id or not cnpj_cliente:
        return jsonify({
            'sucesso': False,
            'mensagem': 'embarque_id e cnpj_cliente são obrigatórios'
        }), 400
    
    sucesso, mensagem = lancar_frete_automatico(
        embarque_id, 
        cnpj_cliente, 
        usuario=current_user.nome
    )
    
    return jsonify({
        'sucesso': sucesso,
        'mensagem': mensagem
    })

@fretes_bp.route('/corrigir_nfs_fretes')
@login_required
def corrigir_nfs_fretes():
    """Corrige fretes existentes que não têm o campo numeros_nfs preenchido"""
    try:
        # Busca fretes que não têm numeros_nfs preenchido ou está vazio
        fretes_para_corrigir = Frete.query.filter(
            or_(
                Frete.numeros_nfs.is_(None),
                Frete.numeros_nfs == '',
                Frete.numeros_nfs == 'N/A'
            )
        ).all()
        
        fretes_corrigidos = 0
        
        for frete in fretes_para_corrigir:
            # ✅ CORREÇÃO: Busca itens ATIVOS do embarque deste CNPJ
            itens_embarque = EmbarqueItem.query.filter(
                and_(
                    EmbarqueItem.embarque_id == frete.embarque_id,
                    EmbarqueItem.cnpj_cliente == frete.cnpj_cliente,
                    EmbarqueItem.status == 'ativo',
                    EmbarqueItem.nota_fiscal.isnot(None)
                )
            ).all()
            
            if itens_embarque:
                # Extrai os números das NFs
                numeros_nfs = [item.nota_fiscal for item in itens_embarque if item.nota_fiscal]
                if numeros_nfs:
                    frete.numeros_nfs = ','.join(numeros_nfs)
                    frete.quantidade_nfs = len(numeros_nfs)
                    fretes_corrigidos += 1
        
        db.session.commit()
        
        flash(f'✅ {fretes_corrigidos} frete(s) corrigido(s) com sucesso!', 'success')
        return redirect(url_for('fretes.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao corrigir fretes: {str(e)}', 'error')
        return redirect(url_for('fretes.index'))

# =================== FUNÇÃO PARA LANÇAMENTO AUTOMÁTICO ===================

def validar_cnpj_embarque_faturamento(embarque_id):
    """
    Valida se os CNPJs das NFs no embarque coincidem com os CNPJs no faturamento
    
    REGRAS IMPLEMENTADAS:
    a) Conferir se a NF está no faturamento
    b) Conferir se o CNPJ bate com o do faturamento  
    c) Atualizar peso e valor da NF no embarque a partir do faturamento
    d) NÃO SUBSTITUIR dados do embarque pelos dados da NF
    """
    try:
        from app.faturamento.models import RelatorioFaturamentoImportado
        
        embarque = Embarque.query.get(embarque_id)
        if not embarque:
            return False, "Embarque não encontrado"
        
        erros_encontrados = []
        itens_com_erro = 0
        itens_sem_nf = 0
        
        for item in embarque.itens:
            # ✅ CORREÇÃO: Só valida itens ATIVOS
            if item.status != 'ativo':
                continue
                
            # REQUISITO: Todas as NFs dos itens ATIVOS devem estar preenchidas
            if not item.nota_fiscal or item.nota_fiscal.strip() == '':
                item.erro_validacao = "NF_NAO_PREENCHIDA"
                erros_encontrados.append(f"Item {item.cliente} - {item.pedido}: NF não preenchida")
                itens_com_erro += 1
                itens_sem_nf += 1
                continue
            
            # REGRA a: Conferir se a NF está no faturamento
            nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(
                numero_nf=item.nota_fiscal
            ).first()
            
            if not nf_faturamento:
                # NF não encontrada - marca como pendente mas permite continuar o processo
                item.erro_validacao = "NF_PENDENTE_FATURAMENTO"
                # Não conta como erro crítico - permite lançamento de frete
                continue
            
            # REGRA b: Conferir se a NF pertence ao cliente correto
            # ✅ CORREÇÃO: Se o item tem CNPJ, verifica se a NF pertence a este CNPJ
            if item.cnpj_cliente:
                if item.cnpj_cliente != nf_faturamento.cnpj_cliente:
                    # ✅ CORREÇÃO: NF não pertence ao cliente - APAGA APENAS a NF, mantém todos os outros dados
                    nf_original = item.nota_fiscal
                    item.erro_validacao = f"NF_DIVERGENTE: NF {nf_original} pertence ao CNPJ {nf_faturamento.cnpj_cliente}, não a {item.cnpj_cliente}"
                    item.nota_fiscal = None  # ✅ APAGA APENAS a NF divergente
                    
                    # ✅ MANTÉM todos os outros dados: CNPJ, peso, valor, tabelas, separação, etc.
                    # NÃO toca em nada além da NF e do erro_validacao
                    
                    erros_encontrados.append(f"NF {nf_original} foi removida pois pertence ao CNPJ {nf_faturamento.cnpj_cliente}, não a {item.cnpj_cliente}")
                    itens_com_erro += 1
                    continue
                    
                # ✅ CNPJ BATE: Atualiza peso e valor da NF no embarque
                item.peso = float(nf_faturamento.peso_bruto or 0)
                item.valor = float(nf_faturamento.valor_total or 0)
                item.erro_validacao = None  # Limpa erro se estava OK
                
            else:
                # ✅ CORREÇÃO: Item sem CNPJ não pode ter NF preenchida
                # Mantém a NF para posterior validação quando o faturamento for importado
                # Esta validação será refeita quando o CNPJ for definido
                item.erro_validacao = f"CLIENTE_NAO_DEFINIDO: Defina o cliente antes de preencher a NF"
                
                # ✅ MANTÉM a NF para validação posterior (quando faturamento for importado)
                # NÃO apaga a NF - apenas marca como pendente de definição de cliente
                # Se o usuário informar o CNPJ depois, a validação será refeita
                
                erros_encontrados.append(f"NF {item.nota_fiscal} está pendente - defina o cliente primeiro")
                itens_com_erro += 1
                continue
        
        db.session.commit()
        
        if itens_sem_nf > 0:
            return False, f"❌ {itens_sem_nf} item(ns) sem NF preenchida. Todos os itens devem ter NF para lançar fretes."
        
        if erros_encontrados:
            return False, f"❌ Encontrados {itens_com_erro} erro(s): {'; '.join(erros_encontrados)}"
        
        return True, f"✅ Todos os requisitos atendidos! {len(embarque.itens)} NF(s) validada(s) com sucesso"
        
    except Exception as e:
        return False, f"Erro na validação: {str(e)}"

def processar_lancamento_automatico_fretes(embarque_id=None, cnpj_cliente=None, usuario='Sistema'):
    """
    Processa lançamento automático de fretes com REGRAS RIGOROSAS:
    
    REQUISITOS OBRIGATÓRIOS:
    d) Verificar se todas as NFs daquele embarque estão validadas
    e) Lançar o frete respeitando o tipo_carga ("FRACIONADA", "DIRETA")
    
    Pode ser chamado:
    - Ao salvar embarque (embarque_id fornecido)
    - Ao importar faturamento (cnpj_cliente fornecido)
    """
    try:
        fretes_lancados = []
        
        if embarque_id:
            # Cenário 1: Embarque foi salvo
            embarque = Embarque.query.get(embarque_id)
            if not embarque:
                return False, "Embarque não encontrado"
            
            # VALIDAÇÃO RIGOROSA: Todas as NFs devem estar validadas
            sucesso_validacao, resultado_validacao = validar_cnpj_embarque_faturamento(embarque_id)
            
            if not sucesso_validacao:
                # Se há erros, não lança fretes
                return True, resultado_validacao
            
            # ✅ Todas as NFs estão validadas - procede com lançamento
            # Busca todos os CNPJs únicos deste embarque
            # ✅ CORREÇÃO: Busca CNPJs únicos deste embarque (apenas itens ATIVOS)
            cnpjs_embarque = db.session.query(EmbarqueItem.cnpj_cliente)\
                .filter(EmbarqueItem.embarque_id == embarque_id)\
                .filter(EmbarqueItem.status == 'ativo')\
                .filter(EmbarqueItem.nota_fiscal.isnot(None))\
                .filter(EmbarqueItem.cnpj_cliente.isnot(None))\
                .filter(EmbarqueItem.erro_validacao.is_(None))\
                .distinct().all()
            
            for (cnpj,) in cnpjs_embarque:
                if cnpj:
                    sucesso, resultado = tentar_lancamento_frete_automatico(embarque_id, cnpj, usuario)
                    if sucesso:
                        fretes_lancados.append(resultado)
        
        elif cnpj_cliente:
            # Cenário 2: Faturamento foi importado
            # ✅ CORREÇÃO: Busca embarques que têm NFs deste CNPJ preenchidas (apenas itens ATIVOS)
            embarques_com_cnpj = db.session.query(EmbarqueItem.embarque_id)\
                .filter(EmbarqueItem.cnpj_cliente == cnpj_cliente)\
                .filter(EmbarqueItem.status == 'ativo')\
                .filter(EmbarqueItem.nota_fiscal.isnot(None))\
                .distinct().all()
            
            for (embarque_id_encontrado,) in embarques_com_cnpj:
                # VALIDAÇÃO RIGOROSA para cada embarque
                sucesso_validacao, _ = validar_cnpj_embarque_faturamento(embarque_id_encontrado)
                
                # Só lança se TODOS os requisitos estiverem atendidos
                if "✅ Todos os requisitos atendidos" in _:
                    sucesso, resultado = tentar_lancamento_frete_automatico(embarque_id_encontrado, cnpj_cliente, usuario)
                    if sucesso:
                        fretes_lancados.append(resultado)
        
        if fretes_lancados:
            return True, f"✅ {len(fretes_lancados)} frete(s) lançado(s) automaticamente seguindo as regras DIRETA/FRACIONADA!"
        else:
            return True, "ℹ️ Nenhum frete foi lançado automaticamente. Verifique se todos os requisitos estão atendidos."
        
    except Exception as e:
        return False, f"Erro no processamento automático: {str(e)}"

def tentar_lancamento_frete_automatico(embarque_id, cnpj_cliente, usuario='Sistema'):
    """
    Tenta lançar um frete específico para um embarque + CNPJ
    """
    try:
        # Verifica se já existe frete para esta combinação
        frete_existente = Frete.query.filter(
            and_(
                Frete.embarque_id == embarque_id,
                Frete.cnpj_cliente == cnpj_cliente
            )
        ).first()
        
        if frete_existente:
            return False, f"Frete já existe: #{frete_existente.id}"
        
        # Verifica se pode lançar (requisitos atendidos)
        pode_lancar, motivo = verificar_requisitos_para_lancamento_frete(embarque_id, cnpj_cliente)
        if not pode_lancar:
            return False, motivo
        
        # Lança o frete automaticamente
        sucesso, resultado = lancar_frete_automatico(embarque_id, cnpj_cliente, usuario)
        return sucesso, resultado
        
    except Exception as e:
        return False, f"Erro ao tentar lançamento: {str(e)}"

# =================== GERENCIAMENTO DE DESPESAS EXTRAS ===================

@fretes_bp.route('/despesas/gerenciar', methods=['GET'])
@login_required
def gerenciar_despesas_extras():
    """Lista despesas extras para gerenciamento (vinculação a faturas, etc.)"""
    # Busca despesas extras sem fatura vinculada
    despesas_sem_fatura = db.session.query(DespesaExtra).join(Frete).filter(
        or_(
            DespesaExtra.observacoes.is_(None),
            ~DespesaExtra.observacoes.contains('Fatura:')
        )
    ).order_by(desc(DespesaExtra.criado_em)).all()
    
    # Busca despesas extras com fatura vinculada
    despesas_com_fatura = db.session.query(DespesaExtra).join(Frete).filter(
        and_(
            DespesaExtra.observacoes.isnot(None),
            DespesaExtra.observacoes.contains('Fatura:')
        )
    ).order_by(desc(DespesaExtra.criado_em)).all()
    
    return render_template('fretes/gerenciar_despesas_extras.html',
                         despesas_sem_fatura=despesas_sem_fatura,
                         despesas_com_fatura=despesas_com_fatura)


@fretes_bp.route('/despesas/<int:despesa_id>/vincular_fatura', methods=['GET', 'POST'])
@login_required
def vincular_despesa_fatura(despesa_id):
    """Vincula uma despesa extra existente a uma fatura"""
    despesa = DespesaExtra.query.get_or_404(despesa_id)
    frete = Frete.query.get(despesa.frete_id)
    
    # Busca faturas disponíveis da mesma transportadora
    faturas_disponiveis = FaturaFrete.query.filter_by(
        transportadora_id=frete.transportadora_id,
        status_conferencia='PENDENTE'
    ).order_by(desc(FaturaFrete.criado_em)).all()
    
    if request.method == 'POST':
        fatura_id = request.form.get('fatura_id')
        tipo_documento_cobranca = request.form.get('tipo_documento_cobranca')
        valor_cobranca = request.form.get('valor_cobranca')
        numero_cte_documento = request.form.get('numero_cte_documento')  # ✅ NOVO CAMPO
        
        if not fatura_id:
            flash('Selecione uma fatura!', 'error')
            return render_template('fretes/vincular_despesa_fatura.html',
                                 despesa=despesa,
                                 frete=frete,
                                 faturas_disponiveis=faturas_disponiveis)
        
        try:
            # Busca a fatura selecionada
            fatura = FaturaFrete.query.get(fatura_id)
            if not fatura:
                flash('Fatura não encontrada!', 'error')
                return render_template('fretes/vincular_despesa_fatura.html',
                                     despesa=despesa,
                                     frete=frete,
                                     faturas_disponiveis=faturas_disponiveis)
            
            # Converte valor da cobrança
            valor_cobranca_float = float(valor_cobranca.replace(',', '.')) if valor_cobranca else despesa.valor_despesa
            
            # Atualiza a despesa
            despesa.tipo_documento = tipo_documento_cobranca
            despesa.valor_despesa = valor_cobranca_float
            # ✅ ATUALIZA NÚMERO DO DOCUMENTO
            despesa.numero_documento = numero_cte_documento if numero_cte_documento else 'PENDENTE_FATURA'
            
            # **COPIA VENCIMENTO DA FATURA PARA A DESPESA**
            if fatura.vencimento:
                despesa.vencimento_despesa = fatura.vencimento
            
            # Atualiza observações para incluir fatura
            observacoes_original = despesa.observacoes or ""
            despesa.observacoes = f"Fatura: {fatura.numero_fatura} | {observacoes_original}"
            
            db.session.commit()
            
            flash(f'Despesa extra vinculada à fatura {fatura.numero_fatura} com sucesso!', 'success')
            return redirect(url_for('fretes.visualizar_frete', frete_id=frete.id))
            
        except Exception as e:
            flash(f'Erro ao vincular despesa à fatura: {str(e)}', 'error')
            return render_template('fretes/vincular_despesa_fatura.html',
                                 despesa=despesa,
                                 frete=frete,
                                 faturas_disponiveis=faturas_disponiveis)
    
    return render_template('fretes/vincular_despesa_fatura.html',
                         despesa=despesa,
                         frete=frete,
                         faturas_disponiveis=faturas_disponiveis)


@fretes_bp.route('/despesas/<int:despesa_id>/desvincular_fatura', methods=['POST'])
@login_required
def desvincular_despesa_fatura(despesa_id):
    """Desvincula uma despesa extra de sua fatura"""
    despesa = DespesaExtra.query.get_or_404(despesa_id)
    
    try:
        # Remove referência da fatura das observações
        if despesa.observacoes and 'Fatura:' in despesa.observacoes:
            # Remove a parte "Fatura: XXX |" das observações
            despesa.observacoes = re.sub(r'Fatura: [^|]+ \| ?', '', despesa.observacoes)
            if not despesa.observacoes.strip():
                despesa.observacoes = None
        
        db.session.commit()
        flash('Despesa extra desvinculada da fatura com sucesso!', 'success')
        
    except Exception as e:
        flash(f'Erro ao desvincular despesa da fatura: {str(e)}', 'error')
    
    return redirect(url_for('fretes.gerenciar_despesas_extras'))

@fretes_bp.route('/despesas/<int:despesa_id>/editar_documento', methods=['GET', 'POST'])
@login_required  
def editar_documento_despesa(despesa_id):
    """Permite editar o número do documento APENAS se houver fatura vinculada"""
    despesa = DespesaExtra.query.get_or_404(despesa_id)
    
    # ✅ VALIDAÇÃO: Só permite editar se houver fatura vinculada
    if not despesa.frete.fatura_frete_id:
        flash('⚠️ Para preencher o número do documento, a fatura deve estar vinculada primeiro!', 'warning')
        return redirect(url_for('fretes.visualizar_frete', frete_id=despesa.frete_id))
    
    if request.method == 'POST':
        numero_documento = request.form.get('numero_documento', '').strip()
        tipo_documento = request.form.get('tipo_documento', '')
        
        if not numero_documento:
            flash('Número do documento é obrigatório!', 'error')
        elif numero_documento == 'PENDENTE_FATURA':
            flash('Este número não é permitido!', 'error')
        else:
            try:
                despesa.numero_documento = numero_documento
                despesa.tipo_documento = tipo_documento
                
                db.session.commit()
                flash('Documento atualizado com sucesso!', 'success')
                return redirect(url_for('fretes.visualizar_frete', frete_id=despesa.frete_id))
                
            except Exception as e:
                flash(f'Erro ao atualizar documento: {str(e)}', 'error')
    
    return render_template('fretes/editar_documento_despesa.html', 
                         despesa=despesa,
                         fatura=despesa.frete.fatura_frete)

@fretes_bp.route('/contas_correntes')
@login_required
def listar_contas_correntes():
    """Lista todas as contas correntes das transportadoras"""
    try:
        # Busca todas as transportadoras com movimentações de conta corrente
        from sqlalchemy import func
        from app.transportadoras.models import Transportadora
        
        transportadoras_com_conta = db.session.query(
            Transportadora.id,
            Transportadora.razao_social,
            func.sum(ContaCorrenteTransportadora.valor_credito).label('total_creditos'),
            func.sum(ContaCorrenteTransportadora.valor_debito).label('total_debitos'),
            func.count(ContaCorrenteTransportadora.id).label('total_movimentacoes')
        ).join(
            ContaCorrenteTransportadora,
            Transportadora.id == ContaCorrenteTransportadora.transportadora_id
        ).filter(
            ContaCorrenteTransportadora.status == 'ATIVO'
        ).group_by(
            Transportadora.id,
            Transportadora.razao_social
        ).all()
        
        # Calcula saldo para cada transportadora
        contas_correntes = []
        for tp in transportadoras_com_conta:
            total_creditos = tp.total_creditos or 0
            total_debitos = tp.total_debitos or 0
            saldo_atual = total_debitos - total_creditos  # Positivo = transportadora deve para empresa
            
            contas_correntes.append({
                'transportadora_id': tp.id,
                'transportadora_nome': tp.razao_social,
                'total_creditos': total_creditos,
                'total_debitos': total_debitos,
                'saldo_atual': saldo_atual,
                'total_movimentacoes': tp.total_movimentacoes
            })
        
        # Ordena por saldo (maiores débitos primeiro)
        contas_correntes.sort(key=lambda x: x['saldo_atual'], reverse=True)
        
        return render_template('fretes/contas_correntes.html',
                             contas_correntes=contas_correntes)
        
    except Exception as e:
        flash(f'Erro ao carregar contas correntes: {str(e)}', 'error')
        return redirect(url_for('fretes.index'))

@fretes_bp.route('/<int:frete_id>/excluir', methods=['POST'])
@login_required
def excluir_frete(frete_id):
    """Exclui um frete (CTe) se a fatura não estiver conferida"""
    frete = Frete.query.get_or_404(frete_id)
    
    try:
        # Verifica se fatura está conferida
        if frete.fatura_frete and frete.fatura_frete.status_conferencia == 'CONFERIDO':
            flash('❌ Não é possível excluir CTe de fatura conferida!', 'error')
            return redirect(url_for('fretes.visualizar_frete', frete_id=frete_id))
        
        # Remove movimentações da conta corrente relacionadas
        ContaCorrenteTransportadora.query.filter_by(frete_id=frete_id).delete()
        
        # Salva dados para o flash
        numero_cte = frete.numero_cte or f'Frete #{frete.id}'
        cliente = frete.nome_cliente
        transportadora = frete.transportadora.razao_social
        
        # Exclui o frete
        db.session.delete(frete)
        db.session.commit()
        
        flash(f'✅ CTe {numero_cte} excluído com sucesso! Cliente: {cliente} | Transportadora: {transportadora}', 'success')
        return redirect(url_for('fretes.listar_fretes'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir CTe: {str(e)}', 'error')
        return redirect(url_for('fretes.visualizar_frete', frete_id=frete_id))

@fretes_bp.route('/despesas/<int:despesa_id>/excluir', methods=['POST'])
@login_required
def excluir_despesa_extra(despesa_id):
    """Exclui uma despesa extra se a fatura não estiver conferida"""
    despesa = DespesaExtra.query.get_or_404(despesa_id)
    frete = despesa.frete
    
    try:
        # Verifica se fatura está conferida
        if frete.fatura_frete and frete.fatura_frete.status_conferencia == 'CONFERIDO':
            flash('❌ Não é possível excluir despesa de fatura conferida!', 'error')
            return redirect(url_for('fretes.visualizar_frete', frete_id=frete.id))
        
        # Salva dados para o flash
        tipo_despesa = despesa.tipo_despesa
        numero_documento = despesa.numero_documento
        valor = despesa.valor_despesa
        
        # Exclui a despesa
        db.session.delete(despesa)
        db.session.commit()
        
        flash(f'✅ Despesa extra excluída com sucesso! Tipo: {tipo_despesa} | Documento: {numero_documento} | Valor: R$ {valor:.2f}', 'success')
        return redirect(url_for('fretes.visualizar_frete', frete_id=frete.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir despesa extra: {str(e)}', 'error')
        return redirect(url_for('fretes.visualizar_frete', frete_id=frete.id))

@fretes_bp.route('/fatura/<int:fatura_id>/download')
@login_required
def download_pdf_fatura(fatura_id):
    """Serve PDFs de faturas (S3 e locais)"""
    fatura = FaturaFrete.query.get_or_404(fatura_id)
    
    if not fatura.arquivo_pdf:
        flash("❌ Esta fatura não possui arquivo PDF.", 'warning')
        return redirect(request.referrer or url_for('fretes.listar_faturas'))
    
    try:
        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        
        # Para arquivos S3 (novos)
        if not fatura.arquivo_pdf.startswith('uploads/'):
            url = storage.get_file_url(fatura.arquivo_pdf)
            if url:
                return redirect(url)
            else:
                flash("❌ Erro ao gerar link do arquivo.", 'danger')
                return redirect(request.referrer)
        else:
            # Para arquivos locais (antigos)
            pasta = os.path.dirname(fatura.arquivo_pdf)
            nome_arquivo = os.path.basename(fatura.arquivo_pdf)
            return send_from_directory(
                os.path.join(current_app.root_path, 'static', pasta), 
                nome_arquivo
            )
            
    except Exception as e:
        flash(f"❌ Erro ao baixar arquivo: {str(e)}", 'danger')
        return redirect(request.referrer)

# ============================================================================
# LANÇAMENTO FRETEIROS
# ============================================================================

@fretes_bp.route('/lancamento_freteiros')
@login_required
@require_financeiro()  # 🔒 RESTRITO - apenas financeiro pode lançar freteiros
def lancamento_freteiros():
    """
    Tela para lançamento de fretes dos freteiros
    Mostra todos os freteiros com fretes e despesas extras pendentes
    """
    
    # Busca apenas transportadoras marcadas como freteiros
    freteiros = Transportadora.query.filter_by(freteiro=True).all()
    
    dados_freteiros = []
    
    for freteiro in freteiros:
        # Busca fretes pendentes (sem número CTE ou com valor CTE vazio) - APENAS EMBARQUES ATIVOS
        fretes_pendentes = Frete.query.join(Embarque).filter(
            Frete.transportadora_id == freteiro.id,
            Embarque.status == 'ativo',  # Apenas embarques ativos
            db.or_(
                Frete.numero_cte.is_(None),
                Frete.numero_cte == '',
                Frete.valor_cte.is_(None)
            )
        ).all()
        
        # Busca despesas extras pendentes (sem documento) - através do frete - APENAS EMBARQUES ATIVOS
        despesas_pendentes = db.session.query(DespesaExtra).join(Frete).join(Embarque).filter(
            Frete.transportadora_id == freteiro.id,
            Embarque.status == 'ativo',  # Apenas embarques ativos
            db.or_(
                DespesaExtra.numero_documento.is_(None),
                DespesaExtra.numero_documento == '',
                DespesaExtra.numero_documento == 'PENDENTE_FATURA'
            )
        ).all()
        
        if fretes_pendentes or despesas_pendentes:
            # Organiza fretes por embarque
            fretes_por_embarque = {}
            total_valor = 0
            peso_total_transportadora = 0
            valor_nf_total_transportadora = 0
            valor_cotado_total_transportadora = 0
            
            for frete in fretes_pendentes:
                embarque_id = frete.embarque_id
                if embarque_id not in fretes_por_embarque:
                    fretes_por_embarque[embarque_id] = {
                        'embarque': frete.embarque,
                        'fretes': [],
                        'total_cotado': 0,
                        'total_considerado': 0
                    }
                
                # **FORÇA CÁLCULO** do peso total APENAS das NFs específicas do frete
                if frete.embarque and frete.numeros_nfs:
                    # Pega apenas as NFs que pertencem a este frete
                    nfs_frete = [nf.strip() for nf in frete.numeros_nfs.split(',') if nf.strip()]
                    frete.peso_total = sum([
                        item.peso or 0 for item in frete.embarque.itens 
                        if item.peso and item.nota_fiscal and item.nota_fiscal.strip() in nfs_frete and item.status == 'ativo'
                    ])
                else:
                    frete.peso_total = 0
                
                # **FORÇA CÁLCULO** valor NF do frete através APENAS dos itens que pertencem a este frete específico
                if frete.embarque and frete.numeros_nfs:
                    # Pega apenas as NFs que pertencem a este frete
                    nfs_frete = [nf.strip() for nf in frete.numeros_nfs.split(',') if nf.strip()]
                    frete.valor_nf = sum([
                        item.valor or 0 for item in frete.embarque.itens 
                        if item.valor and item.nota_fiscal and item.nota_fiscal.strip() in nfs_frete and item.status == 'ativo'
                    ])
                else:
                    frete.valor_nf = 0
                
                fretes_por_embarque[embarque_id]['fretes'].append(frete)
                fretes_por_embarque[embarque_id]['total_cotado'] += frete.valor_cotado or 0
                fretes_por_embarque[embarque_id]['total_considerado'] += frete.valor_considerado or frete.valor_cotado or 0
                
                # Soma totais da transportadora usando valores calculados
                total_valor += frete.valor_considerado or frete.valor_cotado or 0
                peso_total_transportadora += frete.peso_total
                valor_nf_total_transportadora += frete.valor_nf
                valor_cotado_total_transportadora += frete.valor_cotado or 0
            
            dados_freteiros.append({
                'freteiro': freteiro,
                'fretes_por_embarque': fretes_por_embarque,
                'despesas_extras': despesas_pendentes,
                'total_pendencias': len(fretes_pendentes) + len(despesas_pendentes),
                'total_valor': total_valor + sum([d.valor_despesa or 0 for d in despesas_pendentes]),
                'peso_total': peso_total_transportadora,
                'valor_nf_total': valor_nf_total_transportadora,
                'valor_cotado_total': valor_cotado_total_transportadora
            })
    
    return render_template('fretes/lancamento_freteiros.html', 
                          dados_freteiros=dados_freteiros,
                          form=LancamentoFreteirosForm())

@fretes_bp.route('/emitir_fatura_freteiro/<int:transportadora_id>', methods=['POST'])
@login_required
@require_financeiro()  # 🔒 RESTRITO - apenas financeiro pode emitir faturas de freteiros
def emitir_fatura_freteiro(transportadora_id):
    """
    Emite fatura para um freteiro com base nos lançamentos selecionados
    """
    
    form = LancamentoFreteirosForm()
    transportadora = Transportadora.query.get_or_404(transportadora_id)
    
    if not transportadora.freteiro:
        flash('Erro: Transportadora não é um freteiro', 'danger')
        return redirect(url_for('fretes.lancamento_freteiros'))
    
    if form.validate_on_submit():
        try:
            # Pega os IDs dos fretes e despesas selecionados via request.form
            fretes_selecionados = request.form.getlist('fretes_selecionados')
            despesas_selecionadas = request.form.getlist('despesas_selecionadas')
            
            if not fretes_selecionados and not despesas_selecionadas:
                flash('Selecione pelo menos um lançamento para emitir a fatura', 'warning')
                return redirect(url_for('fretes.lancamento_freteiros'))
            
            data_vencimento = form.data_vencimento.data
            observacoes = form.observacoes.data or ''
            
            # Calcula valor total da fatura
            valor_total_fatura = 0
            ctes_criados = []
            
            # Captura valores considerados alterados por embarque (se houver)
            valores_considerados_embarque = {}
            for key, value in request.form.items():
                if key.startswith('valor_considerado_') and value:
                    embarque_id = key.replace('valor_considerado_', '')
                    try:
                        valores_considerados_embarque[int(embarque_id)] = float(value)
                    except (ValueError, TypeError):
                        pass
            
            # Aplica rateio por peso se valores foram alterados
            rateios_por_embarque = {}
            for embarque_id, valor_novo in valores_considerados_embarque.items():
                # Busca fretes do embarque selecionados
                fretes_embarque = [
                    Frete.query.get(int(fid)) for fid in fretes_selecionados 
                    if Frete.query.get(int(fid)) and Frete.query.get(int(fid)).embarque_id == embarque_id
                ]
                
                if fretes_embarque:
                    # Calcula peso total
                    peso_total = sum([
                        sum([item.peso for item in frete.embarque.itens if item.peso]) 
                        for frete in fretes_embarque if frete.embarque
                    ])
                    
                    if peso_total > 0:
                        # Calcula rateio por peso
                        for frete in fretes_embarque:
                            peso_frete = sum([item.peso for item in frete.embarque.itens if item.peso]) if frete.embarque else 0
                            valor_rateado = (peso_frete / peso_total) * valor_novo
                            rateios_por_embarque[frete.id] = valor_rateado
            
            # Processa fretes selecionados
            for frete_id in fretes_selecionados:
                frete = Frete.query.get(int(frete_id))
                if frete and frete.transportadora_id == transportadora_id:
                    # Usa valor rateado se existe, senão usa valor original
                    valor_considerado = rateios_por_embarque.get(frete.id) or frete.valor_considerado or frete.valor_cotado
                    valor_total_fatura += valor_considerado
                    
                    # Gera nome do CTe
                    data_embarque = frete.embarque.data_embarque or frete.embarque.data_prevista_embarque
                    data_str = data_embarque.strftime('%d/%m/%Y') if data_embarque else 'S/Data'
                    nfs_str = frete.numeros_nfs[:50] + ('...' if len(frete.numeros_nfs) > 50 else '')
                    
                    nome_cte = f"Frete ({data_str}) NFs {nfs_str}"
                    
                    # Atualiza frete
                    frete.numero_cte = nome_cte
                    frete.valor_cte = valor_considerado
                    frete.valor_considerado = valor_considerado
                    frete.valor_pago = valor_considerado
                    frete.vencimento = data_vencimento
                    frete.status = 'APROVADO'
                    frete.aprovado_por = current_user.nome
                    frete.aprovado_em = datetime.utcnow()
                    
                    ctes_criados.append(nome_cte)
            
            # Processa despesas extras selecionadas
            for despesa_id in despesas_selecionadas:
                despesa = DespesaExtra.query.get(int(despesa_id))
                if despesa and despesa.frete.transportadora_id == transportadora_id:
                    valor_total_fatura += despesa.valor_despesa or 0
                    
                    # Preenche documento da despesa
                    despesa.tipo_documento = 'CTE'
                    despesa.numero_documento = f"Despesa {despesa.tipo_despesa}"
                    despesa.vencimento_despesa = data_vencimento
                    
                    ctes_criados.append(f"Despesa: {despesa.tipo_despesa}")
            
            # Cria a fatura
            data_venc_str = data_vencimento.strftime('%d%m%Y')
            nome_fatura = f"Fechamento {transportadora.razao_social} {data_venc_str}"
            
            nova_fatura = FaturaFrete(
                transportadora_id=transportadora_id,
                numero_fatura=nome_fatura,
                data_emissao=datetime.now().date(),
                valor_total_fatura=valor_total_fatura,
                vencimento=data_vencimento,
                status_conferencia='CONFERIDO',  # Automaticamente conferida
                conferido_por=current_user.nome,
                conferido_em=datetime.utcnow(),
                observacoes_conferencia=f"Fatura criada automaticamente via lançamento freteiros. {observacoes}",
                criado_por=current_user.nome
            )
            
            db.session.add(nova_fatura)
            db.session.flush()  # Para obter o ID
            
            # Vincula fretes à fatura
            for frete_id in fretes_selecionados:
                frete = Frete.query.get(int(frete_id))
                if frete:
                    frete.fatura_frete_id = nova_fatura.id
            
            # Vincula despesas à fatura (via observações)
            for despesa_id in despesas_selecionadas:
                despesa = DespesaExtra.query.get(int(despesa_id))
                if despesa:
                    obs_atual = despesa.observacoes or ''
                    despesa.observacoes = f"{obs_atual} | Fatura: {nova_fatura.numero_fatura}".strip(' |')
            
            db.session.commit()
            
            flash(f'''
                <strong>Fatura criada com sucesso!</strong><br>
                <strong>Fatura:</strong> {nova_fatura.numero_fatura}<br>
                <strong>Valor Total:</strong> R$ {valor_total_fatura:,.2f}<br>
                <strong>CTes Criados:</strong> {len(ctes_criados)}<br>
                <strong>Vencimento:</strong> {data_vencimento.strftime('%d/%m/%Y')}
            ''', 'success')
            
            return redirect(url_for('fretes.listar_faturas'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao emitir fatura: {str(e)}', 'danger')
            return redirect(url_for('fretes.lancamento_freteiros'))
    
    flash('Dados inválidos no formulário', 'danger')
    return redirect(url_for('fretes.lancamento_freteiros'))
