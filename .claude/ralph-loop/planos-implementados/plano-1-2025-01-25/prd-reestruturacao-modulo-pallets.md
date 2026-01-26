# PRD: Reestruturação do Módulo de Gestão de Pallets

**Versão**: 1.0.0
**Data**: 25/01/2026
**Status**: DRAFT - Aguardando Aprovação
**Autor**: Claude Code (Precision Engineer Mode)

---

## 1. VISÃO GERAL

### 1.1 Problema

O módulo atual de pallets mistura conceitos e fluxos de forma não estruturada. As duas responsabilidades principais (Controle de Pallets/Créditos e Tratativa de NFs) estão entrelaçadas na UI e no código, dificultando:

- Rastreabilidade de créditos de pallet
- Resolução independente de pallets vs NFs
- Auditoria de operações

### 1.2 Solução Proposta

Reestruturar o módulo em **dois domínios independentes** mas relacionados:

1. **Domínio A - Controle dos Pallets**: Gerencia créditos, vales e soluções de pallets
2. **Domínio B - Tratativa das NFs**: Gerencia o ciclo de vida das NFs de remessa

### 1.3 Fluxo Macro

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLUXO COMPLETO DE PALLETS                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [1] IMPORTAÇÃO DA NF DE REMESSA DE PALLET (via Odoo)                     │
│       └── Ponto de partida único (NF emitida no Odoo, importada aqui)       │
│           └── Cria registro em ambos os domínios                            │
│                          │                                                  │
│           ┌──────────────┴──────────────┐                                   │
│           ▼                             ▼                                   │
│   ┌───────────────────┐       ┌────────────────────┐                        │
│   │  DOMÍNIO A        │       │  DOMÍNIO B         │                        │
│   │  Controle Pallets │       │  Tratativa NFs     │                        │
│   └───────────────────┘       └────────────────────┘                        │
│           │                             │                                   │
│   ┌───────┴───────┐             ┌───────┴───────┐                           │
│   │               │             │               │                           │
│   ▼               ▼             ▼               ▼                           │
│ [A.1] Docs     [A.2] Soluções  [B.1] NFs      [B.2] Status                  │
│ Enriquecer     Resolver        Vincular       Final                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. DOMÍNIO A - CONTROLE DOS PALLETS

### 2.1 Conceito

Gerencia o **crédito de pallets** que a Nacom tem direito de receber/vender. Independente de como a NF de remessa será resolvida documentalmente.

### 2.2 Estrutura Hierárquica

```
DOMÍNIO A: CONTROLE DOS PALLETS
│
├── A.1 CONTROLE DOS VALES (Enriquecimento de Informações)
│   │
│   ├── A.1.1 Canhoto da NF de Remessa
│   │   └── Cliente confirmou recebimento da remessa
│   │   └── Dados: foto_canhoto, data_recebimento, assinatura_conferente
│   │
│   └── A.1.2 Vale Pallet
│       └── Documento emitido pelo cliente informando débito
│       └── Normalmente quando NÃO houve NF de remessa (falha operacional)
│       └── Dados: numero_vale, data_emissao, qtd_pallets, validade
│
└── A.2 SOLUÇÕES DOS PALLETS (Resolução dos Créditos)
    │
    ├── A.2.1 Baixa (Descarte)
    │   └── Pallet descartável, cliente não devolverá
    │   └── Confirmado com cliente, deduz do crédito
    │   └── Dados: motivo_baixa, qtd_baixa, confirmado_por, data_confirmacao
    │
    ├── A.2.2 Venda
    │   └── Vender os pallets que temos direito
    │   └── 1 NF de Venda pode resolver N NFs de Remessa
    │   └── Dados: nf_venda, valor_venda, nfs_remessa_vinculadas[]
    │
    ├── A.2.3 Recebimento (Coleta)
    │   └── Receber pallets físicos do cliente ou transportadora
    │   └── Pode ser parcial ou total
    │   └── Dados: qtd_recebida, data_recebimento, recebido_de, local_recebimento
    │
    └── A.2.4 Substituição de Responsabilidade
        └── Transferir crédito de um devedor para outro
        └── Ex: Transportadora (NF 123, 30 pallets) → Cliente X (NF 456, 10 pallets)
        └── Transportadora agora deve apenas 20 pallets na NF 123
        └── Dados: nf_origem, qtd_transferida, nf_destino, novo_responsavel
```

