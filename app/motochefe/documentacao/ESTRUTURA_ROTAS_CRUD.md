# 📦 ESTRUTURA COMPLETA - ROTAS E CRUD MOTOCHEFE

Este arquivo contém TODO o código necessário para criar o sistema CRUD completo.

---

## 📁 ESTRUTURA DE PASTAS A CRIAR

```
app/motochefe/
├── routes/
│   ├── __init__.py
│   ├── cadastros.py (Equipes, Vendedores, Transportadoras, Clientes)
│   ├── produtos.py (ModeloMoto)
│   └── operacional.py (CustosOperacionais)
│
└── templates/
    ├── cadastros/
    │   ├── equipes/
    │   │   ├── listar.html
    │   │   ├── form.html
    │   ├── vendedores/
    │   │   ├── listar.html
    │   │   ├── form.html
    │   ├── transportadoras/
    │   │   ├── listar.html
    │   │   ├── form.html
    │   └── clientes/
    │       ├── listar.html
    │       ├── form.html
    ├── produtos/
    │   ├── modelos/
    │       ├── listar.html
    │       ├── form.html
    └── operacional/
        ├── custos.html
```

---

## 📝 CÓDIGO COMPLETO

### 1. `app/motochefe/routes/__init__.py`

```python
"""
Blueprint principal do sistema MotoChefe
"""
from flask import Blueprint

# Criar blueprint
motochefe_bp = Blueprint('motochefe', __name__, url_prefix='/motochefe')

# Importar rotas depois de criar blueprint para evitar imports circulares
from . import cadastros, produtos, operacional

__all__ = ['motochefe_bp']
```

---

### 2. `app/motochefe/routes/cadastros.py`

```python
"""
Rotas de Cadastros Básicos - MotoChefe
"""
from flask import render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from functools import wraps
import pandas as pd
from io import BytesIO
from datetime import datetime

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.models import (
    EquipeVendasMoto, VendedorMoto, TransportadoraMoto, ClienteMoto
)

# Decorator para verificar acesso ao motochefe
def requer_motochefe(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.pode_acessar_motochefe():
            flash('Acesso negado ao sistema MotoChefe.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# EQUIPES DE VENDAS
# ============================================================

@motochefe_bp.route('/equipes')
@login_required
@requer_motochefe
def listar_equipes():
    """Lista todas as equipes de vendas"""
    equipes = EquipeVendasMoto.query.filter_by(ativo=True).order_by(EquipeVendasMoto.equipe_vendas).all()
    return render_template('motochefe/cadastros/equipes/listar.html', equipes=equipes)

@motochefe_bp.route('/equipes/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_equipe():
    """Adiciona nova equipe"""
    if request.method == 'POST':
        nome = request.form.get('equipe_vendas')

        if not nome:
            flash('Nome da equipe é obrigatório', 'danger')
            return redirect(url_for('motochefe.adicionar_equipe'))

        # Verificar duplicidade
        existe = EquipeVendasMoto.query.filter_by(equipe_vendas=nome, ativo=True).first()
        if existe:
            flash('Equipe já cadastrada', 'warning')
            return redirect(url_for('motochefe.listar_equipes'))

        equipe = EquipeVendasMoto(
            equipe_vendas=nome,
            criado_por=current_user.nome
        )
        db.session.add(equipe)
        db.session.commit()

        flash(f'Equipe {nome} cadastrada com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_equipes'))

    return render_template('motochefe/cadastros/equipes/form.html', equipe=None)

@motochefe_bp.route('/equipes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def editar_equipe(id):
    """Edita equipe existente"""
    equipe = EquipeVendasMoto.query.get_or_404(id)

    if request.method == 'POST':
        equipe.equipe_vendas = request.form.get('equipe_vendas')
        equipe.atualizado_por = current_user.nome
        db.session.commit()

        flash('Equipe atualizada com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_equipes'))

    return render_template('motochefe/cadastros/equipes/form.html', equipe=equipe)

@motochefe_bp.route('/equipes/<int:id>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_equipe(id):
    """Remove (desativa) equipe"""
    equipe = EquipeVendasMoto.query.get_or_404(id)
    equipe.ativo = False
    equipe.atualizado_por = current_user.nome
    db.session.commit()

    flash('Equipe removida com sucesso!', 'success')
    return redirect(url_for('motochefe.listar_equipes'))

@motochefe_bp.route('/equipes/exportar')
@login_required
@requer_motochefe
def exportar_equipes():
    """Exporta equipes para Excel"""
    equipes = EquipeVendasMoto.query.filter_by(ativo=True).all()

    data = [{
        'ID': e.id,
        'Equipe': e.equipe_vendas,
        'Criado Em': e.criado_em.strftime('%d/%m/%Y %H:%M') if e.criado_em else '',
        'Criado Por': e.criado_por or ''
    } for e in equipes]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Equipes')

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'equipes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@motochefe_bp.route('/equipes/importar', methods=['POST'])
@login_required
@requer_motochefe
def importar_equipes():
    """Importa equipes de Excel"""
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('motochefe.listar_equipes'))

    file = request.files['arquivo']
    if file.filename == '':
        flash('Arquivo inválido', 'danger')
        return redirect(url_for('motochefe.listar_equipes'))

    try:
        df = pd.read_excel(file)

        # Validar colunas obrigatórias
        if 'Equipe' not in df.columns:
            flash('Planilha deve conter coluna "Equipe"', 'danger')
            return redirect(url_for('motochefe.listar_equipes'))

        importados = 0
        for _, row in df.iterrows():
            nome = row['Equipe']
            if pd.isna(nome):
                continue

            # Verificar se já existe
            existe = EquipeVendasMoto.query.filter_by(equipe_vendas=nome, ativo=True).first()
            if existe:
                continue

            equipe = EquipeVendasMoto(
                equipe_vendas=nome,
                criado_por=current_user.nome
            )
            db.session.add(equipe)
            importados += 1

        db.session.commit()
        flash(f'{importados} equipes importadas com sucesso!', 'success')

    except Exception as e:
        flash(f'Erro ao importar: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_equipes'))

# ============================================================
# VENDEDORES - Implementar igual acima
# TRANSPORTADORAS - Implementar igual acima
# CLIENTES - Implementar igual acima (com mais campos)
# ============================================================

# ... (código similar para Vendedores, Transportadoras, Clientes)
```

