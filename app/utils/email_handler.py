"""
Utilitário para processar e armazenar emails .msg e .eml
"""
import os
import json
import extract_msg
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
from typing import Optional, Dict, Any
from app.utils.file_storage import get_file_storage
from email import policy
from email.parser import BytesParser
from dateutil import parser
import email.utils


class EmailHandler:
    """
    Classe para processar emails .msg e .eml usando FileStorage centralizado
    """

    def __init__(self):
        """Inicializa o handler com FileStorage"""
        self.storage = get_file_storage()
    
    def processar_email_msg(self, arquivo_msg) -> Optional[Dict[str, Any]]:
        """
        Processa arquivo .msg e extrai metadados
        
        Args:
            arquivo_msg: FileStorage object do Flask
            
        Returns:
            Dict com metadados do email ou None se erro
        """
        try:
            # Salva temporariamente o arquivo
            temp_path = f"/tmp/{secure_filename(arquivo_msg.filename)}"
            arquivo_msg.save(temp_path)
            
            # Processa o arquivo .msg
            msg = extract_msg.openMsg(temp_path)
            
            # Extrai metadados (garantindo str)
            metadados = {
                'remetente': str(msg.sender or ''),
                'destinatarios': json.dumps(str(msg.to or '').split(';')) if msg.to else '[]',
                'cc': json.dumps(str(msg.cc or '').split(';')) if msg.cc else '[]',
                'bcc': json.dumps(str(msg.bcc or '').split(';')) if hasattr(msg, 'bcc') and msg.bcc else '[]',
                'assunto': str(msg.subject or ''),
                'data_envio': self._parse_date(str(msg.date) if msg.date else ''),
                'tem_anexos': len(msg.attachments) > 0,
                'qtd_anexos': len(msg.attachments),
                'conteudo_preview': str(msg.body or '')[:500],
                'tamanho_bytes': os.path.getsize(temp_path)
            }

            
            # Limpa arquivo temporário
            msg.close()
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return metadados
            
        except Exception as e:
            current_app.logger.error(f"❌ Erro ao processar email .msg: {str(e)}")
            # Limpa arquivo temporário em caso de erro
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            return None

    def processar_email_eml(self, arquivo_eml) -> Optional[Dict[str, Any]]:
        """
        Processa arquivo .eml e extrai metadados

        Args:
            arquivo_eml: FileStorage object do Flask

        Returns:
            Dict com metadados do email ou None se erro
        """
        try:
            # Lê o conteúdo do arquivo
            email_bytes = arquivo_eml.read()

            # Parse do email usando biblioteca nativa
            msg = BytesParser(policy=policy.default).parsebytes(email_bytes)

            # Extrai destinatários
            to_addresses = []
            if msg.get('To'):
                to_addresses = [addr.strip() for addr in msg.get('To').split(',')]

            cc_addresses = []
            if msg.get('Cc'):
                cc_addresses = [addr.strip() for addr in msg.get('Cc').split(',')]

            bcc_addresses = []
            if msg.get('Bcc'):
                bcc_addresses = [addr.strip() for addr in msg.get('Bcc').split(',')]

            # Extrai corpo do email
            body = ''
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_content()
                        break
            else:
                body = msg.get_content()

            # Conta anexos
            qtd_anexos = 0
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_disposition() == 'attachment':
                        qtd_anexos += 1

            # Parse da data
            date_tuple = email.utils.parsedate_to_datetime(msg.get('Date')) if msg.get('Date') else None

            # Salva temporariamente para pegar tamanho
            arquivo_eml.seek(0)  # Volta ao início
            temp_path = f"/tmp/{secure_filename(arquivo_eml.filename)}"
            arquivo_eml.save(temp_path)
            tamanho_bytes = os.path.getsize(temp_path)

            # Extrai metadados
            metadados = {
                'remetente': str(msg.get('From', '')),
                'destinatarios': json.dumps(to_addresses),
                'cc': json.dumps(cc_addresses),
                'bcc': json.dumps(bcc_addresses),
                'assunto': str(msg.get('Subject', '')),
                'data_envio': date_tuple,
                'tem_anexos': qtd_anexos > 0,
                'qtd_anexos': qtd_anexos,
                'conteudo_preview': str(body)[:500] if body else '',
                'tamanho_bytes': tamanho_bytes
            }

            # Limpa arquivo temporário
            if os.path.exists(temp_path):
                os.remove(temp_path)

            return metadados

        except Exception as e:
            current_app.logger.error(f"❌ Erro ao processar email .eml: {str(e)}")
            # Limpa arquivo temporário em caso de erro
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Converte string de data de e-mails para datetime, aceitando múltiplos formatos.
        """
        if not date_str:
            return None

        date_str = date_str.strip().replace('\x00', '')  # Remove NUL chars problemáticos

        try:
            formats = [
                '%a, %d %b %Y %H:%M:%S %z',      # ex: Tue, 28 Oct 2025 17:56:02 +0000
                '%Y-%m-%d %H:%M:%S.%f%z',        # ex: 2025-10-28 17:56:02.756887+00:00
                '%Y-%m-%d %H:%M:%S.%f',          # ex: 2025-10-28 17:56:02.756887
                '%Y-%m-%d %H:%M:%S',             # ex: 2025-10-28 17:56:02
                '%d/%m/%Y %H:%M:%S'              # ex: 28/10/2025 17:56:02
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            # Fallback: usa parser inteligente do dateutil
            return parser.parse(date_str)

        except Exception as e:
            current_app.logger.warning(f"⚠️ Não foi possível parsear data: {date_str} - {str(e)}")
            return None    
    def upload_email(self, arquivo_email, despesa_id: int, usuario: str) -> Optional[str]:
        """
        Faz upload do arquivo .msg ou .eml usando FileStorage centralizado

        Args:
            arquivo_email: FileStorage object
            despesa_id: ID da despesa
            usuario: Nome do usuário

        Returns:
            Caminho do arquivo ou None se erro
        """
        try:
            # Define pasta e nome do arquivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_seguro = secure_filename(arquivo_email.filename)
            nome_final = f"{timestamp}_{nome_seguro}"

            # Usa FileStorage centralizado - aceita .msg e .eml
            caminho = self.storage.save_file(
                file=arquivo_email,
                folder=f"fretes/despesas/{despesa_id}/emails",
                filename=nome_final,
                allowed_extensions=['msg', 'eml']
            )

            if caminho:
                current_app.logger.info(f"✅ Email salvo: {caminho}")
                return caminho
            else:
                current_app.logger.error("❌ Falha ao salvar email")
                return None

        except Exception as e:
            current_app.logger.error(f"❌ Erro no upload do email: {str(e)}")
            return None
    
    def get_email_url(self, caminho: str) -> Optional[str]:
        """
        Gera URL para acessar o email
        
        Args:
            caminho: Caminho do arquivo
            
        Returns:
            URL para download ou None se erro
        """
        try:
            return self.storage.get_file_url(caminho)
        except Exception as e:
            current_app.logger.error(f"❌ Erro ao gerar URL do email: {str(e)}")
            return None
    
    def deletar_email(self, caminho: str) -> bool:
        """
        Deleta arquivo de email
        
        Args:
            caminho: Caminho do arquivo
            
        Returns:
            True se sucesso, False se erro
        """
        try:
            return self.storage.delete_file(caminho)
        except Exception as e:
            current_app.logger.error(f"❌ Erro ao deletar email: {str(e)}")
            return False