### 2.3 Modelo de Dados - Domínio A

#### Tabela: `pallet_credito` (NOVA)

```python
class PalletCredito(db.Model):
    """
    Registro de crédito de pallet a receber.
    Criado automaticamente ao IMPORTAR NF de remessa do Odoo.
    """
    __tablename__ = 'pallet_creditos'

    id = db.Column(db.Integer, primary_key=True)

    # Vínculo com NF de remessa (origem)
    nf_remessa_id = db.Column(db.Integer, db.ForeignKey('pallet_nf_remessa.id'), nullable=False)

    # Quantidade original e saldo
    qtd_original = db.Column(db.Integer, nullable=False)
    qtd_saldo = db.Column(db.Integer, nullable=False)  # Saldo pendente de resolução

    # Responsável atual pelo débito
    tipo_responsavel = db.Column(db.String(20))  # 'TRANSPORTADORA', 'CLIENTE'
    cnpj_responsavel = db.Column(db.String(20), index=True)
    nome_responsavel = db.Column(db.String(255))

    # Status
    status = db.Column(db.String(20), default='PENDENTE')
    # PENDENTE, PARCIAL, RESOLVIDO

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)
```

#### Tabela: `pallet_documento` (NOVA - substitui parcialmente ValePallet)

```python
class PalletDocumento(db.Model):
    """
    Documentos que enriquecem o crédito de pallet.
    Canhoto ou Vale Pallet emitido pelo cliente.
    """
    __tablename__ = 'pallet_documentos'

    id = db.Column(db.Integer, primary_key=True)
    credito_id = db.Column(db.Integer, db.ForeignKey('pallet_creditos.id'), nullable=False)

    # Tipo do documento
    tipo = db.Column(db.String(20), nullable=False)
    # 'CANHOTO' - Canhoto da NF assinado
    # 'VALE_PALLET' - Vale emitido pelo cliente

    # Dados do documento
    numero_documento = db.Column(db.String(50))
    data_emissao = db.Column(db.Date)
    data_validade = db.Column(db.Date)
    quantidade = db.Column(db.Integer, nullable=False)

    # Arquivo anexo
    arquivo_path = db.Column(db.String(500))

    # Quem emitiu
    cnpj_emissor = db.Column(db.String(20))
    nome_emissor = db.Column(db.String(255))

    # Status de recebimento pela Nacom
    recebido = db.Column(db.Boolean, default=False)
    recebido_em = db.Column(db.DateTime)
    recebido_por = db.Column(db.String(100))

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    observacao = db.Column(db.Text)
```

#### Tabela: `pallet_solucao` (NOVA)

```python
class PalletSolucao(db.Model):
    """
    Registro de resolução de crédito de pallet.
    Um crédito pode ter múltiplas soluções parciais.
    """
    __tablename__ = 'pallet_solucoes'

    id = db.Column(db.Integer, primary_key=True)
    credito_id = db.Column(db.Integer, db.ForeignKey('pallet_creditos.id'), nullable=False)

    # Tipo de solução
    tipo = db.Column(db.String(20), nullable=False)
    # 'BAIXA' - Descarte confirmado
    # 'VENDA' - Vendidos ao cliente/terceiro
    # 'RECEBIMENTO' - Pallets físicos recebidos
    # 'SUBSTITUICAO' - Transferência de responsabilidade

    # Quantidade resolvida
    quantidade = db.Column(db.Integer, nullable=False)

    # Dados específicos por tipo
    # Para BAIXA:
    motivo_baixa = db.Column(db.String(100))
    confirmado_cliente = db.Column(db.Boolean)

    # Para VENDA:
    nf_venda = db.Column(db.String(20))
    valor_venda = db.Column(db.Numeric(15, 2))

    # Para RECEBIMENTO:
    data_recebimento = db.Column(db.Date)
    local_recebimento = db.Column(db.String(100))

    # Para SUBSTITUICAO:
    nf_destino = db.Column(db.String(20))  # Nova NF de remessa
    credito_destino_id = db.Column(db.Integer, db.ForeignKey('pallet_creditos.id'))

    # Responsável pela solução
    cnpj_responsavel = db.Column(db.String(20))
    nome_responsavel = db.Column(db.String(255))

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    observacao = db.Column(db.Text)
```

