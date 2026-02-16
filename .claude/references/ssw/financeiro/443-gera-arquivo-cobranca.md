# Opção 443 — Gera Arquivo de Cobrança (CNAB Remessa)

> **Módulo**: Financeiro
> **Páginas de ajuda**: 1 página consolidada (referenciada na opção 444)
> **Atualizado em**: 2026-02-14

## Função
Gera arquivo de remessa de cobrança bancária no formato CNAB para envio ao banco. Inclui faturas/boletos para processamento bancário (registro, alterações, baixas, protestos).

## Quando Usar
- Após faturamento (opção 436, 437)
- Para registrar boletos no banco
- Para enviar alterações de vencimento, abatimentos, protestos
- Diariamente para incluir novas faturas na cobrança bancária

## Pré-requisitos
- Faturas emitidas com cobrança bancária (opção 436, 437)
- Banco/carteira configurado (opção 904)
- Cliente com tipo de cobrança = B (Via banco) na opção 384

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Banco** | Sim | Banco da cobrança (opção 904) |
| **Período de faturas** | Não | Filtro por data de emissão das faturas |
| **Tipo de remessa** | Sim | Inclusão, alteração, baixa, protesto |

## Abas / Sub-telas

**Seleção:**
- Faturas disponíveis para remessa
- Filtros por banco, período, tipo

**Geração:**
- Confirma geração do arquivo CNAB
- Download do arquivo

## Fluxo de Uso

1. Acessar opção 443
2. Selecionar banco
3. Escolher tipo de remessa:
   - Inclusão: Novas faturas
   - Alteração: Vencimentos, abatimentos
   - Baixa: Cancelamento de boletos
   - Protesto: Envio para protesto
4. Aplicar filtros (opcional)
5. Gerar arquivo CNAB
6. Baixar arquivo
7. Enviar ao banco via site internet
8. Aguardar processamento
9. Importar retorno (opção 444)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 384 | Define tipo de cobrança do cliente (B=banco) |
| 436 | Faturamento geral (gera faturas para cobrança) |
| 437 | Faturamento manual (gera arquivo específico da fatura) |
| 444 | Recepciona arquivo de retorno da cobrança |
| 446 | Monitora trocas de arquivos com bancos |
| 457 | Controle de faturas (pode gerar arquivo individual) |
| 483 | Clientes especiais (excluídos de protesto) |
| 904 | Cadastro de bancos e carteiras (parâmetros de cobrança) |

## Observações e Gotchas

- **Ordem cronológica**: Arquivos devem ser enviados e importados em ordem
- **Banco Itaú**: Faturas descontadas exigem carteira tipo "Carteira Desconto" (opção 904)
- **Envio manual**: Arquivo deve ser enviado ao banco via site internet
- **Retorno obrigatório**: Importar retorno diariamente antes 09:30h (avisos de atraso)
- **Cobrança automatizada**: API processa remessa e retorno automaticamente às 23:00h (Itaú, Sicred, Bradesco)
- **Protesto**: Configurado por cliente (opção 384) ou banco (opção 904)
- **Clientes especiais**: Excluídos de protesto (opção 483)
- **Arquivo individual**: Opção 437 pode gerar arquivo exclusivo de uma fatura
- **Tarifas**: Banco cobra tarifas que podem ser repassadas ao cliente (opção 384)
- **Rastreamento**: Opção 446 monitora todas as trocas de arquivos
- **Críticas**: Arquivo de retorno (opção 444) traz críticas do banco

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-E04](../pops/POP-E04-cobranca-bancaria.md) | Cobranca bancaria |
| [POP-E06](../pops/POP-E06-manutencao-faturas.md) | Manutencao faturas |
