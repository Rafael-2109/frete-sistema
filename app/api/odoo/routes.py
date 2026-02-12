"""
Rotas API para integração com Odoo
Sincronização de carteira de pedidos e faturamento
"""

from flask import Blueprint, request
from flask_login import current_user
from datetime import datetime
import logging
from sqlalchemy.exc import IntegrityError


from app import db
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.api.odoo.validators import validate_faturamento_data
from app.api.odoo.auth import require_api_key, require_jwt_token
from app.api.odoo.utils import process_bulk_operation, create_response
from app.odoo.services.pedido_sync_service import PedidoSyncService
from app.utils.timezone import agora_utc_naive

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
    if 'equipe_vendas' in data:
        item.equipe_vendas = data['equipe_vendas']

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
    if 'equipe_vendas' in data:
        item.equipe_vendas = data['equipe_vendas']
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

# ============================================================================
# ROTA: SINCRONIZAÇÃO MANUAL DE PEDIDO ESPECÍFICO
# ============================================================================

@odoo_bp.route('/pedido/<string:num_pedido>/sync', methods=['POST'])
def sincronizar_pedido_especifico(num_pedido):
    """
    Sincroniza um pedido específico com o Odoo

    Endpoint: POST /api/v1/odoo/pedido/<num_pedido>/sync

    Comportamento:
    - Se pedido ENCONTRADO no Odoo: ATUALIZA no sistema
    - Se pedido NÃO ENCONTRADO no Odoo: EXCLUI do sistema
    - Se pedido CANCELADO no Odoo: EXCLUI do sistema

    Args:
        num_pedido: Número do pedido (ex: VSC12345)

    Returns:
        JSON com resultado da sincronização:
        {
            "success": true/false,
            "message": "...",
            "data": {
                "acao": "ATUALIZADO" | "EXCLUIDO" | "NAO_PROCESSADO",
                "num_pedido": "VSC12345",
                "detalhes": {...},
                "tempo_execucao": 1.23,
                "timestamp": "2025-01-20T10:30:00"
            }
        }

    Exemplo de uso:
        POST /api/v1/odoo/pedido/VSC12345/sync
        Headers:
            - X-API-Key: sua-api-key
            - Authorization: Bearer seu-jwt-token
    """
    try:
        logger.info(f"📥 Requisição de sincronização manual para pedido: {num_pedido}")

        # Validar número do pedido
        if not num_pedido or len(num_pedido.strip()) == 0:
            return create_response(
                success=False,
                message="Número do pedido não pode ser vazio",
                status_code=400
            )

        # Criar instância do serviço
        sync_service = PedidoSyncService()

        # Executar sincronização
        resultado = sync_service.sincronizar_pedido_especifico(num_pedido)

        # Determinar status code baseado no resultado
        status_code = 200 if resultado.get('sucesso', False) else 500

        # Se foi excluído por não existir, usar 404
        if resultado.get('acao') == 'EXCLUIDO' and 'não encontrado' in resultado.get('mensagem', '').lower():
            status_code = 200  # Mantém 200 pois a operação foi bem sucedida

        return create_response(
            success=resultado.get('sucesso', False),
            message=resultado.get('mensagem', ''),
            data={
                'acao': resultado.get('acao'),
                'num_pedido': num_pedido,
                'detalhes': resultado.get('detalhes', {}),
                'tempo_execucao': resultado.get('tempo_execucao', 0),
                'timestamp': resultado.get('timestamp', agora_utc_naive()).isoformat() if isinstance(resultado.get('timestamp'), datetime) else str(resultado.get('timestamp'))
            },
            status_code=status_code
        )

    except Exception as e:
        logger.error(f"❌ Erro ao processar sincronização do pedido {num_pedido}: {e}")
        return create_response(
            success=False,
            message=f"Erro ao sincronizar pedido: {str(e)}",
            status_code=500
        )


@odoo_bp.route('/test', methods=['GET'])
def test_connection():
    """Testa conectividade com a API"""
    return create_response(
        success=True,
        message="Conexão estabelecida com sucesso!",
        data={
            'timestamp': agora_utc_naive().isoformat(),
            'version': '1.0.0',
            'endpoints': [
                '/api/v1/odoo/carteira/bulk-update',
                '/api/v1/odoo/faturamento/bulk-update',
                '/api/v1/odoo/pedido/<num_pedido>/sync',
                '/api/v1/odoo/test'
            ]
        }
    ) 