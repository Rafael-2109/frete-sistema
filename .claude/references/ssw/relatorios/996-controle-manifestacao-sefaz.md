# Opção 996 — CT-e em Desacordo e Desconhecimento NF-e

> **Módulo**: Sistema (Controle)
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Manifesta ao SEFAZ que CT-es (transportes) e NF-es (mercadorias) não foram adquiridas por esta transportadora, atualizando automaticamente Contas a Pagar.

## Quando Usar
- Manifestar prestação de serviço de transporte em desacordo (CT-e não contratado)
- Manifestar desconhecimento de aquisição de mercadoria (NF-e não adquirida)
- Evitar lançamento indevido no Contas a Pagar
- Corrigir CT-e emitido erradamente (substituição)

## Pré-requisitos
- Inscrição Estadual da transportadora
- CNPJ pagador (para CT-e)
- Chave do CT-e ou NF-e

## Processo

### Prestação CT-e em Desacordo

```
Outra transportadora emite CT-e (Subcontrato/Redespacho)
         ↓
Esta transportadora não contratou
         ↓
Opção 996 - Manifesta "Prestação em desacordo" ao SEFAZ
         ↓
Opção 475 e 582 - Atualizados automaticamente
```

### Desconhecimento NF-e

```
Fornecedor emite NF-e
         ↓
Esta transportadora não adquiriu mercadoria
         ↓
Opção 996 - Manifesta "Desconhecimento da operação" ao SEFAZ
         ↓
Opção 475 e 582 - Atualizados automaticamente
```

## Campos / Interface

### Prestação em Desacordo (CT-e)

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Inscrição Estadual** | Sim | IE desta transportadora que está manifestando o serviço em desacordo |
| **CNPJ pagador** | Sim | CNPJ desta transportadora que está como pagadora do CT-e em desacordo |
| **Chave CT-e** | Sim | Chave do CT-e em desacordo (44 dígitos) |

### Desconhecimento da Operação (NF-e)

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Chave NF-e** | Sim | Chave da NF-e desconhecida (44 dígitos) |

## Fluxo de Uso

### Manifestar CT-e em Desacordo

1. Identificar CT-e não contratado
2. Obter chave do CT-e
3. Acessar opção 996
4. Informar Inscrição Estadual
5. Informar CNPJ pagador
6. Informar chave CT-e
7. Confirmar manifestação
8. SEFAZ é notificado automaticamente
9. Opção 475 e 582 atualizadas

### Manifestar Desconhecimento NF-e

1. Identificar NF-e não adquirida
2. Obter chave da NF-e
3. Acessar opção 996
4. Informar chave NF-e
5. Confirmar manifestação
6. SEFAZ é notificado automaticamente
7. Opção 475 e 582 atualizadas

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 475 | Contas a Pagar - atualizado automaticamente |
| 520 | Substituição de CT-e (alternativa para CT-e emitido erradamente) |
| 582 | Movimentação financeira - atualizada automaticamente |

## Observações e Gotchas

### CT-e em Desacordo vs Substituição
- **CT-e em desacordo** (opção 996): manifesta ao SEFAZ que **não contratou** serviço de outra transportadora
- **Substituição** (opção 520): **própria transportadora** emitiu CT-e erradamente e substitui por novo (CT-e substituído é cancelado automaticamente)

### Uso Correto
- **Opção 996**: quando CT-e/NF-e de **terceiros** não foi contratado/adquirido
- **Opção 520**: quando **própria transportadora** errou na emissão

### Atualização Automática
- Opção 475 (Contas a Pagar) atualizada automaticamente
- Opção 582 (Movimentação financeira) atualizada automaticamente
- Não requer ajustes manuais

### Legislação
- Manifestação prevista em legislação SEFAZ
- Consultar link AQUI (na opção) para detalhes legais

### Chave de 44 Dígitos
- CT-e e NF-e possuem chave de acesso de 44 dígitos
- Copiar exatamente como recebida (sem espaços ou formatação)

### IE e CNPJ Pagador
- **IE**: da transportadora manifestando
- **CNPJ pagador**: da transportadora que consta no CT-e como pagadora
- Ambos devem ser da mesma empresa (esta transportadora)

### Diferença CT-e vs NF-e
- **CT-e**: prestação de serviço de transporte
- **NF-e**: aquisição de mercadoria
- Campos diferentes na manifestação

### Quando NÃO Usar
- CT-e emitido pela própria transportadora com erro: usar opção 520 (substituição)
- CT-e contratado mas com divergências: ajustar via opção 475 diretamente
- NF-e adquirida mas com divergências: ajustar via opção 475 diretamente

### Consequências da Manifestação
- SEFAZ registra manifestação
- Emissor (CT-e/NF-e) é notificado
- Contas a Pagar não considera documento
- Documentação legal preservada
