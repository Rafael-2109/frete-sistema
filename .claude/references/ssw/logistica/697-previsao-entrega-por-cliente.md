# Opção 697 — Previsão de Entrega por Cliente (Origem-Destino)

> **Módulo**: Logística
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Configura previsão de entrega específica por cliente, por **origem-destino** e opcionalmente por mercadoria. Alternativa à opção 696 que permite cadastrar a origem e apenas as exceções em relação aos prazos padrão.

## Quando Usar
- Para clientes com operações em **várias origens** (para apenas uma origem, usar opção 696)
- Para cadastrar prazos específicos diferentes do padrão da transportadora
- Quando cliente possui necessidades de prazo diferenciadas por origem-destino

## Pré-requisitos
- **Exclusão da tabela 696**: Se existir tabela cadastrada na opção 696, deve ser excluída para usar opção 697
- Cliente cadastrado no sistema

## Campos / Interface

### Tela Inicial
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ/raiz | Sim | CNPJ ou raiz (8 dígitos) do cliente |
| Tipo do cliente | Sim | Pagador, remetente ou destinatário |
| Prazo em dias | Sim | Útil (desconsiderando sábados, domingos e feriados) ou corridos |
| Dias da semana opc 402 | Não | S para buscar dias da semana da cidade (opção 402), incluindo sábado |

### Tela Principal (Cadastro de Prazos)
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Cidade origem ou UF origem | Sim | Cidade tem prioridade sobre UF |
| Cidade destino ou UF destino | Sim | Cidade tem prioridade sobre UF |
| Prazo (dias) | Sim | Prazo em dias da cidade origem até cidade destino |
| Prazo P Física (dias) | Não | Prazo específico quando destinatário for pessoa física (tem prioridade) |
| Mercadoria | Não | Para prazos específicos por tipo de mercadoria |

## Fluxo de Uso
1. **Excluir opção 696**: Se existir tabela na opção 696, excluí-la primeiro
2. Informar CNPJ/raiz do cliente
3. Definir tipo do cliente (pagador, remetente ou destinatário)
4. Configurar tipo de prazo (dias úteis) e uso de dias da semana da opção 402
5. Cadastrar prazos específicos por origem-destino
6. Opcionalmente, cadastrar prazos diferenciados por mercadoria
7. Opcionalmente, importar prazos via arquivo CSV (limitado a 50.000 linhas)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 696 | Alternativa (apenas uma pode ser usada por cliente) |
| 402 | Fornece prazo de entrega padrão e dias da semana |
| 403 | Fornece prazo de transferência padrão |
| 406 | Tipo de mercadoria para diferenciar prazos |

## Observações e Gotchas

### Diferenças com Opção 696
- **696**: Para clientes com operações em **apenas uma origem**
- **697**: Para clientes com operações em **várias origens**
- **Exclusão mútua**: Apenas uma opção pode ser utilizada por cliente

### Regras de Priorização
- **Prioridade de cadastro**: Opção 697 tem prioridade sobre cálculo padrão
- **Especificidade**: Prazo mais específico cadastrado será utilizado
- **Cliente**: Prazos buscados no pagador; se terceiro pagador, remetente tem prioridade

### Características Importantes
- **Exceções**: Permite cadastrar apenas as exceções em relação aos prazos padrão (mais eficiente)
- **Frete CIF**: Prazo cadastrado na cidade destino (entrega)
- **Frete FOB**: Prazo cadastrado na cidade origem (coleta)
- **Dias da semana**: Quando omitidos, os da opção 402 são utilizados (exceto em frete FOB)
- **Contagem de dias**: Início da contagem ocorre em dias úteis ou corridos conforme opção 903/Operação/Prazo de transferência
- **Pessoa Física**: Prazo P Física tem prioridade sobre prazo geral
- **Mercadoria**: Mesma origem-destino pode ter diferenciação com Tipo de Mercadoria (opção 406)
- **Importação**: Arquivo CSV no formato do arquivo baixado, limitado a 50.000 linhas
- **Replicação**: Prazos podem ser replicados para CNPJs da mesma raiz ou do mesmo grupo (opção 583)
- **Consulta**: Link "Consultar" permite filtrar tabelas por origem/destino (cidade ou UF)
- **Relações**: Links disponíveis para listar clientes com prazos cadastrados e relatórios de prazos por cidade
