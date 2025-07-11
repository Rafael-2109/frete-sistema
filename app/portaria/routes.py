from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import traceback
import logging

logger = logging.getLogger(__name__)

from app import db

# 🔒 Importar decoradores de permissão
from app.utils.auth_decorators import require_portaria

from app.portaria.models import Motorista, ControlePortaria
from app.portaria.forms import CadastroMotoristaForm, BuscarMotoristaForm, ControlePortariaForm, FiltroHistoricoForm
from app.embarques.models import Embarque
from app.monitoramento.models import EntregaMonitorada
from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf
from app.utils.file_storage import get_file_storage

portaria_bp = Blueprint('portaria', __name__, url_prefix='/portaria')

def salvar_foto_documento(foto):
    """
    Salva foto do documento do motorista usando sistema centralizado
    """
    if not foto:
        return None
    
    try:
        storage = get_file_storage()
        file_path = storage.save_file(
            file=foto,
            folder='motoristas',
            allowed_extensions=['jpg', 'jpeg', 'png']
        )
        return file_path
    except Exception as e:
        current_app.logger.error(f"Erro ao salvar foto do motorista: {str(e)}")
        return None



@portaria_bp.route('/')
@login_required
@require_portaria()  # 🔒 BLOQUEADO para vendedores
def dashboard():
    """
    Dashboard principal da portaria - mostra veículos do dia e embarques pendentes
    """
    form_buscar = BuscarMotoristaForm()
    form_controle = ControlePortariaForm()
    
    # Busca veículos do dia ordenados conforme especificação
    veiculos_hoje = ControlePortaria.veiculos_do_dia()
    
    # Busca embarques pendentes (sem data de embarque)
    embarques_pendentes = Embarque.query.filter(
        Embarque.status == 'ativo',
        Embarque.data_embarque.is_(None)
    ).order_by(Embarque.numero.desc()).all()
    
    return render_template(
        'portaria/dashboard.html',
        form_buscar=form_buscar,
        form_controle=form_controle,
        veiculos_hoje=veiculos_hoje,
        embarques_pendentes=embarques_pendentes
    )

@portaria_bp.route('/buscar_motorista', methods=['POST'])
@login_required
@require_portaria()  # 🔒 BLOQUEADO para vendedores
def buscar_motorista():
    """
    Busca motorista por CPF via AJAX
    """
    # 🐛 Debug CSRF
    logger.info(f"🔍 Headers: {dict(request.headers)}")
    logger.info(f"🔍 Form data: {dict(request.form)}")
    
    cpf = request.form.get('cpf', '').strip()
    
    if not cpf:
        return jsonify({'success': False, 'message': 'CPF é obrigatório'})
    
    motorista = Motorista.buscar_por_cpf(cpf)
    
    if motorista:
        return jsonify({
            'success': True,
            'motorista': {
                'id': motorista.id,
                'nome_completo': motorista.nome_completo,
                'rg': motorista.rg,
                'cpf': motorista.cpf,
                'telefone': motorista.telefone
            }
        })
    else:
        return jsonify({
            'success': False, 
            'message': 'Motorista não encontrado',
            'redirect_cadastro': True
        })

