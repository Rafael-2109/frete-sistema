# No routes.py
import os
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
        # 🌐 Salvar no S3 para armazenamento permanente
        storage = get_file_storage()
        file_path = storage.save_file(
            file=arquivo,
            folder='temp_imports',
            allowed_extensions=['xlsx', 'xls', 'csv', 'txt', 'pdf']
        )
        
        # 📁 Criar arquivo temporário local para processamento
        arquivo.seek(0)  # Reset pointer
        nome_seguro = secure_filename(arquivo.filename)
        
        with tempfile.NamedTemporaryFile(
            suffix=f"_{nome_seguro}", 
            delete=False
        ) as temp_file:
            temp_file.write(arquivo.read())
            temp_path = temp_file.name
        
        return temp_path
        
    except Exception as e:
        # 🚨 Fallback para método antigo se S3 falhar
        print(f"⚠️ Erro no S3, usando método local: {e}")
        nome_seguro = secure_filename(arquivo.filename)
        caminho_pasta = os.path.join('app', 'uploads')
        os.makedirs(caminho_pasta, exist_ok=True)
        caminho_completo = os.path.join(caminho_pasta, nome_seguro)
        arquivo.seek(0)  # Reset pointer
        arquivo.save(caminho_completo)
        return caminho_completo

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
