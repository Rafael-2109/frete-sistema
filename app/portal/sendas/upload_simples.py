#!/usr/bin/env python3
"""
Script simplificado para fazer upload no Sendas
Foca apenas no essencial para fazer funcionar
"""

import asyncio
import os
import sys
import logging

# Adicionar o caminho do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.portal.sendas.sendas_playwright import SendasPortal # noqa: E402
from app.portal.sendas.normalizar_com_libreoffice import normalizar_planilha_sendas # noqa: E402

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def upload_simples(arquivo_xlsx: str):
    """Upload simplificado - apenas o essencial"""
    
    if not os.path.exists(arquivo_xlsx):
        logger.error(f"❌ Arquivo não existe: {arquivo_xlsx}")
        return False
    
    # NORMALIZAR COM LIBREOFFICE (converte para sharedStrings)
    logger.info("🔧 Normalizando com LibreOffice (abrir/salvar)...")
    sucesso_norm, arquivo_normalizado = normalizar_planilha_sendas(arquivo_xlsx)
    
    if sucesso_norm:
        logger.info(f"✅ Arquivo normalizado com template: {arquivo_normalizado}")
        arquivo_para_upload = arquivo_normalizado
    else:
        logger.warning("⚠️ Normalização falhou, usando arquivo original")
        arquivo_para_upload = arquivo_xlsx
    
    portal = SendasPortal(headless=False)  # Ver o que está acontecendo
    
    try:
        # 1. Iniciar e fazer login
        logger.info("🌐 Iniciando navegador...")
        await portal.iniciar_navegador()
        
        logger.info("🔐 Fazendo login...")
        if not await portal.fazer_login():
            logger.error("❌ Login falhou")
            return False
        
        # 2. Ir direto para Gestão de Pedidos
        logger.info("📦 Navegando para Gestão de Pedidos...")
        await portal.page.goto("https://plataforma.trizy.com.br/#/terminal/painel")
        await portal.page.wait_for_timeout(2000)
        
        # Menu > Gestão de Pedidos
        await portal.page.get_by_label("Menu").click()
        await portal.page.wait_for_timeout(1000)
        await portal.page.get_by_role("button", name="Gestão de Pedidos").click()
        await portal.page.wait_for_timeout(3000)
        
        # --- após ir para "Gestão de Pedidos", antes do AÇÕES > CONSUMIR ITENS ---
        iframe = portal.page.frame_locator("#iframe-servico")

        # 1) pegar o JWT do cookie trizy_access_token ou storage
        jwt = None
        for c in await portal.page.context.cookies():
            if c["name"] == "trizy_access_token": # pyright: ignore[reportTypedDictNotRequiredAccess]
                jwt = c["value"] # pyright: ignore[reportTypedDictNotRequiredAccess]
                break
        if not jwt:
            jwt = await portal.page.evaluate("""
                () => localStorage.getItem('trizy_access_token')
                    || sessionStorage.getItem('trizy_access_token')
                    || localStorage.getItem('access_token')
                    || sessionStorage.getItem('access_token')
            """)

        # 2) mandar via postMessage para o iFrame (o front do MRO ouve isso e seta o header)
        if jwt:
            # envie 2x com pequeno atraso para garantir que o iFrame já está pronto
            for _ in range(2):
                await portal.page.evaluate("""
                    (tok) => {
                    const ifr = document.querySelector('#iframe-servico');
                    if (ifr && ifr.contentWindow) {
                        ifr.contentWindow.postMessage({ token: tok, modulo_gped: 1 }, '*');
                    }
                    }
                """, jwt)
                await portal.page.wait_for_timeout(400)

        
        # Preparar captura de resposta ANTES de abrir o menu
        upload_response = {"hit": False, "ok": False, "status": None, "body": None}
        
        async def _capture_body(resp):
            try:
                body = await resp.json()
            except Exception:
                try:
                    body = await resp.text()
                except Exception:
                    body = None
            return body
        
        async def on_response_async(response):
            if "/empresa/demanda/consumoExcelUpload" in response.url:
                logger.info(f"🎯 Capturado upload para: {response.url}")
                upload_response["hit"] = True
                upload_response["status"] = response.status
                upload_response["body"] = await _capture_body(response)
                # considerar sucesso apenas se JSON tiver statusCode 200
                try:
                    if isinstance(upload_response["body"], dict) and upload_response["body"].get("statusCode") == 200:
                        upload_response["ok"] = True
                except Exception:
                    pass
        
        # Adicionar listener assíncrono
        portal.page.on("response", lambda r: asyncio.create_task(on_response_async(r)))
        
        # AÇÕES > CONSUMIR ITENS
        logger.info("🔘 Abrindo menu de consumo...")
        await iframe.get_by_role("button", name="AÇÕES").click()
        await portal.page.wait_for_timeout(1000)
        await iframe.get_by_role("menuitem", name="CONSUMIR ITENS").click()
        await portal.page.wait_for_timeout(2000)
        
        # 4. Tentar pelo botão de upload (abrir modal)
        logger.info("🔍 Procurando botão 'Upload da planilha'...")
        
        btn_upload = iframe.locator('button:has-text("Upload da planilha")').first
        if await btn_upload.is_visible(timeout=2000):
            logger.info("✅ Botão 'Upload da planilha' encontrado")
            await btn_upload.click()
            await portal.page.wait_for_timeout(2000)
            
            # Procurar input no modal
            logger.info("🔍 Procurando input no modal...")
            modal = iframe.locator('.rs-modal').first
            if await modal.is_visible(timeout=2000):
                modal_inputs = await modal.locator('input[type="file"]').all()
                if modal_inputs:
                    logger.info(f"📁 {len(modal_inputs)} inputs encontrados no modal")
                    for i, input_elem in enumerate(modal_inputs):
                        try:
                            logger.info(f"📤 Enviando arquivo para input {i+1}...")
                            await input_elem.set_input_files(arquivo_para_upload)
                            logger.info("✅ Arquivo enviado, aguardando resposta...")
                            break
                        except Exception as e:
                            logger.warning(f"⚠️ Erro no input {i+1}: {e}")
                else:
                    logger.error("❌ Nenhum input encontrado no modal")
            else:
                logger.error("❌ Modal não apareceu")
        else:
            # Tentar outros botões se o principal não existir
            logger.info("⚠️ Botão principal não encontrado, tentando alternativas...")
            for seletor in ['button:has-text("UPLOAD")', '.upload-button']:
                btn = iframe.locator(seletor).first
                if await btn.is_visible(timeout=1000):
                    logger.info(f"✅ Botão alternativo encontrado: {seletor}")
                    await btn.click()
                    await portal.page.wait_for_timeout(2000)
                    break
        
        # Aguardar resposta do servidor (máximo 30 segundos)
        logger.info("⏳ Aguardando resposta do servidor...")
        for _ in range(60):  # 30 segundos (60 x 500ms)
            if upload_response["hit"]:
                break
            await portal.page.wait_for_timeout(500)
        
        # Avaliar resultado real
        if not upload_response["hit"]:
            logger.error("❌ Nenhuma resposta do endpoint de upload foi capturada")
            logger.error("   Possíveis causas:")
            logger.error("   - O endpoint pode estar em outro domínio")
            logger.error("   - O upload pode não ter sido disparado")
            logger.error("   - Token JWT pode estar inválido")
            return False
        
        logger.info(f"🛰️ Upload HTTP status: {upload_response['status']}")
        logger.info(f"🧾 Corpo da resposta: {str(upload_response['body'])[:500]}")
        
        if not upload_response["ok"]:
            logger.error("❌ Upload rejeitado pela API")
            if upload_response["body"]:
                if isinstance(upload_response["body"], dict):
                    logger.error(f"   Mensagem: {upload_response['body'].get('message', 'Sem mensagem')}")
                    logger.error(f"   StatusCode: {upload_response['body'].get('statusCode', 'N/A')}")
                else:
                    logger.error(f"   Resposta: {upload_response['body'][:200]}")
            return False
        
        logger.info("✅ Upload confirmado pela API (statusCode 200)")
        
        # 5. CONFIRMAR DEMANDA após upload bem-sucedido
        logger.info("🔍 Procurando botão CONFIRMAR DEMANDA...")
        
        # Aguardar um pouco para o botão aparecer
        await portal.page.wait_for_timeout(2000)
        
        # Fechar modal se ainda estiver aberto
        close_btn = iframe.locator('.rs-modal-header-close').first
        if await close_btn.is_visible(timeout=1000):
            logger.info("🔒 Fechando modal...")
            await close_btn.click()
            await portal.page.wait_for_timeout(1000)
        
        # Procurar botão CONFIRMAR DEMANDA
        confirm_selectors = [
            'button:has-text("CONFIRMAR DEMANDA")',
            'button.rs-btn-primary:has-text("CONFIRMAR DEMANDA")',
            '.rs-btn.rs-btn-primary:has-text("CONFIRMAR DEMANDA")',
            'button[type="button"]:has-text("CONFIRMAR DEMANDA")'
        ]
        
        confirmado = False
        for selector in confirm_selectors:
            btn_confirmar = iframe.locator(selector).first
            if await btn_confirmar.is_visible(timeout=2000):
                logger.info(f"✅ Botão CONFIRMAR DEMANDA encontrado")
                await btn_confirmar.click()
                logger.info("🖱️ Clicou em CONFIRMAR DEMANDA")
                
                # Aguardar processamento
                await portal.page.wait_for_timeout(3000)
                
                # Verificar se apareceu mensagem de sucesso
                success_msgs = [
                    '.alert-success',
                    '.rs-notification-item-success',
                    'text=/.*confirmad.*/i',
                    'text=/.*sucesso.*/i'
                ]
                
                for msg_selector in success_msgs:
                    if await iframe.locator(msg_selector).is_visible(timeout=1000):
                        logger.info("✅ Confirmação realizada com sucesso!")
                        confirmado = True
                        break
                
                # Verificar se há mensagem de erro
                if not confirmado:
                    error_msgs = ['.alert-danger', '.rs-notification-item-error']
                    for err_selector in error_msgs:
                        if await iframe.locator(err_selector).is_visible(timeout=1000):
                            msg = await iframe.locator(err_selector).text_content()
                            logger.error(f"❌ Erro na confirmação: {msg}")
                
                break
        
        if not confirmado:
            logger.warning("⚠️ Botão CONFIRMAR DEMANDA não encontrado ou confirmação não necessária")
            logger.info("   (Upload já foi realizado com sucesso)")
        else:
            logger.info("✅ DEMANDA CONFIRMADA COM SUCESSO!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        return False
    finally:
        await portal.fechar()


async def main():
    """Função principal"""
    
    # Arquivo para testar
    arquivo = sys.argv[1] if len(sys.argv) > 1 else "/tmp/sendas_multi_20250910_203434.xlsx"
    
    if not os.path.exists(arquivo):
        # Procurar arquivo mais recente
        import glob
        arquivos = sorted(glob.glob("/tmp/sendas*.xlsx"))
        if arquivos:
            arquivo = arquivos[-1]
            logger.info(f"📁 Usando arquivo: {arquivo}")
        else:
            logger.error("❌ Nenhum arquivo Excel encontrado")
            return False
    
    logger.info("=" * 60)
    logger.info("TESTE DE UPLOAD SIMPLES")
    logger.info("=" * 60)
    logger.info(f"📁 Arquivo: {arquivo}")
    
    sucesso = await upload_simples(arquivo)
    
    if sucesso:
        logger.info("✅ UPLOAD BEM-SUCEDIDO!")
    else:
        logger.error("❌ UPLOAD FALHOU!")
    
    return sucesso


if __name__ == "__main__":
    asyncio.run(main())