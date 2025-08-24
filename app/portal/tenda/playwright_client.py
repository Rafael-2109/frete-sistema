"""
Cliente Tenda usando Playwright
Implementa o fluxo de 3 telas do portal Agendar Entrega
"""

import os
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright
import logging
from .config import TENDA_CONFIG
from .models import ProdutoDeParaEAN, LocalEntregaDeParaTenda
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

logger = logging.getLogger(__name__)


class TendaPlaywrightClient:
    """Cliente Playwright para o portal Tenda (Agendar Entrega)"""
    
    def __init__(self, headless=True):
        self.headless = headless
        # Path para o storage_state
        root_storage = Path.cwd() / "storage_state_tenda.json"
        module_storage = Path(__file__).resolve().parent / "storage_state_tenda.json"
        
        if root_storage.exists():
            self.storage_file = str(root_storage)
            logger.info(f"Usando storage_state do raiz: {self.storage_file}")
        else:
            self.storage_file = str(module_storage)
            logger.info(f"Usando storage_state do módulo: {self.storage_file}")
            
        self.config = TENDA_CONFIG
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def iniciar_sessao(self, salvar_login=False):
        """Inicia sessao do Playwright com ou sem login salvo"""
        self.playwright = sync_playwright().start()
        
        # Configuracoes do navegador
        self.browser = self.playwright.chromium.launch(
            headless=self.headless
        )
        
        # Contexto com sessao salva ou novo
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
        print("LOGIN MANUAL NO TENDA")
        print("="*60)
        print("\n1. O navegador vai abrir no portal Tenda")
        print("2. Faca login com suas credenciais")
        print("3. Quando estiver logado, pressione ENTER aqui")
        print("\n" + "="*60 + "\n")
        
        # Iniciar em modo visivel
        self.headless = False
        self.iniciar_sessao(salvar_login=True)
        
        # Navegar para o portal
        url_login = self.config['urls']['login']
        print(f"Abrindo: {url_login}")
        self.page.goto(url_login)
        
        # Esperar o usuario fazer login
        input("\n Faca login no navegador e pressione ENTER quando terminar...")
        
        # Salvar a sessao
        self.context.storage_state(path=self.storage_file)
        print(f" Sessao salva em {self.storage_file}")
        
        self.fechar()
        return True
    
    def fazer_login_automatico(self):
        """
        Faz login automaticamente preenchendo credenciais do .env
        """
        try:
            # Verificar se tem credenciais no .env
            usuario = os.environ.get('TENDA_USUARIO')
            senha = os.environ.get('TENDA_SENHA')
            
            if not usuario or not senha:
                logger.warning("Credenciais não encontradas no .env - usando login manual")
                return self.fazer_login_manual()
            
            logger.info("Iniciando login automático...")
            
            # Navegar para login
            url_login = self.config['urls']['login']
            logger.info(f"Navegando para: {url_login}")
            self.page.goto(url_login)
            
            # Aguardar página carregar
            self.page.wait_for_selector(
                self.config['seletores']['campo_usuario'],
                timeout=self.config['timeouts']['element_wait'] * 1000
            )
            
            # Preencher credenciais
            logger.info("Preenchendo credenciais...")
            self.page.fill(self.config['seletores']['campo_usuario'], usuario)
            self.page.fill(self.config['seletores']['campo_senha'], senha)
            
            # Clicar em login
            self.page.click(self.config['seletores']['botao_login'])
            
            # Aguardar login completar
            self.page.wait_for_selector(
                self.config['seletores']['usuario_logado'],
                timeout=self.config['timeouts']['page_load'] * 1000
            )
            
            # Salvar sessão
            self.context.storage_state(path=self.storage_file)
            logger.info("Login realizado e sessão salva com sucesso")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro no login automático: {e}")
            return False
    
    def criar_agendamento(self, dados_agendamento):
        """
        Cria um agendamento completo no portal Tenda
        Implementa o fluxo das 3 telas
        
        Args:
            dados_agendamento: Dict com todos os dados necessários
                - cnpj_cliente: CNPJ do cliente
                - local_entrega_id: ID do local no portal
                - produtos: Lista de produtos com EAN
                - pdd_numero: Número do PDD
                - data_agendamento: Data desejada
                - horario: Horário desejado
                - tipo_veiculo: Tipo de veículo
                - tipo_carga: Tipo de carga
                - tipo_volume: Tipo de volume
                - quantidade_volume: Quantidade
                
        Returns:
            Dict com resultado do agendamento
        """
        try:
            logger.info("Iniciando criação de agendamento no Tenda...")
            
            # Navegar para página de marcar agenda
            self.page.goto(self.config['urls']['marcar_agenda'])
            
            # ========== TELA 1: Marcar Agenda ==========
            logger.info("TELA 1: Configurando dados iniciais...")
            
            # Marcar checkbox "sem XML" se configurado
            if self.config['valores_padrao']['marcar_sem_xml']:
                self.page.check(self.config['seletores']['checkbox_sem_xml'])
            
            # Preencher CNPJ do fornecedor (hardcoded)
            cnpj_fornecedor = self.config['valores_padrao']['cnpj_fornecedor']
            self.page.fill(
                self.config['seletores']['campo_cnpj_fornecedor'],
                cnpj_fornecedor
            )
            
            # Selecionar destinatário (baseado no CNPJ do cliente)
            # Primeiro clicar para abrir o dropdown
            self.page.click(self.config['seletores']['campo_filtro_destinatario'])
            time.sleep(1)
            
            # Selecionar o cliente correto (TENDA ATACADO SA)
            # Procurar pelo texto que contém "TENDA"
            self.page.click('text=TENDA ATACADO SA')
            time.sleep(1)
            
            # Selecionar local de entrega
            local_id = dados_agendamento.get('local_entrega_id')
            if local_id:
                # Clicar para abrir dropdown de locais
                self.page.click('text=- Selecione um Local de Entrega -')
                time.sleep(1)
                
                # Selecionar o local específico pelo data-value
                self.page.click(f'li[data-value="{local_id}"]')
            
            # Clicar em confirmar
            self.page.click(self.config['seletores']['botao_confirmar_tela1'])
            
            # Aguardar próxima tela
            time.sleep(2)
            
            # ========== TELA 2: Pesquisar PDD ==========
            logger.info("TELA 2: Selecionando PDD...")
            
            # Clicar no botão pesquisar PDD
            self.page.click(self.config['seletores']['botao_pesquisar_pdd'])
            
            # Aguardar modal abrir
            self.page.wait_for_selector(
                self.config['seletores']['campo_busca_pdd'],
                timeout=self.config['timeouts']['modal_wait'] * 1000
            )
            
            # Buscar PDD específico se fornecido
            pdd_numero = dados_agendamento.get('pdd_numero')
            if pdd_numero:
                self.page.fill(self.config['seletores']['campo_busca_pdd'], pdd_numero)
                time.sleep(1)
            
            # Selecionar primeiro PDD disponível (ou o encontrado)
            self.page.click(f'{self.config["seletores"]["checkbox_pdd"]}:first')
            
            # Confirmar seleção de produtos
            self.page.click(self.config['seletores']['botao_confirmar_produtos'])
            
            # Aguardar modal fechar
            time.sleep(1)
            
            # Clicar em próximo
            self.page.click(self.config['seletores']['botao_proximo_tela2'])
            
            # Aguardar próxima tela
            time.sleep(2)
            
            # ========== TELA 3: Configurações Finais ==========
            logger.info("TELA 3: Configurando detalhes do agendamento...")
            
            # Selecionar tipo de veículo
            tipo_veiculo = dados_agendamento.get('tipo_veiculo', 'TRUCK')
            self.page.select_option(
                self.config['seletores']['select_veiculo'],
                tipo_veiculo
            )
            
            # Selecionar tipo de carga
            tipo_carga = dados_agendamento.get('tipo_carga', 'PALETIZADA')
            self.page.select_option(
                self.config['seletores']['select_tipo_carga'],
                tipo_carga
            )
            
            # Selecionar tipo de volume
            tipo_volume = dados_agendamento.get('tipo_volume', 'PALLET')
            self.page.select_option(
                self.config['seletores']['select_tipo_volume'],
                tipo_volume
            )
            
            # Preencher quantidade de volume
            qtd_volume = dados_agendamento.get('quantidade_volume', 1)
            self.page.fill(
                self.config['seletores']['campo_qtd_volume'],
                str(qtd_volume)
            )
            
            # Selecionar data
            data_agendamento = dados_agendamento.get('data_agendamento')
            if isinstance(data_agendamento, str):
                # Converter string para formato aceito pelo input date
                data_formatada = datetime.strptime(data_agendamento, '%d/%m/%Y').strftime('%Y-%m-%d')
            else:
                data_formatada = data_agendamento.strftime('%Y-%m-%d')
            
            self.page.fill(
                self.config['seletores']['campo_data_agendamento'],
                data_formatada
            )
            
            # Selecionar horário
            horario = dados_agendamento.get('horario', '09:00')
            self.page.select_option(
                self.config['seletores']['select_horario'],
                horario
            )
            
            # Finalizar agendamento
            self.page.click(self.config['seletores']['botao_finalizar'])
            
            # Aguardar resposta
            time.sleep(3)
            
            # Capturar protocolo gerado
            protocolo = None
            try:
                protocolo_element = self.page.query_selector(
                    self.config['seletores']['protocolo_gerado']
                )
                if protocolo_element:
                    protocolo = protocolo_element.inner_text()
            except:
                pass
            
            # Verificar mensagem de sucesso
            sucesso = False
            mensagem = ""
            try:
                mensagem_element = self.page.query_selector(
                    self.config['seletores']['mensagem_sucesso']
                )
                if mensagem_element:
                    mensagem = mensagem_element.inner_text()
                    sucesso = any(msg in mensagem for msg in self.config['mensagens']['sucesso'])
                
                # Se não encontrou sucesso, verificar erro
                if not sucesso:
                    erro_element = self.page.query_selector(
                        self.config['seletores']['mensagem_erro']
                    )
                    if erro_element:
                        mensagem = erro_element.inner_text()
            except:
                pass
            
            # Capturar screenshot para evidência
            screenshot_path = f"agendamento_tenda_{protocolo or 'sem_protocolo'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.page.screenshot(path=screenshot_path)
            
            resultado = {
                'sucesso': sucesso,
                'protocolo': protocolo,
                'mensagem': mensagem,
                'screenshot': screenshot_path,
                'data_agendamento': data_agendamento,
                'horario': horario
            }
            
            logger.info(f"Agendamento finalizado: {resultado}")
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao criar agendamento no Tenda: {e}")
            
            # Capturar screenshot de erro
            try:
                error_screenshot = f"erro_tenda_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.page.screenshot(path=error_screenshot)
            except:
                error_screenshot = None
            
            return {
                'sucesso': False,
                'erro': str(e),
                'screenshot': error_screenshot
            }
    
    def consultar_protocolo(self, protocolo):
        """
        Consulta status de um protocolo no portal
        
        Args:
            protocolo: Número do protocolo
            
        Returns:
            Dict com informações do protocolo
        """
        try:
            # Navegar para página de consulta
            url_consulta = self.config['urls']['consultar_protocolo'].format(protocolo=protocolo)
            self.page.goto(url_consulta)
            
            # Aguardar página carregar
            time.sleep(2)
            
            # Capturar informações do protocolo
            # (implementar conforme estrutura real da página)
            
            return {
                'protocolo': protocolo,
                'status': 'consultado',
                'detalhes': {}
            }
            
        except Exception as e:
            logger.error(f"Erro ao consultar protocolo: {e}")
            return {
                'erro': str(e)
            }
    
    def fechar(self):
        """Fecha o navegador e limpa recursos"""
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
            logger.error(f"Erro ao fechar cliente: {e}")


