"""
Rotas para receber webhooks do TagPlus
"""
from flask import Blueprint, request, jsonify
import logging
from datetime import datetime
from app import db
from app.carteira.models import CadastroCliente
from app.faturamento.models import FaturamentoProduto
import re
import hashlib
import hmac

logger = logging.getLogger(__name__)

tagplus_webhook = Blueprint('tagplus_webhook', __name__)

# Token secreto para validar webhooks (configurar no TagPlus)
WEBHOOK_SECRET = 'frete2024tagplus#secret'  # Use este mesmo valor no campo X-Hub-Secret do TagPlus

@tagplus_webhook.route('/webhook/tagplus/cliente', methods=['POST'])
def webhook_cliente():
    """Recebe webhook quando um cliente é criado/atualizado no TagPlus"""
    try:
        # Valida assinatura do webhook (se TagPlus enviar)
        if not validar_assinatura(request):
            return jsonify({'erro': 'Assinatura inválida'}), 401
        
        # Pega dados do webhook
        dados = request.get_json()
        evento = dados.get('evento', '')  # criado, atualizado, excluido
        cliente_data = dados.get('cliente', {})
        
        logger.info(f"Webhook cliente recebido: {evento}")
        
        if evento in ['criado', 'atualizado']:
            processar_cliente_webhook(cliente_data)
            
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Erro no webhook de cliente: {e}")
        return jsonify({'erro': str(e)}), 500

@tagplus_webhook.route('/webhook/tagplus/nfe', methods=['POST'])
def webhook_nfe():
    """Recebe webhook quando uma NFE é emitida no TagPlus"""
    try:
        # Valida assinatura
        if not validar_assinatura(request):
            return jsonify({'erro': 'Assinatura inválida'}), 401
        
        # Pega dados do webhook
        dados = request.get_json()
        evento = dados.get('evento', '')  # autorizada, cancelada, inutilizada
        nfe_data = dados.get('nfe', {})
        
        logger.info(f"Webhook NFE recebido: {evento} - NF {nfe_data.get('numero')}")
        
        if evento == 'autorizada':
            processar_nfe_webhook(nfe_data)
        elif evento == 'cancelada':
            cancelar_nfe_webhook(nfe_data)
            
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Erro no webhook de NFE: {e}")
        return jsonify({'erro': str(e)}), 500

@tagplus_webhook.route('/webhook/tagplus/teste', methods=['GET', 'POST'])
def webhook_teste():
    """Endpoint de teste para verificar se webhook está funcionando"""
    logger.info("Webhook de teste recebido")
    
    if request.method == 'POST':
        dados = request.get_json()
        logger.info(f"Dados recebidos no teste: {dados}")
    
    return jsonify({
        'status': 'ok',
        'mensagem': 'Webhook TagPlus funcionando',
        'timestamp': datetime.now().isoformat()
    }), 200

def validar_assinatura(request):
    """Valida assinatura do webhook para garantir que veio do TagPlus"""
    # Se TagPlus não enviar assinatura, aceitar por enquanto
    assinatura_tagplus = request.headers.get('X-TagPlus-Signature', '')
    
    if not assinatura_tagplus:
        # Por enquanto, aceitar sem assinatura
        logger.warning("Webhook recebido sem assinatura")
        return True
    
    # Calcular assinatura esperada
    payload = request.get_data()
    assinatura_esperada = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(assinatura_tagplus, assinatura_esperada)

def processar_cliente_webhook(dados):
    """Processa dados de cliente recebidos via webhook"""
    try:
        # Extrai CNPJ
        cnpj = re.sub(r'\D', '', str(dados.get('cnpj', dados.get('cpf', ''))))
        
        if not cnpj:
            logger.error("Cliente sem CNPJ/CPF no webhook")
            return
        
        # Verifica se existe
        cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj).first()
        
        if cliente:
            # Atualiza
            atualizar_cliente_webhook(cliente, dados)
        else:
            # Cria novo
            criar_cliente_webhook(dados, cnpj)
        
        db.session.commit()
        logger.info(f"Cliente {cnpj} processado via webhook")
        
    except Exception as e:
        logger.error(f"Erro ao processar cliente webhook: {e}")
        db.session.rollback()
        raise

