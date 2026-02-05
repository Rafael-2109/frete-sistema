# Tabelas do Domínio Entregas

## Diagrama de Relacionamentos

```
entregas_monitoradas (tabela principal)
├── agendamentos_entrega (1:N)
│   └── entrega_id → entregas_monitoradas.id
├── nf_devolucao (1:N)
│   ├── entrega_monitorada_id → entregas_monitoradas.id
│   ├── nf_devolucao_linha (1:N)
│   │   └── nf_devolucao_id → nf_devolucao.id
│   └── ocorrencia_devolucao (1:1)
│       └── nf_devolucao_id → nf_devolucao.id
└── substituida_por_nf_id → entregas_monitoradas.id (auto-referência)
```

---

## entregas_monitoradas

**Descrição:** Tabela principal de monitoramento de entregas. Cada registro representa uma NF em processo de entrega.

**Campos Principais:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | integer | PK |
| `numero_nf` | varchar(20) | Número da NF (NOT NULL) |
| `cliente` | varchar(255) | Nome do cliente (NOT NULL) |
| `cnpj_cliente` | varchar(20) | CNPJ do cliente |
| `transportadora` | varchar(255) | Nome da transportadora |
| `municipio` | varchar(100) | Cidade de destino |
| `uf` | varchar(2) | UF de destino |
| `valor_nf` | float | Valor da NF |
| `data_faturamento` | date | Data do faturamento |
| `data_embarque` | date | Data do embarque |
| `data_entrega_prevista` | date | Previsão de entrega |
| `data_hora_entrega_realizada` | timestamp | Data/hora efetiva da entrega |
| `status_finalizacao` | varchar(50) | Status final (ver regras de negócio) |
| `entregue` | boolean | True se entregue |
| `nf_cd` | boolean | True se NF está no CD |
| `reagendar` | boolean | True se precisa reagendar |
| `motivo_reagendamento` | varchar(255) | Motivo do reagendamento |
| `data_agenda` | date | Data agendada |
| `canhoto_arquivo` | varchar(500) | Caminho do arquivo do canhoto |
| `teve_devolucao` | boolean | True se houve devolução |
| `nova_nf` | varchar(20) | Número da NF substituta |
| `substituida_por_nf_id` | integer | FK para NF substituta |
| `separacao_lote_id` | varchar(50) | ID do lote de separação |

**Índices:**
- `ix_entregas_monitoradas_numero_nf`
- `ix_entregas_monitoradas_cnpj_cliente`
- `ix_entregas_monitoradas_separacao_lote_id`

---

## agendamentos_entrega

**Descrição:** Histórico de agendamentos de cada entrega.

**Campos Principais:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | integer | PK |
| `entrega_id` | integer | FK → entregas_monitoradas.id |
| `data_agendada` | date | Data do agendamento |
| `hora_agendada` | time | Hora do agendamento |
| `forma_agendamento` | varchar(50) | Portal, Telefone, etc. |
| `contato_agendamento` | varchar(255) | Login, telefone, e-mail |
| `protocolo_agendamento` | varchar(100) | Número/código do protocolo |
| `status` | varchar(20) | aguardando, confirmado |
| `motivo` | varchar(255) | Motivo do agendamento |
| `confirmado_por` | varchar(100) | Quem confirmou |
| `confirmado_em` | timestamp | Quando foi confirmado |

---

## nf_devolucao

**Descrição:** NFs de devolução recebidas.

