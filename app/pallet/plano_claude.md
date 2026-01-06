# Revisão do Processo de Controle de Pallets - Nacom Goya

## Objetivo da Revisão
Revisar o fluxo completo de controle de pallets, documentar cada etapa e alinhar com a implementação existente.

---

## FLUXOGRAMA PRINCIPAL DO PROCESSO

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              PROCESSO PRÉVIO                                        │
│                                                                                     │
│  ┌──────────┐     ┌───────────┐     ┌──────────────┐     ┌──────────────────────┐  │
│  │ PEDIDO   │────►│ SEPARAÇÃO │────►│   EMBARQUE   │────►│ SEPARAÇÃO FÍSICA +   │  │
│  │ Carteira │     │           │     │              │     │ CONTAGEM DE PALLETS  │  │
│  └──────────┘     └───────────┘     └──────────────┘     └──────────────────────┘  │
│                                                                    │               │
└────────────────────────────────────────────────────────────────────│───────────────┘
                                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         ETAPA 1: FATURAMENTO                                        │
│                                                                                     │
│                    ┌──────────────────────────────────┐                            │
│                    │ Transportador trouxe pallets     │                            │
│                    │ para troca?                      │                            │
│                    └─────────────┬────────────────────┘                            │
│                                  │                                                  │
│                    ┌─────────────┴─────────────┐                                   │
│                    ▼                           ▼                                    │
│               ┌────────┐                  ┌────────┐                               │
│               │  SIM   │                  │  NÃO   │                               │
│               └────┬───┘                  └────┬───┘                               │
│                    │                           │                                    │
│                    ▼                           ▼                                    │
│         ┌─────────────────────┐    ┌────────────────────────────┐                  │
│         │ SEM EMISSÃO DE NF   │    │ Transportador aceita NF    │                  │
│         │ de remessa          │    │ de pallet contra ele?      │                  │
│         │ (troca no ato)      │    │ (campo: nao_aceita_nf_pallet│                  │
│         └─────────────────────┘    │ em Transportadora)          │                  │
│                                    └──────────────┬─────────────┘                  │
│                                                   │                                 │
│                                    ┌──────────────┴──────────────┐                 │
│                                    ▼                             ▼                  │
│                               ┌────────┐                    ┌────────┐             │
│                               │  SIM   │                    │  NÃO   │             │
│                               └────┬───┘                    └────┬───┘             │
│                                    │                             │                  │
│                                    ▼                             ▼                  │
│                      ┌──────────────────────┐      ┌──────────────────────────┐    │
│                      │ EMITIR NF REMESSA    │      │ Cliente aceita NF        │    │
│                      │ p/ TRANSPORTADORA    │      │ de pallet contra ele?    │    │
│                      │                      │      │ (campo em contatos_      │    │
│                      │ - 1 NF para todo     │      │ agendamento)             │    │
│                      │   Embarque           │      └─────────────┬────────────┘    │
│                      │ - Ou 1 NF por        │                    │                 │
│                      │   EmbarqueItem       │       ┌────────────┴────────────┐    │
│                      └──────────────────────┘       ▼                         ▼    │
│                                                ┌────────┐                ┌────────┐│
│                                                │  SIM   │                │  NÃO   ││
│                                                └────┬───┘                └────┬───┘│
│                                                     │                         │    │
│                                                     ▼                         ▼    │
│                                       ┌─────────────────────┐    ┌───────────────┐ │
│                                       │ EMITIR NF REMESSA   │    │ EMBARCAR SEM  │ │
│                                       │ p/ CLIENTE          │    │ NF DE PALLET  │ │
│                                       └─────────────────────┘    │ (troca no ato │ │
│                                                                  │ obrigatória)  │ │
│                                                                  └───────────────┘ │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    ETAPA 2: RESPONSABILIDADE E PRAZOS                               │
│                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────┐ │
│  │                     NF EMITIDA PARA TRANSPORTADORA                            │ │
│  ├───────────────────────────────────────────────────────────────────────────────┤ │
│  │ • Transportadora é responsável pelo retorno dos pallets                       │ │
│  │ • Prazo para retornar vale pallet / canhoto: 30 dias (ou 7 dias para SP/RED)  │ │
│  │ • Se não retornar no prazo → Transformar NF remessa em COBRANÇA               │ │
│  │ • Responsabilidade encerra quando entrega: pallets OU vale pallet OU canhoto  │ │
│  └───────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────┐ │
│  │                        NF EMITIDA PARA CLIENTE                                │ │
│  ├───────────────────────────────────────────────────────────────────────────────┤ │
│  │ • Cliente recebe mercadoria + pallets                                         │ │
│  │ • Cliente dá entrada na NF de pallet                                          │ │
│  │ • Cliente pode: devolver no ato OU assinar canhoto OU emitir vale pallet      │ │
│  └───────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       ETAPA 3: RESOLUÇÃO DA NF DE REMESSA                           │
│                                                                                     │
│  ┌────────────────────────────────────────────────────────────────────────────────┐│
│  │                                                                                ││
│  │                     ┌─────────────────────────┐                                ││
│  │                     │    NF DE REMESSA        │                                ││
│  │                     │    (l10n_br_tipo_pedido │                                ││
│  │                     │    = 'vasilhame')       │                                ││
│  │                     └───────────┬─────────────┘                                ││
│  │                                 │                                              ││
│  │    ┌────────────┬───────────────┼───────────────┬────────────┐                 ││
│  │    ▼            ▼               ▼               ▼            ▼                 ││
│  │ ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────────┐       ││
│  │ │CANCELAR  │ │DEVOLUÇÃO │ │   RECUSA     │ │SUBSTITUIR│ │   VENDA      │       ││
│  │ │          │ │          │ │              │ │          │ │              │       ││
│  │ └────┬─────┘ └────┬─────┘ └──────┬───────┘ └────┬─────┘ └──────┬───────┘       ││
│  │      │            │              │              │              │               ││
│  │      ▼            ▼              ▼              ▼              ▼               ││
│  │ Pallet      Cliente        NF retornou    NF do cliente  Emitir NF de          ││
│  │ devolvido   emite NF       recusada       "consome"      venda (baixa          ││
│  │ no ato      de devolução   (não entrou)   parte da NF    manual)               ││
│  │ (prazo OK)                                da transp.                           ││
│  │                                                                                ││
│  │      │            │              │              │              │               ││
│  │      ▼            ▼              ▼              ▼              ▼               ││
│  │ ┌──────────────────────────────────────────────────────────────────────────┐   ││
│  │ │           SALDO DEVEDOR REDUZIDO AUTOMATICAMENTE                         │   ││
│  │ │           (MovimentacaoEstoque.baixado = True)                           │   ││
│  │ └──────────────────────────────────────────────────────────────────────────┘   ││
│  │                                                                                ││
│  └────────────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       ETAPA 4: VALE PALLET / CANHOTO                                │
│                                                                                     │
│  ┌────────────────────────────────────────────────────────────────────────────────┐│
│  │                                                                                ││
│  │  Cliente não devolveu no ato → Assinou canhoto OU Emitiu vale pallet           ││
│  │                                                                                ││
│  │                     ┌─────────────────────────┐                                ││
│  │                     │   CRIAR VALE NO SISTEMA │                                ││
│  │                     │   (manual)              │                                ││
│  │                     └───────────┬─────────────┘                                ││
│  │                                 │                                              ││
│  │                     ┌───────────┴───────────┐                                  ││
│  │                     │      CAMPOS:          │                                  ││
│  │                     │ • nf_pallet           │                                  ││
│  │                     │ • data_emissao        │                                  ││
│  │                     │ • quantidade          │                                  ││
│  │                     │ • data_validade       │                                  ││
│  │                     │ • tipo (vale/canhoto) │                                  ││
│  │                     │ • posse_atual         │                                  ││
│  │                     │ • pasta_arquivo       │                                  ││
│  │                     └───────────┬───────────┘                                  ││
│  │                                 │                                              ││
│  │                                 ▼                                              ││
│  │                     ┌─────────────────────────┐                                ││
│  │                     │   CICLO DE VIDA         │                                ││
│  │                     │                         │                                ││
│  │                     │ PENDENTE                │                                ││
│  │                     │     ↓                   │                                ││
│  │                     │ RECEBIDO (posse=NACOM)  │                                ││
│  │                     │     ↓                   │                                ││
│  │                     │ EM RESOLUÇÃO            │                                ││
│  │                     │     ↓                   │                                ││
│  │                     │ RESOLVIDO               │                                ││
│  │                     └─────────────────────────┘                                ││
│  │                                                                                ││
│  └────────────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       ETAPA 5: RESOLUÇÃO DO VALE PALLET                             │
│                                                                                     │
│  ┌────────────────────────────────────────────────────────────────────────────────┐│
│  │                                                                                ││
│  │                     ┌─────────────────────────┐                                ││
│  │                     │      VALE PALLET        │                                ││
│  │                     │   (recebido na Nacom)   │                                ││
│  │                     └───────────┬─────────────┘                                ││
│  │                                 │                                              ││
│  │          ┌──────────────────────┼──────────────────────┐                       ││
│  │          ▼                      ▼                      ▼                       ││
│  │    ┌───────────────┐    ┌───────────────┐    ┌────────────────────┐            ││
│  │    │    COLETA     │    │    VENDA      │    │ COBRANÇA           │            ││
│  │    │               │    │               │    │ (transportadora    │            ││
│  │    │ Agendar       │    │ Cotar venda   │    │ não entregou no    │            ││
│  │    │ coleta com    │    │ para terceiro │    │ prazo)             │            ││
│  │    │ transportadora│    │               │    │                    │            ││
│  │    └───────┬───────┘    └───────┬───────┘    └─────────┬──────────┘            ││
│  │            │                    │                      │                       ││
│  │            ▼                    ▼                      ▼                       ││
│  │    ┌───────────────┐    ┌───────────────┐    ┌────────────────────┐            ││
│  │    │ Registrar     │    │ Emitir NF     │    │ Emitir NF venda    │            ││
│  │    │ custo_coleta  │    │ de venda      │    │ p/ transportadora  │            ││
│  │    └───────┬───────┘    └───────┬───────┘    └─────────┬──────────┘            ││
│  │            │                    │                      │                       ││
│  │            └────────────────────┼──────────────────────┘                       ││
│  │                                 ▼                                              ││
│  │                     ┌─────────────────────────┐                                ││
│  │                     │   VALE RESOLVIDO        │                                ││
│  │                     │   resolvido = True      │                                ││
│  │                     │   nf_resolucao = NF     │                                ││
│  │                     │   valor_resolucao = R$  │                                ││
│  │                     └─────────────────────────┘                                ││
│  │                                                                                ││
│  └────────────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ENTIDADES DO PROCESSO

