# Mapeamento: Fluxo de Processo x Telas do Sistema - Pallet

**Data**: 05/01/2026
**Status**: Revisao completa

---

## RESUMO DAS TELAS DISPONIVEIS

| URL | Tela | Proposito |
|-----|------|-----------|
| `/pallet/` | Dashboard | Visao geral: saldos, alertas, ultimos movimentos |
| `/pallet/movimentos` | Lista de Movimentos | Historico de todas as movimentacoes |
| `/pallet/registrar-saida` | Registrar Saida | Saida manual de pallet |
| `/pallet/registrar-retorno` | Registrar Retorno | Retorno manual de pallet |
| `/pallet/baixar/<id>` | Baixar Movimento | Baixar saida vinculando a retorno |
| `/pallet/sync` | Sincronizar Odoo | Importar NFs do Odoo |
| `/pallet/vales` | Lista de Vales | Gestao de vales pallet |
| `/pallet/vales/novo` | Criar Vale | Cadastrar novo vale pallet |
| `/pallet/vales/<id>` | Editar Vale | Editar vale existente |
| `/pallet/vales/<id>/receber` | Receber Vale | Marcar vale como recebido |
| `/pallet/vales/<id>/enviar-resolucao` | Enviar Resolucao | Definir tipo (VENDA/COLETA) |
| `/pallet/vales/<id>/resolver` | Resolver Vale | Finalizar vale |
| `/pallet/vincular-venda/<id>` | Vincular Venda | Vincular NF venda a remessa |

---

## ETAPA 1: FATURAMENTO (Emissao de NF de Pallet)

### Quando Ocorre
No momento do faturamento, apos separacao fisica e contagem de pallets.

### Fluxo de Decisao

```
Transportador trouxe pallets para troca?
├── SIM (qtd_trazidos >= qtd_separados) → SEM NF de pallet
└── NÃO → Transportador aceita NF?
          ├── SIM → Emitir NF p/ TRANSPORTADORA
          └── NÃO → Cliente aceita NF?
                    ├── SIM → Emitir NF p/ CLIENTE
                    └── NÃO → Embarcar SEM NF (troca obrigatoria)
```

### Como o Usuario Registra no Sistema

| Acao | Tela | Campos | Notas |
|------|------|--------|-------|
| **NF emitida automaticamente via Odoo** | - | - | Processador Faturamento emite NF no Odoo |
| **Importar NFs para sistema** | `/pallet/sync` | tipo=remessas, dias | Sincroniza NFs tipo 'vasilhame' |
| **Registrar manualmente** | `/pallet/registrar-saida` | tipo_destinatario, cnpj, quantidade, numero_nf, embarque_id | Usado quando NF nao veio do Odoo |

### Gap Identificado

| Gap | Descricao | Impacto |
|-----|-----------|---------|
| **G1.1** | Nao existe interface para **EMITIR** NF de pallet - apenas importar | Emissao e feita no Odoo manualmente ou via ProcessadorFaturamento |
| **G1.2** | Campo `nao_aceita_nf_pallet` em Transportadora e `contatos_agendamento` nao e consultado automaticamente | Usuario precisa saber previamente se aceita ou nao |

---

## ETAPA 2: RESPONSABILIDADE E PRAZOS

### Quando Ocorre
Apos emissao da NF de pallet - define quem e responsavel e prazo de cobranca.

### Regras de Prazo

| Condicao | Prazo |
|----------|-------|
| UF = SP ou Rota = RED | 7 dias |
| Demais | 30 dias |

### Como o Usuario Acompanha no Sistema

| Acao | Tela | Indicador Visual |
|------|------|------------------|
| **Ver remessas vencidas** | `/pallet/` (Dashboard) | Card vermelho "Remessas Vencidas (> X dias)" |
| **Ver remessas prestes a vencer** | `/pallet/` (Dashboard) | Card amarelo "Remessas Prestes a Vencer (25-30 dias)" |
| **Filtrar por status** | `/pallet/movimentos` | Filtro "Status Baixa" = Pendentes |

