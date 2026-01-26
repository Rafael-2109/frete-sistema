# IMPLEMENTATION PLAN: Correções no Módulo de Recebimento - CNPJ, Empresa e Produto

**Spec**: `.claude/ralph-loop/specs/correcoes-recebimento-cnpj-empresa-produto.md`
**Versão**: 1.3.0
**Data**: 26/01/2026
**Status**: EM IMPLEMENTAÇÃO (FASE 1 CONCLUÍDA ✅)

---

## ⚠️ CORREÇÕES IDENTIFICADAS NA REVISÃO (v1.2.0)

**Data da revisão**: 26/01/2026 (v1.2 - verificação final)
**Revisado por**: Agente de Planejamento

### ✅ VERIFICAÇÃO FINAL VIA GREP/READ (v1.2.0):

| Item | Verificação | Resultado |
|------|-------------|-----------|
| Import `obter_nome_empresa` em `validacao_nf_po_service.py` | `grep "obter_nome_empresa"` | ❌ **NÃO IMPORTADO** - CONFIRMADO |
| Import em `validacao_fiscal_service.py` | Linha 42 | ✅ JÁ IMPORTADO |
| Uso de `nfe_infnfe_dest_xnome` em `validacao_nf_po_service.py` | Linhas 1133, 1165, 1217, 1302, 1447 | ❌ **5 OCORRÊNCIAS** usando campo inexistente |
| `dados_nf['razao_empresa_compradora']` não atualizado | Linha 256 resolve `nome_empresa` mas linha 210 já definiu `dados_nf` | ❌ **BUG CONFIRMADO** |
| `cod_produto` usa `product_id` | Linha 855 | ❌ **BUG CONFIRMADO** |
| `_criar_registro_primeira_compra()` não recebe `cod_produto` | Linhas 445-450, 490-495 | ❌ **NÃO PASSA** parâmetros disponíveis |
| `normalizar_cnpj` em `validacao_nf_po_routes.py` | grep | ❌ **NÃO USA** |
| Status `finalizado_odoo` deleta matches | Linhas 179-185 | ⚠️ **INTENCIONAL** - matches são deletados ao finalizar |

### Discrepâncias entre Plano Original e Código Atual:

| Fase | Item | Plano Original | Realidade do Código | Ação |
|------|------|----------------|---------------------|------|
| 1.1.1 | Import `obter_nome_empresa` em `validacao_nf_po_service.py` | PENDENTE | **NÃO IMPORTADO** | ✅ MANTER - Precisa ser feito |
| 1.1.1 | Import em `validacao_fiscal_service.py` | PENDENTE | **JÁ IMPORTADO** (linha 42) | ❌ REMOVER da lista |
| 1.2.1 | Uso de `nfe_infnfe_dest_xnome` em `validacao_fiscal_service.py` | Linha 198 | Linha 198 usa, MAS linha 256 tem **fallback correto** | ⚠️ VERIFICAR comportamento |
| 2.x | `cod_produto` em `_criar_registro_primeira_compra()` | Usa `product_id` | Código JÁ resolve `default_code` em `validar_nf()` (linhas 234-278), MAS `_criar_registro_primeira_compra()` **IGNORA** e recalcula na linha 855 | ✅ MANTER - Bug confirmado |
| N/A | Campos `nfe_infnfe_dest_cnpj` em `_buscar_dfe()` | Não mencionado | **NÃO ESTÁ** na lista de campos buscados (linha 349-362) | ⚠️ ADICIONAR tarefa |

### Arquivos Verificados:

1. **`app/recebimento/services/validacao_fiscal_service.py`** (1692 linhas)
   - ✅ Linha 42: `from app.utils.cnpj_utils import normalizar_cnpj, obter_nome_empresa` - JÁ IMPORTADO
   - ✅ Linha 256: `nome_empresa = obter_nome_empresa(cnpj_empresa_compradora) or razao_empresa_compradora` - JÁ USA FALLBACK
   - ❌ Linha 855: `cod_produto = str(linha.get('product_id', [None, ''])[0])` - BUG CONFIRMADO
   - ✅ Linhas 234-278: Resolve `default_code` em bulk - MAS NÃO É PASSADO para `_criar_registro_primeira_compra()`

