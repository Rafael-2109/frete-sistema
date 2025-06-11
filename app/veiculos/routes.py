from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.veiculos.models import Veiculo
from app import db
from flask_login import login_required

veiculos_bp = Blueprint('veiculos', __name__, url_prefix='/veiculos')

@veiculos_bp.route('/consulta')
@veiculos_bp.route('/admin')
@login_required
def admin_veiculos():
    """Administração completa de veículos (CRUD) - unificado"""
    veiculos = Veiculo.query.order_by(Veiculo.peso_maximo.asc()).all()
    return render_template('veiculos/admin_veiculos.html', veiculos=veiculos)

@veiculos_bp.route('/criar', methods=['POST'])
@login_required
def criar_veiculo():
    """Criar novo veículo"""
    try:
        nome = request.form.get('nome', '').strip().upper()
        peso_maximo = float(request.form.get('peso_maximo', 0))
        
        # Validações
        if not nome:
            flash('Nome do veículo é obrigatório!', 'danger')
            return redirect(url_for('veiculos.admin_veiculos'))
        
        if peso_maximo <= 0:
            flash('Peso máximo deve ser maior que zero!', 'danger')
            return redirect(url_for('veiculos.admin_veiculos'))
        
        # Verificar se já existe
        if Veiculo.query.filter_by(nome=nome).first():
            flash(f'Veículo "{nome}" já existe!', 'warning')
            return redirect(url_for('veiculos.admin_veiculos'))
        
        # Criar veículo
        veiculo = Veiculo(
            nome=nome,
            peso_maximo=peso_maximo
        )
        
        db.session.add(veiculo)
        db.session.commit()
        
        flash(f'Veículo "{nome}" criado com sucesso!', 'success')
        
    except ValueError:
        flash('Peso máximo deve ser um número válido!', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar veículo: {str(e)}', 'danger')
    
    return redirect(url_for('veiculos.admin_veiculos'))

@veiculos_bp.route('/editar', methods=['POST'])
@login_required
def editar_veiculo():
    """Editar veículo existente"""
    try:
        veiculo_id = int(request.form.get('veiculo_id'))
        nome = request.form.get('nome', '').strip().upper()
        peso_maximo = float(request.form.get('peso_maximo', 0))
        
        # Buscar veículo
        veiculo = Veiculo.query.get_or_404(veiculo_id)
        
        # Validações
        if not nome:
            flash('Nome do veículo é obrigatório!', 'danger')
            return redirect(url_for('veiculos.admin_veiculos'))
        
        if peso_maximo <= 0:
            flash('Peso máximo deve ser maior que zero!', 'danger')
            return redirect(url_for('veiculos.admin_veiculos'))
        
        # Verificar duplicata (exceto ele mesmo)
        duplicata = Veiculo.query.filter(
            Veiculo.nome == nome,
            Veiculo.id != veiculo_id
        ).first()
        
        if duplicata:
            flash(f'Já existe outro veículo com o nome "{nome}"!', 'warning')
            return redirect(url_for('veiculos.admin_veiculos'))
        
        # Atualizar dados
        nome_antigo = veiculo.nome
        peso_antigo = veiculo.peso_maximo
        
        veiculo.nome = nome
        veiculo.peso_maximo = peso_maximo
        
        db.session.commit()
        
        # Mensagem detalhada das mudanças
        mudancas = []
        if nome != nome_antigo:
            mudancas.append(f'nome: {nome_antigo} → {nome}')
        if peso_maximo != peso_antigo:
            mudancas.append(f'peso: {peso_antigo:,.0f}kg → {peso_maximo:,.0f}kg')
        
        if mudancas:
            flash(f'Veículo atualizado! Mudanças: {", ".join(mudancas)}', 'success')
        else:
            flash('Nenhuma alteração foi feita.', 'info')
        
    except ValueError:
        flash('Dados inválidos! Verifique os campos numéricos.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao editar veículo: {str(e)}', 'danger')
    
    return redirect(url_for('veiculos.admin_veiculos'))

@veiculos_bp.route('/excluir', methods=['POST'])
@login_required
def excluir_veiculo():
    """Excluir veículo"""
    try:
        veiculo_id = int(request.form.get('veiculo_id'))
        veiculo = Veiculo.query.get_or_404(veiculo_id)
        
        nome_veiculo = veiculo.nome
        
        # Verificar se tem registros vinculados
        from app.portaria.models import ControlePortaria
        registros_vinculados = ControlePortaria.query.filter_by(tipo_veiculo_id=veiculo_id).count()
        
        if registros_vinculados > 0:
            flash(f'Não é possível excluir o veículo "{nome_veiculo}" pois há {registros_vinculados} registro(s) vinculado(s) na portaria.', 'warning')
            return redirect(url_for('veiculos.admin_veiculos'))
        
        # Excluir
        db.session.delete(veiculo)
        db.session.commit()
        
        flash(f'Veículo "{nome_veiculo}" excluído com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir veículo: {str(e)}', 'danger')
    
    return redirect(url_for('veiculos.admin_veiculos'))

@veiculos_bp.route('/api/lista')
@login_required
def api_lista_veiculos():
    """API para listar veículos (usado em outros módulos)"""
    veiculos = Veiculo.query.order_by(Veiculo.nome).all()
    return jsonify([
        {
            'id': v.id,
            'nome': v.nome,
            'peso_maximo': v.peso_maximo
        } for v in veiculos
    ])

@veiculos_bp.route('/inicializar')
@login_required
def inicializar_veiculos():
    """Inicializar veículos padrão do sistema"""
    try:
        # Verificar se já existem veículos
        if Veiculo.query.count() > 0:
            flash('Já existem veículos cadastrados no sistema!', 'info')
            return redirect(url_for('veiculos.admin_veiculos'))
        
        # Veículos padrão do sistema
        veiculos_padrao = [
            {'nome': 'FIORINO', 'peso_maximo': 600},
            {'nome': 'VAN/HR', 'peso_maximo': 1700},
            {'nome': 'MASTER', 'peso_maximo': 2000}, 
            {'nome': 'IVECO', 'peso_maximo': 2500},
            {'nome': '3/4', 'peso_maximo': 4500},
            {'nome': 'TOCO', 'peso_maximo': 6500},
            {'nome': 'TRUCK', 'peso_maximo': 14500},
            {'nome': 'CARRETA', 'peso_maximo': 27000},
        ]
        
        veiculos_criados = []
        for veiculo_data in veiculos_padrao:
            veiculo = Veiculo(
                nome=veiculo_data['nome'],
                peso_maximo=veiculo_data['peso_maximo']
            )
            db.session.add(veiculo)
            veiculos_criados.append(veiculo_data['nome'])
        
        db.session.commit()
        
        flash(f'✅ {len(veiculos_criados)} veículos inicializados: {", ".join(veiculos_criados)}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao inicializar veículos: {str(e)}', 'danger')
    
    return redirect(url_for('veiculos.admin_veiculos'))
