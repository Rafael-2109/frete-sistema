import os
import sys

# 🔥 PRIMEIRA COISA: REGISTRAR TIPOS POSTGRESQL
try:
    import register_pg_types
    print("✅ run.py: Tipos PostgreSQL registrados ANTES de importar app")
except Exception as e:
    print(f"⚠️ run.py: Erro ao registrar tipos PostgreSQL: {e}")

# Configurar encoding UTF-8 para Windows
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from app import create_app

app = create_app()

if __name__ == '__main__':
    # Instalar modelos NLP na primeira execução
    import os
    nlp_marker = '.nlp_models_installed'
    
    if not os.path.exists(nlp_marker):
        print("🧠 Primeira execução detectada - instalando modelos NLP...")
        try:
            from install_nlp_models import instalar_modelos_nlp
            instalar_modelos_nlp()
            # Criar marcador para não instalar novamente
            with open(nlp_marker, 'w') as f:
                f.write('NLP models installed')
        except Exception as e:
            print(f"⚠️ Erro ao instalar modelos NLP: {e}")
            print("Continuando sem modelos avançados...")
    
    app.run(debug=True)
