# PRD: Revisão do Módulo de Pallets - Fluxos 2.2 e 3.2

**Versão**: 1.1.0
**Data**: 25/01/2026
**Status**: ✅ 100% IMPLEMENTADO
**Autor**: Claude Code (Precision Engineer Mode)
**Referência**: PRD original em `.claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md`

> **Changelog v1.1.0**: Endpoints de sincronização (seção 6) implementados.

---

## 1. ESCOPO DA REVISÃO

### 1.1 Objetivos
1. Revisar implementação do fluxo 2.2 (Domínio A - Controle dos Pallets)
2. Revisar implementação do fluxo 3.2 (Domínio B - Tratativa das NFs)
3. Verificar sincronização com Odoo
4. Documentar endpoints para sincronização por data
5. Gerar documentação "Como Usar" para cada etapa

---

## 2. ESTRUTURA IMPLEMENTADA

### 2.1 Arquivos do Módulo

```
app/pallet/
├── models/
│   ├── credito.py          # PalletCredito (280 linhas)
│   ├── documento.py        # PalletDocumento (228 linhas)
│   ├── solucao.py          # PalletSolucao (386 linhas)
│   ├── nf_remessa.py       # PalletNFRemessa (188 linhas)
│   └── nf_solucao.py       # PalletNFSolucao (387 linhas)
├── routes/
│   ├── dashboard.py        # Dashboard principal
│   ├── controle_pallets.py # Domínio A (733 linhas)
│   ├── tratativa_nfs.py    # Domínio B (724 linhas)
│   ├── nf_remessa.py       # CRUD NF Remessa
│   └── movimentacoes.py    # Movimentações
├── services/
│   ├── credito_service.py       # Lógica de créditos
│   ├── solucao_pallet_service.py # Soluções (642 linhas)
│   ├── match_service.py         # Match automático (986 linhas)
│   ├── nf_service.py            # Serviço de NFs (896 linhas)
│   └── sync_odoo_service.py     # Sincronização Odoo
└── templates/pallet/v2/
    ├── dashboard.html
    ├── controle_pallets/
    │   ├── vales.html
    │   ├── solucoes.html
    │   └── historico.html
    └── tratativa_nfs/
        ├── direcionamento.html
        ├── sugestoes.html
        ├── solucoes.html
        └── canceladas.html
```

### 2.2 Acesso via Menu

**Localização**: Menu Operacional > Gestão de Pallets
**URL**: `/pallet/v2/`

---

## 3. FLUXO 2.2 - DOMÍNIO A (CONTROLE DOS PALLETS)

### 3.1 A.1 - CONTROLE DOS VALES

| Funcionalidade | Status | Rota | Template |
|----------------|--------|------|----------|
| Registrar Canhoto | ✅ | POST `/controle/documento` | `vales.html` |
| Registrar Vale Pallet | ✅ | POST `/controle/documento` | `vales.html` |
| Marcar como Recebido | ✅ | POST `/controle/documento/<id>/receber` | `vales.html` |
| Listar Documentos | ✅ | GET `/controle/vales` | `vales.html` |

### 3.2 A.2 - SOLUÇÕES DOS PALLETS

| Solução | Status | Rota | Template |
|---------|--------|------|----------|
| **A.2.1 Baixa** (Descarte) | ✅ | POST `/controle/baixa` | Modal em `solucoes.html` |
| **A.2.2 Venda** (N:1) | ✅ | POST `/controle/venda` | Modal em `solucoes.html` |
| **A.2.3 Recebimento** (Coleta) | ✅ | POST `/controle/recebimento` | Modal em `solucoes.html` |
| **A.2.4 Substituição** | ✅ | POST `/controle/substituicao` | Modal em `solucoes.html` |

### 3.3 Rotas Completas do Domínio A

| Rota | Método | Descrição |
|------|--------|-----------|
| `/pallet/v2/controle/vales` | GET | Lista canhotos/vales |
| `/pallet/v2/controle/solucoes` | GET | Lista créditos pendentes |
| `/pallet/v2/controle/historico` | GET | Histórico de soluções |
| `/pallet/v2/controle/documento` | POST | Registra canhoto/vale |
| `/pallet/v2/controle/documento/<id>/receber` | POST | Marca documento recebido |
| `/pallet/v2/controle/baixa` | POST | Registra baixa |
| `/pallet/v2/controle/venda` | POST | Registra venda (N:1) |
| `/pallet/v2/controle/recebimento` | POST | Registra recebimento |
| `/pallet/v2/controle/substituicao` | POST | Registra substituição |
| `/pallet/v2/controle/api/creditos` | GET | API - Lista créditos |
| `/pallet/v2/controle/api/credito/<id>` | GET | API - Detalhe crédito |