| Entidade | Tabela | Descrição |
|----------|--------|-----------|
| **Pedido** | `carteira_principal` | Origem da demanda |
| **Separação** | `separacoes` | Pedidos agrupados para expedição |
| **Embarque** | `embarques` | Agrupamento de separações + cotação frete |
| **EmbarqueItem** | `embarque_itens` | Itens individuais do embarque |
| **Transportadora** | `transportadoras` | Responsável pelo transporte (campo: `nao_aceita_nf_pallet`) |
| **Cliente** | `contatos_agendamento` | Destinatário final (campo aceita NF a definir) |
| **NF Venda** | Odoo `account.move` | NF de venda da mercadoria |
| **NF Remessa Pallet** | Odoo `account.move` + `MovimentacaoEstoque` | NF de remessa tipo vasilhame |
| **Vale Pallet** | `vale_pallets` | Documento de direito sobre pallets |
| **Movimentação** | `movimentacao_estoque` | Controle de saldo devedor/credor |

---

## TIPOS DE MOVIMENTAÇÃO

### SAÍDAS (Aumentam saldo devedor)

| Tipo | Descrição | Impacto |
|------|-----------|---------|
| **REMESSA** | NF de remessa de vasilhame emitida | ➕ Soma ao saldo devedor automaticamente |
| **VENDA** | NF de venda de pallet (baixa) | ➖ Reduz do saldo (vinculado manualmente) |