---

## 3. DOMÍNIO B - TRATATIVA DAS NFs

### 3.1 Conceito

Gerencia o **ciclo de vida documental** das NFs de remessa de pallet. Como a NF será "fechada" fiscalmente.

### 3.2 Estrutura Hierárquica

```
DOMÍNIO B: TRATATIVA DAS NFs
│
├── B.1 DIRECIONAMENTO DAS NFs
│   │
│   ├── B.1.1 Vinculação NF Origem
│   │   └── Vincular NF de remessa a documento de retorno
│   │   └── Automático ou manual
│   │
│   └── B.1.2 NFs Canceladas (Visualização)
│       └── NFs que foram canceladas
│       └── Mantidas para auditoria
│
└── B.2 SOLUÇÃO DAS NFs (Fechamento Fiscal)
    │
    ├── B.2.1 Devolução
    │   └── NF de devolução emitida pelo cliente
    │   └── 1 NF Devolução pode referenciar N NFs de Remessa
    │   └── Sistema sugere match, usuário confirma
    │   └── Dados: nf_devolucao, nfs_remessa_vinculadas[], status_sugestao
    │
    ├── B.2.2 Retorno
    │   └── NF de retorno emitida pelo cliente referenciando 1 NF de remessa
    │   └── Vínculo automático pelo número nas informações complementares
    │   └── Similar a devolução mas 1:1
    │   └── Dados: nf_retorno, nf_remessa_vinculada
    │
    └── B.2.3 Cancelamento
        └── NF de remessa foi cancelada
        └── Pode ser por recebimento ou emissão errada
        └── Manter registro para auditoria
        └── Dados: motivo_cancelamento, cancelado_em, cancelado_por
```

### 3.3 Modelo de Dados - Domínio B

#### Tabela: `pallet_nf_remessa` (NOVA - centraliza NFs)

```python
class PalletNFRemessa(db.Model):
    """
    NF de remessa de pallet emitida.
    Ponto central de rastreamento.
    """
    __tablename__ = 'pallet_nf_remessa'

    id = db.Column(db.Integer, primary_key=True)

    # Identificação da NF
    numero_nf = db.Column(db.String(20), nullable=False, unique=True, index=True)
    serie = db.Column(db.String(5))
    chave_nfe = db.Column(db.String(44))
    data_emissao = db.Column(db.DateTime, nullable=False)

    # Dados Odoo
    odoo_account_move_id = db.Column(db.Integer)
    odoo_picking_id = db.Column(db.Integer)

    # Empresa emissora
    empresa = db.Column(db.String(10), nullable=False)  # CD, FB, SC

    # Destinatário
    tipo_destinatario = db.Column(db.String(20))  # 'TRANSPORTADORA', 'CLIENTE'
    cnpj_destinatario = db.Column(db.String(20), nullable=False, index=True)
    nome_destinatario = db.Column(db.String(255))

    # Transportadora (se tipo_destinatario = 'CLIENTE')
    cnpj_transportadora = db.Column(db.String(20))
    nome_transportadora = db.Column(db.String(255))

    # Quantidade
    quantidade = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Numeric(15, 2), default=35.00)
    valor_total = db.Column(db.Numeric(15, 2))

    # Status da NF
    status = db.Column(db.String(20), default='ATIVA')
    # ATIVA, RESOLVIDA, CANCELADA

    # Campos de cancelamento
    cancelada = db.Column(db.Boolean, default=False)
    cancelada_em = db.Column(db.DateTime)
    motivo_cancelamento = db.Column(db.String(255))

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))

    # Relacionamentos
    creditos = db.relationship('PalletCredito', backref='nf_remessa')
    solucoes_nf = db.relationship('PalletNFSolucao', backref='nf_remessa')
```

#### Tabela: `pallet_nf_solucao` (NOVA)

