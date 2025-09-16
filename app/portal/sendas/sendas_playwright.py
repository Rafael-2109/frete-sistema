#!/usr/bin/env python3
"""
Script Playwright para automação do Portal Sendas (Trizy)
"""

import os
import sys
import asyncio
import json
from playwright.async_api import async_playwright
import logging
from dotenv import load_dotenv
from playwright.async_api import TimeoutError as PWTimeout
# from gravar_acoes import GravadorAcoes

# Configurar path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



class SendasPortal:
    def __init__(self, headless: bool = False):
        # FORÇAR headless=True em produção (Render)
        # Detectar ambiente de produção de várias formas
        is_render = os.getenv('RENDER') is not None
        is_production = os.getenv('IS_PRODUCTION', '').lower() in ['true', '1', 'yes']
        is_render_path = '/opt/render' in os.getcwd()
        
        # Se estiver em produção, SEMPRE forçar headless=True
        if is_render or is_production or is_render_path:
            logger.warning(f"🚀 PRODUÇÃO DETECTADA - Forçando headless=True (parâmetro era {headless})")
            self.headless = True
        else:
            self.headless = headless
            
        self.browser = None
        self.page = None
        self.context = None

        # credenciais / urls / arquivos
        self.usuario = os.getenv('SENDAS_USUARIO')
        self.senha = os.getenv('SENDAS_SENHA')
        self.url_login = 'https://plataforma.trizy.com.br/#/terminal/painel'
        self.url_home = 'https://plataforma.trizy.com.br/#/terminal/painel'
        self.state_file = os.path.join(os.path.dirname(__file__), 'sendas_state.json')
        self.cookies_file = os.path.join(os.path.dirname(__file__), 'sendas_cookies.json')
        # Arquivo de cookies da sessão capturada manualmente
        self.session_cookies_file = os.path.join(os.path.dirname(__file__), 'sessions', 'sendas_cookies.json')
        # Diretório para downloads
        self.download_dir = os.path.join(os.path.dirname(__file__), 'downloads')
        os.makedirs(self.download_dir, exist_ok=True)
        logger.info(f"Portal Sendas inicializado - Headless: {headless}")
        logger.info(f"Usuário configurado: {self.usuario}")
        logger.info(f"Diretório de downloads: {self.download_dir}")

    # ====== MOVER ESTES HELPERS PARA FORA DO __init__ (nível da classe) ======
    async def _log_turnstile_diagnostico(self):
        self.page.on("console", lambda m: logger.info(f"📜 CONSOLE[{m.type}] {m.text}"))
        
        async def on_response(resp):
            if "challenges.cloudflare.com" in resp.url:
                logger.info(f"🌐 RESP {resp.status} {resp.url}")
        self.page.on("response", on_response)

    async def _esperar_script_turnstile(self, timeout_ms=15000):
        await self.page.wait_for_function(
            "() => !![...document.scripts].find(s => (s.src||'').includes('challenges.cloudflare.com/turnstile'))",
            timeout=timeout_ms
        )
        await self.page.wait_for_function("() => typeof window.turnstile === 'object'", timeout=timeout_ms)

    async def _esperar_token_turnstile(self, timeout_ms=25000) -> str:
        await self.page.wait_for_selector('input[name="cf-turnstile-response"]', state='attached', timeout=timeout_ms)
        await self.page.wait_for_function(
            """() => {
                const el = document.querySelector('input[name="cf-turnstile-response"]');
                return el && el.value && el.value.length > 10;
            }""",
            timeout=timeout_ms
        )
        return await self.page.locator('input[name="cf-turnstile-response"]').input_value()
    # ========================================================================
    
    async def carregar_cookies_salvos(self) -> bool:
        """
        Carrega os cookies salvos da sessão capturada manualmente
        Retorna True se conseguiu carregar e aplicar os cookies
        """
        try:
            # Verifica se o arquivo de cookies existe
            if not os.path.exists(self.session_cookies_file):
                logger.warning(f"❌ Arquivo de cookies não encontrado: {self.session_cookies_file}")
                return False
            
            logger.info(f"📦 Carregando cookies de: {self.session_cookies_file}")
            
            # Ler cookies do arquivo
            with open(self.session_cookies_file, 'r') as f:
                cookies_json = json.load(f)
            
            logger.info(f"✅ {len(cookies_json)} cookies carregados do arquivo")
            
            # Converter cookies para formato Playwright
            playwright_cookies = []
            for cookie in cookies_json:
                # Formato esperado pelo Playwright
                pw_cookie = {
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    'domain': cookie.get('domain', '.trizy.com.br'),
                    'path': cookie.get('path', '/'),
                }
                
                # Adicionar campos opcionais se existirem
                if 'secure' in cookie:
                    pw_cookie['secure'] = cookie.get('secure', True)
                if 'httpOnly' in cookie:
                    pw_cookie['httpOnly'] = cookie.get('httpOnly', False)
                if 'sameSite' in cookie:
                    # Playwright espera 'Lax', 'Strict' ou 'None'
                    same_site = cookie.get('sameSite', 'None')
                    if same_site and same_site != 'None':
                        pw_cookie['sameSite'] = same_site
                    
                playwright_cookies.append(pw_cookie)
            
            # Adicionar cookies ao contexto
            await self.context.add_cookies(playwright_cookies)
            logger.info(f"✅ {len(playwright_cookies)} cookies adicionados ao navegador")
            
            # Salvar como storage_state para futuras sessões
            await self.salvar_storage_state()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar cookies: {e}")
            return False
    
    async def verificar_autenticacao(self) -> bool:
        """
        Verifica se está autenticado tentando acessar uma área protegida
        """
        try:
            logger.info("🔍 Verificando autenticação...")
            
            # Tentar acessar a plataforma
            await self.page.goto(self.url_home, wait_until='domcontentloaded', timeout=15000)
            await self.page.wait_for_timeout(2000)  # Aguardar possíveis redirecionamentos
            
            current_url = self.page.url
            logger.info(f"📍 URL atual: {current_url}")
            
            # Verificar se foi redirecionado para login
            if 'login' in current_url.lower() or 'auth' in current_url.lower():
                logger.warning("❌ Redirecionado para login - não autenticado")
                return False
            
            # Verificar se está na plataforma
            if 'plataforma' in current_url.lower() or 'trizy' in current_url.lower():
                logger.info("✅ Acesso autorizado à plataforma")
                
                # Tentar capturar informações do usuário se disponível
                try:
                    # Aguardar possível elemento com nome do usuário
                    user_element = await self.page.wait_for_selector(
                        '[class*="user"], [class*="User"], [id*="user"], [class*="profile"]',
                        timeout=3000
                    )
                    if user_element:
                        user_text = await user_element.text_content()
                        logger.info(f"👤 Usuário detectado: {user_text}")
                except Exception:
                    pass  # Não é crítico se não encontrar
                
                return True
            
            logger.warning(f"⚠️ URL não reconhecida: {current_url}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar autenticação: {e}")
            return False

    async def fazer_login(self) -> bool:
        """
        Tenta fazer login no portal Sendas
        Primeiro tenta usar cookies salvos, se falhar, tenta login com credenciais
        """
        try:
            # Primeiro, tentar carregar cookies salvos
            logger.info("🍪 Tentando usar cookies salvos...")
            if await self.carregar_cookies_salvos():
                # Verificar se os cookies funcionam
                if await self.verificar_autenticacao():
                    logger.info("✅ Login realizado com sucesso usando cookies salvos!")
                    return True
                else:
                    logger.warning("⚠️ Cookies carregados mas não funcionaram, tentando login tradicional...")
            else:
                logger.info("⚠️ Sem cookies salvos, tentando login tradicional...")
            
            # Se chegou aqui, precisa fazer login tradicional com captcha
            logger.info("📋 Iniciando login tradicional no portal Sendas…")
            await self._log_turnstile_diagnostico()

            await self.page.goto(self.url_login, wait_until='domcontentloaded')
            logger.info("✅ Página de login carregada")

            # Confirma carregamento do Turnstile (se falhar, é tipicamente CSP/bloqueio)
            try:
                await self._esperar_script_turnstile(15000)
                logger.info("✅ Turnstile api.js carregado")
            except PWTimeout:
                logger.error("❌ Turnstile não carregou (CSP/bloqueio?). Tentaremos mesmo assim.")

            # Preenche credenciais
            await self.page.wait_for_selector('input[name="email_or_telephone"]', state='visible')
            await self.page.fill('input[name="email_or_telephone"]', self.usuario)
            await self.page.wait_for_selector('input[name="password"]', state='visible')
            await self.page.fill('input[name="password"]', self.senha)

            # Garante que o container do widget está em viewport
            ts_container = self.page.locator('#cf-turnstile')
            if await ts_container.count():
                await ts_container.scroll_into_view_if_needed()
                await self.page.wait_for_timeout(300)

            # ==== Estrat A: token antes do submit (auto/managed) ====
            token_obtido = False
            try:
                token = await self._esperar_token_turnstile(15000)
                logger.info(f"🔑 Token (pré-submit): {token[:24]}…")
                token_obtido = True
            except PWTimeout:
                logger.info("⌛ Sem token pré-submit — pode ser modo checkbox/invisível.")

            # ==== Se não veio token, tente interagir com o checkbox dentro do iframe ====
            if not token_obtido:
                try:
                    # aguarda iframe existir
                    iframe_el = await self.page.wait_for_selector(
                        '#cf-turnstile iframe, iframe[src*="challenges.cloudflare.com"]',
                        timeout=8000
                    )
                    frame = await iframe_el.content_frame()
                    clicked = False

                    if frame:
                        logger.info("📦 Iframe do Turnstile detectado (content_frame OK) — tentando clique dentro.")
                        # heurísticas internas (UI do Turnstile varia por tema):
                        # 1) role checkbox
                        try:
                            await frame.get_by_role("checkbox").click(timeout=2500)
                            clicked = True
                        except Exception:
                            pass
                        # 2) elementos focáveis genéricos
                        if not clicked:
                            try:
                                await frame.locator('[tabindex="0"]').first.click(timeout=2500)
                                clicked = True
                            except Exception:
                                pass
                    # 3) fallback: clique no centro do próprio iframe (coordenadas na página)
                    if not clicked:
                        bb = await iframe_el.bounding_box()
                        if bb:
                            logger.info("🖱️ Fallback: clicando no centro do iframe…")
                            await self.page.mouse.move(bb['x'] + bb['width']/2, bb['y'] + bb['height']/2)
                            await self.page.mouse.click(bb['x'] + bb['width']/2, bb['y'] + bb['height']/2)
                            clicked = True

                    if clicked:
                        logger.info("✅ Clique no widget efetuado. Aguardando token…")
                        try:
                            token = await self._esperar_token_turnstile(20000)
                            logger.info(f"🔑 Token (após checkbox): {token[:24]}…")
                            token_obtido = True
                        except PWTimeout:
                            logger.warning("⚠️ Sem token após clicar no checkbox (tentaremos pós-submit).")
                    else:
                        logger.info("ℹ️ Não foi possível interagir no iframe; seguindo com pós-submit.")

                except PWTimeout:
                    logger.info("ℹ️ Iframe do Turnstile não ficou disponível a tempo (pode ser invisível).")
                except Exception as e:
                    logger.info(f"ℹ️ Erro ao interagir com iframe do Turnstile: {e}")

            # ==== Submit ====
            btn = self.page.locator('button[type="submit"]')
            if not await btn.count():
                btn = self.page.get_by_role("button", name="Entrar")
            try:
                await btn.wait_for(state="visible", timeout=8000)
            except PWTimeout:
                logger.warning("⚠️ Botão 'Entrar' não ficou visível a tempo; tentando mesmo assim.")

            logger.info("🖱️ Clicando em Entrar…")
            await btn.click()

            # ==== Estrat B: token pós-submit (modo invisível/managed) ====
            if not token_obtido:
                try:
                    await self.page.wait_for_selector('input[name="cf-turnstile-response"]', state='attached', timeout=10000)
                    for i in range(35):  # ~35s de poll com log
                        val = await self.page.locator('input[name="cf-turnstile-response"]').input_value()
                        if val and len(val) > 10:
                            logger.info(f"🔑 Token (pós-submit): {val[:24]}…")
                            token_obtido = True
                            break
                        await self.page.wait_for_timeout(1000)

                    if not token_obtido:
                        val2 = await self._esperar_token_turnstile(25000)
                        logger.info(f"🔑 Token (pós-submit - 2ª): {val2[:24]}…")
                        token_obtido = True
                except PWTimeout:
                    logger.warning("⚠️ Input do Turnstile não apareceu após submit.")
                except Exception as e:
                    logger.warning(f"⚠️ Ao aguardar token pós-submit: {e}")

            # (extra) último empurrão: se ainda sem token, clique no container do widget e repita poll curto
            if not token_obtido and await ts_container.count():
                try:
                    logger.info("↻ Tentando ativar widget clicando no container…")
                    await ts_container.click(force=True)
                    for i in range(10):  # +10s
                        val = await self.page.locator('input[name="cf-turnstile-response"]').input_value()
                        if val and len(val) > 10:
                            logger.info(f"🔑 Token (após container): {val[:24]}…")
                            token_obtido = True
                            break
                        await self.page.wait_for_timeout(1000)
                except Exception:
                    pass

            # Espera sair de /access/auth/login (SPA pode demorar; toleramos timeout)
            try:
                await self.page.wait_for_function(
                    "() => !location.pathname.includes('/access/auth/login')",
                    timeout=22000
                )
            except PWTimeout:
                pass

            current_url = self.page.url
            logger.info(f"📍 URL atual: {current_url}")
            await self.page.screenshot(path='sendas_apos_login.png')

            if 'login' not in current_url.lower():
                await self.salvar_storage_state()
                logger.info("✅ Login OK (sessão salva).")
                return True

            # Mensagens de erro visuais
            for selector in ('.MuiAlert-root', '[role="alert"]', '.error-message'):
                if await self.page.locator(selector).count():
                    txt = await self.page.locator(selector).first.text_content()
                    logger.error(f"❌ Erro detectado: {(txt or '').strip()}")
                    break

            logger.warning("⚠️ Ainda na página de login (provável token ausente/credenciais/erro backend).")
            return False

        except Exception as e:
            logger.error(f"❌ Erro ao fazer login: {e}")
            try:
                await self.page.screenshot(path='sendas_erro_login.png')
                logger.info("📸 Screenshot do erro: sendas_erro_login.png")
            except Exception:
                pass
            return False



    
    async def iniciar_navegador(self):
        """Inicia o navegador com Playwright"""
        try:
            logger.info("Iniciando navegador...")
            
            # Criar playwright
            self.playwright = await async_playwright().start()
            
            # Configurações do navegador (removidas flags agressivas)
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            
            # Configurações do contexto
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'timezone_id': 'America/Sao_Paulo',
                'locale': 'pt-BR',
                'accept_downloads': True  # Permite downloads (salvaremos manualmente no diretório desejado)
            }
            
            # Carregar storage_state se existir (cookies + localStorage)
            if os.path.exists(self.state_file):
                logger.info("📦 Carregando storage_state...")
                context_options['storage_state'] = self.state_file
            # Fallback para cookies antigos
            elif os.path.exists(self.cookies_file):
                logger.info("🍪 Carregando cookies salvos (formato antigo)...")
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                    context_options['storage_state'] = {'cookies': cookies}
            
            # Criar contexto
            self.context = await self.browser.new_context(**context_options)
            
            # Criar página
            self.page = await self.context.new_page()
            
            # Configurar timeout padrão
            self.page.set_default_timeout(30000)  # 30 segundos
            
            logger.info("✅ Navegador iniciado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar navegador: {e}")
            return False
    
    async def esperar_turnstile_token(self, timeout_ms=30000) -> str:
        """
        Utilitário para esperar o token do Turnstile ser preenchido
        
        Args:
            timeout_ms: Timeout em milissegundos para aguardar o token
            
        Returns:
            Token gerado pelo Turnstile
        """
        logger.info("📍 Verificando presença do input cf-turnstile-response...")
        
        # Garante que o input oculto existe
        await self.page.wait_for_selector('input[name="cf-turnstile-response"]', state='attached', timeout=timeout_ms)
        logger.info("✅ Input cf-turnstile-response encontrado")
        
        # Aguardar o widget do Turnstile estar pronto
        await self.page.wait_for_timeout(3000)
        
        logger.info("⏳ Aguardando token ser preenchido...")
        
        # Espera o valor não-vazio - com polling mais frequente
        await self.page.wait_for_function(
            """
            () => {
              const el = document.querySelector('input[name="cf-turnstile-response"]');
              if (el && el.value) {
                console.log('Token length:', el.value.length);
                return el.value.length > 10;
              }
              return false;
            }
            """,
            timeout=timeout_ms,
            polling=500  # Verificar a cada 500ms
        )
        
        token = await self.page.locator('input[name="cf-turnstile-response"]').input_value()
        logger.info(f"✅ Token obtido: {token[:20]}...")
        return token
    
    
    async def navegar_para_servico(self, servico_url: str = None):
        """
        Navega para um serviço específico na plataforma Trizy
        
        Args:
            servico_url: URL do serviço (ex: 'https://mro.trizy.com.br/')
                        Se None, vai para a home da plataforma
        """
        try:
            if servico_url:
                # Codificar a URL do serviço em base64 para o formato da plataforma
                import base64
                encoded_url = base64.b64encode(servico_url.encode()).decode()
                url_final = f"https://plataforma.trizy.com.br/#/servico/{encoded_url}"
                logger.info(f"🔗 Navegando para serviço: {servico_url}")
            else:
                url_final = self.url_home
                logger.info(f"🏠 Navegando para home da plataforma")
            
            await self.page.goto(url_final, wait_until='domcontentloaded', timeout=20000)
            await self.page.wait_for_timeout(3000)  # Aguardar carregamento completo
            
            current_url = self.page.url
            logger.info(f"📍 URL atual: {current_url}")
            
            # Verificar se continua autenticado
            if 'login' in current_url.lower() or 'auth' in current_url.lower():
                logger.warning("❌ Redirecionado para login - sessão expirou")
                return False
            
            logger.info("✅ Navegação bem-sucedida")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao navegar: {e}")
            return False
    
    async def aguardar_instrucoes(self, com_gravacao=False):
        """Mantém o navegador aberto aguardando instruções
        
        Args:
            com_gravacao: Se True, inicia gravação de ações
        """
        gravador = None

        if com_gravacao:
            # Iniciar gravação automaticamente
            gravador = GravadorAcoes(self.page)
            await gravador.iniciar_gravacao()
            
            logger.info("\n" + "=" * 60)
            logger.info("🎬 MODO DE GRAVAÇÃO ATIVO")
            logger.info("=" * 60)
            logger.info("TODAS AS SUAS AÇÕES ESTÃO SENDO GRAVADAS!")
            logger.info("\nINSTRUÇÕES:")
            logger.info("  1. Navegue até a área de AGENDAMENTO")
            logger.info("  2. Localize a opção de DOWNLOAD da planilha")
            logger.info("  3. Clique para baixar a planilha")
            logger.info("\nCOMANDOS DISPONÍVEIS:")
            logger.info("  - Digite 'marcar' para marcar um ponto importante")
            logger.info("  - Digite 'comentario' para adicionar uma observação")
            logger.info("  - Digite 'resumo' para ver as ações gravadas")
            logger.info("  - Pressione Ctrl+C para parar e salvar a gravação")
            logger.info("=" * 60 + "\n")
            
            # Adicionar marcação inicial
            await gravador.marcar_ponto_importante("Início da navegação pós-login")
            
        else:
            logger.info("\n" + "=" * 60)
            logger.info("🔍 AGUARDANDO SUAS INSTRUÇÕES")
            logger.info("=" * 60)
            logger.info("O navegador está aberto. Por favor, me informe:")
            logger.info("  1. O login funcionou?")
            logger.info("  2. Qual a URL atual?")
            logger.info("  3. O que você vê na tela?")
            logger.info("  4. Qual o próximo passo?")
            logger.info("\nPressione Ctrl+C quando quiser fechar o navegador")
            logger.info("=" * 60 + "\n")

        try:
            # Loop interativo com comandos
            import select
            import sys
            
            while True:
                # Verificar se há entrada do usuário (não bloqueante)
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    linha = sys.stdin.readline().strip()
                    
                    if gravador and linha:
                        if linha.lower() == 'marcar':
                            logger.info("📍 Digite a descrição do ponto importante:")
                            descricao = input().strip()
                            await gravador.marcar_ponto_importante(descricao)
                            
                        elif linha.lower() == 'comentario':
                            logger.info("💬 Digite o comentário:")
                            comentario = input().strip()
                            await gravador.adicionar_comentario(comentario)
                            
                        elif linha.lower() == 'resumo':
                            resumo = gravador.obter_resumo()
                            logger.info("\n📊 RESUMO DA GRAVAÇÃO:")
                            logger.info(json.dumps(resumo, indent=2, ensure_ascii=False))
                            logger.info("")
                
                await asyncio.sleep(0.5)
                
        except KeyboardInterrupt:
            logger.info("\n⏹️ Finalizando...")
            
            if gravador:
                # Marcar fim e parar gravação
                await gravador.marcar_ponto_importante("Fim da navegação")
                gravador.parar_gravacao()
                
                # Mostrar resumo final
                resumo = gravador.obter_resumo()
                logger.info("\n" + "=" * 60)
                logger.info("📊 RESUMO FINAL DA GRAVAÇÃO:")
                logger.info("=" * 60)
                logger.info(f"Total de ações: {resumo['total_acoes']}")
                logger.info(f"Tipos de ações: {resumo['tipos_acoes']}")
                logger.info(f"URLs visitadas: {len(resumo['urls_visitadas'])}")
                if resumo['downloads']:
                    logger.info(f"\n📥 DOWNLOADS CAPTURADOS:")
                    for download in resumo['downloads']:
                        logger.info(f"  - {download}")
                logger.info(f"\n📁 Arquivo salvo: {gravador.arquivo_saida}")
                logger.info("=" * 60)
    
    async def salvar_storage_state(self):
        """Salva o storage_state completo (cookies + localStorage) para reutilização"""
        try:
            await self.context.storage_state(path=self.state_file)
            logger.info(f"💾 Sessão salva em {self.state_file}")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar storage_state: {e}")
    
    async def salvar_cookies(self):
        """Salva os cookies da sessão atual para reutilização (DEPRECATED - use salvar_storage_state)"""
        try:
            cookies = await self.context.cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"🍪 Cookies salvos em: {self.cookies_file}")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar cookies: {e}")
    
    async def limpar_sessao(self):
        """Remove os arquivos de sessão salvos (storage_state e cookies)"""
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
                logger.info("🗑️ Storage state removido")
            if os.path.exists(self.cookies_file):
                os.remove(self.cookies_file)
                logger.info("🗑️ Cookies removidos")
        except Exception as e:
            logger.error(f"❌ Erro ao remover arquivos de sessão: {e}")
    
    async def limpar_cookies(self):
        """Remove o arquivo de cookies salvos (DEPRECATED - use limpar_sessao)"""
        try:
            if os.path.exists(self.cookies_file):
                os.remove(self.cookies_file)
                logger.info("🗑️ Cookies removidos")
        except Exception as e:
            logger.error(f"❌ Erro ao remover cookies: {e}")
    
    async def fechar(self):
        """Fecha o navegador e limpa recursos"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            logger.info("✅ Navegador fechado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao fechar navegador: {e}")


async def main():
    """Função principal para teste"""
    logger.info("=" * 60)
    logger.info("TESTE DE LOGIN - PORTAL SENDAS (TRIZY)")
    logger.info("=" * 60)
    
    # Criar instância do portal com headless=False para visualizar
    portal = SendasPortal(headless=False)
    
    try:
        # Iniciar navegador
        if not await portal.iniciar_navegador():
            logger.error("Falha ao iniciar navegador")
            return
        
        # Fazer login (primeiro tentará usar cookies salvos)
        if await portal.fazer_login():
            logger.info("\n" + "=" * 60)
            logger.info("✅ LOGIN BEM-SUCEDIDO!")
            logger.info("=" * 60)
            
            # Capturar screenshot da área autenticada
            await portal.page.screenshot(path='sendas_autenticado.png')
            logger.info("📸 Screenshot salvo: sendas_autenticado.png")
            
            # Perguntar se quer iniciar gravação
            logger.info("\n" + "=" * 60)
            logger.info("🎯 PRÓXIMO PASSO")
            logger.info("=" * 60)
            logger.info("Deseja iniciar a GRAVAÇÃO das ações para download da planilha?")
            logger.info("Digite 'sim' para iniciar gravação ou 'nao' para apenas navegar")
            logger.info("=" * 60)
            
            resposta = input("Sua escolha (sim/nao): ").strip().lower()
            
            if resposta == 'sim':
                logger.info("\n🎬 Iniciando modo de gravação...")
                await portal.aguardar_instrucoes(com_gravacao=True)
            else:
                logger.info("\n📌 Modo navegação sem gravação...")
                await portal.aguardar_instrucoes(com_gravacao=False)
        else:
            # Se falhou, manter aberto para debug
            logger.info("\n⚠️ Login falhou, mantendo navegador aberto para verificação...")
            await portal.aguardar_instrucoes(com_gravacao=False)
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro no teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Fechar navegador
        await portal.fechar()
    
    logger.info("=" * 60)
    logger.info("TESTE FINALIZADO")
    logger.info("=" * 60)


if __name__ == "__main__":
    # Executar teste
    asyncio.run(main())