# IMPLEMENTATION PLAN: Correções no Módulo de Recebimento - CNPJ, Empresa e Produto

**Spec**: `.claude/ralph-loop/specs/correcoes-recebimento-cnpj-empresa-produto.md`
**Versão**: 1.8.0
**Data**: 26/01/2026
**Status**: ✅ IMPLEMENTAÇÃO CONCLUÍDA (TODAS AS FASES)

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
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `app/recebimento/services/validacao_fiscal_service.py`
- **Linhas modificadas**: 853-881 (assinatura e corpo do método)
- **Solução**: Adicionados parâmetros opcionais `cod_produto` e `nome_produto_interno`

##### 2.1.2 Adicionar parâmetro cod_produto ao método
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Código implementado** (linhas 853-874):
```python
def _criar_registro_primeira_compra(
    self,
    odoo_dfe_id: int,
    linha: Dict,
    cnpj: str,
    razao: str,
    dados_nf: Dict = None,
    cod_produto: str = None,
    nome_produto_interno: str = None
) -> Dict:
    """
    Cria registro de 1a compra para validacao manual.

    Args:
        odoo_dfe_id: ID do DFE no Odoo
        linha: Dados da linha do DFE (dfe.line)
        cnpj: CNPJ do fornecedor (normalizado)
        razao: Razao social do fornecedor
        dados_nf: Dados gerais da NF (cnpj_empresa_compradora, etc.)
        cod_produto: Codigo interno do produto (default_code). Se None, usa product_id (legado)
        nome_produto_interno: Nome interno do produto. Se None, usa det_prod_xprod
    """
```

##### 2.1.3 Usar cod_produto passado ao invés de recalcular
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Código implementado** (linhas 875-881):
```python
# CORREÇÃO FASE 2: Usar cod_produto passado (já resolvido de product_id → default_code)
# Se não passado, usar fallback para product_id (comportamento legado)
if cod_produto is None:
    cod_produto = str(linha.get('product_id', [None, ''])[0])

# Usar nome_produto_interno se disponível, senão usar nome do XML
nome_produto = nome_produto_interno or linha.get('det_prod_xprod', '')
```

##### 2.1.4 Atualizar chamadas de `_criar_registro_primeira_compra()`
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `app/recebimento/services/validacao_fiscal_service.py`
- **Linhas modificadas**:
  - **449-457**: Chamada em `_processar_sem_perfil()` (caso: sem histórico) ✅
  - **496-504**: Chamada em `_processar_sem_perfil()` (caso: histórico inconsistente) ✅
- **Código implementado** (ambas as chamadas):
```python
registro = self._criar_registro_primeira_compra(
    odoo_dfe_id=odoo_dfe_id,
    linha=linha,
    cnpj=cnpj,
    razao=razao,
    dados_nf=dados_nf,
    cod_produto=cod_produto,  # FASE 2: passa código já resolvido (default_code)
    nome_produto_interno=nome_produto_interno
)
```
- **Validação**: Sintaxe OK via `py_compile`

---

### FASE 3: IMPLEMENTAR PROPAGAÇÃO DE VALIDAÇÃO
**Prioridade**: MÉDIA | **Depende de**: Fase 1
**Impacto**: REQ-2

#### 3.1 Modificar `validar_primeira_compra()` em validacao_fiscal_service.py