```python
class PalletNFSolucao(db.Model):
    """
    Solução documental de NF de remessa.
    Como a NF foi "fechada" fiscalmente.
    """
    __tablename__ = 'pallet_nf_solucoes'

    id = db.Column(db.Integer, primary_key=True)
    nf_remessa_id = db.Column(db.Integer, db.ForeignKey('pallet_nf_remessa.id'), nullable=False)

    # Tipo de solução
    tipo = db.Column(db.String(20), nullable=False)
    # 'DEVOLUCAO' - NF de devolução do cliente
    # 'RETORNO' - NF de retorno do cliente
    # 'CANCELAMENTO' - NF foi cancelada

    # Quantidade resolvida nesta solução
    quantidade = db.Column(db.Integer, nullable=False)

    # Dados da NF de devolução/retorno
    numero_nf_solucao = db.Column(db.String(20))
    chave_nfe_solucao = db.Column(db.String(44))
    data_nf_solucao = db.Column(db.DateTime)

    # Status de vinculação
    vinculacao = db.Column(db.String(20), default='MANUAL')
    # 'AUTOMATICO' - Sistema encontrou match
    # 'MANUAL' - Usuário vinculou manualmente
    # 'SUGESTAO' - Sistema sugeriu, aguarda confirmação

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    confirmado_em = db.Column(db.DateTime)
    confirmado_por = db.Column(db.String(100))
    observacao = db.Column(db.Text)
```

---

## 4. INTERFACE DO USUÁRIO

### 4.1 Estrutura de Navegação

```
MENU: Financeiro > Central Fiscal > Gestão de Pallets
│
├── [TAB 1] NFs de Remessa (Ponto de Partida)
│   ├── Listagem de todas as NFs de remessa
│   ├── Filtros: status, empresa, destinatário, período
│   ├── Ações: Emitir nova NF, Ver detalhes
│   └── Link para os dois domínios de cada NF
│
├── [TAB 2] Controle dos Pallets (Domínio A)
│   │
│   ├── [SUB-TAB 2.1] Controle de Vales
│   │   ├── Canhotos recebidos
│   │   ├── Vales Pallet pendentes
│   │   └── Ação: Registrar documento
│   │
│   └── [SUB-TAB 2.2] Soluções de Pallets
│       ├── Pendentes de resolução (saldo > 0)
│       ├── Ações: Baixa, Venda, Recebimento, Substituição
│       └── Histórico de soluções
│
└── [TAB 3] Tratativa das NFs (Domínio B)
    │
    ├── [SUB-TAB 3.1] Direcionamento
    │   ├── NFs aguardando vinculação
    │   ├── Sugestões automáticas de match
    │   └── NFs canceladas (visualização)
    │
    └── [SUB-TAB 3.2] Soluções de NFs
        ├── Devoluções registradas
        ├── Retornos registrados
        └── Ação: Vincular NF de devolução/retorno
```

### 4.2 Fluxo de Telas

```
[1] DASHBOARD PALLETS
    │
    ├── Cards de resumo:
    │   ├── Total pallets em terceiros
    │   ├── Créditos pendentes de solução
    │   ├── NFs pendentes de vinculação
    │   └── Vales próximos do vencimento
    │
    └── Ações rápidas:
        ├── [Registrar Vale Pallet]
        └── [Registrar Recebimento]

[2] DETALHE NF REMESSA
    │
    ├── Dados da NF
    ├── Status dos dois domínios
    │   ├── Domínio A: Saldo de crédito, documentos
    │   └── Domínio B: Status da NF, vinculações
    │
    └── Ações contextuais por status

[3] FORMULÁRIOS DE AÇÃO
    │
    ├── Registrar Canhoto
    ├── Registrar Vale Pallet
    ├── Registrar Baixa
    ├── Registrar Venda (N:1)
    ├── Registrar Recebimento
    ├── Registrar Substituição
    ├── Vincular Devolução (1:N)
    └── Vincular Retorno (1:1)
```

---

## 5. REGRAS DE NEGÓCIO CRÍTICAS

### 5.1 Importação de NF de Remessa (via Odoo)

```
REGRA 001: Ao IMPORTAR NF de remessa do Odoo:
  - NF é emitida no Odoo, sistema apenas IMPORTA e VINCULA
  - CRIAR registro em pallet_nf_remessa (dados da NF do Odoo)
  - CRIAR registro em pallet_credito vinculado automaticamente
  - qtd_saldo inicial = quantidade da NF importada
```