### Implementacao no Codigo

```python
# app/pallet/routes.py - funcao calcular_prazo_remessa()
# Busca UF do destinatario e rota do embarque para calcular prazo
```

### Gap Identificado

| Gap | Descricao | Impacto |
|-----|-----------|---------|
| **G2.1** | Alerta de vencimento usa prazo fixo (30 dias) em vez de dinamico (7/30) | Remessas SP/RED podem aparecer como "a vencer" quando ja venceram |
| **G2.2** | Nao existe botao "Cobrar" direto na lista de vencidos | Usuario precisa navegar para emitir NF de venda manualmente |

---

## ETAPA 3: RESOLUCAO DA NF DE REMESSA

### Tipos de Tratativa

| Tratativa | Quando | Acao no Odoo | Como Registrar no Sistema |
|-----------|--------|--------------|---------------------------|
| **CANCELAMENTO** | Pallet devolvido <24h | Cancelar NF | Sync recusas (`/pallet/sync` tipo=recusas) |
| **DEVOLUCAO** | Cliente emite NF devolucao | Cliente emite NF refund | Sync devolucoes (`/pallet/sync` tipo=devolucoes) |
| **RECUSA** | NF nao entrou no cliente | Evento SEFAZ | Sync recusas (`/pallet/sync` tipo=recusas) |
| **SUBSTITUICAO** | NF cliente consome NF transp | Emitir nova NF | Sem interface especifica (manual) |
| **VENDA** | Nao retornou no prazo | Emitir NF venda | Vincular venda (`/pallet/vincular-venda/<id>`) |

### Como o Usuario Registra no Sistema

#### 3.1 Cancelamento/Recusa (Automatico via Sync)

```
1. Acessar: /pallet/sync
2. Selecionar: "Apenas Recusas/Cancelamentos"
3. Clicar: "Iniciar Sincronizacao"
→ Sistema importa NFs canceladas do Odoo e baixa remessas automaticamente
```

#### 3.2 Devolucao (Automatico via Sync)

```
1. Acessar: /pallet/sync
2. Selecionar: "Apenas Devolucoes"
3. Clicar: "Iniciar Sincronizacao"
→ Sistema importa NFs out_refund do Odoo e baixa remessas automaticamente
```

#### 3.3 Venda (Manual - Vincular)

```
1. Dashboard mostra: "Vendas Pendentes de Vinculo"
2. Clicar no icone de link
3. Acessar: /pallet/vincular-venda/<id>
4. Selecionar qual remessa esta venda abate
5. Confirmar
→ Sistema baixa a remessa vinculada
```

#### 3.4 Baixa Manual (Retorno Fisico)

```
1. Acessar: /pallet/movimentos
2. Localizar a REMESSA pendente
3. Clicar no icone de check (Baixar)
4. Acessar: /pallet/baixar/<id>
5. Opcionalmente vincular a um RETORNO
6. Adicionar observacao
7. Confirmar baixa
```

### Gap Identificado

| Gap | Descricao | Impacto |
|-----|-----------|---------|
| **G3.1** | Nao existe interface para SUBSTITUICAO | Usuario precisa fazer manualmente no banco ou Odoo |
| **G3.2** | Vinculo de venda so aparece quando venda e importada | Se venda for manual, nao aparece no alerta |
| **G3.3** | Nao existe botao "Emitir NF de Cobranca" | Usuario precisa ir ao Odoo emitir a NF de venda |

---

## ETAPA 4: VALE PALLET / CANHOTO

### Quando Ocorre
Cliente nao devolveu pallets no ato → assinou canhoto ou emitiu vale.

### Ciclo de Vida do Vale