**Campos Principais:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | integer | PK |
| `entrega_monitorada_id` | integer | FK → entregas_monitoradas.id |
| `numero_nfd` | varchar(20) | Número da NFD (NOT NULL) |
| `numero_nf_venda` | varchar(20) | Número da NF original |
| `chave_nfd` | varchar(44) | Chave de acesso da NFD |
| `motivo` | varchar(50) | Motivo da devolução (NOT NULL) |
| `descricao_motivo` | text | Descrição detalhada |
| `confianca_motivo` | numeric(5,4) | Confiança da extração IA (0-1) |
| `valor_total` | numeric(15,2) | Valor total da NFD |
| `valor_produtos` | numeric(15,2) | Valor dos produtos |
| `data_emissao` | date | Data de emissão |
| `data_entrada` | date | Data de entrada |
| `cnpj_emitente` | varchar(20) | CNPJ do cliente |
| `nome_emitente` | varchar(255) | Nome do cliente |
| `status` | varchar(30) | Status da NFD (default: REGISTRADA) |
| `odoo_dfe_id` | integer | ID do DFe no Odoo |
| `odoo_nf_venda_id` | integer | ID da NF original (account.move) |
| `odoo_nota_credito_id` | integer | ID da nota de crédito |
| `sincronizado_odoo` | boolean | Se sincronizado com Odoo |
| `e_pallet_devolucao` | boolean | Se é devolução de pallet |

**Índices:**
- `ix_nf_devolucao_numero_nfd`
- `ix_nf_devolucao_chave_nfd` (unique)
- `ix_nf_devolucao_numero_nf_venda`
- `ix_nf_devolucao_cnpj_emitente`
- `ix_nf_devolucao_odoo_dfe_id` (unique)
- `ix_nf_devolucao_status`

---

## ocorrencia_devolucao

**Descrição:** Ocorrências/tratativas de devolução. Uma por NFD.

**Campos Principais:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | integer | PK |
| `nf_devolucao_id` | integer | FK → nf_devolucao.id (unique) |
| `numero_ocorrencia` | varchar(20) | Número da ocorrência (unique) |
| `status` | varchar(30) | Status (default: ABERTA) |
| `destino` | varchar(20) | Destino da mercadoria |
| `localizacao_atual` | varchar(20) | Onde está (default: CLIENTE) |
| `categoria` | varchar(30) | Categoria da ocorrência |
| `subcategoria` | varchar(50) | Subcategoria |
| `responsavel` | varchar(30) | Área responsável |
| `origem` | varchar(30) | Origem do problema |
| `momento_devolucao` | varchar(20) | Quando ocorreu |
| `transportadora_retorno_id` | integer | FK → transportadoras.id |
| `data_previsao_retorno` | date | Previsão de retorno ao CD |
| `data_chegada_cd` | timestamp | Quando chegou no CD |
| `data_abertura` | timestamp | Data de abertura |
| `data_resolucao` | timestamp | Data de resolução |
| `desfecho` | text | Como foi resolvido |

**Índices:**
- `ix_ocorrencia_devolucao_numero_ocorrencia` (unique)
- `ix_ocorrencia_devolucao_status`
- `idx_ocorrencia_status_destino`
- `idx_ocorrencia_categoria`
- `idx_ocorrencia_responsavel`

---

## Queries Comuns

### Entregas Pendentes
```sql
SELECT * FROM entregas_monitoradas
WHERE status_finalizacao IS NULL
ORDER BY data_embarque;
```

### Entregas com Problema
```sql
SELECT * FROM entregas_monitoradas
WHERE (nf_cd = true OR reagendar = true)
  AND status_finalizacao IS NULL;
```

### Entregas sem Canhoto
```sql
SELECT * FROM entregas_monitoradas
WHERE status_finalizacao = 'Entregue'
  AND canhoto_arquivo IS NULL;
```

### Devoluções Abertas
```sql
SELECT nfd.*, oc.*
FROM nf_devolucao nfd
JOIN ocorrencia_devolucao oc ON oc.nf_devolucao_id = nfd.id
WHERE oc.status = 'ABERTA'
  AND oc.ativo = true;
```

### Agendamentos Pendentes
```sql
SELECT ae.*, em.numero_nf, em.cliente
FROM agendamentos_entrega ae
JOIN entregas_monitoradas em ON em.id = ae.entrega_id
WHERE ae.status = 'aguardando'
ORDER BY ae.data_agendada;
```
