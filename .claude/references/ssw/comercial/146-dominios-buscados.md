# Opção 146 — Domínios a Serem Buscados

> **Módulo**: Comercial
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Cadastra domínios de outras transportadoras que utilizam SSW para serem buscados de forma on-line, permitindo que clientes embarcadores visualizem informações de múltiplas transportadoras de forma conjunta.

## Quando Usar
- Cliente embarcador contrata múltiplas transportadoras que usam SSW
- Necessidade de consultar CTRCs, situação de clientes ou coletas em outras transportadoras
- Cliente embarcador possui seu próprio Sistema SSW e quer integração com transportadoras contratadas
- Centralização de informações logísticas de múltiplos fornecedores

## Pré-requisitos
- **Opção 434**: Domínio a ser buscado deve liberar acesso via opção 434 (na transportadora destino)
- **SSW em ambos os domínios**: Tanto cliente embarcador quanto transportadora devem usar SSW
- **CNPJ do cliente cadastrado**: Cliente específico deve estar liberado na opção 434 do domínio destino
- **Integração configurada**: Comunicação entre domínios deve estar estabelecida

## Campos / Interface

### Tela da Opção 146 (Cliente Embarcador)
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Domínio | Sim | Sigla do domínio a ser buscado (transportadora) |
| Exc (link) | - | Excluir domínio cadastrado da tabela |

### Tela da Opção 434 (Transportadora)
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Domínio | Sim | Sigla do domínio autorizado (cliente embarcador) a acessar este domínio |
| CNP cliente | Sim | CNPJ do cliente específico liberado para consulta (raiz - busca todos CNPJs da raiz automaticamente) |
| Exc (link) | - | Excluir liberação da tabela |

## Fluxo de Uso

### Configuração no Cliente Embarcador (Opção 146)
1. Cliente embarcador acessa seu próprio Sistema SSW
2. Acessar opção 146
3. Informar sigla do domínio da transportadora a ser buscada
4. Salvar cadastro → domínio aparece na tabela
5. Repetir para cada transportadora contratada
6. Para remover domínio, clicar em **Exc** na tabela

### Configuração na Transportadora (Opção 434)
1. Transportadora acessa opção 434
2. Informar sigla do domínio do cliente embarcador autorizado
3. Informar CNPJ do cliente específico liberado (apenas raiz - sistema busca todos CNPJs da raiz automaticamente)
4. Salvar cadastro → domínio e cliente aparecem na tabela
5. Para remover liberação, clicar em **Exc** na tabela

### Uso nas Consultas (após configuração)
1. Cliente embarcador acessa opções de consulta integradas:
   - **Opção 101**: Situação de CTRCs
   - **Opção 102**: Situação de clientes
   - **Opção 103**: Situação de coletas
2. Sistema busca informações **on-line** de todos os domínios cadastrados (opção 146)
3. Informações são exibidas de forma conjunta
4. Cliente visualiza dados de múltiplas transportadoras em uma única tela

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 434 | Liberação de domínios e clientes (na transportadora - par da opção 146) |
| 101 | Situação de CTRCs (usa busca em domínios cadastrados) |
| 102 | Situação de clientes (usa busca em domínios cadastrados) |
| 103 | Situação de coletas (usa busca em domínios cadastrados) |

## Observações e Gotchas
- **Configuração bidirecional**:
  - **Opção 146** (cliente embarcador): cadastra domínios a serem buscados
  - **Opção 434** (transportadora): libera acesso para domínio buscador
- **Busca automática por raiz**: Ao cadastrar CNPJ do cliente na opção 434, SSW automaticamente busca **todos os CNPJs da raiz** (não precisa cadastrar cada filial individualmente)
- **Consulta on-line**: Informações são buscadas em tempo real dos domínios cadastrados
- **Visualização conjunta**: Cliente embarcador vê dados de múltiplas transportadoras em uma única interface
- **SSW obrigatório**: Funcionalidade só opera entre sistemas SSW (ambos os domínios devem usar SSW)
- **Cliente embarcador com SSW próprio**: Ideal para grandes embarcadores que possuem seu próprio Sistema SSW
- **Múltiplas transportadoras**: Cliente pode cadastrar quantos domínios forem necessários (opção 146)
- **Segurança**: Transportadora controla quais clientes específicos são visíveis via opção 434
- **Exclusão simples**: Link **Exc** permite remover cadastros de ambos os lados (opção 146 e 434)
- **Opções integradas**: Funcionalidade disponível em 3 opções principais: 101 (CTRCs), 102 (clientes), 103 (coletas)