### ENTRADAS (Reduzem saldo devedor)

| Tipo | Descrição | Impacto |
|------|-----------|---------|
| **DEVOLUÇÃO** | Cliente emite NF de devolução | ➖ Reduz automaticamente |
| **CANCELAMENTO** | NF de remessa cancelada (prazo OK) | ➖ Reduz automaticamente |
| **RECUSA** | NF retornou recusada | ➖ Reduz automaticamente |
| **COMPRA** | Compra de pallets novos | ❌ Não afeta saldo devedor (só estoque próprio) |

---

## TRATATIVAS DA NF DE REMESSA

| Tratativa | Quando Ocorre | Ação no Sistema | Impacto no Saldo |
|-----------|---------------|-----------------|------------------|
| **CANCELAMENTO** | Pallet devolvido no ato, dentro do prazo | Cancelar NF, registrar motivo | ➖ Reduz |
| **DEVOLUÇÃO** | Cliente deu entrada na NF e devolveu depois | Importar NF devolução do Odoo | ➖ Reduz |
| **RECUSA** | NF não entrou no cliente | Importar retorno do Odoo | ➖ Reduz |
| **SUBSTITUIÇÃO** | NF emitida p/ transp., mas cliente precisa de NF específica | Relacionar NF cliente à NF transp. | ⚠️ Não duplica (consome) |
| **VENDA** | Transformar remessa em cobrança | Emitir NF venda, baixar remessa | ➖ Reduz (manual) |

---

## PONTOS PARA REVISÃO

### ❓ Dúvidas a Esclarecer

1. **Quando transportadora E cliente não aceitam NF**: O que acontece? (linha não definida no fluxo)
2. **Substituição**: Como implementar o "consumo" da NF da transportadora pela NF do cliente?
3. **Campo aceita NF do cliente**: Qual tabela/campo em `contatos_agendamento`?
4. **FK NF Pallet**: Garantir que o ProcessadorFaturamento crie a FK corretamente

### ✅ Já Implementado

- ValePallet com ciclo de vida completo
- MovimentacaoEstoque com tipos REMESSA/ENTRADA/SAIDA
- Sincronização com Odoo (importação)
- Emissão de NF de pallet no Odoo
- Controle de prazos (7 dias SP/RED, 30 dias outros)

### ⚠️ Implementação Parcial

- Tratativas de NF (não há interface específica)
- Substituição de NF (não há lógica de "consumo")
- Vinculação FK em todos os pontos de preenchimento

---

---

# REVISÃO DETALHADA - ETAPA 1: FATURAMENTO

## Contexto
Esta etapa ocorre no momento do faturamento, após a separação física e contagem de pallets.

## Fluxo de Decisão

```
┌─────────────────────────────────────────────────────────────────┐
│ PONTO DE ENTRADA: Embarque pronto para faturar                 │
│ Pallets já foram contados (qtd_pallets_separados)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ DECISÃO 1: Transportador trouxe pallets para troca?            │
│                                                                 │
│ Campo: Embarque.qtd_pallets_trazidos                           │
│                                                                 │
│ • SIM (qtd_trazidos >= qtd_separados) → Sem NF de pallet       │
│ • NÃO (qtd_trazidos < qtd_separados) → Próxima decisão         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (quando NÃO)
┌─────────────────────────────────────────────────────────────────┐
│ DECISÃO 2: Transportador aceita NF de pallet?                  │
│                                                                 │
│ Campo: Transportadora.nao_aceita_nf_pallet = False             │
│                                                                 │
│ • SIM (aceita) → Emitir NF para TRANSPORTADORA                 │
│ • NÃO (não aceita) → Próxima decisão                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (quando NÃO aceita)
┌─────────────────────────────────────────────────────────────────┐
│ DECISÃO 3: Cliente aceita NF de pallet?                        │
│                                                                 │
│ Campo: contatos_agendamento.??? (A DEFINIR)                    │
│                                                                 │
│ • SIM (aceita) → Emitir NF para CLIENTE                        │
│ • NÃO (não aceita) → EMBARCAR SEM NF (troca obrigatória)       │
└─────────────────────────────────────────────────────────────────┘
```

## Pontos Validados - Etapa 1

| # | Ponto | Resposta | Status |
|---|-------|----------|--------|
| 1.1 | **Campo aceita NF cliente** | `contatos_agendamento.nao_aceita_nf_pallet` (Boolean) | ✅ VALIDADO |
| 1.2 | **Troca parcial** | NF emitida pela **DIFERENÇA** (qtd_separados - qtd_trazidos) | ✅ VALIDADO |
| 1.3 | **NF no Embarque** | Sim, pode ter 1 NF para todo o Embarque | ✅ VALIDADO |
| 1.4 | **NF no EmbarqueItem** | Sim, pode ter NF individual por EmbarqueItem | ✅ VALIDADO |
| 1.5 | **Hierarquia NF** | NF em EmbarqueItem **SOBRESCREVE** a do Embarque para aquele item | ✅ VALIDADO |
| 1.6 | **FK obrigatória** | Sim, FK entre NF pallet e NF venda é **OBRIGATÓRIA** | ✅ VALIDADO |
| 1.7 | **Embarque sem NF** | **NÃO REGISTRAR** - Sem NF, sem controle de pallet | ✅ VALIDADO |

