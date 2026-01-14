# Recebimento de Materiais - Documentacao de Referencia

**Versao**: 1.0
**Status**: FASE 1 - Validacao Fiscal
**Atualizado**: 13/01/2025

---

## Visao Geral

Sistema de validacao e recebimento de materiais integrado com Odoo.

### Fases de Implementacao

| Fase | Descricao | Status |
|------|-----------|--------|
| **1** | Validacao Fiscal | ✅ IMPLEMENTADO |
| 2 | Vinculacao NF-PO | Pendente |
| 3 | Tratamento de Parciais | Pendente |
| 4 | Recebimento Fisico (Lotes + Qualidade) | Pendente |
| 5 | Criacao Fatura Automatica | Pendente |

---

## FASE 1: Validacao Fiscal

### Objetivo

Validar campos fiscais de NFs de compra comparando com baseline historico.
**BLOQUEIA** recebimento ate resolucao de divergencias.

### Campos Validados

| Campo | Tipo | Tolerancia |
|-------|------|------------|
| NCM | Exato | 0% |
| CFOP | Lista | 0% (pode ter multiplos) |
| CST ICMS | Exato | 0% |
| % ICMS | Exato | 0% |
| % ICMS ST | Exato | 0% |
| % IPI | Exato | 0% |
| BC ICMS | Percentual | 2% (configuravel) |
| BC ICMS ST | Percentual | 2% (configuravel) |
| Tributos Aprox | Percentual | 5% (configuravel) |

### Fluxo de Validacao

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCHEDULER (30 min)                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│         Buscar DFEs de Compra Nao Validados                     │
│         (l10n_br_tipo_pedido = 'compra', state = 'done')        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                  ┌─────────────────┐
                  │ Para cada Linha │
                  └────────┬────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │   Tem Perfil Fiscal Local? │
              └────────────┬───────────────┘
                           │
            ┌──────────────┴──────────────┐
            │ NAO                         │ SIM
            ▼                             ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│ Buscar Historico Odoo   │   │ Comparar com Baseline   │
│ (3 ultimas NFs)         │   │                         │
└───────────┬─────────────┘   └───────────┬─────────────┘
            │                             │
            ▼                             │
┌─────────────────────────┐               │
│ Historico Consistente?  │               │
└───────────┬─────────────┘               │
            │                             │
     ┌──────┴──────┐                      │
     │SIM          │NAO                   │
     ▼             ▼                      ▼
┌──────────┐  ┌──────────┐   ┌─────────────────────────┐
│ Criar    │  │ 1a Compra│   │ Divergencia Detectada?  │
│ Perfil   │  │ (manual) │   └───────────┬─────────────┘
│ Auto     │  └──────────┘               │
└──────────┘                      ┌──────┴──────┐
                                  │SIM          │NAO
                                  ▼             ▼
                           ┌──────────┐   ┌──────────┐
                           │BLOQUEADO │   │APROVADO  │
                           └──────────┘   └──────────┘
