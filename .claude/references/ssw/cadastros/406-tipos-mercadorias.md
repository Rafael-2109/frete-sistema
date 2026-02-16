# Opção 406 — Cadastro de Tipos de Mercadorias

> **Módulo**: Cadastros
> **Páginas de ajuda**: 7 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Cadastra tipos de mercadorias para diferenciar tabelas de fretes de clientes, definir densidade para cálculo de frete, configurar mercadorias prioritárias, prazos de entrega específicos e restrições de unidades expedidoras.

## Quando Usar
- Criar novos tipos de mercadoria para diferenciação comercial
- Configurar densidade específica para cálculo de frete
- Definir mercadorias prioritárias no carregamento
- Estabelecer prazos de entrega diferenciados por tipo de mercadoria
- Restringir unidades expedidoras para tipos específicos
- Marcar mercadorias não tributadas (livros, revistas, jornais)
- Sugerir tipo de mercadoria automaticamente via NCM (opção 207)
- Configurar comissionamento específico por mercadoria (opção 408)
- Definir unidades alternativas por tipo de mercadoria (opção 430)

## Pré-requisitos
- Nenhum pré-requisito obrigatório para cadastro básico
- Para uso em tabelas de frete: cliente deve estar cadastrado (opção 483)

## Campos / Interface

### Opção 010 - Relação de Tipos de Mercadorias

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Código | Sim | Código identificador do tipo de mercadoria |
| Descrição | Sim | Nome/descrição do tipo de mercadoria |
| TRIBUTADA | Sim | N=não ocorre tributação ICMS do CTRC (livros, revistas, jornais, etc.) |
| DENSIDADE | Não | Quando menor que 300 m³, sistema sugere cubagem na emissão do CTRC |
| CALC FRTE | Sim | S=usa densidade informada acima para calcular frete, N=usa densidade do cliente/transportadora (opção 423) |
| PRIORITARIO | Sim | S=CTRCs com este tipo têm prioridade no carregamento de Manifestos (opção 020) e Romaneios (opção 035) |
| PZOENTR | Não | Prazo de entrega em dias úteis específico da mercadoria (prioridade sobre prazo padrão) |
| UNIDADES DE EXPEDIÇÃO | Não | Unidades expedidoras restritas para uso desta mercadoria |

## Fluxo de Uso

### Cadastrar Novo Tipo de Mercadoria
1. Acessar opção 406
2. Informar código (numérico ou alfanumérico)
3. Definir descrição clara
4. Marcar TRIBUTADA (N para livros/revistas/jornais)
5. Configurar densidade (se aplicável)
6. Definir se usa densidade para cálculo de frete
7. Marcar como PRIORITARIO (se aplicável)
8. Configurar prazo de entrega específico (se aplicável)
9. Restringir unidades expedidoras (se aplicável)
10. Salvar tipo de mercadoria

### Vincular ao Cliente (opção 483/Mercadorias)
1. Acessar cadastro do cliente (opção 483)
2. Aba/seção Mercadorias
3. Vincular tipos de mercadoria ao cliente
4. Sistema usará para diferenciação de tabelas de frete

### Sugestão Automática via NCM (opção 207)
1. Cadastrar relação NCM → Tipo de Mercadoria na opção 207
2. Na emissão do CTRC (opções 004 e 006), tipo será sugerido automaticamente
3. NCM é lido do XML da NF-e
4. Se diversos NCMs no CT-e, escolhe o de maior valor de mercadoria

### Uso em Tabelas de Frete
- Permite ter múltiplas tabelas para mesmo cliente diferenciadas por tipo de mercadoria
- Tipo de mercadoria é parâmetro nas opções de tabelas de frete (417, 418, 501, etc.)
- Ordem de prioridade na escolha da tabela considera o tipo de mercadoria

### Configurar Comissionamento Específico
- Opção 408 permite definir comissão diferenciada por tipo de mercadoria
- Comissão por mercadoria tem prioridade sobre comissão geral

