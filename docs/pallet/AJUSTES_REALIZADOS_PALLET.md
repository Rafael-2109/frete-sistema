# Log de Ajustes Realizados - Modulo Pallet

**Data**: 05/01/2026
**Status**: CONCLUIDO

---

## COMPARACAO UI x PROCESSO

### Etapa 1: Faturamento

| Aspecto | Processo Documentado | UI Atual | Status |
|---------|---------------------|----------|--------|
| Emissao NF | ProcessadorFaturamento emite | Sync Odoo importa | OK (externo) |
| Registro manual | Registrar Saida | /pallet/registrar-saida | OK |
| Campo aceita NF | nao_aceita_nf_pallet | Consultado na API buscar-destinatario | OK |

### Etapa 2: Responsabilidade/Prazos

| Aspecto | Processo Documentado | UI Atual | Status |
|---------|---------------------|----------|--------|
| Prazo 7d SP/RED | calcular_prazo_cobranca() | calcular_prazo_remessa() | OK |
| Prazo 30d outros | calcular_prazo_cobranca() | calcular_prazo_remessa() | OK |
| Alertas vencimento | Dashboard | Cards de alerta | OK |
| Calculo dinamico | Por UF/Rota | Implementado | OK |

### Etapa 3: Resolucao NF Remessa

| Aspecto | Processo Documentado | UI Atual | Status |
|---------|---------------------|----------|--------|
| CANCELAMENTO | Importar via Sync | tipo=recusas | OK |
| DEVOLUCAO | Importar via Sync | tipo=devolucoes | OK |
| RECUSA | Importar via Sync | tipo=recusas | OK |
| SUBSTITUICAO | Vincular NF cliente a NF transp | /pallet/substituicao | OK |
| VENDA | Vincular venda a remessa | /pallet/vincular-venda | OK |

### Etapa 4: Vale Pallet

| Aspecto | Processo Documentado | UI Atual | Status |
|---------|---------------------|----------|--------|
| Criar vale | Manual | /pallet/vales/novo | OK |
| Campos obrigatorios | nf, tipo, qtd, data | Formulario completo | OK |
| tipo_vale | VALE_PALLET / CANHOTO_ASSINADO | Implementado | OK |
| Baixa automatica | Ao criar vale | Implementado | OK |

### Etapa 5: Resolucao Vale

| Aspecto | Processo Documentado | UI Atual | Status |
|---------|---------------------|----------|--------|
| Ciclo PENDENTE->RECEBIDO | Botao Receber | POST /receber | OK |
| Ciclo RECEBIDO->EM RESOLUCAO | Enviar para resolucao | /enviar-resolucao | OK |
| Ciclo EM RESOLUCAO->RESOLVIDO | Resolver vale | /resolver | OK |
| Tipos VENDA/COLETA | Radio buttons | Implementado | OK |

---

## DIFERENCAS ENCONTRADAS

### D1: Filtro de Movimentos Incompleto

**Problema**: O filtro de tipo na tela `/pallet/movimentos` oferece apenas "SAIDA" e "RETORNO", mas o sistema usa tipos: REMESSA, SAIDA, ENTRADA, DEVOLUCAO, RECUSA.

**Arquivo**: `app/templates/pallet/movimentos.html` linha 29-33

**Solucao**: Adicionar opcoes de filtro para REMESSA, DEVOLUCAO, RECUSA

---

### D2: Dashboard usa prazo fixo no titulo

**Problema**: O dashboard mostra "Remessas Vencidas (> X dias)" onde X deveria ser dinamico (7 ou 30), mas no template usa variavel `prazo_dias` que nao existe.

**Arquivo**: `app/templates/pallet/index.html` linha 57-58

**Observacao**: Verificar se a variavel prazo_dias esta sendo passada. Apos analise, vi que sao passados `prazo_sp_red` e `prazo_outros`.

**Solucao**: Ajustar o template para mostrar os dois prazos corretamente

---

### D3: Falta Interface de Substituicao

**Problema**: O processo define SUBSTITUICAO como uma tratativa onde NF do cliente consome parte da NF da transportadora. O campo `nf_remessa_origem` foi adicionado ao modelo, mas nao existe interface para usar.

**Arquivo**: Nao existe

**Solucao**: Criar rota e template para substituicao de NF

---

## AJUSTES IMPLEMENTADOS

### A1: Corrigir Filtro de Movimentos

**Data**: 05/01/2026
**Status**: IMPLEMENTADO

**Arquivo modificado**: `app/templates/pallet/movimentos.html` linhas 29-36

**Alteracao**: Adicionado os tipos REMESSA, ENTRADA, DEVOLUCAO, RECUSA ao filtro de movimentos.

Opcoes anteriores: SAIDA, RETORNO
Opcoes atuais: REMESSA, SAIDA (Venda), ENTRADA (Retorno), DEVOLUCAO, RECUSA

---

### A2: Corrigir Template Dashboard

**Data**: 05/01/2026
**Status**: IMPLEMENTADO

**Arquivo modificado**: `app/templates/pallet/index.html` linha 57-58

**Alteracao**: Ajustado o titulo do alerta de vencimento para mostrar os dois prazos.

Antes: "Remessas Vencidas (> {{ prazo_dias }} dias)" - variavel inexistente
Depois: "Remessas Vencidas (7d SP/RED, 30d outros)" - texto fixo explicativo

---

### A3: Criar Interface de Substituicao

**Data**: 05/01/2026
**Status**: IMPLEMENTADO

**Arquivos criados**:
- `app/pallet/routes.py` - Rotas `listar_substituicoes()` e `registrar_substituicao()`
- `app/templates/pallet/substituicao_lista.html` - Lista de remessas disponiveis
- `app/templates/pallet/substituicao.html` - Formulario de substituicao

**Arquivo modificado**: `app/templates/pallet/index.html` - Adicionado botao "Substituicao de NF"

**Funcionalidade**:
- Lista remessas de TRANSPORTADORA pendentes
- Permite criar NF para CLIENTE que "consome" parte da NF da transportadora
- Usa campo `nf_remessa_origem` para vincular NF cliente a NF transportadora
- Usa campo `cnpj_responsavel` para manter responsabilidade na transportadora
- Baixa automatica da remessa original quando quantidade total e substituida

---

## RESUMO FINAL

| Ajuste | Arquivo | Status |
|--------|---------|--------|
| A1 - Filtro movimentos | movimentos.html | IMPLEMENTADO |
| A2 - Prazo dashboard | index.html | IMPLEMENTADO |
| A3 - Interface substituicao | routes.py + 2 templates | IMPLEMENTADO |

**Todos os ajustes foram implementados com sucesso.**

---

## ARQUIVOS MODIFICADOS/CRIADOS

1. `app/templates/pallet/movimentos.html` - Filtro de tipos atualizado
2. `app/templates/pallet/index.html` - Titulo corrigido + botao substituicao
3. `app/pallet/routes.py` - 2 novas rotas de substituicao
4. `app/templates/pallet/substituicao_lista.html` - NOVO
5. `app/templates/pallet/substituicao.html` - NOVO

