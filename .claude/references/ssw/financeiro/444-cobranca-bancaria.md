# Opção 444 — Cobrança Bancária (Retorno)

> **Módulo**: Financeiro
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Recepciona e processa arquivos de retorno de cobrança bancária enviados pelos bancos. Atualiza situação das faturas/boletos com base em ocorrências bancárias (liquidação, entrada confirmada, rejeição, alterações, tarifas, etc.).

## Quando Usar
- Após o banco processar arquivo de remessa (opção 443)
- Diariamente antes das 09:30h (antes do envio de avisos de atraso)
- Quando houver liquidações, confirmações ou alterações de boletos
- Para contabilização automática dos recebimentos

## Pré-requisitos
- Arquivo de remessa previamente gerado e enviado ao banco (opção 443)
- Arquivo de retorno disponibilizado pelo banco
- Banco/carteira configurado na opção 904

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Arquivo de retorno** | Sim | Arquivo fornecido pelo banco com ocorrências dos boletos |
| **Período** | Não | Filtro para relatórios de ocorrências por período |

## Abas / Sub-telas

**Importação:**
- Upload do arquivo de retorno
- Validação e processamento das ocorrências

**Relatórios:**
- **Opção 460**: Valores de retornos por ocorrência bancária
- **Opção 446**: Monitora trocas de arquivos com bancos

## Fluxo de Uso

1. Baixar arquivo de retorno do banco
2. Acessar opção 444
3. Fazer upload do arquivo de retorno
4. Sistema processa ocorrências:
   - **002**: Entrada confirmada
   - **003**: Entrada rejeitada
   - **005**: Liquidação sem registro
   - **006**: Liquidação normal
   - **010**: Sustação de protesto / Baixa de título
   - **012**: Abatimento concedido
   - **014**: Vencimento alterado
   - **028**: Débito de tarifa/custas
5. Verificar processamento no relatório (opção 460)
6. Conferir liquidações e pendências

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 443 | Gera arquivo de remessa de cobrança bancária |
| 446 | Monitora trocas de arquivos com bancos no período |
| 457 | Controle de faturas (consulta ocorrências bancárias) |
| 460 | Relatório de valores de retornos por ocorrência |
| 480 | Promessas de pagamento (consideradas no aviso de atraso) |
| 541 | Lançamentos automáticos contábeis (sequência 11 para liquidações) |
| 548 | Livro Razão (analítico 1 relaciona faturas via retorno bancário) |
| 904 | Cadastro de bancos e carteiras |
| 912 | Ocorrências bancárias (configuração para cobrar despesas) |

## Observações e Gotchas

- **Importar antes das 09:30h**: Sistema envia avisos de atraso às 09:30h, considerar retornos importados
- **Códigos de ocorrência**: Variam de banco para banco (verificar opção 912)
- **Contabilização automática**:
  - Liquidação (006): Crédito sequência 13/14, Débito sequência 63/11
  - Com juros: Crédito sequência 33, Débito sequência 13/14
  - Com desconto: Crédito sequência 13/14, Débito sequência 35
- **Tarifas bancárias**: Podem ser repassadas ao cliente (configurar opção 384)
- **Despesas de retorno**: Cobradas na próxima fatura (se configurado opção 912)
- **Livro Razão**: Analítico 1 relaciona faturas liquidadas (sequencial 11, opção 548)
- **Cobrança automatizada**: API processa retornos automaticamente às 23:00h (Itaú, Sicred)
- **Arquivo morto**: Faturas liquidadas há 90+ dias vão para arquivo morto
- **Rastreamento**: Opção 446 permite monitorar todas as trocas de arquivos com banco

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-E03](../pops/POP-E03-faturamento-automatico.md) | Faturamento automatico |
| [POP-E04](../pops/POP-E04-cobranca-bancaria.md) | Cobranca bancaria |
| [POP-E06](../pops/POP-E06-manutencao-faturas.md) | Manutencao faturas |
