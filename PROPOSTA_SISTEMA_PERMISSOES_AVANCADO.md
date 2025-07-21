# 🔐 PROPOSTA: SISTEMA DE PERMISSÕES GRANULAR AVANÇADO
# =====================================================

## 📋 ANÁLISE DO SISTEMA ATUAL

### Limitações Identificadas:
1. **Sistema binário simples**: require_admin(), require_financeiro() - muito restritivo
2. **Um vendedor por usuário**: campo `vendedor_vinculado` permite apenas 1 vendedor
3. **Equipe_vendas limitada**: existe apenas na CarteiraPrincipal
4. **Permissões hardcoded**: métodos como `pode_acessar_financeiro()` não são flexíveis
5. **Gestão descentralizada**: não há interface única para administrar acessos

### Campos Atuais Relevantes:
- **CarteiraPrincipal**: `vendedor`, `equipe_vendas`
- **FaturamentoProduto**: `vendedor` (sem equipe_vendas)
- **RelatorioFaturamentoImportado**: `vendedor` (sem equipe_vendas)
- **Usuario**: `vendedor_vinculado` (único vendedor)

## 🎯 OBJETIVOS DO NOVO SISTEMA

### 1. Múltiplos Vendedores por Usuário
- Um usuário pode ter acesso a dados de vários vendedores
- Relacionamento N:N entre Usuario ↔ Vendedor

### 2. Múltiplas Equipes de Vendas por Usuário
- Um usuário pode ter acesso a várias equipes de vendas
- Relacionamento N:N entre Usuario ↔ EquipeVendas

### 3. Gestão Centralizada de Permissões
- Interface única para administrar todos os acessos
- Estrutura hierárquica: Módulo → Função → Visualizar/Editar

### 4. Permissões Granulares
- Controle fino sobre cada funcionalidade
- Sistema de herança: módulo → todas as funções

## 🏗️ ARQUITETURA PROPOSTA

### Novos Modelos de Banco de Dados:

```python
# 1. PERFIS DE USUÁRIO (mais flexível que enum fixo)
class PerfilUsuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True)  # ex: "Gerente Regional"
    descricao = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

# 2. MÓDULOS DO SISTEMA
class ModuloSistema(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True)  # ex: "faturamento"
    nome_exibicao = db.Column(db.String(100))     # ex: "Faturamento"
    descricao = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True)
    ordem = db.Column(db.Integer, default=0)      # Para ordenação na interface

# 3. FUNÇÕES DENTRO DOS MÓDULOS
class FuncaoModulo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    modulo_id = db.Column(db.Integer, db.ForeignKey('modulo_sistema.id'))
    nome = db.Column(db.String(50))               # ex: "listar_faturas"
    nome_exibicao = db.Column(db.String(100))     # ex: "Listar Faturas"
    descricao = db.Column(db.String(255))
    rota_padrao = db.Column(db.String(200))       # ex: "/faturamento/listar"
    ativo = db.Column(db.Boolean, default=True)
    ordem = db.Column(db.Integer, default=0)

# 4. PERMISSÕES GRANULARES
class PermissaoUsuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    funcao_id = db.Column(db.Integer, db.ForeignKey('funcao_modulo.id'))
    pode_visualizar = db.Column(db.Boolean, default=False)
    pode_editar = db.Column(db.Boolean, default=False)
    concedida_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    concedida_em = db.Column(db.DateTime, default=datetime.utcnow)
    observacoes = db.Column(db.String(255))

# 5. MÚLTIPLOS VENDEDORES POR USUÁRIO
class UsuarioVendedor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    vendedor = db.Column(db.String(100))          # Nome do vendedor
    ativo = db.Column(db.Boolean, default=True)
    adicionado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    adicionado_em = db.Column(db.DateTime, default=datetime.utcnow)

# 6. MÚLTIPLAS EQUIPES DE VENDAS POR USUÁRIO
class UsuarioEquipeVendas(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    equipe_vendas = db.Column(db.String(100))     # Nome da equipe
    ativo = db.Column(db.Boolean, default=True)
    adicionado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    adicionado_em = db.Column(db.DateTime, default=datetime.utcnow)

# 7. LOG DE AUDITORIA
class LogPermissao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    acao = db.Column(db.String(50))               # CONCEDIDA, REVOGADA, USADA
    funcao_id = db.Column(db.Integer, db.ForeignKey('funcao_modulo.id'))
    detalhes = db.Column(db.Text)
    ip_origem = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
```