## Regras de Negócio Consolidadas - Etapa 1

### Decisão de Emissão de NF de Pallet

```python
# Pseudocódigo da lógica de decisão
qtd_a_emitir = embarque.qtd_pallets_separados - embarque.qtd_pallets_trazidos

if qtd_a_emitir <= 0:
    # Troca no ato - sem emissão de NF
    return None

if not transportadora.nao_aceita_nf_pallet:
    # Transportadora aceita NF
    return emitir_nf_para_transportadora(qtd_a_emitir)

if not cliente.nao_aceita_nf_pallet:
    # Cliente aceita NF
    return emitir_nf_para_cliente(qtd_a_emitir)

# Ninguém aceita NF - embarcar sem NF (troca no ato obrigatória)
# NÃO REGISTRAR - sem NF, sem controle de pallet para este embarque
return None
```

### Hierarquia de NFs de Pallet

```
┌────────────────────────────────────────────────────────────────┐
│                        EMBARQUE                                │
│  nf_pallet_transportadora = "12345"  (NF para todo embarque)   │
│  qtd_pallet_transportadora = 50                                │
│                                                                │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐│
│  │  EmbarqueItem 1  │ │  EmbarqueItem 2  │ │  EmbarqueItem 3  ││
│  │  nf_pallet=NULL  │ │  nf_pallet=NULL  │ │  nf_pallet=67890 ││
│  │  (usa NF 12345)  │ │  (usa NF 12345)  │ │  (usa NF 67890)  ││
│  │                  │ │                  │ │  (sobrescreveu)  ││
│  └──────────────────┘ └──────────────────┘ └──────────────────┘│
└────────────────────────────────────────────────────────────────┘

Resultado:
- EmbarqueItem 1 → FK com NF 12345 (herdou do Embarque)
- EmbarqueItem 2 → FK com NF 12345 (herdou do Embarque)
- EmbarqueItem 3 → FK com NF 67890 (específica do item)
```

---

# REVISÃO DETALHADA - ETAPA 2: RESPONSABILIDADE E PRAZOS

## Contexto
Após a emissão da NF de pallet, define-se quem é responsável pelo retorno e os prazos de cobrança.

## Fluxo de Responsabilidade

```
┌─────────────────────────────────────────────────────────────────┐
│              NF DE PALLET EMITIDA                               │
└─────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
┌──────────────────────────┐      ┌──────────────────────────┐
│ NF p/ TRANSPORTADORA     │      │ NF p/ CLIENTE            │
│                          │      │                          │
│ • Responsável: Transp.   │      │ • Responsável: Cliente   │
│ • Prazo SP/RED: 7 dias   │      │ • Prazo: N/A (?)         │
│ • Prazo outros: 30 dias  │      │                          │
│                          │      │ • Cliente dá entrada     │
│ • Se não retornar no     │      │   na NF                  │
│   prazo → COBRANÇA       │      │ • Pode devolver no ato   │
│                          │      │   OU assinar canhoto     │
│ • Resp. encerra quando   │      │   OU emitir vale pallet  │
│   entrega:               │      │                          │
│   - Pallets físicos      │      │                          │
│   - Vale pallet          │      │                          │
│   - Canhoto assinado     │      │                          │
└──────────────────────────┘      └──────────────────────────┘
```

## Pontos Validados - Etapa 2

| # | Ponto | Resposta | Status |
|---|-------|----------|--------|
| 2.1 | **Prazo cliente** | **NÃO** - Cliente não tem prazo de cobrança (apenas validade do vale) | ✅ VALIDADO |
| 2.2 | **Prazo por UF** | **SIM** - 7 dias para SP/RED, 30 dias para outros | ✅ VALIDADO |
| 2.3 | **Cobrança transp.** | **EMITIR NF DE VENDA** - Transformar remessa em cobrança | ✅ VALIDADO |
| 2.4 | **Entrega parcial** | Criar vale com qtd entregue → vale baixa parcial/totalmente a NF | ✅ VALIDADO |
| 2.5 | **Responsabilidade FK** | **SIM** - `MovimentacaoEstoque.tipo_destinatario` + `cnpj_destinatario` | ✅ VALIDADO |
| 2.6 | **Transf. responsabilidade** | **NACOM ASSUME** - Quando recebe canhoto/vale, Nacom fica responsável por resolver | ✅ VALIDADO |

## Regras de Negócio Consolidadas - Etapa 2

### Fluxo de Responsabilidade Atualizado

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     NF DE PALLET EMITIDA                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│   NF p/ TRANSPORTADORA        │   │   NF p/ CLIENTE               │
│                               │   │                               │
│   • Resp: Transportadora      │   │   • Resp: Cliente (NF)        │
│   • Prazo: 7d (SP/RED) ou 30d │   │   • Prazo vale: N/A           │
│                               │   │                               │
│   TRANSPORTADORA DEVE:        │   │   TRANSPORTADORA AINDA DEVE:  │
│   ┌─────────────────────────┐ │   │   ┌─────────────────────────┐ │
│   │ 1. Entregar pallet      │ │   │   │ Entregar vale/canhoto   │ │
│   │    físico               │ │   │   │ (Mesmo prazo: 7d/30d)   │ │
│   │    OU                   │ │   │   │                         │ │
│   │ 2. Entregar vale/canhoto│ │   │   │ DIFERENÇA:              │ │
│   │    (se cliente não      │ │   │   │ Não precisa entregar    │ │
│   │    devolveu no ato)     │ │   │   │ pallet físico - apenas  │ │
│   └─────────────────────────┘ │   │   │ o documento             │ │
│                               │   │   └─────────────────────────┘ │
│   Se não retornar no prazo:   │   │                               │
│   → EMITIR NF DE VENDA        │   │   Se não retornar no prazo:   │
│                               │   │   → EMITIR NF DE VENDA        │
│   Se retornar vale/canhoto:   │   │                               │
│   → NACOM ASSUME resolução    │   │   Se retornar vale/canhoto:   │
│                               │   │   → NACOM ASSUME resolução    │
└───────────────────────────────┘   └───────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  IMPORTANTE: A única diferença entre NF p/ Transportadora e NF p/ Cliente:     │
│                                                                                 │
│  • NF p/ Transportadora: Transp. deve entregar PALLET FÍSICO ou VALE/CANHOTO   │
│  • NF p/ Cliente: Transp. deve entregar apenas o VALE/CANHOTO (sem pallet)     │
│                                                                                 │
│  A COBRANÇA sobre o vale/canhoto é IGUAL nos dois casos!                        │
│  Prazo e responsabilidade da transportadora pelo DOCUMENTO permanecem.          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Prazo de Cobrança da Transportadora