2. **`app/recebimento/services/validacao_nf_po_service.py`** (2000+ linhas)
   - ❌ **NÃO importa** `obter_nome_empresa` - PRECISA ADICIONAR
   - ❌ Linha 1133: `razao_empresa = dfe_data.get('nfe_infnfe_dest_xnome', '')` - CAMPO NÃO EXISTE NO ODOO
   - ❌ Linha 1165: idem
   - ❌ Linha 1217: idem
   - ❌ Linha 1302: idem
   - ❌ Linha 1447: `validacao.razao_empresa_compradora = dfe_data.get('nfe_infnfe_dest_xnome')` - CAMPO NÃO EXISTE
   - ⚠️ Comentário linha 458: `'nfe_infnfe_dest_cnpj',  # CNPJ empresa compradora (dest_xnome não existe no Odoo)` - DOCUMENTAÇÃO CONFIRMA

3. **`app/recebimento/routes/validacao_fiscal_routes.py`** (1253 linhas)
   - ✅ Linha 25: `from app.utils.cnpj_utils import normalizar_cnpj, formatar_cnpj, obter_nome_empresa, EMPRESAS_CNPJ_NOME` - JÁ IMPORTA
   - Endpoint de criação de perfil fiscal: Não chama revalidação de primeiras compras

---

## RESUMO EXECUTIVO

Corrigir problemas de preenchimento e propagação de dados nas telas de **Validação de Primeira Compra** e **Validações NF x PO**, que estão causando campos EMPRESA vazios e dados inconsistentes em produção.

### Evidências de Produção (26/01/2026)

| Problema | Tabela | Total | Afetados | % |
|----------|--------|-------|----------|---|
| CNPJ/Razão empresa vazio | `cadastro_primeira_compra` | 345 | 345 | **100%** |
| razao_empresa vazio | `validacao_nf_po_dfe` | 181 | 181 | **100%** |
| Finalizado Odoo sem itens | `validacao_nf_po_dfe` (status=finalizado_odoo) | 114 | 114 | **100%** |
| cod_produto é product_id | `cadastro_primeira_compra` | 345 | 345 | **100%** |

### Causa Raiz Identificada

1. **Campo `nfe_infnfe_dest_xnome` NÃO EXISTE no Odoo** (conforme comentário em validacao_nf_po_service.py:458)
2. O código busca `dfe_data.get('nfe_infnfe_dest_xnome', '')` que retorna vazio
3. `obter_nome_empresa(cnpj)` não está sendo usado como fallback consistentemente
4. Em `_criar_registro_primeira_compra`: `cod_produto` recebe `product_id` (linha 855) ao invés de `default_code`

---

## FASES DE IMPLEMENTAÇÃO

### FASE 1: CORRIGIR PREENCHIMENTO DE RAZÃO EMPRESA
**Prioridade**: CRÍTICA | **Bloqueadora**: SIM
**Impacto**: REQ-1, REQ-5

#### 1.1 Modificar `app/recebimento/services/validacao_nf_po_service.py`

##### 1.1.1 Importar `obter_nome_empresa` de `cnpj_utils.py`
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `app/recebimento/services/validacao_nf_po_service.py`
- **Linha 48**: Import adicionado
- **Código implementado**:
```python
from app.utils.cnpj_utils import obter_nome_empresa
```

##### 1.1.2 Modificar `_atualizar_validacao_com_dfe()` para usar `obter_nome_empresa`
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `app/recebimento/services/validacao_nf_po_service.py`
- **Linha 1452-1453**: Método modificado
- **Código implementado**:
```python
# IMPORTANTE: nfe_infnfe_dest_xnome NÃO existe no Odoo, usar mapeamento centralizado
validacao.razao_empresa_compradora = obter_nome_empresa(validacao.cnpj_empresa_compradora)
```

##### 1.1.3 Corrigir TODAS as ocorrências de `nfe_infnfe_dest_xnome`
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `app/recebimento/services/validacao_nf_po_service.py`
- **5 ocorrências corrigidas**:
  - Linha 1134-1135: `_registrar_divergencias_sem_depara()` ✅
  - Linha 1167-1168: `_registrar_divergencias_sem_po()` ✅
  - Linha 1220-1221: `_registrar_divergencias_match()` ✅
  - Linha 1306-1307: `_registrar_divergencias_match_agrupado()` ✅
  - Linha 1452-1453: `_atualizar_validacao_com_dfe()` ✅
- **Padrão aplicado** (em todas):
```python
# IMPORTANTE: nfe_infnfe_dest_xnome NÃO existe no Odoo, usar mapeamento centralizado
razao_empresa = obter_nome_empresa(cnpj_empresa)
```