def criar_cliente_webhook(dados, cnpj):
    """Cria cliente a partir de webhook"""
    cliente = CadastroCliente(
        # Identificação
        cnpj_cpf=cnpj,
        raz_social=dados.get('razao_social', dados.get('nome', '')),
        raz_social_red=(dados.get('nome_fantasia', '') or dados.get('nome', ''))[:50],
        
        # Endereço
        cep_endereco_ent=dados.get('cep', ''),
        rua_endereco_ent=dados.get('logradouro', ''),
        endereco_ent=f"{dados.get('logradouro', '')}, {dados.get('numero', '')}",
        bairro_endereco_ent=dados.get('bairro', ''),
        nome_cidade=dados.get('cidade', ''),
        municipio=dados.get('cidade', ''),
        estado=dados.get('uf', ''),
        cod_uf=dados.get('uf', ''),
        
        # Contato
        telefone_endereco_ent=dados.get('telefone', ''),
        email=dados.get('email', ''),
        
        # Endereço de entrega
        cnpj_endereco_ent=cnpj,
        empresa_endereco_ent=dados.get('razao_social', dados.get('nome', '')),
        
        # Defaults
        vendedor='A DEFINIR',
        equipe_vendas='GERAL',
        cliente_ativo=True,
        
        # Controle
        created_by='WebhookTagPlus',
        updated_by='WebhookTagPlus',
        observacoes=f"Criado via webhook TagPlus - ID: {dados.get('id', '')}"
    )
    
    db.session.add(cliente)
    logger.info(f"Cliente {cliente.raz_social} criado via webhook")

def atualizar_cliente_webhook(cliente, dados):
    """Atualiza cliente existente via webhook"""
    # Atualiza todos os campos (webhook indica mudança)
    cliente.raz_social = dados.get('razao_social', dados.get('nome', cliente.raz_social))
    cliente.raz_social_red = (dados.get('nome_fantasia', '') or cliente.raz_social_red)[:50]
    
    if dados.get('email'):
        cliente.email = dados.get('email')
    
    if dados.get('telefone'):
        cliente.telefone_endereco_ent = dados.get('telefone')
    
    # Atualiza endereço se vier completo
    if dados.get('cep'):
        cliente.cep_endereco_ent = dados.get('cep', '')
        cliente.rua_endereco_ent = dados.get('logradouro', '')
        cliente.endereco_ent = f"{dados.get('logradouro', '')}, {dados.get('numero', '')}"
        cliente.bairro_endereco_ent = dados.get('bairro', '')
        cliente.nome_cidade = dados.get('cidade', '')
        cliente.municipio = dados.get('cidade', '')
        cliente.estado = dados.get('uf', '')
        cliente.cod_uf = dados.get('uf', '')
    
    cliente.updated_by = 'WebhookTagPlus'
    cliente.updated_at = datetime.utcnow()
    
    logger.info(f"Cliente {cliente.raz_social} atualizado via webhook")

def processar_nfe_webhook(nfe_data):
    """Processa NFE recebida via webhook"""
    try:
        numero_nf = str(nfe_data.get('numero', ''))
        
        # Verifica se já existe
        existe = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).first()
        if existe:
            logger.info(f"NF {numero_nf} já existe")
            return
        
        # Busca cliente
        cliente_data = nfe_data.get('cliente', {})
        cnpj_cliente = re.sub(r'\D', '', str(cliente_data.get('cnpj', '')))
        
        cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj_cliente).first()
        if not cliente:
            # Cria cliente básico
            criar_cliente_webhook(cliente_data, cnpj_cliente)
            db.session.flush()
            cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj_cliente).first()
        
        # Processa itens da NF
        itens_criados = []
        for item in nfe_data.get('itens', []):
            item_faturamento = criar_item_faturamento_webhook(nfe_data, item, cliente)
            itens_criados.append(item_faturamento)
        
        db.session.commit()
        logger.info(f"NF {numero_nf} processada via webhook com {len(nfe_data.get('itens', []))} itens")
        
        # Executa processamento completo (score, movimentação, vinculação)
        processar_faturamento_tagplus(numero_nf)
        
    except Exception as e:
        logger.error(f"Erro ao processar NFE webhook: {e}")
        db.session.rollback()
        raise