```python
# Cálculo do prazo (app/pallet/utils.py)
PRAZO_COBRANCA_SP_RED = 7    # dias
PRAZO_COBRANCA_OUTROS = 30   # dias

def calcular_prazo_cobranca(uf, rota):
    if uf == 'SP' or rota == 'RED':
        return PRAZO_COBRANCA_SP_RED
    return PRAZO_COBRANCA_OUTROS
```

---

# REVISÃO DETALHADA - ETAPA 3: RESOLUÇÃO DA NF DE REMESSA

## Contexto
A NF de remessa de pallet pode ser resolvida de 5 formas diferentes, cada uma com impacto específico no saldo devedor.

## Fluxo de Tratativas

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        NF DE REMESSA DE PALLET                                      │
│                        (tipo_movimentacao = REMESSA)                                │
│                        (saldo devedor ATIVO)                                        │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │               │               │               │               │
        ▼               ▼               ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ CANCELAMENTO│ │  DEVOLUÇÃO  │ │   RECUSA    │ │SUBSTITUIÇÃO │ │    VENDA    │
│             │ │             │ │             │ │             │ │             │
│ Pallet      │ │ Cliente     │ │ NF retornou │ │ NF cliente  │ │ Não retornou│
│ devolvido   │ │ emite NF    │ │ recusada    │ │ "consome"   │ │ no prazo    │
│ no ato      │ │ devolução   │ │ (não entrou)│ │ NF transp.  │ │             │
│             │ │             │ │             │ │             │ │             │
│ Prazo: OK   │ │ Entrada no  │ │ Importação  │ │ Vinculação  │ │ Emitir NF   │
│ (cancelável)│ │ Odoo        │ │ automática  │ │ manual      │ │ de venda    │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │               │               │
       ▼               ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     SALDO DEVEDOR REDUZIDO                                          │
│                     (MovimentacaoEstoque.baixado = True)                            │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Detalhamento de Cada Tratativa

### 1. CANCELAMENTO

| Aspecto | Descrição |
|---------|-----------|
| **Quando ocorre** | Pallet devolvido (pode ser no ato da entrega) |
| **Prazo** | **Dentro de 24h** da emissão da NF |
| **Ação** | Cancelar NF de remessa no Odoo |
| **Campo motivo** | Registrar "Devolução de pallets" |
| **Impacto saldo** | ➖ Reduz automaticamente |
| **Origem** | Manual (usuário cancela) |
| **Diferencial** | Mais simples - menos burocracia |

### 2. DEVOLUÇÃO

| Aspecto | Descrição |
|---------|-----------|
| **Quando ocorre** | Pallet devolvido (pode ser no ato da entrega) |
| **Prazo** | **Após 24h** - NF já foi aceita/entrou no cliente |
| **Documento** | NF de devolução emitida pelo cliente referenciando NF remessa |
| **Ação** | Importar NF devolução do Odoo |
| **Impacto saldo** | ➖ Reduz automaticamente |
| **Origem** | Sincronização Odoo (automático) |
| **Diferencial** | Mais burocrático - cliente precisa emitir NF |

### 3. RECUSA

| Aspecto | Descrição |
|---------|-----------|
| **Quando ocorre** | Pallet devolvido (pode ser no ato da entrega) |
| **Prazo** | Qualquer momento - cliente não deu entrada na NF |
| **Documento** | Evento de recusa no SEFAZ (registrado no Odoo) |
| **Ação** | Importar retorno/recusa do Odoo |
| **Impacto saldo** | ➖ Reduz automaticamente |
| **Origem** | Sincronização Odoo (automático) |
| **Diferencial** | NF não entrou - cliente recusou formalmente |

### Diferença entre as 3 tratativas

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│               PALLET DEVOLVIDO (pode ser no ato ou depois)                         │
│                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                             │  │
│  │  CANCELAMENTO        DEVOLUÇÃO               RECUSA                         │  │
│  │  ───────────         ─────────               ──────                         │  │
│  │  Prazo: <24h         Prazo: >24h             Prazo: N/A                     │  │
│  │  NF: Cancelada       NF: Ativa + NF Dev.     NF: Recusada (evento SEFAZ)    │  │
│  │  Cliente: Não deu    Cliente: Deu entrada    Cliente: Não deu entrada       │  │
│  │  entrada             na NF                   (recusou formalmente)          │  │
│  │                                                                             │  │
│  │  Burocracia: BAIXA   Burocracia: ALTA        Burocracia: MÉDIA              │  │
│  │  (só cancelar)       (cliente emite NF)      (evento SEFAZ)                 │  │
│  │                                                                             │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### 4. SUBSTITUIÇÃO

