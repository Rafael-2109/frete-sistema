# Opção 402 — Cadastro de Cidades Atendidas

> **Módulo**: Cadastros
> **Páginas de ajuda**: 6 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Define as cidades atendidas pela transportadora, vinculando-as às unidades operacionais e comerciais. Atribui classificação de pólo, região ou interior para diferenciação operacional e comercial.

## Quando Usar
- Configurar novas cidades atendidas pela transportadora
- Definir unidades responsáveis por coleta e entrega em cada cidade
- Configurar prazos de entrega por cidade
- Definir classificação de praças comerciais (pólo, região, interior)
- Configurar taxas de difícil acesso (TDA), SUFRAMA, valores de coleta/entrega
- Cadastrar feriados municipais
- Definir dias de semana para coletas/entregas
- Configurar alíquota ISS para emissão de NFS-e

## Pré-requisitos
- Opção 401: Cadastro de unidades operacionais
- Opção 060: Cadastro de feriados estaduais (opcional)
- Opção 944: Atualização de CEPs das cidades (automática quinzenal)

## Campos / Interface

### Tela Inicial

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| UF | Não | Traz todas as cidades da UF para alterações |
| Unidade | Não | Traz todas as cidades atendidas pela unidade |
| Cidade/UF | Não | Traz a cidade informada para alteração |

### Tela Principal

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Unidade | Sim | Unidade (opção 401) que atende a cidade operacionalmente. Para cidades não atendidas pode-se cadastrar unidade FEC |
| Pólo, Região e Interior | Sim | P=cidade próxima da sede, R=média, I=distante. Define a "Praça Operacional" (sigla unidade + P/R/I) |
| Tipo de frete | Sim | C=CIF, F=FOB, A=ambos |
| Restrita | Sim | Quando Coleta=N ou Entrega=N, com Restrita=S permite atender clientes cadastrados na opção 134 |
| Coleta | Sim | S=transportadora efetua coletas na cidade (opção 001) |
| Entrega | Sim | S=transportadora faz entregas na cidade |
| Prazo de entrega | Sim | Prazo de entrega em dias úteis partindo da sede da unidade (considera feriados municipais, estaduais e federais) |
| Prazo e-commerce | Não | Prazo de entrega específico para mercadorias de e-commerce (opção 406) |
| Quantidade de pedágios | Não | Quantidade de postos de pedágio entre a unidade e a cidade |
| Distância | Não | Distância em Km da sede da unidade até a cidade. Se não informado, SSW calcula via Google Maps |
| Valor TDA | Não | Taxa de Difícil Acesso em R$ acrescida no frete. Prioridade: opção 404 (CEP) > opção 423 (cliente) > opção 402 |
| Valor SUFRAMA | Não | Valor em R$ + 1% do valor da mercadoria para Zona Franca de Manaus. Prioridade: tabelas de frete > opção 402 |
| Valor Coleta/Entrega | Não | Valor em R$ cobrado via Tabela Genérica (opção 923) quando ocorrer coleta ou entrega |
| Praça Comercial | Não | Sugerida automaticamente. Formada por sigla da unidade + P/R/I. Define origem/destino de tabelas de fretes |

### Link MAIS (Complementos)

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Observações | Não | Utilizada na cotação (opção 002) |
| Coletas/entregas | Não | Dias de semana que coletas/entregas são realizadas |
| Feriados municipais | Não | Já sugeridos pelo SSW com dados da FEBRABAN |
| Alíquota ISS | Não | Normal ou Substituição Tributária para emissão RPS/NFS-e (opção 004, 005, 006) |

## Fluxo de Uso

### Cadastrar Nova Cidade Atendida
1. Acessar opção 402
2. Selecionar UF ou Unidade
3. Localizar cidade desejada
4. Informar unidade responsável
5. Definir classificação (Pólo, Região ou Interior)
6. Configurar tipos de frete permitidos
7. Informar se faz coleta e/ou entrega
8. Definir prazo de entrega
9. Configurar valores opcionais (TDA, distância, pedágios)
10. Salvar configuração

### Replicar Configurações
1. Configurar uma cidade modelo
2. Clicar no link REPLICAR
3. Selecionar cidades destino
4. Sistema calcula distância automaticamente via Google

### Importar Dados de Parceiro
1. Clicar em "Importar dados do parceiro"
2. Informar CNPJ do parceiro que usa SSW
3. Escolher tipo de importação:
   - Importar cidades não atendidas
   - Importar cidades atendidas por minha unidade
   - Importar todas as cidades do parceiro
