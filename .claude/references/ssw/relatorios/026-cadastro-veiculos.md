# Opção 026 — Cadastro de Veículos

> **Módulo**: Frota
> **Páginas de ajuda**: 4 páginas consolidadas (referências indiretas)
> **Atualizado em**: 2026-02-15

## Função
Cadastra e mantém o registro de veículos da frota, incluindo suas características físicas, configurações de odômetro e dados de identificação.

## Quando Usar
- Ao adicionar um novo veículo à frota
- Para atualizar informações de veículos existentes
- Para configurar quantidade de eixos (utilizada na movimentação de pneus - opção 316)
- Para atualizar manualmente odômetro e quilometragem geral (requer usuário FRT)

## Pré-requisitos
- Tipo de veículo cadastrado (opção 097)
- Permissão de usuário Frota (FRT) para atualizações manuais de odômetro

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Placa | Sim | Identificação do veículo (usada como login no SSW Mobile) |
| Tipo de veículo | Sim | Referência à opção 097 (determina se tem motor ou não) |
| Quantidade de eixos | Sim | Define posições disponíveis para pneus (opção 316) |
| Possui odômetro | Não | Indica se o veículo possui odômetro |
| Qtde dígitos odômetro | Condicional | Permite reiniciar odômetro mantendo continuidade na km total |
| Km odômetro | Não | Quilometragem atual do odômetro (reinicia ao atingir limite) |
| Qtde voltas | Não | Quantidade de voltas completas do odômetro |
| Km veículo | Não | Quilometragem total desde a compra |
| Data de cadastramento | Automático | Data de inclusão no sistema |
| Unidade | Não | Unidade padrão para operações |

## Fluxo de Uso
1. Informar placa do veículo (novo ou existente)
2. Preencher tipo de veículo e quantidade de eixos
3. Configurar odômetro (se aplicável):
   - Quantidade de dígitos do odômetro
   - Quilometragem inicial
4. Salvar cadastro
5. Para atualizações manuais de odômetro (requer usuário FRT):
   - Acessar opção 026
   - Localizar veículo
   - Atualizar Km odômetro e/ou Km veículo

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 097 | Tipo de veículo (define se tem motor) |
| 316 | Movimentação de pneus (usa quantidade de eixos) |
| 045 | Relação de veículos (relatório, filtra por período de cadastramento) |
| 328 | Quilometragem de veículos (consulta odômetro e km total) |
| 945 | Cadastramento para SSW Mobile (usa placa como login) |
| 131 | Ordens de Serviço (atualizam odômetro automaticamente) |
| 120 | Autorizações de saída/entrada (pontos para cálculo de distâncias) |
| 038 | Informação de odômetro para coletas/entregas |

## Observações e Gotchas
- **Cálculo de Km veículo**: Km veículo = Qtde voltas × (999999+1) + Km odômetro
  - Exemplo: Se odômetro tem 6 dígitos (999999 max) e deu 2 voltas com 150000 km atual: 2 × 1000000 + 150000 = 2.150.000 km
- **Atualização automática de odômetro**:
  - Veículos de transferência: calculado via API Google (saídas/chegadas de Manifestos)
  - Veículos de coleta/entrega: informado manualmente (opção 038)
  - Ordens de Serviço: atualizam quando providências são informadas (opção 131)
- **Veículos sem motor**: Recebem odômetro do veículo trator (distância replicada)
- **Usuário FRT**: Somente usuários com permissão Frota podem atualizar manualmente odômetro e quilometragem
- **SSW Mobile**: A placa é utilizada como login para acesso mobile (opção 945)
- **Reinício do odômetro**: Sistema mantém continuidade na quilometragem total mesmo quando odômetro reinicia (via campo "Qtde voltas")

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A08](../pops/POP-A08-cadastrar-veiculo.md) | Cadastrar veiculo |
| [POP-C02](../pops/POP-C02-emitir-cte-carga-direta.md) | Emitir cte carga direta |
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
| [POP-D03](../pops/POP-D03-manifesto-mdfe.md) | Manifesto mdfe |
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
| [POP-G02](../pops/POP-G02-checklist-gerenciadora-risco.md) | Checklist gerenciadora risco |
| [POP-G03](../pops/POP-G03-custos-frota.md) | Custos frota |
