# Opção 409 — Remuneração de Veículos

> **Módulo**: Comercial
> **Páginas de ajuda**: 7 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função

Cadastra tabelas de remuneração para veículos de coleta/entrega (agregados e frota). Define como será calculado o pagamento aos proprietários de veículos que prestam serviços de coleta e entrega local.

## Quando Usar

- Ao contratar novo veículo agregado para coleta/entrega
- Ao ajustar valores de remuneração de veículos existentes
- Para configurar tabelas de veículos da frota (apenas para apuração de resultado, sem efeito financeiro)
- Antes de processar demonstrativos (opção 076) e emissão de OS (opção 075)

## Pré-requisitos

- Fornecedor (proprietário) cadastrado no sistema
- Veículo (placa) cadastrado
- Unidade principal definida
- Para replicação: unidades alternativas configuradas (opção 408) se necessário

## Campos / Interface

### Componentes da Tabela de Remuneração

A tabela pode incluir parcelas baseadas em:

- **Percentual sobre frete**: comissão calculada sobre o valor do frete (com ICMS)
- **Valor por entrega**: valor fixo por CTRC entregue
- **Valor por coleta**: valor fixo por CTRC coletado
- **Valor por quilometragem**: remuneração por KM rodado (requer digitação de odômetro via opção 093)
- **Diária**: valor fixo pago por dia de trabalho
- **Mínimo diário**: garantia de remuneração mínima por dia

### Opção 086 — Replicação de Tabelas

Permite copiar tabelas de remuneração para outros veículos:

- **Placa do veículo**: veículo de origem (com tabelas já cadastradas)
- **Unidade principal**: unidade das tabelas
- **Replicar para outras placas da mesma unidade**: permite informar múltiplas placas destino
- **Replicar para unidade alternativas**: copia para todas as unidades alternativas (opção 408)
- **Replicar todos os veículos da unidade principal para as unidades alternativas**: replicação em massa

## Fluxo de Uso

### Processo Normal (Manual)

```
1. Opção 409 → Cadastro de tabelas de remuneração por veículo
2. Opção 076 → Geração de demonstrativo (prévia) para conferência
3. Proprietário confere e aprova valores
4. Opção 075 → Processamento final:
   - Calcula remuneração
   - Emite OS (Ordem de Serviço)
   - Credita na CCF (Conta Corrente Fornecedor - opção 486)
5. Opção 486 → Acerto do saldo gera lançamento no Contas a Pagar (opção 475)
```

### Processo Automatizado

Pode ser configurado via **opção 903 / Agendar processamento**:

- Deve ser ativado também no cadastro do fornecedor (opção 478)
- Executa automaticamente as funções das opções 076 e 075
- Considera apenas períodos com Romaneios de Entregas baixados (com ocorrências)
- Coleta é paga conforme placa informada no CTRC
- Demonstrativo enviado por e-mail ao fornecedor
- Disponibilizado na opção 056 (relatório 276)

### Opção 093 — Digitação de Odômetro

Para remuneração por KM rodado:

- **KM inicial**: odômetro antes de sair para entregas/coletas
- **KM final**: odômetro após retorno à unidade
- **Percorrido**: diferença entre KM final e inicial (usado no cálculo)
- Período máximo: 30 dias retroativos
- **ATENÇÃO**: usar com cuidado, alterações afetam demonstrativos e pagamentos

## Integração com Outras Opções

### Opções Relacionadas ao Processo

- **Opção 076**: Demonstrativo de Remuneração (prévia sem pagamento)
- **Opção 075**: Emissão de OS de Coleta/Entrega (processamento final)
- **Opção 086**: Replicação de tabelas entre veículos
- **Opção 093**: Digitação de odômetro (para remuneração por KM)
- **Opção 118**: OS Avulso (remuneração excepcional sem vínculo a CTRCs)

### Opções de Controle Financeiro

