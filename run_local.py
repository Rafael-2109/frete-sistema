import os
import sys

# Configuração SEGURA para desenvolvimento local apenas
# NÃO afeta o ambiente Render em produção
if not os.environ.get('RENDER'):  # Só roda se NÃO for Render
    os.environ['ENVIRONMENT'] = 'development'
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['FLASK_DEBUG'] = '1'
    os.environ['SECRET_KEY'] = 'dev_key_local_apenas'
    # Force SQLite local (comentar DATABASE_URL)
    if 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']
    print("🔧 Modo desenvolvimento local ativado - SQLite")
    print("🔧 UTF-8 configurado")

from run import app

if __name__ == '__main__':
    app.run(debug=True, port=5000)