##### 3.1.1 Após criar perfil, propagar para outras NFs pendentes
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `app/recebimento/services/validacao_fiscal_service.py`
- **Linhas 1437-1479**: Lógica de propagação adicionada após `db.session.commit()`
- **Código implementado**:
```python
# ===========================================================
# FASE 3: PROPAGAÇÃO - Validar outras 1as compras pendentes
# com mesma combinação (empresa + fornecedor + produto)
# ===========================================================
outros_validados = 0
ids_propagados = []

if cadastro.cnpj_empresa_compradora and cadastro.cnpj_fornecedor and cadastro.cod_produto:
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
        ids_propagados.append(outro.id)

    if outros_pendentes:
        db.session.commit()
        outros_validados = len(outros_pendentes)
        logger.info(
            f"Propagação: {outros_validados} registros de 1a compra validados "
            f"automaticamente para combinação empresa={cadastro.cnpj_empresa_compradora}, "
            f"fornecedor={cadastro.cnpj_fornecedor}, produto={cadastro.cod_produto}. "
            f"IDs: {ids_propagados}"
        )

mensagem = 'Perfil fiscal criado com sucesso'
if outros_validados > 0:
    mensagem += f'. {outros_validados} outras NFs validadas automaticamente'

return {
    'sucesso': True,
    'mensagem': mensagem,
    'perfil_id': perfil.id,
    'propagados': outros_validados,
    'ids_propagados': ids_propagados
}
```
- **Validação**: Sintaxe OK via `py_compile`
- **Melhorias sobre o plano original**:
  1. Adicionada verificação de campos não-nulos antes da busca
  2. Retorna IDs dos registros propagados para rastreabilidade
  3. Mensagem de retorno informativa para o usuário

---

### FASE 4: IMPLEMENTAR REVALIDAÇÃO AO CRIAR PERFIL FISCAL
**Prioridade**: MÉDIA | **Depende de**: Fase 1
**Impacto**: REQ-3

#### 4.1 Criar método `revalidar_primeiras_compras_por_perfil()`

##### 4.1.1 Adicionar novo método em validacao_fiscal_service.py
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `app/recebimento/services/validacao_fiscal_service.py`
- **Localização**: Após método `validar_primeira_compra()` (linhas 1481-1527)
- **Código implementado**:
```python
def revalidar_primeiras_compras_por_perfil(
    self,
    perfil: PerfilFiscalProdutoFornecedor
) -> Dict:
    """
    Revalida primeiras compras pendentes que fazem match com o perfil criado.

    FASE 4: Chamado após criar perfil fiscal manualmente (via importação Excel
    ou outro fluxo que não seja a validação de 1ª compra).

    Args:
        perfil: Perfil fiscal recém criado

    Returns:
        {'sucesso': bool, 'validados': int, 'ids': List[int]}
    """
    # Validar que perfil tem campos necessários para match
    if not perfil.cnpj_empresa_compradora or not perfil.cnpj_fornecedor or not perfil.cod_produto:
        return {'sucesso': True, 'validados': 0, 'ids': []}

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
        cadastro.observacao = f'Validado automaticamente ao criar/atualizar perfil fiscal {perfil.id}'
        ids_validados.append(cadastro.id)

    db.session.commit()
    return {'sucesso': True, 'validados': len(ids_validados), 'ids': ids_validados}
```
- **Validação**: Sintaxe OK via `py_compile`

##### 4.1.2 Chamar método após criar perfil via importação Excel
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `app/recebimento/routes/validacao_fiscal_routes.py`
- **Endpoint**: `POST /api/recebimento/perfil-fiscal/importar-excel`
- **Linhas modificadas**:
  - **460**: Adicionada lista `perfis_processados = []` para coletar perfis
  - **624-625**: Perfis atualizados são coletados
  - **651-652**: Perfis criados são coletados
  - **659-685**: Loop de revalidação após commit + retorno de estatísticas
- **Retorno do endpoint agora inclui**:
  - `revalidacoes`: quantidade de 1as compras validadas automaticamente
  - `ids_revalidados`: lista dos IDs validados (limitado a 100)
- **Validação**: Sintaxe OK via `py_compile`

---

### FASE 5: NORMALIZAR BUSCA POR CNPJ
**Prioridade**: MÉDIA | **Depende de**: Nenhuma
**Impacto**: REQ-4

#### 5.1 Verificar APIs de listagem

##### 5.1.1 Verificar rota de listagem de validações NF x PO
- [x] **Status**: ✅ JÁ IMPLEMENTADO (verificado 26/01/2026)
- **Arquivo**: `app/recebimento/routes/validacao_nf_po_routes.py`
- **Verificação**: O método `listar_validacoes` no service já chama `self._limpar_cnpj(cnpj_fornecedor)` na linha 2073
- **Evidência**: `validacao_nf_po_service.py:2073`: `cnpj_limpo = self._limpar_cnpj(cnpj_fornecedor)`