---

## 4. FLUXO 3.2 - DOMÍNIO B (TRATATIVA DAS NFs)

### 4.1 B.1 - DIRECIONAMENTO DAS NFs

| Funcionalidade | Status | Rota | Template |
|----------------|--------|------|----------|
| Listar NFs Ativas | ✅ | GET `/tratativa/direcionamento` | `direcionamento.html` |
| Listar NFs Canceladas | ✅ | GET `/tratativa/canceladas` | `canceladas.html` |
| Processar Devoluções DFe | ✅ | POST `/tratativa/processar-devolucoes` | `direcionamento.html` |

### 4.2 B.2 - SOLUÇÃO DAS NFs

| Solução | Status | Rota | Template |
|---------|--------|------|----------|
| **B.2.1 Devolução** (1:N) | ✅ | POST `/tratativa/vincular-devolucao` | `sugestoes.html` |
| **B.2.2 Retorno** (1:1) | ✅ | POST `/tratativa/vincular-retorno` | `sugestoes.html` |
| **B.2.3 Cancelamento** | ✅ | Via NFService.cancelar_nf() | - |

### 4.3 Rotas Completas do Domínio B

| Rota | Método | Descrição |
|------|--------|-----------|
| `/pallet/v2/tratativa/direcionamento` | GET | NFs aguardando vinculação |
| `/pallet/v2/tratativa/sugestoes` | GET | Sugestões automáticas |
| `/pallet/v2/tratativa/solucoes` | GET | Histórico de soluções |
| `/pallet/v2/tratativa/canceladas` | GET | NFs canceladas |
| `/pallet/v2/tratativa/vincular-devolucao` | POST | Vincular devolução 1:N |
| `/pallet/v2/tratativa/vincular-retorno` | POST | Vincular retorno 1:1 |
| `/pallet/v2/tratativa/confirmar-sugestao/<id>` | POST | Confirmar sugestão |
| `/pallet/v2/tratativa/rejeitar-sugestao/<id>` | POST | Rejeitar sugestão |
| `/pallet/v2/tratativa/processar-devolucoes` | POST | Buscar devoluções no DFe |
| `/pallet/v2/tratativa/api/sugestoes` | GET | API - Lista sugestões |
| `/pallet/v2/tratativa/api/buscar-devolucoes` | GET | API - Busca NFs DFe |

---

## 5. SINCRONIZAÇÃO COM ODOO

### 5.1 Serviço de Sincronização

**Arquivo**: `app/pallet/services/sync_odoo_service.py`
**Classe**: `PalletSyncService`

### 5.2 Tipos de Sincronização

| Tipo | Método | Fonte Odoo | Destino |
|------|--------|------------|---------|
| NF de Remessa | `sincronizar_remessas()` | `account.move` (l10n_br_tipo_pedido='vasilhame') | PalletNFRemessa + PalletCredito |
| NF de Venda | `sincronizar_vendas_pallet()` | `account.move.line` (produto='208000012') | MovimentacaoEstoque |
| NF Devolução/Retorno | `match_service.buscar_nfs_devolucao_pallet_dfe()` | `l10n_br_fiscal.document` | PalletNFSolucao |

### 5.3 Fluxo de Importação de NF de Remessa

```
sync_odoo_service.sincronizar_remessas(data_de, data_ate)
    │
    ├── Domain Odoo:
    │   - move_type IN ['out_invoice', 'out_refund']
    │   - state = 'posted'
    │   - l10n_br_tipo_pedido = 'vasilhame'
    │   - invoice_date >= data_de
    │   - invoice_date <= data_ate
    │
    ├── Filtra CNPJs intercompany (Nacom/La Famiglia)
    │
    ├── Cria MovimentacaoEstoque (sistema legado)
    │
    └── Chama NFService.importar_nf_remessa_odoo()
            │
            ├── Cria PalletNFRemessa
            │
            └── Cria PalletCredito (automático via REGRA 001)
```

### 5.4 Fluxo de Busca de Devoluções no DFe