---

### 3. `app/motochefe/routes/produtos.py`

```python
"""
Rotas de Produtos (ModeloMoto) - MotoChefe
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from decimal import Decimal

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models import ModeloMoto

@motochefe_bp.route('/modelos')
@login_required
@requer_motochefe
def listar_modelos():
    """Lista modelos de motos"""
    modelos = ModeloMoto.query.filter_by(ativo=True).order_by(ModeloMoto.nome_modelo).all()
    return render_template('motochefe/produtos/modelos/listar.html', modelos=modelos)

@motochefe_bp.route('/modelos/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_modelo():
    """Adiciona novo modelo"""
    if request.method == 'POST':
        modelo = ModeloMoto(
            nome_modelo=request.form.get('nome_modelo'),
            descricao=request.form.get('descricao'),
            potencia_motor=request.form.get('potencia_motor'),
            autopropelido=bool(request.form.get('autopropelido')),
            preco_tabela=Decimal(request.form.get('preco_tabela')),
            criado_por=current_user.nome
        )
        db.session.add(modelo)
        db.session.commit()

        flash('Modelo cadastrado com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_modelos'))

    return render_template('motochefe/produtos/modelos/form.html', modelo=None)

# ... (editar, remover, export/import similar)
```

---

### 4. `app/motochefe/routes/operacional.py`