```
PENDENTE → RECEBIDO → EM RESOLUCAO → RESOLVIDO
   |           |           |             |
   |           |           |             +-- resolvido=True
   |           |           +-- enviado_coleta=True, tipo_resolucao definido
   |           +-- recebido=True, posse_atual=NACOM
   +-- posse_atual=TRANSPORTADORA
```

### Como o Usuario Registra no Sistema

#### 4.1 Criar Vale Pallet

```
1. Acessar: /pallet/vales
2. Clicar: "Novo Vale"
3. Preencher formulario:
   - NF de Pallet: numero da NF de remessa
   - Tipo do Vale: CANHOTO_ASSINADO ou VALE_PALLET
   - Quantidade: quantidade de pallets
   - Data Emissao: data do documento
   - Data Validade: prazo para resolver
   - Cliente: CNPJ e nome de quem emitiu
   - Transportadora: CNPJ e nome responsavel
   - Posse Atual: quem esta com o documento
4. Salvar
→ Sistema verifica se deve baixar a NF de remessa automaticamente
```

#### 4.2 Receber Vale (Transportadora entregou)

```
1. Acessar: /pallet/vales
2. Localizar vale com status PENDENTE
3. Clicar no icone de inbox (Receber)
→ Vale muda para RECEBIDO, posse=NACOM
```

#### 4.3 Editar Vale

```
1. Acessar: /pallet/vales
2. Clicar no icone de lapis (Editar)
3. Acessar: /pallet/vales/<id>
4. Modificar campos desejados
5. Salvar
```

### Baixa Automatica da NF

Quando um vale e criado, o sistema verifica:
- Se a soma de todos os vales >= quantidade da remessa
- Se sim, baixa a remessa automaticamente

```python
# app/pallet/routes.py - funcao baixar_nf_remessa_automaticamente()
```

### Gap Identificado

| Gap | Descricao | Impacto |
|-----|-----------|---------|
| **G4.1** | Nao existe alerta visual quando transportadora atrasa entrega do vale | Usuario precisa verificar manualmente |
| **G4.2** | Campo posse_atual nao tem historico | Nao e possivel rastrear transicoes de posse |

---

## ETAPA 5: RESOLUCAO DO VALE

### Tipos de Resolucao

| Tipo | Descricao | Campos |
|------|-----------|--------|
| **VENDA** | Vender pallets para terceiro (ou cobrar transportadora) | responsavel, valor, nf_resolucao |
| **COLETA** | Coletar pallets fisicamente do cliente | responsavel, valor (custo), nf_resolucao |

### Como o Usuario Registra no Sistema

#### 5.1 Enviar para Resolucao

```
1. Acessar: /pallet/vales
2. Localizar vale RECEBIDO
3. Clicar no icone de aviao (Enviar para Resolucao)
4. Acessar: /pallet/vales/<id>/enviar-resolucao
5. Selecionar tipo: VENDA ou COLETA
6. Preencher:
   - Responsavel pela Resolucao: empresa compradora/coletora
   - CNPJ do Responsavel
   - Valor (venda ou custo coleta)
7. Enviar
→ Vale muda para EM RESOLUCAO
```

#### 5.2 Resolver Vale (Finalizar)

```
1. Acessar: /pallet/vales
2. Localizar vale EM RESOLUCAO
3. Clicar no icone de check (Resolver)
4. Acessar: /pallet/vales/<id>/resolver
5. Preencher:
   - NF de Resolucao: numero da NF emitida
   - Valor Final: valor efetivo
   - Observacao
6. Confirmar
→ Vale muda para RESOLVIDO
→ NF de remessa vinculada e baixada
```

### Gap Identificado

| Gap | Descricao | Impacto |
|-----|-----------|---------|
| **G5.1** | Nao existe integracao para emitir NF de venda automaticamente | Usuario precisa emitir no Odoo e depois registrar aqui |
| **G5.2** | Custo de coleta nao e lancado em nenhum sistema financeiro | Apenas registro informativo |

---

## RESUMO DE GAPS

