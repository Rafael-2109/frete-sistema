"""
Rotas API para integração com Odoo
Sincronização de carteira de pedidos e faturamento
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_

from app import db
from app.carteira.models import CarteiraPrincipal, CarteiraCopia
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.api.odoo.validators import validate_carteira_data, validate_faturamento_data
from app.api.odoo.auth import require_api_key, require_jwt_token
from app.api.odoo.utils import process_bulk_operation, create_response

# Configurar logging
logger = logging.getLogger(__name__)

# Definir o blueprint
odoo_bp = Blueprint('odoo', __name__, url_prefix='/api/v1/odoo')

# ============================================================================
# MIDDLEWARE DE AUTENTICAÇÃO
# ============================================================================

@odoo_bp.before_request
def verify_authentication():
    """Verifica autenticação antes de cada requisição"""
    # Verificar se tem API key
    if not require_api_key():
        return create_response(
            success=False,
            message="API Key inválida ou ausente",
            status_code=401
        )
    
    # Verificar JWT token
    if not require_jwt_token():
        return create_response(
            success=False,
            message="Token JWT inválido ou ausente",
            status_code=401
        )

# ============================================================================
# ROTA: CARTEIRA DE PEDIDOS
# ============================================================================

@odoo_bp.route('/carteira/bulk-update', methods=['POST'])
def bulk_update_carteira():
    """
    Atualiza/cria registros na carteira de pedidos em lote
    
    Endpoint: POST /api/v1/odoo/carteira/bulk-update
    """
    try:
        # Validar dados de entrada
        data = request.get_json()
        if not data or 'items' not in data:
            return create_response(
                success=False,
                message="Dados inválidos. Campo 'items' é obrigatório.",
                status_code=400
            )
        
        items = data['items']
        if not isinstance(items, list) or len(items) == 0:
            return create_response(
                success=False,
                message="Campo 'items' deve ser uma lista não vazia.",
                status_code=400
            )
        
        logger.info(f"Iniciando bulk update carteira com {len(items)} itens")
        
        # Validar cada item
        validation_errors = []
        validated_items = []
        
        for index, item in enumerate(items):
            try:
                validated_item = validate_carteira_data(item)
                validated_items.append(validated_item)
            except ValueError as e:
                validation_errors.append(f"Item {index + 1}: {str(e)}")
        
        if validation_errors:
            return create_response(
                success=False,
                message="Erros de validação encontrados",
                errors=validation_errors,
                status_code=400
            )
        
        # Processar em lote
        result = process_bulk_operation(
            validated_items,
            _process_carteira_item,
            "carteira"
        )
        
        logger.info(f"Bulk update carteira concluído: {result}")
        
        return create_response(
            success=True,
            message="Carteira atualizada com sucesso",
            **result
        )
        
    except Exception as e:
        logger.error(f"Erro no bulk update carteira: {str(e)}")
        return create_response(
            success=False,
            message=f"Erro interno: {str(e)}",
            status_code=500
        )

def _process_carteira_item(item):
    """Processa um item individual da carteira"""
    try:
        # Buscar item existente
        existing_item = CarteiraPrincipal.query.filter_by(
            num_pedido=item['num_pedido'],
            cod_produto=item['cod_produto']
        ).first()
        
        if existing_item:
            # Atualizar item existente
            _update_carteira_item(existing_item, item)
            action = 'updated'
        else:
            # Criar novo item
            _create_carteira_item(item)
            action = 'created'
        
        db.session.commit()
        return action
        
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Erro de integridade ao processar item carteira: {str(e)}")
        raise ValueError(f"Erro de integridade: {str(e)}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar item carteira: {str(e)}")
        raise ValueError(f"Erro no processamento: {str(e)}")

def _update_carteira_item(item, data):
    """Atualiza um item existente da carteira"""
    # Atualizar dados mestres preservando operacionais
    item.nome_produto = data['nome_produto']
    item.qtd_produto_pedido = data['qtd_produto_pedido']
    item.qtd_saldo_produto_pedido = data['qtd_saldo_produto_pedido']
    item.preco_produto_pedido = data['preco_produto_pedido']
    item.cnpj_cpf = data['cnpj_cpf']
    
    # Dados opcionais do pedido
    if 'pedido_cliente' in data:
        item.pedido_cliente = data['pedido_cliente']
    if 'data_pedido' in data:
        item.data_pedido = datetime.strptime(data['data_pedido'], '%Y-%m-%d').date()
    if 'status_pedido' in data:
        item.status_pedido = data['status_pedido']
    
    # Dados opcionais do cliente
    if 'raz_social' in data:
        item.raz_social = data['raz_social']
    if 'raz_social_red' in data:
        item.raz_social_red = data['raz_social_red']
    if 'municipio' in data:
        item.municipio = data['municipio']
    if 'estado' in data:
        item.estado = data['estado']
    if 'vendedor' in data:
        item.vendedor = data['vendedor']
    if 'equipe_vendas' in data:
        item.equipe_vendas = data['equipe_vendas']
    
    # Dados opcionais do produto
    if 'unid_medida_produto' in data:
        item.unid_medida_produto = data['unid_medida_produto']
    if 'embalagem_produto' in data:
        item.embalagem_produto = data['embalagem_produto']
    if 'materia_prima_produto' in data:
        item.materia_prima_produto = data['materia_prima_produto']
    if 'categoria_produto' in data:
        item.categoria_produto = data['categoria_produto']
    
    # Dados opcionais comerciais
    if 'qtd_cancelada_produto_pedido' in data:
        item.qtd_cancelada_produto_pedido = data['qtd_cancelada_produto_pedido']
    if 'cond_pgto_pedido' in data:
        item.cond_pgto_pedido = data['cond_pgto_pedido']
    if 'forma_pgto_pedido' in data:
        item.forma_pgto_pedido = data['forma_pgto_pedido']
    if 'incoterm' in data:
        item.incoterm = data['incoterm']
    if 'metodo_entrega_pedido' in data:
        item.metodo_entrega_pedido = data['metodo_entrega_pedido']
    if 'data_entrega_pedido' in data:
        item.data_entrega_pedido = datetime.strptime(data['data_entrega_pedido'], '%Y-%m-%d').date()
    if 'cliente_nec_agendamento' in data:
        item.cliente_nec_agendamento = data['cliente_nec_agendamento']
    if 'observ_ped_1' in data:
        item.observ_ped_1 = data['observ_ped_1']
    
    # Dados opcionais de endereço
    if 'cnpj_endereco_ent' in data:
        item.cnpj_endereco_ent = data['cnpj_endereco_ent']
    if 'empresa_endereco_ent' in data:
        item.empresa_endereco_ent = data['empresa_endereco_ent']
    if 'cep_endereco_ent' in data:
        item.cep_endereco_ent = data['cep_endereco_ent']
    if 'nome_cidade' in data:
        item.nome_cidade = data['nome_cidade']
    if 'cod_uf' in data:
        item.cod_uf = data['cod_uf']
    if 'bairro_endereco_ent' in data:
        item.bairro_endereco_ent = data['bairro_endereco_ent']
    if 'rua_endereco_ent' in data:
        item.rua_endereco_ent = data['rua_endereco_ent']
    if 'endereco_ent' in data:
        item.endereco_ent = data['endereco_ent']
    if 'telefone_endereco_ent' in data:
        item.telefone_endereco_ent = data['telefone_endereco_ent']
    
    # Dados opcionais de estoque
    if 'estoque' in data:
        item.estoque = data['estoque']
    if 'menor_estoque_produto_d7' in data:
        item.menor_estoque_produto_d7 = data['menor_estoque_produto_d7']
    if 'saldo_estoque_pedido' in data:
        item.saldo_estoque_pedido = data['saldo_estoque_pedido']
    if 'saldo_estoque_pedido_forcado' in data:
        item.saldo_estoque_pedido_forcado = data['saldo_estoque_pedido_forcado']
    if 'qtd_total_produto_carteira' in data:
        item.qtd_total_produto_carteira = data['qtd_total_produto_carteira']
    
    # Projeção de estoque D0-D28
    for i in range(29):  # D0 a D28
        field_name = f'estoque_d{i}'
        if field_name in data:
            setattr(item, field_name, data[field_name])
    
    # Auditoria
    item.updated_by = current_user.nome if current_user.is_authenticated else 'API_ODOO'

def _create_carteira_item(data):
    """Cria um novo item da carteira"""
    item = CarteiraPrincipal()
    
    # Campos obrigatórios
    item.num_pedido = data['num_pedido']
    item.cod_produto = data['cod_produto']
    item.nome_produto = data['nome_produto']
    item.qtd_produto_pedido = data['qtd_produto_pedido']
    item.qtd_saldo_produto_pedido = data['qtd_saldo_produto_pedido']
    item.cnpj_cpf = data['cnpj_cpf']
    item.preco_produto_pedido = data['preco_produto_pedido']
    
    # Auditoria
    item.created_by = current_user.nome if current_user.is_authenticated else 'API_ODOO'
    item.updated_by = current_user.nome if current_user.is_authenticated else 'API_ODOO'
    
    # Aplicar campos opcionais
    _update_carteira_item(item, data)
    
    # Adicionar ao banco
    db.session.add(item)
    
    # Também criar/atualizar na carteira cópia
    _sync_carteira_copia(item)

def _sync_carteira_copia(item):
    """Sincroniza com a carteira cópia"""
    try:
        # Buscar item existente na cópia
        copia_item = CarteiraCopia.query.filter_by(
            num_pedido=item.num_pedido,
            cod_produto=item.cod_produto
        ).first()
        
        if copia_item:
            # Atualizar sincronizando campos relevantes
            copia_item.qtd_produto_pedido = item.qtd_produto_pedido
            copia_item.qtd_saldo_produto_pedido = item.qtd_saldo_produto_pedido
            copia_item.preco_produto_pedido = item.preco_produto_pedido
            copia_item.cnpj_cpf = item.cnpj_cpf
            copia_item.raz_social = item.raz_social
            copia_item.raz_social_red = item.raz_social_red
            copia_item.nome_produto = item.nome_produto
            copia_item.updated_by = item.updated_by
        else:
            # Criar novo item na cópia
            copia_item = CarteiraCopia()
            copia_item.num_pedido = item.num_pedido
            copia_item.cod_produto = item.cod_produto
            copia_item.nome_produto = item.nome_produto
            copia_item.qtd_produto_pedido = item.qtd_produto_pedido
            copia_item.qtd_saldo_produto_pedido = item.qtd_saldo_produto_pedido
            copia_item.preco_produto_pedido = item.preco_produto_pedido
            copia_item.cnpj_cpf = item.cnpj_cpf
            copia_item.raz_social = item.raz_social
            copia_item.raz_social_red = item.raz_social_red
            copia_item.qtd_saldo_produto_calculado = item.qtd_saldo_produto_pedido  # Inicial igual ao saldo
            copia_item.created_by = item.created_by
            copia_item.updated_by = item.updated_by
            db.session.add(copia_item)
            
    except Exception as e:
        logger.warning(f"Erro ao sincronizar carteira cópia: {str(e)}")
        # Não interromper o processo principal por erro na cópia

# ============================================================================
# ROTA: FATURAMENTO
# ============================================================================

@odoo_bp.route('/faturamento/bulk-update', methods=['POST'])
def bulk_update_faturamento():
    """
    Atualiza/cria registros de faturamento em lote
    
    Endpoint: POST /api/v1/odoo/faturamento/bulk-update
    """
    try:
        # Validar dados de entrada
        data = request.get_json()
        if not data or 'items' not in data:
            return create_response(
                success=False,
                message="Dados inválidos. Campos 'tipo' e 'items' são obrigatórios.",
                status_code=400
            )
        
        tipo = data.get('tipo', 'consolidado')  # Default: consolidado
        items = data['items']
        
        if not isinstance(items, list) or len(items) == 0:
            return create_response(
                success=False,
                message="Campo 'items' deve ser uma lista não vazia.",
                status_code=400
            )
        
        if tipo not in ['consolidado', 'produto']:
            return create_response(
                success=False,
                message="Campo 'tipo' deve ser 'consolidado' ou 'produto'.",
                status_code=400
            )
        
        logger.info(f"Iniciando bulk update faturamento ({tipo}) com {len(items)} itens")
        
        # Validar cada item
        validation_errors = []
        validated_items = []
        
        for index, item in enumerate(items):
            try:
                validated_item = validate_faturamento_data(item, tipo)
                validated_items.append(validated_item)
            except ValueError as e:
                validation_errors.append(f"Item {index + 1}: {str(e)}")
        
        if validation_errors:
            return create_response(
                success=False,
                message="Erros de validação encontrados",
                errors=validation_errors,
                status_code=400
            )
        
        # Processar em lote
        if tipo == 'consolidado':
            result = process_bulk_operation(
                validated_items,
                _process_faturamento_consolidado_item,
                "faturamento_consolidado"
            )
        else:
            result = process_bulk_operation(
                validated_items,
                _process_faturamento_produto_item,
                "faturamento_produto"
            )
        
        logger.info(f"Bulk update faturamento concluído: {result}")
        
        return create_response(
            success=True,
            message="Faturamento atualizado com sucesso",
            **result
        )
        
    except Exception as e:
        logger.error(f"Erro no bulk update faturamento: {str(e)}")
        return create_response(
            success=False,
            message=f"Erro interno: {str(e)}",
            status_code=500
        )

def _process_faturamento_consolidado_item(item):
    """Processa um item individual do faturamento consolidado"""
    try:
        # Buscar item existente
        existing_item = RelatorioFaturamentoImportado.query.filter_by(
            numero_nf=item['numero_nf']
        ).first()
        
        if existing_item:
            # Atualizar item existente
            _update_faturamento_consolidado_item(existing_item, item)
            action = 'updated'
        else:
            # Criar novo item
            _create_faturamento_consolidado_item(item)
            action = 'created'
        
        db.session.commit()
        return action
        
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Erro de integridade ao processar faturamento consolidado: {str(e)}")
        raise ValueError(f"Erro de integridade: {str(e)}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar faturamento consolidado: {str(e)}")
        raise ValueError(f"Erro no processamento: {str(e)}")

def _update_faturamento_consolidado_item(item, data):
    """Atualiza um item existente do faturamento consolidado"""
    item.data_fatura = datetime.strptime(data['data_fatura'], '%Y-%m-%d').date()
    item.cnpj_cliente = data['cnpj_cliente']
    item.nome_cliente = data['nome_cliente']
    item.valor_total = data['valor_total']
    item.origem = data['origem']
    
    # Campos opcionais
    if 'peso_bruto' in data:
        item.peso_bruto = data['peso_bruto']
    if 'cnpj_transportadora' in data:
        item.cnpj_transportadora = data['cnpj_transportadora']
    if 'nome_transportadora' in data:
        item.nome_transportadora = data['nome_transportadora']
    if 'municipio' in data:
        item.municipio = data['municipio']
    if 'estado' in data:
        item.estado = data['estado']
    if 'codigo_ibge' in data:
        item.codigo_ibge = data['codigo_ibge']
    if 'incoterm' in data:
        item.incoterm = data['incoterm']
    if 'vendedor' in data:
        item.vendedor = data['vendedor']

def _create_faturamento_consolidado_item(data):
    """Cria um novo item do faturamento consolidado"""
    item = RelatorioFaturamentoImportado()
    item.numero_nf = data['numero_nf']
    item.data_fatura = datetime.strptime(data['data_fatura'], '%Y-%m-%d').date()
    item.cnpj_cliente = data['cnpj_cliente']
    item.nome_cliente = data['nome_cliente']
    item.valor_total = data['valor_total']
    item.origem = data['origem']
    
    # Aplicar campos opcionais
    _update_faturamento_consolidado_item(item, data)
    
    # Adicionar ao banco
    db.session.add(item)

def _process_faturamento_produto_item(item):
    """Processa um item individual do faturamento por produto"""
    try:
        # Buscar item existente
        existing_item = FaturamentoProduto.query.filter_by(
            numero_nf=item['numero_nf'],
            cod_produto=item['cod_produto']
        ).first()
        
        if existing_item:
            # Atualizar item existente
            _update_faturamento_produto_item(existing_item, item)
            action = 'updated'
        else:
            # Criar novo item
            _create_faturamento_produto_item(item)
            action = 'created'
        
        db.session.commit()
        return action
        
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Erro de integridade ao processar faturamento produto: {str(e)}")
        raise ValueError(f"Erro de integridade: {str(e)}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar faturamento produto: {str(e)}")
        raise ValueError(f"Erro no processamento: {str(e)}")

def _update_faturamento_produto_item(item, data):
    """Atualiza um item existente do faturamento por produto"""
    item.data_fatura = datetime.strptime(data['data_fatura'], '%Y-%m-%d').date()
    item.cnpj_cliente = data['cnpj_cliente']
    item.nome_cliente = data['nome_cliente']
    item.nome_produto = data['nome_produto']
    item.qtd_produto_faturado = data['qtd_produto_faturado']
    item.preco_produto_faturado = data['preco_produto_faturado']
    item.valor_produto_faturado = data['valor_produto_faturado']
    
    # Campos opcionais
    if 'municipio' in data:
        item.municipio = data['municipio']
    if 'estado' in data:
        item.estado = data['estado']
    if 'vendedor' in data:
        item.vendedor = data['vendedor']
    if 'incoterm' in data:
        item.incoterm = data['incoterm']
    if 'origem' in data:
        item.origem = data['origem']
    if 'status_nf' in data:
        item.status_nf = data['status_nf']
    if 'peso_total' in data:
        item.peso_total = data['peso_total']
    
    # Auditoria
    item.updated_by = current_user.nome if current_user.is_authenticated else 'API_ODOO'

def _create_faturamento_produto_item(data):
    """Cria um novo item do faturamento por produto"""
    item = FaturamentoProduto()
    item.numero_nf = data['numero_nf']
    item.data_fatura = datetime.strptime(data['data_fatura'], '%Y-%m-%d').date()
    item.cnpj_cliente = data['cnpj_cliente']
    item.nome_cliente = data['nome_cliente']
    item.cod_produto = data['cod_produto']
    item.nome_produto = data['nome_produto']
    item.qtd_produto_faturado = data['qtd_produto_faturado']
    item.preco_produto_faturado = data['preco_produto_faturado']
    item.valor_produto_faturado = data['valor_produto_faturado']
    item.created_by = current_user.nome if current_user.is_authenticated else 'API_ODOO'
    item.updated_by = current_user.nome if current_user.is_authenticated else 'API_ODOO'
    
    # Aplicar campos opcionais
    _update_faturamento_produto_item(item, data)
    
    # Adicionar ao banco
    db.session.add(item)

# ============================================================================
# ROTA: TESTE DE CONECTIVIDADE
# ============================================================================

@odoo_bp.route('/test', methods=['GET'])
def test_connection():
    """Testa conectividade com a API"""
    return create_response(
        success=True,
        message="Conexão estabelecida com sucesso!",
        data={
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'endpoints': [
                '/api/v1/odoo/carteira/bulk-update',
                '/api/v1/odoo/faturamento/bulk-update',
                '/api/v1/odoo/test'
            ]
        }
    ) 