```python
"""
Rotas Operacionais (Custos) - MotoChefe
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from decimal import Decimal

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models import CustosOperacionais

@motochefe_bp.route('/custos')
@login_required
@requer_motochefe
def custos_operacionais():
    """Exibe e edita custos operacionais"""
    custos = CustosOperacionais.get_custos_vigentes()

    if not custos:
        # Criar registro inicial se não existir
        custos = CustosOperacionais(criado_por=current_user.nome)
        db.session.add(custos)
        db.session.commit()

    return render_template('motochefe/operacional/custos.html', custos=custos)

@motochefe_bp.route('/custos/atualizar', methods=['POST'])
@login_required
@requer_motochefe
def atualizar_custos():
    """Atualiza custos operacionais"""
    custos = CustosOperacionais.get_custos_vigentes()

    if not custos:
        flash('Custos não encontrados', 'danger')
        return redirect(url_for('motochefe.custos_operacionais'))

    custos.custo_montagem = Decimal(request.form.get('custo_montagem'))
    custos.custo_movimentacao_rj = Decimal(request.form.get('custo_movimentacao_rj'))
    custos.custo_movimentacao_nacom = Decimal(request.form.get('custo_movimentacao_nacom'))
    custos.valor_comissao_fixa = Decimal(request.form.get('valor_comissao_fixa'))
    custos.atualizado_por = current_user.nome

    db.session.commit()
    flash('Custos atualizados com sucesso!', 'success')

    return redirect(url_for('motochefe.custos_operacionais'))
```

---

### 5. Registrar Blueprint em `app/__init__.py`

**Localizar a seção de blueprints e ADICIONAR**:

```python
# Blueprint MotoChefe
from app.motochefe.routes import motochefe_bp
app.register_blueprint(motochefe_bp)
```

---

## 🎨 TEMPLATES HTML

Devido ao tamanho, criei templates base que você pode replicar.

### Template Base: `listar.html`

```html
{% extends 'base.html' %}

{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h2><i class="fas fa-ICONE"></i> TITULO</h2>
        <div>
            <a href="{{ url_for('motochefe.adicionar_ENTIDADE') }}" class="btn btn-primary">
                <i class="fas fa-plus"></i> Adicionar
            </a>
            <a href="{{ url_for('motochefe.exportar_ENTIDADE') }}" class="btn btn-success">
                <i class="fas fa-file-excel"></i> Exportar
            </a>
            <button type="button" class="btn btn-info" data-bs-toggle="modal" data-bs-target="#modalImportar">
                <i class="fas fa-upload"></i> Importar
            </button>
        </div>
    </div>

    <!-- Tabela -->
    <div class="card">
        <div class="card-body">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Campo1</th>
                        <th>Campo2</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in LISTA %}
                    <tr>
                        <td>{{ item.id }}</td>
                        <td>{{ item.campo1 }}</td>
                        <td>{{ item.campo2 }}</td>
                        <td>
                            <a href="{{ url_for('motochefe.editar_ENTIDADE', id=item.id) }}" class="btn btn-sm btn-warning">
                                <i class="fas fa-edit"></i>
                            </a>
                            <form method="POST" action="{{ url_for('motochefe.remover_ENTIDADE', id=item.id) }}" style="display: inline;">
                                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                                <button type="submit" class="btn btn-sm btn-danger" onclick="return confirm('Confirma remoção?')">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- Modal Importar -->
<div class="modal fade" id="modalImportar">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5><i class="fas fa-upload"></i> Importar Excel</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form method="POST" action="{{ url_for('motochefe.importar_ENTIDADE') }}" enctype="multipart/form-data">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                <div class="modal-body">
                    <input type="file" name="arquivo" class="form-control" accept=".xlsx,.xls" required>
                </div>
                <div class="modal-footer">
                    <button type="submit" class="btn btn-primary">Importar</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

- [ ] Criar pasta `app/motochefe/routes/`
- [ ] Criar `__init__.py` com blueprint
- [ ] Criar `cadastros.py` com rotas
- [ ] Criar `produtos.py` com rotas
- [ ] Criar `operacional.py` com rotas
- [ ] Registrar blueprint em `app/__init__.py`
- [ ] Criar pasta `app/motochefe/templates/`
- [ ] Criar templates para cada entidade (18 templates)
- [ ] Testar import/export Excel
- [ ] Validar permissões de acesso

---

**Arquivo anterior**: [INSTRUCOES_COMPLETAS.md](./INSTRUCOES_COMPLETAS.md)
**Próximo passo**: Executar implementação seguindo esta estrutura