### 5.2 Resolução de Crédito (Domínio A)

```
REGRA 002: Qualquer solução de pallet:
  - DECREMENTA pallet_credito.qtd_saldo
  - CRIA registro em pallet_solucao
  - Se qtd_saldo = 0, status = 'RESOLVIDO'
  - Se qtd_saldo > 0 e < original, status = 'PARCIAL'

REGRA 003: Substituição de responsabilidade:
  - DECREMENTA saldo do crédito origem
  - CRIA novo crédito no destino OU incrementa existente
  - Mantém rastreabilidade via pallet_solucao.credito_destino_id
```

### 5.3 Resolução de NF (Domínio B)

```
REGRA 004: Vinculação de devolução/retorno:
  - 1 NF devolução pode fechar N NFs remessa
  - 1 NF retorno fecha apenas 1 NF remessa
  - Sistema sugere match mas EXIGE confirmação do usuário

REGRA 005: Cancelamento de NF:
  - NÃO apaga registro
  - SET cancelada = True
  - SET motivo_cancelamento
  - Crédito associado deve ser tratado separadamente
```

### 5.4 Independência dos Domínios

```
REGRA 006: Os domínios são INDEPENDENTES
  - Crédito pode estar RESOLVIDO e NF ainda ATIVA (vendeu pallets mas não tem NF de devolução)
  - NF pode estar RESOLVIDA e Crédito ainda PENDENTE (tem NF de devolução mas não recebeu os pallets)
  - Cada domínio tem seu próprio status e workflow
```

---

## 6. MIGRAÇÃO DE DADOS

### 6.1 Tabelas Afetadas

| Tabela Atual | Ação | Destino |
|--------------|------|---------|
| `vale_pallets` | MIGRAR | `pallet_documentos` |
| `Embarque.nf_pallet_*` | MANTER | Continua existindo (campos físicos) |
| `EmbarqueItem.nf_pallet_*` | MANTER | Continua existindo |
| `MovimentacaoEstoque` | AVALIAR | Pode ser fonte de dados históricos |

### 6.2 Script de Migração

```python
# Scripts a criar:
# 1. scripts/migrate_pallet_create_tables.py - Cria novas tabelas
# 2. scripts/migrate_pallet_import_data.py - Importa dados existentes
# 3. scripts/migrate_pallet_validate.py - Valida integridade
```

---

## 7. ARQUIVOS A CRIAR/MODIFICAR

### 7.1 Novos Arquivos

```
app/pallet/
├── models/
│   ├── __init__.py
│   ├── nf_remessa.py          # PalletNFRemessa
│   ├── credito.py             # PalletCredito
│   ├── documento.py           # PalletDocumento
│   ├── solucao.py             # PalletSolucao
│   └── nf_solucao.py          # PalletNFSolucao
│
├── routes/
│   ├── __init__.py
│   ├── dashboard.py           # Dashboard principal
│   ├── nf_remessa.py          # CRUD NF Remessa
│   ├── controle_pallets.py    # Domínio A
│   └── tratativa_nfs.py       # Domínio B
│
├── services/
│   ├── __init__.py
│   ├── emissao_nf_pallet.py   # (existente, manter)
│   ├── credito_service.py     # Lógica Domínio A
│   ├── nf_service.py          # Lógica Domínio B
│   └── match_service.py       # Sugestões de vinculação
│
└── templates/pallet/
    ├── dashboard.html
    ├── nf_remessa/
    │   ├── listagem.html
    │   └── detalhe.html
    ├── controle_pallets/
    │   ├── vales.html
    │   └── solucoes.html
    └── tratativa_nfs/
        ├── direcionamento.html
        └── solucoes.html
```

### 7.2 Arquivos a Modificar

```
app/pallet/
├── __init__.py                # Registrar novos blueprints
├── routes.py                  # Deprecar em favor de routes/
└── models.py                  # Deprecar ValePallet, importar novos

app/templates/base.html        # Adicionar links no menu

scripts/
├── criar_tabelas_pallet_v2.py
└── migrar_dados_pallet.py
```