#### 1.2 Modificar `app/recebimento/services/validacao_fiscal_service.py`

##### 1.2.1 Corrigir extração de razão empresa compradora
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `app/recebimento/services/validacao_fiscal_service.py`
- **Linha 259**: Adicionada atualização de dados_nf
- **Código implementado**:
```python
# 3.4. Resolver nome da empresa compradora (usa mapeamento centralizado)
# IMPORTANTE: nfe_infnfe_dest_xnome NÃO existe no Odoo, usar mapeamento centralizado
nome_empresa = obter_nome_empresa(cnpj_empresa_compradora) or razao_empresa_compradora
# 3.4.1. Atualizar dados_nf com nome resolvido (corrige bug de dados_nf com razao vazia)
dados_nf['razao_empresa_compradora'] = nome_empresa
```
- **Resultado**: Linhas 893 e 1167 agora receberão valor correto via `dados_nf.get('razao_empresa_compradora')`

##### 1.2.2 Verificar que `_buscar_dfe()` busca campo correto
- [x] **Status**: JÁ IMPLEMENTADO ✅
- **Arquivo**: `app/recebimento/services/validacao_fiscal_service.py`
- **Evidência**: Linha 353 já busca `nfe_infnfe_dest_cnpj`:
```python
'nfe_infnfe_dest_cnpj',  # CNPJ da empresa compradora
```
- **NOTA**: Campo está na lista de campos buscados no método `_buscar_dfe()`

---

### FASE 2: CORRIGIR cod_produto (product_id → default_code)
**Prioridade**: ALTA | **Depende de**: Nenhuma
**Impacto**: REQ-7

#### 2.1 Modificar `_criar_registro_primeira_compra()` em validacao_fiscal_service.py

##### 2.1.1 Usar default_code ao invés de product_id
- [ ] **Status**: PENDENTE (análise concluída)
- **Arquivo**: `app/recebimento/services/validacao_fiscal_service.py`
- **Linhas 845-940**: Modificar método
- **Problema atual** (linha 855):
```python
# ERRADO: Usa product_id do Odoo
cod_produto = str(linha.get('product_id', [None, ''])[0])
```
- **ANÁLISE DETALHADA**:
  - `_processar_sem_perfil()` (linha 409) **JÁ RECEBE** `cod_produto` como parâmetro (já resolvido!)
  - MAS as chamadas na linha 445 e 490 **NÃO PASSAM** esse parâmetro para `_criar_registro_primeira_compra()`
  - `_criar_registro_primeira_compra()` (linha 845) recalcula errado na linha 855

##### 2.1.2 Adicionar parâmetro cod_produto ao método
- [ ] **Status**: PENDENTE
- **Mudança de assinatura**:
```python
# ANTES:
def _criar_registro_primeira_compra(
    self,
    odoo_dfe_id: int,
    linha: Dict,
    cnpj: str,
    razao: str,
    dados_nf: Dict = None
) -> Dict:

# DEPOIS:
def _criar_registro_primeira_compra(
    self,
    odoo_dfe_id: int,
    linha: Dict,
    cnpj: str,
    razao: str,
    dados_nf: Dict = None,
    cod_produto: str = None,  # NOVO: código interno já resolvido
    nome_produto_interno: str = None  # NOVO: nome do produto interno
) -> Dict:
```

##### 2.1.3 Usar cod_produto passado ao invés de recalcular
- [ ] **Status**: PENDENTE
- **Mudança no corpo do método** (linha 855):
```python
# ANTES:
cod_produto = str(linha.get('product_id', [None, ''])[0])

# DEPOIS:
# Usar cod_produto passado (já resolvido de product_id → default_code)
# Se não passado, usar fallback para product_id (comportamento legado)
if cod_produto is None:
    cod_produto = str(linha.get('product_id', [None, ''])[0])
```

##### 2.1.4 Atualizar chamadas de `_criar_registro_primeira_compra()`
- [ ] **Status**: PENDENTE (linhas confirmadas via grep)
- **Arquivo**: `app/recebimento/services/validacao_fiscal_service.py`
- **Linhas a modificar**:
  - **445-450**: Chamada em `_processar_sem_perfil()` (caso: sem histórico)
  - **490-495**: Chamada em `_processar_sem_perfil()` (caso: histórico inconsistente)