| Aspecto | Descrição |
|---------|-----------|
| **Quando ocorre** | NF emitida para transportadora, mas cliente precisa de NF específica |
| **Exemplo** | Transp. tem NF de 50 pallets, cliente X precisa de NF individual de 10 |
| **Ação** | Emitir NF para cliente E vincular à NF da transportadora |
| **Vinculação** | NF cliente "consome" parte da NF transportadora |
| **Impacto saldo** | ⚠️ NÃO DUPLICA - saldo só existe uma vez |
| **Origem** | Manual (usuário vincula) |

### 5. VENDA

| Aspecto | Descrição |
|---------|-----------|
| **Quando ocorre** | Transportadora não retornou no prazo (7 ou 30 dias) |
| **Ação** | Emitir NF de venda de pallet para transportadora |
| **Vinculação** | NF venda baixa a NF remessa correspondente |
| **Impacto saldo** | ➖ Reduz (vinculação manual) |
| **Origem** | Manual (usuário emite e vincula) |

## Pontos Validados - Etapa 3

| # | Ponto | Resposta | Status |
|---|-------|----------|--------|
| 3.1 | **Cancelamento prazo** | **24 horas** - Prazo padrão do SEFAZ | ✅ VALIDADO |
| 3.2 | **Devolução automática** | **NÃO IMPLEMENTADO** - sync_odoo_service.py não importa devoluções | ⚠️ GAP |
| 3.3 | **Recusa automática** | **NÃO IMPLEMENTADO** - sync_odoo_service.py não importa recusas | ⚠️ GAP |
| 3.4 | **Substituição - lógica** | Vincular NF cliente à NF transp. OU transferir saldo | ⚠️ A IMPLEMENTAR |
| 3.5 | **Substituição - responsabilidade** | **TRANSPORTADORA PERMANECE RESPONSÁVEL** mesmo após substituição | ✅ VALIDADO |
| 3.6 | **Venda - valor** | **R$ 35,00** por pallet | ✅ VALIDADO |

## Regras de Negócio Consolidadas - Etapa 3

### Substituição (Caso Especial)

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                              SUBSTITUIÇÃO                                          │
│                                                                                    │
│  Cenário: Transportadora tem NF de 50 pallets (para N clientes)                   │
│           Cliente X precisa de NF específica de 10 pallets                        │
│                                                                                    │
│  ANTES:                              DEPOIS:                                       │
│  ┌────────────────────────┐         ┌────────────────────────┐                    │
│  │ NF 12345 (Transp.)     │         │ NF 12345 (Transp.)     │                    │
│  │ Qtd: 50 pallets        │         │ Qtd: 50 pallets        │ ← Responsável      │
│  │ Resp: Transportadora   │ ───────►│ Resp: Transportadora   │                    │
│  │ Saldo devedor: 50      │         │ Saldo devedor: 40      │ ← Baixou 10        │
│  └────────────────────────┘         └────────────────────────┘                    │
│                                              │                                     │
│                                     ┌────────┴─────────┐                          │
│                                     │ NF 67890 (Cliente)│                          │
│                                     │ Qtd: 10 pallets   │                          │
│                                     │ Vinculada a 12345 │                          │
│                                     │ Resp: TRANSP.     │ ← Continua transp.!     │
│                                     │ Saldo devedor: 10 │                          │
│                                     └───────────────────┘                          │
│                                                                                    │
│  IMPORTANTE: A responsabilidade NUNCA transfere para o cliente na substituição!   │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### Gaps Identificados na Implementação

| Gap | Descrição | Ação Necessária |
|-----|-----------|-----------------|
| 1 | Importação de NFs de devolução | Adicionar método `sincronizar_devolucoes()` |
| 2 | Importação de NFs recusadas | Adicionar método `sincronizar_recusas()` |
| 3 | Vinculação de substituição | Criar campo `nf_remessa_origem` na MovimentacaoEstoque |
| 4 | Manter responsabilidade na substituição | Lógica para manter `cnpj_responsavel` mesmo com `cnpj_destinatario` diferente |

---

# REVISÃO DETALHADA - ETAPA 4: VALE PALLET / CANHOTO

## Contexto
Quando o cliente não devolve os pallets no ato da entrega, ele assina o canhoto ou emite um vale pallet. Este documento representa o direito de recebimento dos pallets.

## Fluxo de Criação do Vale

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     CLIENTE NÃO DEVOLVEU NO ATO                                     │
│                     (NF de pallet foi aceita/entrou)                                │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
            ┌───────────────────────────┴───────────────────────────┐
            ▼                                                       ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│     CANHOTO ASSINADO          │               │       VALE PALLET             │
│                               │               │                               │
│ • Documento: Canhoto da NF    │               │ • Documento: Vale emitido     │
│ • Assinado pelo cliente       │               │   pelo cliente                │
│ • Mais simples                │               │ • Mais formal                 │
│                               │               │                               │
└───────────────────────────────┘               └───────────────────────────────┘
            │                                                       │
            └───────────────────────────┬───────────────────────────┘
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     CRIAR VALE NO SISTEMA (MANUAL)                                  │
│                                                                                     │
│  Campos obrigatórios:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ • nf_pallet: Número da NF de remessa                                        │   │
│  │ • data_emissao: Data do vale/canhoto                                        │   │
│  │ • quantidade: Quantidade de pallets                                         │   │
│  │ • data_validade: Normalmente 1 ano após emissão                            │   │
│  │ • tipo: 'VALE_PALLET' ou 'CANHOTO_ASSINADO'                                │   │
│  │ • cnpj_cliente: CNPJ do cliente que emitiu                                  │   │
│  │ • cnpj_transportadora: CNPJ da transportadora responsável                   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  Campos de controle:                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ • posse_atual: TRANSPORTADORA → NACOM → EM_RESOLUCAO                        │   │
│  │ • pasta_arquivo / aba_arquivo: Local físico do documento                    │   │
│  │ • recebido / recebido_em / recebido_por                                     │   │
│  │ • enviado_coleta / enviado_coleta_em / enviado_coleta_por                   │   │
│  │ • resolvido / resolvido_em / resolvido_por                                  │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Ciclo de Vida do Vale

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           CICLO DE VIDA DO VALE                                  │
│                                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │  PENDENTE   │───►│  RECEBIDO   │───►│EM RESOLUÇÃO │───►│  RESOLVIDO  │       │
│  │             │    │             │    │             │    │             │       │
│  │ posse:      │    │ posse:      │    │ tipo_resol: │    │ resolvido:  │       │
│  │ TRANSP.     │    │ NACOM       │    │ VENDA/COLETA│    │ True        │       │
│  │             │    │             │    │             │    │             │       │
│  │ recebido:   │    │ recebido:   │    │ enviado_    │    │ nf_resolucao│       │
│  │ False       │    │ True        │    │ coleta: True│    │ valor_resol.│       │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘       │
│                                                                                  │
│  Alertas:                                                                        │
│  • VENCIDO: data_validade < hoje                                                │
│  • A VENCER: data_validade dentro de 30 dias                                    │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## Pontos Validados - Etapa 4