##### 5.1.2 Verificar rota de listagem de primeira compra
- [x] **Status**: ✅ NÃO REQUER (sem filtro por CNPJ)
- **Arquivo**: `app/recebimento/routes/validacao_fiscal_routes.py`
- **Verificação**: O endpoint `GET /primeira-compra` não tem parâmetro de busca por CNPJ, apenas `status`

##### 5.1.3 Verificar rota de listagem de perfis fiscais (adicional)
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `app/recebimento/routes/validacao_fiscal_routes.py`
- **Linha 288**: Corrigida busca por CNPJ para normalizar entrada
- **Código implementado**:
```python
# FASE 5: Normalizar CNPJ antes de buscar (aceita formatado ou apenas dígitos)
cnpj_limpo = normalizar_cnpj(cnpj)
query = query.filter(PerfilFiscalProdutoFornecedor.cnpj_fornecedor.ilike(f'%{cnpj_limpo}%'))
```
- **Validação**: Sintaxe OK via `py_compile`

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
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.py`
- **Funcionalidade**: Atualizar registros com cnpj preenchido mas razao vazia
- **Uso**:
  - Dry-run: `python scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.py --dry-run`
  - Execução: `python scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.py`

##### 7.1.2 Criar script SQL para Render
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.sql`
- **Contém**: Diagnóstico, preview, UPDATE, verificação e rollback
- **Uso**: Conectar `psql $DATABASE_URL` e executar os passos na ordem

#### 7.2 Script para corrigir dados em cadastro_primeira_compra

##### 7.2.1 Criar script Python
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `scripts/recebimento/002_corrigir_primeira_compra.py`
- **Funcionalidade**:
  1. Atualizar `cnpj_empresa_compradora` buscando do DFE no Odoo
  2. Atualizar `razao_empresa_compradora` usando mapeamento CNPJ
  3. Converter `cod_produto` de product_id para default_code (consulta Odoo em batch)
- **Uso**:
  - Dry-run: `python scripts/recebimento/002_corrigir_primeira_compra.py --dry-run`
  - Execução: `python scripts/recebimento/002_corrigir_primeira_compra.py`
  - Apenas CNPJ/razão: `python scripts/recebimento/002_corrigir_primeira_compra.py --skip-produto`
  - Apenas cod_produto: `python scripts/recebimento/002_corrigir_primeira_compra.py --only-produto`

##### 7.2.2 Criar script SQL parcial para Render
- [x] **Status**: ✅ IMPLEMENTADO (26/01/2026)
- **Arquivo**: `scripts/recebimento/002_corrigir_primeira_compra.sql`
- **NOTA**: Correção COMPLETA requer script Python (consulta Odoo)
- **Contém**: Diagnóstico, UPDATE parcial (apenas razão), instruções para usar Python

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
| `app/recebimento/services/validacao_nf_po_service.py` | 1.1 | 48 (import), 1133, 1165, 1217, 1302, 1447 | Import + 5 métodos | ✅ IMPLEMENTADO |
| `app/recebimento/services/validacao_fiscal_service.py` | 1.2 | 256-259 (atualização dados_nf) | Propagar nome empresa | ✅ IMPLEMENTADO |
| `app/recebimento/services/validacao_fiscal_service.py` | 2.1 | 853-881 (assinatura), 875-881 (uso), 449-457, 496-504 (chamadas) | Fix cod_produto | ✅ IMPLEMENTADO |
| `app/recebimento/services/validacao_fiscal_service.py` | 3.1 | 1437-1479 (propagação) | Propagação 1a compra | ✅ IMPLEMENTADO |
| `app/recebimento/services/validacao_fiscal_service.py` | 4.1 | 1481-1527 (novo método) | Revalidar por perfil | ✅ IMPLEMENTADO |
| `app/recebimento/routes/validacao_fiscal_routes.py` | 4.1.2 | 460, 624-625, 651-652, 659-685 | Chamar revalidação na importação | ✅ IMPLEMENTADO |
| `app/recebimento/routes/validacao_nf_po_routes.py` | 5.1.1 | N/A | Filtro CNPJ | ✅ JÁ NORMALIZA (service:2073) |
| `app/recebimento/routes/validacao_fiscal_routes.py` | 5.1.3 | 288 | Filtro CNPJ perfis-fiscais | ✅ IMPLEMENTADO |