- **CONTEXTO IMPORTANTE**:
  - `_processar_sem_perfil()` já recebe `cod_produto` (linha 413) e `nome_produto_interno` (linha 418)
  - Esses valores JÁ ESTÃO DISPONÍVEIS no escopo, só não estão sendo passados
- **Mudança**:
```python
# ANTES (linha 445-450):
registro = self._criar_registro_primeira_compra(
    odoo_dfe_id=odoo_dfe_id,
    linha=linha,
    cnpj=cnpj,
    razao=razao,
    dados_nf=dados_nf
)

# DEPOIS:
registro = self._criar_registro_primeira_compra(
    odoo_dfe_id=odoo_dfe_id,
    linha=linha,
    cnpj=cnpj,
    razao=razao,
    dados_nf=dados_nf,
    cod_produto=cod_produto,  # NOVO: passa código já resolvido (default_code)
    nome_produto_interno=nome_produto_interno  # NOVO: passa nome interno
)
```
- **APLICAR EM AMBAS**: linhas 445-450 E linhas 490-495

---

### FASE 3: IMPLEMENTAR PROPAGAÇÃO DE VALIDAÇÃO
**Prioridade**: MÉDIA | **Depende de**: Fase 1
**Impacto**: REQ-2

#### 3.1 Modificar `validar_primeira_compra()` em validacao_fiscal_service.py

##### 3.1.1 Após criar perfil, propagar para outras NFs pendentes
- [ ] **Status**: PENDENTE
- **Arquivo**: `app/recebimento/services/validacao_fiscal_service.py`
- **Linhas 1340-1416**: Modificar método
- **Adicionar após linha ~1405** (após `db.session.commit()`):
```python
# PROPAGAÇÃO: Validar outras 1as compras pendentes com mesma combinação
outros_pendentes = CadastroPrimeiraCompra.query.filter_by(
    cnpj_empresa_compradora=cadastro.cnpj_empresa_compradora,
    cnpj_fornecedor=cadastro.cnpj_fornecedor,
    cod_produto=cadastro.cod_produto,
    status='pendente'
).filter(CadastroPrimeiraCompra.id != cadastro_id).all()

for outro in outros_pendentes:
    outro.status = 'validado'
    outro.validado_por = f'PROPAGADO_DE_{cadastro_id}'
    outro.validado_em = datetime.utcnow()
    outro.observacao = f'Validado automaticamente por propagação do registro {cadastro_id}'

if outros_pendentes:
    db.session.commit()
    logger.info(
        f"Propagação: {len(outros_pendentes)} registros de 1a compra validados "
        f"automaticamente para combinação empresa={cadastro.cnpj_empresa_compradora}, "
        f"fornecedor={cadastro.cnpj_fornecedor}, produto={cadastro.cod_produto}"
    )
```

---

### FASE 4: IMPLEMENTAR REVALIDAÇÃO AO CRIAR PERFIL FISCAL
**Prioridade**: MÉDIA | **Depende de**: Fase 1
**Impacto**: REQ-3

#### 4.1 Criar método `revalidar_primeiras_compras_por_perfil()`

##### 4.1.1 Adicionar novo método em validacao_fiscal_service.py
- [ ] **Status**: PENDENTE
- **Arquivo**: `app/recebimento/services/validacao_fiscal_service.py`
- **Localização**: Após método `validar_primeira_compra()` (~linha 1416)
- **Código**:
```python
def revalidar_primeiras_compras_por_perfil(
    self,
    perfil: PerfilFiscalProdutoFornecedor
) -> Dict:
    """
    Revalida primeiras compras pendentes que fazem match com o perfil criado.

    Chamado após criar perfil fiscal manualmente.

    Args:
        perfil: Perfil fiscal recém criado

    Returns:
        {'sucesso': bool, 'validados': int, 'ids': List[int]}
    """
    # Buscar primeiras compras pendentes com mesma combinação
    pendentes = CadastroPrimeiraCompra.query.filter_by(
        cnpj_empresa_compradora=perfil.cnpj_empresa_compradora,
        cnpj_fornecedor=perfil.cnpj_fornecedor,
        cod_produto=perfil.cod_produto,
        status='pendente'
    ).all()

    if not pendentes:
        return {'sucesso': True, 'validados': 0, 'ids': []}

    ids_validados = []
    for cadastro in pendentes:
        cadastro.status = 'validado'
        cadastro.validado_por = f'AUTO_PERFIL_{perfil.id}'
        cadastro.validado_em = datetime.utcnow()
        cadastro.observacao = f'Validado automaticamente ao criar perfil fiscal {perfil.id}'
        ids_validados.append(cadastro.id)

    db.session.commit()

    logger.info(
        f"Revalidação por perfil {perfil.id}: {len(ids_validados)} registros "
        f"de 1a compra validados automaticamente"
    )

    return {
        'sucesso': True,
        'validados': len(ids_validados),
        'ids': ids_validados
    }
```

