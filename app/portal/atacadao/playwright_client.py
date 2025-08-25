"""
Cliente Atacadao usando Playwright - USANDO URLs CORRETAS DO CONFIG
Localizado na pasta CORRETA: app/portal/atacadao/
"""

import os
import time
from datetime import datetime, date
from pathlib import Path
from playwright.sync_api import sync_playwright
import logging
from .config import ATACADAO_CONFIG
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

logger = logging.getLogger(__name__)

class AtacadaoPlaywrightClient:
    """Cliente Playwright para o portal Atacadao (Hodie Booking)"""
    
    def __init__(self, headless=True): 
        self.headless = headless
        # Path absoluto para o storage_state - usar raiz do projeto
        # Primeiro tentar no diretório raiz (onde geralmente está)
        root_storage = Path.cwd() / "storage_state_atacadao.json"
        # Se não existir, usar o diretório do módulo
        module_storage = Path(__file__).resolve().parent / "storage_state_atacadao.json"
        
        if root_storage.exists():
            self.storage_file = str(root_storage)
            logger.info(f"Usando storage_state do raiz: {self.storage_file}")
        else:
            self.storage_file = str(module_storage)
            logger.info(f"Usando storage_state do módulo: {self.storage_file}")
        self.config = ATACADAO_CONFIG  # USANDO CONFIG CORRETO
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def iniciar_sessao(self, salvar_login=False):
        """Inicia sessao do Playwright com ou sem login salvo"""
        self.playwright = sync_playwright().start()
        
        # Configuracoes do navegador - IGUAL AO SCRIPT QUE FUNCIONA
        # REMOVIDO: args=['--disable-blink-features=AutomationControlled']
        self.browser = self.playwright.chromium.launch(
            headless=self.headless
        )
        
        # Contexto com sessao salva ou novo - IGUAL AO SCRIPT QUE FUNCIONA
        # REMOVIDO: viewport={'width': 1280, 'height': 720}
        if os.path.exists(self.storage_file) and not salvar_login:
            logger.info(f"Carregando sessao salva de {self.storage_file}")
            self.context = self.browser.new_context(
                storage_state=self.storage_file
            )
        else:
            logger.info("Criando nova sessao")
            self.context = self.browser.new_context()
        
        self.page = self.context.new_page()
    
    def fazer_login_manual(self):
        """Abre o navegador para login manual e salva a sessao"""
        print("\n" + "="*60)
        print("LOGIN MANUAL NO ATACADAO")
        print("="*60)
        print("\n1. O navegador vai abrir no portal Atacadao")
        print("2. Faca login com suas credenciais")
        print("3. Quando estiver logado, pressione ENTER aqui")
        print("\n" + "="*60 + "\n")
        
        # Iniciar em modo visivel
        self.headless = False
        self.iniciar_sessao(salvar_login=True)
        
        # Navegar para o portal CORRETO
        url_login = self.config['urls']['login']  # https://atacadao.hodiebooking.com.br/
        print(f"Abrindo: {url_login}")
        self.page.goto(url_login)
        
        # Esperar o usuario fazer login
        input("\n Faca login no navegador e pressione ENTER quando terminar...")
        
        # Salvar a sessao
        self.context.storage_state(path=self.storage_file)
        print(f" Sessao salva em {self.storage_file}")
        
        self.fechar()
        return True
    
    def fazer_login_com_captcha(self):
        """
        Faz login automaticamente preenchendo credenciais do .env
        Abre navegador visível para o usuário resolver o CAPTCHA
        """
        try:
            # Verificar se tem credenciais no .env
            usuario = os.environ.get('ATACADAO_USUARIO')
            senha = os.environ.get('ATACADAO_SENHA')
            
            if not usuario or not senha:
                logger.warning("Credenciais não encontradas no .env - usando login manual")
                return self.fazer_login_manual()
            
            logger.info("Iniciando login com CAPTCHA...")
            print("\n" + "="*60)
            print("🔐 LOGIN AUTOMÁTICO COM CAPTCHA")
            print("="*60)
            print(f"\n✅ Usuário: {usuario}")
            print("✅ Senha: ****")
            print("\n📌 Os campos serão preenchidos automaticamente")
            print("🔍 Você só precisa:")
            print("   1. Resolver o CAPTCHA")
            print("   2. Clicar em ENTRAR")
            print("\n⏳ Aguardando até 5 minutos...")
            print("="*60 + "\n")
            
            # Fechar sessão atual se existir
            if self.page:
                self.fechar()
            
            # Iniciar em modo visível - IGUAL AO SCRIPT QUE FUNCIONA
            self.headless = False
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True
                # REMOVIDO: args=['--disable-blink-features=AutomationControlled']
            )
            
            # Criar contexto novo (sem sessão antiga) - IGUAL AO SCRIPT QUE FUNCIONA
            # REMOVIDO: viewport={'width': 1280, 'height': 720}
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
            
            # Navegar para login
            url_login = self.config['urls']['login']
            logger.info(f"Navegando para: {url_login}")
            self.page.goto(url_login)
            
            # WAIT ADAPTATIVO - Aguardar página de login carregar
            self.aguardar_elemento_visivel('#email, #username, input[type="email"]', timeout_ms=1000)
            
            # Pré-preencher credenciais
            logger.info("Preenchendo credenciais...")
            
            # Tentar diferentes seletores para email
            seletores_email = [
                'input[type="email"]',
                'input[name="email"]',
                'input[name="username"]',
                'input[placeholder*="mail" i]',
                '#email',
                '#username'
            ]
            
            for seletor in seletores_email:
                try:
                    if self.page.locator(seletor).count() > 0:
                        self.page.locator(seletor).first.fill(usuario)
                        logger.info(f"Email preenchido com seletor: {seletor}")
                        break
                except Exception:
                    continue
            
            # Tentar diferentes seletores para senha
            seletores_senha = [
                'input[type="password"]',
                'input[name="password"]',
                'input[name="senha"]',
                '#password'
            ]
            
            for seletor in seletores_senha:
                try:
                    if self.page.locator(seletor).count() > 0:
                        self.page.locator(seletor).first.fill(senha)
                        logger.info(f"Senha preenchida com seletor: {seletor}")
                        break
                except Exception:
                    continue
            
            print("\n✅ Credenciais preenchidas!")
            print("👉 Por favor, resolva o CAPTCHA e clique em ENTRAR\n")
            
            # Aguardar login com timeout de 5 minutos
            inicio = time.time()
            timeout_segundos = 300
            login_sucesso = False
            
            while time.time() - inicio < timeout_segundos:
                try:
                    # Verificar se saiu da página de login
                    url_atual = self.page.url
                    
                    if 'login' not in url_atual.lower():
                        # Verificar se chegou em página autenticada
                        if '/pedidos' in url_atual or '/dashboard' in url_atual:
                            logger.info("Login detectado!")
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
                    
                    time.sleep(2)
                    
                except Exception:
                    pass
            
            if login_sucesso:
                # Salvar sessão
                self.context.storage_state(path=self.storage_file)
                logger.info(f"Sessão salva em {self.storage_file}")
                print("\n✅ LOGIN REALIZADO COM SUCESSO!")
                print(f"📁 Sessão salva para uso futuro")
                print("="*60 + "\n")
                return True
            else:
                print("\n❌ Timeout - Login não foi completado em 5 minutos")
                return False
                
        except Exception as e:
            logger.error(f"Erro no login com CAPTCHA: {e}")
            print(f"\n❌ Erro: {e}")
            return False
    
    def verificar_login(self):
        """Verifica se esta logado no portal"""
        try:
            # Navegar para a pagina de pedidos
            url_pedidos = self.config['urls']['pedidos']  # https://atacadao.hodiebooking.com.br/pedidos
            self.page.goto(url_pedidos, wait_until='domcontentloaded')
            
            # Verificar indicadores de login do CONFIG
            usuario_logado = self.config['seletores']['usuario_logado']
            link_logout = self.config['seletores']['link_logout']
            
            # Se encontrar indicadores de usuario logado
            if self.page.locator(usuario_logado).is_visible() or self.page.locator(link_logout).is_visible():
                logger.info("Sessao valida - usuario logado")
                return True
            
            # Se estiver na pagina de login
            if "login" in self.page.url.lower() or self.page.locator("input[type='password']").is_visible():
                logger.warning("Nao esta logado - redirecionado para login")
                return False
            
            # Se conseguiu acessar a pagina de pedidos
            if "/pedidos" in self.page.url:
                logger.info("Acesso a pagina de pedidos - sessao valida")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar login: {e}")
            return False
    
    def _garantir_sessao(self):
        """Garante que a sessão está válida antes de operações POST"""
        # Se não tem página, criar uma
        if not self.page:
            logger.info("Nenhuma sessão ativa. Iniciando...")
            self.iniciar_sessao(salvar_login=False)
        
        # Verificar se está logado
        if not self.verificar_login():
            logger.info("Sessão inválida ou expirada. Tentando login interativo...")
            
            # Fechar sessão atual
            self.fechar()
            
            # Fazer login com CAPTCHA (usa credenciais do .env)
            if self.fazer_login_com_captcha():
                logger.info("Login realizado com sucesso. Reiniciando sessão...")
                # Reiniciar com a nova sessão salva
                self.iniciar_sessao(salvar_login=False)
                
                # Verificar se funcionou
                if self.verificar_login():
                    logger.info("Sessão válida estabelecida!")
                    return True
                else:
                    logger.error("Login ainda inválido após sucesso do CAPTCHA")
                    return False
            else:
                logger.error("Usuário não completou o login com CAPTCHA")
                return False
        
        # Sessão já válida
        return True
    
    def aguardar_com_retry(self, condicao_func, timeout_ms=5000, intervalo_ms=200, descricao="operação"):
        """
        Aguarda uma condição com retry rápido
        
        Args:
            condicao_func: Função que retorna True quando a condição é satisfeita
            timeout_ms: Timeout total em milissegundos (padrão 5000ms = 5s)
            intervalo_ms: Intervalo entre tentativas em ms (padrão 200ms)
            descricao: Descrição da operação para log
        
        Returns:
            True se a condição foi satisfeita, False se deu timeout
        """
        import time
        tempo_inicial = time.time()
        timeout_segundos = timeout_ms / 1000.0
        intervalo_segundos = intervalo_ms / 1000.0
        
        tentativa = 0
        while (time.time() - tempo_inicial) < timeout_segundos:
            tentativa += 1
            
            try:
                if condicao_func():
                    logger.info(f"✅ {descricao} - sucesso na tentativa {tentativa} após {(time.time() - tempo_inicial)*1000:.0f}ms")
                    return True
            except Exception as e:
                logger.debug(f"Tentativa {tentativa} falhou: {e}")
            
            # Aguardar intervalo antes da próxima tentativa
            time.sleep(intervalo_segundos)
        
        logger.warning(f"⚠️ {descricao} - timeout após {tentativa} tentativas em {timeout_ms}ms")
        return False
    
    def aguardar_com_retry_progressivo(self, condicao_func, timeout_ms=5000, 
                                       inicial_ms=300, max_intervalo_ms=1000, 
                                       descricao="operação"):
        """
        Aguarda com retry progressivo (backoff) - ADAPTATIVO À VELOCIDADE DO NAVEGADOR
        
        Args:
            condicao_func: Função que retorna True quando pronto
            timeout_ms: Timeout total (default 5000ms)
            inicial_ms: Intervalo inicial (default 300ms)
            max_intervalo_ms: Intervalo máximo (default 1000ms)
            descricao: Descrição para log
        
        Returns:
            True se sucesso, False se timeout
        """
        import time
        tempo_inicial = time.time()
        timeout_segundos = timeout_ms / 1000.0
        intervalo_atual_ms = inicial_ms
        tentativa = 0
        
        while (time.time() - tempo_inicial) < timeout_segundos:
            tentativa += 1
            tempo_decorrido_ms = (time.time() - tempo_inicial) * 1000
            
            try:
                if condicao_func():
                    logger.info(f"✅ {descricao} - sucesso na tentativa {tentativa} "
                              f"após {tempo_decorrido_ms:.0f}ms (economizou {timeout_ms - tempo_decorrido_ms:.0f}ms)")
                    return True
            except Exception as e:
                logger.debug(f"Tentativa {tentativa} ({tempo_decorrido_ms:.0f}ms): {e}")
            
            # Aguardar com backoff progressivo
            time.sleep(intervalo_atual_ms / 1000.0)
            
            # Aumentar intervalo progressivamente (até o máximo)
            intervalo_atual_ms = min(intervalo_atual_ms * 1.5, max_intervalo_ms)
        
        logger.warning(f"⚠️ {descricao} - timeout após {tentativa} tentativas "
                      f"em {(time.time() - tempo_inicial)*1000:.0f}ms")
        return False
    
    def aguardar_elemento_visivel(self, seletor, timeout_ms=3000):
        """
        Helper específico para aguardar elementos ficarem visíveis
        ADAPTATIVO - para assim que o elemento aparece
        """
        def elemento_visivel():
            try:
                return self.page.locator(seletor).is_visible()
            except Exception as e:
                logger.warning(f"Erro ao verificar elemento visível: {e}")
                return False
        
        return self.aguardar_com_retry_progressivo(
            elemento_visivel,
            timeout_ms=timeout_ms,
            inicial_ms=200,  # Check rápido a cada 200ms
            max_intervalo_ms=500,  # Máximo 500ms entre checks
            descricao=f"Elemento '{seletor}' ficar visível"
        )
    
    def _detectar_paginacao(self):
        """
        Detecta informações de paginação na página
        
        Returns:
            dict: {
                'tem_paginacao': bool,
                'pagina_atual': int,
                'total_paginas': int,
                'registro_inicio': int,
                'registro_fim': int,
                'total_registros': int
            }
        """
        try:
            info = {
                'tem_paginacao': False,
                'pagina_atual': 1,
                'total_paginas': 1,
                'registro_inicio': 0,
                'registro_fim': 0,
                'total_registros': 0
            }
            
            # Verificar se existe elemento de paginação
            paginacao = self.page.locator('.VuePagination__pagination, .pagination, nav.text-center')
            if paginacao.count() == 0:
                logger.info("Não há paginação na página")
                return info
            
            # Verificar texto de contagem de registros
            count_text = self.page.locator('.VuePagination__count, p:has-text("Registros")')
            if count_text.count() > 0:
                texto = count_text.first.text_content()
                logger.info(f"Texto de paginação encontrado: {texto}")
                
                # Extrair números do texto tipo "Registros 1 ao 20 de 35"
                import re
                numeros = re.findall(r'\d+', texto)
                if len(numeros) >= 3:
                    info['registro_inicio'] = int(numeros[0])
                    info['registro_fim'] = int(numeros[1])
                    info['total_registros'] = int(numeros[2])
                    
                    # Calcular total de páginas
                    registros_por_pagina = info['registro_fim'] - info['registro_inicio'] + 1
                    if registros_por_pagina > 0:
                        info['total_paginas'] = (info['total_registros'] + registros_por_pagina - 1) // registros_por_pagina
                    
                    info['tem_paginacao'] = info['total_paginas'] > 1
            
            # Detectar página atual
            pagina_ativa = self.page.locator('.pagination .active, .VuePagination__pagination-item.active')
            if pagina_ativa.count() > 0:
                texto_pagina = pagina_ativa.first.text_content()
                try:
                    info['pagina_atual'] = int(texto_pagina)
                except ValueError:
                    pass
            
            logger.info(f"📊 Paginação detectada: Página {info['pagina_atual']}/{info['total_paginas']}, "
                       f"Registros {info['registro_inicio']}-{info['registro_fim']} de {info['total_registros']}")
            
            return info
            
        except Exception as e:
            logger.error(f"Erro ao detectar paginação: {e}")
            return {
                'tem_paginacao': False,
                'pagina_atual': 1,
                'total_paginas': 1,
                'registro_inicio': 0,
                'registro_fim': 0,
                'total_registros': 0
            }
    
    def _navegar_proxima_pagina(self):
        """
        Navega para a próxima página se disponível
        
        Returns:
            bool: True se navegou com sucesso, False caso contrário
        """
        try:
            # Procurar botão de próxima página
            botao_proxima = self.page.locator('.VuePagination__pagination-item-next-page:not(.disabled) a')
            
            # Se não encontrar, tentar seletor alternativo
            if botao_proxima.count() == 0:
                botao_proxima = self.page.locator('li.page-item:has-text(">"):not(.disabled) a')
            
            if botao_proxima.count() == 0:
                logger.info("Não há próxima página disponível")
                return False
            
            # Verificar se o botão não está desabilitado
            parent_li = botao_proxima.locator('..')
            if parent_li.count() > 0:
                classes = parent_li.get_attribute('class') or ''
                if 'disabled' in classes:
                    logger.info("Botão de próxima página está desabilitado")
                    return False
            
            # Clicar no botão
            logger.info("📄 Navegando para a próxima página...")
            botao_proxima.first.click()
            
            # Aguardar a página carregar (usar wait adaptativo)
            def nova_pagina_carregada():
                try:
                    # Verificar se a tabela foi atualizada verificando se há produtos
                    return self.page.locator('table tbody tr').count() > 0
                except Exception:
                    return False
            
            carregou = self.aguardar_com_retry(
                nova_pagina_carregada,
                timeout_ms=3000,
                intervalo_ms=200,
                descricao="Nova página carregar"
            )
            
            if carregou:
                logger.info("✅ Navegou para a próxima página com sucesso")
                return True
            else:
                logger.warning("⚠️ Timeout aguardando nova página carregar")
                return False
            
        except Exception as e:
            logger.error(f"Erro ao navegar para próxima página: {e}")
            return False
    
    def _processar_produtos_pagina_atual(self, produtos_separacao):
        """
        Processa os produtos da página atual
        
        Args:
            produtos_separacao: dict com código do produto como chave e quantidade como valor
            
        Returns:
            dict: {'preenchidos': int, 'zerados': int, 'processados': list}
        """
        resultado = {
            'preenchidos': 0,
            'zerados': 0,
            'processados': []
        }
        
        try:
            # Preencher cada linha da tabela
            linhas_produtos = self.page.locator('table tbody tr').all()
            logger.info(f"📋 Processando {len(linhas_produtos)} produtos nesta página")
            
            for linha in linhas_produtos:
                try:
                    # Pegar código do produto (primeira coluna)
                    codigo = linha.locator('td').first.text_content().strip()
                    
                    # Campo de quantidade
                    campo_qtd = linha.locator('input[name*="qtd_alocada"]')
                    
                    if campo_qtd.count() > 0:
                        if codigo in produtos_separacao:
                            # Produto está na separação
                            qtd = produtos_separacao[codigo]
                            campo_qtd.fill(str(qtd))
                            logger.info(f"  ✅ Produto {codigo}: {qtd} unidades")
                            resultado['preenchidos'] += 1
                            resultado['processados'].append(codigo)
                        else:
                            # Produto NÃO está na separação - zerar
                            campo_qtd.fill('0')
                            logger.debug(f"  ❌ Produto {codigo}: 0 (não na separação)")
                            resultado['zerados'] += 1
                
                except Exception as e:
                    logger.warning(f"Erro ao processar linha do produto: {e}")
                    continue
            
            logger.info(f"📊 Página processada: {resultado['preenchidos']} preenchidos, {resultado['zerados']} zerados")
            
        except Exception as e:
            logger.error(f"Erro ao processar produtos da página: {e}")
        
        return resultado
    
    def _processar_produtos_todas_paginas(self, produtos_separacao):
        """
        Processa produtos em todas as páginas disponíveis
        
        Args:
            produtos_separacao: dict com código do produto como chave e quantidade como valor
            
        Returns:
            dict: Resumo do processamento
        """
        resumo = {
            'total_preenchidos': 0,
            'total_zerados': 0,
            'total_paginas': 0,
            'produtos_processados': []
        }
        
        try:
            # Detectar informações de paginação
            info_paginacao = self._detectar_paginacao()
            
            if not info_paginacao['tem_paginacao']:
                # Não tem paginação, processar apenas página atual
                logger.info("📄 Processando página única (sem paginação)")
                resultado = self._processar_produtos_pagina_atual(produtos_separacao)
                resumo['total_preenchidos'] = resultado['preenchidos']
                resumo['total_zerados'] = resultado['zerados']
                resumo['total_paginas'] = 1
                resumo['produtos_processados'] = resultado['processados']
            else:
                # Tem múltiplas páginas
                logger.info(f"📚 Detectadas {info_paginacao['total_paginas']} páginas de produtos")
                
                # Processar cada página
                pagina_atual = 1
                max_paginas = min(info_paginacao['total_paginas'], 10)  # Limitar a 10 páginas por segurança
                
                while pagina_atual <= max_paginas:
                    logger.info(f"\n🔄 PROCESSANDO PÁGINA {pagina_atual}/{info_paginacao['total_paginas']}")
                    
                    # Processar página atual
                    resultado = self._processar_produtos_pagina_atual(produtos_separacao)
                    resumo['total_preenchidos'] += resultado['preenchidos']
                    resumo['total_zerados'] += resultado['zerados']
                    resumo['produtos_processados'].extend(resultado['processados'])
                    
                    # Verificar se há próxima página
                    if pagina_atual < info_paginacao['total_paginas']:
                        # Navegar para próxima página
                        if self._navegar_proxima_pagina():
                            pagina_atual += 1
                            # Pequena pausa para garantir estabilidade
                            self.page.wait_for_timeout(500)
                        else:
                            logger.warning("Não foi possível navegar para a próxima página")
                            break
                    else:
                        break
                
                resumo['total_paginas'] = pagina_atual
                
                # Verificar se todos os produtos foram processados
                produtos_nao_encontrados = []
                for codigo in produtos_separacao.keys():
                    if codigo not in resumo['produtos_processados']:
                        produtos_nao_encontrados.append(codigo)
                
                if produtos_nao_encontrados:
                    logger.warning(f"⚠️ {len(produtos_nao_encontrados)} produtos da separação não foram encontrados nas páginas: {produtos_nao_encontrados[:5]}...")
                
        except Exception as e:
            logger.error(f"Erro ao processar produtos em múltiplas páginas: {e}")
            # Em caso de erro, tentar processar ao menos a página atual
            resultado = self._processar_produtos_pagina_atual(produtos_separacao)
            resumo['total_preenchidos'] = resultado['preenchidos']
            resumo['total_zerados'] = resultado['zerados']
            resumo['total_paginas'] = 1
            resumo['produtos_processados'] = resultado['processados']
        
        return resumo
    
    def _capturar_protocolo_apos_salvar(self, timeout_ms=5000):
        """Captura protocolo com retry rápido"""
        inicio = time.time()
        timeout_s = timeout_ms / 1000
        tentativa = 0
        
        while (time.time() - inicio) < timeout_s:
            tentativa += 1
            
            try:
                # Pequeno scroll para forçar renderização (100ms total)
                self.page.evaluate("window.scrollBy(0, 50)")
                self.page.wait_for_timeout(50)
                self.page.evaluate("window.scrollBy(0, -50)")
                self.page.wait_for_timeout(50)
                
                # Estratégia 1: Link "ACOMPANHE AGENDAMENTO" (mais rápido)
                links = self.page.locator('a[href*="/agendamentos/"]').all()
                for link in links[:3]:  # Verificar apenas os 3 primeiros
                    href = link.get_attribute('href')
                    if href and '/agendamentos/' in href:
                        protocolo = href.split('/agendamentos/')[-1].split('/')[0].split('?')[0]
                        if protocolo and protocolo.isdigit():
                            logger.info(f"✅ Protocolo capturado: {protocolo}")
                            return protocolo
                
                # Estratégia 2: URL atual
                if '/agendamentos/' in self.page.url:
                    protocolo = self.page.url.split('/agendamentos/')[-1].split('/')[0].split('?')[0]
                    if protocolo and protocolo.isdigit():
                        logger.info(f"✅ Protocolo da URL: {protocolo}")
                        return protocolo
                
            except Exception:
                pass
            
            # Aguardar 200ms antes da próxima tentativa
            self.page.wait_for_timeout(200)
        
        logger.warning(f"⚠️ Protocolo não capturado após {tentativa} tentativas")
        return None
    
    def _clicar_salvar(self):
        """Clica no botão Salvar - COM DIAGNÓSTICO DETALHADO"""
        
        logger.info("🔍 Analisando botões de salvar na página...")
        
        # 1. Verificar se o botão #salvar existe e suas propriedades
        botao_salvar = self.page.locator('#salvar')
        if botao_salvar.count() > 0:
            logger.info(f"✅ Botão #salvar encontrado!")
            
            # Verificar se está visível
            is_visible = botao_salvar.is_visible()
            logger.info(f"   - Visível: {is_visible}")
            
            # Verificar se está habilitado
            is_enabled = botao_salvar.is_enabled()
            logger.info(f"   - Habilitado: {is_enabled}")
            
            # Verificar classes
            classes = botao_salvar.get_attribute('class')
            logger.info(f"   - Classes: {classes}")
            
            # Verificar style
            style = botao_salvar.get_attribute('style')
            logger.info(f"   - Style: {style}")
            
            # Verificar se tem onclick
            onclick = botao_salvar.get_attribute('onclick')
            logger.info(f"   - OnClick: {onclick}")
            
            # Screenshot do botão antes de clicar
            if is_visible:
                try:
                    botao_salvar.screenshot(path=f"botao_salvar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    logger.info("   📸 Screenshot do botão salvo")
                except Exception:
                    pass
            
            # FORÇAR CLIQUE DE VÁRIAS FORMAS
            logger.info("🎯 Tentando clicar no botão Salvar...")
            
            # Método 1: Click normal com tratamento de navegação
            try:
                # Capturar URL antes do clique
                url_before = self.page.url
                logger.info(f"   URL antes: {url_before}")
                
                # Clicar e aguardar navegação ou timeout
                try:
                    with self.page.expect_navigation(wait_until="domcontentloaded", timeout=5000):
                        botao_salvar.click()
                        logger.info("   ✅ Click executado, aguardando navegação...")
                except Exception as e:
                    logger.warning(f"Erro ao clicar no botão salvar: {e}")
                    # Se não houve navegação, tentar outros métodos
                    logger.info("   ⚠️ Sem navegação detectada, verificando estado...")
                
                # Verificar URL após clique
                url_after = self.page.url
                logger.info(f"   URL depois: {url_after}")
                
                # Se mudou de página, sucesso
                if url_after != url_before:
                    logger.info("   ✅ Navegação detectada!")
                    return True
                    
                # Se ainda na mesma página, verificar se há modal de erro
                if self.page.locator('.modal.show, .alert-danger').count() > 0:
                    logger.warning("   ⚠️ Modal ou erro detectado")
                    return False
                    
                return True
                
            except Exception as e:
                logger.warning(f"   ⚠️ Click normal falhou: {e}")
                
                # Se o contexto foi destruído, significa que navegou (sucesso)
                if "context was destroyed" in str(e).lower() or "execution context" in str(e).lower():
                    logger.info("   ✅ Contexto destruído = navegação ocorreu (sucesso)")
                    return True
                
                # Método 2: Forçar com JavaScript se necessário
                try:
                    logger.info("   Tentando click via JavaScript...")
                    self.page.evaluate('document.querySelector("#salvar").click()')
                    # Aguardar pequeno tempo para processar
                    try:
                        self.page.wait_for_url("**/cargas/**", timeout=2000)
                        logger.info("   ✅ Click JavaScript funcionou")
                        return True
                    except Exception as e:
                        logger.warning(f"Erro ao aguardar URL: {e}")
                        pass
                except Exception as e2:
                    logger.warning(f"   ⚠️ Click JavaScript falhou: {e2}")
                
                return False
        
        # Se não encontrou #salvar, procurar alternativas
        logger.warning("❌ Botão #salvar não encontrado, procurando alternativas...")
        
        # Procurar TODOS os botões possíveis na página
        botoes_possiveis = self.page.locator('button, div.btn-panel, a.btn, input[type="submit"], div[onclick], button[onclick]').all()
        logger.info(f"Encontrados {len(botoes_possiveis)} elementos clicáveis")
        
        for idx, botao in enumerate(botoes_possiveis):
            try:
                text = botao.text_content() or ""
                if "salvar" in text.lower():
                    logger.info(f"   Botão {idx}: {text.strip()[:50]}")
                    
                    # Tentar clicar
                    if botao.is_visible():
                        botao.click()
                        logger.info(f"   ✅ Clicado no botão: {text.strip()}")
                        return True
            except Exception:
                continue
        
        logger.error("❌ Nenhum botão de salvar encontrado!")
        return False

    
    def buscar_pedido(self, numero_pedido):
        """Busca um pedido no portal"""
        try:
            # Navegar para pagina de pedidos
            self.page.goto(self.config['urls']['pedidos'], timeout=30000)
            # Aguardar DOM em vez de networkidle (pode travar em produção)
            try:
                self.page.wait_for_load_state('domcontentloaded', timeout=5000)
            except Exception as e:
                logger.warning(f"Erro ao aguardar DOM: {e}")
                pass  # Continuar mesmo se timeout
            
            # ABRIR FILTROS PRIMEIRO - IMPORTANTE!
            logger.info("Abrindo secao de filtros...")
            try:
                # O link correto tem data-target="#filtros-collapse"
                filtro_toggle = self.page.locator('a[data-toggle="collapse"][data-target="#filtros-collapse"]')
                if filtro_toggle.is_visible():
                    filtro_toggle.click()
                    logger.info("Clicando no toggle de filtros")
                    
                    # WAIT ADAPTATIVO - Aguardar campo de filtro ficar visível
                    campo_visivel = self.aguardar_elemento_visivel('#nr_pedido', timeout_ms=1000)
                    
                    if not campo_visivel:
                        # Tentar clicar novamente
                        logger.info("Campo ainda nao visivel, clicando novamente...")
                        filtro_toggle.click()
                        # WAIT ADAPTATIVO - Segunda tentativa
                        self.aguardar_elemento_visivel('#nr_pedido', timeout_ms=1000)
                        
            except Exception as e:
                logger.warning(f"Erro ao abrir filtros: {e}")
                # Continuar, pode ja estar aberto
            
            # CORREÇÃO: Limpar APENAS o botão específico do campo dthr_elaboracao
            logger.info("Limpando filtro de data de elaboração...")
            try:
                # Usar seletor ESPECÍFICO com DOIS atributos para garantir elemento correto
                botao_limpar_especifico = self.page.locator(
                    'button[data-target_daterangepicker="dthr_elaboracao"][data-action="remove"]'
                )
                
                if botao_limpar_especifico.count() > 0:
                    try:
                        # Aguardar estar visível com timeout curto
                        botao_limpar_especifico.wait_for(state="visible", timeout=2000)
                        botao_limpar_especifico.click()
                        self.page.wait_for_timeout(300)  # Pausa mínima após clique
                        logger.info("✅ Filtro dthr_elaboracao limpo com sucesso")
                    except Exception as e:
                        logger.debug(f"Botão não ficou visível no tempo esperado: {e}")
                else:
                    logger.debug("Botão de limpar dthr_elaboracao não encontrado, continuando...")
            except Exception as e:
                logger.warning(f"Erro ao limpar filtro de data: {e} - continuando sem limpar")
                pass
            
            # Verificar se o campo esta visivel apos abrir filtros
            campo_pedido = self.config['seletores']['campo_pedido']  # #nr_pedido
            
            # Se o campo nao estiver visivel, tentar abrir filtros novamente
            if not self.page.locator(campo_pedido).is_visible():
                logger.warning("Campo de pedido nao visivel, tentando abrir filtros novamente...")
                try:
                    # Forcar clique no primeiro elemento que pareca ser o toggle
                    self.page.locator('a[data-toggle="collapse"]').first.click()
                    # WAIT ADAPTATIVO - Aguardar filtros abrirem
                    self.aguardar_elemento_visivel(campo_pedido, timeout_ms=1000)
                except Exception as e:
                    logger.error(f"Erro ao abrir filtros novamente: {e}")
                    pass
            
            # Preencher campo de busca
            logger.info(f"Preenchendo campo {campo_pedido} com {numero_pedido}")
            self.page.wait_for_selector(campo_pedido, timeout=5000, state='visible')
            # Limpar campo antes de preencher
            self.page.fill(campo_pedido, '')
            self.page.wait_for_timeout(200)
            self.page.fill(campo_pedido, numero_pedido)
            
            # Clicar em filtrar
            botao_filtrar = self.config['seletores']['botao_filtrar']  # #enviarFiltros
            logger.info(f"Clicando em filtrar: {botao_filtrar}")
            self.page.wait_for_selector(botao_filtrar, timeout=5000)
            self.page.click(botao_filtrar)
            
            # Aguardar resultado COM RETRY RÁPIDO
            logger.info("Aguardando resultado da busca...")
            
            # Usar retry rápido - verificar a cada 200ms por até 5 segundos
            def tem_resultados():
                linhas = self.page.locator('table tbody tr').count()
                if linhas > 0:
                    # Verificar se tem o pedido específico
                    todas_linhas = self.page.locator('table tbody tr').all()
                    for linha in todas_linhas:
                        colunas = linha.locator('td').all()
                        if len(colunas) >= 2:
                            # Segunda coluna é "N° pedido original"
                            pedido_original = colunas[1].text_content().strip()
                            if pedido_original == numero_pedido:
                                return True
                return False
            
            pedido_encontrado = self.aguardar_com_retry(
                tem_resultados, 
                timeout_ms=5000, 
                intervalo_ms=200, 
                descricao=f"Busca do pedido {numero_pedido}"
            )
            
            if not pedido_encontrado:
                # Se não encontrou com retry rápido, tentar mais uma vez clicando em filtrar novamente
                logger.info("Pedido não encontrado no primeiro retry, tentando novamente...")
                self.page.click(botao_filtrar)
                
                pedido_encontrado = self.aguardar_com_retry(
                    tem_resultados, 
                    timeout_ms=3000, 
                    intervalo_ms=200, 
                    descricao=f"Segunda tentativa - pedido {numero_pedido}"
                )
                
            
            if pedido_encontrado:
                # Pedido encontrado, agora abrir ele
                linhas = self.page.locator('table tbody tr').all()
                for linha in linhas:
                    colunas = linha.locator('td').all()
                    if len(colunas) >= 2:
                        pedido_original = colunas[1].text_content().strip()
                        if pedido_original == numero_pedido:
                            # Clicar no link desta linha
                            link_exibir = linha.locator('a[title="Exibir"]')
                            if link_exibir.count() > 0:
                                link_exibir.click()
                                logger.info(f"Pedido {numero_pedido} aberto com sucesso")
                                # Aguardar DOM em vez de networkidle (pode travar em produção)
                                try:
                                    self.page.wait_for_load_state('domcontentloaded', timeout=5000)
                                except Exception as e:
                                    pass  # Continuar mesmo se timeout
                                    return True
                            break  # Sair do loop após encontrar o pedido
            else:
                # Não encontrou o pedido
                logger.warning(f"Pedido {numero_pedido} não encontrado na busca")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao buscar pedido: {e}")
            return False
    
    def criar_agendamento(self, dados):
        """Cria um agendamento no portal seguindo o fluxo real"""
        try:
            # GARANTIR SESSÃO VÁLIDA (com login automático se necessário)
            if not self._garantir_sessao():
                return {
                    'success': False,
                    'message': 'Não foi possível estabelecer sessão válida.'
                }
            
            # 1. Verificar login (já deve estar válido após _garantir_sessao)
            if not self.verificar_login():
                logger.error("Sessão ainda inválida após tentativa de login")
                return {
                    'success': False,
                    'message': 'Não foi possível fazer login. Verifique as credenciais no .env'
                }
            
            # 2. Buscar o pedido
            pedido_cliente = dados.get('pedido_cliente')
            if not pedido_cliente:
                return {
                    'success': False,
                    'message': 'Numero do pedido nao fornecido'
                }
            
            logger.info(f"Buscando pedido {pedido_cliente}...")
            # Usar método robusto que busca na coluna correta
            if not self.buscar_pedido_robusto(pedido_cliente):
                return {
                    'success': False,
                    'message': f'Pedido {pedido_cliente} nao encontrado no portal'
                }
            
            # 3. Solicitar agendamento
            # DIAGNÓSTICO: Verificar URL antes de clicar
            url_antes = self.page.url
            logger.info(f"📍 URL ANTES de solicitar: {url_antes}")
            
            # Screenshot antes
            self.page.screenshot(path=f"antes_solicitar_{pedido_cliente}.png")
            
            botao_solicitar = self.config['seletores']['botao_solicitar_agendamento']
            self.page.wait_for_selector(botao_solicitar)
            self.page.click(botao_solicitar)
            
            # WAIT ADAPTATIVO - Para assim que o formulário abrir
            logger.info("⏳ Aguardando formulário abrir (adaptativo até 3s)...")
            
            # Aguardar campo de data ficar visível (indica que formulário abriu)
            formulario_aberto = self.aguardar_elemento_visivel(
                'input[name="data_desejada"]', 
                timeout_ms=3000  # Mesmo timeout de antes, mas adaptativo
            )
            
            if not formulario_aberto:
                # Fallback: tentar aguardar qualquer campo do formulário
                logger.warning("Campo data_desejada não encontrado, tentando alternativas...")
                formulario_aberto = self.aguardar_elemento_visivel(
                    '#leadtime_minimo, input[name="leadtime_minimo"]',
                    timeout_ms=2000
                )
            
            logger.info("Formulario de agendamento aberto")
            # REMOVIDO wait_for_load_state('networkidle') - pode travar em produção
            # Aguardar apenas o DOM estar pronto
            try:
                self.page.wait_for_load_state('domcontentloaded', timeout=3000)
            except Exception as e:
                logger.warning(f"Erro ao aguardar DOM: {e}")
                logger.warning("Timeout aguardando DOM, continuando...")
            
            # DIAGNÓSTICO: Verificar URL depois
            url_depois = self.page.url
            logger.info(f"📍 URL DEPOIS de solicitar: {url_depois}")
            
            # Screenshot depois
            self.page.screenshot(path=f"depois_solicitar_{pedido_cliente}.png")
            
            # 4. Preencher formulario
            
            # 4.1 PRIMEIRA DATA: Data desejada de agendamento (IGUAL AO SCRIPT QUE FUNCIONA)
            if dados.get('data_agendamento'):
                data_agendamento = dados['data_agendamento']
                # Garantir formato DD/MM/AAAA
                if isinstance(data_agendamento, (datetime, date)):
                    data_agendamento = data_agendamento.strftime('%d/%m/%Y')
                
                # Converter para ISO também (como no script que funciona)
                data_iso = ""
                if data_agendamento and '/' in data_agendamento:
                    partes = data_agendamento.split('/')
                    if len(partes) == 3:
                        data_iso = f"{partes[2]}-{partes[1]}-{partes[0]}"  # YYYY-MM-DD
                    else:
                        logger.warning(f"Formato de data inválido: {data_agendamento}")
                        # Tentar usar a data como está
                        data_iso = data_agendamento
                else:
                    # CONVERTER DATA ISO PARA FORMATO BR
                    if data_agendamento and '-' in str(data_agendamento):
                        # Formato ISO (YYYY-MM-DD) para BR (DD/MM/YYYY)
                        try:
                            partes_iso = str(data_agendamento).split('-')
                            if len(partes_iso) == 3:
                                data_iso = data_agendamento  # Manter ISO original
                                data_agendamento = f"{partes_iso[2]}/{partes_iso[1]}/{partes_iso[0]}"  # Converter para BR
                                logger.info(f"Data convertida de ISO para BR: {data_iso} → {data_agendamento}")
                            else:
                                logger.warning(f"Formato de data ISO inválido: {data_agendamento}")
                                data_iso = data_agendamento or ""
                        except Exception as e:
                            logger.error(f"Erro ao converter data: {e}")
                            data_iso = data_agendamento or ""
                    else:
                        logger.warning(f"Data sem formato DD/MM/AAAA: {data_agendamento}")
                        data_iso = data_agendamento or ""
                
                logger.info(f"Preenchendo data desejada: {data_agendamento}")
                
                # Verificar campos
                campo_data_iso = self.page.locator('input[name="data_desejada_iso"]')
                campo_data_visivel = self.page.locator('input[name="data_desejada"]')
                
                try:
                    # Método 1: Clicar e digitar (IGUAL ao script que funciona)
                    if campo_data_visivel.count() > 0:
                        logger.info("   Clicando no campo de data desejada...")
                        campo_data_visivel.click()
                        self.page.wait_for_timeout(200)  # Reduzido para otimizar interação
                        
                        # Limpar campo usando Ctrl+A e Delete
                        self.page.keyboard.press('Control+A')
                        self.page.keyboard.press('Delete')
                        self.page.wait_for_timeout(200)  # Reduzido para otimizar interação
                        
                        # Digitar a data
                        logger.info(f"   Digitando data: {data_agendamento}")
                        self.page.keyboard.type(data_agendamento)
                        
                        # VERIFICAR se a data foi digitada corretamente
                        def data_foi_digitada():
                            try:
                                valor_atual = campo_data_visivel.input_value()
                                return valor_atual == data_agendamento
                            except Exception as e:
                                logger.warning(f"Erro ao verificar data: {e}")
                                return False
                        
                        # Aguardar confirmação que digitou
                        digitou_ok = self.aguardar_com_retry(
                            data_foi_digitada,
                            timeout_ms=1000,
                            intervalo_ms=100,
                            descricao="Data ser digitada corretamente"
                        )
                        
                        if digitou_ok:
                            # Sair do campo
                            self.page.keyboard.press('Tab')
                            logger.info(f"   ✅ Data confirmada: {data_agendamento}")
                        else:
                            # Fallback: wait fixo mínimo
                            self.page.wait_for_timeout(300)
                            self.page.keyboard.press('Tab')
                            logger.info(f"   ⚠️ Data digitada (sem confirmação): {data_agendamento}")
                    
                    # Método 2: Se houver campo ISO, preencher também (IGUAL ao script)
                    if campo_data_iso.count() > 0:
                        self.page.evaluate(f'document.querySelector(\'input[name="data_desejada_iso"]\').value = "{data_iso}"')
                        self.page.evaluate(f'document.querySelector(\'input[name="data_desejada"]\').value = "{data_agendamento}"')
                        logger.info(f"   ✅ Data desejada preenchida via JavaScript: {data_agendamento}")
                        
                except Exception as e:
                    logger.warning(f"   ⚠️ Erro ao preencher data desejada: {e}")
                    
                    # Método 3: Forçar via JavaScript (fallback)
                    logger.info("   Tentando método alternativo...")
                    script = f"""
                        var campo = document.querySelector('input[name="data_desejada"]');
                        if (campo) {{
                            campo.value = '{data_agendamento}';
                            campo.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            campo.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                        var campoIso = document.querySelector('input[name="data_desejada_iso"]');
                        if (campoIso) {{
                            campoIso.value = '{data_iso}';
                        }}
                    """
                    self.page.evaluate(script)
                    logger.info(f"   ✅ Data desejada forçada via JavaScript: {data_agendamento}")
                
                # 4.2 SEGUNDA DATA: Disponibilidade de entrega (leadtime_minimo)
                logger.info(f"Preenchendo disponibilidade de entrega: {data_agendamento}")
                
                campo_leadtime = self.page.locator('input[name="leadtime_minimo"]')
                campo_leadtime_iso = self.page.locator('input[name="leadtime_minimo_iso"]')
                
                if campo_leadtime.count() > 0:
                    try:
                        # Método 1: Clicar e digitar
                        logger.info("   Clicando no campo de disponibilidade de entrega...")
                        campo_leadtime.click()
                        self.page.wait_for_timeout(200)  # Reduzido para otimizar interação
                        
                        # Limpar e digitar
                        self.page.keyboard.press('Control+A')
                        self.page.keyboard.press('Delete')
                        self.page.wait_for_timeout(200)  # Reduzido para otimizar interação
                        
                        logger.info(f"   Digitando data: {data_agendamento}")
                        self.page.keyboard.type(data_agendamento)
                        
                        # VERIFICAR se a data foi digitada corretamente
                        def leadtime_foi_digitado():
                            try:
                                valor_atual = campo_leadtime.input_value()
                                return valor_atual == data_agendamento
                            except Exception as e:
                                logger.warning(f"Erro ao verificar leadtime: {e}")
                                return False
                        
                        # Aguardar confirmação que digitou
                        digitou_ok = self.aguardar_com_retry(
                            leadtime_foi_digitado,
                            timeout_ms=1000,
                            intervalo_ms=100,
                            descricao="Leadtime ser digitado corretamente"
                        )
                        
                        if digitou_ok:
                            # Sair do campo
                            self.page.keyboard.press('Tab')
                            logger.info(f"   ✅ Disponibilidade confirmada: {data_agendamento}")
                        else:
                            # Fallback: wait fixo mínimo
                            self.page.wait_for_timeout(300)
                            self.page.keyboard.press('Tab')
                            logger.info(f"   ⚠️ Disponibilidade digitada (sem confirmação): {data_agendamento}")
                        
                        # Preencher campo ISO também
                        if campo_leadtime_iso.count() > 0:
                            self.page.evaluate(f'document.querySelector(\'input[name="leadtime_minimo_iso"]\').value = "{data_iso}"')
                            self.page.evaluate(f'document.querySelector(\'input[name="leadtime_minimo"]\').value = "{data_agendamento}"')
                            
                    except Exception as e:
                        logger.warning(f"   ⚠️ Erro ao preencher disponibilidade: {e}")
                        # Forçar via JavaScript
                        script = f"""
                            var campo = document.querySelector('input[name="leadtime_minimo"]');
                            if (campo) {{
                                campo.value = '{data_agendamento}';
                                campo.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                            var campoIso = document.querySelector('input[name="leadtime_minimo_iso"]');
                            if (campoIso) {{
                                campoIso.value = '{data_iso}';
                            }}
                        """
                        self.page.evaluate(script)
                        logger.info(f"   ✅ Disponibilidade forçada via JavaScript: {data_agendamento}")
                else:
                    logger.warning("   ⚠️ Campo leadtime_minimo não encontrado")
            
            # 4.3 Transportadora (usar padrao Agregado)
            # Primeiro verificar se transportadora já está preenchida
            campo_transportadora = self.page.locator('#id_transportadora, #transportadora')
            transportadora_preenchida = False
            
            try:
                valor_transportadora = campo_transportadora.input_value() if campo_transportadora.count() > 0 else ""
                transportadora_preenchida = valor_transportadora != "" and valor_transportadora != "0"
            except Exception as e:
                logger.warning(f"Erro ao verificar transportadora: {e}")
                pass
            
            if not transportadora_preenchida and self.page.locator(self.config['seletores']['botao_buscar_transportadora']).is_visible():
                logger.info("Selecionando transportadora...")
                self.page.click(self.config['seletores']['botao_buscar_transportadora'])
                
                # WAIT MAIS ROBUSTO - Aguardar modal estar COMPLETAMENTE aberto
                # Não só visível, mas também interativo
                def modal_pronto():
                    try:
                        # Modal deve estar visível
                        modal_visivel = self.page.locator('.modal.show, .modal.in, #modal-transportadoras').is_visible()
                        # Radio button deve estar visível e clicável
                        radio_visivel = self.page.locator('input[type="radio"][id="1"], input[type="radio"][value*="Agregado"]').is_visible()
                        # Botão selecionar deve existir
                        botao_existe = self.page.locator('.modal-footer button.selecionar').count() > 0
                        
                        return modal_visivel and radio_visivel and botao_existe
                    except Exception as e:
                        logger.warning(f"Erro ao verificar modal: {e}")
                        return False
                
                modal_aberto = self.aguardar_com_retry_progressivo(
                    modal_pronto,
                    timeout_ms=2000,  # Aumentado para 2s
                    inicial_ms=300,
                    max_intervalo_ms=500,
                    descricao="Modal de transportadora abrir completamente"
                )
                
                if modal_aberto:
                    # Aguardar um pouco mais para garantir que animação terminou
                    self.page.wait_for_timeout(300)  # Wait mínimo de segurança
                    
                    # Selecionar Agregado
                    radio_agregado = self.page.locator('input[type="radio"][id="1"]')
                    if radio_agregado.count() > 0:
                        radio_agregado.click()
                        
                        # VERIFICAR se radio foi marcado
                        def radio_marcado():
                            try:
                                return radio_agregado.is_checked()
                            except Exception as e:
                                logger.warning(f"Erro ao verificar radio: {e}")
                                return False
                        
                        self.aguardar_com_retry(
                            radio_marcado,
                            timeout_ms=1000,
                            intervalo_ms=100,
                            descricao="Radio button Agregado ser marcado"
                        )
                    
                    # IMPORTANTE: Clicar no botao Selecionar do modal-footer
                    botao_selecionar = self.page.locator('.modal-footer button.btn-primary.selecionar')
                    if botao_selecionar.count() > 0:
                        if botao_selecionar.count() > 1:
                            # Se houver mais de um, pegar o visivel
                            for i in range(botao_selecionar.count()):
                                if botao_selecionar.nth(i).is_visible():
                                    botao_selecionar.nth(i).click()
                                    break
                        else:
                            botao_selecionar.click()
                        
                        logger.info(" Transportadora Agregado selecionada")
                        
                        # Aguardar um momento para o JavaScript processar
                        self.page.wait_for_timeout(200)
                        
                        # VERIFICAR se transportadora foi preenchida no formulário
                        def transportadora_foi_preenchida():
                            try:
                                valor = self.page.locator('#id_transportadora, #transportadora').input_value()
                                # Verificar se tem valor e não é "0" ou vazio
                                return valor != "" and valor != "0"
                            except Exception as e:
                                logger.warning(f"Erro ao verificar transportadora: {e}")
                                return False
                        
                        preencheu = self.aguardar_com_retry_progressivo(
                            transportadora_foi_preenchida,
                            timeout_ms=2000,
                            inicial_ms=200,
                            max_intervalo_ms=500,
                            descricao="Campo transportadora ser preenchido"
                        )
                        
                        if preencheu:
                            logger.info("✅ Transportadora confirmada no formulário")
                        else:
                            logger.warning("⚠️ Transportadora pode não ter sido preenchida corretamente")
                else:
                    logger.warning("⚠️ Modal de transportadora não abriu corretamente")
            elif transportadora_preenchida:
                logger.info(f"✅ Transportadora já preenchida: {valor_transportadora}")
            
            # 4.4 Tipo de carga (pode estar desabilitado)
            logger.info("Verificando tipo de carga...")
            select_carga = self.page.locator('select[name="carga_especie_id"]')
            if select_carga.count() > 0:
                is_disabled = select_carga.get_attribute('disabled')
                if is_disabled is None or is_disabled == "false":
                    select_carga.select_option(value='1')  # Paletizada
                    logger.info(" Tipo de carga: Paletizada")
                else:
                    logger.info("⚠️ Tipo de carga ja definido (campo desabilitado)")
            
            # 4.5 Tipo de veiculo - Determinar automaticamente pelo peso
            peso_total = dados.get('peso_total', 0)
            
            # Se não foi fornecido tipo_veiculo ou peso_total, usar o método para determinar
            if peso_total and not dados.get('tipo_veiculo_manual'):
                tipo_veiculo = self.determinar_tipo_veiculo_por_peso(peso_total)
            else:
                tipo_veiculo = dados.get('tipo_veiculo', '11')  # Default: Toco-Bau se não tiver peso
            
            logger.info(f"Selecionando tipo de veiculo: {tipo_veiculo}")
            select_veiculo = self.page.locator('select[name="tipo_veiculo"]')
            if select_veiculo.count() > 0:
                try:
                    select_veiculo.select_option(value=tipo_veiculo)
                    logger.info(f"✅ Tipo de veiculo selecionado: ID {tipo_veiculo}")
                except Exception as e:
                    logger.warning(f"Erro ao selecionar veiculo: {e}")
            
            # 4.6 Preencher quantidades dos produtos em TODAS AS PÁGINAS
            logger.info("Preenchendo quantidades dos produtos...")
            
            # Criar mapa de produtos da separação
            produtos_separacao = {}
            if dados.get('produtos'):
                for produto in dados['produtos']:
                    codigo = str(produto.get('codigo'))
                    quantidade = produto.get('quantidade', 0)
                    produtos_separacao[codigo] = int(quantidade)
                logger.info(f"📦 Total de produtos na separação: {len(produtos_separacao)}")
            
            # NOVO: Processar produtos em todas as páginas
            produtos_processados = self._processar_produtos_todas_paginas(produtos_separacao)
            
            # Log final
            logger.info(f"✅ RESUMO: {produtos_processados['total_preenchidos']} produtos preenchidos, "
                       f"{produtos_processados['total_zerados']} zerados em {produtos_processados['total_paginas']} página(s)")
            
            # 5. NÃO MEXER NO MODO DE EDIÇÃO (como o script que funciona)
            # REMOVIDO: window.f_editando = true (estava quebrando o formulário)
            # REMOVIDO: checkbox agendar_depois (script funcional não mexe nisso)
            
            # 6. DIAGNÓSTICO: Verificar campos hidden e valores do formulário
            logger.info("🔍 Verificando campos do formulário antes de salvar...")
            
            # Verificar se há campos hidden com ID do pedido
            campos_pedido = self.page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input[name*="pedido"], input[name*="id_pedido"], input[type="hidden"]');
                    const valores = {};
                    inputs.forEach(input => {
                        valores[input.name || input.id] = input.value;
                    });
                    return valores;
                }
            """)
            logger.info(f"📋 Campos do formulário: {campos_pedido}")
            
            # WAIT INTELIGENTE DE ESTABILIZAÇÃO - Adaptativo
            # Verifica se formulário está pronto em vez de esperar tempo fixo
            logger.info("⏳ Aguardando formulário estabilizar (adaptativo)...")
            
            def formulario_pronto_para_salvar():
                """Verifica se formulário está pronto para salvar"""
                try:
                    # Verificar se campos críticos estão preenchidos
                    data_ok = self.page.locator('input[name="data_desejada"]').input_value() != ''
                    transp_ok = self.page.locator('#id_transportadora').input_value() != ''
                    
                    # Verificar se não há erros visíveis
                    tem_erro = self.page.locator('.has-error, .erro, .invalid').count() > 0
                    
                    # Verificar se botão salvar está habilitado
                    botao_habilitado = self.page.locator('#salvar').is_enabled()
                    
                    return data_ok and transp_ok and not tem_erro and botao_habilitado
                except Exception as e:
                    logger.warning(f"Erro ao verificar formulário: {e}")
                    return False
            
            # Primeiro wait curto para casos rápidos
            self.page.wait_for_timeout(300)  # 300ms mínimo de segurança
            
            # Depois verificar se está pronto com retry progressivo
            formulario_estavel = self.aguardar_com_retry_progressivo(
                formulario_pronto_para_salvar,
                timeout_ms=4700,  # 300ms + 4700ms = 5000ms total máximo
                inicial_ms=400,
                max_intervalo_ms=800,
                descricao="Formulário estabilizar e ficar pronto"
            )
            
            if not formulario_estavel:
                logger.warning("⚠️ Formulário pode não estar completamente estável")
                # Wait adicional de segurança se não estabilizou
                self.page.wait_for_timeout(500)
            
            # Screenshot antes de salvar
            self.page.screenshot(path=f"agendamento_{datetime.now().strftime('%Y%m%d_%H%M%S')}_antes.png")
            
            logger.info("🎯 Salvando formulário...")
            
            # Clicar em Salvar (método simples que funciona)
            if not self._clicar_salvar():
                logger.error("❌ Não conseguiu clicar no botão Salvar")
                return {'success': False, 'message': 'Impossível clicar no botão Salvar'}
            
            # AGUARDAR RESPOSTA COM RETRY RÁPIDO
            logger.info("Aguardando resposta...")
            
            # Aguardar redirecionamento ou modal com retry rápido (max 3 segundos)
            for i in range(4):  # 15 x 200ms = 3 segundos
                self.page.wait_for_timeout(500)
                
                # Verificar se mudou de URL
                if "/cargas/" in self.page.url or "/agendamentos/" in self.page.url:
                    logger.info("✅ Redirecionamento detectado!")
                    break
                    
                # Verificar modal de sucesso
                if self.page.locator('#regSucesso').count() > 0:
                    logger.info("✅ Modal de sucesso detectado!")
                    
                    # Clicar em "Não incluir NF agora" rapidamente
                    if self.page.locator('#btnNao').count() > 0:
                        try:
                            self.page.locator('#btnNao').click(timeout=200)
                            logger.info("Optou por não incluir NF agora")
                        except Exception as e:
                            logger.warning(f"Erro ao clicar em #btnNao: {e}")
                            pass
                    self.page.wait_for_timeout(200)
                    break
                
            # VERIFICAR REDIRECIONAMENTO (copiado do script original - linhas 551-570)
            current_url = self.page.url
            logger.info(f"URL atual: {current_url}")
            
            # Verificar se redirecionou para /cargas/ ou /agendamentos/
            if "/cargas/" in current_url or "/agendamentos/" in current_url:
                logger.info("✅ Redirecionou após salvar!")
            
            # CAPTURAR PROTOCOLO (método do script original - linhas 541-570)
            logger.info("Capturando protocolo...")
            protocolo = None
            
            # Verificar URL atual
            if "/agendamentos/" in current_url:
                # Extrair o protocolo da URL (linha 556 do script original)
                protocolo = current_url.split("/agendamentos/")[-1].split("/")[0].split("?")[0]
                logger.info(f"✅ Protocolo extraído da URL: {protocolo}")
            elif "/cargas/" in current_url:
                # Se voltou para a página da carga, procurar o link do agendamento (linha 561-569)
                logger.info("Página redirecionou para carga, procurando link do agendamento...")
                link_acompanhe = self.page.locator('a[href*="/agendamentos/"]:has-text("ACOMPANHE")')
                if link_acompanhe.count() == 0:
                    link_acompanhe = self.page.locator('a[href*="/agendamentos/"]').first
                
                if link_acompanhe.count() > 0:
                    href = link_acompanhe.get_attribute('href')
                    if href and "/agendamentos/" in href:
                        protocolo = href.split("/agendamentos/")[-1].split("/")[0].split("?")[0]
                        logger.info(f"✅ Protocolo extraído do link: {protocolo}")
            
            # Se não encontrou, usar método robusto
            if not protocolo:
                protocolo = self._capturar_protocolo_apos_salvar(timeout_ms=20000)
            
            
            # Retornar resultado
            if protocolo:
                # Screenshot de sucesso
                self.page.screenshot(path=f"sucesso_agendamento_{protocolo}.png")
                logger.info(f"✅✅✅ AGENDAMENTO CRIADO COM SUCESSO! Protocolo: {protocolo}")
                
                return {
                    'success': True,
                    'protocolo': protocolo.strip() if isinstance(protocolo, str) else protocolo,
                    'message': f'Agendamento realizado com sucesso! Protocolo: {protocolo}',
                    'url': self.page.url
                }
            else:
                # Tentar capturar informações adicionais para debug
                logger.warning("⚠️ Protocolo não capturado, verificando se agendamento foi criado...")
                
                # Screenshot detalhado para debug
                screenshot_path = f"agendamento_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"Screenshot salvo: {screenshot_path}")
                
                # Verificar se está na página de carga com número de carga
                numero_carga = None
                try:
                    # Procurar número da carga de várias formas
                    seletores_carga = [
                        '.box-numero-carga .valor',
                        '[class*="numero-carga"]',
                        'span:has-text("Carga:")',
                        'div:has-text("Número da Carga")'
                    ]
                    
                    for seletor in seletores_carga:
                        element = self.page.locator(seletor)
                        if element.count() > 0:
                            texto = element.first.text_content()
                            # Extrair apenas números
                            import re
                            numeros = re.findall(r'\d+', texto)
                            if numeros:
                                numero_carga = numeros[0]
                                logger.info(f"Número da carga encontrado: {numero_carga}")
                                break
                except Exception as e:
                    logger.debug(f"Erro ao buscar número da carga: {e}")
                
                # Verificar se há mensagem de sucesso na página (sem logar HTML inteiro)
                mensagem_sucesso = None
                try:
                    seletores_sucesso = [
                        '.alert-success',
                        '.success-message',
                        '.modal-body:has-text("agendamento realizado")'
                    ]
                    
                    for seletor in seletores_sucesso:
                        element = self.page.locator(seletor)
                        if element.count() > 0:
                            # Limitar o texto capturado para evitar poluir logs
                            texto = element.first.text_content().strip()
                            if texto and len(texto) < 200:  # Só logar se for mensagem curta
                                mensagem_sucesso = texto
                                logger.info(f"Mensagem de sucesso encontrada (tamanho: {len(texto)} chars)")
                            break
                except Exception as e:
                    logger.debug(f"Nenhuma mensagem de sucesso específica encontrada")
                    pass
                
                # Verificar se URL indica sucesso
                current_url = self.page.url
                url_sucesso = "/cargas/" in current_url or "/agendamentos/" in current_url
                
                # Se tem número de carga ou mensagem de sucesso ou URL de sucesso
                if numero_carga or mensagem_sucesso or url_sucesso:
                    return {
                        'success': True,
                        'protocolo': None,
                        'message': f'Agendamento aparentemente criado mas protocolo não capturado. '
                                   f'{"Carga: " + numero_carga if numero_carga else ""} '
                                   f'Verifique manualmente no portal.',
                        'url': current_url,
                        'numero_carga': numero_carga,
                        'screenshot': screenshot_path
                    }
                else:
                    # Capturar informações mínimas para debug (sem HTML)
                    page_title = self.page.title()
                    
                    return {
                        'success': False,
                        'message': f'Não foi possível confirmar se o agendamento foi criado. '
                                   f'Título da página: {page_title}. '
                                   f'Verifique o screenshot: {screenshot_path}',
                        'url': current_url,
                        'screenshot': screenshot_path
                    }
                
        except Exception as e:
            logger.error(f"Erro ao criar agendamento: {e}")
            if self.page:
                self.page.screenshot(path=f"erro_geral_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            return {
                'success': False,
                'message': f'Erro: {str(e)}'
            }
    
    def criar_agendamento_completo(self, pedido_numero, data_agendamento, produtos=None):
        """
        Metodo robusto para criar agendamento baseado no script de teste bem-sucedido
        
        Args:
            pedido_numero: Numero do pedido (ex: '932955')
            data_agendamento: Data no formato DD/MM/YYYY (ex: '27/08/2025')
            produtos: Lista de dicionarios com 'codigo' e 'quantidade'
        """
        try:
            logger.info(f"\nINICIANDO AGENDAMENTO DO PEDIDO {pedido_numero}")
            logger.info("=" * 60)
            
            # 1. Verificar login
            if not self.verificar_login():
                return {
                    'success': False,
                    'message': 'Sessao expirada. Execute: python configurar_sessao_atacadao.py'
                }
            
            # 2. Buscar pedido com metodo robusto
            logger.info(f"Buscando pedido {pedido_numero}...")
            if not self.buscar_pedido_robusto(pedido_numero):
                return {
                    'success': False,
                    'message': f'Pedido {pedido_numero} nao encontrado apos multiplas tentativas'
                }
            
            # 3. Clicar no botao de solicitar agendamento
            logger.info("Procurando botao de agendamento...")
            botoes_agendamento = [
                '.btn_solicitar_agendamento',
                '.btn-panel.btn_solicitar_agendamento',
                'div.btn_solicitar_agendamento',
                '[class*="btn_solicitar_agendamento"]'
            ]
            
            botao_encontrado = False
            for seletor in botoes_agendamento:
                try:
                    elemento = self.page.locator(seletor)
                    if elemento.count() > 0:
                        logger.info(f"Botao encontrado: {seletor}")
                        if elemento.locator('label').count() > 0:
                            elemento.locator('label').first.click()
                        else:
                            elemento.first.click()
                        botao_encontrado = True
                        break
                except Exception:
                    continue
            
            if not botao_encontrado:
                return {
                    'success': False,
                    'message': 'Botao de agendamento nao encontrado (pedido pode ja ter agendamento)'
                }
            
            # Aguardar formulario abrir
            self.page.wait_for_timeout(500)  # Reduzido para otimizar
            
            # 4. Preencher datas (2 campos) e calcular peso total
            # Calcular peso total se tiver produtos
            peso_total = 0
            if produtos:
                for produto in produtos:
                    peso_produto = float(produto.get('peso', 0))
                    peso_total += peso_produto
            
            dados = {
                'data_agendamento': data_agendamento,
                'peso_total': peso_total,  # Passa o peso total para determinar tipo de veículo
                'produtos': produtos or []
            }
            
            # Chamar o metodo criar_agendamento com os dados preparados
            return self.criar_agendamento(dados)
            
        except Exception as e:
            logger.error(f"Erro ao criar agendamento completo: {e}")
            return {
                'success': False,
                'message': f'Erro: {str(e)}'
            }
    
    def buscar_pedido_robusto(self, numero_pedido):
        """
        Busca pedido verificando especificamente a coluna 'N pedido original'
        """
        try:
            # Navegar para pagina de pedidos
            self.page.goto(self.config['urls']['pedidos'], timeout=30000)
            # Aguardar DOM em vez de networkidle (pode travar em produção)
            try:
                self.page.wait_for_load_state('domcontentloaded', timeout=5000)
            except Exception as e:
                logger.warning(f"Erro ao aguardar DOM: {e}")
                pass  # Continuar mesmo se timeout
            
            # Abrir filtros
            logger.info("Abrindo filtros...")
            filtro_toggle = self.page.locator('a[data-toggle="collapse"][data-target="#filtros-collapse"]')
            if filtro_toggle.is_visible():
                filtro_toggle.click()
                # WAIT ADAPTATIVO - Aguardar filtros abrirem completamente
                self.aguardar_elemento_visivel('#nr_pedido', timeout_ms=1500)
            
            # CORREÇÃO: Limpar apenas o filtro específico
            logger.info("Limpando filtro de data de elaboração...")
            try:
                botao_limpar = self.page.locator(
                    'button[data-target_daterangepicker="dthr_elaboracao"][data-action="remove"]'
                )
                if botao_limpar.is_visible(timeout=2000):
                    botao_limpar.click()
                    self.page.wait_for_timeout(300)
                    logger.info("✅ Filtro dthr_elaboracao limpo")
            except Exception as e:
                logger.error(f"Erro ao limpar filtro de data: {e}")
                logger.debug("Botão de limpar não encontrado, continuando...")
            
            # Preencher numero do pedido
            logger.info(f"Buscando pedido {numero_pedido}...")
            self.page.fill('#nr_pedido', numero_pedido)
            
            # Buscar com multiplas tentativas
            for tentativa in range(5):
                logger.info(f"Tentativa {tentativa + 1}/5...")
                
                # Clicar em filtrar
                self.page.click('#enviarFiltros')
                
                # Aguardar resposta (tempo reduzido)
                self.page.wait_for_timeout(500 if tentativa == 0 else 300)
                
                # Verificar se encontrou na coluna correta
                linhas_tabela = self.page.locator('table tbody tr').count()
                if linhas_tabela > 0:
                    linhas = self.page.locator('table tbody tr').all()
                    for linha in linhas:
                        colunas = linha.locator('td').all()
                        if len(colunas) >= 2:
                            # Segunda coluna e 'N pedido original'
                            pedido_original = colunas[1].text_content().strip()
                            if pedido_original == numero_pedido:
                                logger.info(f"Pedido {numero_pedido} encontrado!")
                                # Clicar no link de exibir
                                link_exibir = linha.locator('a[title="Exibir"]')
                                if link_exibir.count() > 0:
                                    link_exibir.click()
                                    self.page.wait_for_load_state('domcontentloaded')
                                    return True
                
                # Se nao encontrou, limpar e tentar novamente
                if tentativa < 4:
                    self.page.fill('#nr_pedido', '')
                    self.page.wait_for_timeout(500)
                    self.page.fill('#nr_pedido', numero_pedido)
            
            return False
            
        except Exception as e:
            logger.error(f"Erro na busca robusta: {e}")
            return False
    
    def _converter_data_iso(self, data_br):
        """Converte data de DD/MM/YYYY para YYYY-MM-DD"""
        try:
            partes = data_br.split('/')
            if len(partes) == 3:
                return f"{partes[2]}-{partes[1]}-{partes[0]}"
        except Exception as e:
            logger.error(f"Erro na conversão de data: {e}")
            pass
        return ""
    
    def verificar_status_agendamento(self, protocolo):
        """Verifica o status de um agendamento pelo protocolo"""
        try:
            # URL do agendamento
            url_agendamento = self.config['urls']['agendamento_status'].format(protocolo=protocolo)
            self.page.goto(url_agendamento)
            # Aguardar DOM em vez de networkidle (pode travar em produção)
            try:
                self.page.wait_for_load_state('domcontentloaded', timeout=5000)
            except Exception as e:
                logger.warning(f"Erro ao aguardar DOM: {e}")
                pass  # Continuar mesmo se timeout
            
            # Extrair status
            status_selector = self.config['seletores']['status_agendamento']
            if self.page.locator(status_selector).is_visible():
                status = self.page.text_content(status_selector)
                logger.info(f"Status do protocolo {protocolo}: {status}")
                return status
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao verificar status: {e}")
            return None
    
    def determinar_tipo_veiculo_por_peso(self, peso_total):
        """
        Determina o tipo de veículo baseado no peso total
        
        Regras:
        - Até 2.000 kg: ID 5 (F4000-3/4)
        - Até 4.000 kg: ID 11 (Toco-Baú)
        - Até 7.000 kg: ID 8 (Truck-Baú)
        - Acima de 7.000 kg: ID 2 (Carreta-Baú)
        
        Args:
            peso_total: Peso total em kg
            
        Returns:
            str: ID do tipo de veículo
        """
        try:
            # Converter para float se necessário
            peso = float(peso_total) if peso_total else 0
            
            if peso <= 2000:
                tipo_id = '5'  # F4000-3/4
                tipo_nome = 'F4000-3/4'
            elif peso <= 4000:
                tipo_id = '11'  # Toco-Baú
                tipo_nome = 'Toco-Baú'
            elif peso <= 7000:
                tipo_id = '8'  # Truck-Baú
                tipo_nome = 'Truck-Baú'
            else:
                tipo_id = '2'  # Carreta-Baú
                tipo_nome = 'Carreta-Baú'
            
            logger.info(f"Peso total: {peso:.2f} kg → Tipo de veículo: {tipo_nome} (ID: {tipo_id})")
            return tipo_id
            
        except Exception as e:
            logger.error(f"Erro ao determinar tipo de veículo: {e}")
            # Retorna Toco-Baú como padrão em caso de erro
            return '11'
    
    def fechar(self):
        """Fecha o navegador"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()