### Tarefas JÁ IMPLEMENTADAS (não requerem mudança):

| Arquivo | O que | Evidência |
|---------|-------|-----------|
| `app/recebimento/services/validacao_fiscal_service.py` | Import `obter_nome_empresa` | Linha 42: já importa |
| `app/recebimento/services/validacao_fiscal_service.py` | `_buscar_dfe()` busca `nfe_infnfe_dest_cnpj` | Linha 353: já busca |
| `app/recebimento/services/validacao_fiscal_service.py` | Fallback `nome_empresa` | Linha 256: já resolve (mas não atualiza dados_nf) |

## ARQUIVOS CRIADOS

| Arquivo | Fase | Descrição | Status |
|---------|------|-----------|--------|
| `scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.py` | 7.1.1 | Script Python migração | ✅ CRIADO |
| `scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.sql` | 7.1.2 | Script SQL Render | ✅ CRIADO |
| `scripts/recebimento/002_corrigir_primeira_compra.py` | 7.2.1 | Script Python migração | ✅ CRIADO |
| `scripts/recebimento/002_corrigir_primeira_compra.sql` | 7.2.2 | Script SQL parcial | ✅ CRIADO |

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
| 2. cod_produto | 4 | 4 | 0 | ✅ **IMPLEMENTADO** |
| 3. Propagação | 1 | 1 | 0 | ✅ **IMPLEMENTADO** |
| 4. Revalidação | 2 | 2 | 0 | ✅ **IMPLEMENTADO** |
| 5. Busca CNPJ | 3 | 3 | 0 | ✅ **IMPLEMENTADO** |
| 6. Finalizado Odoo | 2 | 0 | 0 | ✅ NÃO REQUER MUDANÇA |
| 7. Scripts | 4 | 4 | 0 | ✅ **IMPLEMENTADO** |
| **TOTAL** | **22** | **22** | **0** | 🟢 **CONCLUÍDO - v1.8.0** |

### Notas da Implementação v1.3.0 (26/01/2026):

1. **Fase 1 (Razão Empresa)**: ✅ **IMPLEMENTADO**
   - Import `obter_nome_empresa` adicionado em `validacao_nf_po_service.py:48`
   - 5 ocorrências de `nfe_infnfe_dest_xnome` corrigidas para usar `obter_nome_empresa(cnpj)`
   - Propagação de `nome_empresa` para `dados_nf` corrigida em `validacao_fiscal_service.py:259`
   - **Arquivos modificados**:
     - `app/recebimento/services/validacao_nf_po_service.py`
     - `app/recebimento/services/validacao_fiscal_service.py`
   - **Validação**: Sintaxe OK via `py_compile`

2. **Próximo passo**: ~~Implementar Fase 2 (cod_produto: product_id → default_code)~~ → **CONCLUÍDO**

### Notas da Implementação v1.4.0 (26/01/2026):

1. **Fase 2 (cod_produto)**: ✅ **IMPLEMENTADO**
   - Método `_criar_registro_primeira_compra()` agora aceita `cod_produto` e `nome_produto_interno` como parâmetros opcionais
   - Se `cod_produto` não for passado, mantém fallback para comportamento legado (`product_id`)
   - Ambas as chamadas em `_processar_sem_perfil()` atualizadas para passar os novos parâmetros
   - **Arquivos modificados**:
     - `app/recebimento/services/validacao_fiscal_service.py` (linhas 449-457, 496-504, 853-881)
   - **Validação**: Sintaxe OK via `py_compile`

### Notas da Implementação v1.5.0 (26/01/2026):

