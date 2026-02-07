"""
Rotas para configuração de sessões dos portais
Permite configurar sessões sem acesso ao Shell
"""

from flask import render_template, request, jsonify
from flask_login import login_required
from app.portal import portal_bp
from app.portal.models import PortalConfiguracao, PortalSessao
from app.portal.session_manager import SessionManager
from app.portal.utils.grupo_empresarial import GrupoEmpresarial
from app import db
from datetime import datetime, timedelta
from app.utils.timezone import agora_utc_naive
import os
import json
import logging

# Fix para Playwright Sync em loop asyncio
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass  # Se não tiver nest_asyncio, continuar sem ele

logger = logging.getLogger(__name__)

# Inicializar gerenciador de sessões
session_manager = SessionManager()

@portal_bp.route('/configurar-sessao')
@login_required
def configurar_sessao():
    """Página para configurar sessões dos portais"""
    # Buscar configurações existentes
    configs = PortalConfiguracao.query.filter_by(ativo=True).all()
    
    # Buscar sessões válidas
    sessoes = PortalSessao.query.filter(
        PortalSessao.valido_ate > agora_utc_naive()
    ).all()
    
    # Grupos empresariais disponíveis
    grupos = GrupoEmpresarial.listar_grupos()
    
    return render_template('portal/configurar_sessao.html',
                         configs=configs,
                         sessoes=sessoes,
                         grupos=grupos)

@portal_bp.route('/api/salvar-credenciais', methods=['POST'])
@login_required
def salvar_credenciais():
    """API para salvar credenciais de um portal"""
    try:
        dados = request.json
        portal = dados.get('portal')
        cnpj_cliente = dados.get('cnpj_cliente')
        usuario = dados.get('usuario')
        senha = dados.get('senha')
        
        if not all([portal, usuario, senha]):
            return jsonify({
                'success': False,
                'message': 'Portal, usuário e senha são obrigatórios'
            }), 400
        
        # Criptografar senha
        cipher = session_manager.cipher
        senha_criptografada = cipher.encrypt(senha.encode()).decode()
        
        # Buscar configuração existente ou criar nova
        config = PortalConfiguracao.query.filter_by(
            portal=portal,
            cnpj_cliente=cnpj_cliente
        ).first()
        
        if not config:
            config = PortalConfiguracao(
                portal=portal,
                cnpj_cliente=cnpj_cliente
            )
            db.session.add(config)
        
        # Atualizar dados
        config.usuario = usuario
        config.senha_criptografada = senha_criptografada
        
        # URLs específicas por portal
        if portal == 'atacadao':
            config.url_portal = 'https://atacadao.hodiebooking.com.br/pedidos'
            config.url_login = 'https://atacadao.hodiebooking.com.br/'
            config.login_indicators = {
                'selectors': ['input[type="password"]', '.login-form']
            }
        # Adicionar outros portais aqui quando necessário
        
        config.ativo = True
        config.atualizado_em = agora_utc_naive()
        
        db.session.commit()
        
        logger.info(f"Credenciais salvas para {portal} - CNPJ: {cnpj_cliente or 'Global'}")
        
        return jsonify({
            'success': True,
            'message': 'Credenciais salvas com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao salvar credenciais: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao salvar credenciais: {str(e)}'
        }), 500

@portal_bp.route('/api/testar-login', methods=['POST'])
@login_required
def testar_login():
    """Testa login no portal e salva sessão se sucesso"""
    try:
        dados = request.json
        portal = dados.get('portal')
        cnpj_cliente = dados.get('cnpj_cliente')
        
        # Buscar configuração
        config = PortalConfiguracao.query.filter_by(
            portal=portal,
            cnpj_cliente=cnpj_cliente,
            ativo=True
        ).first()
        
        if not config:
            # Tentar configuração global
            config = PortalConfiguracao.query.filter_by(
                portal=portal,
                cnpj_cliente=None,
                ativo=True
            ).first()
        
        if not config or not config.senha_criptografada:
            return jsonify({
                'success': False,
                'message': 'Credenciais não configuradas para este portal'
            }), 400
        
        # Descriptografar senha
        cipher = session_manager.cipher
        senha = cipher.decrypt(config.senha_criptografada.encode()).decode()
        
        # Testar login baseado no portal
        if portal == 'atacadao':
            from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient
            
            client = AtacadaoPlaywrightClient(headless=True)
            client.iniciar_sessao()
            
            # Fazer login automático
            success = fazer_login_automatico_atacadao(client, config.usuario, senha)
            
            if success:
                # Salvar sessão
                client.context.storage_state(path="storage_state_atacadao.json")
                
                # Salvar no banco também
                salvar_sessao_banco(portal, config.usuario, client)
                
                client.fechar()
                
                return jsonify({
                    'success': True,
                    'message': 'Login realizado com sucesso! Sessão salva.'
                })
            else:
                client.fechar()
                return jsonify({
                    'success': False,
                    'message': 'Falha no login. Verifique usuário e senha.'
                }), 401
        
        else:
            return jsonify({
                'success': False,
                'message': f'Portal {portal} ainda não implementado'
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao testar login: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao testar login: {str(e)}'
        }), 500