@portaria_bp.route('/cadastrar_motorista', methods=['GET', 'POST'])
@login_required
@require_portaria()  # 🔒 BLOQUEADO para vendedores
def cadastrar_motorista():
    """
    Cadastra ou edita motorista
    """
    motorista_id = request.args.get('id', type=int)
    motorista = None
    
    if motorista_id:
        motorista = Motorista.query.get_or_404(motorista_id)
    
    form = CadastroMotoristaForm(obj=motorista)
    
    if form.validate_on_submit():
        try:
            if motorista:
                # Atualiza motorista existente
                form.populate_obj(motorista)
                motorista.atualizado_em = datetime.utcnow()
                acao = 'atualizado'
            else:
                # Verifica se CPF já existe
                cpf_existente = Motorista.buscar_por_cpf(form.cpf.data)
                if cpf_existente:
                    flash('CPF já cadastrado para outro motorista!', 'danger')
                    return render_template('portaria/cadastrar_motorista.html', form=form)
                
                # Cria novo motorista
                motorista = Motorista()
                form.populate_obj(motorista)
                acao = 'cadastrado'
            
            # Salva foto se fornecida
            if form.foto_documento.data:
                foto_path = salvar_foto_documento(form.foto_documento.data)
                if foto_path:
                    motorista.foto_documento = foto_path
            
            db.session.add(motorista)
            db.session.commit()
            
            flash(f'Motorista {acao} com sucesso!', 'success')
            
            # Se veio da portaria, redireciona com dados do motorista
            if request.args.get('from') == 'portaria':
                return redirect(url_for('portaria.dashboard', motorista_cpf=motorista.cpf))
            else:
                return redirect(url_for('portaria.listar_motoristas'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar motorista: {str(e)}', 'danger')
    
    return render_template('portaria/cadastrar_motorista.html', form=form, motorista=motorista)

@portaria_bp.route('/registrar_movimento', methods=['POST'])
@login_required
@require_portaria()  # 🔒 BLOQUEADO para vendedores
def registrar_movimento():
    """
    Registra chegada, entrada ou saída de veículo
    """
    # 🔒 VALIDAÇÃO CSRF ROBUSTA
    from flask_wtf.csrf import validate_csrf
    from app.utils.csrf_helper import validate_api_csrf
    
    try:
        # Tentativa de validação CSRF com fallback
        csrf_valido = validate_api_csrf(request, logger)
        if not csrf_valido:
            logger.warning(f"🔒 CSRF inválido na portaria - usuário: {current_user.nome}, IP: {request.remote_addr}")
            flash('Erro de segurança. Tente novamente.', 'danger')
            return redirect(url_for('portaria.dashboard'))
    except Exception as csrf_error:
        logger.error(f"🔒 Erro na validação CSRF: {csrf_error}")
        # Em modo gracioso, permite continuar em produção
        if not current_app.config.get('TESTING'):
            flash('Aviso: Problema de validação detectado, mas operação continuada.', 'warning')
    
    try:
        acao = request.form.get('acao')  # 'chegada', 'entrada', 'saida'
        print(f"[DEBUG] Ação recebida: {acao}")
        
        if acao == 'chegada':
            # Novo registro de controle
            form = ControlePortariaForm()
            print(f"[DEBUG] Formulário criado para chegada")
            
            if form.validate_on_submit():
                print(f"[DEBUG] Validação passou")
                
                if not form.motorista_id.data:
                    print(f"[DEBUG] Nenhum motorista_id disponível")
                    flash('É necessário buscar um motorista antes de registrar a chegada!', 'danger')
                    return redirect(url_for('portaria.dashboard'))
                
                registro = ControlePortaria()
                print(f"[DEBUG] Registro criado")
                form.populate_obj(registro)
                print(f"[DEBUG] Dados populados no registro, motorista_id: {registro.motorista_id}")
                
                # ✅ NOVO: Registra usuário que criou
                registro.registrado_por_id = current_user.id
                registro.atualizado_por_id = current_user.id
                
                registro.registrar_chegada()
                print(f"[DEBUG] Chegada registrada")
                
                db.session.add(registro)
                db.session.commit()
                print(f"[DEBUG] Salvo no banco com sucesso")
                
                flash('Chegada registrada com sucesso!', 'success')
            else:
                print(f"[DEBUG] Validação falhou: {form.errors}")
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'{field}: {error}', 'danger')
        
        elif acao in ['entrada', 'saida']:
            # Atualiza registro existente
            registro_id = request.form.get('registro_id', type=int)
            print(f"[DEBUG] Registro ID: {registro_id}")
            
            if not registro_id:
                flash('Registro não encontrado!', 'danger')
                return redirect(url_for('portaria.dashboard'))
            
            registro = ControlePortaria.query.get_or_404(registro_id)
            print(f"[DEBUG] Registro encontrado: {registro.id}")
            
            if acao == 'entrada':
                print(f"[DEBUG] Verificando se pode registrar entrada...")
                pode_registrar = registro.pode_registrar_entrada
                print(f"[DEBUG] Pode registrar entrada: {pode_registrar} (tipo: {type(pode_registrar)})")
                
                if not pode_registrar:
                    flash('Não é possível registrar entrada sem chegada ou entrada já foi registrada!', 'warning')
                else:
                    print(f"[DEBUG] Registrando entrada...")
                    # ✅ NOVO: Registra usuário que fez a atualização
                    registro.atualizado_por_id = current_user.id
                    registro.registrar_entrada()
                    db.session.commit()
                    flash('Entrada registrada com sucesso!', 'success')
            
            elif acao == 'saida':
                print(f"[DEBUG] Verificando se pode registrar saída...")
                pode_registrar = registro.pode_registrar_saida
                print(f"[DEBUG] Pode registrar saída: {pode_registrar} (tipo: {type(pode_registrar)})")
                
                if not pode_registrar:
                    flash('Não é possível registrar saída sem entrada ou saída já foi registrada!', 'warning')
                else:
                    print(f"[DEBUG] Registrando saída...")
                    # ✅ NOVO: Registra usuário que fez a atualização
                    registro.atualizado_por_id = current_user.id
                    registro.registrar_saida()
                    
                    # Atualiza data_embarque do embarque vinculado automaticamente
                    if registro.embarque_id and registro.embarque:
                        embarque = registro.embarque
                        if not embarque.data_embarque:  # Só atualiza se não estiver preenchida
                            embarque.data_embarque = registro.data_saida
                            print(f"[DEBUG] Data embarque atualizada para {registro.data_saida}")
                            flash(f'Data de embarque do Embarque #{embarque.numero} atualizada para {registro.data_saida.strftime("%d/%m/%Y")}!', 'info')
                            
                            # Sincroniza com sistema de entregas para cada item do embarque
                            if embarque.itens:
                                print(f"[DEBUG] Sincronizando {len(embarque.itens)} itens com sistema de entregas...")
                                
                                for item in embarque.itens:
                                    if item.nota_fiscal:
                                        try:
                                            sincronizar_entrega_por_nf(item.nota_fiscal)
                                            # 🔒 NOVO: Reseta flag de NF no CD
                                            from app.pedidos.models import Pedido
                                            pedido = Pedido.query.filter_by(nf=item.nota_fiscal).first()
                                            if pedido:
                                                pedido.nf_cd = False
                                            print(f"[DEBUG] NF {item.nota_fiscal} sincronizada com entregas")
                                        except Exception as e:
                                            print(f"[DEBUG] Erro ao sincronizar NF {item.nota_fiscal}: {str(e)}")
                                            # Não interrompe o processo por erro de sincronização
                                
                                flash(f'Sistema de entregas sincronizado para {len(embarque.itens)} nota(s) fiscal(is)!', 'success')
                    
                    db.session.commit()
                    flash('Saída registrada com sucesso!', 'success')
        
        else:
            flash('Ação inválida!', 'danger')
            
    except Exception as e:
        print(f"[DEBUG] Erro capturado: {str(e)}")
        print(f"[DEBUG] Tipo do erro: {type(e)}")
        traceback.print_exc()
        
        db.session.rollback()
        flash(f'Erro ao registrar movimento: {str(e)}', 'danger')
    
    return redirect(url_for('portaria.dashboard'))

@portaria_bp.route('/historico')
@login_required
def historico():
    """
    Exibe histórico completo da portaria com filtros expandidos
    """
    form = FiltroHistoricoForm(request.args)
    registros = []
    filtros_aplicados = False
    
    # Processa filtros
    data_inicio = None
    data_fim = None
    embarque_numero = request.args.get('embarque_numero', '').strip()
    tem_embarque = request.args.get('tem_embarque', '').strip()
    tipo_carga = request.args.get('tipo_carga', '').strip()
    tipo_veiculo_id = request.args.get('tipo_veiculo_id', '').strip()
    status = request.args.get('status', '').strip()
    
    # Converte datas
    data_inicio_str = request.args.get('data_inicio')
    if data_inicio_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            filtros_aplicados = True
        except ValueError:
            flash('Data de início inválida!', 'warning')
    
    data_fim_str = request.args.get('data_fim')
    if data_fim_str:
        try:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            filtros_aplicados = True
        except ValueError:
            flash('Data de fim inválida!', 'warning')
    
    # Converte tipo_veiculo_id para int se fornecido
    tipo_veiculo_id_int = None
    if tipo_veiculo_id:
        try:
            tipo_veiculo_id_int = int(tipo_veiculo_id)
            filtros_aplicados = True
        except ValueError:
            pass
    
    # Verifica se há filtros aplicados
    if embarque_numero or tem_embarque or tipo_carga or status:
        filtros_aplicados = True
    
    # Busca registros com todos os filtros
    registros = ControlePortaria.historico(
        data_inicio=data_inicio,
        data_fim=data_fim,
        embarque_numero=embarque_numero if embarque_numero else None,
        tem_embarque=tem_embarque if tem_embarque else None,
        tipo_carga=tipo_carga if tipo_carga else None,
        tipo_veiculo_id=tipo_veiculo_id_int,
        status=status if status else None
    )
    
    return render_template(
        'portaria/historico.html',
        form=form,
        registros=registros,
        data_inicio=data_inicio,
        data_fim=data_fim,
        filtros_aplicados=filtros_aplicados
    )

@portaria_bp.route('/listar_motoristas')
@login_required
def listar_motoristas():
    """
    Lista todos os motoristas cadastrados
    """
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    motoristas = Motorista.query.order_by(Motorista.nome_completo).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return render_template('portaria/listar_motoristas.html', motoristas=motoristas)

@portaria_bp.route('/editar_motorista/<int:id>')
@login_required
def editar_motorista(id):
    """
    Redireciona para o formulário de edição do motorista
    """
    return redirect(url_for('portaria.cadastrar_motorista', id=id))

@portaria_bp.route('/excluir_motorista/<int:id>', methods=['POST'])
@login_required
def excluir_motorista(id):
    """
    Exclui motorista (se não tiver registros de portaria)
    """
    try:
        motorista = Motorista.query.get_or_404(id)
        
        # Verifica se tem registros na portaria
        if motorista.registros_portaria.count() > 0:
            flash('Não é possível excluir motorista com registros na portaria!', 'warning')
        else:
            # Remove foto se existir (S3 ou local)
            if motorista.foto_documento:
                try:
                    from app.utils.file_storage import get_file_storage
                    storage = get_file_storage()
                    
                    # Para arquivos S3 (novos)
                    if not motorista.foto_documento.startswith('uploads/'):
                        # TODO: Implementar exclusão no S3 se necessário
                        pass
                    else:
                        # Para arquivos locais (antigos)
                        foto_path = os.path.join(current_app.root_path, 'static', motorista.foto_documento)
                        if os.path.exists(foto_path):
                            os.remove(foto_path)
                except:
                    pass  # Ignora erro na exclusão do arquivo
            
            db.session.delete(motorista)
            db.session.commit()
            flash('Motorista excluído com sucesso!', 'success')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir motorista: {str(e)}', 'danger')
    
    return redirect(url_for('portaria.listar_motoristas'))

@portaria_bp.route('/api/embarques')
@login_required
def api_embarques():
    """
    API para buscar embarques pendentes de embarque (para select dinâmico)
    """
    termo = request.args.get('q', '')
    
    query = Embarque.query.filter(
        Embarque.status == 'ativo',
        Embarque.data_embarque.is_(None)  # Apenas embarques pendentes
    )
    
    if termo:
        query = query.filter(
            db.or_(
                Embarque.numero.like(f'%{termo}%'),
                Embarque.transportadora.has(razao_social=f'%{termo}%')
            )
        )
    
    embarques = query.order_by(Embarque.numero.desc()).all()
    
    resultados = []
    for e in embarques:
        resultados.append({
            'id': e.id,
            'text': f'Embarque #{e.numero} - {e.transportadora.razao_social if e.transportadora else ""}'
        })
    
    return jsonify({'results': resultados})

@portaria_bp.route('/detalhes_veiculo/<int:registro_id>')
@login_required
def detalhes_veiculo(registro_id):
    """
    Mostra detalhes de um registro específico da portaria
    """
    registro = ControlePortaria.query.get_or_404(registro_id)
    
    return render_template('portaria/detalhes_veiculo.html', registro=registro)

@portaria_bp.route('/api/embarques_disponiveis')
@login_required
def api_embarques_disponiveis():
    """
    API para buscar embarques pendentes de embarque para vincular à portaria
    (apenas embarques ativos sem data_embarque)
    """
    # Busca apenas embarques pendentes de embarque (sem data_embarque)
    embarques = Embarque.query.filter(
        Embarque.status == 'ativo',
        Embarque.data_embarque.is_(None)  # Apenas embarques que ainda não saíram
    ).order_by(Embarque.numero.desc()).all()
    
    resultado = []
    for embarque in embarques:
        # Verifica se já está vinculado a algum veículo
        registro_vinculado = ControlePortaria.query.filter_by(embarque_id=embarque.id).first()
        
        item_embarque = {
            'id': embarque.id,
            'numero': embarque.numero,
            'transportadora': embarque.transportadora.razao_social if embarque.transportadora else None,
            'data_embarque': embarque.data_embarque.strftime('%d/%m/%Y') if embarque.data_embarque else None,
            'veiculo_vinculado': None
        }
        
        # Se já está vinculado, adiciona informações do veículo
        if registro_vinculado:
            motorista_nome = registro_vinculado.motorista_obj.nome_completo if registro_vinculado.motorista_obj else 'N/A'
            item_embarque['veiculo_vinculado'] = {
                'registro_id': registro_vinculado.id,
                'placa': registro_vinculado.placa,
                'motorista': motorista_nome,
                'status': registro_vinculado.status
            }
        
        resultado.append(item_embarque)
    
    return jsonify({'embarques': resultado})

@portaria_bp.route('/adicionar_embarque', methods=['POST'])
@login_required
def adicionar_embarque():
    """
    Vincula um embarque a um registro da portaria
    """
    try:
        registro_id = request.form.get('registro_id', type=int)
        embarque_id = request.form.get('embarque_id', type=int)
        substituir_veiculo = request.form.get('substituir_veiculo', '').lower() == 'true'
        
        if not registro_id or not embarque_id:
            flash('Dados obrigatórios não fornecidos!', 'danger')
            return redirect(request.referrer or url_for('portaria.dashboard'))
        
        # Busca o registro da portaria atual
        registro = ControlePortaria.query.get_or_404(registro_id)
        
        # Verifica se já tem embarque vinculado ao registro atual
        if registro.embarque_id:
            flash('Este veículo já possui um embarque vinculado!', 'warning')
            return redirect(url_for('portaria.detalhes_veiculo', registro_id=registro_id))
        
        # Busca o embarque
        embarque = Embarque.query.get_or_404(embarque_id)
        
        # Verifica se o embarque já está vinculado a outro veículo
        registro_existente = ControlePortaria.query.filter_by(embarque_id=embarque_id).first()
        
        if registro_existente and not substituir_veiculo:
            flash(f'Este embarque já está vinculado ao veículo {registro_existente.placa}! Use a opção de substituir se necessário.', 'warning')
            return redirect(url_for('portaria.detalhes_veiculo', registro_id=registro_id))
        
        # Se for substituição, remove o vínculo anterior
        if registro_existente and substituir_veiculo:
            placa_anterior = registro_existente.placa
            
            # Aplica mesma lógica de limpeza do embarque substituído
            embarque_substituido = Embarque.query.get(embarque_id)
            if embarque_substituido and embarque_substituido.data_embarque:
                embarque_substituido.data_embarque = None
                print(f"[DEBUG] Data embarque removida do Embarque #{embarque_substituido.numero} (substituído)")
                
                # Ajusta sistema de entregas para cada NF do embarque substituído
                if embarque_substituido.itens:
                    for item in embarque_substituido.itens:
                        if item.nota_fiscal:
                            entrega = EntregaMonitorada.query.filter_by(numero_nf=item.nota_fiscal).first()
                            print(f"[DEBUG] Verificando NF {item.nota_fiscal}: entrega encontrada = {entrega is not None}")
                            
                            if entrega:
                                print(f"[DEBUG] NF {item.nota_fiscal}: data_entrega_prevista = {entrega.data_entrega_prevista}")
                                print(f"[DEBUG] NF {item.nota_fiscal}: data_embarque = {entrega.data_embarque}")
                                print(f"[DEBUG] NF {item.nota_fiscal}: agendamentos = {len(entrega.agendamentos)}")
                                
                                # SEMPRE limpa a data_embarque quando embarque é desvinculado
                                if entrega.data_embarque:
                                    entrega.data_embarque = None
                                    print(f"[DEBUG] NF {item.nota_fiscal}: data_embarque removida")
                                
                                if entrega.data_entrega_prevista:
                                    # Verifica se a data_entrega_prevista veio de agendamento
                                    tem_agendamento_ativo = any(
                                        ag.data_agendada and ag.data_agendada == entrega.data_entrega_prevista 
                                        for ag in entrega.agendamentos
                                    )
                                    
                                    print(f"[DEBUG] NF {item.nota_fiscal}: tem_agendamento_ativo = {tem_agendamento_ativo}")
                                    
                                    if tem_agendamento_ativo:
                                        # Mantém data_entrega_prevista pois veio de agendamento
                                        print(f"[DEBUG] NF {item.nota_fiscal}: Mantida data_entrega_prevista (veio de agendamento)")
                                    else:
                                        # Remove data_entrega_prevista pois veio de embarque+lead_time
                                        entrega.data_entrega_prevista = None
                                        print(f"[DEBUG] NF {item.nota_fiscal}: Removida data_entrega_prevista (veio de embarque+lead_time)")
                                else:
                                    print(f"[DEBUG] NF {item.nota_fiscal}: Sem data_entrega_prevista para processar")
                    
                    flash(f'Embarque #{embarque_substituido.numero} substituído: Sistema de entregas ajustado para {len(embarque_substituido.itens)} nota(s) fiscal(is)!', 'info')
            
            registro_existente.embarque_id = None
            db.session.add(registro_existente)
            flash(f'Vínculo removido do veículo {placa_anterior}!', 'info')
        
        # Vincula o embarque ao novo registro
        registro.embarque_id = embarque_id
        db.session.commit()
        
        acao_msg = 'substituído' if substituir_veiculo else 'vinculado'
        flash(f'Embarque #{embarque.numero} {acao_msg} com sucesso ao veículo {registro.placa}!', 'success')
        
        # Se o veículo já saiu, atualiza a data_embarque imediatamente
        if registro.data_saida and not embarque.data_embarque:
            embarque.data_embarque = registro.data_saida
            print(f"[DEBUG] Data embarque atualizada para {registro.data_saida} (vinculação após saída)")
            
            # 🔧 CORREÇÃO: Sincroniza com sistema de entregas para cada item do embarque
            if embarque.itens:
                print(f"[DEBUG] Sincronizando {len(embarque.itens)} itens com sistema de entregas...")
                
                for item in embarque.itens:
                    if item.nota_fiscal:
                        try:
                            sincronizar_entrega_por_nf(item.nota_fiscal)
                            print(f"[DEBUG] NF {item.nota_fiscal} sincronizada com entregas")
                        except Exception as e:
                            print(f"[DEBUG] Erro ao sincronizar NF {item.nota_fiscal}: {str(e)}")
                            # Não interrompe o processo por erro de sincronização
                
                flash(f'Sistema de entregas sincronizado para {len(embarque.itens)} nota(s) fiscal(is)!', 'success')
            
            db.session.commit()
            flash(f'Data de embarque atualizada para {registro.data_saida.strftime("%d/%m/%Y")}!', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao vincular embarque: {str(e)}', 'danger')
    
    return redirect(url_for('portaria.detalhes_veiculo', registro_id=registro_id))

@portaria_bp.route('/excluir_embarque', methods=['POST'])
@login_required
def excluir_embarque():
    """
    Remove vínculo entre embarque e veículo da portaria
    """
    try:
        registro_id = request.form.get('registro_id', type=int)
        
        if not registro_id:
            flash('Registro não encontrado!', 'danger')
            return redirect(url_for('portaria.dashboard'))
        
        # Busca o registro da portaria
        registro = ControlePortaria.query.get_or_404(registro_id)
        
        if not registro.embarque_id:
            flash('Este veículo não possui embarque vinculado!', 'warning')
            return redirect(url_for('portaria.detalhes_veiculo', registro_id=registro_id))
        
        # Busca o embarque para processar antes de remover o vínculo
        embarque = registro.embarque
        embarque_numero = embarque.numero if embarque else 'N/A'
        
        # 1. Apaga a data_embarque do embarque desvinculado
        if embarque and embarque.data_embarque:
            embarque.data_embarque = None
            print(f"[DEBUG] Data embarque removida do Embarque #{embarque_numero}")
            
            # 2. Ajusta sistema de entregas para cada NF do embarque
            if embarque.itens:
                for item in embarque.itens:
                    if item.nota_fiscal:
                        entrega = EntregaMonitorada.query.filter_by(numero_nf=item.nota_fiscal).first()
                        print(f"[DEBUG] Verificando NF {item.nota_fiscal}: entrega encontrada = {entrega is not None}")
                        
                        if entrega:
                            print(f"[DEBUG] NF {item.nota_fiscal}: data_entrega_prevista = {entrega.data_entrega_prevista}")
                            print(f"[DEBUG] NF {item.nota_fiscal}: data_embarque = {entrega.data_embarque}")
                            print(f"[DEBUG] NF {item.nota_fiscal}: agendamentos = {len(entrega.agendamentos)}")
                            
                            # SEMPRE limpa a data_embarque quando embarque é desvinculado
                            if entrega.data_embarque:
                                entrega.data_embarque = None
                                print(f"[DEBUG] NF {item.nota_fiscal}: data_embarque removida")
                            
                            if entrega.data_entrega_prevista:
                                # Verifica se a data_entrega_prevista veio de agendamento
                                tem_agendamento_ativo = any(
                                    ag.data_agendada and ag.data_agendada == entrega.data_entrega_prevista 
                                    for ag in entrega.agendamentos
                                )
                                
                                print(f"[DEBUG] NF {item.nota_fiscal}: tem_agendamento_ativo = {tem_agendamento_ativo}")
                                
                                if tem_agendamento_ativo:
                                    # Mantém data_entrega_prevista pois veio de agendamento
                                    print(f"[DEBUG] NF {item.nota_fiscal}: Mantida data_entrega_prevista (veio de agendamento)")
                                else:
                                    # Remove data_entrega_prevista pois veio de embarque+lead_time
                                    entrega.data_entrega_prevista = None
                                    print(f"[DEBUG] NF {item.nota_fiscal}: Removida data_entrega_prevista (veio de embarque+lead_time)")
                            else:
                                print(f"[DEBUG] NF {item.nota_fiscal}: Sem data_entrega_prevista para processar")
                
                flash(f'Sistema de entregas ajustado para {len(embarque.itens)} nota(s) fiscal(is)!', 'info')
        
        # 3. Remove o vínculo
        registro.embarque_id = None
        db.session.commit()
        
        flash(f'Vínculo com Embarque #{embarque_numero} removido com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover vínculo: {str(e)}', 'danger')
    
    return redirect(url_for('portaria.detalhes_veiculo', registro_id=registro_id))