1. **Fase 3 (Propagação de validação)**: ✅ **IMPLEMENTADO**
   - Lógica de propagação adicionada ao método `validar_primeira_compra()`
   - Após criar perfil e validar o cadastro original, busca outros cadastros pendentes com mesma combinação
   - Combinação: `cnpj_empresa_compradora` + `cnpj_fornecedor` + `cod_produto`
   - Registros propagados são marcados com `validado_por = 'PROPAGADO_DE_{id_original}'`
   - Retorno do método agora inclui `propagados` (contagem) e `ids_propagados` (lista)
   - **Arquivos modificados**:
     - `app/recebimento/services/validacao_fiscal_service.py` (linhas 1437-1479)
   - **Validação**: Sintaxe OK via `py_compile`

2. **Próximo passo**: ~~Implementar Fase 4 (Revalidação ao criar perfil)~~ → **CONCLUÍDO**

### Notas da Implementação v1.6.0 (26/01/2026):

1. **Fase 4 (Revalidação ao criar perfil)**: ✅ **IMPLEMENTADO**
   - Criado método `revalidar_primeiras_compras_por_perfil()` em `validacao_fiscal_service.py` (linhas 1481-1527)
   - O método é chamado para cada perfil processado na importação Excel
   - Endpoint `POST /api/recebimento/perfil-fiscal/importar-excel` agora:
     - Coleta perfis criados/atualizados durante o processamento
     - Após commit, chama revalidação para cada perfil
     - Retorna `revalidacoes` (count) e `ids_revalidados` (lista)
   - **Arquivos modificados**:
     - `app/recebimento/services/validacao_fiscal_service.py`
     - `app/recebimento/routes/validacao_fiscal_routes.py`
   - **Validação**: Sintaxe OK via `py_compile`

2. **Próximo passo**: ~~Implementar Fase 5 (Busca CNPJ)~~ → **CONCLUÍDO**

### Notas da Implementação v1.7.0 (26/01/2026):

1. **Fase 5 (Busca CNPJ)**: ✅ **IMPLEMENTADO**
   - Verificado endpoint `GET /validacoes-nf-po`: JÁ normaliza via `service._limpar_cnpj()` (linha 2073)
   - Verificado endpoint `GET /primeira-compra`: NÃO TEM filtro por CNPJ (apenas status)
   - Verificado endpoint `GET /buscar-pos-fornecedor`: JÁ normaliza (linha 1235)
   - Corrigido endpoint `GET /perfis-fiscais`: Adicionada normalização via `normalizar_cnpj()` (linha 288)
   - **Arquivos modificados**:
     - `app/recebimento/routes/validacao_fiscal_routes.py` (linha 288)
   - **Validação**: Sintaxe OK via `py_compile`

2. **Próximo passo**: ~~Implementar Fase 7 (Scripts de migração)~~ → **CONCLUÍDO**

### Notas da Implementação v1.8.0 (26/01/2026):

1. **Fase 7 (Scripts de Migração)**: ✅ **IMPLEMENTADO**
   - Criado diretório `scripts/recebimento/`
   - **Script 001**: `001_corrigir_razao_empresa_validacao_nf_po.py`
     - Corrige `razao_empresa_compradora` em `validacao_nf_po_dfe`
     - Usa mapeamento `EMPRESAS_CNPJ_NOME` de `cnpj_utils.py`
     - Suporta `--dry-run` para simulação
   - **Script 001 SQL**: `001_corrigir_razao_empresa_validacao_nf_po.sql`
     - UPDATE direto para uso no Render Shell
     - Inclui diagnóstico, preview, verificação e rollback
   - **Script 002**: `002_corrigir_primeira_compra.py`
     - Busca `cnpj_empresa_compradora` do DFE no Odoo em batch
     - Preenche `razao_empresa_compradora` via mapeamento
     - Converte `cod_produto` de product_id para default_code via Odoo
     - Suporta `--dry-run`, `--skip-produto`, `--only-produto`
   - **Script 002 SQL**: `002_corrigir_primeira_compra.sql`
     - Correção parcial (apenas razão se CNPJ já preenchido)
     - Nota que correção COMPLETA requer script Python
   - **Arquivos criados**:
     - `scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.py`
     - `scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.sql`
     - `scripts/recebimento/002_corrigir_primeira_compra.py`
     - `scripts/recebimento/002_corrigir_primeira_compra.sql`
   - **Validação**: Sintaxe OK via `py_compile`

