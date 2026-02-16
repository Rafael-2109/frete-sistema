# Opção 314 — Cadastro de Check-list de Manutenção

> **Módulo**: Frota
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Cadastra check-lists de manutenção preventiva para tipos de veículos. Check-list é uma lista de verificações relacionadas a manutenções que devem ser realizadas a cada quilometragem.

## Quando Usar
- Criar novo check-list para tipo de veículo
- Definir itens de verificação (serviços) do check-list
- Configurar periodicidade (km) do check-list
- Editar check-list existente

## Pré-requisitos
- Módulo Frota ativado
- Manual do Proprietário do veículo (base para itens)

## Processo

```
Opção 314 - Cadastra check-list
         ↓
Opção 315 - Vincula check-list ao veículo
         ↓
Opção 131 - OSs geradas automaticamente na km configurada
         ↓
Próximo agendamento - ao confirmar providências (opção 131)
```

## Campos / Interface

### Novo Check-list

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Número do Check-list** | Sim (automático) | Numerado automaticamente para identificar o check-list |
| **Descrição do Check-list** | Sim | Descrição relacionando-o a um tipo de veículo |
| **Km** | Sim | Quantidade de Km que define o próximo check-list a partir da execução da OS (opção 131) |
| **Itens a serem verificados** | Sim | Todos serviços a executar no veículo. Base: Manual do Proprietário. Até **150 caracteres de largura** por linha |

## Fluxo de Uso

1. Acesse opção 314
2. Sistema numera automaticamente o check-list
3. Informe descrição (ex: "MERCEDES BENS 1111")
4. Informe periodicidade em Km (ex: 30.000)
5. Liste todos itens a serem verificados (serviços)
6. Confirme cadastro
7. Vincule o check-list aos veículos via opção 315

## Exemplo de Check-list

```
Km = 30.000

CHECK-LIST: 00001 MERCEDES BENS 1111
EXECUTAR A CADA 30.000 KM
---------------------------------------------------------------------------

0100 CHASSIS
---------------------------------------------------------------------------
0101 REAPERTAR PORCAS DE RODAS
0102 VERIFICAR FOLGA DA DIRECAO HIDRAULICA
0103 ALINHAMENTO DO EIXO DIANTEIRO
0104 VERIFICAR A FOLGA DA BARRA DE DIRECAO
0105 VERIFICAR AMORTECEDORES
0106 VERIFICAR EMBUCHAMENTO
0107 VERIFICAR ESTADO DOS RESERVATORIOS
0108 APERTO GERAL DO CHASSIS

0200 MOTOR
---------------------------------------------------------------------------
0201 TROCAR OLEO LUBRIFICANTE
0202 VERIFICAR NIVEL DE OLEO DO CAMBIO
0203 LIMPAR BICO E BOMBA INJETORA
0204 ...

0300 ELETRICA
---------------------------------------------------------------------------
0301 REGULAR FAROIS
0302 VERIFICAR E SUBSTITUIR PELO RESERVA SE NECESSARIO
0303 VERIFICAR MOTOR DE ARRANQUE

etc.
```

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 131 | OSs geradas automaticamente na km configurada; próximo agendamento ao confirmar providências |
| 315 | Vincula check-list aos veículos |
| 045 | Lista veículos e check-lists vinculados |

## Observações e Gotchas

### Numeração Automática
- Check-lists são numerados automaticamente
- Número identifica o check-list no sistema

### Periodicidade (Km)
- Define intervalo entre execuções
- Próximo check-list agendado automaticamente após execução da OS (opção 131)
- Agendamento baseado em **quilometragem**, não data

### Base para Itens
- Utilizar **Manual do Proprietário do veículo** como referência
- Incluir todos serviços preventivos recomendados pelo fabricante

### Largura de Texto
- Cada item pode ter até **150 caracteres de largura**
- Organizar em seções (ex: CHASSIS, MOTOR, ELETRICA)

### Vinculação aos Veículos
- Após criar check-list, vincular aos veículos via opção 315
- Primeiro agendamento ocorre na vinculação
- Próximos agendamentos ao confirmar providências (opção 131)

### Diferença Check-list vs Planos de Manutenção
- **Check-list** (opção 314): lista de verificações para manutenção preventiva
- **Planos de Manutenção** (opção 615): agendamento mais complexo, múltiplos critérios

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-G03](../pops/POP-G03-custos-frota.md) | Custos frota |