##### 4.1.2 Chamar método após criar perfil manualmente
- [ ] **Status**: PENDENTE
- **Arquivo**: `app/recebimento/routes/validacao_fiscal_routes.py`
- **Endpoint**: POST para criar perfil fiscal
- **Verificar**: Existe endpoint de criação manual de perfil?

---

### FASE 5: NORMALIZAR BUSCA POR CNPJ
**Prioridade**: MÉDIA | **Depende de**: Nenhuma
**Impacto**: REQ-4

#### 5.1 Verificar APIs de listagem

##### 5.1.1 Verificar rota de listagem de validações NF x PO
- [ ] **Status**: PENDENTE
- **Arquivo**: `app/recebimento/routes/validacao_nf_po_routes.py`
- **Verificar**: Parâmetro de busca por CNPJ normaliza entrada?
- **Se não**: Adicionar `normalizar_cnpj()` no filtro

##### 5.1.2 Verificar rota de listagem de primeira compra
- [ ] **Status**: PENDENTE
- **Arquivo**: `app/recebimento/routes/validacao_fiscal_routes.py`
- **Verificar**: Parâmetro de busca por CNPJ normaliza entrada?

---

### FASE 6: REGISTROS "FINALIZADO ODOO" SEM ITENS ✅ NÃO REQUER MUDANÇA
**Prioridade**: N/A | **Depende de**: N/A
**Impacto**: REQ-6 (esclarecido - não é bug)

#### 6.1 Investigação Concluída (v1.2.0)

##### 6.1.1 Comportamento Verificado
- [x] **Status**: CONFIRMADO COMO INTENCIONAL
- **Arquivo**: `app/recebimento/services/validacao_nf_po_service.py`
- **Linhas 179-185**: Matches/divergências são **DELETADOS INTENCIONALMENTE**
- **Motivo**: DFE já tem PO vinculado no Odoo → validação local não é mais necessária
- **Decisão**: **Manter comportamento atual** (correto por design)

##### 6.1.2 Documentação
- [x] **Status**: DOCUMENTADO
- Comportamento é intencional e correto
- Quando DFE tem PO vinculado (`odoo_po_vinculado_id` ou `odoo_po_fiscal_id`):
  1. Sistema limpa matches/divergências locais
  2. Status muda para `finalizado_odoo`
  3. Não há mais validação a fazer (Odoo já resolveu)

---

### FASE 7: SCRIPTS DE MIGRAÇÃO
**Prioridade**: ALTA | **Depende de**: Fase 1, 2
**Impacto**: Corrigir dados existentes

#### 7.1 Script para corrigir razao_empresa_compradora em validacao_nf_po_dfe

##### 7.1.1 Criar script Python
- [ ] **Status**: PENDENTE
- **Arquivo**: `scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.py`
- **Funcionalidade**: Atualizar registros com cnpj preenchido mas razao vazia

##### 7.1.2 Criar script SQL para Render
- [ ] **Status**: PENDENTE
- **Arquivo**: `scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.sql`
- **SQL**:
```sql
-- CORREÇÃO: razao_empresa_compradora em validacao_nf_po_dfe
UPDATE validacao_nf_po_dfe
SET razao_empresa_compradora = CASE cnpj_empresa_compradora
    WHEN '61724241000330' THEN 'NACOM GOYA - CD'
    WHEN '61724241000178' THEN 'NACOM GOYA - FB'
    WHEN '61724241000259' THEN 'NACOM GOYA - SC'
    WHEN '18467441000163' THEN 'LA FAMIGLIA - LF'
END
WHERE razao_empresa_compradora IS NULL
  AND cnpj_empresa_compradora IN ('61724241000330','61724241000178','61724241000259','18467441000163');
```

#### 7.2 Script para corrigir dados em cadastro_primeira_compra

