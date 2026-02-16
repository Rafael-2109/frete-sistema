# Opção 208 — SSWMobile 4 (versão desktop)

> **Módulo**: Operacional/Entregas
> **Referência interna**: Opção 155
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função

Executa as mesmas funções do SSWMobile 4, permitindo que motoristas em regiões remotas usem micro em vez de smartphone para receber instruções e gravar ocorrências de entregas e coletas.

## Quando Usar

- Substituir SSWMobile 4 quando motorista não tem smartphone disponível
- Operar entregas em regiões remotas usando computador
- Receber instruções do SAC e gravar ocorrências de entregas/coletas
- Registrar pré-entregas e ocorrências sem uso de dispositivo móvel

## Campos / Interface

### Tela 1 - Instruções e Seleção de CTRC

#### ENTREGA

**Entregar**: CTRCs disponíveis para entrega

**Aguardar**: SAC instruiu que CTRCs desta fila aguardem, sem nenhuma tentativa de entrega. Devem permanecer no veículo.

**Ocorrências**: CTRCs que já receberam ocorrências pelo SSWMobile 4 do veículo ou esta opção 155

**Devolver**: SAC instruiu que CTRCs desta fila devem retornar à filial

**Entregues**: Relação de CTRCs que receberam pré-entrega do SSWMobile 4 deste veículo ou opção 155

#### COLETA

**Coletar**: Relação de coletas disponíveis para coletar

**Vou coletar**: Relação de coletas já comandadas para o veículo

**Ocorrências**: Coletas que receberam ocorrências de coletas no SSWMobile 4 ou opção 155

**Coletados**: Coletas coletadas, informadas pelo SSWMobile 4 ou opção 155

### Tela 2 - Gravar Ocorrência no CTRC

#### Incluir Ocorrência

**Código**: Código da ocorrência auxiliar (opção 890)

**Complemento**: Texto complementar da ocorrência

## Integração com Outras Opções

- **Opção 208**: SAC cadastra instruções aos motoristas (complementar a esta opção)
- **Opção 890**: Cadastro de códigos de ocorrências auxiliares
- **SSWMobile 4**: Aplicativo móvel equivalente (esta opção é alternativa desktop)

## Observações e Gotchas

### Processo Completo

1. SAC cadastra instruções aos motoristas (opção 208) que se encontram entregando com uso do SSWMobile 4
2. Motoristas recebem instruções através do SSWMobile 4 e gravam ocorrências
3. Alternativamente ao SSWMobile 4, esta opção 155 pode executar as mesmas funções

### Cenário de Uso Ideal

Permite que motorista responsável por entregas em **regiões remotas** faça uso do micro em vez do smartphone, onde conectividade móvel pode ser limitada ou quando smartphone não está disponível.

### Filas de Instrução do SAC

Sistema organiza CTRCs em filas conforme instrução do SAC:
- **Entregar**: Seguir com entrega normal
- **Aguardar**: Reter no veículo temporariamente
- **Devolver**: Retornar à filial

### Sincronização com SSWMobile

As ocorrências e pré-entregas registradas nesta opção aparecem integradas com as do SSWMobile 4, permitindo uso intercambiável.

### Códigos de Ocorrência

Utiliza códigos auxiliares específicos (opção 890), diferentes dos códigos principais de ocorrências (opção 405).
