# Opção 924 — Conversão de Ocorrências da Subcontratada

> **Módulo**: Sistema (Controle)
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Cadastra tabela de conversão de ocorrências da subcontratada para atualização automática de CTRCs da subcontratante quando ambas utilizam o SSW.

## Quando Usar
- Configurar conversão automática de ocorrências entre transportadoras SSW
- Definir DE-PARA de códigos de ocorrências da subcontratada para a subcontratante
- Permitir rastreamento de mercadorias em subcontratos

## Pré-requisitos
- Subcontratante (emissor CTRC ORIGEM) usando SSW
- Subcontratada (emissor SUBCONTRATO) usando SSW
- Domínio da subcontratada conhecido

## Processo

### Conversão Automática

```
Subcontratada - Lança ocorrências no SUBCONTRATO
         ↓
Tabela DE-PARA (opção 924)
         ↓
Subcontratante - CTRC ORIGEM atualizado automaticamente
```

### Instruções (Caminho Inverso)

```
Subcontratante - Lança instruções no CTRC ORIGEM
         ↓
Subcontratada - SUBCONTRATO atualizado automaticamente
```

### Subcontratos em Cadeia

```
CTRC ORIGEM → SUBCONTRATO → SUBCONTRATO de SUBCONTRATO
         ↓              ↓                    ↓
   Atualização automática em toda cadeia
```

## Campos / Interface

### Tela Inicial

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **DOMÍNIO** | Sim | Domínio da transportadora subcontratada |

### Tela Seguinte

- **Tabela de ocorrências da subcontratada** é apresentada
- Subcontratante informa código de ocorrência correspondente para conversão

| Coluna | Descrição |
|--------|-----------|
| **Código subcontratada** | Código de ocorrência da subcontratada (origem) |
| **Descrição** | Descrição da ocorrência da subcontratada |
| **Código subcontratante** | Código correspondente na tabela da subcontratante (informar) |

## Fluxo de Uso

1. Subcontratante acessa opção 924
2. Informa domínio da subcontratada
3. Sistema apresenta tabela de ocorrências da subcontratada
4. Subcontratante informa códigos correspondentes de conversão
5. Confirma cadastro
6. Ocorrências lançadas no SUBCONTRATO atualizam CTRC ORIGEM automaticamente

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 101 | CTRC ORIGEM (subcontratante) |
| 108 | Visualiza ocorrências lançadas pela subcontratada no SUBCONTRATO |

## Observações e Gotchas

### Requisito: Ambas SSW
- Conversão automática só funciona se **ambas** transportadoras usam SSW
- Se subcontratada não usa SSW: usar opção 908 (tabela DE-PARA para arquivos EDI)

### Conversão de Ocorrências
- Ocorrências do **SUBCONTRATO** atualizam **CTRC ORIGEM** automaticamente
- Base: tabela DE-PARA cadastrada nesta opção 924

### Instruções (Caminho Inverso)
- Instruções do **CTRC ORIGEM** atualizam **SUBCONTRATO** automaticamente
- Não requer configuração adicional

### Subcontratos de Subcontratos
- Atualização automática ocorre em toda cadeia
- Exemplo: ORIGEM → SUB1 → SUB2
- Ocorrência em SUB2 atualiza SUB1 e ORIGEM

### Visualização de Ocorrências do Parceiro
- Subcontratante visualiza ocorrências da subcontratada via opção 108
- Mesmo sem conversão, pode consultar

### Diferença opção 924 vs 908
- **924**: Conversão entre transportadoras SSW (subcontrato)
- **908**: Conversão para clientes/parceiros via EDI (arquivos)

### Cadastro por Subcontratante
- Subcontratante (emissor CTRC ORIGEM) cadastra a tabela
- Subcontratada (emissor SUBCONTRATO) não precisa configurar

### Código Correspondente
- Deve existir na tabela de ocorrências da subcontratante
- Se não informado, ocorrência não é convertida (mas fica visível na opção 108)
