#!/usr/bin/env python3
"""
DevCommands - Comandos especializados para desenvolvimento
Versão otimizada integrada com BaseCommand
"""

from app.claude_ai_novo.commands.base_command import (
    BaseCommand, format_response_advanced, create_excel_summary,
    logging, datetime, db, current_user, ClaudeAIConfig, AdvancedConfig
)
import anthropic

logger = logging.getLogger(__name__)

class DevCommands(BaseCommand):
    """Classe para comandos especializados de desenvolvimento"""
    
    def __init__(self, claude_client=None):
        super().__init__(claude_client)
        self.system_prompt = """Você é um assistente especializado em desenvolvimento Flask, Python, SQLAlchemy, WTForms, Jinja2, Bootstrap, HTML, CSS, JavaScript, React, Node.js, Express, MongoDB, PostgreSQL, MySQL, SQLite, Oracle, SQL Server, MariaDB, etc.

ESTRUTURA DO PROJETO:
```
app/
├── [módulo]/
│   ├── __init__.py      # Blueprint e inicialização
│   ├── models.py        # Modelos SQLAlchemy
│   ├── routes.py        # Rotas Flask
│   ├── forms.py         # Formulários WTForms
├── templates/           # Templates HTML
├── utils/               # Utilitários compartilhados
├── static/              # CSS, JS, imagens
```

PADRÕES DO SISTEMA:
- Modelos: SQLAlchemy com db.Model
- Formulários: WTForms com FlaskForm
- Templates: Jinja2 com herança de base.html
- Autenticação: @login_required
- Permissões: @require_financeiro(), @require_admin()
- Logs: logger.info(), logger.error()"""
        
    def is_dev_command(self, consulta: str) -> bool:
        """Detecta comandos de desenvolvimento/criação de código"""
        if not self._validate_input(consulta):
            return False
        
        comandos_dev = [
            # Comandos diretos
            'criar módulo', 'crie módulo', 'criar modulo', 'crie modulo',
            'criar funcionalidade', 'criar função', 'criar rota',
            'criar modelo', 'criar model', 'criar tabela',
            'criar template', 'criar formulário', 'criar form',
            'desenvolver', 'programar', 'codificar', 'implementar',
            
            # Solicitações de código
            'código para', 'codigo para', 'script para',
            'função que', 'funcao que', 'método para',
            'classe para', 'api para', 'endpoint para',
            
            # Melhorias e otimizações
            'melhorar código', 'otimizar função', 'refatorar',
            'corrigir bug', 'resolver erro', 'debug',
            
            # Arquitetura
            'estrutura para', 'arquitetura de', 'design pattern',
            'organizar módulo', 'reestruturar'
        ]
        
        consulta_lower = consulta.lower()
        return any(comando in consulta_lower for comando in comandos_dev)
    
    def processar_comando_desenvolvimento(self, consulta: str, user_context=None) -> str:
        """Processa comandos de desenvolvimento com contexto do projeto"""
        
        if not self._validate_input(consulta):
            return self._handle_error(ValueError("Consulta inválida"), "desenvolvimento", "Entrada vazia ou inválida")
        
        # Sanitizar entrada
        consulta = self._sanitize_input(consulta)
        
        # Extrair filtros avançados
        filtros = self._extract_filters_advanced(consulta)
        
        # Log avançado
        self._log_command(consulta, "desenvolvimento", filtros)
        
        try:
            # Verificar cache primeiro (desenvolvimento tem cache menor)
            cache_key = self._generate_cache_key("dev", consulta, filtros)
            cached_result = self._get_cached_result(cache_key, 300)  # 5 min cache
            
            if cached_result:
                logger.info("✅ Resultado de desenvolvimento encontrado em cache")
                return cached_result
            
            # Processar comando
            resultado = self._processar_desenvolvimento_interno(consulta, filtros, user_context)
            
            # Armazenar em cache
            self._set_cached_result(cache_key, resultado, 300)
            
            return resultado
            
        except Exception as e:
            return self._handle_error(e, "desenvolvimento", f"Consulta: {consulta[:100]}")
    
    def _processar_desenvolvimento_interno(self, consulta: str, filtros: dict, user_context) -> str:
        """Processamento interno de desenvolvimento"""
        
        # Detectar tipo específico de desenvolvimento
        tipo_dev = self._detectar_tipo_desenvolvimento(consulta)
        
        # Adicionar contexto específico do projeto
        contexto_completo = self._construir_contexto_projeto(consulta, filtros, tipo_dev)
        
        # Processar com Claude incluindo contexto
        if self.client:
            return self._processar_com_claude(consulta, contexto_completo, tipo_dev)
        else:
            return self._fallback_sem_claude(consulta, tipo_dev, filtros)
    
    def _detectar_tipo_desenvolvimento(self, consulta: str) -> str:
        """Detecta tipo específico de desenvolvimento"""
        consulta_lower = consulta.lower()
        
        if any(palavra in consulta_lower for palavra in ['módulo', 'modulo']):
            return 'modulo'
        elif any(palavra in consulta_lower for palavra in ['modelo', 'model', 'tabela']):
            return 'modelo'
        elif any(palavra in consulta_lower for palavra in ['rota', 'route', 'endpoint']):
            return 'rota'
        elif any(palavra in consulta_lower for palavra in ['template', 'html', 'jinja','tela']):
            return 'template'
        elif any(palavra in consulta_lower for palavra in ['formulário', 'form', 'wtforms']):
            return 'formulario'
        elif any(palavra in consulta_lower for palavra in ['api', 'rest', 'json']):
            return 'api'
        elif any(palavra in consulta_lower for palavra in ['otimizar', 'refatorar', 'melhorar']):
            return 'otimizacao'
        elif any(palavra in consulta_lower for palavra in ['bug', 'erro', 'debug']):
            return 'debug'
        else:
            return 'geral'
    
    def _construir_contexto_projeto(self, consulta: str, filtros: dict, tipo_dev: str) -> str:
        """Constrói contexto específico baseado no tipo de desenvolvimento"""
        
        base_context = f"""
SOLICITAÇÃO: {consulta}

TIPO DE DESENVOLVIMENTO: {tipo_dev}
"""
        
        if filtros.get('cliente'):
            base_context += f"\nCLIENTE RELACIONADO: {filtros['cliente']}"
        
        # Contexto específico por tipo
        contextos_especificos = {
            'modulo': """
PADRÃO PARA MÓDULOS:
```python
# __init__.py
from flask import Blueprint
bp = Blueprint('modulo', __name__)
from app.modulo import routes

# models.py
from app import db
class Model(db.Model):
    __tablename__ = 'tabela'
    id = db.Column(db.Integer, primary_key=True)
    
# routes.py
from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required
from app.modulo import bp

@bp.route('/')
@login_required
def index():
    return render_template('modulo/index.html')

# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class Form(FlaskForm):
    campo = StringField('Campo', validators=[DataRequired()])
    submit = SubmitField('Enviar')
```""",
            
            'modelo': """
PADRÃO PARA MODELOS:
```python
from app import db
from datetime import datetime

class NovoModelo(db.Model):
    __tablename__ = 'nova_tabela'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<NovoModelo {self.nome}>'
```""",
            
            'rota': """
PADRÃO PARA ROTAS:
```python
@bp.route('/nova-rota')
@login_required
def nova_rota():
    try:
        # Lógica da rota
        return render_template('template.html')
    except Exception as e:
        logger.error(f"Erro na rota: {e}")
        flash('Erro interno', 'error')
        return redirect(url_for('main.index'))
```""",
            
            'template': """
PADRÃO PARA TEMPLATES:
```html
{% extends "base.html" %}

{% block title %}Título{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-md-12">
            <h1>Conteúdo</h1>
        </div>
    </div>
</div>
{% endblock %}
```""",
            
            'formulario': """
PADRÃO PARA FORMULÁRIOS:
```python
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Email

class NovoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Salvar')
```""",
            
            'api': """
PADRÃO PARA APIS:
```python
@bp.route('/api/data', methods=['GET'])
@login_required
def api_data():
    try:
        data = {'status': 'success', 'data': []}
        return jsonify(data)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
```"""
        }
        
        if tipo_dev in contextos_especificos:
            base_context += contextos_especificos[tipo_dev]
        
        return base_context
    
    def _processar_com_claude(self, consulta: str, contexto: str, tipo_dev: str) -> str:
        """Processa com Claude usando context avançado"""
        
        messages = [
            {
                "role": "user",
                "content": contexto
            }
        ]
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                temperature=0.5,  # Equilibrio entre determinismo e criatividade
                timeout=120.0,
                system=self.system_prompt,
                messages=messages
            )
            
            resultado = response.content[0].text
            
            # Criar estatísticas
            stats = {
                'total': 1,
                'tipo': tipo_dev,
                'linhas_codigo': len(resultado.split('\n'))
            }
            
            return format_response_advanced(resultado, "DevCommands", stats)
            
        except Exception as e:
            return self._handle_error(e, "desenvolvimento", f"Processamento Claude: {tipo_dev}")
    
    def _fallback_sem_claude(self, consulta: str, tipo_dev: str, filtros: dict) -> str:
        """Fallback quando Claude não disponível"""
        
        templates_fallback = {
            'modulo': self._template_modulo_fallback,
            'modelo': self._template_modelo_fallback,
            'rota': self._template_rota_fallback,
            'template': self._template_html_fallback,
            'formulario': self._template_form_fallback,
            'api': self._template_api_fallback
        }
        
        if tipo_dev in templates_fallback:
            content = templates_fallback[tipo_dev](consulta, filtros)
        else:
            content = self._template_geral_fallback(consulta, tipo_dev, filtros)
        
        stats = {'total': 1, 'tipo': tipo_dev, 'modo': 'fallback'}
        return format_response_advanced(content, "DevCommands", stats)
    
    def _template_modulo_fallback(self, consulta: str, filtros: dict) -> str:
        """Template fallback para módulos"""
        nome_modulo = filtros.get('cliente', 'novo_modulo').lower().replace(' ', '_')
        
        return f"""💻 **ESTRUTURA DE MÓDULO GERADA**

📁 **Módulo:** {nome_modulo}

```python
# app/{nome_modulo}/__init__.py
from flask import Blueprint

bp = Blueprint('{nome_modulo}', __name__)

from app.{nome_modulo} import routes

# app/{nome_modulo}/models.py
from app import db
from datetime import datetime

class {nome_modulo.title()}(db.Model):
    __tablename__ = '{nome_modulo}'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<{nome_modulo.title()} {{self.nome}}>'

# app/{nome_modulo}/routes.py
from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required
from app.{nome_modulo} import bp

@bp.route('/')
@login_required
def index():
    return render_template('{nome_modulo}/index.html')

# app/{nome_modulo}/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class {nome_modulo.title()}Form(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    submit = SubmitField('Salvar')
```

🎯 **Próximos passos:**
1. Registrar blueprint no app/__init__.py
2. Criar migration: `flask db migrate -m "Add {nome_modulo}"`
3. Aplicar: `flask db upgrade`
4. Criar template em templates/{nome_modulo}/"""
    
    def _template_modelo_fallback(self, consulta: str, filtros: dict) -> str:
        """Template fallback para modelos"""
        return """💻 **MODELO SQLAlchemy GERADO**

```python
from app import db
from datetime import datetime

class NovoModelo(db.Model):
    __tablename__ = 'nova_tabela'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<NovoModelo {self.nome}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'ativo': self.ativo,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
```

🎯 **Para usar:**
1. `flask db migrate -m "Add nova_tabela"`
2. `flask db upgrade`"""
    
    def _template_rota_fallback(self, consulta: str, filtros: dict) -> str:
        """Template fallback para rotas"""
        return """💻 **ROTA FLASK GERADA**

```python
@bp.route('/nova-rota')
@login_required
def nova_rota():
    try:
        # Sua lógica aqui
        dados = {'status': 'success'}
        
        return render_template('template.html', dados=dados)
        
    except Exception as e:
        logger.error(f"Erro na nova_rota: {e}")
        flash('Erro interno', 'error')
        return redirect(url_for('main.index'))

@bp.route('/nova-rota', methods=['POST'])
@login_required
def nova_rota_post():
    form = NovoForm()
    
    if form.validate_on_submit():
        # Processar dados do formulário
        flash('Dados salvos com sucesso!', 'success')
        return redirect(url_for('modulo.nova_rota'))
    
    return render_template('form.html', form=form)
```"""
    
    def _template_html_fallback(self, consulta: str, filtros: dict) -> str:
        """Template fallback para HTML"""
        return """💻 **TEMPLATE HTML GERADO**

```html
{% extends "base.html" %}

{% block title %}Novo Template{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-md-12">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Novo Template</h3>
                </div>
                <div class="card-body">
                    <!-- Seu conteúdo aqui -->
                    <p>Template gerado automaticamente</p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
$(document).ready(function() {
    // Seu JavaScript aqui
});
</script>
{% endblock %}
```"""
    
    def _template_form_fallback(self, consulta: str, filtros: dict) -> str:
        """Template fallback para formulários"""
        return """💻 **FORMULÁRIO WTForms GERADO**

```python
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Optional

class NovoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    descricao = TextAreaField('Descrição', validators=[Optional(), Length(max=500)])
    ativo = BooleanField('Ativo', default=True)
    categoria = SelectField('Categoria', choices=[('', 'Selecione...'), ('op1', 'Opção 1')])
    submit = SubmitField('Salvar')
    
    def validate_nome(self, nome):
        # Validação customizada
        if len(nome.data) < 3:
            raise ValidationError('Nome deve ter pelo menos 3 caracteres')
```

```html
<!-- Template do formulário -->
{% extends "base.html" %}

{% block content %}
<form method="POST">
    {{ form.hidden_tag() }}
    
    <div class="form-group">
        {{ form.nome.label(class="form-label") }}
        {{ form.nome(class="form-control") }}
        {% if form.nome.errors %}
            <div class="text-danger">{{ form.nome.errors[0] }}</div>
        {% endif %}
    </div>
    
    {{ form.submit(class="btn btn-primary") }}
</form>
{% endblock %}
```"""
    
    def _template_api_fallback(self, consulta: str, filtros: dict) -> str:
        """Template fallback para APIs"""
        return """💻 **API REST GERADA**

```python
from flask import jsonify, request
from flask_login import login_required, current_user

@bp.route('/api/dados', methods=['GET'])
@login_required
def api_listar_dados():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        dados = Modelo.query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': [item.to_dict() for item in dados.items],
            'pagination': {
                'page': page,
                'pages': dados.pages,
                'total': dados.total
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/dados', methods=['POST'])
@login_required
def api_criar_dado():
    try:
        data = request.get_json()
        
        novo_item = Modelo(
            nome=data['nome'],
            user_id=current_user.id
        )
        
        db.session.add(novo_item)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'data': novo_item.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
```"""
    
    def _template_geral_fallback(self, consulta: str, tipo_dev: str, filtros: dict) -> str:
        """Template fallback geral"""
        return f"""💻 **CÓDIGO DE DESENVOLVIMENTO GERADO**

🎯 **Tipo:** {tipo_dev}
📝 **Solicitação:** {consulta}

⚠️ **Claude não disponível - Modo Fallback**

💡 **Sugestões para {tipo_dev}:**
• Siga os padrões Flask estabelecidos
• Use SQLAlchemy para modelos
• Implemente validação adequada
• Adicione logs para debug
• Teste a funcionalidade

🔧 **Estrutura recomendada:**
1. Defina os requisitos claramente
2. Crie os modelos necessários
3. Implemente as rotas
4. Adicione validação
5. Teste a funcionalidade

📚 **Documentação útil:**
• Flask: https://flask.palletsprojects.com/
• SQLAlchemy: https://docs.sqlalchemy.org/
• WTForms: https://wtforms.readthedocs.io/"""

# Instância global
_dev_commands = None

def get_dev_commands():
    """Retorna instância de DevCommands"""
    global _dev_commands
    if _dev_commands is None:
        _dev_commands = DevCommands()
    return _dev_commands