### Atualizações nos Modelos Existentes:

```python
# ADICIONAR equipe_vendas aos modelos que não têm
class FaturamentoProduto(db.Model):
    # ... campos existentes ...
    equipe_vendas = db.Column(db.String(100), nullable=True)  # NOVO CAMPO

class RelatorioFaturamentoImportado(db.Model):
    # ... campos existentes ...
    equipe_vendas = db.Column(db.String(100), nullable=True)  # NOVO CAMPO

# EXPANDIR modelo Usuario
class Usuario(db.Model):
    # ... campos existentes ...
    perfil_id = db.Column(db.Integer, db.ForeignKey('perfil_usuario.id'))  # SUBSTITUIR enum
    # Manter vendedor_vinculado para compatibilidade, deprecar gradualmente
    
    # NOVOS RELACIONAMENTOS
    vendedores = db.relationship('UsuarioVendedor', backref='usuario', lazy='dynamic')
    equipes_vendas = db.relationship('UsuarioEquipeVendas', backref='usuario', lazy='dynamic')
    permissoes = db.relationship('PermissaoUsuario', backref='usuario', lazy='dynamic')
```

## 💻 INTERFACE DE ADMINISTRAÇÃO

### Página Principal: `/admin/permissoes`

```html
<!-- ESTRUTURA HIERÁRQUICA -->
<div class="admin-permissoes">
    <!-- SELETOR DE USUÁRIO -->
    <div class="usuario-selector">
        <select id="usuario_id">
            <option value="">Selecione um usuário...</option>
            <!-- Lista de usuários -->
        </select>
        <button onclick="carregarPermissoes()">Carregar Permissões</button>
    </div>
    
    <!-- GRID DE PERMISSÕES -->
    <div class="permissoes-grid">
        <table class="table">
            <thead>
                <tr>
                    <th>Módulo / Função</th>
                    <th>Visualizar</th>
                    <th>Editar</th>
                    <th>Ações</th>
                </tr>
            </thead>
            <tbody>
                <!-- MÓDULO FATURAMENTO -->
                <tr class="modulo-row">
                    <td>
                        <strong>📊 Faturamento</strong>
                        <input type="checkbox" id="modulo_faturamento" onchange="toggleModulo('faturamento')">
                        <label>Aplicar a todas as funções</label>
                    </td>
                    <td>
                        <input type="checkbox" class="visualizar-modulo" data-modulo="faturamento">
                    </td>
                    <td>
                        <input type="checkbox" class="editar-modulo" data-modulo="faturamento">
                    </td>
                    <td>
                        <button onclick="salvarModulo('faturamento')">Salvar</button>
                    </td>
                </tr>
                
                <!-- FUNÇÕES DO FATURAMENTO -->
                <tr class="funcao-row" data-modulo="faturamento">
                    <td style="padding-left: 30px;">
                        ↳ Listar Faturas
                    </td>
                    <td>
                        <input type="checkbox" class="perm-visualizar" data-funcao="listar_faturas">
                    </td>
                    <td>
                        <input type="checkbox" class="perm-editar" data-funcao="listar_faturas">
                    </td>
                    <td>
                        <span class="status-badge">Ativo</span>
                    </td>
                </tr>
                
                <!-- Mais funções... -->
            </tbody>
        </table>
    </div>
    
    <!-- SEÇÃO VENDEDORES -->
    <div class="vendedores-section">
        <h4>🧑‍💼 Vendedores Autorizados</h4>
        <div class="vendedores-list">
            <!-- Lista de vendedores com checkbox -->
        </div>
        <button onclick="adicionarVendedor()">+ Adicionar Vendedor</button>
    </div>
    
    <!-- SEÇÃO EQUIPES DE VENDAS -->
    <div class="equipes-section">
        <h4>👥 Equipes de Vendas Autorizadas</h4>
        <div class="equipes-list">
            <!-- Lista de equipes com checkbox -->
        </div>
        <button onclick="adicionarEquipe()">+ Adicionar Equipe</button>
    </div>
</div>
```

