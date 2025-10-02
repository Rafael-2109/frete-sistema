"""
🔲 SERVIÇO DE GERAÇÃO DE QR CODES
Gera QR Codes para acesso ao sistema de rastreamento
"""

import qrcode
from io import BytesIO
import base64
from flask import current_app


class QRCodeService:
    """Serviço para geração de QR Codes"""

    @staticmethod
    def gerar_qrcode(url, tamanho=10, borda=2):
        """
        Gera um QR Code para a URL fornecida

        Args:
            url (str): URL para codificar no QR Code
            tamanho (int): Tamanho do QR Code (1-40, padrão 10)
            borda (int): Tamanho da borda branca (padrão 2)

        Returns:
            str: QR Code em formato base64 para embed em HTML
        """
        try:
            # Configurar QR Code
            qr = qrcode.QRCode(
                version=1,  # Controla o tamanho (1 é o menor)
                error_correction=qrcode.constants.ERROR_CORRECT_H,  # Alta correção de erros
                box_size=tamanho,
                border=borda,
            )

            # Adicionar dados
            qr.add_data(url)
            qr.make(fit=True)

            # Gerar imagem
            img = qr.make_image(fill_color="black", back_color="white")

            # Converter para base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            current_app.logger.error(f"Erro ao gerar QR Code: {str(e)}")
            return None

    @staticmethod
    def gerar_qrcode_arquivo(url, caminho_arquivo, tamanho=10, borda=2):
        """
        Gera um QR Code e salva em arquivo

        Args:
            url (str): URL para codificar
            caminho_arquivo (str): Caminho completo para salvar o arquivo PNG
            tamanho (int): Tamanho do QR Code
            borda (int): Tamanho da borda

        Returns:
            bool: True se sucesso, False se erro
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=tamanho,
                border=borda,
            )

            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            img.save(caminho_arquivo)

            return True

        except Exception as e:
            current_app.logger.error(f"Erro ao salvar QR Code: {str(e)}")
            return False