##### 7.2.1 Criar script Python
- [ ] **Status**: PENDENTE
- **Arquivo**: `scripts/recebimento/002_corrigir_primeira_compra.py`
- **Funcionalidade**:
  1. Atualizar `razao_empresa_compradora` usando mapeamento CNPJ
  2. Atualizar `cnpj_empresa_compradora` buscando do DFE no Odoo
  3. Converter `cod_produto` de product_id para default_code (requer consulta Odoo)

##### 7.2.2 Criar script SQL parcial para Render
- [ ] **Status**: PENDENTE
- **Arquivo**: `scripts/recebimento/002_corrigir_primeira_compra.sql`
- **NOTA**: Conversão de cod_produto requer mapeamento do Odoo, não pode ser feita apenas com SQL

---

## CRITÉRIOS DE ACEITE

### Tela de Primeira Compra
- [ ] Campo EMPRESA exibe nome correto (NACOM GOYA - CD, LA FAMIGLIA, etc.)
- [ ] Nunca exibe "N/A" ou "-" quando DFE tem dados válidos
- [ ] Ao validar uma combinação, outras NFs pendentes com mesma combinação são validadas automaticamente
- [ ] Produto exibe código alfanumérico (ex: 'PAL001'), não ID numérico

### Tela de Validações NF x PO
- [ ] Busca por CNPJ funciona com qualquer formato (XX.XXX.XXX/XXXX-XX ou 14 dígitos)
- [ ] Todos os registros exibem CNPJ e nome da empresa
- [ ] Registros "Finalizado Odoo" → comportamento documentado e aprovado

### Perfil Fiscal
- [ ] Ao criar perfil fiscal, primeiras compras pendentes com match são validadas automaticamente

### Scripts de Migração
- [ ] Script Python para ambiente local (usando Flask app context)
- [ ] Script SQL para produção (Render Shell)
- [ ] Rollback documentado em caso de erro

---

## ARQUIVOS A MODIFICAR

| Arquivo | Fase | Linhas (VERIFICADAS) | Tipo de Mudança | Status |
|---------|------|----------------------|-----------------|--------|
| `app/recebimento/services/validacao_nf_po_service.py` | 1.1 | 48 (import), 1133, 1165, 1217, 1302, 1447 | Import + 5 métodos | ⏳ PENDENTE |
| `app/recebimento/services/validacao_fiscal_service.py` | 1.2 | 256 (adicionar atualização dados_nf) | Propagar nome empresa | ⏳ PENDENTE |
| `app/recebimento/services/validacao_fiscal_service.py` | 2.1 | 845-852 (assinatura), 855 (uso), 445-450, 490-495 (chamadas) | Fix cod_produto | ⏳ PENDENTE |
| `app/recebimento/services/validacao_fiscal_service.py` | 3.1 | ~1405 (após commit) | Propagação 1a compra | ⏳ PENDENTE |
| `app/recebimento/services/validacao_fiscal_service.py` | 4.1 | ~1416 (novo método) | Revalidar por perfil | ⏳ PENDENTE |
| `app/recebimento/routes/validacao_nf_po_routes.py` | 5.1.1 | A verificar | Filtro CNPJ | 🔍 VERIFICAR |
| `app/recebimento/routes/validacao_fiscal_routes.py` | 4.1.2, 5.1.2 | Após criar perfil | Chamar revalidação + Filtro CNPJ | 🔍 VERIFICAR |

### Tarefas JÁ IMPLEMENTADAS (não requerem mudança):

| Arquivo | O que | Evidência |
|---------|-------|-----------|
| `app/recebimento/services/validacao_fiscal_service.py` | Import `obter_nome_empresa` | Linha 42: já importa |
| `app/recebimento/services/validacao_fiscal_service.py` | `_buscar_dfe()` busca `nfe_infnfe_dest_cnpj` | Linha 353: já busca |
| `app/recebimento/services/validacao_fiscal_service.py` | Fallback `nome_empresa` | Linha 256: já resolve (mas não atualiza dados_nf) |

## ARQUIVOS A CRIAR

| Arquivo | Fase | Descrição |
|---------|------|-----------|
| `scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.py` | 7.1.1 | Script Python migração |
| `scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.sql` | 7.1.2 | Script SQL Render |
| `scripts/recebimento/002_corrigir_primeira_compra.py` | 7.2.1 | Script Python migração |
| `scripts/recebimento/002_corrigir_primeira_compra.sql` | 7.2.2 | Script SQL parcial |

