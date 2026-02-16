# Opção 097 — Cadastro de Tipos de Veículos

> **Módulo**: Operacional — Configuração de Veículos
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Cadastra tipos de veículos e suas características (consumo, motor, odômetro, controle de frota) para uso em opções operacionais, módulo Frota e emissão de CO2.

## Quando Usar
- Criar novos tipos de veículos além dos padrões SSW
- Configurar características de tipos de veículos
- Definir consumo médio para cálculo de CO2
- Habilitar/desabilitar controle de frota por tipo

## Pré-requisitos
- Nenhum — tabela disponível para todos os usuários

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Tipo | Sim | Caractere alfanumérico (tipos SSW não podem ser alterados) |
| Descrição | Sim | Descrição sucinta do veículo |
| Consumo médio | Sim | Consumo médio em Km/l |
| Veículo verde | Não | X indica veículo que não emite CO2 |
| Possui motor | Não | X indica que sim, diferencia cavalo de carreta (opção 020) |
| Possui odômetro | Não | X indica que sim, solicita odômetro na operação quando Frota ativado |
| Frota controla | Não | X indica controle de pneus e manutenção pelo módulo Frota |

## Tipos Padrão SSW (Não Alteráveis)
| Tipo | Descrição |
|------|-----------|
| C | Cavalo |
| Z | Cavalo trucado |
| R | Carreta |
| T | Truck |
| 3 | 3/4 |
| F | Furgão leve |
| V | Van |
| U | VUC |
| K | Toco |
| N | Ônibus |
| B | Balsa |
| E | Empurrador |
| 1 | Carro |
| I | Bicicleta |
| Y | Avião |
| O | Outros |

## Fluxo de Uso
1. Usuário acessa opção 097
2. Escolhe tipo existente para alterar OU cria novo tipo
3. Define características:
   - Descrição
   - Consumo médio (Km/l)
   - Veículo verde (não emite CO2)
   - Possui motor
   - Possui odômetro
   - Frota controla
4. Salva configuração
5. Tipo fica disponível para uso em cadastro de veículos (opção 026)

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 026 | Cadastro de veículos — utiliza tipos cadastrados |
| 020 | Emissão de Manifestos — diferencia cavalo de carreta |
| Frota | Módulo Frota utiliza configurações de odômetro e controle |
| CO2 | Emissão de CO2 utiliza consumo médio e veículo verde |

## Observações e Gotchas
- **Tipos SSW não alteráveis**: C, Z, R, T, 3, F, V, U, K, N, B, E, 1, I, Y, O são padrões do sistema
- **Consumo médio**: Utilizado para cálculo de emissão de CO2
- **Veículo verde**: Não emite CO2 (elétricos, híbridos, etc.)
- **Possui motor**: Diferencia veículos de tração (cavalo) de reboques (carreta)
- **Possui odômetro**: Quando módulo Frota ativado, solicita odômetro em operações
- **Frota controla**: Habilita controle de pneus e manutenção quando módulo Frota ativo
- **Balsa e Empurrador (B, E)**: Só podem ser utilizados por unidade AQUAVIÁRIA (opção 401)
- **Avião (Y)**: Manifestos carregados não são submetidos ao SEFAZ para autorização
- **Uso amplo**: Tabela utilizada por diversas opções operacionais e módulo Frota

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A08](../pops/POP-A08-cadastrar-veiculo.md) | Cadastrar veiculo |
| [POP-G03](../pops/POP-G03-custos-frota.md) | Custos frota |