4. **ATENÇÃO**: Operação não pode ser revertida

### Atualizar Prazos em Lote
- Usar opção 121 para trocar prazos de entrega em lote (por UF, Unidade ou Praça)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 001 | Cadastro de coletas (usa cidades com Coleta=S) |
| 002 | Cotação de frete (usa observações das cidades) |
| 004, 005, 006 | Emissão de CTRCs e NFS-e (usa alíquota ISS) |
| 060 | Cadastro de feriados estaduais (usado no cálculo de prazo de entrega) |
| 121 | Ajuste de prazos de entrega em lote |
| 134 | Clientes com atendimento diferenciado (para cidades restritas) |
| 395 | Escolha automática de unidade alternativa |
| 401 | Cadastro de unidades (define unidades responsáveis) |
| 403 | Cadastro de rotas (usa quantidade de pedágios) |
| 404 | Setores de coleta/entrega (define TDA por faixa de CEP) |
| 417, 418, etc | Tabelas de fretes (usam praças comerciais) |
| 420 | Tabela de fretes promocionais |
| 423 | Tabelas de fretes por cliente (pode definir TDA específico) |
| 427 | Tabela genérica de fretes |
| 696 | Prazo de entrega específico por cliente |
| 923 | Tabela genérica (usa valores de coleta/entrega) |
| 944 | Atualização de CEPs das cidades |

## Observações e Gotchas

### Praça Operacional vs Praça Comercial
- **Praça Operacional**: Define a operação real da transportadora (unidade + P/R/I)
- **Praça Comercial**: Usada em tabelas de fretes. Permite que várias praças operacionais (inclusive FEC) adotem a mesma praça comercial, reduzindo quantidade de tabelas

### Operações FEC (Fechada ou Completa)
- Cidade com operação FEC não precisa ser configurada nesta opção
- Pode ser cadastrada como FEC se quiser definir praça comercial para cálculo de frete

### Cálculo de Previsão de Entrega
- Considera: prazo de entrega da cidade + prazo de transferência (opção 403)
- Feriados considerados: municipais, estaduais e federais
- Prazo de entrega específico para e-commerce (se configurado)
- Prazo específico por tipo de mercadoria tem prioridade sobre prazo padrão

### Faixas de CEPs
- Baseadas nos Correios
- Alterações podem ser feitas pela opção 944 (com cuidado)
- SSW atualiza CEPs quinzenalmente com dados dos Correios (desde 2026)

### Atualização Automática
- SSW ajusta automaticamente Unidade Responsável e Unidade de Cobrança à Unidade Operacional (diariamente)
- Clientes configurados para ajuste manual (opção 483) não são alterados automaticamente
- Divergências são listadas na opção 090

### Taxas e Valores
- **TDA (Taxa de Difícil Acesso)**: Prioridade → opção 404 (CEP) > opção 423 (cliente) > opção 402 (cidade)
- **SUFRAMA**: Para subcontratação/redespacho, considera cidade origem (expedição) ou destino (recepção)
- **SUFRAMA nas tabelas**: Valor das tabelas de frete tem prioridade sobre opção 402
- **Valor Coleta/Entrega**: Cobrado via Tabela Genérica (opção 923)

### Unidades Alternativas
- Opção 395 permite trocar unidade de coleta/entrega automaticamente
- Mudança tem efeito apenas operacional (não afeta cálculo de frete nem questões fiscais)
- Apenas um critério de unidade alternativa pode ser escolhido por unidade principal

### Importação e Exportação
- Função "Baixar arquivo CSV / Importar" permite alterações em massa
- Importação de parceiro é irreversível - usar com cuidado
- Função "Trocar unidades" permite substituir unidades mantendo classificações

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A01](../pops/POP-A01-cadastrar-cliente.md) | Cadastrar cliente |
| [POP-A02](../pops/POP-A02-cadastrar-unidade-parceira.md) | Cadastrar unidade parceira |
| [POP-A03](../pops/POP-A03-cadastrar-cidades.md) | Cadastrar cidades |
| [POP-A04](../pops/POP-A04-cadastrar-rotas.md) | Cadastrar rotas |
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
| [POP-A10](../pops/POP-A10-implantar-nova-rota.md) | Implantar nova rota |
| [POP-B01](../pops/POP-B01-cotar-frete.md) | Cotar frete |
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
| [POP-C01](../pops/POP-C01-emitir-cte-fracionado.md) | Emitir cte fracionado |