---

## 8. ESTIMATIVA DE ESFORÇO

### Fase 1: Infraestrutura (Fundação)
- [ ] Criar novos models
- [ ] Criar migrations
- [ ] Criar scripts de migração

### Fase 2: Backend (Lógica)
- [ ] Services Domínio A
- [ ] Services Domínio B
- [ ] Match service automático

### Fase 3: Frontend (UI)
- [ ] Dashboard principal
- [ ] Telas Domínio A (Controle Pallets)
- [ ] Telas Domínio B (Tratativa NFs)
- [ ] Formulários de ação

### Fase 4: Migração e Testes
- [ ] Migrar dados existentes
- [ ] Validar integridade
- [ ] Testes de regressão

---

## 9. CRITÉRIOS DE ACEITE

1. ✓ NF de remessa cria automaticamente registro de crédito
2. ✓ Crédito pode ser resolvido independente da NF
3. ✓ NF pode ser resolvida independente do crédito
4. ✓ Venda de pallets permite N NFs remessa → 1 NF venda
5. ✓ Substituição transfere responsabilidade com rastreabilidade
6. ✓ Devolução permite 1 NF → N NFs remessa com confirmação
7. ✓ Retorno vincula automaticamente 1:1 por informações complementares
8. ✓ Cancelamento mantém registro para auditoria
9. ✓ UI separa claramente os dois domínios
10. ✓ Dados históricos migrados corretamente

---

## 10. DECISÕES CONFIRMADAS

### 10.1 Origem das NFs de Devolução/Retorno

**DECISÃO**: Híbrido com sincronização Odoo

```
FLUXO DE NFs DE DEVOLUÇÃO:
┌─────────────────────────────────────────────────────────────────┐
│ 1. NFs aparecem automaticamente no DFe do Odoo (já sincroniza)  │
│ 2. Sistema identifica NFs que são de pallet (CFOP 6920, etc)    │
│ 3. Sistema SUGERE vinculação com NF de remessa original         │
│ 4. Usuário CONFIRMA a vinculação (obrigatório)                  │
│ 5. Só após confirmação, NF de remessa é marcada como resolvida  │
└─────────────────────────────────────────────────────────────────┘

PROBLEMA ATUAL: NFs de devolução de pallet estão aparecendo
incorretamente no módulo de devolução (de produtos).
SOLUÇÃO: Filtrar por CFOP/produto e direcionar para módulo de pallet.

FLUXO DE NFs DE RETORNO:
┌─────────────────────────────────────────────────────────────────┐
│ 1. Verificar se já está sendo sincronizado do Odoo              │
│ 2. Se não, implementar sincronização                            │
│ 3. Sistema busca número da NF de remessa nas info complementares│
│ 4. Sistema SUGERE vinculação automática                         │
│ 5. Usuário CONFIRMA a vinculação                                │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Preço do Pallet

**DECISÃO**: Buscar da NF (não hardcoded)

```
REGRA: O valor unitário deve ser lido da NF de remessa emitida.
- Ao emitir NF via Odoo: valor vem da fatura criada
- Ao registrar NF manual: usuário informa valor
- Default sugerido: R$ 35,00 (mas editável)
```

### 10.3 Questões Ainda em Aberto

1. **Prazos de cobrança**: Manter a lógica atual (7 dias SP/RED, 30 dias demais) ou parametrizar?

2. **Relatórios**: Quais relatórios são necessários para cada domínio?

3. **Notificações**: Alertas automáticos para vales próximos do vencimento?

---

## 11. INTEGRAÇÃO COM MÓDULOS EXISTENTES

### 11.1 Módulo de Devolução (Problema Atual)

**PROBLEMA**: NFs de devolução de pallet estão aparecendo no módulo de devolução de produtos.

**SOLUÇÃO**:

```python
# Filtro a adicionar no módulo de devolução existente
# para EXCLUIR devoluções de pallet:

def filtrar_devolucoes_produto(query):
    """
    Exclui devoluções de pallet do módulo de produtos.
    Pallets são identificados por:
    - CFOP 6920 (Devolução de vasilhame)
    - Produto código 208000012 (PALLET)
    """
    return query.filter(
        ~DFe.cfop.in_(['5920', '6920']),  # Exclui remessa/devolução vasilhame
        ~DFe.produto_codigo.contains('208000012')  # Exclui produto PALLET
    )
