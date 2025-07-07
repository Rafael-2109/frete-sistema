"""
🚀 CLAUDE CODE GENERATOR - Autonomia Total para Geração de Código
Permite ao Claude AI criar, modificar e gerenciar arquivos do projeto
"""

import os
import ast
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ClaudeCodeGenerator:
    """Gerador de código com autonomia total para Claude AI"""
    
    def __init__(self, app_path: Optional[str] = None):
        """Inicializa gerador de código"""
        self.app_path = Path(app_path) if app_path else Path(__file__).parent.parent
        self.backup_dir = self.app_path / 'claude_ai' / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"🚀 Claude Code Generator inicializado: {self.app_path}")
    
    def create_backup(self, file_path: str) -> str:
        """Cria backup de arquivo antes de modificar"""
        try:
            source_file = Path(file_path)
            if source_file.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"{source_file.name}.backup_{timestamp}"
                backup_path = self.backup_dir / backup_name
                
                shutil.copy2(source_file, backup_path)
                logger.info(f"💾 Backup criado: {backup_name}")
                return str(backup_path)
            
            return ""
        except Exception as e:
            logger.error(f"❌ Erro ao criar backup: {e}")
            return ""
    
    def write_file(self, file_path: str, content: str, create_backup: bool = True) -> bool:
        """Escreve arquivo com backup automático"""
        try:
            full_path = self.app_path / file_path if not os.path.isabs(file_path) else Path(file_path)
            
            # Criar backup se arquivo existe
            if create_backup and full_path.exists():
                self.create_backup(str(full_path))
            
            # Criar diretórios se necessário
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Escrever arquivo
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✅ Arquivo salvo: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao escrever arquivo {file_path}: {e}")
            return False
    
    def read_file(self, file_path: str) -> str:
        """Lê arquivo do projeto"""
        try:
            full_path = self.app_path / file_path if not os.path.isabs(file_path) else Path(file_path)
            
            if not full_path.exists():
                return f"❌ Arquivo não encontrado: {file_path}"
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"📖 Arquivo lido: {file_path}")
            return content
            
        except Exception as e:
            logger.error(f"❌ Erro ao ler arquivo {file_path}: {e}")
            return f"❌ Erro: {e}"
    
    def generate_flask_module(self, module_name: str, fields: List[Dict], 
                            templates: Optional[List[str]] = None) -> Dict[str, str]:
        """Gera módulo Flask completo"""
        
        templates = templates or ['form.html', 'list.html']
        
        files = {}
        
        # 1. MODELS.PY
        files[f"app/{module_name}/models.py"] = self._generate_model_file(module_name, fields)
        
        # 2. FORMS.PY  
        files[f"app/{module_name}/forms.py"] = self._generate_form_file(module_name, fields)
        
        # 3. ROUTES.PY
        files[f"app/{module_name}/routes.py"] = self._generate_routes_file(module_name, fields)
        
        # 4. __INIT__.PY
        files[f"app/{module_name}/__init__.py"] = self._generate_init_file(module_name)
        
        # 5. TEMPLATES
        for template in templates:
            files[f"app/templates/{module_name}/{template}"] = self._generate_template_file(module_name, template, fields)
        
        return files
    
    def _generate_model_file(self, module_name: str, fields: List[Dict]) -> str:
        """Gera arquivo models.py"""
        
        model_class = f"{module_name.title().replace('_', '')}"
        
        content = f'''from app import db
from datetime import datetime

class {model_class}(db.Model):
    """Modelo para {module_name}"""
    
    __tablename__ = '{module_name}'
    
    id = db.Column(db.Integer, primary_key=True)
'''
        
        # Adicionar campos
        for field in fields:
            field_name = field['name']
            field_type = field.get('type', 'String')
            nullable = field.get('nullable', True)
            
            if field_type.lower() == 'string':
                content += f"    {field_name} = db.Column(db.String(255), nullable={nullable})\n"
            elif field_type.lower() == 'integer':
                content += f"    {field_name} = db.Column(db.Integer, nullable={nullable})\n"
            elif field_type.lower() == 'float':
                content += f"    {field_name} = db.Column(db.Float, nullable={nullable})\n"
            elif field_type.lower() == 'date':
                content += f"    {field_name} = db.Column(db.Date, nullable={nullable})\n"
            elif field_type.lower() == 'datetime':
                content += f"    {field_name} = db.Column(db.DateTime, nullable={nullable})\n"
            elif field_type.lower() == 'boolean':
                content += f"    {field_name} = db.Column(db.Boolean, default=False, nullable={nullable})\n"
            else:
                content += f"    {field_name} = db.Column(db.String(255), nullable={nullable})\n"
        
        # Campos de auditoria
        content += f'''
    # Campos de auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<{model_class} {{self.id}}>'
    
    def to_dict(self):
        """Converte modelo para dicionário"""
        return {{
            'id': self.id,
'''
        
        for field in fields:
            content += f"            '{field['name']}': self.{field['name']},\n"
        
        content += '''            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }
'''
        
        return content
    
    def _generate_form_file(self, module_name: str, fields: List[Dict]) -> str:
        """Gera arquivo forms.py"""
        
        form_class = f"{module_name.title().replace('_', '')}Form"
        
        content = f'''from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, DateField, DateTimeField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Optional, Length

class {form_class}(FlaskForm):
    """Formulário para {module_name}"""
    
'''
        
        # Adicionar campos
        for field in fields:
            field_name = field['name']
            field_type = field.get('type', 'String')
            required = not field.get('nullable', True)
            
            validators = "DataRequired()" if required else "Optional()"
            
            if field_type.lower() == 'string':
                content += f"    {field_name} = StringField('{field_name.replace('_', ' ').title()}', validators=[{validators}])\n"
            elif field_type.lower() == 'integer':
                content += f"    {field_name} = IntegerField('{field_name.replace('_', ' ').title()}', validators=[{validators}])\n"
            elif field_type.lower() == 'float':
                content += f"    {field_name} = FloatField('{field_name.replace('_', ' ').title()}', validators=[{validators}])\n"
            elif field_type.lower() == 'date':
                content += f"    {field_name} = DateField('{field_name.replace('_', ' ').title()}', validators=[{validators}])\n"
            elif field_type.lower() == 'datetime':
                content += f"    {field_name} = DateTimeField('{field_name.replace('_', ' ').title()}', validators=[{validators}])\n"
            elif field_type.lower() == 'boolean':
                content += f"    {field_name} = BooleanField('{field_name.replace('_', ' ').title()}')\n"
            elif field_type.lower() == 'text':
                content += f"    {field_name} = TextAreaField('{field_name.replace('_', ' ').title()}', validators=[{validators}])\n"
            else:
                content += f"    {field_name} = StringField('{field_name.replace('_', ' ').title()}', validators=[{validators}])\n"
        
        return content
    
    def _generate_routes_file(self, module_name: str, fields: List[Dict]) -> str:
        """Gera arquivo routes.py"""
        
        model_class = f"{module_name.title().replace('_', '')}"
        form_class = f"{model_class}Form"
        
        content = f'''from flask import render_template, request, flash, redirect, url_for, jsonify, Blueprint
from flask_login import login_required, current_user
from app import db
from .models import {model_class}
from .forms import {form_class}

# Criar blueprint
{module_name}_bp = Blueprint('{module_name}', __name__, url_prefix='/{module_name}')

@{module_name}_bp.route('/')
@login_required
def index():
    """Página inicial do módulo {module_name}"""
    page = request.args.get('page', 1, type=int)
    items = {model_class}.query.paginate(
        page=page, per_page=100, error_out=False
    )
    
    return render_template('{module_name}/list.html', 
                         items=items, 
                         title='{module_name.replace("_", " ").title()}')

@{module_name}_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    """Criar novo {module_name}"""
    form = {form_class}()
    
    if form.validate_on_submit():
        try:
            item = {model_class}()
'''
        
        # Adicionar campos do formulário
        for field in fields:
            content += f"            item.{field['name']} = form.{field['name']}.data\n"
        
        content += f'''            
            db.session.add(item)
            db.session.commit()
            
            flash('{model_class} criado com sucesso!', 'success')
            return redirect(url_for('{module_name}.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar {module_name}: {{e}}', 'error')
    
    return render_template('{module_name}/form.html', 
                         form=form, 
                         title='Novo {module_name.replace("_", " ").title()}')

@{module_name}_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Editar {module_name}"""
    item = {model_class}.query.get_or_404(id)
    form = {form_class}(obj=item)
    
    if form.validate_on_submit():
        try:
'''
        
        # Adicionar campos do formulário para edição
        for field in fields:
            content += f"            item.{field['name']} = form.{field['name']}.data\n"
        
        content += f'''            
            db.session.commit()
            
            flash('{model_class} atualizado com sucesso!', 'success')
            return redirect(url_for('{module_name}.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar {module_name}: {{e}}', 'error')
    
    return render_template('{module_name}/form.html', 
                         form=form, 
                         item=item,
                         title='Editar {module_name.replace("_", " ").title()}')

@{module_name}_bp.route('/api/<int:id>')
@login_required
def api_detalhes(id):
    """API para detalhes do item"""
    item = {model_class}.query.get_or_404(id)
    return jsonify(item.to_dict())
'''
        
        return content
    
    def _generate_init_file(self, module_name: str) -> str:
        """Gera arquivo __init__.py"""
        return f'''from flask import Blueprint

{module_name}_bp = Blueprint('{module_name}', __name__)

from . import routes
'''
    
    def _generate_template_file(self, module_name: str, template_name: str, fields: List[Dict]) -> str:
        """Gera arquivo de template"""
        
        if template_name == 'form.html':
            return self._generate_form_template(module_name, fields)
        elif template_name == 'list.html':
            return self._generate_list_template(module_name, fields)
        else:
            return "<!-- Template básico -->"
    
    def _generate_form_template(self, module_name: str, fields: List[Dict]) -> str:
        """Gera template de formulário"""
        
        title = module_name.replace('_', ' ').title()
        
        content = f'''{{%% extends "base.html" %%}}
{{%% block title %%}}{title}{{%% endblock %%}}

{{%% block content %%}}
<div class="container-fluid">
    <div class="d-sm-flex align-items-center justify-content-between mb-4">
        <h1 class="h3 mb-0 text-gray-800">
            <i class="fas fa-plus text-primary"></i> {{{{ title }}}}
        </h1>
        <a href="{{{{ url_for('{module_name}.index') }}}}" class="btn btn-outline-secondary">
            <i class="fas fa-arrow-left"></i> Voltar
        </a>
    </div>

    <div class="row justify-content-center">
        <div class="col-lg-8">
            <div class="card shadow">
                <div class="card-header py-3">
                    <h6 class="m-0 font-weight-bold text-primary">Formulário</h6>
                </div>
                <div class="card-body">
                    <form method="POST">
                        {{{{ form.hidden_tag() }}}}
                        
'''
        
        # Adicionar campos do formulário
        for field in fields:
            field_name = field['name']
            field_label = field_name.replace('_', ' ').title()
            
            content += f'''                        <div class="form-group">
                            {{{{ form.{field_name}.label(class="form-label") }}}}
                            {{{{ form.{field_name}(class="form-control") }}}}
                            {{%% if form.{field_name}.errors %%}}
                                <div class="text-danger">
                                    {{%% for error in form.{field_name}.errors %%}}
                                        <small>{{{{ error }}}}</small>
                                    {{%% endfor %%}}
                                </div>
                            {{%% endif %%}}
                        </div>
                        
'''
        
        content += f'''                        <div class="form-group">
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-save"></i> Salvar
                            </button>
                            <a href="{{{{ url_for('{module_name}.index') }}}}" class="btn btn-secondary">
                                <i class="fas fa-times"></i> Cancelar
                            </a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{{%% endblock %%}}'''
        
        return content
    
    def _generate_list_template(self, module_name: str, fields: List[Dict]) -> str:
        """Gera template de listagem"""
        
        title = module_name.replace('_', ' ').title()
        
        content = f'''{{%% extends "base.html" %%}}
{{%% block title %%}}{title}{{%% endblock %%}}

{{%% block content %%}}
<div class="container-fluid">
    <div class="d-sm-flex align-items-center justify-content-between mb-4">
        <h1 class="h3 mb-0 text-gray-800">
            <i class="fas fa-list text-primary"></i> {title}
        </h1>
        <a href="{{{{ url_for('{module_name}.novo') }}}}" class="btn btn-primary">
            <i class="fas fa-plus"></i> Novo {title[:-1] if title.endswith('s') else title}
        </a>
    </div>

    <div class="card shadow mb-4">
        <div class="card-header py-3">
            <h6 class="m-0 font-weight-bold text-primary">Lista de {title}</h6>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-bordered table-hover">
                    <thead>
                        <tr>
                            <th>ID</th>
'''
        
        # Adicionar cabeçalhos das colunas
        for field in fields[:5]:  # Mostrar apenas os primeiros 5 campos
            field_label = field['name'].replace('_', ' ').title()
            content += f"                            <th>{field_label}</th>\n"
        
        content += f'''                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{%% for item in items.items %%}}
                        <tr>
                            <td>{{{{ item.id }}}}</td>
'''
        
        # Adicionar dados das colunas
        for field in fields[:5]:
            field_name = field['name']
            content += f"                            <td>{{{{ item.{field_name} or '-' }}}}</td>\n"
        
        content += f'''                            <td>
                                <a href="{{{{ url_for('{module_name}.editar', id=item.id) }}}}" class="btn btn-sm btn-primary">
                                    <i class="fas fa-edit"></i> Editar
                                </a>
                            </td>
                        </tr>
                        {{%% endfor %%}}
                    </tbody>
                </table>
            </div>
            
            <!-- Paginação -->
            {{%% if items.pages > 1 %%}}
            <nav aria-label="Navegação de página">
                <ul class="pagination justify-content-center">
                    {{%% if items.has_prev %%}}
                    <li class="page-item">
                        <a class="page-link" href="{{{{ url_for('{module_name}.index', page=items.prev_num) }}}}">Anterior</a>
                    </li>
                    {{%% endif %%}}
                    
                    {{%% for page_num in items.iter_pages() %%}}
                        {{%% if page_num %%}}
                            {{%% if page_num != items.page %%}}
                            <li class="page-item">
                                <a class="page-link" href="{{{{ url_for('{module_name}.index', page=page_num) }}}}">{{{{ page_num }}}}</a>
                            </li>
                            {{%% else %%}}
                            <li class="page-item active">
                                <span class="page-link">{{{{ page_num }}}}</span>
                            </li>
                            {{%% endif %%}}
                        {{%% endif %%}}
                    {{%% endfor %%}}
                    
                    {{%% if items.has_next %%}}
                    <li class="page-item">
                        <a class="page-link" href="{{{{ url_for('{module_name}.index', page=items.next_num) }}}}">Próximo</a>
                    </li>
                    {{%% endif %%}}
                </ul>
            </nav>
            {{%% endif %%}}
        </div>
    </div>
</div>
{{%% endblock %%}}'''
        
        return content

# Instância global
code_generator = None

def init_code_generator(app_path: Optional[str] = None) -> ClaudeCodeGenerator:
    """Inicializa o gerador de código"""
    global code_generator
    code_generator = ClaudeCodeGenerator(app_path)
    return code_generator

def get_code_generator() -> Optional[ClaudeCodeGenerator]:
    """Retorna instância do gerador de código"""
    return code_generator 