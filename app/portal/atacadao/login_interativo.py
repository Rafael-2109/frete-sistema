"""
Sistema de Login Interativo para Portal Atacadão
Gerencia re-login quando sessão expira, com suporte a CAPTCHA
"""

import os
import time
import logging
from playwright.sync_api import sync_playwright
from app.portal.atacadao.config import ATACADAO_CONFIG

logger = logging.getLogger(__name__)

class LoginInterativoAtacadao:
    """
    Gerencia login interativo quando há CAPTCHA ou sessão expirada
    """
    
    def __init__(self):
        self.config = ATACADAO_CONFIG
        self.storage_file = "storage_state_atacadao.json"
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def verificar_necessidade_login(self, client=None):
        """
        Verifica se precisa fazer login
        
        Args:
            client: Cliente Playwright existente (opcional)
            
        Returns:
            dict com status e mensagem
        """
        try:
            # Se tem cliente, usar ele
            if client and hasattr(client, 'page'):
                page = client.page
            else:
                # Criar temporário para verificar
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.launch(headless=True)
                
                # Tentar carregar sessão existente
                if os.path.exists(self.storage_file):
                    self.context = self.browser.new_context(
                        storage_state=self.storage_file
                    )
                else:
                    self.context = self.browser.new_context()
                
                self.page = self.context.new_page()
                page = self.page
            
            # Navegar para página de pedidos
            page.goto(self.config['urls']['pedidos'], wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(2000)
            
            url_atual = page.url
            
            # Verificar se está na página de login
            if 'login' in url_atual.lower() or 'signin' in url_atual.lower():
                logger.info("Redirecionado para login - sessão expirada")
                
                # Verificar se tem CAPTCHA
                tem_captcha = False
                captcha_selectors = [
                    'div[class*="captcha"]',
                    'div[class*="recaptcha"]',
                    'iframe[src*="recaptcha"]',
                    'div#captcha',
                    '.g-recaptcha'
                ]
                
                for selector in captcha_selectors:
                    if page.locator(selector).count() > 0:
                        tem_captcha = True
                        break
                
                return {
                    'precisa_login': True,
                    'tem_captcha': tem_captcha,
                    'url_login': url_atual,
                    'mensagem': 'Sessão expirada. Login necessário.'
                }
            
            # Verificar indicadores de login bem sucedido
            indicadores_logado = [
                'a[href*="logout"]',
                '.user-menu',
                '#usuario-logado',
                '.navbar-user'
            ]
            
            for selector in indicadores_logado:
                if page.locator(selector).count() > 0:
                    logger.info("Usuário logado - sessão válida")
                    return {
                        'precisa_login': False,
                        'tem_captcha': False,
                        'mensagem': 'Sessão válida'
                    }
            
            # Se chegou na página de pedidos sem problemas
            if '/pedidos' in url_atual:
                return {
                    'precisa_login': False,
                    'tem_captcha': False,
                    'mensagem': 'Sessão válida'
                }
            
            # Estado indeterminado
            return {
                'precisa_login': True,
                'tem_captcha': self.config.get('tem_captcha', True),
                'url_login': self.config['urls']['login'],
                'mensagem': 'Estado indeterminado - login recomendado'
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar necessidade de login: {e}")
            return {
                'precisa_login': True,
                'tem_captcha': self.config.get('tem_captcha', True),
                'erro': str(e),
                'mensagem': f'Erro ao verificar sessão: {str(e)}'
            }
        finally:
            # Limpar recursos se criou temporário
            if not client:
                self.fechar()
    
    def abrir_login_interativo(self, headless=False, timeout_segundos=300, pre_preencher=True):
        """
        Abre navegador para login manual com CAPTCHA
        
        Args:
            headless: Se True, abre em modo headless (não recomendado para CAPTCHA)
            timeout_segundos: Tempo máximo de espera para login
            pre_preencher: Se True, pré-preenche credenciais das variáveis de ambiente
            
        Returns:
            dict com resultado do login
        """
        try:
            logger.info("Abrindo navegador para login interativo...")
            
            # Iniciar Playwright em modo visível
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            # Criar contexto novo (sem sessão antiga)
            self.context = self.browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            self.page = self.context.new_page()
            
            # Navegar para login
            url_login = self.config['urls']['login']
            logger.info(f"Navegando para: {url_login}")
            self.page.goto(url_login)
            
            # Pré-preencher credenciais se disponíveis nas variáveis de ambiente
            if pre_preencher:
                self._pre_preencher_credenciais()
            
            # Registrar timestamp de início
            inicio = time.time()
            login_sucesso = False
            
            # Monitorar até login ou timeout
            while time.time() - inicio < timeout_segundos:
                try:
                    # Verificar URL atual
                    url_atual = self.page.url
                    
                    # Se saiu da página de login, verificar se foi sucesso
                    if 'login' not in url_atual.lower() and 'signin' not in url_atual.lower():
                        # Verificar se chegou em página autenticada
                        if '/pedidos' in url_atual or '/dashboard' in url_atual or '/home' in url_atual:
                            logger.info("Login detectado - salvando sessão...")
                            login_sucesso = True
                            break
                    
                    # Verificar indicadores de login
                    for selector in ['.user-menu', 'a[href*="logout"]', '#usuario-logado']:
                        if self.page.locator(selector).count() > 0:
                            logger.info(f"Login detectado via {selector}")
                            login_sucesso = True
                            break
                    
                    if login_sucesso:
                        break
                    
                    # Aguardar um pouco antes de verificar novamente
                    time.sleep(2)
                    
                except Exception as e:
                    logger.debug(f"Erro durante monitoramento: {e}")
                    # Continuar monitorando
            
            if login_sucesso:
                # Salvar sessão
                self.context.storage_state(path=self.storage_file)
                logger.info(f"Sessão salva em {self.storage_file}")
                
                return {
                    'sucesso': True,
                    'mensagem': 'Login realizado com sucesso!',
                    'sessao_salva': True
                }
            else:
                return {
                    'sucesso': False,
                    'mensagem': f'Timeout após {timeout_segundos} segundos',
                    'sessao_salva': False
                }
                
        except Exception as e:
            logger.error(f"Erro no login interativo: {e}")
            return {
                'sucesso': False,
                'mensagem': f'Erro: {str(e)}',
                'sessao_salva': False
            }
        finally:
            self.fechar()
    
    def abrir_janela_login_usuario(self):
        """
        Abre janela menor específica para login do usuário
        Ideal para ser chamada durante operações quando detecta sessão expirada
        
        Returns:
            dict com resultado
        """
        try:
            # Verificar se tem credenciais nas variáveis de ambiente
            tem_credenciais = bool(os.environ.get('ATACADAO_USUARIO') and os.environ.get('ATACADAO_SENHA'))
            
            print("\n" + "="*60)
            print("⚠️  SESSÃO EXPIRADA - LOGIN NECESSÁRIO")
            print("="*60)
            print("\n📌 Uma janela do navegador será aberta")
            
            if tem_credenciais:
                print("✅ Suas credenciais serão pré-preenchidas")
                print("🔐 Você só precisa resolver o CAPTCHA e clicar em Entrar")
            else:
                print("📌 Faça login no portal (resolva o CAPTCHA se necessário)")
                print("💡 Dica: Configure ATACADAO_USUARIO e ATACADAO_SENHA no .env")
            
            print("📌 Após o login, a janela fechará automaticamente")
            print("\n" + "="*60 + "\n")
            
            # Abrir em modo visível com timeout de 5 minutos
            resultado = self.abrir_login_interativo(headless=False, timeout_segundos=300)
            
            if resultado['sucesso']:
                print("\n✅ Login realizado com sucesso! Continuando operação...")
            else:
                print(f"\n❌ {resultado['mensagem']}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao abrir janela de login: {e}")
            return {
                'sucesso': False,
                'mensagem': str(e)
            }
    
    def _pre_preencher_credenciais(self):
        """
        Pré-preenche campos de login com credenciais das variáveis de ambiente
        Usuário ainda precisa resolver o CAPTCHA
        """
        try:
            # Buscar credenciais das variáveis de ambiente
            usuario = os.environ.get('ATACADAO_USUARIO')
            senha = os.environ.get('ATACADAO_SENHA')
            
            if not usuario or not senha:
                logger.info("Credenciais não encontradas nas variáveis de ambiente")
                return False
            
            logger.info("Pré-preenchendo credenciais...")
            
            # Aguardar campos carregarem
            self.page.wait_for_timeout(2000)
            
            # Tentar diferentes seletores para o campo de email/usuário
            seletores_email = [
                'input[type="email"]',
                'input[name="email"]',
                'input[name="username"]',
                'input[placeholder*="mail" i]',
                'input[placeholder*="usuário" i]',
                '#email',
                '#username',
                'input.form-control[type="text"]'
            ]
            
            email_preenchido = False
            for seletor in seletores_email:
                try:
                    elemento = self.page.locator(seletor).first
                    if elemento.count() > 0:
                        elemento.fill('')  # Limpar primeiro
                        elemento.fill(usuario)
                        email_preenchido = True
                        logger.info(f"Email pré-preenchido com seletor: {seletor}")
                        break
                except Exception as e:
                    logger.debug(f"Tentativa com {seletor} falhou: {e}")
                    continue
            
            if not email_preenchido:
                logger.warning("Não foi possível pré-preencher o email")
            
            # Tentar diferentes seletores para o campo de senha
            seletores_senha = [
                'input[type="password"]',
                'input[name="password"]',
                'input[name="senha"]',
                '#password',
                '#senha'
            ]
            
            senha_preenchida = False
            for seletor in seletores_senha:
                try:
                    elemento = self.page.locator(seletor).first
                    if elemento.count() > 0:
                        elemento.fill('')  # Limpar primeiro
                        elemento.fill(senha)
                        senha_preenchida = True
                        logger.info(f"Senha pré-preenchida com seletor: {seletor}")
                        break
                except Exception as e:
                    logger.debug(f"Tentativa com {seletor} falhou: {e}")
                    continue
            
            if not senha_preenchida:
                logger.warning("Não foi possível pré-preencher a senha")
            
            if email_preenchido and senha_preenchida:
                logger.info("✅ Credenciais pré-preenchidas! Aguardando usuário resolver CAPTCHA...")
                
                # Mostrar mensagem na página se possível
                try:
                    self.page.evaluate("""
                        console.log('🔐 Credenciais pré-preenchidas. Por favor, resolva o CAPTCHA e clique em Entrar.');
                    """)
                except Exception as e:
                    logger.error(f"Erro ao mostrar mensagem: {e}")
                    pass
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao pré-preencher credenciais: {e}")
            return False
    
    def fechar(self):
        """Fecha navegador e limpa recursos"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.error(f"Erro ao fechar navegador: {e}")
            pass


class GerenciadorSessaoAtacadao:
    """
    Gerencia sessões do Atacadão com re-login automático quando necessário
    """
    
    @staticmethod
    def executar_com_retry(funcao, *args, **kwargs):
        """
        Executa uma função com retry automático se sessão expirar
        
        Args:
            funcao: Função a executar
            *args, **kwargs: Argumentos da função
            
        Returns:
            Resultado da função ou erro
        """
        max_tentativas = 2
        
        for tentativa in range(max_tentativas):
            try:
                # Tentar executar
                resultado = funcao(*args, **kwargs)
                
                # Se tem indicação de erro de sessão no resultado
                if isinstance(resultado, dict):
                    if resultado.get('sessao_expirada') or 'sessão expirada' in str(resultado.get('message', '')).lower():
                        if tentativa < max_tentativas - 1:
                            logger.info("Sessão expirada detectada - tentando re-login...")
                            
                            # Abrir login interativo
                            login_manager = LoginInterativoAtacadao()
                            login_result = login_manager.abrir_janela_login_usuario()
                            
                            if login_result['sucesso']:
                                logger.info("Re-login bem sucedido - tentando novamente...")
                                continue  # Tentar novamente
                            else:
                                return {
                                    'success': False,
                                    'message': 'Não foi possível fazer re-login',
                                    'requer_login': True
                                }
                
                return resultado
                
            except Exception as e:
                erro_str = str(e).lower()
                
                # Verificar se é erro de sessão
                if 'sessão' in erro_str or 'session' in erro_str or 'login' in erro_str:
                    if tentativa < max_tentativas - 1:
                        logger.info(f"Possível erro de sessão: {e}")
                        
                        # Verificar se precisa de login
                        login_manager = LoginInterativoAtacadao()
                        status = login_manager.verificar_necessidade_login()
                        
                        if status['precisa_login']:
                            logger.info("Login necessário - abrindo janela...")
                            login_result = login_manager.abrir_janela_login_usuario()
                            
                            if login_result['sucesso']:
                                logger.info("Re-login bem sucedido - tentando novamente...")
                                continue
                
                # Se não é erro de sessão ou é última tentativa
                raise e
        
        return {
            'success': False,
            'message': 'Máximo de tentativas excedido'
        }


# Função helper para ser usada em verificacao_protocolo.py
def garantir_sessao_antes_operacao():
    """
    Verifica e garante que a sessão está válida antes de uma operação
    
    Returns:
        bool: True se sessão válida ou re-login bem sucedido
    """
    try:
        login_manager = LoginInterativoAtacadao()
        status = login_manager.verificar_necessidade_login()
        
        if status['precisa_login']:
            logger.info("Sessão expirada - solicitando re-login ao usuário...")
            
            # Se tem CAPTCHA, precisa de login manual
            if status.get('tem_captcha'):
                resultado = login_manager.abrir_janela_login_usuario()
                return resultado['sucesso']
            
        return True
        
    except Exception as e:
        logger.error(f"Erro ao garantir sessão: {e}")
        return False