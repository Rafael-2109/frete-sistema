from flask import current_app
from app.utils.file_storage import get_file_storage

def file_url(file_path):
    """
    Filtro Jinja2 para gerar URL de arquivo
    Compatível com sistema local e S3
    """
    if not file_path:
        return None
    
    try:
        storage = get_file_storage()
        return storage.get_file_url(file_path)
    except Exception:
        # Fallback para sistema antigo
        if file_path.startswith('uploads/'):
            from flask import url_for
            return url_for('static', filename=file_path)
        return None

def register_template_filters(app):
    """Registra filtros customizados no Flask"""
    app.jinja_env.filters['file_url'] = file_url 