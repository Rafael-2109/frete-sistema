import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app, url_for
import mimetypes
from app.utils.timezone import agora_utc_naive

try:
    import boto3
    from botocore.exceptions import ClientError
    from botocore.config import Config
    from boto3.s3.transfer import TransferConfig
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False

class FileStorage:
    """
    Sistema centralizado de armazenamento de arquivos
    Suporta armazenamento local (desenvolvimento) e AWS S3 (produção)
    """
    
    def __init__(self):
        self.use_s3 = current_app.config.get('USE_S3', False) and S3_AVAILABLE

        if self.use_s3:
            # ✅ OTIMIZAÇÃO: Configurar timeouts e retries
            config = Config(
                connect_timeout=10,  # Timeout de conexão: 10 segundos
                read_timeout=30,     # Timeout de leitura: 30 segundos
                retries={'max_attempts': 2}  # Máximo 2 tentativas
            )

            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=current_app.config.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=current_app.config.get('AWS_SECRET_ACCESS_KEY'),
                region_name=current_app.config.get('AWS_REGION', 'us-east-1'),
                config=config  # ✅ Aplicar configuração
            )
            self.bucket_name = current_app.config.get('S3_BUCKET_NAME')

            # ✅ OTIMIZAÇÃO: Configurar TransferConfig para uploads mais rápidos
            self.transfer_config = TransferConfig(
                multipart_threshold=8 * 1024 * 1024,  # 8MB - arquivos maiores usam multipart
                max_concurrency=10,  # Até 10 threads para upload paralelo
                multipart_chunksize=8 * 1024 * 1024,  # 8MB por chunk
                use_threads=True
            )
    
    def save_file(self, file, folder, filename=None, allowed_extensions=None):
        """
        Salva arquivo no storage configurado
        
        Args:
            file: Arquivo do formulário (FileStorage) ou BytesIO
            folder: Pasta de destino (ex: 'motoristas', 'faturas')
            filename: Nome personalizado (opcional)
            allowed_extensions: Lista de extensões permitidas (opcional)
        
        Returns:
            str: URL/caminho do arquivo salvo ou None se erro
        """
        # 🛠️ CORREÇÃO: Suporte a BytesIO e FileStorage
        file_name = getattr(file, 'filename', None) or getattr(file, 'name', None)
        
        if not file or not file_name:
            return None
        
        # Verifica extensão se especificada
        if allowed_extensions:
            file_ext = file_name.rsplit('.', 1)[1].lower() if '.' in file_name else ''
            if file_ext not in allowed_extensions:
                raise ValueError(f"Extensão '{file_ext}' não permitida. Permitidas: {allowed_extensions}")
        
        # Gera nome seguro
        if not filename:
            timestamp = agora_utc_naive().strftime('%Y%m%d_%H%M%S_')
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{timestamp}{unique_id}_{secure_filename(file_name)}"
        else:
            filename = secure_filename(filename)
        
        # Caminho completo
        file_path = f"{folder}/{filename}"
        
        try:
            if self.use_s3:
                return self._save_to_s3(file, file_path)
            else:
                return self._save_locally(file, file_path)
        except Exception as e:
            current_app.logger.error(f"Erro ao salvar arquivo {file_path}: {str(e)}")
            return None
    
    def _save_to_s3(self, file, file_path):
        """Salva arquivo no S3 com otimizações de performance"""
        try:
            # 🛠️ CORREÇÃO: Suporte a BytesIO e FileStorage
            file_name = getattr(file, 'filename', None) or getattr(file, 'name', None)

            # Determina content type
            content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream' if file_name else 'application/octet-stream'

            # ✅ OTIMIZAÇÃO: Upload para S3 com TransferConfig
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                file_path,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'private'  # Arquivos privados por padrão
                },
                Config=self.transfer_config  # ✅ Usar configuração otimizada
            )

            # 🆕 CORRIGIDO: Retorna apenas o caminho, sem prefixo
            # Isso mantém consistência com o banco de dados
            return file_path

        except ClientError as e:
            current_app.logger.error(f"Erro S3: {str(e)}")
            raise
    
    def _save_locally(self, file, file_path):
        """Salva arquivo localmente"""
        # 🔴 CORRIGIDO: Criar TODA a estrutura de pastas, não só a primeira
        full_path = os.path.join(current_app.root_path, 'static', 'uploads', file_path)

        # Criar diretórios intermediários se não existirem
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Salvar arquivo no caminho completo (suporta Werkzeug FileStorage e BytesIO)
        if hasattr(file, 'save'):
            file.save(full_path)
        else:
            # BytesIO ou similar — escrita manual
            with open(full_path, 'wb') as f:
                file.seek(0)
                f.write(file.read())

        # Retorna caminho relativo para templates
        return f"uploads/{file_path}"
    
    def get_file_url(self, file_path):
        """
        Gera URL para acessar arquivo

        Args:
            file_path: Caminho do arquivo retornado por save_file()

        Returns:
            str: URL para acesso ao arquivo
        """
        if not file_path:
            return None

        # 🆕 CORRIGIDO: Detecta automaticamente se é S3 ou local
        if self.use_s3 and not file_path.startswith('uploads/'):
            # Sistema S3 ativo e não é arquivo local antigo
            try:
                # Remove prefixo s3:// se existir
                if file_path.startswith('s3://'):
                    bucket_name = file_path.split('/')[2]
                    object_key = '/'.join(file_path.split('/')[3:])
                else:
                    # Arquivo S3 sem prefixo
                    bucket_name = self.bucket_name
                    object_key = file_path

                # Gera URL assinada (válida por 1 hora)
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket_name, 'Key': object_key},
                    ExpiresIn=3600  # 1 hora
                )
                return url
            except ClientError as e:
                current_app.logger.error(f"Erro ao gerar URL S3 para {file_path}: {str(e)}")
                return None
        else:
            # Para arquivos locais ou sistema S3 desativado
            try:
                # 🔴 CORRIGIDO: Arquivo local já vem com "uploads/" do save_file()
                # Então basta passar direto para url_for sem duplicar
                if file_path.startswith('s3://'):
                    # Fallback: Converte S3 para caminho local
                    local_path = '/'.join(file_path.split('/')[3:])
                    return url_for('static', filename=f'uploads/{local_path}')
                else:
                    # Arquivo local: já vem no formato "uploads/pasta/arquivo.ext"
                    return url_for('static', filename=file_path)
            except Exception as e:
                current_app.logger.error(f"Erro ao gerar URL local para {file_path}: {str(e)}")
                return None
    
    def file_exists(self, file_path):
        """
        Verifica existencia do arquivo no storage (S3 head_object ou local).

        Necessario antes de gerar presigned URL — a URL e valida mesmo
        quando o objeto nao existe, e o 404 so apareceria ao usuario no
        navegador. Usar este metodo para decidir se re-enfileira o job
        SSW (ex: DACTE sumiu do bucket).

        Returns:
            bool: True se existe e acessivel.
        """
        if not file_path:
            return False

        if self.use_s3 and not file_path.startswith('uploads/'):
            try:
                if file_path.startswith('s3://'):
                    bucket_name = file_path.split('/')[2]
                    object_key = '/'.join(file_path.split('/')[3:])
                else:
                    bucket_name = self.bucket_name
                    object_key = file_path
                self.s3_client.head_object(Bucket=bucket_name, Key=object_key)
                return True
            except ClientError as e:
                code = e.response.get('Error', {}).get('Code', '')
                if code in ('404', 'NoSuchKey', 'NotFound'):
                    return False
                current_app.logger.warning(
                    f"head_object erro inesperado para {file_path}: {str(e)}"
                )
                return False

        full_path = os.path.join(current_app.root_path, 'static', file_path)
        return os.path.exists(full_path)

    def get_presigned_url(self, file_path, expires_in=3600):
        """
        Gera presigned URL para VISUALIZACAO inline (sem Content-Disposition).

        Usado por rotas de download de PDF/XML originais quando o arquivo
        esta no S3 (fallback apos tentativa local). Diferente de
        `get_file_url` porque aceita TTL customizado e e seguro chamar
        em fluxos com URL de curta duracao (ex: 300s).

        Args:
            file_path: Caminho do arquivo (bucket_key ou 's3://bucket/key')
            expires_in: TTL em segundos (default 3600 = 1h)

        Returns:
            str: Presigned URL, ou None se local/erro.
        """
        if not file_path:
            return None

        if not (self.use_s3 and not file_path.startswith('uploads/')):
            return None

        try:
            if file_path.startswith('s3://'):
                bucket_name = file_path.split('/')[2]
                object_key = '/'.join(file_path.split('/')[3:])
            else:
                bucket_name = self.bucket_name
                object_key = file_path

            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': object_key},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            current_app.logger.error(
                f"Erro ao gerar presigned URL para {file_path}: {str(e)}"
            )
            return None

    def get_download_url(self, file_path, filename=None):
        """
        Gera URL para DOWNLOAD forçado de arquivo (Content-Disposition: attachment)

        Args:
            file_path: Caminho do arquivo retornado por save_file()
            filename: Nome do arquivo para download (opcional)

        Returns:
            str: URL para download do arquivo
        """
        if not file_path:
            return None

        if self.use_s3 and not file_path.startswith('uploads/'):
            try:
                if file_path.startswith('s3://'):
                    bucket_name = file_path.split('/')[2]
                    object_key = '/'.join(file_path.split('/')[3:])
                else:
                    bucket_name = self.bucket_name
                    object_key = file_path

                # Nome do arquivo para download
                if not filename:
                    filename = object_key.split('/')[-1]

                # Gera URL assinada COM Content-Disposition para forçar download
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': bucket_name,
                        'Key': object_key,
                        'ResponseContentDisposition': f'attachment; filename="{filename}"'
                    },
                    ExpiresIn=3600
                )
                return url
            except ClientError as e:
                current_app.logger.error(f"Erro ao gerar URL download S3 para {file_path}: {str(e)}")
                return None
        else:
            # Para arquivos locais, retorna None (deve usar send_file)
            return None

    def download_file(self, file_path):
        """
        Baixa arquivo do storage e retorna os bytes.

        Args:
            file_path: Caminho do arquivo (retornado por save_file())

        Returns:
            bytes: Conteúdo do arquivo ou None se erro
        """
        if not file_path:
            return None

        try:
            if self.use_s3 and not file_path.startswith('uploads/'):
                return self._download_from_s3(file_path)
            else:
                return self._download_locally(file_path)
        except Exception as e:
            current_app.logger.error(f"Erro ao baixar arquivo {file_path}: {str(e)}")
            return None

    def _download_from_s3(self, file_path):
        """Baixa arquivo do S3 e retorna bytes."""
        from io import BytesIO

        try:
            if file_path.startswith('s3://'):
                bucket_name = file_path.split('/')[2]
                object_key = '/'.join(file_path.split('/')[3:])
            else:
                bucket_name = self.bucket_name
                object_key = file_path

            buffer = BytesIO()
            self.s3_client.download_fileobj(bucket_name, object_key, buffer)
            buffer.seek(0)
            return buffer.read()

        except ClientError as e:
            current_app.logger.error(f"Erro S3 download: {str(e)}")
            raise

    def _download_locally(self, file_path):
        """Baixa arquivo local e retorna bytes."""
        if file_path.startswith('s3://'):
            local_path = '/'.join(file_path.split('/')[3:])
            full_path = os.path.join(current_app.root_path, 'static', 'uploads', local_path)
        else:
            full_path = os.path.join(current_app.root_path, 'static', file_path)

        if not os.path.exists(full_path):
            current_app.logger.error(f"Arquivo local não encontrado: {full_path}")
            return None

        with open(full_path, 'rb') as f:
            return f.read()

    def delete_file(self, file_path):
        """
        Remove arquivo do storage

        Args:
            file_path: Caminho do arquivo retornado por save_file()

        Returns:
            bool: True se removido com sucesso
        """
        if not file_path:
            return False

        try:
            if file_path.startswith('s3://'):
                # Path com prefixo S3 explícito
                bucket_name = file_path.split('/')[2]
                object_key = '/'.join(file_path.split('/')[3:])
                self.s3_client.delete_object(
                    Bucket=bucket_name,
                    Key=object_key
                )
            elif self.use_s3 and not file_path.startswith('uploads/'):
                # Path S3 sem prefixo (retornado por save_file com S3 ativo)
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=file_path
                )
            else:
                # Remove arquivo local
                full_path = os.path.join(current_app.root_path, 'static', file_path)
                if os.path.exists(full_path):
                    os.remove(full_path)

            return True
        except Exception as e:
            current_app.logger.error(f"Erro ao deletar arquivo {file_path}: {str(e)}")
            return False

# Função helper para facilitar uso
def get_file_storage():
    """Retorna instância do FileStorage"""
    return FileStorage() 