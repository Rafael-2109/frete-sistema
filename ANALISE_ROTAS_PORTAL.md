# ANÁLISE COMPLETA DO SISTEMA DE ROTAS - PORTAL
**Data: 24/08/2025**
**Análise Profunda com Evidências**

## 1. ESTRUTURA DE BLUEPRINTS

### 1.1 Blueprint PAI
```python
portal_bp = Blueprint('portal', __name__, url_prefix='/portal')
```

### 1.2 Blueprints FILHOS Registrados
```python
portal_bp.register_blueprint(depara_bp)         # Atacadão De-Para
portal_bp.register_blueprint(agendamento_bp)    # Atacadão Agendamento  
portal_bp.register_blueprint(verificacao_protocolo_bp, url_prefix='/atacadao')
portal_bp.register_blueprint(tenda_depara_bp)   # Tenda De-Para
portal_bp.register_blueprint(tenda_agendamento_bp) # Tenda Agendamento
```

## 2. DEFINIÇÃO DOS BLUEPRINTS FILHOS

### 2.1 ATACADÃO DE-PARA
```python
# Arquivo: app/portal/atacadao/routes_depara.py
bp = Blueprint('portal_depara', __name__, url_prefix='/atacadao/depara')
```

**Rotas definidas no código:**
- `/` → função `index`
- `/novo` → função `novo`
- `/editar/<int:id>` → função `editar`
- `/excluir/<int:id>` → função `excluir`
- `/importar` → função `importar`
- `/buscar_produto_nosso/<codigo>` → função `buscar_produto_nosso`
- `/converter_codigo/<codigo_nosso>` → função `converter_codigo`
- `/api/criar` → função `api_criar`

**❌ PROBLEMA: NÃO EXISTE ROTA `/listar`**

### 2.2 TENDA DE-PARA
```python
# Arquivo: app/portal/tenda/routes_depara.py
bp = Blueprint('portal_tenda_depara', __name__, url_prefix='/tenda/depara')
```

**Rotas definidas no código:**
- `/` → função `index`
- `/ean` → função `index_ean`
- `/filiais` → função `index_filiais`
- `/ean/listar` → função `listar_ean`
- `/ean/novo` → função `novo_ean`
- `/ean/importar` → função `importar_ean`
- `/ean/<int:id>/editar` → função `editar_ean`
- `/ean/<int:id>/excluir` → função `excluir_ean`
- `/local` → função `listar_local`
- `/local/novo` → função `novo_local`
- `/local/importar` → função `importar_local`
- `/local/<int:id>/editar` → função `editar_local`
- `/local/<int:id>/excluir` → função `excluir_local`
- `/api/ean/buscar/<codigo_nosso>` → função `api_buscar_ean`
- `/api/local/buscar/<cnpj>` → função `api_buscar_local`

## 3. ROTAS FINAIS NO SISTEMA (Runtime)

### 3.1 ATACADÃO
```
/portal/atacadao/depara/ → portal.portal_depara.index
/portal/atacadao/depara/novo → portal.portal_depara.novo
/portal/atacadao/depara/editar/<int:id> → portal.portal_depara.editar
/portal/atacadao/depara/excluir/<int:id> → portal.portal_depara.excluir
/portal/atacadao/depara/importar → portal.portal_depara.importar
/portal/atacadao/depara/buscar_produto_nosso/<codigo> → portal.portal_depara.buscar_produto_nosso
/portal/atacadao/depara/converter_codigo/<codigo_nosso> → portal.portal_depara.converter_codigo
/portal/atacadao/depara/api/criar → portal.portal_depara.api_criar
```

### 3.2 TENDA
```
/portal/tenda/depara/ → portal.portal_tenda_depara.index
/portal/tenda/depara/ean → portal.portal_tenda_depara.index_ean
/portal/tenda/depara/filiais → portal.portal_tenda_depara.index_filiais
/portal/tenda/depara/ean/listar → portal.portal_tenda_depara.listar_ean
/portal/tenda/depara/ean/novo → portal.portal_tenda_depara.novo_ean
/portal/tenda/depara/ean/importar → portal.portal_tenda_depara.importar_ean
/portal/tenda/depara/ean/<int:id>/editar → portal.portal_tenda_depara.editar_ean
/portal/tenda/depara/ean/<int:id>/excluir → portal.portal_tenda_depara.excluir_ean
/portal/tenda/depara/local → portal.portal_tenda_depara.listar_local
/portal/tenda/depara/local/novo → portal.portal_tenda_depara.novo_local
/portal/tenda/depara/local/importar → portal.portal_tenda_depara.importar_local
/portal/tenda/depara/local/<int:id>/editar → portal.portal_tenda_depara.editar_local
/portal/tenda/depara/local/<int:id>/excluir → portal.portal_tenda_depara.excluir_local
```

