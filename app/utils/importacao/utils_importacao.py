# No routes.py
import os
import io
import tempfile
from werkzeug.utils import secure_filename
from app.utils.file_storage import get_file_storage

def salvar_temp(arquivo):
    """
    🆕 Salva arquivo temporariamente usando sistema S3 + arquivo local para processamento
    
    Args:
        arquivo: Arquivo do Flask (request.files)
    
    Returns:
        str: Caminho do arquivo temporário local para processamento
    """
    try:
        # 📖 Ler o arquivo UMA vez no início para evitar problemas de arquivo fechado
        file_content = arquivo.read()
        nome_seguro = secure_filename(arquivo.filename)
        
        # 🌐 Salvar no S3 para armazenamento permanente usando BytesIO
        storage = get_file_storage()
        file_like = io.BytesIO(file_content)
        file_like.filename = arquivo.filename  # Preservar nome original
        
        file_path = storage.save_file(
            file=file_like,
            folder='temp_imports',
            allowed_extensions=['xlsx', 'xls', 'csv', 'txt', 'pdf']
        )
        
        # 📁 Criar arquivo temporário local para processamento usando os mesmos bytes
        with tempfile.NamedTemporaryFile(
            suffix=f"_{nome_seguro}", 
            delete=False
        ) as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        
        return temp_path
        
    except Exception as e:
        # 🚨 Fallback para método antigo se S3 falhar
        print(f"⚠️ Erro no S3, usando método local: {e}")
        try:
            # Usar file_content se já foi lido, senão ler o arquivo
            content = file_content if 'file_content' in locals() else arquivo.read()
            nome_seguro = secure_filename(arquivo.filename)
            caminho_pasta = os.path.join('app', 'uploads')
            os.makedirs(caminho_pasta, exist_ok=True)
            caminho_completo = os.path.join(caminho_pasta, nome_seguro)
            
            with open(caminho_completo, 'wb') as f:
                f.write(content)
            
            return caminho_completo
        except Exception as fallback_error:
            raise Exception(f"Erro no S3 e fallback: {e} | {fallback_error}")

def limpar_temp(caminho_arquivo):
    """
    🗑️ Remove arquivo temporário após processamento
    
    Args:
        caminho_arquivo (str): Caminho do arquivo para remover
    """
    try:
        if os.path.exists(caminho_arquivo):
            os.unlink(caminho_arquivo)
    except Exception as e:
        print(f"⚠️ Erro ao remover arquivo temporário {caminho_arquivo}: {e}")
