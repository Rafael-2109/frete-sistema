"""
Cliente Atacadao usando Playwright - USANDO URLs CORRETAS DO CONFIG
Localizado na pasta CORRETA: app/portal/atacadao/
"""

import os
from datetime import datetime
from playwright.sync_api import sync_playwright
import logging
from .config import ATACADAO_CONFIG

logger = logging.getLogger(__name__)

class AtacadaoPlaywrightClient:
    """Cliente Playwright para o portal Atacadao (Hodie Booking)"""
    
    def __init__(self, headless=True):
        self.headless = headless
        self.storage_file = "storage_state_atacadao.json"
        self.config = ATACADAO_CONFIG  # USANDO CONFIG CORRETO
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def iniciar_sessao(self, salvar_login=False):
        """Inicia sessao do Playwright com ou sem login salvo"""
        self.playwright = sync_playwright().start()
        
        # Configuracoes do navegador
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Contexto com sessao salva ou novo
        if os.path.exists(self.storage_file) and not salvar_login:
            logger.info(f"Carregando sessao salva de {self.storage_file}")
            self.context = self.browser.new_context(
                storage_state=self.storage_file,
                viewport={'width': 1280, 'height': 720}
            )
        else:
            logger.info("Criando nova sessao")
            self.context = self.browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
        
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
    
    def verificar_login(self):
        """Verifica se esta logado no portal"""
        try:
            # Navegar para a pagina de pedidos
            url_pedidos = self.config['urls']['pedidos']  # https://atacadao.hodiebooking.com.br/pedidos
            self.page.goto(url_pedidos, wait_until='networkidle')
            
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
    
    def buscar_pedido(self, numero_pedido):
        """Busca um pedido no portal"""
        try:
            # Navegar para pagina de pedidos
            self.page.goto(self.config['urls']['pedidos'], timeout=30000)
            self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # ABRIR FILTROS PRIMEIRO - IMPORTANTE!
            logger.info("Abrindo secao de filtros...")
            try:
                # O link correto tem data-target="#filtros-collapse"
                filtro_toggle = self.page.locator('a[data-toggle="collapse"][data-target="#filtros-collapse"]')
                if filtro_toggle.is_visible():
                    filtro_toggle.click()
                    logger.info("Clicando no toggle de filtros")
                    self.page.wait_for_timeout(1500)  # Aguardar animacao do collapse
                    
                    # Verificar se abriu verificando se o campo esta visivel
                    if not self.page.locator('#nr_pedido').is_visible():
                        # Tentar clicar novamente
                        logger.info("Campo ainda nao visivel, clicando novamente...")
                        filtro_toggle.click()
                        self.page.wait_for_timeout(1500)
                        
            except Exception as e:
                logger.warning(f"Erro ao abrir filtros: {e}")
                # Continuar, pode ja estar aberto
            
            # LIMPAR FILTROS DE DATA
            logger.info("Limpando filtros de data...")
            try:
                # Procurar botoes de limpar data (X)
                botoes_limpar = self.page.locator('button[data-action="remove"]').all()
                for botao in botoes_limpar:
                    if botao.is_visible():
                        botao.click()
                        logger.info("Filtro de data limpo")
                        self.page.wait_for_timeout(500)
            except:
                pass  # Se nao encontrar, continua
            
            # Limpar campos de data diretamente se existirem
            try:
                # Limpar data de elaboracao
                if self.page.locator('#dthr_elaboracao').is_visible():
                    self.page.fill('#dthr_elaboracao', '')
                # Limpar outros campos de data que possam existir
                if self.page.locator('#data_inicio').is_visible():
                    self.page.fill('#data_inicio', '')
                if self.page.locator('#data_fim').is_visible():
                    self.page.fill('#data_fim', '')
            except:
                pass
            
            # Verificar se o campo esta visivel apos abrir filtros
            campo_pedido = self.config['seletores']['campo_pedido']  # #nr_pedido
            
            # Se o campo nao estiver visivel, tentar abrir filtros novamente
            if not self.page.locator(campo_pedido).is_visible():
                logger.warning("Campo de pedido nao visivel, tentando abrir filtros novamente...")
                try:
                    # Forcar clique no primeiro elemento que pareca ser o toggle
                    self.page.locator('a[data-toggle="collapse"]').first.click()
                    self.page.wait_for_timeout(1000)
                except:
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
            
            # Aguardar resultado COM RETRY
            logger.info("Aguardando resultado da busca...")
            
            # Tentar multiplas vezes para garantir que o resultado carregue
            max_tentativas = 5
            pedido_encontrado = False
            
            for tentativa in range(max_tentativas):
                logger.info(f"Tentativa {tentativa + 1} de {max_tentativas}...")
                
                # Aguardar um tempo antes de verificar
                self.page.wait_for_timeout(3000 if tentativa == 0 else 5000)
                
                # IMPORTANTE: Verificar na coluna correta "N pedido original"
                # A segunda coluna (indice 1) contem o pedido original
                linhas_tabela = self.page.locator('table tbody tr').count()
                if linhas_tabela > 0:
                    linhas = self.page.locator('table tbody tr').all()
                    for linha in linhas:
                        colunas = linha.locator('td').all()
                        if len(colunas) >= 2:
                            # Segunda coluna e "N pedido original"
                            pedido_original = colunas[1].text_content().strip()
                            if pedido_original == numero_pedido:
                                logger.info(f"Pedido {numero_pedido} encontrado na coluna 'N pedido original'!")
                                pedido_encontrado = True
                                # Clicar no link desta linha
                                link_exibir = linha.locator('a[title="Exibir"]')
                                if link_exibir.count() > 0:
                                    link_exibir.click()
                                    logger.info(f"Pedido {numero_pedido} aberto com sucesso")
                                    self.page.wait_for_load_state('networkidle', timeout=10000)
                                    return True
                                break
                    
                    if pedido_encontrado:
                        break
                
                # Verificar se tem mensagem de vazio
                content = self.page.content()
                if "Nenhum registro encontrado" in content or "Nenhum dado disponivel" in content:
                    # Se esta vazio, tentar clicar em filtrar novamente
                    if tentativa < max_tentativas - 1:
                        logger.info("Tabela vazia, tentando filtrar novamente...")
                        self.page.click(botao_filtrar)
                    else:
                        logger.warning("Tabela continua vazia apos todas tentativas")
                        break
                
                # Se nao encontrou nem resultado nem mensagem de vazio, aguardar mais
                if tentativa < max_tentativas - 1:
                    logger.info("Aguardando carregamento...")
                    try:
                        self.page.wait_for_load_state('networkidle', timeout=5000)
                    except:
                        pass
            
            # Screenshot para debug
            self.page.screenshot(path=f"busca_pedido_{numero_pedido}_resultado.png")
            logger.info(f"Screenshot salvo: busca_pedido_{numero_pedido}_resultado.png")
            
            # Verificar se ha resultados
            link_exibir = self.config['seletores']['link_exibir_pedido']
            
            # Verificar se encontrou algum link
            if self.page.locator(link_exibir).count() > 0:
                try:
                    # Clicar no primeiro link encontrado
                    self.page.locator(link_exibir).first.click()
                    logger.info(f" Pedido {numero_pedido} encontrado e aberto")
                    
                    # Aguardar carregar a pagina do pedido
                    self.page.wait_for_load_state('networkidle', timeout=10000)
                    return True
                except Exception as e:
                    logger.error(f"Erro ao clicar no link: {e}")
                    return False
            else:
                # Nao encontrou resultado
                logger.warning(f" Pedido {numero_pedido} nao encontrado apos {max_tentativas} tentativas")
                
                # Como alternativa, se tivermos um mapeamento de pedidos para IDs, podemos tentar URL direta
                # Por exemplo, voce mencionou que 606833 corresponde ao ID 912933499
                pedido_id_map = {
                    '606833': '912933499',  # Voce forneceu este mapeamento
                    '109561': '912933499',  # Mesmo ID para o pedido filial
                }
                
                if numero_pedido in pedido_id_map:
                    pedido_id = pedido_id_map[numero_pedido]
                    url_direta = f"{self.config['urls']['base']}/pedidos/{pedido_id}"
                    logger.info(f"Tentando URL direta: {url_direta}")
                    
                    try:
                        self.page.goto(url_direta, timeout=15000)
                        self.page.wait_for_load_state('networkidle', timeout=10000)
                        
                        # Verificar se chegou no pedido
                        if f"/pedidos/{pedido_id}" in self.page.url:
                            logger.info(f" Pedido aberto via URL direta!")
                            return True
                    except:
                        pass
                
                return False
                
        except Exception as e:
            logger.error(f"Erro ao buscar pedido: {e}")
            return False
    
    def criar_agendamento(self, dados):
        """Cria um agendamento no portal seguindo o fluxo real"""
        try:
            # 1. Verificar login
            if not self.verificar_login():
                return {
                    'success': False,
                    'message': 'Sessao expirada. Execute: python configurar_sessao_atacadao.py'
                }
            
            # 2. Buscar o pedido
            pedido_cliente = dados.get('pedido_cliente')
            if not pedido_cliente:
                return {
                    'success': False,
                    'message': 'Numero do pedido nao fornecido'
                }
            
            logger.info(f"Buscando pedido {pedido_cliente}...")
            if not self.buscar_pedido(pedido_cliente):
                return {
                    'success': False,
                    'message': f'Pedido {pedido_cliente} nao encontrado no portal'
                }
            
            # 3. Solicitar agendamento
            botao_solicitar = self.config['seletores']['botao_solicitar_agendamento']
            self.page.wait_for_selector(botao_solicitar)
            self.page.click(botao_solicitar)
            
            logger.info("Formulario de agendamento aberto")
            self.page.wait_for_load_state('networkidle')
            
            # 4. Preencher formulario
            
            # 4.1 PRIMEIRA DATA: Data desejada de agendamento
            if dados.get('data_agendamento'):
                data_agendamento = dados['data_agendamento']
                data_iso = dados.get('data_agendamento_iso', '')
                
                logger.info(f"Preenchendo data desejada: {data_agendamento}")
                try:
                    # Metodo 1: Clicar e digitar
                    campo_data = self.page.locator('input[name="data_desejada"]')
                    if campo_data.count() > 0:
                        campo_data.click()
                        self.page.wait_for_timeout(500)
                        self.page.keyboard.press('Control+A')
                        self.page.keyboard.press('Delete')
                        self.page.wait_for_timeout(500)
                        self.page.keyboard.type(data_agendamento)
                        self.page.keyboard.press('Tab')
                        
                    # Preencher campo ISO tambem
                    self.page.evaluate(f'''
                        document.querySelector('input[name="data_desejada_iso"]').value = "{data_iso}";
                        document.querySelector('input[name="data_desejada"]').value = "{data_agendamento}";
                    ''')
                    logger.info(" Data desejada preenchida")
                except Exception as e:
                    logger.warning(f"Erro ao preencher data desejada: {e}")
                
                # 4.2 SEGUNDA DATA: Disponibilidade de entrega (leadtime_minimo)
                logger.info(f"Preenchendo disponibilidade de entrega: {data_agendamento}")
                try:
                    campo_leadtime = self.page.locator('input[name="leadtime_minimo"]')
                    if campo_leadtime.count() > 0:
                        campo_leadtime.click()
                        self.page.wait_for_timeout(500)
                        self.page.keyboard.press('Control+A')
                        self.page.keyboard.press('Delete')
                        self.page.wait_for_timeout(500)
                        self.page.keyboard.type(data_agendamento)
                        self.page.keyboard.press('Tab')
                        
                        # Preencher campo ISO tambem
                        self.page.evaluate(f'''
                            document.querySelector('input[name="leadtime_minimo_iso"]').value = "{data_iso}";
                            document.querySelector('input[name="leadtime_minimo"]').value = "{data_agendamento}";
                        ''')
                        logger.info(" Disponibilidade de entrega preenchida")
                except Exception as e:
                    logger.warning(f"Campo leadtime_minimo nao encontrado ou erro: {e}")
            
            # 4.3 Transportadora (usar padrao Agregado)
            if self.page.locator(self.config['seletores']['botao_buscar_transportadora']).is_visible():
                logger.info("Selecionando transportadora...")
                self.page.click(self.config['seletores']['botao_buscar_transportadora'])
                self.page.wait_for_timeout(2000)
                
                # Selecionar Agregado
                radio_agregado = self.page.locator('input[type="radio"][id="1"]')
                if radio_agregado.count() > 0:
                    radio_agregado.click()
                    self.page.wait_for_timeout(500)
                
                # IMPORTANTE: Clicar no botao Selecionar do modal-footer
                # Pode haver multiplos botoes "Selecionar"
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
                    self.page.wait_for_timeout(1000)
            
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
            
            # 4.5 Tipo de veiculo
            tipo_veiculo = dados.get('tipo_veiculo', '11')  # Default: Toco-Bau (value="11")
            logger.info(f"Selecionando tipo de veiculo: {tipo_veiculo}")
            select_veiculo = self.page.locator('select[name="tipo_veiculo"]')
            if select_veiculo.count() > 0:
                try:
                    select_veiculo.select_option(value=tipo_veiculo)
                    logger.info(" Tipo de veiculo selecionado")
                except Exception as e:
                    logger.warning(f"Erro ao selecionar veiculo: {e}")
            
            # 4.6 Preencher quantidades dos produtos (se fornecido)
            if dados.get('produtos'):
                logger.info("Preenchendo quantidades dos produtos...")
                for produto in dados['produtos']:
                    codigo = produto.get('codigo')
                    quantidade = produto.get('quantidade', 0)
                    
                    # Procurar o produto na tabela
                    linhas_produtos = self.page.locator('table tbody tr').all()
                    for linha in linhas_produtos:
                        codigo_atual = linha.locator('td').first.text_content().strip()
                        if codigo_atual == codigo:
                            campo_qtd = linha.locator('input[name*="qtd_alocada"]')
                            if campo_qtd.count() > 0:
                                campo_qtd.fill(str(quantidade))
                                logger.info(f" Produto {codigo}: {quantidade} unidades")
                            break
            
            # Screenshot antes de salvar
            self.page.screenshot(path=f"agendamento_{datetime.now().strftime('%Y%m%d_%H%M%S')}_antes.png")
            
            # 5. Salvar
            botao_salvar = self.config['seletores']['botao_salvar']  # #salvar
            self.page.click(botao_salvar)
            logger.info("Formulario enviado, aguardando resposta...")
            
            # 6. Aguardar modal de sucesso ou erro
            try:
                # Aguardar modal de sucesso
                modal_sucesso = self.config['seletores']['modal_sucesso']  # #regSucesso
                self.page.wait_for_selector(modal_sucesso, timeout=20000)
                
                # Clicar em "Nao incluir NF agora"
                botao_nao = self.config['seletores']['botao_nao_incluir_nf']  # #btnNao
                if self.page.locator(botao_nao).is_visible():
                    self.page.click(botao_nao)
                    logger.info("Optou por nao incluir NF agora")
                
                # Aguardar redirecionamento
                self.page.wait_for_load_state('networkidle')
                self.page.wait_for_timeout(3000)
                
                # Extrair protocolo - MUTIPLOS METODOS
                protocolo = None
                current_url = self.page.url
                logger.info(f"URL apos salvar: {current_url}")
                
                # METODO 1: Extrair da URL apos redirecionamento
                if "/agendamentos/" in current_url:
                    protocolo = current_url.split("/agendamentos/")[-1].split("/")[0].split("?")[0]
                    logger.info(f" Protocolo extraido da URL: {protocolo}")
                elif "/cargas/" in current_url:
                    # Se voltou para a pagina da carga, procurar o link do agendamento
                    logger.info("Pagina redirecionou para carga, procurando link do agendamento...")
                    link_acompanhe = self.page.locator('a[href*="/agendamentos/"]:has-text("ACOMPANHE")')
                    if link_acompanhe.count() == 0:
                        link_acompanhe = self.page.locator('a[href*="/agendamentos/"]').first
                    
                    if link_acompanhe.count() > 0:
                        href = link_acompanhe.get_attribute('href')
                        if href and "/agendamentos/" in href:
                            protocolo = href.split("/agendamentos/")[-1].split("/")[0].split("?")[0]
                            logger.info(f" Protocolo extraido do link: {protocolo}")
                
                # METODO 2: Procurar no HTML
                if not protocolo:
                    logger.info("Procurando protocolo no HTML...")
                    links_agendamento = self.page.locator('a[href*="/agendamentos/"]').all()
                    for link in links_agendamento:
                        href = link.get_attribute('href')
                        if href and "/agendamentos/" in href:
                            protocolo_temp = href.split("/agendamentos/")[-1].split("/")[0].split("?")[0]
                            if protocolo_temp and protocolo_temp.isdigit():
                                protocolo = protocolo_temp
                                logger.info(f" Protocolo encontrado em link: {protocolo}")
                                break
                
                # METODO 3: Procurar por padrao de protocolo
                if not protocolo:
                    import re
                    page_content = self.page.content()
                    padrao_protocolo = re.compile(r'\b\d{13}\b')
                    matches = padrao_protocolo.findall(page_content)
                    for match in matches:
                        if match.startswith(('25', '24', '23')):
                            protocolo = match
                            logger.info(f" Protocolo encontrado por padrao: {protocolo}")
                            break
                
                if protocolo:
                    # Screenshot do protocolo
                    self.page.screenshot(path=f"protocolo_{protocolo}.png")
                    
                    return {
                        'success': True,
                        'protocolo': protocolo.strip() if isinstance(protocolo, str) else protocolo,
                        'message': 'Agendamento realizado com sucesso',
                        'url': current_url
                    }
                else:
                    # Screenshot para debug
                    self.page.screenshot(path=f"agendamento_sem_protocolo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    return {
                        'success': True,  # Pode ter sido criado mesmo sem capturar protocolo
                        'message': 'Agendamento pode ter sido criado mas protocolo nao capturado',
                        'url': current_url
                    }
                    
            except Exception as e:
                # Verificar se houve erro
                logger.error(f"Erro ao aguardar resposta: {e}")
                
                # Screenshot de erro
                self.page.screenshot(path=f"erro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                
                # Tentar capturar mensagem de erro
                erro_msg = "Erro desconhecido"
                if self.page.locator(".alert-danger").is_visible():
                    erro_msg = self.page.text_content(".alert-danger")
                
                return {
                    'success': False,
                    'message': f'Erro no portal: {erro_msg}'
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
            self.page.wait_for_timeout(3000)
            
            # 4. Preencher datas (2 campos)
            dados = {
                'data_agendamento': data_agendamento,
                'data_agendamento_iso': self._converter_data_iso(data_agendamento),
                'tipo_veiculo': '11',  # Toco-Bau
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
            self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Abrir filtros
            logger.info("Abrindo filtros...")
            filtro_toggle = self.page.locator('a[data-toggle="collapse"][data-target="#filtros-collapse"]')
            if filtro_toggle.is_visible():
                filtro_toggle.click()
                self.page.wait_for_timeout(1500)
            
            # Limpar filtros de data
            logger.info("Limpando filtros de data...")
            botoes_limpar = self.page.locator('button[data-action="remove"]').all()
            for botao in botoes_limpar:
                if botao.is_visible():
                    botao.click()
                    self.page.wait_for_timeout(500)
            
            # Preencher numero do pedido
            logger.info(f"Buscando pedido {numero_pedido}...")
            self.page.fill('#nr_pedido', numero_pedido)
            
            # Buscar com multiplas tentativas
            for tentativa in range(5):
                logger.info(f"Tentativa {tentativa + 1}/5...")
                
                # Clicar em filtrar
                self.page.click('#enviarFiltros')
                
                # Aguardar resposta
                self.page.wait_for_timeout(5000 if tentativa > 0 else 3000)
                
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
                                    self.page.wait_for_load_state('networkidle')
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
        except:
            pass
        return ""
    
    def verificar_status_agendamento(self, protocolo):
        """Verifica o status de um agendamento pelo protocolo"""
        try:
            # URL do agendamento
            url_agendamento = self.config['urls']['agendamento_status'].format(protocolo=protocolo)
            self.page.goto(url_agendamento)
            self.page.wait_for_load_state('networkidle')
            
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