"""
API para gerenciar cadastro de clientes não-Odoo
"""
from flask import Blueprint, jsonify, request
from app import db
from app.carteira.models import CadastroCliente
from app.faturamento.models import RelatorioFaturamentoImportado
from app.utils.ufs import UF_LIST
from app.localidades.models import Cidade
from sqlalchemy import distinct
import logging

logger = logging.getLogger(__name__)

cadastro_cliente_api = Blueprint('cadastro_cliente_api', __name__)

@cadastro_cliente_api.route('/api/cadastro-cliente', methods=['GET'])
def listar_clientes():
    """Lista todos os clientes não-Odoo cadastrados"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        
        query = CadastroCliente.query.filter_by(cliente_ativo=True)
        
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                db.or_(
                    CadastroCliente.cnpj_cpf.ilike(search_pattern),
                    CadastroCliente.raz_social.ilike(search_pattern),
                    CadastroCliente.raz_social_red.ilike(search_pattern),
                    CadastroCliente.municipio.ilike(search_pattern)
                )
            )
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'clientes': [cliente.to_dict() for cliente in paginated.items],
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar clientes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@cadastro_cliente_api.route('/api/cadastro-cliente/<int:id>', methods=['GET'])
def obter_cliente(id):
    """Obtém um cliente específico por ID"""
    try:
        cliente = CadastroCliente.query.get_or_404(id)
        return jsonify({
            'success': True,
            'cliente': cliente.to_dict()
        })
    except Exception as e:
        logger.error(f"Erro ao obter cliente {id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@cadastro_cliente_api.route('/api/cadastro-cliente/cnpj/<cnpj>', methods=['GET'])
def buscar_por_cnpj(cnpj):
    """Busca cliente por CNPJ/CPF"""
    try:
        # Limpar CNPJ
        cnpj_limpo = CadastroCliente.limpar_cnpj(cnpj)
        
        cliente = CadastroCliente.query.filter_by(
            cnpj_cpf=cnpj_limpo,
            cliente_ativo=True
        ).first()
        
        if cliente:
            return jsonify({
                'success': True,
                'found': True,
                'cliente': cliente.to_dict()
            })
        else:
            return jsonify({
                'success': True,
                'found': False,
                'message': 'Cliente não encontrado'
            })
            
    except Exception as e:
        logger.error(f"Erro ao buscar cliente por CNPJ: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@cadastro_cliente_api.route('/api/cadastro-cliente', methods=['POST'])
def criar_cliente():
    """Cria um novo cliente não-Odoo"""
    try:
        data = request.get_json()
        
        # Validações básicas
        if not data.get('cnpj_cpf'):
            return jsonify({'success': False, 'error': 'CNPJ/CPF é obrigatório'}), 400
            
        if not data.get('raz_social'):
            return jsonify({'success': False, 'error': 'Razão social é obrigatória'}), 400
            
        if not data.get('municipio'):
            return jsonify({'success': False, 'error': 'Município é obrigatório'}), 400
            
        if not data.get('estado'):
            return jsonify({'success': False, 'error': 'Estado é obrigatório'}), 400
        
        # Limpar CNPJ
        cnpj_limpo = CadastroCliente.limpar_cnpj(data['cnpj_cpf'])
        
        # Verificar se já existe
        cliente_existente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj_limpo).first()
        if cliente_existente:
            return jsonify({
                'success': False, 
                'error': 'Cliente já cadastrado com este CNPJ/CPF'
            }), 400
        
        # Criar novo cliente
        novo_cliente = CadastroCliente(
            cnpj_cpf=cnpj_limpo,
            raz_social=data['raz_social'],
            raz_social_red=data.get('raz_social_red'),
            municipio=data['municipio'],
            estado=data['estado'],
            vendedor=data.get('vendedor'),
            equipe_vendas=data.get('equipe_vendas'),
            cnpj_endereco_ent=data.get('cnpj_endereco_ent'),
            empresa_endereco_ent=data.get('empresa_endereco_ent'),
            cep_endereco_ent=data.get('cep_endereco_ent'),
            nome_cidade=data.get('nome_cidade'),
            cod_uf=data.get('cod_uf'),
            bairro_endereco_ent=data.get('bairro_endereco_ent'),
            rua_endereco_ent=data.get('rua_endereco_ent'),
            endereco_ent=data.get('endereco_ent'),
            telefone_endereco_ent=data.get('telefone_endereco_ent'),
            endereco_mesmo_cliente=data.get('endereco_mesmo_cliente', True),
            criado_por=data.get('usuario', 'Sistema')
        )
        
        # Se marcou para aplicar endereço do cliente
        if data.get('aplicar_endereco_cliente'):
            novo_cliente.aplicar_endereco_cliente()
        
        db.session.add(novo_cliente)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cliente criado com sucesso',
            'cliente': novo_cliente.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar cliente: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@cadastro_cliente_api.route('/api/cadastro-cliente/<int:id>', methods=['PUT'])
def atualizar_cliente(id):
    """Atualiza um cliente existente"""
    try:
        cliente = CadastroCliente.query.get_or_404(id)
        data = request.get_json()
        
        # Atualizar campos
        if 'raz_social' in data:
            cliente.raz_social = data['raz_social']
        if 'raz_social_red' in data:
            cliente.raz_social_red = data['raz_social_red']
        if 'municipio' in data:
            cliente.municipio = data['municipio']
        if 'estado' in data:
            cliente.estado = data['estado']
        if 'vendedor' in data:
            cliente.vendedor = data['vendedor']
        if 'equipe_vendas' in data:
            cliente.equipe_vendas = data['equipe_vendas']
            
        # Atualizar endereço de entrega
        if 'cnpj_endereco_ent' in data:
            cliente.cnpj_endereco_ent = data['cnpj_endereco_ent']
        if 'empresa_endereco_ent' in data:
            cliente.empresa_endereco_ent = data['empresa_endereco_ent']
        if 'cep_endereco_ent' in data:
            cliente.cep_endereco_ent = data['cep_endereco_ent']
        if 'nome_cidade' in data:
            cliente.nome_cidade = data['nome_cidade']
        if 'cod_uf' in data:
            cliente.cod_uf = data['cod_uf']
        if 'bairro_endereco_ent' in data:
            cliente.bairro_endereco_ent = data['bairro_endereco_ent']
        if 'rua_endereco_ent' in data:
            cliente.rua_endereco_ent = data['rua_endereco_ent']
        if 'endereco_ent' in data:
            cliente.endereco_ent = data['endereco_ent']
        if 'telefone_endereco_ent' in data:
            cliente.telefone_endereco_ent = data['telefone_endereco_ent']
        if 'endereco_mesmo_cliente' in data:
            cliente.endereco_mesmo_cliente = data['endereco_mesmo_cliente']
            
        # Se marcou para aplicar endereço do cliente
        if data.get('aplicar_endereco_cliente'):
            cliente.aplicar_endereco_cliente()
            
        cliente.atualizado_por = data.get('usuario', 'Sistema')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cliente atualizado com sucesso',
            'cliente': cliente.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar cliente {id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@cadastro_cliente_api.route('/api/cadastro-cliente/<int:id>', methods=['DELETE'])
def inativar_cliente(id):
    """Inativa um cliente (soft delete)"""
    try:
        cliente = CadastroCliente.query.get_or_404(id)
        cliente.cliente_ativo = False
        cliente.atualizado_por = request.args.get('usuario', 'Sistema')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cliente inativado com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao inativar cliente {id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@cadastro_cliente_api.route('/api/cadastro-cliente/opcoes', methods=['GET'])
def obter_opcoes():
    """Obtém listas de opções para os campos select"""
    try:
        # Lista de UFs
        ufs = [{'value': uf[0], 'label': uf[1]} for uf in UF_LIST]
        
        # Lista de vendedores (distinct)
        vendedores = db.session.query(distinct(RelatorioFaturamentoImportado.vendedor))\
            .filter(RelatorioFaturamentoImportado.vendedor.isnot(None))\
            .order_by(RelatorioFaturamentoImportado.vendedor)\
            .all()
        vendedores = [{'value': v[0], 'label': v[0]} for v in vendedores if v[0]]
        
        # Lista de equipes de vendas (distinct)
        equipes = db.session.query(distinct(RelatorioFaturamentoImportado.equipe_vendas))\
            .filter(RelatorioFaturamentoImportado.equipe_vendas.isnot(None))\
            .order_by(RelatorioFaturamentoImportado.equipe_vendas)\
            .all()
        equipes = [{'value': e[0], 'label': e[0]} for e in equipes if e[0]]
        
        return jsonify({
            'success': True,
            'opcoes': {
                'ufs': ufs,
                'vendedores': vendedores,
                'equipes_vendas': equipes
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter opções: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@cadastro_cliente_api.route('/api/cadastro-cliente/cidades/<uf>', methods=['GET'])
def obter_cidades_por_uf(uf):
    """Obtém lista de cidades por UF"""
    try:
        cidades = Cidade.query.filter_by(uf=uf.upper())\
            .order_by(Cidade.nome)\
            .all()
            
        cidades_list = [{
            'value': cidade.nome,
            'label': cidade.nome,
            'id': cidade.id
        } for cidade in cidades]
        
        return jsonify({
            'success': True,
            'cidades': cidades_list
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter cidades para UF {uf}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500