## 🔧 NOVO SISTEMA DE DECORADORES

### Decorador Principal:
```python
from functools import wraps
from flask import abort, request
from flask_login import current_user

def require_permission(modulo, funcao, nivel='visualizar'):
    """
    Decorador principal para verificar permissões granulares
    
    Args:
        modulo (str): Nome do módulo (ex: 'faturamento')
        funcao (str): Nome da função (ex: 'listar_faturas')
        nivel (str): 'visualizar' ou 'editar'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            # Verificar permissão específica
            if not PermissaoService.usuario_tem_permissao(
                current_user.id, modulo, funcao, nivel
            ):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# DECORADORES DE CONVENIÊNCIA
def require_faturamento_view(funcao):
    return require_permission('faturamento', funcao, 'visualizar')

def require_faturamento_edit(funcao):
    return require_permission('faturamento', funcao, 'editar')

# EXEMPLO DE USO
@app.route('/faturamento/listar')
@require_faturamento_view('listar_faturas')
def listar_faturas():
    # Aplicar filtros automáticos de vendedor/equipe
    faturas = FaturamentoService.listar_com_filtros_usuario(current_user)
    return render_template('faturamento/listar.html', faturas=faturas)
```

### Service de Permissões:
```python
class PermissaoService:
    
    @staticmethod
    def usuario_tem_permissao(usuario_id, modulo, funcao, nivel='visualizar'):
        """Verifica se usuário tem permissão específica"""
        permissao = PermissaoUsuario.query.join(FuncaoModulo).join(ModuloSistema).filter(
            PermissaoUsuario.usuario_id == usuario_id,
            ModuloSistema.nome == modulo,
            FuncaoModulo.nome == funcao
        ).first()
        
        if not permissao:
            return False
        
        if nivel == 'visualizar':
            return permissao.pode_visualizar
        elif nivel == 'editar':
            return permissao.pode_editar
        
        return False
    
    @staticmethod
    def obter_vendedores_usuario(usuario_id):
        """Retorna lista de vendedores que usuário tem acesso"""
        return [v.vendedor for v in UsuarioVendedor.query.filter_by(
            usuario_id=usuario_id, ativo=True
        ).all()]
    
    @staticmethod
    def obter_equipes_usuario(usuario_id):
        """Retorna lista de equipes que usuário tem acesso"""
        return [e.equipe_vendas for e in UsuarioEquipeVendas.query.filter_by(
            usuario_id=usuario_id, ativo=True
        ).all()]
    
    @staticmethod
    def aplicar_filtro_vendedor_automatico(query, model, usuario_id):
        """Aplica filtro automático baseado nos vendedores do usuário"""
        vendedores = PermissaoService.obter_vendedores_usuario(usuario_id)
        equipes = PermissaoService.obter_equipes_usuario(usuario_id)
        
        # Se usuário tem acesso total, não filtrar
        if PermissaoService.usuario_tem_permissao(usuario_id, 'admin', 'acesso_total'):
            return query
        
        # Aplicar filtros
        filtros = []
        
        if vendedores:
            filtros.append(model.vendedor.in_(vendedores))
        
        if equipes and hasattr(model, 'equipe_vendas'):
            filtros.append(model.equipe_vendas.in_(equipes))
        
        if filtros:
            return query.filter(or_(*filtros))
        else:
            # Usuário sem acesso a nenhum vendedor/equipe
            return query.filter(False)  # Retorna vazio
```

## 📊 MIGRAÇÃO GRADUAL

### Fase 1: Preparação (Semana 1)
1. ✅ Criar novos modelos de banco
2. ✅ Adicionar campo `equipe_vendas` aos modelos existentes
3. ✅ Atualizar importação Odoo
4. ✅ Migração de dados preservando funcionalidade atual