```
match_service.buscar_nfs_devolucao_pallet_dfe(data_de, data_ate)
    │
    ├── Domain Odoo (l10n_br_fiscal.document):
    │   - document_type_id.code = '55' (NF-e)
    │   - state = 'autorizada'
    │   - document_date >= data_de
    │
    ├── Filtra por CFOP: ['5920', '6920', '1920', '2920']
    │   OU produto código = '208000012' (PALLET)
    │
    ├── Extrai info_complementar para identificar NF de origem
    │
    └── Retorna lista de candidatas para vinculação
```

### 5.5 Endpoints de Sincronização por Data

#### 5.5.1 Sincronizar NFs de Remessa

**Endpoint Atual**: Não existe endpoint HTTP direto

**Uso via CLI**:
```bash
flask pallet sync-remessas --data-de 2026-01-01 --data-ate 2026-01-25
```

**Uso via Python**:
```python
from app.pallet.services.sync_odoo_service import PalletSyncService

service = PalletSyncService()
resultado = service.sincronizar_remessas(
    data_de='2026-01-01',
    data_ate='2026-01-25'
)
```

#### 5.5.2 Processar Devoluções do DFe

**Endpoint**: `POST /pallet/v2/tratativa/processar-devolucoes`

**Parâmetros**:
```json
{
  "data_de": "2026-01-01",
  "data_ate": "2026-01-25",
  "criar_sugestoes": true
}
```

**Resposta**:
```json
{
  "success": true,
  "processadas": 15,
  "devolucoes": 10,
  "retornos": 5,
  "retornos_automaticos": 3,
  "sugestoes_criadas": 12,
  "sem_match": 0,
  "erros": []
}
```

#### 5.5.3 API para Buscar Devoluções (sem criar sugestões)

**Endpoint**: `GET /pallet/v2/tratativa/api/buscar-devolucoes`

**Parâmetros Query**:
- `data_de`: Data inicial (formato YYYY-MM-DD)
- `data_ate`: Data final (formato YYYY-MM-DD)

**Resposta**:
```json
{
  "success": true,
  "total": 15,
  "nfs": [
    {
      "numero_nf": "12345",
      "chave_nfe": "...",
      "data_emissao": "2026-01-15",
      "cnpj_emitente": "12345678000199",
      "nome_emitente": "Cliente XYZ",
      "quantidade": 10,
      "tipo_sugerido": "DEVOLUCAO",
      "candidatas_remessa": [...]
    }
  ]
}
```

### 5.6 Constantes de Identificação

```python
# app/pallet/services/sync_odoo_service.py
COD_PRODUTO_PALLET = '208000012'
NOME_PRODUTO_PALLET = 'PALLET'

# CNPJs intercompany (ignorar)
CNPJS_INTERCOMPANY_PREFIXOS = [
    '61724241',  # Nacom Goya
    '18467441',  # La Famiglia
]

# Mapeamento company_id → empresa
COMPANY_ID_TO_EMPRESA = {
    4: 'CD',  # NACOM GOYA - CD
    1: 'FB',  # NACOM GOYA - FB
    3: 'SC',  # NACOM GOYA - SC
}

# app/pallet/services/match_service.py
CFOP_PALLET = ['5920', '6920', '1920', '2920']
```

---

## 6. ENDPOINTS DE SINCRONIZAÇÃO (IMPLEMENTADOS ✅)

### 6.1 Endpoint de Sincronização de Remessas via HTTP

**Status**: ✅ IMPLEMENTADO em 25/01/2026

**Rota**: `POST /pallet/v2/nf-remessa/api/sync/remessas`

**Parâmetros (JSON body)**:
```json
{
  "data_de": "2026-01-01",
  "data_ate": "2026-01-25",
  "dias_retroativos": 30  // usado se data_de não informado
}
```

**Resposta**:
```json
{
  "success": true,
  "mensagem": "Sincronização concluída: 15 novos registros, 3 baixas",
  "resultado": {
    "remessas": {"processados": 50, "novos": 5, "ja_existentes": 45, "erros": 0},
    "vendas": {"processados": 20, "novos": 3, "ja_existentes": 17, "erros": 0},
    "devolucoes": {"processados": 30, "novos": 5, "baixas_realizadas": 2, "erros": 0},
    "recusas": {"processados": 10, "novos": 2, "baixas_realizadas": 1, "erros": 0},
    "total_novos": 15,
    "total_baixas": 3
  }
}
```

**Arquivo**: `app/pallet/routes/nf_remessa.py:364-426`

### 6.2 Endpoint de Status de Sincronização

**Status**: ✅ IMPLEMENTADO em 25/01/2026

**Rota**: `GET /pallet/v2/nf-remessa/api/sync/status`

