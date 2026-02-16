# Opção 696 — Previsão de Entrega por Cliente

> **Módulo**: Logística/Comercial
> **Páginas de ajuda**: 3 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função
Cadastrar prazos de entrega específicos por cliente, permitindo customização de previsões de entrega diferentes do padrão calculado pelo sistema (rotas + cidades).

## Quando Usar
Quando for necessário:
- Definir prazos de entrega diferenciados para clientes específicos
- Atender acordos comerciais com prazos personalizados
- Sobrepor cálculo padrão de prazo (opção 403 + 402) para clientes específicos
- Consultar prazos customizados nas opções 107 e 109

## Pré-requisitos
- Cliente cadastrado (opção 483)
- Cidades atendidas cadastradas (opção 402)
- Rotas cadastradas (opção 403) — necessárias para cálculo padrão
- **NÃO pode coexistir com opção 697**: Apenas UMA das duas pode ser usada por cliente — se opção 697 existir, excluir antes de usar opção 696

## Campos / Interface

### Tela Principal — Cadastro de Prazos

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ/CPF cliente | Sim | Cliente para o qual prazos serão cadastrados |
| Cidade origem | Condicional | Cidade de origem da operação (informar cidade OU UF) |
| UF origem | Condicional | UF de origem (informar cidade OU UF) |
| Cidade destino | Condicional | Cidade de destino (informar cidade OU UF) |
| UF destino | Condicional | UF de destino (informar cidade OU UF) |
| Prazo (dias) | Sim | Prazo customizado em dias |
| Tipo de prazo | Sim | **Dias úteis** (desconsideram sábados, domingos, feriados) ou **Dias corridos** |

## Fluxo de Uso

### Cadastro de prazos customizados
1. Acessar opção 696
2. Informar CNPJ/CPF do cliente
3. Cadastrar prazos para cada combinação origem-destino desejada
4. Informar se prazo é em dias úteis ou corridos
5. Salvar — prazos customizados têm prioridade sobre cálculo padrão

### Consulta de prazos cadastrados
6. Acessar opção 107 (Relatório de Cidades Atendidas):
   - Informar CNPJ cliente no campo próprio
   - Gerar relatório — prazos específicos (opção 696) são considerados
7. OU acessar opção 109 (Consulta de Cidades Atendidas):
   - Informar CNPJ/CPF no campo próprio
   - Prazos cadastrados na opção 696 serão considerados no cálculo de entrega

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 697 | Previsão de entrega por origem-destino — ALTERNATIVA à opção 696 (apenas UMA pode ser usada por cliente) |
| 107 | Relatório de Cidades Atendidas — campo CNPJ considera prazos da opção 696 |
| 109 | Consulta de Cidades Atendidas — campo CNPJ/CPF considera prazos da opção 696 |
| 402 | Cadastro de Cidades — prazos de entrega padrão + dias da semana |
| 403 | Rotas — prazos de transferência padrão entre unidades |
| 483 | Cadastro de Clientes — cliente deve existir antes de cadastrar prazos |

## Observações e Gotchas

- **Opção 696 vs 697 — MUTUAMENTE EXCLUDENTES**:
  - **696**: Prazos simples por cliente (origem/destino)
  - **697**: Prazos mais complexos com origem + exceções + mercadoria
  - **APENAS UMA** pode ser usada por cliente
  - Se opção 697 existir, **excluir** antes de usar opção 696

- **Hierarquia de cálculo de prazo**:
  1. **Opção 696 ou 697** (prazos por cliente) — PRIORIDADE MÁXIMA
  2. Cálculo padrão (opção 403 + 402) — usado se não houver 696/697

- **Dias úteis vs corridos**:
  - **Dias úteis**: Desconsideram sábados, domingos, feriados nacionais, estaduais (opção 060) e municipais (opção 402)
  - **Dias corridos**: Contam todos os dias

- **Consultas consideram prazos customizados**: Opções 107 e 109 possuem campo CNPJ/CPF — quando informado, prazos da opção 696 são usados no lugar do cálculo padrão

- **Origem/Destino flexível**: Pode-se cadastrar por cidade específica OU por UF inteira — cidade tem prioridade sobre UF se ambas estiverem cadastradas

- **Relatório 107 — Campos relevantes**:
  - **Prazo máximo**: Soma de transferência (403) + entrega (402) — OU prazo customizado (696)
  - **Dias da semana**: Dias que cidade é atendida
  - **TDA**: Taxa de Dificuldade de Acesso
  - **Pedágios**: Quantidade entre origem-destino

- **Consulta 109 — Campos relevantes**:
  - **ENTREGA**: Data prevista calculada usando prazo da opção 696 se CNPJ/CPF informado
  - **PRAZO MÁXIMO**: Em dias úteis
  - **FERIADOS**: Municipais (402) e estaduais (060) considerados

- **Google Maps fallback**: Quando tabelas necessárias não estiverem cadastradas, algumas opções utilizam duração da viagem do Google — opção 696 tem prioridade

- **Cliente pagador vs remetente**: Numa operação, prazos são buscados no cliente **pagador**. Se for terceiro pagador, **remetente** é buscado prioritariamente

- **Rota necessária para cidade aparecer em relatório 107**: Mesmo com prazo customizado, para cidade ser relacionada deve existir rota (opção 403) ligando unidade origem à unidade destino
