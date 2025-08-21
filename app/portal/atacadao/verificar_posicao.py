"""
Função para verificar posição na fila de agendamento do Atacadão
"""

from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient
import logging
import re

logger = logging.getLogger(__name__)

class VerificadorPosicaoAtacadao:
    """Verifica posição na fila de agendamento do Atacadão"""
    
    def __init__(self):
        self.client = None
    
    def verificar_posicao(self, protocolo):
        """
        Verifica a posição na fila de um agendamento
        
        Args:
            protocolo: Número do protocolo do agendamento
            
        Returns:
            dict com informações da posição:
            {
                'success': bool,
                'protocolo': str,
                'status': str (aguardando, confirmado, cancelado),
                'posicao_fila': int ou None,
                'total_fila': int ou None,
                'data_prevista': str ou None,
                'observacoes': str ou None,
                'detalhes': dict com informações adicionais
            }
        """
        try:
            # Iniciar cliente
            self.client = AtacadaoPlaywrightClient(headless=True)
            self.client.iniciar_sessao()
            
            # Verificar login
            if not self.client.verificar_login():
                return {
                    'success': False,
                    'message': 'Sessão expirada. Execute: python configurar_sessao_atacadao.py'
                }
            
            # Navegar para página do agendamento
            url_agendamento = f"https://atacadao.hodiebooking.com.br/agendamentos/{protocolo}"
            logger.info(f"Abrindo agendamento: {url_agendamento}")
            
            self.client.page.goto(url_agendamento, timeout=30000)
            self.client.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Verificar se chegou na página correta
            if "agendamentos" not in self.client.page.url:
                logger.warning(f"Redirecionado para: {self.client.page.url}")
                return {
                    'success': False,
                    'message': 'Protocolo não encontrado ou sem permissão'
                }
            
            # Extrair informações
            resultado = {
                'success': True,
                'protocolo': protocolo,
                'status': None,
                'posicao_fila': None,
                'total_fila': None,
                'data_prevista': None,
                'observacoes': None,
                'detalhes': {}
            }
            
            # 1. Status do agendamento
            try:
                # Procurar por diferentes indicadores de status
                status_selectors = [
                    '.status-agendamento',
                    '.badge-status',
                    '[class*="status"]',
                    'span:has-text("Aguardando")',
                    'span:has-text("Confirmado")',
                    'span:has-text("Cancelado")'
                ]
                
                for selector in status_selectors:
                    if self.client.page.locator(selector).is_visible():
                        status_text = self.client.page.locator(selector).first.text_content()
                        resultado['status'] = status_text.strip().lower()
                        logger.info(f"Status encontrado: {resultado['status']}")
                        break
            except:
                pass
            
            # 2. Posição na fila
            try:
                # Procurar por texto como "Posição: 5 de 20" ou "5º na fila"
                page_text = self.client.page.content()
                
                # Padrões para encontrar posição
                patterns = [
                    r'Posição[:\s]+(\d+)\s+de\s+(\d+)',
                    r'(\d+)[ºª]\s+na\s+fila\s+de\s+(\d+)',
                    r'Você está em\s+(\d+)[ºª]\s+de\s+(\d+)',
                    r'Posição na fila[:\s]+(\d+)/(\d+)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        resultado['posicao_fila'] = int(match.group(1))
                        resultado['total_fila'] = int(match.group(2))
                        logger.info(f"Posição: {resultado['posicao_fila']} de {resultado['total_fila']}")
                        break
            except:
                pass
            
            # 3. Data prevista
            try:
                # Procurar por data prevista
                data_selectors = [
                    '.data-prevista',
                    '[class*="data-agenda"]',
                    'span:has-text("Data prevista")',
                    'span:has-text("Agendado para")'
                ]
                
                for selector in data_selectors:
                    element = self.client.page.locator(selector)
                    if element.is_visible():
                        # Pegar o próximo elemento ou o texto
                        parent = element.locator('..')
                        text = parent.text_content()
                        
                        # Extrair data (formato DD/MM/YYYY)
                        data_match = re.search(r'\d{2}/\d{2}/\d{4}', text)
                        if data_match:
                            resultado['data_prevista'] = data_match.group()
                            logger.info(f"Data prevista: {resultado['data_prevista']}")
                            break
            except:
                pass
            
            # 4. Informações adicionais
            try:
                # Procurar por tabela de detalhes
                if self.client.page.locator('table').is_visible():
                    rows = self.client.page.locator('table tr').all()
                    for row in rows:
                        cells = row.locator('td').all()
                        if len(cells) >= 2:
                            label = cells[0].text_content().strip()
                            value = cells[1].text_content().strip()
                            if label and value:
                                resultado['detalhes'][label] = value
            except:
                pass
            
            # 5. Observações ou mensagens
            try:
                obs_selectors = [
                    '.observacoes',
                    '.alert-info',
                    '.mensagem-agendamento'
                ]
                
                for selector in obs_selectors:
                    if self.client.page.locator(selector).is_visible():
                        resultado['observacoes'] = self.client.page.locator(selector).text_content().strip()
                        break
            except:
                pass
            
            # Screenshot para debug
            self.client.page.screenshot(path=f"posicao_{protocolo}.png")
            logger.info(f"Screenshot salvo: posicao_{protocolo}.png")
            
            # Interpretar resultado
            if resultado['posicao_fila']:
                resultado['message'] = f"Agendamento {protocolo}: Posição {resultado['posicao_fila']} de {resultado['total_fila']} na fila"
            elif resultado['status'] == 'confirmado':
                resultado['message'] = f"Agendamento {protocolo} confirmado"
                if resultado['data_prevista']:
                    resultado['message'] += f" para {resultado['data_prevista']}"
            elif resultado['status'] == 'cancelado':
                resultado['message'] = f"Agendamento {protocolo} foi cancelado"
            else:
                resultado['message'] = f"Status do agendamento {protocolo}: {resultado['status'] or 'Aguardando'}"
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao verificar posição: {e}")
            return {
                'success': False,
                'message': f'Erro ao verificar posição: {str(e)}'
            }
        finally:
            if self.client:
                self.client.fechar()


def verificar_posicao_agendamento(protocolo):
    """Função helper para verificar posição"""
    verificador = VerificadorPosicaoAtacadao()
    return verificador.verificar_posicao(protocolo)


if __name__ == "__main__":
    # Teste
    import sys
    
    if len(sys.argv) > 1:
        protocolo = sys.argv[1]
    else:
        protocolo = input("Digite o número do protocolo: ").strip()
    
    print(f"\n🔍 Verificando posição do protocolo {protocolo}...")
    
    resultado = verificar_posicao_agendamento(protocolo)
    
    if resultado['success']:
        print(f"\n✅ {resultado['message']}")
        
        if resultado['posicao_fila']:
            print(f"   📊 Posição: {resultado['posicao_fila']} de {resultado['total_fila']}")
        
        if resultado['data_prevista']:
            print(f"   📅 Data prevista: {resultado['data_prevista']}")
        
        if resultado['observacoes']:
            print(f"   📝 Observações: {resultado['observacoes']}")
        
        if resultado['detalhes']:
            print("\n   📋 Detalhes:")
            for key, value in resultado['detalhes'].items():
                print(f"      {key}: {value}")
    else:
        print(f"\n❌ {resultado['message']}")