```

### 11.2 Sincronização com DFe

**LOCAL**: O módulo de pallets deve consumir dados do DFe sync existente.

```
TABELAS ENVOLVIDAS:
- dfe (NFs de entrada sincronizadas do Odoo)
- dfe_itens (Itens das NFs)

IDENTIFICAÇÃO DE NF DE PALLET:
- CFOP 5920/6920 (Remessa de vasilhame)
- CFOP 1920/2920 (Entrada para devolução de vasilhame)
- Produto: código 208000012 ou nome contém "PALLET"
- Informações complementares: contém número de NF de remessa original
```

### 11.3 Campos do Embarque (Manter)

Os campos de pallet em `Embarque` e `EmbarqueItem` serão **MANTIDOS**:

```
GRUPO 2 - PALLETS FÍSICOS (continua existindo):
- Embarque.nf_pallet_transportadora
- Embarque.qtd_pallet_transportadora
- Embarque.qtd_pallets_separados
- Embarque.qtd_pallets_trazidos
- EmbarqueItem.nf_pallet_cliente
- EmbarqueItem.qtd_pallet_cliente

RELACIONAMENTO:
- Ao preencher nf_pallet_* no Embarque/EmbarqueItem
- Sistema pode criar automaticamente PalletNFRemessa
- OU usuário vincula manualmente a uma PalletNFRemessa existente
```

---

## 12. PRÓXIMOS PASSOS

Após aprovação deste PRD:

1. **Validar modelo de dados** com stakeholders
2. **Definir prioridade** das fases
3. **Criar branch de desenvolvimento**
4. **Implementar Fase 1** (infraestrutura)
5. **Review incremental** a cada fase

---

## APÊNDICE A: RESUMO VISUAL DOS DOMÍNIOS

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                 IMPORTAÇÃO DA NF DE REMESSA DE PALLET (via Odoo)             ║
║                              (Ponto de Partida)                              ║
╠═══════════════════════════════════╦══════════════════════════════════════════╣
║  DOMÍNIO A: CONTROLE DOS PALLETS  ║    DOMÍNIO B: TRATATIVA DAS NFs          ║
║  (Créditos e Soluções)            ║    (Ciclo Documental)                    ║
╠═══════════════════════════════════╬══════════════════════════════════════════╣
║                                   ║                                          ║
║  A.1 CONTROLE DOS VALES           ║    B.1 DIRECIONAMENTO                    ║
║  ├── Canhoto NF Remessa           ║    ├── Vinculação NF Origem              ║
║  └── Vale Pallet                  ║    └── NFs Canceladas (view)             ║
║                                   ║                                          ║
║  A.2 SOLUÇÕES DOS PALLETS         ║    B.2 SOLUÇÃO DAS NFs                   ║
║  ├── Baixa (descarte)             ║    ├── Devolução (1 NF → N remessas)     ║
║  ├── Venda (N remessas → 1 venda) ║    ├── Retorno (1:1 automático)          ║
║  ├── Recebimento (coleta)         ║    └── Cancelamento (auditoria)          ║
║  └── Substituição (transfere)     ║                                          ║
║                                   ║                                          ║
╠═══════════════════════════════════╬══════════════════════════════════════════╣
║  STATUS: PENDENTE/PARCIAL/        ║    STATUS: ATIVA/RESOLVIDA/              ║
║          RESOLVIDO                ║            CANCELADA                     ║
╠═══════════════════════════════════╬══════════════════════════════════════════╣
║  Pergunta: "Quem deve os pallets? ║    Pergunta: "A NF foi fechada           ║
║   Quanto falta receber/vender?"   ║     fiscalmente?"                        ║
╚═══════════════════════════════════╩══════════════════════════════════════════╝

IMPORTANTE: Os domínios são INDEPENDENTES!
- Crédito RESOLVIDO + NF ATIVA = Vendeu pallets, mas não tem NF devolução
- Crédito PENDENTE + NF RESOLVIDA = Tem NF devolução, mas não recebeu pallets
```