### Definir Unidade Alternativa
- Opção 430 permite definir unidade alternativa por tipo de mercadoria
- Útil para entregas prioritárias através de parceiros específicos

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 004, 005, 006 | Emissão de CTRCs (informa tipo de mercadoria) |
| 010 | Relação de tipos de mercadorias (consulta) |
| 020 | Emissão de Manifestos (usa PRIORITARIO para ordenação) |
| 035 | Romaneios de entrega (usa PRIORITARIO para ordenação) |
| 207 | NCM define Tipo de Mercadoria (sugestão automática) |
| 395 | Escolha automática de unidade alternativa por tipo de mercadoria |
| 408 | Comissão de unidade por mercadoria (diferenciação comercial) |
| 409 | Tabela de remuneração de veículos por mercadoria |
| 417, 418, 501, etc. | Tabelas de fretes (diferenciação por tipo de mercadoria) |
| 420 | Tabelas promocionais (pode usar tipo de mercadoria) |
| 423 | Configuração de densidade padrão do cliente (usado quando CALC FRTE=N) |
| 430 | Cadastro de unidade por tipo de mercadoria (embarcador) |
| 483 | Cadastro de clientes (vinculação de tipos de mercadoria) |
| 696 | Prazo de entrega específico por cliente (tipo de mercadoria tem prioridade) |

## Observações e Gotchas

### Tributação ICMS
- Mercadorias com TRIBUTADA=N não têm ICMS destacado no CTRC
- Usado para: livros, revistas, jornais e papel destinado à sua impressão
- Isenção baseada na Constituição Federal, Art. 150, inciso VI, "d"
- Deve ser parametrizada pelo código de mercadoria usado na emissão (opção 004)

### Densidade e Cálculo de Frete
- **DENSIDADE < 300 m³**: Sistema sugere cubagem na emissão do CTRC
- **CALC FRTE = S**: Usa densidade informada no cadastro do tipo de mercadoria
- **CALC FRTE = N**: Usa densidade do cliente (opção 483) ou transportadora (opção 423)
- Densidade afeta o peso cubado usado no cálculo do frete

### Mercadorias Prioritárias
- **PRIORITARIO = S**: CTRCs com este tipo têm prioridade no carregamento
- Aplica-se em:
  - Manifestos de transferência (opção 020)
  - Romaneios de entrega (opção 035)
- Útil para mercadorias com prazo apertado ou alto valor agregado

### Prazo de Entrega
- **PZOENTR**: Sobrepõe prazo padrão da cidade (opção 402) e do cliente (opção 696)
- Contado em dias úteis
- Permite SLA diferenciado por tipo de mercadoria (ex: e-commerce express)
- Tem prioridade sobre todos os outros prazos configurados

### Restrição de Unidades Expedidoras
- Permite limitar quais unidades podem transportar determinado tipo de mercadoria
- Útil para:
  - Mercadorias perigosas (apenas unidades autorizadas)
  - Operações especializadas (refrigerados, farmacêuticos, etc.)
  - Controle comercial (direcionar para parceiros específicos)
- Opção 395 também pode restringir unidades por tipo de mercadoria

### Tabelas de Frete
- Tipo de mercadoria é parâmetro chave para diferenciação de tabelas
- Permite cobrar valores diferentes para mesmo cliente conforme mercadoria
- Ordem de busca de tabela considera tipo de mercadoria
- Tabela genérica (CNPJ MTZ sem código de mercadoria) inutiliza tabela da Rota

### Sugestão Automática via NCM
- Opção 207 relaciona NCM do XML → Tipo de Mercadoria
- Na emissão do CTRC, tipo é sugerido automaticamente
- Se XML tiver múltiplos NCMs tabelados, escolhe o de maior valor de mercadoria
- Também sugere Espécie de Mercadoria (opção 407) para gerenciamento de risco

### Diferença entre Tipo e Espécie
- **Tipo de Mercadoria (opção 406)**: Usado para diferenciação de tabelas de frete e prazo de entrega
- **Espécie de Mercadoria (opção 407)**: Usado para gerenciamento de risco (opção 390)
- Ambos podem ser sugeridos automaticamente via NCM (opção 207)
- Podem ser vinculados ao cliente (opção 483)

### Comissionamento e Remuneração
- Opção 408: Comissão de unidade pode ser diferenciada por tipo de mercadoria
- Opção 409: Remuneração de agregados pode variar por tipo de mercadoria
- Permite incentivar transporte de mercadorias específicas

### Simulação de Tabelas
- Opção 400 permite simular cálculo de frete usando tabelas de outros clientes
- Tipo de mercadoria deve ser informado na simulação
- Útil para elaborar propostas comerciais

### Unidade Alternativa por Tipo (Embarcador)
- Opção 430: Embarcador pode definir unidade alternativa por tipo de mercadoria
- Permite contratar transportadoras diferentes por tipo de mercadoria na mesma região
- Parâmetros operacionais (prazo, distância) são da unidade principal
