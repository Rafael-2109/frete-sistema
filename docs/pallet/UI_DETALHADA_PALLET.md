# Documentacao Detalhada da UI - Modulo Pallet

**Data**: 05/01/2026
**Versao**: 1.0

---

## SUMARIO

1. [Dashboard](#1-dashboard)
2. [Movimentos](#2-movimentos)
3. [Registrar Saida](#3-registrar-saida)
4. [Registrar Retorno](#4-registrar-retorno)
5. [Baixar Movimento](#5-baixar-movimento)
6. [Sincronizar Odoo](#6-sincronizar-odoo)
7. [Vale Pallets](#7-vale-pallets)
8. [Criar/Editar Vale](#8-criareditar-vale)
9. [Receber Vale](#9-receber-vale)
10. [Enviar para Resolucao](#10-enviar-para-resolucao)
11. [Resolver Vale](#11-resolver-vale)
12. [Vincular Venda](#12-vincular-venda)

---

## 1. DASHBOARD

**URL**: `/pallet/`
**Arquivo Template**: `app/templates/pallet/index.html`
**Rota**: `pallet_bp.route('/')` - funcao `index()`

### 1.1 Cabecalho

| Elemento | Tipo | Texto/Icone | Acao |
|----------|------|-------------|------|
| Titulo | h2 | "Gestao de Pallet" | - |
| Botao Sync | a.btn-outline-primary | "Sincronizar Odoo" | `url_for('pallet.sincronizar_odoo')` |

### 1.2 Cards de Resumo (Linha 1)

| Card | Cor | Valor | Texto | Acao ao Clicar |
|------|-----|-------|-------|----------------|
| Pallets em Terceiros | bg-primary | `{{ total_em_terceiros }}` | "Pallets em Terceiros" | - (somente informativo) |
| Registrar Saida | bg-success | icone + texto | "Registrar Saida" | `url_for('pallet.registrar_saida')` |
| Registrar Retorno | bg-warning | icone + texto | "Registrar Retorno" | `url_for('pallet.registrar_retorno')` |
| Vale Pallets | bg-info | icone + badge | "Vale Pallets" + badge com `vales_pendentes` | `url_for('pallet.listar_vales')` |

### 1.3 Alertas (Condicional)

#### 1.3.1 Remessas Vencidas
**Condicao**: `{% if remessas_vencidas %}`

| Coluna | Campo | Formato |
|--------|-------|---------|
| NF | `rem.numero_nf` | texto bold |
| Data | `rem.data_movimentacao` | dd/mm/yyyy (classe text-danger) |
| Destinatario | `rem.nome_destinatario` ou `rem.cnpj_destinatario` | texto |
| Qtd | `rem.qtd_movimentacao|int` | numero centralizado |

**Limite**: Mostra ate 5 itens + indicador "+X mais..."

#### 1.3.2 Remessas Prestes a Vencer
**Condicao**: `{% if remessas_prestes_vencer %}`
**Titulo**: "Remessas Prestes a Vencer (25-30 dias)"
**Campos**: Identicos ao anterior, classe text-warning na data

#### 1.3.3 Vendas Pendentes de Vinculo
**Condicao**: `{% if vendas_pendentes_vinculo %}`

| Coluna | Campo | Acao |
|--------|-------|------|
| NF | `venda.numero_nf` | - |
| Data | `venda.data_movimentacao` | - |
| Comprador | `venda.nome_destinatario` | - |
| Qtd | `venda.qtd_movimentacao|int` | - |
| Acao | Botao link | `url_for('pallet.vincular_venda', movimento_id=venda.id)` |

#### 1.3.4 Vales Vencidos
**Condicao**: `{% if vales_vencidos > 0 %}`
**Acao do Link**: `url_for('pallet.listar_vales', status='VENCIDO')`

### 1.4 Tabela Saldos por Destinatario

| Coluna | Campo | Formato |
|--------|-------|---------|
| Tipo | `saldo.tipo_destinatario` | badge (bg-info se TRANSPORTADORA, bg-secondary se outro) |
| CNPJ | `saldo.cnpj_destinatario` | texto |
| Nome | `saldo.nome_destinatario` | texto |
| Saldo | `saldo.saldo` | numero bold alinhado direita |
| Acoes | Botao olho | `url_for('pallet.listar_movimentos', ...)` |

### 1.5 Tabela Ultimos Movimentos

| Coluna | Campo | Formato |
|--------|-------|---------|
| Data | `mov.criado_em` | dd/mm/yyyy HH:MM |
| Tipo | `mov.tipo_movimentacao` | badge (REMESSA=warning, SAIDA=danger, outros=success) |
| Destinatario | tipo + nome/cnpj | small + texto |
| NF | `mov.numero_nf` | texto |
| Qtd | `mov.qtd_movimentacao|int` | numero bold |
| Status | baixado? | badge (Baixado=success, Pendente=warning) |

---

## 2. MOVIMENTOS

**URL**: `/pallet/movimentos`
**Arquivo Template**: `app/templates/pallet/movimentos.html`
**Rota**: `pallet_bp.route('/movimentos')` - funcao `listar_movimentos()`

### 2.1 Cabecalho

| Elemento | Tipo | Texto | Acao |
|----------|------|-------|------|
| Titulo | h2 | "Movimentos de Pallet" | - |
| Nova Saida | a.btn-success | "Nova Saida" | `url_for('pallet.registrar_saida')` |
| Novo Retorno | a.btn-warning | "Novo Retorno" | `url_for('pallet.registrar_retorno')` |
| Dashboard | a.btn-outline-secondary | "Dashboard" | `url_for('pallet.index')` |

### 2.2 Filtros

| Campo | Nome | Tipo | Opcoes |
|-------|------|------|--------|
| Tipo Movimento | `tipo` | select | Todos, SAIDA, RETORNO |
| Tipo Destinatario | `destinatario` | select | Todos, CLIENTE, TRANSPORTADORA |
| Status Baixa | `baixado` | select | Todos, Pendentes (nao), Baixados (sim) |
| Botao Filtrar | - | button | submit |
| Botao Limpar | - | a | `url_for('pallet.listar_movimentos')` |

### 2.3 Tabela de Movimentos

| Coluna | Campo | Acao |
|--------|-------|------|
| ID | `mov.id` | - |
| Data | `mov.criado_em` | - |
| Tipo | badge | - |
| Destinatario | tipo + cnpj + nome | - |
| NF | `mov.numero_nf` | - |
| Qtd | `mov.qtd_movimentacao|int` | - |
| Status | Baixado/Pendente | - |
| Embarque | link para embarque | - |
| Acoes | Botao Baixar | `url_for('pallet.baixar_movimento', movimento_id=mov.id)` (se SAIDA e nao baixado) |

---

## 3. REGISTRAR SAIDA

**URL**: `/pallet/registrar-saida`
**Arquivo Template**: `app/templates/pallet/registrar_saida.html`
**Rota**: `pallet_bp.route('/registrar-saida')` - funcao `registrar_saida()`
**Metodos**: GET, POST

### 3.1 Cabecalho

| Elemento | Tipo | Texto | Acao |
|----------|------|-------|------|
| Titulo | h2 | "Registrar Saida de Pallet" | - |
| Voltar | a.btn-outline-secondary | "Voltar" | `url_for('pallet.index')` |

### 3.2 Formulario

| Campo | Nome | Tipo | Obrigatorio | Validacao |
|-------|------|------|-------------|-----------|
| Tipo Destinatario | `tipo_destinatario` | radio (btn-group) | Sim | CLIENTE (default checked) ou TRANSPORTADORA |
| CNPJ | `cnpj_destinatario` | text | Sim | placeholder "00.000.000/0000-00" |
| Nome/Razao Social | `nome_destinatario` | text | Nao | - |
| Numero da NF | `numero_nf` | text | Nao | - |
| Quantidade | `quantidade` | number | Sim | min=1, default=1 |
| Embarque | `embarque_id` | select | Nao | Lista de embarques ativos |
| Item Embarque | `embarque_item_id` | select | Nao | Carregado via API, visivel se tipo=CLIENTE |
| Observacao | `observacao` | textarea | Nao | rows=2 |

### 3.3 Botoes

| Botao | Tipo | Texto | Acao |
|-------|------|-------|------|
| Cancelar | a.btn-secondary | "Cancelar" | `url_for('pallet.index')` |
| Registrar Saida | button.btn-success | "Registrar Saida" | submit |

### 3.4 JavaScript

- Ao selecionar embarque: carrega itens via `/pallet/api/embarque/{id}/itens`
- Mostra campo Item Embarque apenas se tipo=CLIENTE
- Itens que nao aceitam NF pallet sao desabilitados

---

## 4. REGISTRAR RETORNO

**URL**: `/pallet/registrar-retorno`
**Arquivo Template**: `app/templates/pallet/registrar_retorno.html`
**Rota**: `pallet_bp.route('/registrar-retorno')` - funcao `registrar_retorno()`
**Metodos**: GET, POST

### 4.1 Layout

Duas colunas:
- Esquerda (col-md-7): Formulario
- Direita (col-md-5): Saldos Pendentes

### 4.2 Formulario

| Campo | Nome | Tipo | Obrigatorio | Default |
|-------|------|------|-------------|---------|
| Tipo Destinatario | `tipo_destinatario` | radio | Sim | TRANSPORTADORA (checked) |
| CNPJ | `cnpj_destinatario` | text | Sim | - |
| Nome/Razao Social | `nome_destinatario` | text | Nao | - |
| Numero da NF de Retorno | `numero_nf` | text | Nao | - |
| Quantidade | `quantidade` | number | Sim | min=1, default=1 |
| Observacao | `observacao` | textarea | Nao | rows=2 |

### 4.3 Painel Saldos Pendentes

Lista clicavel com:
- Badge tipo (TRANSPORTADORA ou CLIENTE)
- Nome ou CNPJ
- Saldo (badge warning)

**Acao ao clicar**: Preenche CNPJ, Nome e seleciona Tipo no formulario

### 4.4 Botoes

| Botao | Tipo | Texto |
|-------|------|-------|
| Cancelar | a.btn-secondary | "Cancelar" |
| Registrar Retorno | button.btn-warning | "Registrar Retorno" |

---

## 5. BAIXAR MOVIMENTO

**URL**: `/pallet/baixar/<int:movimento_id>`
**Arquivo Template**: `app/templates/pallet/baixar_movimento.html`
**Rota**: `pallet_bp.route('/baixar/<int:movimento_id>')` - funcao `baixar_movimento()`
**Metodos**: GET, POST

### 5.1 Layout

Duas colunas:
- Esquerda (col-md-6): Detalhes da Saida + Formulario
- Direita (col-md-6): Retornos Disponiveis

### 5.2 Card Detalhes da Saida

| Campo | Valor |
|-------|-------|
| Data | `saida.criado_em` |
| Tipo Destinatario | badge |
| CNPJ | `saida.cnpj_destinatario` |
| Nome | `saida.nome_destinatario` |
| NF | `saida.numero_nf` |
| Quantidade | `saida.qtd_movimentacao` (grande, vermelho) |
| Embarque | link se existir |
| Observacao | `saida.observacao` |

### 5.3 Formulario de Baixa

| Campo | Nome | Tipo | Obrigatorio |
|-------|------|------|-------------|
| Vincular a Retorno | `retorno_id` | select | Nao |
| Observacao da Baixa | `observacao_baixa` | textarea | Nao |

**Opcoes do Select Retorno**:
- "Sem vinculo - Baixa manual"
- Lista de retornos recentes (id, data, nome, quantidade)

### 5.4 Botoes

| Botao | Tipo | Texto |
|-------|------|-------|
| Cancelar | a.btn-secondary | "Cancelar" |
| Confirmar Baixa | button.btn-success | "Confirmar Baixa" |

---

## 6. SINCRONIZAR ODOO

**URL**: `/pallet/sync`
**Arquivo Template**: `app/templates/pallet/sincronizar.html`
**Rota**: `pallet_bp.route('/sync')` - funcao `sincronizar_odoo()`
**Metodos**: GET, POST

### 6.1 Cards Explicativos

| Card | Cor | Icone | Titulo | Descricao |
|------|-----|-------|--------|-----------|
| Remessas | border-warning | truck-loading | "Remessas" | NFs tipo 'vasilhame', tipo_movimentacao = 'REMESSA' |
| Vendas | border-success | dollar-sign | "Vendas" | Produto PALLET, tipo_movimentacao = 'SAIDA' |
| Devolucoes | border-info | undo | "Devolucoes" | NFs de reembolso, tipo_movimentacao = 'DEVOLUCAO' |
| Recusas | border-danger | times-circle | "Recusas" | NFs canceladas, status_nf = 'CANCELADO' |

### 6.2 Formulario

| Campo | Nome | Tipo | Opcoes |
|-------|------|------|--------|
| Tipo de Sincronizacao | `tipo` | select | tudo (selected), remessas, vendas, devolucoes, recusas |
| Periodo (dias) | `dias` | number | min=1, max=365, default=30 |

### 6.3 Nota Informativa

Alert info: "A sincronizacao nao duplica registros. NFs ja importadas serao ignoradas. Devolucoes e recusas baixam automaticamente as remessas correspondentes."

### 6.4 Botoes

| Botao | Tipo | Texto | Acao |
|-------|------|-------|------|
| Voltar | a.btn-secondary | "Voltar" | `url_for('pallet.index')` |
| Iniciar | button.btn-primary | "Iniciar Sincronizacao" | submit |

---

## 7. VALE PALLETS

**URL**: `/pallet/vales`
**Arquivo Template**: `app/templates/pallet/vale_pallets.html`
**Rota**: `pallet_bp.route('/vales')` - funcao `listar_vales()`

### 7.1 Cabecalho

| Elemento | Tipo | Texto | Acao |
|----------|------|-------|------|
| Titulo | h2 | "Vale Pallets" | - |
| Voltar | a.btn-outline-secondary | "Voltar" | `url_for('pallet.index')` |
| Novo Vale | a.btn-success | "Novo Vale" | `url_for('pallet.criar_vale')` |

### 7.2 Cards de Estatisticas

| Card | Valor | Texto | Filtro Aplicado | Cor Ativa |
|------|-------|-------|-----------------|-----------|
| Total Abertos | `stats.total` | "Total Abertos" | nenhum | bg-primary |
| Pendentes | `stats.pendentes` | "Pendentes" | status=PENDENTE | bg-warning |
| Recebidos | `stats.recebidos` | "Recebidos" | status=RECEBIDO | bg-info |
| Vencidos | `stats.vencidos` | "Vencidos" | status=VENCIDO | bg-danger |
| A Vencer (30d) | `stats.a_vencer` | "A Vencer (30d)" | status=A_VENCER | bg-warning |
| Resolvidos | icone check | "Resolvidos" | status=RESOLVIDO | bg-success |

### 7.3 Filtros

| Campo | Nome | Tipo |
|-------|------|------|
| Status | `status` | select (onchange=submit) |
| Transportadora | `transportadora` | text |
| Cliente | `cliente` | text |
| Botao Filtrar | - | button |
| Botao Limpar | - | a |

### 7.4 Tabela de Vales

| Coluna | Campo | Formato |
|--------|-------|---------|
| # | `vale.id` | numero |
| NF Pallet | `vale.nf_pallet` | bold |
| Cliente | cnpj + nome | small + texto |
| Transportadora | cnpj + nome | small + texto |
| Qtd | `vale.quantidade` | numero centralizado bold |
| Validade | data + dias restantes | data + small colorido |
| Posse | `vale.posse_atual` | badge (NACOM=success, TRANSP=info) |
| Status | `vale.status_display` | badge colorido |
| Acoes | botoes | ver abaixo |

### 7.5 Botoes de Acao por Vale

| Condicao | Botao | Icone | Acao |
|----------|-------|-------|------|
| Sempre | Editar | edit | `url_for('pallet.editar_vale', vale_id=vale.id)` |
| Se nao recebido | Receber | inbox | POST `url_for('pallet.receber_vale', vale_id=vale.id)` |
| Se recebido e nao resolvido e nao enviado | Enviar | paper-plane | `url_for('pallet.enviar_resolucao', vale_id=vale.id)` |
| Se recebido e nao resolvido | Resolver | check | `url_for('pallet.resolver_vale', vale_id=vale.id)` |
| Se nao resolvido | Excluir | trash | POST `url_for('pallet.excluir_vale', vale_id=vale.id)` (confirm) |

---

## 8. CRIAR/EDITAR VALE

**URL**: `/pallet/vales/novo` ou `/pallet/vales/<int:vale_id>`
**Arquivo Template**: `app/templates/pallet/vale_pallet_form.html`
**Rotas**: `criar_vale()` e `editar_vale()`
**Metodos**: GET, POST

### 8.1 Formulario - Dados do Vale

| Campo | Nome | Tipo | Obrigatorio | Notas |
|-------|------|------|-------------|-------|
| NF de Pallet | `nf_pallet` | text | Sim | Numero da NF de remessa |
| Tipo do Vale | `tipo_vale` | select | Sim | CANHOTO_ASSINADO (default), VALE_PALLET |
| Quantidade | `quantidade` | number | Sim | min=1 |
| Data Emissao | `data_emissao` | date | Sim | - |
| Data Validade | `data_validade` | date | Nao | Padrao: emissao + 30 dias |

### 8.2 Formulario - Cliente que Emitiu

| Campo | Nome | Tipo | Obrigatorio |
|-------|------|------|-------------|
| CNPJ Cliente | `cnpj_cliente` | text | Nao |
| Nome Cliente | `nome_cliente` | text | Nao |

### 8.3 Formulario - Transportadora Responsavel

| Campo | Nome | Tipo | Obrigatorio |
|-------|------|------|-------------|
| CNPJ Transportadora | `cnpj_transportadora` | text | Nao |
| Nome Transportadora | `nome_transportadora` | text | Nao |

### 8.4 Formulario - Posse Atual

| Campo | Nome | Tipo | Opcoes |
|-------|------|------|--------|
| Quem esta com o vale | `posse_atual` | select | TRANSPORTADORA (default), NACOM, CLIENTE |
| CNPJ Posse | `cnpj_posse` | text | - |
| Nome Posse | `nome_posse` | text | - |

### 8.5 Formulario - Arquivamento

| Campo | Nome | Tipo |
|-------|------|------|
| Pasta do Arquivo | `pasta_arquivo` | text |
| Aba do Arquivo | `aba_arquivo` | text |

### 8.6 Formulario - Observacao

| Campo | Nome | Tipo |
|-------|------|------|
| Observacao | `observacao` | textarea |

### 8.7 JavaScript

- Ao preencher data_emissao: calcula data_validade automaticamente (emissao + prazo_dias)

---

## 9. RECEBER VALE

**URL**: `/pallet/vales/<int:vale_id>/receber`
**Metodo**: POST apenas (sem tela propria)
**Rota**: `pallet_bp.route('/vales/<int:vale_id>/receber')` - funcao `receber_vale()`

### 9.1 Acao

Marca o vale como recebido:
- `recebido = True`
- `recebido_em = agora`
- `recebido_por = usuario`
- `posse_atual = 'NACOM'`
- `nome_posse = 'NACOM GOYA'`

Redireciona para lista de vales.

---

## 10. ENVIAR PARA RESOLUCAO

**URL**: `/pallet/vales/<int:vale_id>/enviar-resolucao`
**Arquivo Template**: `app/templates/pallet/enviar_resolucao.html`
**Rota**: `pallet_bp.route('/vales/<int:vale_id>/enviar-resolucao')` - funcao `enviar_resolucao()`
**Metodos**: GET, POST

### 10.1 Resumo do Vale (Alert Info)

| Campo | Valor |
|-------|-------|
| Vale # | `vale.id` |
| NF | `vale.nf_pallet` |
| Quantidade | `vale.quantidade` pallets |
| Cliente | `vale.nome_cliente` ou `vale.cnpj_cliente` |
| Validade | `vale.data_validade` |
| Dias restantes | calculado |

### 10.2 Formulario

| Campo | Nome | Tipo | Opcoes |
|-------|------|------|--------|
| Tipo de Resolucao | `tipo_resolucao` | radio cards | VENDA (checked), COLETA |
| Responsavel | `responsavel_resolucao` | text | Empresa que vai comprar/coletar |
| CNPJ do Responsavel | `cnpj_resolucao` | text | - |
| Valor (R$) | `valor_resolucao` | text | Valor da venda ou custo coleta |

### 10.3 Botoes

| Botao | Tipo | Texto |
|-------|------|-------|
| Cancelar | a.btn-secondary | "Cancelar" |
| Enviar | button.btn-warning | "Enviar para Resolucao" |

---

## 11. RESOLVER VALE

**URL**: `/pallet/vales/<int:vale_id>/resolver`
**Arquivo Template**: `app/templates/pallet/resolver_vale.html`
**Rota**: `pallet_bp.route('/vales/<int:vale_id>/resolver')` - funcao `resolver_vale()`
**Metodos**: GET, POST

### 11.1 Resumo do Vale

| Campo | Valor |
|-------|-------|
| Vale # | `vale.id` |
| NF | `vale.nf_pallet` |
| Quantidade | `vale.quantidade` pallets |
| Cliente | `vale.nome_cliente` |
| Tipo | `vale.tipo_resolucao` |
| Responsavel | `vale.responsavel_resolucao` |
| Valor | `vale.valor_resolucao` |

### 11.2 Timeline de Status

Recebido -> Enviado -> Resolver (atual)

### 11.3 Formulario

| Campo | Nome | Tipo | Notas |
|-------|------|------|-------|
| NF de Resolucao | `nf_resolucao` | text | NF de venda/recebimento |
| Valor Final (R$) | `valor_resolucao` | text | Valor efetivo |
| Observacao | `observacao` | textarea | - |

### 11.4 Alerta

Warning: "Ao resolver o vale, ele sera marcado como concluido e nao podera mais ser alterado."

### 11.5 Botoes

| Botao | Tipo | Texto |
|-------|------|-------|
| Cancelar | a.btn-secondary | "Cancelar" |
| Resolver | button.btn-success | "Resolver Vale" |

---

## 12. VINCULAR VENDA

**URL**: `/pallet/vincular-venda/<int:movimento_id>`
**Arquivo Template**: `app/templates/pallet/vincular_venda.html`
**Rota**: `pallet_bp.route('/vincular-venda/<int:movimento_id>')` - funcao `vincular_venda()`
**Metodos**: GET, POST

### 12.1 Dados da Venda (Alert Success)

| Campo | Valor |
|-------|-------|
| NF | `venda.numero_nf` |
| Quantidade | `venda.qtd_movimentacao` pallets |
| Data | `venda.data_movimentacao` |
| Comprador | `venda.nome_destinatario` |

### 12.2 Tabela de Remessas Disponiveis

| Coluna | Campo |
|--------|-------|
| Radio | `remessa_id` (required) |
| NF Remessa | `remessa.numero_nf` |
| Data | `remessa.data_movimentacao` |
| Destinatario | tipo + nome/cnpj |
| Quantidade | `remessa.qtd_movimentacao` |
| Status | "Pendente" |

### 12.3 Botoes

| Botao | Tipo | Texto | Condicao |
|-------|------|-------|----------|
| Cancelar | a.btn-secondary | "Cancelar" | sempre |
| Vincular | button.btn-success | "Vincular" | se existem remessas |

---

## APIS DISPONIVEIS

| URL | Metodo | Descricao | Retorno |
|-----|--------|-----------|---------|
| `/pallet/api/saldo/<cnpj>` | GET | Saldo de pallet de um CNPJ | `{cnpj, saldo}` |
| `/pallet/api/buscar-destinatario` | GET | Busca cliente/transportadora | lista com cnpj, nome, aceita_nf_pallet |
| `/pallet/api/embarque/<id>/itens` | GET | Itens de um embarque | lista com id, cliente, cnpj, pedido, aceita_nf_pallet |
| `/pallet/api/dashboard` | GET | Dados do dashboard | `{total_em_terceiros, saldos[]}` |

---

## FLUXOS DE PROCESSO MAPEADOS

### Etapa 1: Faturamento

```
[Sincronizar Odoo] -- tipo=remessas --> [Remessas importadas]
                   -- tipo=vendas --> [Vendas importadas]
```

### Etapa 2: Responsabilidade/Prazos

```
[Dashboard] -- visualiza --> [Remessas Vencidas]
           -- visualiza --> [Remessas Prestes a Vencer]
           -- visualiza --> [Saldos por Destinatario]
```

### Etapa 3: Resolucao NF Remessa

```
[Sincronizar Odoo] -- tipo=devolucoes --> [Devolucoes importadas + baixas automaticas]
                   -- tipo=recusas --> [Recusas importadas + baixas automaticas]

[Dashboard] -- Vendas Pendentes --> [Vincular Venda] --> [Baixa de Remessa]

[Movimentos] -- filtro=Pendentes --> [Baixar Movimento] --> [Baixa manual]
```

### Etapa 4: Vale Pallet

```
[Vale Pallets] -- Novo Vale --> [Criar Vale] --> [Baixa automatica se soma >= remessa]

[Criar Vale] -- campos obrigatorios --> nf_pallet, tipo_vale, quantidade, data_emissao
            -- campos opcionais --> cliente, transportadora, posse, arquivo
```

### Etapa 5: Resolucao Vale

```
[Vale Pallets] -- status=PENDENTE --> [Receber] --> status=RECEBIDO, posse=NACOM

[Vale Pallets] -- status=RECEBIDO --> [Enviar Resolucao] --> tipo=VENDA ou COLETA
                                                          --> status=EM RESOLUCAO

[Vale Pallets] -- status=EM RESOLUCAO --> [Resolver] --> nf_resolucao, valor_final
                                                      --> status=RESOLVIDO
```

---

## FIM DO DOCUMENTO
