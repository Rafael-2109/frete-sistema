# Correções no Módulo de Recebimento - CNPJ, Empresa e Produto

## Objetivo

Corrigir problemas de preenchimento e propagação de dados nas telas de **Validação de Primeira Compra** e **Validações NF x PO**, que estão causando:
- Campos EMPRESA exibindo "N/A" ou "-"
- Falhas na propagação de validações entre NFs com mesma combinação
- Falhas na revalidação automática ao criar perfis fiscais
- Buscas por CNPJ não encontrando registros
- Produtos exibindo product_id do Odoo ao invés do código interno

---

## ⚠️ EVIDÊNCIAS DE PRODUÇÃO (Verificadas em 26/01/2026)

### REQ-1: Campo EMPRESA na Primeira Compra - **100% AFETADOS**

```sql
-- Resultado da consulta em produção:
SELECT COUNT(*) as total,
       COUNT(CASE WHEN cnpj_empresa_compradora = '' OR cnpj_empresa_compradora IS NULL THEN 1 END) as sem_cnpj,
       COUNT(CASE WHEN razao_empresa_compradora = '' OR razao_empresa_compradora IS NULL THEN 1 END) as sem_razao
FROM cadastro_primeira_compra;

-- Resultado:
-- total: 345
-- sem_cnpj: 345 (100%)
-- sem_razao: 345 (100%)
```

**CRÍTICO**: Todos os 345 registros de `cadastro_primeira_compra` estão com `cnpj_empresa_compradora` e `razao_empresa_compradora` VAZIOS.

### REQ-5: CNPJ/EMPRESA em Validações NF x PO - **100% SEM RAZÃO**

```sql
-- Resultado da consulta em produção:
SELECT COUNT(*) as total,
       COUNT(CASE WHEN cnpj_empresa_compradora = '' OR cnpj_empresa_compradora IS NULL THEN 1 END) as sem_cnpj,
       COUNT(CASE WHEN razao_empresa_compradora IS NULL THEN 1 END) as sem_razao
FROM validacao_nf_po_dfe;

-- Resultado:
-- total: 181
-- sem_cnpj: 14 (7.7%)
-- sem_razao: 181 (100%)
```

**CRÍTICO**: Todos os 181 registros de `validacao_nf_po_dfe` estão sem `razao_empresa_compradora`.

### REQ-6: Registros "Finalizado Odoo" sem produtos - **100% SEM ITENS**

```sql
-- Resultado da consulta em produção:
SELECT COUNT(*) as total,
       COUNT(CASE WHEN total_itens = 0 OR total_itens IS NULL THEN 1 END) as sem_itens
FROM validacao_nf_po_dfe
WHERE status = 'finalizado_odoo';

-- Resultado:
-- total: 114
-- sem_itens: 114 (100%)

-- match_nf_po_item para status finalizado_odoo:
-- ZERO registros encontrados
```

**CRÍTICO**: Todos os 114 registros "Finalizado Odoo" têm `total_itens = 0` e nenhum registro em `match_nf_po_item`.

### REQ-7: cod_produto é product_id do Odoo - **CONFIRMADO**

```sql
-- Amostra de cod_produto em produção:
-- Range: 27656 a 36957 (todos numéricos de 5 dígitos)
-- Exemplo NF 430279:
--   cod_produto = "28119"
--   nome_produto = "CXS. P. O. COD. 201030011 06 X 02 KG. CAMPO BELO"
--   (Note: nome menciona "COD. 201030011" mas cod_produto é "28119")
```

**CONFIRMADO**: `cod_produto` contém o `product.id` do Odoo (numérico) ao invés do `default_code` (alfanumérico).

### NF 430279 - Caso de Estudo

| Tabela | Campo | Valor | Status |
|--------|-------|-------|--------|
| `cadastro_primeira_compra` | `cnpj_empresa_compradora` | `""` (vazio) | ❌ ERRO |
| `cadastro_primeira_compra` | `razao_empresa_compradora` | `""` (vazio) | ❌ ERRO |
| `cadastro_primeira_compra` | `cod_produto` | `28119` (numérico) | ⚠️ É product_id |
| `cadastro_primeira_compra` | `status` | `validado` | ✅ OK |
| `validacao_nf_po_dfe` | `cnpj_empresa_compradora` | `61724241000178` | ✅ OK |
| `validacao_nf_po_dfe` | `razao_empresa_compradora` | `null` | ❌ ERRO |
| `validacao_nf_po_dfe` | `total_itens` | `0` | ❌ ERRO |
| `validacao_nf_po_dfe` | `status` | `finalizado_odoo` | ✅ OK |
| `match_nf_po_item` | (registros) | **Nenhum** | ❌ ERRO |
| `recebimento_fisico` | (registros) | **Não existe** | N/A |