@portal_bp.route('/api/verificar-sessao/<portal>')
@login_required
def verificar_sessao(portal):
    """Verifica se existe sessão válida para o portal"""
    try:
        # Verificar arquivo de sessão
        sessao_arquivo_existe = False
        if portal == 'atacadao':
            sessao_arquivo_existe = os.path.exists("storage_state_atacadao.json")
        
        # Verificar sessão no banco
        sessao_banco = PortalSessao.query.filter(
            PortalSessao.portal == portal,
            PortalSessao.valido_ate > agora_utc_naive()
        ).first()
        
        # Verificar credenciais configuradas
        config = PortalConfiguracao.query.filter_by(
            portal=portal,
            ativo=True
        ).first()
        
        return jsonify({
            'success': True,
            'sessao_arquivo': sessao_arquivo_existe,
            'sessao_banco': sessao_banco is not None,
            'credenciais_configuradas': config is not None and config.senha_criptografada is not None,
            'valida_ate': sessao_banco.valido_ate.isoformat() if sessao_banco else None
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar sessão: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def fazer_login_automatico_atacadao(client, usuario, senha):
    """
    Faz login automático no portal Atacadão
    
    Args:
        client: Instância do AtacadaoPlaywrightClient
        usuario: Email/usuário
        senha: Senha
        
    Returns:
        bool: True se login bem sucedido
    """
    try:
        # Navegar para página de login
        from app.portal.atacadao.config import ATACADAO_CONFIG
        url_login = ATACADAO_CONFIG['urls']['login']
        
        client.page.goto(url_login, wait_until='networkidle')
        client.page.wait_for_timeout(2000)
        
        # Verificar se já está logado
        url_atual = client.page.url
        if '/pedidos' in url_atual or client.verificar_login():
            logger.info("Já está logado no Atacadão")
            return True
        
        # Preencher campos de login
        # Tentar diferentes seletores comuns
        seletores_email = [
            'input[type="email"]',
            'input[name="email"]',
            'input[name="username"]',
            'input[placeholder*="mail"]',
            '#email',
            '#username'
        ]
        
        seletores_senha = [
            'input[type="password"]',
            'input[name="password"]',
            '#password'
        ]
        
        # Preencher email
        email_preenchido = False
        for seletor in seletores_email:
            try:
                if client.page.locator(seletor).count() > 0:
                    client.page.locator(seletor).first.fill(usuario)
                    email_preenchido = True
                    logger.info(f"Email preenchido com seletor: {seletor}")
                    break
            except Exception as e:
                logger.error(f"Erro ao preencher email: {e}")
                continue
        
        if not email_preenchido:
            logger.error("Não foi possível encontrar campo de email")
            return False
        
        # Preencher senha
        senha_preenchida = False
        for seletor in seletores_senha:
            try:
                if client.page.locator(seletor).count() > 0:
                    client.page.locator(seletor).first.fill(senha)
                    senha_preenchida = True
                    logger.info(f"Senha preenchida com seletor: {seletor}")
                    break
            except Exception as e:
                logger.error(f"Erro ao preencher senha: {e}")
                continue
        
        if not senha_preenchida:
            logger.error("Não foi possível encontrar campo de senha")
            return False
        
        # Clicar em login
        seletores_submit = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Entrar")',
            'button:has-text("Login")',
            '.btn-login'
        ]
        
        for seletor in seletores_submit:
            try:
                if client.page.locator(seletor).count() > 0:
                    client.page.locator(seletor).first.click()
                    logger.info(f"Botão de login clicado: {seletor}")
                    break
            except Exception as e:
                logger.error(f"Erro ao clicar em login: {e}")
                continue
        
        # Aguardar login processar
        client.page.wait_for_timeout(5000)
        
        # Verificar se login foi bem sucedido
        url_atual = client.page.url
        if '/pedidos' in url_atual or client.verificar_login():
            logger.info("Login automático realizado com sucesso!")
            return True
        
        # Se ainda estiver na página de login, falhou
        if 'login' in url_atual.lower():
            logger.error("Login falhou - ainda na página de login")
            return False
        
        # Se chegou aqui, assumir sucesso
        return True
        
    except Exception as e:
        logger.error(f"Erro no login automático: {e}")
        return False

def salvar_sessao_banco(portal, usuario, client):
    """
    Salva sessão no banco de dados
    
    Args:
        portal: Nome do portal
        usuario: Nome do usuário
        client: Cliente Playwright com sessão ativa
    """
    try:
        # Obter storage state
        storage = client.context.storage_state()
        
        # Buscar ou criar sessão
        sessao = PortalSessao.query.filter_by(
            portal=portal,
            usuario=usuario
        ).first()
        
        if not sessao:
            sessao = PortalSessao(
                portal=portal,
                usuario=usuario
            )
            db.session.add(sessao)
        
        # Criptografar cookies
        cookies_json = json.dumps(storage.get('cookies', []))
        cipher = session_manager.cipher
        cookies_criptografados = cipher.encrypt(cookies_json.encode()).decode()
        
        # Atualizar dados
        sessao.cookies_criptografados = cookies_criptografados
        sessao.storage_state = storage
        sessao.valido_ate = agora_utc_naive() + timedelta(hours=24)
        sessao.ultima_utilizacao = agora_utc_naive()
        sessao.atualizado_em = agora_utc_naive()
        
        db.session.commit()
        logger.info(f"Sessão salva no banco para {portal}")
        
    except Exception as e:
        logger.error(f"Erro ao salvar sessão no banco: {e}")
        db.session.rollback()

# Função para auto-relogin quando necessário
def garantir_sessao_valida(portal, cnpj_cliente=None):
    """
    Garante que existe uma sessão válida para o portal
    Faz re-login automático se necessário
    
    Args:
        portal: Nome do portal
        cnpj_cliente: CNPJ do cliente (opcional)
        
    Returns:
        bool: True se sessão válida ou re-login bem sucedido
    """
    try:
        # Verificar se arquivo de sessão existe
        if portal == 'atacadao':
            if os.path.exists("storage_state_atacadao.json"):
                # Tentar usar a sessão existente
                from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient
                
                client = AtacadaoPlaywrightClient(headless=True)
                client.iniciar_sessao()
                
                if client.verificar_login():
                    client.fechar()
                    return True
                
                client.fechar()
                logger.info("Sessão expirada, tentando re-login automático...")
            
            # Buscar credenciais
            config = PortalConfiguracao.query.filter_by(
                portal=portal,
                cnpj_cliente=cnpj_cliente,
                ativo=True
            ).first()
            
            if not config:
                # Tentar credencial global
                config = PortalConfiguracao.query.filter_by(
                    portal=portal,
                    cnpj_cliente=None,
                    ativo=True
                ).first()
            
            if not config or not config.senha_criptografada:
                logger.warning(f"Sem credenciais configuradas para {portal}")
                return False
            
            # Descriptografar senha
            cipher = session_manager.cipher
            senha = cipher.decrypt(config.senha_criptografada.encode()).decode()
            
            # Fazer re-login
            client = AtacadaoPlaywrightClient(headless=True)
            client.iniciar_sessao(salvar_login=True)  # Força nova sessão
            
            success = fazer_login_automatico_atacadao(client, config.usuario, senha)
            
            if success:
                # Salvar nova sessão
                client.context.storage_state(path="storage_state_atacadao.json")
                salvar_sessao_banco(portal, config.usuario, client)
                logger.info("Re-login automático realizado com sucesso!")
            
            client.fechar()
            return success
            
        return False
        
    except Exception as e:
        logger.error(f"Erro ao garantir sessão válida: {e}")
        return False