**Resposta**:
```json
{
  "ultima_sincronizacao": "2026-01-25T10:30:00",
  "ultima_nf_data_emissao": "2026-01-24",
  "nfs_remessa": {
    "total": 150,
    "ativas": 45,
    "resolvidas": 100,
    "canceladas": 5
  },
  "creditos": {
    "total": 180,
    "pendentes": 55,
    "baixados": 125
  },
  "quantidades": {
    "total_pallets": 2500,
    "pendentes": 650
  }
}
```

**Arquivo**: `app/pallet/routes/nf_remessa.py:429-512`

---

## 7. DOCUMENTAÇÃO "COMO USAR"

### 7.1 Domínio A - Controle dos Pallets

#### Registrar Baixa (Descarte)
```
1. Operacional > Gestão de Pallets
2. Aba "Controle de Pallets" > "Soluções de Pallets"
3. Localizar crédito > Botão "Baixa"
4. Preencher: Quantidade, Motivo, Confirmação cliente
5. Clicar "Registrar Baixa"
```

#### Registrar Venda (N:1)
```
1. Operacional > Gestão de Pallets
2. Aba "Controle de Pallets" > "Soluções de Pallets"
3. Botão "+ Registrar Venda"
4. Preencher: NF venda, Data, Valor unitário, Comprador
5. Selecionar créditos e quantidades
6. Clicar "Registrar Venda"
```

#### Registrar Recebimento (Coleta)
```
1. Operacional > Gestão de Pallets
2. Aba "Controle de Pallets" > "Soluções de Pallets"
3. Localizar crédito > Botão "Recebimento"
4. Preencher: Quantidade, Data, Local, Quem entregou
5. Clicar "Registrar Recebimento"
```

#### Registrar Substituição
```
1. Operacional > Gestão de Pallets
2. Aba "Controle de Pallets" > "Soluções de Pallets"
3. Localizar crédito > Botão "Substituição"
4. Preencher: Quantidade, Novo responsável, NF destino, Motivo
5. Clicar "Registrar Substituição"
```

### 7.2 Domínio B - Tratativa das NFs

#### Processar Devoluções do DFe
```
1. Operacional > Gestão de Pallets
2. Aba "Tratativa das NFs" > "Direcionamento"
3. Botão "Processar Devoluções"
4. Sistema busca NFs no Odoo DFe
5. Sugestões aparecem em "Sugestões"
```

#### Confirmar/Rejeitar Sugestões
```
1. Operacional > Gestão de Pallets
2. Aba "Tratativa das NFs" > "Sugestões"
3. Revisar NF de devolução e remessa sugerida
4. Clicar "Confirmar" ou "Rejeitar" (informar motivo)
```

#### Vincular Devolução Manualmente (1:N)
```
1. Operacional > Gestão de Pallets
2. Aba "Tratativa das NFs" > "Direcionamento"
3. Botão "+ Vincular Devolução"
4. Preencher: NF devolução, Data, Emitente, Quantidade
5. Selecionar NFs de remessa a vincular
6. Clicar "Vincular"
```

#### Vincular Retorno Manualmente (1:1)
```
1. Operacional > Gestão de Pallets
2. Aba "Tratativa das NFs" > "Direcionamento"
3. Localizar NF remessa > Botão "Vincular Retorno"
4. Preencher: NF retorno, Data, Emitente, Quantidade
5. Clicar "Vincular"
```

---

## 8. CONCLUSÃO

### 8.1 Status Geral: 95% IMPLEMENTADO

| Componente | Status |
|------------|--------|
| Modelos de dados (5 tabelas) | ✅ |
| Rotas Domínio A (9+) | ✅ |
| Rotas Domínio B (9+) | ✅ |
| Services (5 arquivos) | ✅ |
| Templates v2 (11 arquivos) | ✅ |
| Sincronização Remessas Odoo | ✅ |
| Sincronização Devoluções DFe | ✅ |
| Match automático | ✅ |
| Acesso via menu | ✅ |

### 8.2 Pendências

| # | Item | Prioridade |
|---|------|------------|
| 1 | Criar endpoint HTTP para sync remessas por data | MÉDIA |
| 2 | Criar endpoint de status de sincronização | BAIXA |

### 8.3 Próximos Passos

1. Testar fluxo completo end-to-end em homologação
2. Validar integração com Odoo real
3. Implementar endpoints pendentes de sincronização
4. Treinar usuários com documentação "Como Usar"
