# Opcao 191 — Instrucoes de Clientes (Embarcador)

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada (referencia na opcao 192)
> **Atualizado em**: 2026-02-14

## Funcao
Permite que clientes embarcadores com dominio proprio cadastrem instrucoes/questionamentos sobre situacao de entregas de CTRCs para transportadoras que utilizam o SSW. Sistema integra comunicacao entre embarcador (opcao 191) e SAC da transportadora (opcao 192), permitindo registro de questionamentos e respostas especializadas.

## Quando Usar
- Cliente embarcador com dominio proprio quer questionar situacao de entrega de CTRC
- Cliente embarcador quer registrar instrucoes especiais sobre CTRCs em transito
- Cliente embarcador quer visualizar respostas do SAC da transportadora
- Facilitar comunicacao estruturada entre embarcador e transportadora

## Pre-requisitos
- Cliente embarcador com dominio proprio cadastrado (opcao 434)
- Grupo de clientes configurado (opcao 583) para buscar todos os CNPJs do grupo
- Usuarios do SAC da transportadora cadastrados no grupo 100-SAC (opcao 925)
- CTRCs emitidos para o cliente embarcador

## Campos / Interface

### Tela Principal (Opcao 191 — Cliente Embarcador)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Cliente (grupo) | Sim | CNPJ do cliente embarcador que possui dominio proprio (opcao 434). Todos os CTRCs dos CNPJs do grupo (opcao 583) sao buscados |
| Periodo | Sim | Data da ultima instrucao registrada pelo cliente embarcador. Nao pode ser maior que 31 dias |

### Tela de Resposta (Opcao 192 — SAC Transportadora)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CTRC | Informativo | CTRC com instrucao do cliente embarcador |
| Instrucao do cliente | Informativo | Questionamento/instrucao registrada pelo cliente embarcador |
| Resposta do SAC | Sim | Resposta especializada registrada pelo usuario do grupo 100-SAC |

## Fluxo de Uso

### Cliente Embarcador Registra Instrucao
1. Cliente embarcador acessa seu dominio proprio (opcao 434)
2. Acessa opcao 191 (Instrucoes de Clientes)
3. Seleciona CTRC de interesse
4. Registra instrucao/questionamento sobre situacao de entrega
5. Envia instrucao para SAC da transportadora

### SAC Transportadora Responde Instrucao
1. Usuario do SAC (grupo 100-SAC) acessa opcao 192
2. Visualiza CTRCs com ultimas instrucoes registradas por clientes embarcadores
3. Seleciona CTRC com instrucao pendente
4. Le instrucao/questionamento do cliente embarcador
5. Registra resposta especializada
6. Salva resposta

### Cliente Embarcador Visualiza Resposta
1. Cliente embarcador acessa seu dominio proprio
2. Acessa opcao 191 (Instrucoes de Clientes)
3. Seleciona periodo de consulta (max 31 dias)
4. Visualiza CTRCs com respostas do SAC da transportadora

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 191 | Instrucoes de Clientes (cliente embarcador registra instrucoes e visualiza respostas) |
| 192 | CTRCs com Instrucoes de Clientes (SAC transportadora responde instrucoes) |
| 434 | Cadastro de dominio proprio do cliente embarcador (pre-requisito) |
| 583 | Grupo de clientes (busca todos os CNPJs do grupo) |
| 925 | Cadastro de usuarios (usuarios do SAC devem pertencer ao grupo 100-SAC) |

## Observacoes e Gotchas
- **Dominio proprio obrigatorio**: Cliente embarcador deve ter dominio proprio cadastrado (opcao 434) para usar opcao 191
- **Grupo 100-SAC**: Usuarios da transportadora que respondem instrucoes devem pertencer ao grupo 100-SAC (opcao 925) para garantir respostas especializadas
- **Periodo maximo de 31 dias**: Consulta de instrucoes na opcao 191 e 192 nao pode ter periodo maior que 31 dias
- **Busca por grupo**: Sistema busca todos os CTRCs dos CNPJs do grupo (opcao 583), nao apenas CNPJ especifico
- **Comunicacao bidirecional**: Opcao 191 permite cliente registrar instrucoes E visualizar respostas — opcao 192 permite SAC visualizar instrucoes E registrar respostas
- **Ultima instrucao**: Tela traz CTRCs com ultima instrucao registrada pelo cliente embarcador (nao historico completo)
- **Respostas especializadas**: Restricao de grupo 100-SAC garante que respostas sejam dadas por usuarios treinados e especializados
- **Instrucoes normalmente sobre entregas**: Questionamentos tipicamente envolvem situacao de entregas, previsoes, ocorrencias, etc.