```

### Status dos DFEs

| Status | Descricao | Acao |
|--------|-----------|------|
| `pendente` | Aguardando validacao | Processar |
| `validando` | Em processamento | Aguardar |
| `aprovado` | Todas linhas OK | Prosseguir fluxo |
| `bloqueado` | Tem divergencia pendente | Resolver divergencias |
| `primeira_compra` | Sem perfil, aguardando fiscal | Validar 1a compra |
| `erro` | Falha no processamento | Investigar/Reprocessar |

---

## Tabelas do Banco

### perfil_fiscal_produto_fornecedor

**Proposito**: Armazena baseline fiscal por produto/fornecedor.

```sql
CREATE TABLE perfil_fiscal_produto_fornecedor (
    id SERIAL PRIMARY KEY,
    cod_produto VARCHAR(50) NOT NULL,
    cnpj_fornecedor VARCHAR(20) NOT NULL,
    ncm_esperado VARCHAR(10),
    cfop_esperados TEXT,                    -- JSON: ["5101", "6101"]
    cst_icms_esperado VARCHAR(5),
    aliquota_icms_esperada NUMERIC(5,2),
    aliquota_icms_st_esperada NUMERIC(5,2),
    aliquota_ipi_esperada NUMERIC(5,2),
    tolerancia_bc_icms_pct NUMERIC(5,2) DEFAULT 2.0,
    tolerancia_bc_icms_st_pct NUMERIC(5,2) DEFAULT 2.0,
    tolerancia_tributos_pct NUMERIC(5,2) DEFAULT 5.0,
    ultimas_nfs_ids TEXT,                   -- JSON: [dfe_id1, dfe_id2, dfe_id3]
    criado_por VARCHAR(100),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE,
    UNIQUE(cod_produto, cnpj_fornecedor)
);
```

### divergencia_fiscal

**Proposito**: Registra divergencias que bloqueiam recebimento.

```sql
CREATE TABLE divergencia_fiscal (
    id SERIAL PRIMARY KEY,
    odoo_dfe_id VARCHAR(50) NOT NULL,
    odoo_dfe_line_id VARCHAR(50),
    perfil_fiscal_id INTEGER REFERENCES perfil_fiscal_produto_fornecedor(id),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    cnpj_fornecedor VARCHAR(20) NOT NULL,
    razao_fornecedor VARCHAR(255),
    campo VARCHAR(50) NOT NULL,             -- ncm, cfop, aliq_icms, etc
    campo_label VARCHAR(100),               -- "NCM", "% ICMS", etc
    valor_esperado VARCHAR(100),
    valor_encontrado VARCHAR(100),
    diferenca_percentual NUMERIC(10,2),
    analise_ia TEXT,
    contexto_ia TEXT,
    status VARCHAR(20) DEFAULT 'pendente',  -- pendente, aprovada, rejeitada
    resolucao VARCHAR(50),                  -- aprovar_manter, aprovar_atualizar, rejeitar
    atualizar_baseline BOOLEAN DEFAULT FALSE,
    justificativa TEXT,
    resolvido_por VARCHAR(100),
    resolvido_em TIMESTAMP,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### cadastro_primeira_compra

**Proposito**: Registra itens sem historico para validacao manual.

```sql
CREATE TABLE cadastro_primeira_compra (
    id SERIAL PRIMARY KEY,
    odoo_dfe_id VARCHAR(50) NOT NULL,
    odoo_dfe_line_id VARCHAR(50),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    cnpj_fornecedor VARCHAR(20) NOT NULL,
    razao_fornecedor VARCHAR(255),
    ncm VARCHAR(10),
    cfop VARCHAR(10),
    cst_icms VARCHAR(5),
    aliquota_icms NUMERIC(5,2),
    aliquota_icms_st NUMERIC(5,2),
    aliquota_ipi NUMERIC(5,2),
    bc_icms NUMERIC(15,2),
    bc_icms_st NUMERIC(15,2),
    valor_tributos_aprox NUMERIC(15,2),
    info_complementar TEXT,
    status VARCHAR(20) DEFAULT 'pendente',  -- pendente, validado, rejeitado
    validado_por VARCHAR(100),
    validado_em TIMESTAMP,
    observacao TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### validacao_fiscal_dfe

**Proposito**: Controle de validacao por DFE (scheduler).

```sql
CREATE TABLE validacao_fiscal_dfe (
    id SERIAL PRIMARY KEY,
    odoo_dfe_id INTEGER NOT NULL UNIQUE,
    numero_nf VARCHAR(20),
    chave_nfe VARCHAR(44),
    cnpj_fornecedor VARCHAR(20),
    razao_fornecedor VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pendente',
    total_linhas INTEGER DEFAULT 0,
    linhas_aprovadas INTEGER DEFAULT 0,
    linhas_divergentes INTEGER DEFAULT 0,
    linhas_primeira_compra INTEGER DEFAULT 0,
    erro_mensagem TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validado_em TIMESTAMP,
    atualizado_em TIMESTAMP
);
```

---

## Campos Odoo Utilizados

### DFE (l10n_br_ciel_it_account.dfe)

| Campo | Descricao |
|-------|-----------|
| `id` | ID do DFE |
| `name` | Nome/referencia |
| `l10n_br_tipo_pedido` | Tipo: 'compra', 'devolucao_compra', etc |
| `state` | Estado: 'done' = processado |
| `nfe_infnfe_emit_cnpj` | CNPJ do fornecedor |
| `nfe_infnfe_emit_xnome` | Razao social do fornecedor |
| `nfe_infnfe_ide_nnf` | Numero da NF |
| `protnfe_infnfe_chnfe` | Chave NF-e (44 digitos) |
| `nfe_infnfe_ide_dhemi` | Data de emissao |
| `write_date` | Data de modificacao |

### DFE Line (l10n_br_ciel_it_account.dfe.line)

| Campo | Descricao |
|-------|-----------|
| `id` | ID da linha |
| `dfe_id` | ID do DFE pai |
| `product_id` | ID do produto |
| `det_prod_xprod` | Nome do produto |
| `det_prod_ncm` | NCM |
| `det_prod_cfop` | CFOP |
| `det_imposto_icms_cst` | CST ICMS |
| `det_imposto_icms_picms` | % ICMS |
| `det_imposto_icms_picmsst` | % ICMS ST |
| `det_imposto_icms_vbc` | Base ICMS |
| `det_imposto_icms_vbcst` | Base ICMS ST |
| `det_imposto_ipi_pipi` | % IPI |
| `det_imposto_vtottrib` | Valor tributos aproximados |

---

## Arquivos do Modulo

### Models
- `app/recebimento/models.py` - 4 models (SQLAlchemy)

### Services
- `app/recebimento/services/validacao_fiscal_service.py` - Logica de validacao

### Jobs
- `app/recebimento/jobs/validacao_fiscal_job.py` - Job do scheduler

### Routes
- `app/recebimento/routes/validacao_fiscal_routes.py` - API endpoints

### Migrations
- `scripts/migrations/criar_tabelas_validacao_fiscal.py` - Script Python
- `scripts/migrations/sql/validacao_fiscal.sql` - Script SQL

---

## API Endpoints

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/recebimento/validar-nf/<dfe_id>` | GET | Valida uma NF especifica |
| `/api/recebimento/divergencias` | GET | Lista divergencias pendentes |
| `/api/recebimento/divergencias/<id>/aprovar` | POST | Aprova divergencia |
| `/api/recebimento/divergencias/<id>/rejeitar` | POST | Rejeita divergencia |
| `/api/recebimento/primeira-compra` | GET | Lista 1as compras pendentes |
| `/api/recebimento/primeira-compra/<id>/validar` | POST | Valida 1a compra |
| `/api/recebimento/primeira-compra/<id>/rejeitar` | POST | Rejeita 1a compra |
| `/api/recebimento/perfis-fiscais` | GET | Lista perfis fiscais |

---

## Configuracao do Scheduler

Variavel de ambiente: `JANELA_VALIDACAO_FISCAL`
Valor padrao: 120 minutos

Integrado ao scheduler existente (`app/scheduler/sincronizacao_incremental_definitiva.py`).

---

## Proximas Fases

### Fase 2: Vinculacao NF-PO
- Vincular NF de compra com Pedido de Compra
- Validar quantidades e valores

### Fase 3: Tratamento de Parciais
- Recebimento parcial de NFs
- Controle de saldo

### Fase 4: Recebimento Fisico
- Gestao de lotes
- Controle de qualidade
- Inspecao de materiais

### Fase 5: Criacao Fatura Automatica
- Gerar fatura no Odoo
- Integracao contabil