2. **IMPLEMENTAÇÃO COMPLETA** - Todas as 7 fases concluídas

### Notas da Verificação v1.2.0:

1. **Fase 6 (Finalizado Odoo)**: Confirmado que a deleção de matches/divergências é **COMPORTAMENTO INTENCIONAL** (linhas 179-185 de `validacao_nf_po_service.py`). Quando DFE já tem PO vinculado no Odoo, os matches locais são limpos porque a validação não é mais necessária. **NÃO é bug, é design.**

2. **Todas as outras fases**: Bugs confirmados via grep/read. Plano detalhado pronto para execução.

---

## ✅ VERIFICAÇÃO FINAL DA IMPLEMENTAÇÃO (v1.9.0 - 26/01/2026)

### Verificação de Sintaxe
| Arquivo | Status |
|---------|--------|
| `app/recebimento/services/validacao_fiscal_service.py` | ✅ OK via `py_compile` |
| `app/recebimento/services/validacao_nf_po_service.py` | ✅ OK via `py_compile` |
| `app/recebimento/routes/validacao_fiscal_routes.py` | ✅ OK via `py_compile` |
| `scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.py` | ✅ OK via `py_compile` |
| `scripts/recebimento/002_corrigir_primeira_compra.py` | ✅ OK via `py_compile` |

### Verificação de Imports
| Verificação | Status |
|-------------|--------|
| Flask app cria contexto | ✅ OK |
| `ValidacaoFiscalService` importa | ✅ OK |
| `ValidacaoNfPoService` importa | ✅ OK |
| Método `revalidar_primeiras_compras_por_perfil` existe | ✅ OK |
| `obter_nome_empresa` importado em `validacao_nf_po_service` | ✅ OK |

### Verificação de Correções de Campo
| Correção | Verificação | Status |
|----------|-------------|--------|
| `nfe_infnfe_dest_xnome` removido (5 ocorrências) | grep retorna apenas comentários | ✅ OK |
| `obter_nome_empresa()` usado em vez de campo inexistente | Linhas 1135, 1168, 1221, 1307, 1453 | ✅ OK |
| `dados_nf['razao_empresa_compradora']` atualizado | Linha 260 | ✅ OK |
| `cod_produto` recebe parâmetro ao invés de recalcular | Linhas 455, 502, 877-878 | ✅ OK |

### Scripts de Migração
| Script | Teste | Status |
|--------|-------|--------|
| `001_corrigir_razao_empresa_validacao_nf_po.py` | `--help` funciona | ✅ OK |
| `002_corrigir_primeira_compra.py` | `--help` funciona | ✅ OK |

### Status Final
- **Todas as 7 fases implementadas e verificadas**
- **Código compila e importa sem erros**
- **Scripts de migração prontos para execução**
- **Próximo passo**: Executar scripts de migração em produção para corrigir dados existentes

---

## 📋 PRÓXIMOS PASSOS PARA DEPLOY

1. **Fazer deploy do código** (via git push/Render)
2. **Executar script 001** no Render Shell:
   ```bash
   python scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.py --dry-run
   python scripts/recebimento/001_corrigir_razao_empresa_validacao_nf_po.py
   ```
3. **Executar script 002** no Render Shell:
   ```bash
   python scripts/recebimento/002_corrigir_primeira_compra.py --dry-run
   python scripts/recebimento/002_corrigir_primeira_compra.py
   ```
4. **Testar manualmente**:
   - Acessar tela de Primeira Compra e verificar campo EMPRESA
   - Acessar tela de Validações NF x PO e verificar CNPJ/Razão
   - Testar busca por CNPJ (formatado e sem formatação)
   - Validar uma combinação e verificar propagação para outras NFs