### Resumo de Severidade

| Alegação | Confirmada | % Afetados | Severidade |
|----------|------------|------------|------------|
| 1. EMPRESA vazio na 1ª compra | ✅ SIM | **100%** | 🔴 CRÍTICA |
| 2. Propagação não funciona | ✅ SIM | N/A | 🟠 ALTA |
| 3. Revalidação ao criar perfil | ✅ SIM | N/A | 🟠 ALTA |
| 4. Busca CNPJ não encontra | ⚠️ PARCIAL | N/A | 🟡 MÉDIA |
| 5. razao_empresa vazio em NF x PO | ✅ SIM | **100%** | 🔴 CRÍTICA |
| 6. "Finalizado Odoo" sem itens | ✅ SIM | **100%** | 🔴 CRÍTICA |
| 7. cod_produto é product_id | ✅ SIM | **100%** | 🟠 ALTA |

---

## Requisitos

### REQ-1: Corrigir campo EMPRESA na tela de Primeira Compra
**Problema**: Campo EMPRESA mostrando "N/A" e "-"
**Causa provável**: `cnpj_empresa_compradora` não está sendo normalizado ou `razao_empresa_compradora` não está sendo preenchido na criação do `CadastroPrimeiraCompra`
**Solução**:
1. Verificar service `ValidacaoFiscalService` onde cria `CadastroPrimeiraCompra`
2. Garantir extração de `nfe_infnfe_dest_cnpj` e `nfe_infnfe_dest_xnome` do DFE
3. Usar `obter_nome_empresa(cnpj)` de `cnpj_utils.py` como fallback
4. Atualizar registros existentes via script de migração

### REQ-2: Propagação de validação para outras NFs com mesma combinação
**Problema**: Validar (CNPJ + PRODUTO + EMPRESA) não propaga para outras NFs pendentes
**Causa provável**: Lógica de propagação ausente ou condicional não executando
**Solução**:
1. No endpoint `POST /api/recebimento/primeira-compra/<id>/validar`
2. Após criar `PerfilFiscalProdutoFornecedor`, buscar outros `CadastroPrimeiraCompra` pendentes com mesma combinação
3. Marcar como validados automaticamente

### REQ-3: Revalidação automática ao criar perfil fiscal
**Problema**: Criar perfil fiscal manualmente não revalida primeiras compras pendentes
**Causa provável**: Campos CNPJ e EMPRESA em branco impedem o match
**Solução**:
1. Corrigir REQ-1 primeiro (garantir CNPJ e EMPRESA preenchidos)
2. No `PerfilFiscalProdutoFornecedor.after_insert` ou endpoint de criação
3. Buscar `CadastroPrimeiraCompra` pendentes que façam match
4. Validar automaticamente os que tiverem perfil correspondente

### REQ-4: Busca por CNPJ na tela de Validações NF x PO
**Problema**: Busca por CNPJ não encontra registros
**Causa provável**: Formato inconsistente (com/sem pontuação, zeros à esquerda)
**Solução**:
1. Na API de listagem, normalizar CNPJ de entrada
2. Usar `cnpjs_iguais()` de `cnpj_utils.py` para comparação
3. Garantir que dados salvos estejam normalizados (14 dígitos)

### REQ-5: Preencher CNPJ e nome da EMPRESA na tela de Validações NF x PO
**Problema**: Registros sem CNPJ da empresa e todos sem nome da empresa
**Causa provável**: Campos não estão sendo preenchidos na criação de `ValidacaoNfPoDfe`
**Solução**:
1. Verificar `ValidacaoNfPoService` onde cria `ValidacaoNfPoDfe`
2. Extrair `nfe_infnfe_dest_cnpj` e `nfe_infnfe_dest_xnome` do DFE
3. Preencher `cnpj_empresa_compradora` e `razao_empresa_compradora`
4. Script de correção para registros existentes

