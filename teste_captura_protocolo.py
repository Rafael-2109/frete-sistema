#!/usr/bin/env python3
"""
Script para testar a captura de protocolo após agendamento
"""

import logging
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def testar_captura_protocolo():
    """Testa se o protocolo está sendo capturado corretamente"""
    
    from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient
    
    print("=" * 60)
    print("TESTE DE CAPTURA DE PROTOCOLO")
    print("=" * 60)
    
    client = AtacadaoPlaywrightClient(headless=False)  # Modo visível para debug
    
    try:
        # Iniciar sessão
        client.iniciar_sessao()
        
        # Simular página com protocolo (para teste)
        html_teste = """
        <div class="col-md-12 form-group">
            <label class="orange">Solicitação de agendamento</label>
            <div class="f_exibindo">
                <a href="https://atacadao.hodiebooking.com.br/agendamentos/2508210019148">2508210019148</a>
            </div>
        </div>
        """
        
        # Navegar para uma página de teste
        client.page.goto("data:text/html," + html_teste)
        
        # Testar extração de protocolo
        print("\n🔍 Testando extração de protocolo...")
        
        # Método 1: Buscar pelo label
        try:
            label_agendamento = client.page.locator('label:has-text("Solicitação de agendamento")')
            if label_agendamento.count() > 0:
                link_protocolo = client.page.locator('label:has-text("Solicitação de agendamento") + div a')
                if link_protocolo.count() > 0:
                    protocolo = link_protocolo.first.text_content().strip()
                    print(f"✅ Protocolo capturado: {protocolo}")
                else:
                    print("❌ Link do protocolo não encontrado")
            else:
                print("❌ Label não encontrado")
        except Exception as e:
            print(f"❌ Erro: {e}")
        
        # Método 2: Buscar todos os links
        try:
            links = client.page.locator('a[href*="/agendamentos/"]').all()
            for link in links:
                href = link.get_attribute('href')
                texto = link.text_content().strip()
                if href and "/agendamentos/" in href:
                    protocolo_temp = href.split("/agendamentos/")[-1].split("/")[0].split("?")[0]
                    if protocolo_temp and len(protocolo_temp) == 13:
                        print(f"✅ Protocolo encontrado no href: {protocolo_temp} (texto: {texto})")
        except Exception as e:
            print(f"❌ Erro ao buscar links: {e}")
        
        print("\n✅ Teste concluído!")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
    finally:
        client.fechar()

if __name__ == "__main__":
    testar_captura_protocolo()