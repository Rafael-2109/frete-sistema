import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app, url_for
import mimetypes

try:
    import boto3
    from botocore.exceptions import ClientError
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
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=current_app.config.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=current_app.config.get('AWS_SECRET_ACCESS_KEY'),
                region_name=current_app.config.get('AWS_REGION', 'us-east-1')
            )
            self.bucket_name = current_app.config.get('S3_BUCKET_NAME')
    
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
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
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
        """Salva arquivo no S3"""
        try:
            # 🛠️ CORREÇÃO: Suporte a BytesIO e FileStorage
            file_name = getattr(file, 'filename', None) or getattr(file, 'name', None)
            
            # Determina content type
            content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream' if file_name else 'application/octet-stream'
            
            # Upload para S3
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                file_path,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'private'  # Arquivos privados por padrão
                }
            )
            
            # 🆕 CORRIGIDO: Retorna apenas o caminho, sem prefixo
            # Isso mantém consistência com o banco de dados
            return file_path
            
        except ClientError as e:
            current_app.logger.error(f"Erro S3: {str(e)}")
            raise
    
    def _save_locally(self, file, file_path):
        """Salva arquivo localmente"""
        # Cria diretório se não existir
        local_folder = os.path.join(current_app.root_path, 'static', 'uploads', file_path.split('/')[0])
        os.makedirs(local_folder, exist_ok=True)
        
        # Salva arquivo
        full_path = os.path.join(local_folder, os.path.basename(file_path))
        file.save(full_path)
        
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
                # Remove prefixo s3:// se existir (fallback)
                if file_path.startswith('s3://'):
                    # Converte para caminho local
                    local_path = '/'.join(file_path.split('/')[3:])
                    return url_for('static', filename=f'uploads/{local_path}')
                else:
                    return url_for('static', filename=file_path)
            except Exception:
                return None
    
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
                # Remove do S3
                bucket_name = file_path.split('/')[2]
                object_key = '/'.join(file_path.split('/')[3:])
                
                self.s3_client.delete_object(
                    Bucket=bucket_name,
                    Key=object_key
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