| # | Ponto | Resposta | Status |
|---|-------|----------|--------|
| 4.1 | **Tipo do vale** | **NÃO EXISTE** - Criar campo `tipo_vale`: VALE_PALLET, CANHOTO_ASSINADO | ⚠️ GAP |
| 4.2 | **Validade padrão** | **VARIÁVEL** - Preenchida manualmente conforme negociação | ✅ VALIDADO |
| 4.3 | **Baixa da NF** | **SIM, AUTOMÁTICA** - Vale baixa NF pela quantidade do vale | ✅ VALIDADO |
| 4.4 | **Rastreabilidade** | FK por `nf_pallet` (String) - vinculação implícita | ✅ VALIDADO |

## Regras de Negócio Consolidadas - Etapa 4

### Múltiplos Vales por NF de Remessa

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                    MÚLTIPLOS VALES POR NF DE REMESSA                               │
│                                                                                    │
│  Cenário: NF 12345 de 50 pallets (transportadora) → clientes A, B, C              │
│                                                                                    │
│  ┌────────────────────────────┐                                                   │
│  │  NF 12345 (Transportadora) │                                                   │
│  │  Qtd original: 50 pallets  │                                                   │
│  │  Saldo atual: 10 pallets   │ ← Baixou 40 com os vales                          │
│  └────────────────────────────┘                                                   │
│            │                                                                       │
│    ┌───────┼───────┬───────────────┐                                              │
│    ▼       ▼       ▼               ▼                                              │
│  ┌─────┐ ┌─────┐ ┌─────┐    ┌────────────┐                                        │
│  │Vale1│ │Vale2│ │Vale3│    │ Saldo aberto│                                       │
│  │15 un│ │20 un│ │5 un │    │ 10 un       │                                       │
│  │Cli A│ │Cli B│ │Cli C│    │ (pendente)  │                                       │
│  └─────┘ └─────┘ └─────┘    └────────────┘                                        │
│                                                                                    │
│  IMPORTANTE:                                                                       │
│  • Cada vale pode ser de um CLIENTE DIFERENTE                                     │
│  • Cada vale baixa PARCIALMENTE a NF de remessa                                   │
│  • A RESPONSABILIDADE permanece com a TRANSPORTADORA                              │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### Gaps Identificados - Etapa 4

| Gap | Descrição | Ação Necessária |
|-----|-----------|-----------------|
| 5 | Campo tipo_vale não existe | Adicionar campo `tipo_vale` no modelo ValePallet |
| 6 | Baixa automática da NF ao criar vale | Implementar trigger/lógica de baixa parcial |

---

# REVISÃO DETALHADA - ETAPA 5: RESOLUÇÃO DO VALE PALLET

## Contexto
Após receber o vale pallet/canhoto, a Nacom deve resolver (coletar os pallets ou vender).

## Fluxo de Resolução

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     VALE PALLET RECEBIDO PELA NACOM                                 │
│                     (posse_atual = 'NACOM', recebido = True)                        │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            ▼                           ▼                           ▼
┌───────────────────────────────┐ ┌───────────────────────────────┐
│           COLETA              │ │            VENDA              │
│                               │ │                               │
│ • Contratar transportadora    │ │ • Cotar com comprador         │
│ • Agendar coleta com cliente  │ │ • Agendar coleta com cliente  │ ← TAMBÉM!
│ • Coletar pallets físicos     │ │ • Coletar pallets físicos     │
│ • Pallets vão para Nacom      │ │ • Pallets vão para comprador  │
│                               │ │ • Negociar valor              │
│ Campos:                       │ │ • Emitir NF venda             │
│ • tipo_resolucao: COLETA      │ │                               │
│ • responsavel_resolucao       │ │ Campos:                       │
│ • valor_resolucao (custo)     │ │ • tipo_resolucao: VENDA       │
│                               │ │ • responsavel_resolucao       │
│                               │ │ • valor_resolucao (receita)   │
│                               │ │ • nf_resolucao                │
└───────────────────────────────┘ └───────────────────────────────┘
            │                           │                           │
            └───────────────────────────┼───────────────────────────┘
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              VALE RESOLVIDO                                         │
│                              (resolvido = True)                                     │
│                                                                                     │
│  → NF de remessa original é BAIXADA                                                │
│  → Saldo devedor ZERADO para aquela NF                                             │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Pontos Validados - Etapa 5

| # | Ponto | Resposta | Status |
|---|-------|----------|--------|
| 5.1 | **Cobrança vs Venda** | **COBRANÇA = VENDA** - Não é tipo separado, é venda para transportadora | ✅ VALIDADO |
| 5.2 | **Custo coleta** | Campo `valor_resolucao` registra custo (coleta) ou valor (venda) | ✅ VALIDADO |
| 5.3 | **Baixa automática** | Ao resolver vale, vale já baixou NF ao ser criado | ✅ VALIDADO |
| 5.4 | **Múltiplos vales** | **SIM** - Uma NF pode ter N vales de clientes diferentes | ✅ VALIDADO |