### Fase 2: Interface Admin (Semana 2)
1. ✅ Criar página de administração de permissões
2. ✅ Implementar JavaScript para gestão hierárquica
3. ✅ Testes da interface

### Fase 3: Novo Sistema (Semana 3)
1. ✅ Implementar novos decoradores
2. ✅ Criar PermissaoService
3. ✅ Manter compatibilidade com sistema antigo

### Fase 4: Migração Rotas (Semana 4)
1. ✅ Migrar rotas críticas para novo sistema
2. ✅ Testes extensivos
3. ✅ Documentação

### Fase 5: Finalização (Semana 5)
1. ✅ Migrar todas as rotas restantes
2. ✅ Remover sistema antigo
3. ✅ Treinamento usuários

## 🔒 VANTAGENS DO NOVO SISTEMA

### 1. Flexibilidade Total
- Usuário pode ter acesso a múltiplos vendedores/equipes
- Permissões específicas por função
- Fácil adição de novos módulos/funções

### 2. Gestão Centralizada
- Interface única para todas as permissões
- Visão completa dos acessos de cada usuário
- Log de auditoria completo

### 3. Segurança Avançada
- Princípio do menor privilégio
- Filtros automáticos de dados
- Rastreabilidade completa

### 4. Escalabilidade
- Suporte a novos perfis sem código
- Adição dinâmica de módulos/funções
- Sistema preparado para crescimento

## 📋 CRONOGRAMA DETALHADO

### **SEMANA 1: FUNDAÇÃO**
- **Dia 1-2**: Criar modelos de banco + migração
- **Dia 3-4**: Adicionar equipe_vendas aos modelos existentes
- **Dia 5**: Atualizar importação Odoo + testes

### **SEMANA 2: INTERFACE**
- **Dia 1-3**: Desenvolver página de administração
- **Dia 4-5**: JavaScript hierárquico + testes UX

### **SEMANA 3: BACKEND**
- **Dia 1-2**: Implementar PermissaoService
- **Dia 3-4**: Novos decoradores + filtros automáticos
- **Dia 5**: Testes de integração

### **SEMANA 4: MIGRAÇÃO CRÍTICA**
- **Dia 1-2**: Migrar rotas financeiro + faturamento
- **Dia 3-4**: Migrar rotas monitoramento + carteira
- **Dia 5**: Testes regressivos

### **SEMANA 5: FINALIZAÇÃO**
- **Dia 1-2**: Migrar rotas restantes
- **Dia 3**: Remover sistema antigo
- **Dia 4-5**: Documentação + treinamento

## 🎯 CRITÉRIOS DE SUCESSO

### Funcionais:
- ✅ Usuário pode ter múltiplos vendedores/equipes
- ✅ Interface de administração intuitiva
- ✅ Filtros automáticos funcionando
- ✅ Compatibilidade total com dados existentes

### Técnicos:
- ✅ Performance mantida (queries otimizadas)
- ✅ Zero downtime na migração
- ✅ Log de auditoria completo
- ✅ Testes cobrindo 90%+ do código

### Negócio:
- ✅ Redução de tempo de gestão de acessos
- ✅ Maior segurança e compliance
- ✅ Flexibilidade para crescimento futuro
- ✅ Satisfação dos usuários administradores

---

**📝 Próximos Passos:**
1. Aprovação da proposta pela liderança
2. Alocação de recursos (desenvolvedor + DBA)
3. Setup do ambiente de desenvolvimento
4. Início da Fase 1 com criação dos modelos

**⚠️ Riscos Identificados:**
- Migração de dados complexa (mitigação: testes extensivos)
- Impacto na performance (mitigação: índices otimizados)
- Curva de aprendizado usuários (mitigação: treinamento + docs)

**💰 Estimativa de Esforço:**
- **40-50 horas** de desenvolvimento
- **10-15 horas** de testes
- **5-10 horas** de documentação
- **Total: 55-75 horas** (2-3 sprints) 