# Funções auxiliares para uso direto
def criar_agendamento_tenda(separacao_lote_id, headless=True):
    """
    Função de conveniência para criar agendamento a partir de um lote de separação
    
    Args:
        separacao_lote_id: ID do lote de separação
        headless: Se deve executar em modo headless
        
    Returns:
        Dict com resultado do agendamento
    """
    from app.separacao.models import Separacao
    
    cliente = TendaPlaywrightClient(headless=headless)
    
    try:
        # Buscar dados da separação
        itens = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).all()
        
        if not itens:
            return {'sucesso': False, 'erro': 'Lote não encontrado'}
        
        primeiro_item = itens[0]
        
        # Buscar local de entrega
        local = LocalEntregaDeParaTenda.obter_local_entrega(primeiro_item.cnpj_cpf)
        if not local:
            return {'sucesso': False, 'erro': 'Local de entrega não cadastrado'}
        
        # Preparar dados do agendamento
        dados_agendamento = {
            'cnpj_cliente': primeiro_item.cnpj_cpf,
            'local_entrega_id': local['id_portal'],
            'data_agendamento': primeiro_item.agendamento or (date.today() + timedelta(days=2)),
            'horario': '09:00',
            'tipo_veiculo': 'TRUCK',
            'tipo_carga': 'PALETIZADA',
            'tipo_volume': 'PALLET',
            'quantidade_volume': sum(item.pallet or 0 for item in itens),
            'produtos': []  # Seria preenchido com os EANs
        }
        
        # Iniciar sessão
        cliente.iniciar_sessao()
        
        # Verificar se precisa fazer login
        cliente.page.goto(cliente.config['urls']['base'])
        if not cliente.page.query_selector(cliente.config['seletores']['usuario_logado']):
            if not cliente.fazer_login_automatico():
                cliente.fazer_login_manual()
        
        # Criar agendamento
        resultado = cliente.criar_agendamento(dados_agendamento)
        
        return resultado
        
    finally:
        cliente.fechar()