## Regras de Negócio Consolidadas - Etapa 5

### Tipos de Resolução (Simplificado)

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                    TIPOS DE RESOLUÇÃO DO VALE                                      │
│                                                                                    │
│  tipo_resolucao: PENDENTE | VENDA | COLETA                                        │
│                                                                                    │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐              │
│  │    PENDENTE     │     │      VENDA      │     │     COLETA      │              │
│  │                 │     │                 │     │                 │              │
│  │ • Inicial       │     │ • Venda normal  │     │ • Contratar     │              │
│  │ • Aguardando    │     │ • COBRANÇA da   │     │   transportadora│              │
│  │   resolução     │     │   transportadora│     │ • Coletar físico│              │
│  │                 │     │   (não entregou │     │                 │              │
│  │                 │     │   no prazo)     │     │                 │              │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘              │
│                                                                                    │
│  Campos de resolução:                                                              │
│  • responsavel_resolucao: Empresa compradora/coletora                             │
│  • valor_resolucao: Valor da venda OU custo da coleta                             │
│  • nf_resolucao: NF de venda emitida OU NF de recebimento                         │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

# RESUMO CONSOLIDADO - GAPS E AÇÕES

## Todos os Gaps Identificados

| # | Etapa | Gap | Ação | Prioridade | Status |
|---|-------|-----|------|------------|--------|
| 1 | E3 | Importação de NFs de devolução | Adicionar `sincronizar_devolucoes()` em sync_odoo_service.py | MÉDIA | ✅ IMPLEMENTADO |
| 2 | E3 | Importação de NFs recusadas | Adicionar `sincronizar_recusas()` em sync_odoo_service.py | MÉDIA | ✅ IMPLEMENTADO |
| 3 | E3 | Vinculação de substituição | Criar campo `nf_remessa_origem` na MovimentacaoEstoque | MÉDIA | ✅ IMPLEMENTADO |
| 4 | E3 | Responsabilidade na substituição | Adicionar campo `cnpj_responsavel` separado de `cnpj_destinatario` | MÉDIA | ✅ IMPLEMENTADO |
| 5 | E4 | Campo tipo_vale não existe | Adicionar `tipo_vale` no modelo ValePallet | ALTA | ✅ IMPLEMENTADO |
| 6 | E4 | Baixa automática da NF ao criar vale | Implementar trigger de baixa parcial | ALTA | ✅ IMPLEMENTADO |
| 7 | - | Sincronização no Scheduler | Integrar pallets no scheduler incremental | MÉDIA | ✅ IMPLEMENTADO |

## Arquivos Modificados

| Arquivo | Modificações | Status |
|---------|-------------|--------|
| `app/pallet/models.py` | Campo `tipo_vale` em ValePallet | ✅ FEITO |
| `app/estoque/models.py` | Campos `nf_remessa_origem`, `cnpj_responsavel` | ✅ FEITO |
| `app/pallet/services/sync_odoo_service.py` | Métodos `sincronizar_devolucoes()`, `sincronizar_recusas()` | ✅ FEITO |
| `app/pallet/routes.py` | Lógica de baixa automática ao criar vale | ✅ FEITO |
| `app/scheduler/sincronizacao_incremental_definitiva.py` | Integração de pallets (13º módulo) | ✅ FEITO |

## Status da Revisão por Etapa

| Etapa | Descrição | Status |
|-------|-----------|--------|
| 1 | Faturamento (Emissão de NF) | ✅ REVISADA |
| 2 | Responsabilidade e Prazos | ✅ REVISADA |
| 3 | Resolução da NF de Remessa | ✅ REVISADA |
| 4 | Vale Pallet / Canhoto | ✅ REVISADA |
| 5 | Resolução do Vale | ✅ REVISADA |

---

## PRÓXIMOS PASSOS

1. ✅ Revisão do fluxograma completa
2. ✅ Todas as etapas validadas
3. ✅ Implementação dos gaps concluída:
   - ✅ **ALTA**: Gaps 5, 6 (tipo_vale e baixa automática)
   - ✅ **MÉDIA**: Gaps 1-4 (sincronização e substituição)
   - ✅ **EXTRA**: Gap 7 (integração no scheduler incremental)
4. ⏳ Atualizar o prompt.md com as regras validadas (opcional)

---

## RESUMO EXECUTIVO

Este documento contém o fluxograma completo e validado do processo de controle de pallets da Nacom:

- **Etapa 1**: Decisão de emissão de NF (transp. vs cliente)
- **Etapa 2**: Responsabilidade e prazos (transportadora SEMPRE responsável pelo vale/canhoto)
- **Etapa 3**: Tratativas da NF (Cancelar, Devolver, Recusar, Substituir, Vender)
- **Etapa 4**: Criação e ciclo de vida do Vale Pallet
- **Etapa 5**: Resolução do Vale (Coleta ou Venda)

**7 gaps implementados** - todos concluídos:

| Gap | Implementação |
|-----|---------------|
| tipo_vale | Campo adicionado em ValePallet (VALE_PALLET, CANHOTO_ASSINADO) |
| baixa_automatica | Trigger ao criar vale baixa NF de remessa |
| sincronizar_devolucoes() | Importa NFs de devolução do Odoo |
| sincronizar_recusas() | Importa NFs recusadas/canceladas do Odoo |
| nf_remessa_origem | Campo para vincular substituições |
| cnpj_responsavel | Campo separado de cnpj_destinatario |
| Scheduler | Pallets integrados como 13º módulo (a cada 30min, janela 96h) |