---

## QUESTÕES EM ABERTO

### Q1: Comportamento de "Finalizado Odoo" sem itens ✅ RESOLVIDA
**Contexto**: O código atualmente DELETA matches/divergências quando marca como `finalizado_odoo`
**Resposta (v1.2.0)**: É **COMPORTAMENTO INTENCIONAL** (design, não bug).
- Código em `validacao_nf_po_service.py:179-185` limpa matches/divergências intencionalmente
- Motivo: DFE já tem PO vinculado no Odoo → validação local não é mais necessária
- Ação: **Fase 6 não requer implementação**, apenas documentação confirmando o comportamento

### Q2: Campo `nfe_infnfe_dest_xnome` no Odoo ✅ CONFIRMADA
**Contexto**: O comentário no código indica que não existe
**Confirmação (v1.2.0)**: O próprio código confirma em `validacao_nf_po_service.py:458`:
```python
'nfe_infnfe_dest_cnpj',  # CNPJ empresa compradora (dest_xnome não existe no Odoo)
```
**Ação**: Usar `obter_nome_empresa(cnpj)` como fonte de verdade (já implementado parcialmente na linha 256 de `validacao_fiscal_service.py`)

---

## ORDEM DE IMPLEMENTAÇÃO SUGERIDA

1. **Fase 1** (CRÍTICA) → Corrigir preenchimento de razão empresa (raiz do problema)
2. **Fase 2** (ALTA) → Corrigir cod_produto (product_id → default_code)
3. **Fase 7** (ALTA) → Scripts de migração para dados existentes
4. **Fase 5** (MÉDIA) → Normalizar busca por CNPJ
5. **Fase 3** (MÉDIA) → Implementar propagação de validação
6. **Fase 4** (MÉDIA) → Implementar revalidação ao criar perfil
7. ~~**Fase 6** (MÉDIA) → Investigar "Finalizado Odoo"~~ ✅ **CONCLUÍDA** - Comportamento é intencional

---

## RESUMO DE PROGRESSO

| Fase | Tarefas | Concluídas | Pendentes | Status |
|------|---------|------------|-----------|--------|
| 1. Razão Empresa | 6 | 6 | 0 | ✅ **IMPLEMENTADO** |
| 2. cod_produto | 4 | 0 | 4 | 🟡 PRONTO P/ IMPL |
| 3. Propagação | 1 | 0 | 1 | 🟡 PRONTO P/ IMPL |
| 4. Revalidação | 2 | 0 | 2 | 🟡 PRONTO P/ IMPL |
| 5. Busca CNPJ | 2 | 0 | 2 | 🟡 PRONTO P/ IMPL |
| 6. Finalizado Odoo | 2 | 0 | 0 | ✅ NÃO REQUER MUDANÇA |
| 7. Scripts | 4 | 0 | 4 | 🟡 PRONTO P/ IMPL |
| **TOTAL** | **21** | **6** | **13** | 🟢 **EM IMPLEMENTAÇÃO - v1.3.0** |

### Notas da Implementação v1.3.0 (26/01/2026):

1. **Fase 1 (Razão Empresa)**: ✅ **IMPLEMENTADO**
   - Import `obter_nome_empresa` adicionado em `validacao_nf_po_service.py:48`
   - 5 ocorrências de `nfe_infnfe_dest_xnome` corrigidas para usar `obter_nome_empresa(cnpj)`
   - Propagação de `nome_empresa` para `dados_nf` corrigida em `validacao_fiscal_service.py:259`
   - **Arquivos modificados**:
     - `app/recebimento/services/validacao_nf_po_service.py`
     - `app/recebimento/services/validacao_fiscal_service.py`
   - **Validação**: Sintaxe OK via `py_compile`

2. **Próximo passo**: Implementar Fase 2 (cod_produto: product_id → default_code)

### Notas da Verificação v1.2.0:

1. **Fase 6 (Finalizado Odoo)**: Confirmado que a deleção de matches/divergências é **COMPORTAMENTO INTENCIONAL** (linhas 179-185 de `validacao_nf_po_service.py`). Quando DFE já tem PO vinculado no Odoo, os matches locais são limpos porque a validação não é mais necessária. **NÃO é bug, é design.**

2. **Todas as outras fases**: Bugs confirmados via grep/read. Plano detalhado pronto para execução.
