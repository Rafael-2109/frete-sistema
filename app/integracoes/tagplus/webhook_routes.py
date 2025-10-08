"""
Rotas para receber webhooks do TagPlus

IMPORTANTE - SEGURANÇA:
- Webhooks são requisições externas SEM token CSRF
- Usamos CSRF exempt + validação HMAC com X-Hub-Secret
- Todos os webhooks são logados para auditoria de segurança
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

# ✅ Importar CSRF para usar csrf.exempt
from app import csrf

@csrf.exempt
@tagplus_webhook.route('/webhook/tagplus/cliente', methods=['POST'])
def webhook_cliente():
    """Recebe webhook quando um cliente é criado/atualizado no TagPlus"""
    try:
        # 🔒 LOG DE SEGURANÇA - Início
        logger.info(f"🔔 WEBHOOK RECEBIDO | Endpoint: /webhook/tagplus/cliente | IP: {request.remote_addr}")
        logger.debug(f"🔍 Headers: {dict(request.headers)}")

        # Valida assinatura do webhook (se TagPlus enviar)
        validacao_resultado, motivo = validar_assinatura(request)
        if not validacao_resultado:
            logger.warning(f"🚫 WEBHOOK REJEITADO | Motivo: {motivo} | IP: {request.remote_addr}")
            return jsonify({'erro': motivo}), 401

        logger.info(f"✅ WEBHOOK VALIDADO | {motivo}")

        # Pega dados do webhook
        dados = request.get_json()
        evento = dados.get('evento', '')  # cliente_criado, cliente_atualizado, etc
        cliente_data = dados.get('cliente', {})

        logger.info(f"📦 WEBHOOK CLIENTE | Evento: {evento} | Cliente: {cliente_data.get('cnpj', 'N/A')}")

        # Aceita vários formatos de evento (compatibilidade)
        if evento in ['criado', 'atualizado', 'cliente_criado', 'cliente_atualizado']:
            processar_cliente_webhook(cliente_data)
        else:
            logger.info(f"Evento de cliente ignorado: {evento}")

        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Erro no webhook de cliente: {e}")
        return jsonify({'erro': str(e)}), 500

@csrf.exempt
@tagplus_webhook.route('/webhook/tagplus/nfe', methods=['POST'])
def webhook_nfe():
    """Recebe webhook quando uma NFE é emitida no TagPlus"""
    try:
        # 🔒 LOG DE SEGURANÇA - Início
        logger.info(f"🔔 WEBHOOK RECEBIDO | Endpoint: /webhook/tagplus/nfe | IP: {request.remote_addr}")
        logger.debug(f"🔍 Headers: {dict(request.headers)}")

        # Valida assinatura
        validacao_resultado, motivo = validar_assinatura(request)
        if not validacao_resultado:
            logger.warning(f"🚫 WEBHOOK REJEITADO | Motivo: {motivo} | IP: {request.remote_addr}")
            return jsonify({'erro': motivo}), 401

        logger.info(f"✅ WEBHOOK VALIDADO | {motivo}")

        # Pega dados do webhook
        dados = request.get_json()
        evento = dados.get('evento', '')  # nfe_aprovada, nfe_cancelada, nfe_alterada, nfe_apagada
        nfe_data = dados.get('nfe', {})

        logger.info(f"📦 WEBHOOK NFE | Evento: {evento} | NF: {nfe_data.get('numero', 'N/A')}")

        # TagPlus usa 'nfe_aprovada' para NFe autorizada
        if evento in ['autorizada', 'nfe_aprovada']:
            processar_nfe_webhook(nfe_data)
        # TagPlus usa 'nfe_cancelada' para NFe cancelada
        elif evento in ['cancelada', 'nfe_cancelada']:
            cancelar_nfe_webhook(nfe_data)
        # Eventos ignorados (retorna ok mas não processa)
        elif evento in ['nfe_alterada', 'nfe_apagada']:
            logger.info(f"Evento {evento} ignorado (não processado)")
        else:
            logger.warning(f"Evento desconhecido: {evento}")

        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Erro no webhook de NFE: {e}")
        return jsonify({'erro': str(e)}), 500

@csrf.exempt
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
    """
    Valida assinatura do webhook para garantir que veio do TagPlus

    O TagPlus pode enviar o secret de duas formas:
    1. X-Hub-Secret: O secret em texto plano (configurado no TagPlus)
    2. X-TagPlus-Signature: Hash HMAC-SHA256 do payload

    Retorna: (bool, str) - (validado, motivo)
    """
    # 🔍 MODO 1: Validação via X-Hub-Secret (secret em texto plano)
    secret_enviado = request.headers.get('X-Hub-Secret', '')

    if secret_enviado:
        if secret_enviado == WEBHOOK_SECRET:
            logger.info(f"🔐 Validação via X-Hub-Secret: OK")
            return (True, "X-Hub-Secret válido")
        else:
            logger.error(f"🚫 X-Hub-Secret INVÁLIDO! Esperado: {WEBHOOK_SECRET[:10]}..., Recebido: {secret_enviado[:10]}...")
            return (False, "X-Hub-Secret inválido")

    # 🔍 MODO 2: Validação via X-TagPlus-Signature (HMAC-SHA256)
    assinatura_tagplus = request.headers.get('X-TagPlus-Signature', '')

    if assinatura_tagplus:
        # Calcular assinatura esperada
        payload = request.get_data()
        assinatura_esperada = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(assinatura_tagplus, assinatura_esperada):
            logger.info(f"🔐 Validação via X-TagPlus-Signature (HMAC): OK")
            return (True, "X-TagPlus-Signature válida")
        else:
            logger.error(f"🚫 X-TagPlus-Signature INVÁLIDA!")
            return (False, "X-TagPlus-Signature inválida")

    # ⚠️ NENHUM HEADER DE SEGURANÇA: Aceitar com WARNING (modo desenvolvimento)
    logger.warning(f"⚠️ WEBHOOK SEM ASSINATURA | IP: {request.remote_addr} | Headers: {list(request.headers.keys())}")
    logger.warning("🔓 MODO INSEGURO: Aceitando webhook sem validação (configure X-Hub-Secret no TagPlus!)")
    return (True, "⚠️ Webhook aceito SEM validação de segurança")

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
        from app.faturamento.services.processar_faturamento import ProcessadorFaturamento

        logger.info(f"Iniciando processamento completo da NF {numero_nf}")

        # Busca todos os itens da NF
        itens_nf = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf,
            created_by='WebhookTagPlus'
        ).all()

        if not itens_nf:
            logger.warning(f"Nenhum item encontrado para NF {numero_nf}")
            return

        # Processa usando ProcessadorFaturamento padrão
        processador = ProcessadorFaturamento()
        resultado = processador.processar_nfs_importadas(
            usuario='WebhookTagPlus',
            limpar_inconsistencias=False,
            nfs_especificas=[numero_nf]
        )

        logger.info(f"Processamento completo da NF {numero_nf} finalizado")
        if resultado:
            logger.info(f"NFs processadas: {resultado.get('processadas', 0)}")
            logger.info(f"Movimentações criadas: {resultado.get('movimentacoes_criadas', 0)}")
            if resultado.get('erros'):
                logger.warning(f"Erros: {resultado['erros']}")
        
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
        except Exception as e:
            print(f"Erro ao formatar data: {e}")
            data_fatura = datetime.now().date()
    else:
        data_fatura = datetime.now().date()
    
    # Extrai dados do produto (estrutura aninhada conforme API TagPlus)
    produto_info = item_data.get('produto', {}) or item_data.get('produto_servico', {})
    cod_produto = str(produto_info.get('codigo', '') or item_data.get('item', ''))
    nome_produto = produto_info.get('descricao', '') or ''

    # Extrai quantidades e valores (campos corretos da API TagPlus)
    quantidade = float(item_data.get('qtd', 0) or 0)
    valor_unitario = float(item_data.get('valor_unitario', 0) or 0)
    valor_total = float(item_data.get('valor_subtotal', 0) or 0)

    # Se valor_total estiver zerado, calcular
    if valor_total == 0 and quantidade > 0 and valor_unitario > 0:
        valor_total = quantidade * valor_unitario

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

        # Dados do produto (CORRIGIDO conforme estrutura real da API)
        cod_produto=cod_produto,
        nome_produto=nome_produto,
        qtd_produto_faturado=quantidade,
        preco_produto_faturado=valor_unitario,
        valor_produto_faturado=valor_total,

        # Peso (não vem da API TagPlus, precisa buscar do cadastro)
        peso_unitario_produto=0,
        peso_total=0,

        # Origem (número do pedido se vier na NF)
        origem=nfe_data.get('numero_pedido', '') or '',

        # Status
        status_nf='Lançado',

        # Controle
        created_by='WebhookTagPlus',
        updated_by='WebhookTagPlus'
    )

    db.session.add(faturamento)
    logger.debug(f"Item criado: {cod_produto} - {nome_produto} - Qtd: {quantidade}")
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