- **Opção 486**: Conta Corrente do Fornecedor (débitos/créditos)
- **Opção 475**: Contas a Pagar (acerto de saldo da CCF)
- **Opção 478**: Cadastro de fornecedores (e-mail, ativação de automação)

### Opções de Análise de Resultado

- **Opção 056**: Relatórios gerenciais
  - **Relatório 022**: Resultado Mensal das Coletas e Entregas
  - **Relatório 023**: Resultado das Coletas/Entregas (diário, meio-dia)
  - **Relatório 024**: Resultado das Coletas/Entregas Realizadas
  - **Relatório 276**: Demonstrativo de remuneração automatizada
- **Opção 324**: Avaliação de resultados dos veículos
- **Opção 101**: Resultado do CTRC (custo coleta/entrega embutido na comissão da unidade)

### Opções Operacionais

- **Opção 003**: Romaneios de Coleta (geram remuneração)
- **Opção 035**: Romaneios de Entrega (geram remuneração)
- **Opção 408**: Unidades alternativas (para replicação)
- **Opção 431**: Armazém (unidades do mesmo armazém reconhecem CTRCs entre si)
- **Opção 903**: Configuração de automação

## Observações e Gotchas

### Período e Cálculos

- **Coletas**: período de autorização do CT-e
  - Autorizações entre 0:00h e 06:00h são consideradas no dia anterior
- **Entregas**: período de emissão de Romaneios de Entrega
- **Data do cálculo**: remuneração da entrega é considerada na data de emissão do Romaneio, não na data da ocorrência
- **Apenas Romaneios baixados**: só são considerados Romaneios com todos os CTRCs com ocorrências recebidas

### Base de Cálculo

- **Valores de frete**: sempre integrais (com ICMS incluído)
- **CTRCs reentregados**: contabilizados mais de uma vez na remuneração (FRTPROP)

### Veículos da Frota

- Podem ter tabelas cadastradas pela opção 409 sem efeito financeiro
- Serve apenas para cálculo de resultado e análise de desempenho
- **Ociosidade da frota**: opção 903 pode configurar uso de tabelas de outros veículos do mesmo tipo para identificar ociosidade

### Impostos e Retenções

- **Pessoa Física**: crédito via OS, retenções ocorrem apenas no acerto do saldo da CCF
- Emissão de CTRB/RPA (Contrato de Transporte Rodoviário de Bens / Recibo de Pagamento de Autônomo)

### Unidades do Mesmo Armazém

- CTRCs de unidades do mesmo armazém (opção 431) são reconhecidos
- Todo o processo (opção 409, 076 e 075) deve ser executado na mesma unidade

### Índices de Resultado

- **A/B**: REMUNERAÇÃO / FRETES ROMANEADOS (comprometimento sobre CTRCs romaneados)
- **A/C**: REMUNERAÇÃO / FRETES ENTREGUES (comprometimento sobre CTRCs efetivamente entregues)
- **A/C sempre maior ou igual a A/B** (CTRCs romaneados nem sempre são entregues)
- **Custo coleta/entrega NÃO aparece na opção 101/Resultado**: está embutido no comissionamento das unidades expedidora e receptoras

### Pontos de Atenção

- **Opção 076 não processa pagamentos**: é apenas demonstrativo/prévia
- **Dia de hoje no período**: só incluir se todas as operações estiverem concluídas (diárias e mínimos podem ficar incorretos)
- **Opção 093 (odômetro)**: alterações afetam demonstrativos e pagamentos, usar com cuidado
- **Opção 118 (OS Avulso)**: não usa tabelas da opção 409, é remuneração excepcional manual

### Remuneração no Modelo de Resultados

- O custo de coleta/entrega está embutido na comissão das unidades
- É por conta da filial ou parceiro
- Não aparece como parcela de despesas na opção 101/Resultado
- Avaliação via relatórios específicos: 022, 023, 024

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A04](../pops/POP-A04-cadastrar-rotas.md) | Cadastrar rotas |