## 4. TEMPLATES E SEUS URL_FOR

### 4.1 ATACADÃO index.html
**Arquivo:** `app/templates/portal/atacadao/depara/index.html`

**URL_FOR no template:**
- `url_for('portal.central_portais')` ✅
- `url_for('portal.portal_depara.listar')` ❌ **NÃO EXISTE**
- `url_for('portal.portal_depara.novo')` ✅
- `url_for('portal.portal_depara.importar')` ✅
- `url_for('portal.portal_depara.exportar')` ❌ **NÃO EXISTE**

### 4.2 TENDA index_ean.html
**Arquivo:** `app/templates/portal/tenda/depara/index_ean.html`

**URL_FOR no template:**
- `url_for('portal.central_portais')` ✅
- `url_for('portal_tenda_depara.listar_ean')` ❌ **FALTA PREFIXO portal.**
- `url_for('portal_tenda_depara.novo_ean')` ❌ **FALTA PREFIXO portal.**
- `url_for('portal_tenda_depara.importar_ean')` ❌ **FALTA PREFIXO portal.**

### 4.3 TENDA index_filiais.html
**Arquivo:** `app/templates/portal/tenda/depara/index_filiais.html`

**URL_FOR no template:**
- `url_for('portal.central_portais')` ✅
- `url_for('portal_tenda_depara.listar_local')` ❌ **FALTA PREFIXO portal.**
- `url_for('portal_tenda_depara.novo_local')` ❌ **FALTA PREFIXO portal.**
- `url_for('portal_tenda_depara.importar_local')` ❌ **FALTA PREFIXO portal.**

## 5. PROBLEMAS IDENTIFICADOS

### 🔴 PROBLEMA 1: ATACADÃO
**Template:** `app/templates/portal/atacadao/depara/index.html`
- Está chamando `url_for('portal.portal_depara.listar')` mas **NÃO EXISTE** rota `listar`
- Está chamando `url_for('portal.portal_depara.exportar')` mas **NÃO EXISTE** rota `exportar`

**SOLUÇÃO:**
- Mudar `url_for('portal.portal_depara.listar')` → `url_for('portal.portal_depara.index')`
- Remover ou implementar a rota `exportar`

### 🔴 PROBLEMA 2: TENDA EAN
**Template:** `app/templates/portal/tenda/depara/index_ean.html`
- Todos os `url_for` estão SEM o prefixo `portal.`

**SOLUÇÃO:**
- `url_for('portal_tenda_depara.listar_ean')` → `url_for('portal.portal_tenda_depara.listar_ean')`
- `url_for('portal_tenda_depara.novo_ean')` → `url_for('portal.portal_tenda_depara.novo_ean')`
- `url_for('portal_tenda_depara.importar_ean')` → `url_for('portal.portal_tenda_depara.importar_ean')`

### 🔴 PROBLEMA 3: TENDA FILIAIS
**Template:** `app/templates/portal/tenda/depara/index_filiais.html`
- Todos os `url_for` estão SEM o prefixo `portal.`

**SOLUÇÃO:**
- `url_for('portal_tenda_depara.listar_local')` → `url_for('portal.portal_tenda_depara.listar_local')`
- `url_for('portal_tenda_depara.novo_local')` → `url_for('portal.portal_tenda_depara.novo_local')`
- `url_for('portal_tenda_depara.importar_local')` → `url_for('portal.portal_tenda_depara.importar_local')`

## 6. CORREÇÕES NECESSÁRIAS

### 6.1 Atacadão index.html
- [ ] Linha 35: Mudar `.listar` para `.index`
- [ ] Linha 48: Remover link de exportar ou implementar rota

### 6.2 Tenda index_ean.html
- [ ] Linha 36: Adicionar prefixo `portal.`
- [ ] Linha 40: Adicionar prefixo `portal.`
- [ ] Linha 44: Adicionar prefixo `portal.`

### 6.3 Tenda index_filiais.html
- [ ] Linha 37: Adicionar prefixo `portal.`
- [ ] Linha 41: Adicionar prefixo `portal.`
- [ ] Linha 45: Adicionar prefixo `portal.`

## 7. RESUMO EXECUTIVO

O sistema possui uma hierarquia de blueprints onde:
1. `portal_bp` é o blueprint pai com prefixo `/portal`
2. Os blueprints filhos são registrados dentro dele
3. Os endpoints finais precisam do prefixo `portal.` + nome do blueprint filho

**Principais erros encontrados:**
1. Atacadão tentando acessar rotas inexistentes (`listar` e `exportar`)
2. Tenda sem o prefixo `portal.` nos endpoints

**Status:** Aguardando correções nos templates