### REQ-6: Registros "Finalizado Odoo" sem produtos
**Problema**: Status "Finalizado Odoo" mostra 0 produtos, modal exibe "Itens: N/A"
**Causa provável**: Itens não estão sendo associados ao registro de validação ou foram deletados
**Solução**:
1. Investigar fluxo de finalização no Odoo
2. Verificar se `MatchNfPoItem` está sendo criado/preservado
3. Verificar query do modal de visualização
4. Se dados perdidos: criar rotina de recarga dos itens do DFE

### REQ-7: Exibir código do produto ao invés de product_id do Odoo
**Problema**: Tela de primeira compra mostra product_id (ex: 12345) ao invés de cod_produto (ex: 'PAL001')
**Causa provável**: Sincronização está salvando `product_id` no campo `cod_produto`
**Solução**:
1. Verificar `ValidacaoFiscalService` como obtém código do produto
2. Usar `default_code` do Odoo (produto.default_code) ao invés de `id`
3. Script de migração para converter product_id → cod_produto nos registros existentes

## Critérios de Aceite

### Tela de Primeira Compra
- [ ] Campo EMPRESA exibe nome correto (NACOM GOYA - CD, LA FAMIGLIA, etc.)
- [ ] Nunca exibe "N/A" ou "-" quando DFE tem dados válidos
- [ ] Ao validar uma combinação, outras NFs pendentes com mesma combinação são validadas automaticamente
- [ ] Produto exibe código alfanumérico (ex: 'PAL001'), não ID numérico

### Tela de Validações NF x PO
- [ ] Busca por CNPJ funciona com qualquer formato (XX.XXX.XXX/XXXX-XX ou 14 dígitos)
- [ ] Todos os registros exibem CNPJ e nome da empresa
- [ ] Registros "Finalizado Odoo" mostram quantidade de produtos > 0
- [ ] Modal de visualização mostra itens corretamente

### Perfil Fiscal
- [ ] Ao criar perfil fiscal, primeiras compras pendentes com match são validadas automaticamente

### Scripts de Migração
- [ ] Script Python para ambiente local (usando Flask app context)
- [ ] Script SQL para produção (Render Shell)
- [ ] Rollback documentado em caso de erro

## Notas Técnicas

### Arquivos Relacionados

**Models**:
- `app/recebimento/models.py` - CadastroPrimeiraCompra, ValidacaoNfPoDfe, PerfilFiscalProdutoFornecedor, MatchNfPoItem

**Services**:
- `app/recebimento/services/validacao_fiscal_service.py` - Criação de primeira compra e perfil
- `app/recebimento/services/validacao_nf_po_service.py` - Criação de ValidacaoNfPoDfe e MatchNfPoItem

**Routes**:
- `app/recebimento/routes/validacao_fiscal_routes.py` - Endpoints de primeira compra e perfil fiscal
- `app/recebimento/routes/validacao_nf_po_routes.py` - Endpoints de validação NF x PO

**Templates**:
- `app/templates/recebimento/primeira_compra.html` - Tela de primeira compra
- `app/templates/recebimento/validacoes_nf_po.html` - Tela de validações NF x PO

**Utils**:
- `app/utils/cnpj_utils.py` - normalizar_cnpj, cnpjs_iguais, obter_nome_empresa, EMPRESAS_CNPJ_NOME

### Padrões a Seguir
- Consultar CLAUDE.md para nomes de campos
- Usar `normalizar_cnpj()` em toda manipulação de CNPJ
- Usar `obter_nome_empresa()` como fonte de verdade para nomes de empresas
- Formato brasileiro para números (filtro numero_br)
- Scripts de migração: Python local + SQL para Render

### Mapeamento de Empresas (cnpj_utils.py)
```python
EMPRESAS_CNPJ_NOME = {
    '61724241000330': 'NACOM GOYA - CD',
    '61724241000178': 'NACOM GOYA - FB',
    '61724241000259': 'NACOM GOYA - SC',
    '18467441000163': 'LA FAMIGLIA - LF',
}
```

### Campos Críticos nos Models

**CadastroPrimeiraCompra**:
- `cnpj_empresa_compradora` - CNPJ normalizado (14 dígitos)
- `razao_empresa_compradora` - Razão social extraída do DFE
- `cod_produto` - Deve ser código alfanumérico, NÃO product_id

**ValidacaoNfPoDfe**:
- `cnpj_empresa_compradora` - CNPJ normalizado (14 dígitos)
- `razao_empresa_compradora` - Razão social da empresa