def processar_faturamento_tagplus(numero_nf):
    """Executa processamento completo da NF (score, movimentação, etc)"""
    try:
        from app.integracoes.tagplus.processador_faturamento_tagplus import ProcessadorFaturamentoTagPlus
        
        logger.info(f"Iniciando processamento completo da NF {numero_nf}")
        
        # Busca todos os itens da NF
        itens_nf = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf,
            created_by='WebhookTagPlus'
        ).all()
        
        if not itens_nf:
            logger.warning(f"Nenhum item encontrado para NF {numero_nf}")
            return
        
        # Processa cada item
        processador = ProcessadorFaturamentoTagPlus()
        for item in itens_nf:
            processador.processar_nf_tagplus(item)
        
        # Commit final
        db.session.commit()
        
        logger.info(f"Processamento completo da NF {numero_nf} finalizado")
        logger.info(f"NFs processadas: {len(processador.nfs_processadas)}")
        logger.info(f"Movimentações criadas: {len(processador.movimentacoes_criadas)}")
        if processador.inconsistencias:
            logger.warning(f"Inconsistências: {processador.inconsistencias}")
        
    except Exception as e:
        logger.error(f"Erro no processamento completo da NF {numero_nf}: {e}")
        db.session.rollback()
        # Não relança a exceção para não falhar o webhook

def criar_item_faturamento_webhook(nfe_data, item_data, cliente):
    """Cria item de faturamento a partir de webhook"""
    # Parse da data
    data_emissao = nfe_data.get('data_emissao', '')
    if data_emissao:
        try:
            data_fatura = datetime.strptime(data_emissao[:10], '%Y-%m-%d').date()
        except:
            data_fatura = datetime.now().date()
    else:
        data_fatura = datetime.now().date()
    
    faturamento = FaturamentoProduto(
        # Dados da NF
        numero_nf=str(nfe_data.get('numero', '')),
        data_fatura=data_fatura,
        
        # Dados do cliente
        cnpj_cliente=cliente.cnpj_cpf,
        nome_cliente=cliente.raz_social,
        municipio=cliente.municipio,
        estado=cliente.estado,
        vendedor=cliente.vendedor,
        equipe_vendas=cliente.equipe_vendas,
        
        # Dados do produto
        cod_produto=str(item_data.get('codigo', '')),
        nome_produto=item_data.get('descricao', ''),
        qtd_produto_faturado=float(item_data.get('quantidade', 0)),
        preco_produto_faturado=float(item_data.get('valor_unitario', 0)),
        valor_produto_faturado=float(item_data.get('valor_total', 0)),
        
        # Peso
        peso_unitario_produto=float(item_data.get('peso_unitario', 0)),
        peso_total=float(item_data.get('quantidade', 0)) * float(item_data.get('peso_unitario', 0)),
        
        # Origem
        origem=nfe_data.get('pedido', ''),
        
        # Status
        status_nf='Lançado',
        
        # Controle
        created_by='WebhookTagPlus',
        updated_by='WebhookTagPlus'
    )
    
    db.session.add(faturamento)
    return faturamento

def cancelar_nfe_webhook(nfe_data):
    """Processa cancelamento de NFE via webhook"""
    try:
        numero_nf = str(nfe_data.get('numero', ''))
        
        # Busca itens da NF
        itens = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()
        
        for item in itens:
            item.status_nf = 'Cancelado'
            item.updated_by = 'WebhookTagPlus'
            item.updated_at = datetime.utcnow()
        
        db.session.commit()
        logger.info(f"NF {numero_nf} cancelada via webhook")
        
    except Exception as e:
        logger.error(f"Erro ao cancelar NFE: {e}")
        db.session.rollback()