### Gaps Criticos (Afetam Operacao)

| ID | Etapa | Gap | Sugestao |
|----|-------|-----|----------|
| G1.1 | E1 | Sem interface para emitir NF | Criar botao "Emitir NF Pallet" que chama Odoo |
| G3.1 | E3 | Sem interface para substituicao | Criar tela de vinculo NF cliente → NF transportadora |
| G3.3 | E3 | Sem botao "Emitir Cobranca" | Adicionar acao na lista de vencidos |

### Gaps Moderados (Melhorias)

| ID | Etapa | Gap | Sugestao |
|----|-------|-----|----------|
| G2.1 | E2 | Prazo fixo nos alertas | Calcular prazo dinamico por UF/Rota |
| G2.2 | E2 | Navegacao manual para cobrar | Adicionar botao inline na tabela |
| G4.1 | E4 | Sem alerta de atraso do vale | Adicionar coluna "Dias para Entrega" |

### Gaps Leves (Nice to Have)

| ID | Etapa | Gap | Sugestao |
|----|-------|-----|----------|
| G1.2 | E1 | Campo nao_aceita_nf nao consultado | Mostrar warning ao criar saida |
| G4.2 | E4 | Sem historico de posse | Criar tabela de log de transicoes |
| G5.1 | E5 | Sem integracao NF venda | Integrar com Odoo para emissao |
| G5.2 | E5 | Custo coleta nao lancado | Integrar com contas a pagar |

---

## FLUXO VISUAL DO USUARIO

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DASHBOARD (/pallet/)                                  │
│                                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ Pallets em  │  │ Registrar   │  │ Registrar   │  │ Vale        │           │
│  │ Terceiros   │  │ Saida       │  │ Retorno     │  │ Pallets     │           │
│  └─────────────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘           │
│                          │                │                │                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ ALERTAS: Vencidas | Prestes a Vencer | Vendas Pendentes | Vales Vencidos │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ Saldos por Destinatario (quem deve pallets)                             │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ Ultimos Movimentos                                                       │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────┐          ┌─────────────────┐          ┌─────────────────┐
│ /registrar-   │          │  /movimentos    │          │    /vales       │
│ saida         │          │                 │          │                 │
│               │          │ Filtros:        │          │ Filtros:        │
│ Tipo: Cliente │          │ - Tipo          │          │ - Status        │
│ ou Transp.    │          │ - Destinatario  │          │ - Transportadora│
│               │          │ - Status Baixa  │          │ - Cliente       │
│ CNPJ, Nome    │          │                 │          │                 │
│ NF, Qtd       │          │ Lista paginada  │          │ Lista paginada  │
│ Embarque      │          │ com acoes       │          │ com acoes       │
└───────────────┘          └────────┬────────┘          └────────┬────────┘
                                    │                            │
                                    ▼                            ▼
                           ┌────────────────┐          ┌─────────────────┐
                           │ /baixar/<id>   │          │ /vales/<id>     │
                           │                │          │                 │
                           │ Vincular       │          │ Receber →       │
                           │ retorno        │          │ Enviar Resol →  │
                           │ (opcional)     │          │ Resolver →      │
                           └────────────────┘          └─────────────────┘
```

---

## SCHEDULER (Automatico)

O scheduler executa a cada 30 minutos:
- Sincroniza remessas, vendas, devolucoes e recusas
- Janela de 96 horas (mesmo que faturamento)
- Configuracao: `JANELA_PALLET = 5760` (minutos)

Nao requer acao do usuario.

---

## PROXIMOS PASSOS SUGERIDOS

1. **Prioridade ALTA**: Implementar G3.1 (interface de substituicao)
2. **Prioridade ALTA**: Implementar G3.3 (botao "Emitir Cobranca")
3. **Prioridade MEDIA**: Corrigir G2.1 (prazo dinamico nos alertas)
4. **Prioridade BAIXA**: Demais melhorias de UX
