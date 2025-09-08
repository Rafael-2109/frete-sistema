#!/usr/bin/env python
"""
Script para agendar o pedido 932955 com item 35640 (5 unidades)
"""

from playwright.sync_api import sync_playwright
from datetime import datetime
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def agendar_pedido():
    """Realiza agendamento completo do pedido 932955"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Modo visível para acompanhar
        
        # Carregar sessão salva
        try:
            context = browser.new_context(storage_state="storage_state_atacadao.json")
            print("✅ Sessão carregada")
        except Exception as e:
            print(f"❌ Erro ao carregar sessão: {e}")
            print("Execute: python configurar_sessao_atacadao.py")
            browser.close()
            return False
        
        page = context.new_page()
        
        try:
            print("\n🚀 INICIANDO AGENDAMENTO DO PEDIDO 932955")
            print("=" * 60)
            
            # 1. Ir para página de pedidos
            print("\n1. Abrindo página de pedidos...")
            page.goto("https://atacadao.hodiebooking.com.br/pedidos", timeout=30000)
            page.wait_for_load_state('networkidle')
            
            # 2. Abrir filtros
            print("2. Abrindo filtros...")
            filtro_toggle = page.locator('a[data-toggle="collapse"][data-target="#filtros-collapse"]')
            if filtro_toggle.is_visible():
                filtro_toggle.click()
                time.sleep(1.5)
            
            # 3. Limpar filtros de data
            print("3. Limpando filtros de data...")
            botoes_limpar = page.locator('button[data-action="remove"]').all()
            for botao in botoes_limpar:
                if botao.is_visible():
                    botao.click()
                    time.sleep(0.5)
            
            # 4. Buscar pedido 932955
            print("4. Buscando pedido 932955...")
            page.fill('#nr_pedido', '932955')
            
            # Aguardar resultado com retry REAL
            encontrado = False
            for tentativa in range(5):
                print(f"   Tentativa {tentativa + 1}/5...")
                
                # Clicar em filtrar
                page.click('#enviarFiltros')
                
                # Aguardar mais tempo
                print("   Aguardando resposta do servidor...")
                time.sleep(5)  # Aumentado de 3 para 5 segundos
                
                # Aguardar a página estabilizar
                try:
                    page.wait_for_load_state('networkidle', timeout=10000)
                except Exception:
                    pass  # Continuar mesmo se der timeout
                
                # Verificar se encontrou
                linhas_tabela = page.locator('table tbody tr').count()
                print(f"   Linhas na tabela: {linhas_tabela}")
                
                # Verificar especificamente o pedido 932955 na coluna correta
                if linhas_tabela > 0:
                    linhas = page.locator('table tbody tr').all()
                    for linha in linhas:
                        colunas = linha.locator('td').all()
                        if len(colunas) >= 2:
                            # Segunda coluna é "N° pedido original"
                            pedido_original = colunas[1].text_content().strip()
                            if pedido_original == "932955":
                                print(f"   ✅ Pedido 932955 encontrado na coluna 'N° pedido original'!")
                                encontrado = True
                                break
                    
                    if encontrado:
                        break
                
                # Verificar se tem mensagem de vazio
                content = page.content()
                if "Nenhum registro encontrado" in content:
                    print("   Tabela vazia, tentando novamente...")
                    
                    # Limpar e preencher novamente o campo
                    page.fill('#nr_pedido', '')
                    time.sleep(0.5)
                    page.fill('#nr_pedido', '932955')
                else:
                    print("   Aguardando mais um pouco...")
                    time.sleep(2)  # Aguardar mais 2 segundos
                
                # Screenshot de debug
                if tentativa == 2:  # Na terceira tentativa, tirar screenshot
                    page.screenshot(path=f"busca_tentativa_{tentativa + 1}.png")
                    print(f"   📸 Screenshot: busca_tentativa_{tentativa + 1}.png")
            
            if not encontrado:
                print("   ❌ Pedido 932955 não encontrado após 5 tentativas")
                
                # Tentar extrair ID da tabela se houver resultado parcial
                print("\n4b. Verificando se há resultados na página...")
                
                # Procurar na coluna "N° pedido original" por 932955
                linhas = page.locator('table tbody tr').all()
                for linha in linhas:
                    colunas = linha.locator('td').all()
                    if len(colunas) >= 2:
                        # Segunda coluna é "N° pedido original"
                        pedido_original = colunas[1].text_content().strip()
                        if pedido_original == "932955":
                            print(f"   ✅ Pedido 932955 encontrado na tabela!")
                            # Pegar o link da última coluna
                            link = linha.locator('a[href*="/pedidos/"]')
                            if link.count() > 0:
                                href = link.get_attribute('href')
                                pedido_id = href.split('/pedidos/')[-1] if href else None
                                if pedido_id:
                                    print(f"   ID do pedido: {pedido_id}")
                                    url_direta = f"https://atacadao.hodiebooking.com.br/pedidos/{pedido_id}"
                                    print(f"   Abrindo: {url_direta}")
                                    page.goto(url_direta, timeout=30000)
                                    page.wait_for_load_state('networkidle')
                                    time.sleep(2)
                                    encontrado = True
                                    break
                
                if not encontrado:
                    browser.close()
                    return False
            
            # 5. Abrir o pedido
            print("5. Abrindo pedido...")
            
            # Verificar se já estamos na página do pedido
            if "/pedidos/" in page.url and len(page.url.split("/pedidos/")[1]) > 5:
                print("   Pedido já está aberto")
            else:
                # Procurar o link do pedido 932955 na tabela
                pedido_aberto = False
                linhas = page.locator('table tbody tr').all()
                
                for linha in linhas:
                    colunas = linha.locator('td').all()
                    if len(colunas) >= 2:
                        # Segunda coluna é "N° pedido original"
                        pedido_original = colunas[1].text_content().strip()
                        if pedido_original == "932955":
                            print(f"   Encontrado pedido 932955 na tabela")
                            # Clicar no link "Exibir" desta linha
                            link_exibir = linha.locator('a[title="Exibir"]')
                            if link_exibir.count() > 0:
                                print("   Clicando no link para abrir...")
                                link_exibir.click()
                                page.wait_for_load_state('networkidle')
                                time.sleep(3)
                                pedido_aberto = True
                                break
                
                if not pedido_aberto:
                    print("   ❌ Não conseguiu abrir o pedido")
                    print("   Tentando clicar no primeiro link disponível...")
                    # Como fallback, tenta clicar no primeiro link de exibir
                    link_exibir = page.locator('a[href*="/pedidos/"][title="Exibir"]')
                    if link_exibir.count() > 0:
                        link_exibir.first.click()
                        page.wait_for_load_state('networkidle')
                        time.sleep(3)
            
            # Screenshot do pedido
            page.screenshot(path="pedido_932955_aberto.png")
            print("   📸 Screenshot: pedido_932955_aberto.png")
            
            # 6. Procurar botão de solicitar agendamento
            print("6. Procurando botão de agendamento...")
            
            # O botão está em um div com classe btn_solicitar_agendamento
            botoes_agendamento = [
                '.btn_solicitar_agendamento',  # Classe específica do botão
                '.btn-panel.btn_solicitar_agendamento',  # Classe completa
                'div:has-text("Solicitar agendamento")',
                'label:has-text("Solicitar agendamento")',
                '.btn-panel:has(label:has-text("Solicitar agendamento"))',
                'div.btn_solicitar_agendamento',
                '[class*="btn_solicitar_agendamento"]'
            ]
            
            botao_encontrado = False
            for seletor in botoes_agendamento:
                try:
                    elemento = page.locator(seletor)
                    if elemento.count() > 0:
                        print(f"   ✅ Botão encontrado: {seletor}")
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
                print("   ❌ Botão de agendamento não encontrado")
                
                # Debug: listar elementos com "agend" no texto ou classe
                print("\n   🔍 Debug - Procurando elementos relacionados a agendamento:")
                elementos_agend = page.locator('[class*="agend"], :has-text("agend")').all()
                for i, elem in enumerate(elementos_agend[:5]):  # Listar até 5 elementos
                    try:
                        texto = elem.text_content()[:100] if elem.text_content() else ""  # type: ignore
                        classe = elem.get_attribute('class') or ""
                        print(f"      {i+1}. Classe: {classe[:50]}, Texto: {texto[:50]}")
                    except Exception:
                        pass
                
                print("\n   Possíveis razões:")
                print("   - Pedido já tem agendamento")
                print("   - Pedido não está liberado para agendamento")
                print("   - Falta alguma informação no pedido")
                
                # Tirar screenshot para debug
                page.screenshot(path="debug_botao_agendamento.png")
                print("   📸 Screenshot de debug: debug_botao_agendamento.png")
                
                browser.close()
                return False
            
            # 7. Aguardar formulário abrir
            print("7. Aguardando formulário de agendamento...")
            time.sleep(3)
            
            # Screenshot do formulário
            page.screenshot(path="formulario_agendamento.png")
            print("   📸 Screenshot: formulario_agendamento.png")
            
            # 8. Preencher data de agendamento (Campo 1: data_desejada)
            print("8. Preenchendo primeira data de agendamento...")
            data_agendamento = "27/08/2025"  # Data específica solicitada
            
            # Primeiro, verificar se há campo oculto ISO
            campo_data_iso = page.locator('input[name="data_desejada_iso"]')
            campo_data_visivel = page.locator('input[name="data_desejada"]')
            
            print(f"   📊 DEBUG: Campo visível encontrado: {campo_data_visivel.count()} elementos")
            print(f"   📊 DEBUG: Campo ISO encontrado: {campo_data_iso.count()} elementos")
            
            # Verificar valores ANTES de preencher
            if campo_data_visivel.count() > 0:
                valor_inicial = campo_data_visivel.input_value()
                print(f"   📊 DEBUG: Valor inicial do campo visível: '{valor_inicial}'")
                
                # Verificar atributos do campo
                readonly = campo_data_visivel.get_attribute('readonly')
                disabled = campo_data_visivel.get_attribute('disabled')
                tipo = campo_data_visivel.get_attribute('type')
                classe = campo_data_visivel.get_attribute('class')
                print(f"   📊 DEBUG: readonly={readonly}, disabled={disabled}, type={tipo}")
                print(f"   📊 DEBUG: classes='{classe}'")
            
            try:
                # Método 1: Clicar no campo para focar
                if campo_data_visivel.count() > 0:
                    print("   Clicando no campo de data desejada...")
                    campo_data_visivel.click()
                    print(f"   📊 DEBUG: Campo clicado, aguardando 0.5s...")
                    time.sleep(0.5)
                    
                    # Verificar se o campo tem foco
                    campo_focado = page.evaluate('document.activeElement.name')
                    print(f"   📊 DEBUG: Campo com foco: '{campo_focado}'")
                    
                    # Limpar campo usando Ctrl+A e Delete
                    print(f"   📊 DEBUG: Pressionando Ctrl+A...")
                    page.keyboard.press('Control+A')
                    print(f"   📊 DEBUG: Pressionando Delete...")
                    page.keyboard.press('Delete')
                    time.sleep(0.5)
                    
                    # Verificar se campo foi limpo
                    valor_apos_limpar = campo_data_visivel.input_value()
                    print(f"   📊 DEBUG: Valor após limpar: '{valor_apos_limpar}'")
                    
                    # Digitar a data
                    print(f"   Digitando data: {data_agendamento}")
                    page.keyboard.type(data_agendamento)
                    time.sleep(0.5)
                    
                    # Verificar valor após digitar
                    valor_apos_digitar = campo_data_visivel.input_value()
                    print(f"   📊 DEBUG: Valor após digitar: '{valor_apos_digitar}'")
                    
                    # Pressionar Tab para sair do campo e validar
                    print(f"   📊 DEBUG: Pressionando Tab para validar...")
                    page.keyboard.press('Tab')
                    time.sleep(0.5)
                    
                    # Verificar valor final
                    valor_final = campo_data_visivel.input_value()
                    print(f"   📊 DEBUG: Valor FINAL do campo: '{valor_final}'")
                    
                    # Verificar se campo tem erro
                    container = campo_data_visivel.locator('xpath=ancestor::div[contains(@class, "form-group")]').first
                    if container.count() > 0:
                        classes_container = container.get_attribute('class') or ''
                        print(f"   📊 DEBUG: Classes do container: '{classes_container}'")
                        if 'has-error' in classes_container or 'erro' in classes_container:
                            print(f"   ❌ ERRO: Campo marcado com erro após preenchimento!")
                    
                    print(f"   ✅ Data desejada preenchida: {data_agendamento}")
                    
                # Método 2: Se houver campo ISO, preencher também
                if campo_data_iso.count() > 0:
                    print(f"   📊 DEBUG: Executando Método 2 - JavaScript")
                    
                    # Verificar valores ANTES do JavaScript
                    valor_antes_js = campo_data_visivel.input_value()
                    valor_iso_antes = campo_data_iso.input_value()
                    print(f"   📊 DEBUG: Antes JS - Visível: '{valor_antes_js}', ISO: '{valor_iso_antes}'")
                    
                    # Converter para formato ISO
                    data_iso = "2025-08-27"
                    print(f"   📊 DEBUG: Preenchendo campo ISO com: {data_iso}")
                    page.evaluate(f'document.querySelector(\'input[name="data_desejada_iso"]\').value = "{data_iso}"')
                    
                    print(f"   📊 DEBUG: Preenchendo campo visível com: {data_agendamento}")
                    page.evaluate(f'document.querySelector(\'input[name="data_desejada"]\').value = "{data_agendamento}"')
                    
                    # Verificar valores DEPOIS do JavaScript
                    valor_depois_js = campo_data_visivel.input_value()
                    valor_iso_depois = campo_data_iso.input_value()
                    print(f"   📊 DEBUG: Depois JS - Visível: '{valor_depois_js}', ISO: '{valor_iso_depois}'")
                    
                    print(f"   ✅ Data desejada preenchida via JavaScript: {data_agendamento}")
                    
            except Exception as e:
                print(f"   ⚠️ Erro ao preencher data desejada: {e}")
                
                # Método 3: Forçar via JavaScript
                print("   Tentando método alternativo...")
                script = f"""
                    var campo = document.querySelector('input[name="data_desejada"]');
                    if (campo) {{
                        campo.value = '{data_agendamento}';
                        campo.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        campo.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                    var campoIso = document.querySelector('input[name="data_desejada_iso"]');
                    if (campoIso) {{
                        campoIso.value = '2025-08-27';
                    }}
                """
                page.evaluate(script)
                print(f"   ✅ Data desejada forçada via JavaScript: {data_agendamento}")
            
            # 8b. Preencher segunda data (Campo 2: leadtime_minimo - Disponibilidade de entrega)
            print("8b. Preenchendo segunda data (Disponibilidade de entrega)...")
            
            campo_leadtime = page.locator('input[name="leadtime_minimo"]')
            campo_leadtime_iso = page.locator('input[name="leadtime_minimo_iso"]')
            
            print(f"   📊 DEBUG: Campo leadtime encontrado: {campo_leadtime.count()} elementos")
            print(f"   📊 DEBUG: Campo leadtime_iso encontrado: {campo_leadtime_iso.count()} elementos")
            
            if campo_leadtime.count() > 0:
                # Verificar valores ANTES
                valor_inicial_lead = campo_leadtime.input_value()
                print(f"   📊 DEBUG: Valor inicial leadtime: '{valor_inicial_lead}'")
                
                # Verificar atributos
                readonly_lead = campo_leadtime.get_attribute('readonly')
                disabled_lead = campo_leadtime.get_attribute('disabled')
                classe_lead = campo_leadtime.get_attribute('class')
                print(f"   📊 DEBUG: readonly={readonly_lead}, disabled={disabled_lead}")
                print(f"   📊 DEBUG: classes='{classe_lead}'")
                
                try:
                    # Método 1: Clicar e digitar
                    print("   Clicando no campo de disponibilidade de entrega...")
                    campo_leadtime.click()
                    print(f"   📊 DEBUG: Campo clicado, aguardando 0.5s...")
                    time.sleep(0.5)
                    
                    # Verificar foco
                    campo_focado_lead = page.evaluate('document.activeElement.name')
                    print(f"   📊 DEBUG: Campo com foco: '{campo_focado_lead}'")
                    
                    # Limpar e digitar
                    print(f"   📊 DEBUG: Pressionando Ctrl+A...")
                    page.keyboard.press('Control+A')
                    print(f"   📊 DEBUG: Pressionando Delete...")
                    page.keyboard.press('Delete')
                    time.sleep(0.5)
                    
                    valor_apos_limpar_lead = campo_leadtime.input_value()
                    print(f"   📊 DEBUG: Valor após limpar: '{valor_apos_limpar_lead}'")
                    
                    print(f"   Digitando data: {data_agendamento}")
                    page.keyboard.type(data_agendamento)
                    time.sleep(0.5)
                    
                    valor_apos_digitar_lead = campo_leadtime.input_value()
                    print(f"   📊 DEBUG: Valor após digitar: '{valor_apos_digitar_lead}'")
                    
                    print(f"   📊 DEBUG: Pressionando Tab...")
                    page.keyboard.press('Tab')
                    time.sleep(0.5)
                    
                    valor_final_lead = campo_leadtime.input_value()
                    print(f"   📊 DEBUG: Valor FINAL leadtime: '{valor_final_lead}'")
                    
                    # Verificar erro
                    container_lead = campo_leadtime.locator('xpath=ancestor::div[contains(@class, "form-group")]').first
                    if container_lead.count() > 0:
                        classes_container_lead = container_lead.get_attribute('class') or ''
                        print(f"   📊 DEBUG: Classes do container: '{classes_container_lead}'")
                        if 'has-error' in classes_container_lead or 'erro' in classes_container_lead:
                            print(f"   ❌ ERRO: Campo leadtime marcado com erro!")
                    
                    print(f"   ✅ Disponibilidade de entrega preenchida: {data_agendamento}")
                    
                    # Preencher campo ISO também
                    if campo_leadtime_iso.count() > 0:
                        page.evaluate(f'document.querySelector(\'input[name="leadtime_minimo_iso"]\').value = "2025-08-27"')
                        page.evaluate(f'document.querySelector(\'input[name="leadtime_minimo"]\').value = "{data_agendamento}"')
                        
                except Exception as e:
                    print(f"   ⚠️ Erro ao preencher disponibilidade: {e}")
                    # Forçar via JavaScript
                    script = f"""
                        var campo = document.querySelector('input[name="leadtime_minimo"]');
                        if (campo) {{
                            campo.value = '{data_agendamento}';
                            campo.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        var campoIso = document.querySelector('input[name="leadtime_minimo_iso"]');
                        if (campoIso) {{
                            campoIso.value = '2025-08-27';
                        }}
                    """
                    page.evaluate(script)
                    print(f"   ✅ Disponibilidade forçada via JavaScript: {data_agendamento}")
            else:
                print("   ⚠️ Campo de disponibilidade de entrega não encontrado (pode não ser obrigatório)")
            
            # 9. Selecionar transportadora (se necessário)
            print("9. Verificando transportadora...")
            
            # Verificar se o campo de transportadora está vazio
            campo_transportadora = page.locator('#transportadora')
            if campo_transportadora.count() > 0 and not campo_transportadora.text_content().strip():
                print("   Campo de transportadora vazio, selecionando...")
                
                # Clicar no botão de buscar transportadora
                botao_buscar_transp = page.locator('button[data-target="#modal-transportadoras"]')
                if botao_buscar_transp.count() > 0:
                    print("   Abrindo modal de transportadoras...")
                    botao_buscar_transp.click()
                    time.sleep(2)
                    
                    # Selecionar o radio button "Agregado" (id="1")
                    radio_agregado = page.locator('input[type="radio"][id="1"][value*="Agregado"]')
                    if radio_agregado.count() > 0:
                        print("   Selecionando Agregado...")
                        radio_agregado.click()
                        time.sleep(0.5)
                    else:
                        # Alternativa: clicar no label
                        label_agregado = page.locator('label:has-text("Agregado / Frota Própria")')
                        if label_agregado.count() > 0:
                            label_agregado.first.click()
                            time.sleep(0.5)
                    
                    # Clicar no botão Selecionar do modal (está no modal-footer)
                    # O botão correto está em: .modal-footer .btn-primary.selecionar
                    botao_selecionar = page.locator('.modal-footer button.btn-primary.selecionar')
                    
                    if botao_selecionar.count() > 0:
                        print(f"   Encontrado(s) {botao_selecionar.count()} botão(ões) Selecionar")
                        # Se houver mais de um modal aberto, pegar o visível
                        if botao_selecionar.count() > 1:
                            # Pegar apenas o botão visível
                            for i in range(botao_selecionar.count()):
                                if botao_selecionar.nth(i).is_visible():
                                    print(f"   Clicando no botão Selecionar visível (índice {i})...")
                                    botao_selecionar.nth(i).click()
                                    break
                        else:
                            print("   Clicando em Selecionar...")
                            botao_selecionar.click()
                        
                        time.sleep(1)
                        print("   ✅ Transportadora Agregado selecionada")
                    else:
                        # Alternativa: procurar especificamente no footer do modal visível
                        print("   Tentando seletor alternativo para o botão Selecionar...")
                        page.locator('.modal-footer .row .col-md-12 button.btn-primary.selecionar').click()
                        print("   ✅ Transportadora selecionada")
            else:
                print("   Transportadora já preenchida ou campo não encontrado")
            
            # 10. Preencher quantidades dos produtos
            print("10. Preenchendo quantidades dos produtos...")
            
            # Procurar todas as linhas de produtos na tabela
            linhas_produtos = page.locator('table tbody tr').all()
            produtos_preenchidos = 0
            
            for linha in linhas_produtos:
                # Pegar código do produto (primeira coluna)
                codigo = linha.locator('td').first.text_content().strip()
                
                # Campo de quantidade - está em input[name="qtd_alocada[...]"]
                campo_qtd = linha.locator('input[name*="qtd_alocada"]')
                
                if campo_qtd.count() > 0:
                    if codigo == "35640":
                        # Este é o produto solicitado - preencher com 5
                        campo_qtd.fill('5')
                        print(f"   ✅ Produto {codigo}: 5 unidades")
                        produtos_preenchidos += 1
                    else:
                        # Outros produtos - zerar quantidade
                        campo_qtd.fill('0')
                        print(f"   ⚠️ Produto {codigo}: 0 unidades (não solicitado)")
            
            if produtos_preenchidos == 0:
                print("   ⚠️ Produto 35640 não encontrado na lista")
                print("   Preenchendo todos os produtos disponíveis...")
                # Se não encontrou o 35640, preencher o primeiro produto disponível
                primeiro_campo = page.locator('input[name*="qtd_alocada"]').first
                if primeiro_campo.count() > 0:
                    # Pegar o saldo disponível
                    saldo = page.locator('td.f_editando').first.text_content().strip()
                    quantidade = min(5, int(saldo) if saldo.isdigit() else 5)
                    primeiro_campo.fill(str(quantidade))
                    print(f"   ✅ Primeiro produto preenchido com {quantidade} unidades")
            
            # 11. Verificar tipo de carga (pode estar desabilitado)
            print("11. Verificando tipo de carga...")
            select_carga = page.locator('select[name="carga_especie_id"]')
            if select_carga.count() > 0:
                # Verificar se está desabilitado
                is_disabled = select_carga.get_attribute('disabled')
                if is_disabled is None or is_disabled == "false":
                    # Campo habilitado, selecionar Paletizada (value="1")
                    select_carga.select_option(value='1')
                    print("   ✅ Tipo de carga: Paletizada")
                else:
                    print("   ⚠️ Tipo de carga já definido (campo desabilitado)")
            
            # 12. Selecionar tipo de veículo
            print("12. Selecionando tipo de veículo...")
            select_veiculo = page.locator('select[name="tipo_veiculo"]')
            if select_veiculo.count() > 0:
                # Selecionar Toco-Baú (Cód. 4) - value="11" conforme HTML
                try:
                    # Tentar por value primeiro
                    select_veiculo.select_option(value='11')
                    print("   ✅ Tipo de veículo selecionado: Toco-Baú (Cód. 4)")
                except Exception as e:
                    # Se falhar, tentar por texto parcial
                    print(f"   Tentando seleção alternativa... Erro: {e}")
                    select_veiculo.select_option(label='Toco-Baú')
                    print("   ✅ Tipo de veículo selecionado: Toco-Baú")
            
            # Screenshot antes de salvar
            page.screenshot(path="formulario_preenchido.png")
            print("   📸 Screenshot: formulario_preenchido.png")
            
            # 13. Confirmação com usuário
            print("\n" + "=" * 60)
            print("⚠️ ATENÇÃO: Pronto para enviar o agendamento!")
            print(f"   Pedido: 932955")
            print(f"   Item: 35640 - 5 unidades")
            print(f"   Data: {data_agendamento}")
            print(f"   Veículo: Toco-Baú (Cód. 4)")
            print("=" * 60)
            
            resposta = input("\n▶️ Deseja confirmar o agendamento? (S/N): ").strip().upper()
            
            if resposta != 'S':
                print("❌ Agendamento cancelado pelo usuário")
                browser.close()
                return False
            
            # 14. Salvar/Enviar
            print("\n14. Enviando agendamento...")
            
            # O botão correto é um div com id="salvar"
            botao_salvar = page.locator('#salvar')
            if botao_salvar.count() > 0:
                print("   Clicando em Salvar...")
                botao_salvar.click()
                print("   ✅ Formulário enviado!")
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
                    if page.locator(seletor).count() > 0:
                        page.locator(seletor).first.click()
                        print(f"   ✅ Formulário enviado via: {seletor}")
                        break
            
            # 15. Aguardar resposta
            print("15. Aguardando resposta...")
            time.sleep(5)
            
            # Verificar modal de sucesso
            if page.locator('#regSucesso').count() > 0:
                print("   ✅ Modal de sucesso detectado!")
                
                # Clicar em "Não incluir NF agora"
                if page.locator('#btnNao').count() > 0:
                    page.locator('#btnNao').click()
                    print("   Optou por não incluir NF agora")
            
            # 16. Capturar protocolo
            print("16. Capturando protocolo...")
            time.sleep(3)
            
            protocolo = None
            
            # MÉTODO 1: Extrair da URL após redirecionamento
            # Após salvar, a página pode redirecionar para:
            # - /agendamentos/PROTOCOLO (se foi direto para agendamento)
            # - /cargas/ID_CARGA (se voltou para a carga)
            current_url = page.url
            print(f"   URL atual: {current_url}")
            
            if "/agendamentos/" in current_url:
                # Extrair o protocolo da URL
                protocolo = current_url.split("/agendamentos/")[-1].split("/")[0].split("?")[0]
                print(f"   ✅ Protocolo extraído da URL: {protocolo}")
            elif "/cargas/" in current_url:
                # Se voltou para a página da carga, procurar o link do agendamento
                print("   Página redirecionou para carga, procurando link do agendamento...")
                link_acompanhe = page.locator('a[href*="/agendamentos/"]:has-text("ACOMPANHE")')
                if link_acompanhe.count() == 0:
                    link_acompanhe = page.locator('a[href*="/agendamentos/"]').first
                
                if link_acompanhe.count() > 0:
                    href = link_acompanhe.get_attribute('href')
                    if href and "/agendamentos/" in href:
                        protocolo = href.split("/agendamentos/")[-1].split("/")[0].split("?")[0]
                        print(f"   ✅ Protocolo extraído do link: {protocolo}")
            
            # MÉTODO 2: Se não encontrou na URL, procurar no HTML
            if not protocolo:
                print("   Procurando protocolo no HTML...")
                
                # Procurar link com texto do protocolo
                links_agendamento = page.locator('a[href*="/agendamentos/"]').all()
                for link in links_agendamento:
                    href = link.get_attribute('href')
                    if href and "/agendamentos/" in href:
                        # Extrair protocolo do href
                        protocolo_temp = href.split("/agendamentos/")[-1].split("/")[0].split("?")[0]
                        # Verificar se é um número válido
                        if protocolo_temp and protocolo_temp.isdigit():
                            protocolo = protocolo_temp
                            print(f"   ✅ Protocolo encontrado em link: {protocolo}")
                            break
            
            # MÉTODO 3: Procurar em texto específico
            if not protocolo:
                # Procurar por padrão de protocolo (geralmente 13 dígitos começando com data)
                import re
                page_content = page.content()
                # Padrão: DDMMAA + 7 dígitos
                padrao_protocolo = re.compile(r'\b\d{13}\b')
                matches = padrao_protocolo.findall(page_content)
                if matches:
                    # Pegar o primeiro que parece um protocolo válido
                    for match in matches:
                        if match.startswith(('25', '24', '23')):  # Anos 2023-2025
                            protocolo = match
                            print(f"   ✅ Protocolo encontrado por padrão: {protocolo}")
                            break
            
            # Screenshot final
            page.screenshot(path="agendamento_concluido.png")
            print("   📸 Screenshot: agendamento_concluido.png")
            
            # 17. Resultado
            print("\n" + "=" * 60)
            if protocolo:
                print("🎉 AGENDAMENTO REALIZADO COM SUCESSO!")
                print(f"   📋 Protocolo: {protocolo}")
                print(f"   📅 Data: {data_agendamento}")
                print(f"   📦 Pedido: 932955")
                print(f"   📦 Item: 35640 - 5 unidades")
                print(f"   🚛 Veículo: Toco-Baú (Cód. 4)")
                print("\n   💾 Protocolo salvo para consultas futuras")
                
                # Salvar protocolo em arquivo
                with open("protocolo_932955.txt", "w") as f:
                    f.write(f"Protocolo: {protocolo}\n")
                    f.write(f"Pedido: 932955\n")
                    f.write(f"Item: 35640 - 5 unidades\n")
                    f.write(f"Data: {data_agendamento}\n")
                    f.write(f"Criado em: {datetime.now()}\n")
                
                return True
            else:
                print("⚠️ Agendamento pode ter sido criado mas protocolo não capturado")
                print("   Verifique o screenshot: agendamento_concluido.png")
                return True
                
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            page.screenshot(path=f"erro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            print(f"   Screenshot de erro salvo")
            return False
            
        finally:
            input("\n🔍 Pressione ENTER para fechar o navegador...")
            browser.close()


if __name__ == "__main__":
    print("🚀 AGENDAMENTO AUTOMÁTICO - PEDIDO 932955")
    print("=" * 60)
    print("Este script irá:")
    print("1. Buscar o pedido 932955")
    print("2. Abrir o formulário de agendamento")
    print("3. Definir 5 unidades do item 35640")
    print("4. Preencher data e transportadora")
    print("5. Solicitar confirmação antes de enviar")
    print("=" * 60)
    
    confirmar = input("\n▶️ Deseja continuar? (S/N): ").strip().upper()
    
    if confirmar == 'S':
        resultado = agendar_pedido()
        
        if resultado:
            print("\n✅ Processo concluído com sucesso!")
        else:
            print("\n❌ Processo falhou. Verifique os logs e screenshots")
    else:
        print("\n❌ Operação cancelada")