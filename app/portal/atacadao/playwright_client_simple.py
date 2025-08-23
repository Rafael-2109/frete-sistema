"""
Cliente Atacadao usando Playwright - VERSÃO SIMPLIFICADA
Baseado 100% no agendar_pedido_932955.py que FUNCIONA
"""

from playwright.sync_api import sync_playwright
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AtacadaoPlaywrightSimple:
    """Cliente simplificado baseado no script que funciona"""
    
    def __init__(self, headless=False):
        # FORÇAR MODO VISÍVEL PARA DEBUG
        self.headless = False  # SEMPRE visível para debug
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    def iniciar_sessao(self):
        """Inicia sessão com Playwright"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        
        # Carregar sessão salva (EXATAMENTE como no script)
        storage_path = Path(__file__).parent.parent.parent.parent / "storage_state_atacadao.json"
        
        try:
            self.context = self.browser.new_context(storage_state=str(storage_path))
            logger.info("✅ Sessão carregada")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar sessão: {e}")
            raise Exception("Execute: python configurar_sessao_atacadao.py")
        
        self.page = self.context.new_page()
        
    def buscar_pedido(self, numero_pedido):
        """Busca pedido EXATAMENTE como agendar_pedido_932955.py"""
        logger.info(f"\n🚀 BUSCANDO PEDIDO {numero_pedido}")
        logger.info("=" * 60)
        
        # 1. Ir para página de pedidos
        logger.info("1. Abrindo página de pedidos...")
        self.page.goto("https://atacadao.hodiebooking.com.br/pedidos", timeout=30000)
        self.page.wait_for_load_state('networkidle')
        
        # 2. Abrir filtros
        logger.info("2. Abrindo filtros...")
        filtro_toggle = self.page.locator('a[data-toggle="collapse"][data-target="#filtros-collapse"]')
        if filtro_toggle.is_visible():
            filtro_toggle.click()
            time.sleep(1.5)  # EXATO como no script
        
        # 3. Limpar filtros de data
        logger.info("3. Limpando filtros de data...")
        botoes_limpar = self.page.locator('button[data-action="remove"]').all()
        for botao in botoes_limpar:
            if botao.is_visible():
                botao.click()
                time.sleep(0.5)  # EXATO como no script
        
        # 4. Buscar pedido
        logger.info(f"4. Buscando pedido {numero_pedido}...")
        self.page.fill('#nr_pedido', numero_pedido)
        
        # Aguardar resultado com retry REAL
        encontrado = False
        for tentativa in range(5):
            logger.info(f"   Tentativa {tentativa + 1}/5...")
            
            # Clicar em filtrar
            self.page.click('#enviarFiltros')
            
            # Aguardar mais tempo (EXATO como no script)
            logger.info("   Aguardando resposta do servidor...")
            time.sleep(5)  # 5 segundos como no script
            
            # Aguardar a página estabilizar
            try:
                self.page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass
            
            # Verificar se encontrou
            linhas_tabela = self.page.locator('table tbody tr').count()
            logger.info(f"   Linhas na tabela: {linhas_tabela}")
            
            # Verificar especificamente na coluna correta
            if linhas_tabela > 0:
                linhas = self.page.locator('table tbody tr').all()
                for linha in linhas:
                    colunas = linha.locator('td').all()
                    if len(colunas) >= 2:
                        # Segunda coluna é "N° pedido original"
                        pedido_original = colunas[1].text_content().strip()
                        if pedido_original == numero_pedido:
                            logger.info(f"   ✅ Pedido {numero_pedido} encontrado!")
                            encontrado = True
                            break
                
                if encontrado:
                    break
            
            # Se não encontrou, tentar novamente
            if tentativa < 4:
                self.page.fill('#nr_pedido', '')
                time.sleep(0.5)
                self.page.fill('#nr_pedido', numero_pedido)
            else:
                time.sleep(2)  # Aguardar mais 2 segundos na última tentativa
        
        if not encontrado:
            logger.error(f"❌ Pedido {numero_pedido} não encontrado após 5 tentativas")
            return False
        
        # 5. Abrir o pedido
        logger.info("5. Abrindo pedido...")
        
        # Procurar o link do pedido na tabela
        pedido_aberto = False
        linhas = self.page.locator('table tbody tr').all()
        
        for linha in linhas:
            colunas = linha.locator('td').all()
            if len(colunas) >= 2:
                pedido_original = colunas[1].text_content().strip()
                if pedido_original == numero_pedido:
                    logger.info(f"   Encontrado pedido {numero_pedido} na tabela")
                    # Clicar no link "Exibir" desta linha
                    link_exibir = linha.locator('a[title="Exibir"]')
                    if link_exibir.count() > 0:
                        logger.info("   Clicando no link para abrir...")
                        link_exibir.click()
                        self.page.wait_for_load_state('networkidle')
                        time.sleep(3)  # EXATO como no script
                        pedido_aberto = True
                        break
        
        if not pedido_aberto:
            logger.error("   ❌ Não conseguiu abrir o pedido")
            return False
            
        return True
    
    def solicitar_agendamento(self):
        """Clica no botão Solicitar Agendamento"""
        logger.info("6. Procurando botão de agendamento...")
        
        # EXATO como no script
        botoes_agendamento = [
            '.btn_solicitar_agendamento',
            '.btn-panel.btn_solicitar_agendamento',
            'div:has-text("Solicitar agendamento")',
            'label:has-text("Solicitar agendamento")',
            '.btn-panel:has(label:has-text("Solicitar agendamento"))',
            'div.btn_solicitar_agendamento',
            '[class*="btn_solicitar_agendamento"]'
        ]
        
        botao_encontrado = False
        for seletor in botoes_agendamento:
            try:
                elemento = self.page.locator(seletor)
                if elemento.count() > 0:
                    logger.info(f"   ✅ Botão encontrado: {seletor}")
                    # Clicar no elemento ou no label dentro dele
                    if elemento.locator('label').count() > 0:
                        elemento.locator('label').first.click()
                    else:
                        elemento.first.click()
                    botao_encontrado = True
                    break
            except Exception:
                continue
        
        if not botao_encontrado:
            logger.error("   ❌ Botão de agendamento não encontrado")
            return False
        
        # Aguardar formulário abrir (EXATO como no script)
        logger.info("7. Aguardando formulário de agendamento...")
        time.sleep(3)
        
        return True
    
    def preencher_formulario(self, data_agendamento, produtos=None):
        """Preenche o formulário EXATAMENTE como no script"""
        
        # CONVERTER DATA SE VIER DO BANCO EM FORMATO ISO
        if data_agendamento and '-' in str(data_agendamento):
            # Converter de YYYY-MM-DD ou date object para DD/MM/YYYY
            from datetime import datetime, date
            try:
                if isinstance(data_agendamento, date):
                    data_agendamento = data_agendamento.strftime('%d/%m/%Y')
                else:
                    dt = datetime.strptime(str(data_agendamento), '%Y-%m-%d')
                    data_agendamento = dt.strftime('%d/%m/%Y')
                logger.info(f"   📅 Data convertida de ISO para BR: {data_agendamento}")
            except Exception as e:
                logger.warning(f"   ⚠️ Erro ao converter data: {e}")
        
        # 8. Preencher data de agendamento (Campo 1: data_desejada) - COPIADO EXATO DO agendar_pedido_932955.py
        logger.info("8. Preenchendo primeira data de agendamento...")
        
        # Primeiro, verificar se há campo oculto ISO
        campo_data_iso = self.page.locator('input[name="data_desejada_iso"]')
        campo_data_visivel = self.page.locator('input[name="data_desejada"]')
        
        try:
            # Método 1: Clicar no campo para focar (EXATO como agendar_pedido_932955.py linha 265-283)
            if campo_data_visivel.count() > 0:
                logger.info("   Clicando no campo de data desejada...")
                campo_data_visivel.click()
                time.sleep(0.5)
                
                # Limpar campo usando Ctrl+A e Delete
                self.page.keyboard.press('Control+A')
                self.page.keyboard.press('Delete')
                time.sleep(0.5)
                
                # Digitar a data
                logger.info(f"   Digitando data: {data_agendamento}")
                self.page.keyboard.type(data_agendamento)
                time.sleep(0.5)
                
                # Pressionar Tab para sair do campo e validar
                self.page.keyboard.press('Tab')
                logger.info(f"   ✅ Data desejada preenchida: {data_agendamento}")
                
                # Método 2: Se houver campo ISO, preencher também
                if campo_data_iso.count() > 0:
                    # Converter para formato ISO
                    partes = data_agendamento.split('/')
                    data_iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
                    self.page.evaluate(f'document.querySelector(\'input[name="data_desejada_iso"]\').value = "{data_iso}"')
                    self.page.evaluate(f'document.querySelector(\'input[name="data_desejada"]\').value = "{data_agendamento}"')
                    logger.info(f"   ✅ Data desejada preenchida via JavaScript: {data_agendamento}")
                
        except Exception as e:
            logger.info(f"   ⚠️ Erro ao preencher data desejada: {e}")
            
            # Método 3: Forçar via JavaScript (linha 296-311)
            logger.info("   Tentando método alternativo...")
            partes = data_agendamento.split('/')
            data_iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
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
        
        # 8b. Preencher segunda data (Campo 2: leadtime_minimo - Disponibilidade de entrega)
        # COPIADO EXATO DO agendar_pedido_932955.py linhas 313-360
        logger.info("8b. Preenchendo segunda data (Disponibilidade de entrega)...")
        
        campo_leadtime = self.page.locator('input[name="leadtime_minimo"]')
        campo_leadtime_iso = self.page.locator('input[name="leadtime_minimo_iso"]')
        
        if campo_leadtime.count() > 0:
            try:
                # Método 1: Clicar e digitar
                logger.info("   Clicando no campo de disponibilidade de entrega...")
                campo_leadtime.click()
                time.sleep(0.5)
                
                # Limpar e digitar
                self.page.keyboard.press('Control+A')
                self.page.keyboard.press('Delete')
                time.sleep(0.5)
                
                logger.info(f"   Digitando data: {data_agendamento}")
                self.page.keyboard.type(data_agendamento)
                time.sleep(0.5)
                
                self.page.keyboard.press('Tab')
                logger.info(f"   ✅ Disponibilidade de entrega preenchida: {data_agendamento}")
                
                # Preencher campo ISO também
                if campo_leadtime_iso.count() > 0:
                    partes = data_agendamento.split('/')
                    data_iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
                    self.page.evaluate(f'document.querySelector(\'input[name="leadtime_minimo_iso"]\').value = "{data_iso}"')
                    self.page.evaluate(f'document.querySelector(\'input[name="leadtime_minimo"]\').value = "{data_agendamento}"')
                    
            except Exception as e:
                logger.info(f"   ⚠️ Erro ao preencher disponibilidade: {e}")
                # Forçar via JavaScript
                partes = data_agendamento.split('/')
                data_iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
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
            logger.info("   ⚠️ Campo de disponibilidade de entrega não encontrado (pode não ser obrigatório)")
        
        # 9. Selecionar transportadora
        logger.info("9. Verificando transportadora...")
        botao_transportadora = self.page.locator('a#transportadora[data-transportadora="4"]')
        if botao_transportadora.count() > 0:
            if not botao_transportadora.is_visible():
                logger.info("   Abrindo lista de transportadoras...")
                toggle = self.page.locator('a[data-toggle="collapse"][data-target="#lista-transportadoras"]')
                if toggle.count() > 0:
                    toggle.click()
                    time.sleep(1)
            
            logger.info("   Selecionando transportadora Agregado...")
            botao_transportadora.click()
            time.sleep(0.5)
        
        # 10. Preencher produtos
        if produtos:
            logger.info("10. Preenchendo quantidades dos produtos...")
            
            # Criar mapa de produtos
            produtos_map = {}
            for produto in produtos:
                codigo = str(produto.get('codigo'))
                quantidade = produto.get('quantidade', 0)
                produtos_map[codigo] = int(quantidade)
            
            # Preencher cada linha
            linhas_produtos = self.page.locator('table tbody tr').all()
            for linha in linhas_produtos:
                # Pegar código do produto
                codigo = linha.locator('td').first.text_content().strip()
                
                # Campo de quantidade
                campo_qtd = linha.locator('input[name*="qtd_alocada"]')
                
                if campo_qtd.count() > 0:
                    if codigo in produtos_map:
                        qtd = produtos_map[codigo]
                        campo_qtd.fill(str(qtd))
                        logger.info(f"   ✅ Produto {codigo}: {qtd} unidades")
                    else:
                        campo_qtd.fill('0')
                        logger.info(f"   ❌ Produto {codigo}: 0 (não na separação)")
        
        # 11. Tipo de carga
        logger.info("11. Verificando tipo de carga...")
        select_carga = self.page.locator('select[name="carga_especie_id"]')
        if select_carga.count() > 0:
            is_disabled = select_carga.get_attribute('disabled')
            if is_disabled is None or is_disabled == "false":
                select_carga.select_option(value='1')
                logger.info("   ✅ Tipo de carga: Paletizada")
            else:
                logger.info("   ⚠️ Tipo de carga já definido")
        
        # 12. Tipo de veículo
        logger.info("12. Selecionando tipo de veículo...")
        select_veiculo = self.page.locator('select[name="tipo_veiculo"]')
        if select_veiculo.count() > 0:
            try:
                select_veiculo.select_option(value='11')  # Toco-Baú
                logger.info("   ✅ Tipo de veículo: Toco-Baú")
            except Exception:
                logger.warning("   ⚠️ Erro ao selecionar veículo")
    
    def salvar_agendamento(self, confirmar=True):
        """Salva o agendamento EXATAMENTE como no script"""
        
        if confirmar:
            # Pausa para estabilização (simula input do usuário)
            logger.info("\n" + "=" * 60)
            logger.info("⏳ Aguardando estabilização do formulário...")
            logger.info("=" * 60)
            time.sleep(5)  # Tempo equivalente ao input do usuário
        
        # 14. Salvar/Enviar
        logger.info("\n14. Enviando agendamento...")
        
        # EXATO como no script
        botao_salvar = self.page.locator('#salvar')
        if botao_salvar.count() > 0:
            logger.info("   Clicando em Salvar...")
            botao_salvar.click()
            logger.info("   ✅ Formulário enviado!")
        else:
            # Tentar alternativas
            botoes_salvar = [
                'div#salvar',
                '.btn-panel:has(label:has-text("Salvar"))',
                'div:has-text("Salvar")',
                'button:has-text("Salvar")',
                'button[type="submit"]'
            ]
            
            for seletor in botoes_salvar:
                if self.page.locator(seletor).count() > 0:
                    self.page.locator(seletor).first.click()
                    logger.info(f"   ✅ Formulário enviado via: {seletor}")
                    break
        
        # 15. Aguardar resposta (EXATO como no script)
        logger.info("15. Aguardando resposta...")
        time.sleep(5)  # 5 segundos como no script
        
        # Verificar modal de sucesso
        if self.page.locator('#regSucesso').count() > 0:
            logger.info("   ✅ Modal de sucesso detectado!")
            
            # Clicar em "Não incluir NF agora"
            if self.page.locator('#btnNao').count() > 0:
                self.page.locator('#btnNao').click()
                logger.info("   Optou por não incluir NF agora")
        
        # 16. Capturar protocolo
        logger.info("16. Capturando protocolo...")
        time.sleep(3)  # EXATO como no script
        
        protocolo = None
        
        # Verificar URL
        current_url = self.page.url
        if "/agendamentos/" in current_url:
            partes = current_url.split("/agendamentos/")
            if len(partes) > 1:
                protocolo = partes[1].split("/")[0].split("?")[0]
                logger.info(f"   ✅ Protocolo da URL: {protocolo}")
        
        # Se não achou, procurar no HTML
        if not protocolo:
            import re
            page_content = self.page.content()
            padrao_protocolo = re.compile(r'\b\d{13}\b')
            matches = padrao_protocolo.findall(page_content)
            if matches:
                protocolo = matches[0]
                logger.info(f"   ✅ Protocolo encontrado: {protocolo}")
        
        return protocolo
    
    def criar_agendamento_completo(self, pedido_cliente, data_agendamento, produtos=None):
        """Executa o fluxo completo de agendamento"""
        try:
            # 1. Buscar pedido
            if not self.buscar_pedido(pedido_cliente):
                return {
                    'success': False,
                    'message': f'Pedido {pedido_cliente} não encontrado'
                }
            
            # 2. Solicitar agendamento
            if not self.solicitar_agendamento():
                return {
                    'success': False,
                    'message': 'Botão de agendamento não encontrado'
                }
            
            # 3. Preencher formulário
            self.preencher_formulario(data_agendamento, produtos)
            
            # 4. Salvar
            protocolo = self.salvar_agendamento()
            
            if protocolo:
                return {
                    'success': True,
                    'protocolo': protocolo,
                    'message': 'Agendamento realizado com sucesso'
                }
            else:
                return {
                    'success': False,
                    'message': 'Protocolo não capturado'
                }
            
        except Exception as e:
            logger.error(f"Erro no agendamento: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
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