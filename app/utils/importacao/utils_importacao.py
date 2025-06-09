# No routes.py
import os
from werkzeug.utils import secure_filename

def salvar_temp(arquivo):
    nome_seguro = secure_filename(arquivo.filename)
    caminho_pasta = os.path.join('app', 'uploads')
    os.makedirs(caminho_pasta, exist_ok=True)
    caminho_completo = os.path.join(caminho_pasta, nome_seguro)
    arquivo.save(caminho_completo)
    return caminho_completo