**PerfilFiscalProdutoFornecedor**:
- `cnpj_empresa_compradora` - Chave composta (empresa + fornecedor + produto)
- `cod_produto` - Código interno do produto

## Ordem de Implementação Sugerida

1. **REQ-1 + REQ-5**: Corrigir preenchimento de CNPJ/EMPRESA (raiz do problema)
2. **REQ-4**: Normalizar busca por CNPJ
3. **REQ-7**: Corrigir exibição de produto (product_id → cod_produto via default_code)
4. **REQ-2**: Implementar propagação de validação entre NFs
5. **REQ-3**: Implementar revalidação ao criar perfil fiscal
6. **REQ-6**: Investigar e corrigir registros "Finalizado Odoo" sem itens
7. **Scripts de migração**: Executar após cada correção de service

## Investigação Necessária (Ralph Loop deve fazer)

Antes de implementar, o Ralph Loop deve:

1. **Ler `ValidacaoFiscalService`** para entender como `CadastroPrimeiraCompra` é criado
2. **Ler `ValidacaoNfPoService`** para entender como `ValidacaoNfPoDfe` é criado
3. **Verificar origem do `cod_produto`** - se vem de `product_id` ou `default_code` do Odoo
4. **Verificar fluxo de "Finalizado Odoo"** - quando e como itens são criados/deletados
5. **Verificar se há listener/hook** na criação de perfil fiscal

## Scripts de Migração

### Quantidades a Corrigir (Produção 26/01/2026)

| Tabela | Registros | Correção |
|--------|-----------|----------|
| `cadastro_primeira_compra` | 345 | Preencher `cnpj_empresa_compradora` e `razao_empresa_compradora` |
| `validacao_nf_po_dfe` | 181 | Preencher `razao_empresa_compradora` |
| `cadastro_primeira_compra` | 345 | Converter `cod_produto` de product_id para default_code |

### SQL (Render Shell)
```sql
-- CORREÇÃO 1: razao_empresa_compradora em validacao_nf_po_dfe
UPDATE validacao_nf_po_dfe
SET razao_empresa_compradora = CASE cnpj_empresa_compradora
    WHEN '61724241000330' THEN 'NACOM GOYA - CD'
    WHEN '61724241000178' THEN 'NACOM GOYA - FB'
    WHEN '61724241000259' THEN 'NACOM GOYA - SC'
    WHEN '18467441000163' THEN 'LA FAMIGLIA - LF'
END
WHERE razao_empresa_compradora IS NULL
  AND cnpj_empresa_compradora IN ('61724241000330','61724241000178','61724241000259','18467441000163');

-- CORREÇÃO 2: cnpj/razao em cadastro_primeira_compra
-- REQUER: Investigar ValidacaoFiscalService para saber origem dos dados

-- CORREÇÃO 3: cod_produto (product_id → default_code)
-- REQUER: Mapeamento do Odoo (product.id → product.default_code)
```

**OBRIGATÓRIO** VERIFICAR CAMPOS, DADOS, ODOO, TABELAS ANTES DE EXECUTAR **OBRIGATÓRIO**
**BOAS PRÁTICAS** HÁ UMA ENORMIDADE DE RECURSOS DISPONIVEIS, AGENTES, SKILLS, DOCUMENTAÇÃO ETC, USE-A **BOAS PRÁTICAS**
**BOAS PRÁTICAS** SE ALGO NÃO ESTÁ DOCUMENTADO E TE GEROU DÚVIDA, A SUA MELHOR OPÇÃO DE AÇÃO É PESQUISAR, EVIDENCIAR E DOCUMENTAR **BOAS PRÁTICAS**
**BOAS PRÁTICAS** NÃO ECONOMIZE TOKEN PULANDO UMA VERIFICAÇÃO DE CAMPO **BOAS PRÁTICAS**
**BOAS PRÁTICAS** NÃO QUEIRA RESOLVER TUDO EM 1 SESSÃO **BOAS PRÁTICAS**
**BOAS PRÁTICAS** SE TIVER DUVIDA OPTE POR "GASTAR" A SESSÃO PESQUISANDO E DOCUMENTANDO E ENCERRE A SESSÃO.**BOAS PRÁTICAS**
**BOAS PRÁTICAS** ISSO IRÁ AJUDAR O AGENTE DA SESSÃO SEGUINTE, PORTANTO AJUDE O PRÓXIMO **BOAS PRÁTICAS**

