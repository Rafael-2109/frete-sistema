# Opção 030 — Chegada de Veículo

> **Módulo**: Operacional — Transferência/Contratação
> **Páginas de ajuda**: 6 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Registra a chegada de veículos de transferência na unidade destino, liberando os CTRCs para operações de entrega ou transferência subsequentes.

## Quando Usar
Quando um veículo com Manifesto Operacional chega à unidade destino após viagem de transferência. A chegada é pré-requisito para descarga, roteirização e carregamento para entrega.

## Pré-requisitos
- Veículo deve possuir Manifesto Operacional emitido na origem
- Manifesto não pode estar cancelado ou com falta total já atribuída

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Código de barras Manifesto | Não | Captura do código de barras do Manifesto para chegada rápida |
| Seleção na lista | Não | Clique na linha do Manifesto para registrar chegada |

## Fluxo de Uso
1. Veículo chega à unidade com Manifesto Operacional
2. Usuário acessa opção 030
3. Captura código de barras do Manifesto OU clica na linha correspondente
4. Sistema registra hora/data de chegada
5. CTRCs do Manifesto ficam disponíveis para operações na unidade

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 078 | Início de descarga (opcional após chegada) |
| 064 | Fim de descarga do Manifesto |
| SSWBar | Atualiza chegada automaticamente durante descarga |
| 081 | CTRCs disponíveis para entrega após chegada |
| 019 | Relaciona CTRCs disponíveis no armazém |
| 057 | Monitora chegadas em tempo real |
| 264 | Monitora descarregamento de veículos com chegada nos últimos 3 dias |

## Observações e Gotchas
- **Chegada automática**: SSWBar atualiza chegada automaticamente ao iniciar descarga
- **Manifestos recentes**: Tela relaciona Manifestos com chegada nos últimos 5 dias
- **Previsão de chegada**: Sistema utiliza previsão de chegada informada pela subcontratante quando unidade destino está identificada
- **Gaiolas e pallets**: Podem ser descarregados pela opção 064 sem conferência de volumes
- **Conferentes**: Quando controle ativado (opção 903/Operação), conferente cadastrado (opção 111) é necessário para finalizar descarga
- **CTRCs em trânsito**: Opção 057 mostra CTRCs em trânsito com previsão de chegada, mas não contabiliza nos totais
- **Descarga não obrigatória**: Início e fim de descarga são opcionais — fim pode ser informado sem informar início

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A04](../pops/POP-A04-cadastrar-rotas.md) | Cadastrar rotas |
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
| [POP-D03](../pops/POP-D03-manifesto-mdfe.md) | Manifesto mdfe |
| [POP-D04](../pops/POP-D04-chegada-veiculo.md) | Chegada veiculo |
| [POP-D05](../pops/POP-D05-baixa-entrega.md) | Baixa entrega |
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
