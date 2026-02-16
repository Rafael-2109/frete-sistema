# Opção 436 — Faturamento Geral

> **Módulo**: Financeiro
> **Páginas de ajuda**: 6 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Executa o faturamento automático de todos os CTRCs disponíveis para faturar conforme regras cadastradas no cliente. Agrupa CTRCs em faturas seguindo as parametrizações de periodicidade, separação e vencimento definidas no cadastro do cliente (opção 384).

## Quando Usar
- Faturamento mensal, quinzenal, decenal, semanal ou diário conforme periodicidade do cliente
- Faturamento de clientes com **Tipo de faturamento = A** (automático)
- Processamento pode ser manual ou automatizado (diariamente às 6:00h via opção 903/Cobrança)

## Pré-requisitos
- Usuário deve estar em unidade MTZ (matriz)
- CTRCs autorizados pelo SEFAZ (opção 435 mostra disponíveis)
- Cliente configurado com **Tipo de faturamento = A** na opção 384
- Mês contábil não pode estar fechado (opção 559)
- Vias de cobrança recepcionadas (se cliente exigir)

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Empresa** | Não | Escolhe empresa quando multiempresa configurada |
| **CTRCs autorizados até** | Sim | Seleciona CTRCs autorizados pelo SEFAZ até esta data |
| **Data de emissão da fatura** | Sim | Data de início de contagem do prazo. Pode ser até 15 dias passados ou até 5 dias futuros |
| **Tipo de documento** | Não | Filtra tipo específico ou TODOS |
| **Considerar CTRCs baixados** | Sim | S=fatura incondicionalmente, N=não fatura (exceto complementares e devolvidos) |
| **Considerar CTRCs a vista** | Sim | S=fatura CTRCs à vista (cuidado com dupla cobrança) |
| **Selecionar as filiais** | Não | Filiais de cobrança conforme opção 384 |
| **Manifestos (com DV)** | Não | Seleciona CTRCs de manifestos específicos |
| **CNPJ do cliente pagador** | Não | Fatura cliente específico (mesmo configurado como manual) |
| **Selecionar CNPJs do grupo** | Não | S=seleciona todos CNPJs do grupo (opção 583) |
| **Selecionar CNPJs da raiz** | Não | S=seleciona todos CNPJs da raiz (8 primeiros dígitos) |
| **Código de mercadoria** | Não | Fatura mercadorias específicas (opção 386) |
| **Capa de Remessa CTRCs Origem** | Não | Fatura Subcontratos de comprovantes de entrega (opção 082) |
| **Capa de Canhotos NF** | Não | Quando cliente exige canhotos com fatura (opção 070) |
| **Emissão do CTRC origem** | Não | Período de emissão dos CTRCs Origem para faturar Subcontratos |
| **Banco/Carteira** | Não | Seleciona clientes com este banco/carteira. Carteira=999 |
| **Valor mínimo da fatura** | Não | Desconsiderado se cliente bloqueado ou prazo limite atingido |
| **Periodicidade de faturamento** | Sim | Marcar X nas escolhidas (mensal, quinzenal, decenal, semanal, diário) |
| **Data de vencimento** | Não | Se informada, sobrescreve vencimento do cliente (opção 384) |
| **Desconsiderar banco do cliente** | Sim | S=usa banco indicado, N=usa banco do cliente |

## Abas / Sub-telas

**Tela inicial:**
- Parâmetros de seleção de CTRCs
- Filtros por filial, cliente, manifestos, mercadoria

**Rodapé:**
- **Fatura só meus**: Fatura apenas clientes com faturista = meu login (opção 384)
- **Simulação Faturamento Sintético**: Simula totalizando por cliente
- **Simulação Faturamento Analítico**: Simula relacionando CTRCs

## Fluxo de Uso

1. Verificar CTRCs disponíveis pela opção 435
2. Acessar opção 436 (usuário MTZ)
3. Selecionar parâmetros de faturamento:
   - Data de emissão da fatura
   - Periodicidade (marcar X)
   - Filtros opcionais (filiais, clientes, manifestos)
4. Opcionalmente executar simulação (sintética ou analítica)
5. Confirmar processamento
6. Aguardar geração das faturas
7. Faturas enviadas por e-mail automaticamente (primeiras horas do dia seguinte)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 384 | Define regras de faturamento do cliente (tipo, periodicidade, separação, vencimento) |
| 435 | Mostra CTRCs disponíveis para faturar |
| 437 | Faturamento manual (para clientes com Tipo=M) |
| 443 | Gera arquivo de remessa de cobrança bancária |
| 444 | Recepciona arquivo de retorno da cobrança |
| 457 | Controle de faturas (envio e-mail, adicionais, ocorrências) |
| 459 | Débitos e créditos considerados no faturamento |
| 509 | Gera pré-fatura para opção 437 |
| 559 | Fecha mês contábil (impede faturamento retroativo) |
| 903 | Automatiza faturamento (6:00h) e cobrança bancária (23:00h) |

## Observações e Gotchas

- **Usuário MTZ obrigatório**: Faturamento só pode ser executado por usuário em matriz
- **Contabilidade fechada**: Não pode faturar em data de emissão cujo mês esteja fechado (opção 559)
- **Crédito maior que fatura**: Fatura não é gerada se créditos (descontos) forem maiores que soma dos fretes
- **Faturas grandes**:
  - Processamento com > 200.000 CTRCs executado pela opção 156
  - Faturas com > 5.000 CTRCs terão apenas resumo impresso (CTRCs enviados por EDI)
- **Processamento manual**: Submeter novo processamento somente após finalizar anterior (evita sobrecarga)
- **Clientes grandes**: Fazer faturamento separadamente
- **CTRCs à vista**: Se cobrança PIX, cancelamento on-line no banco leva ~2s (torna faturamento mais lento)
- **Automatização**: Opção 903/Cobrança agenda execução diária às 6:00h
- **Cobrança bancária automática**: API processa remessa e retorno às 23:00h (Itaú, Sicred, Bradesco)
- **Faturas não abertas**: Relatório 154 (opção 056) relaciona faturas não impressas pelo cliente
- **Envio e-mail**: Faturas enviadas automaticamente por e-mail, rastreadas em tempo real
- **Vias de cobrança**: Cliente com condição "Via de Cobrança Recepcionada" só fatura CTRCs recepcionados (opção 434)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-C04](../pops/POP-C04-custos-extras.md) | Custos extras |
| [POP-E01](../pops/POP-E01-pre-faturamento.md) | Pre faturamento |
| [POP-E03](../pops/POP-E03-faturamento-automatico.md) | Faturamento automatico |
| [POP-E04](../pops/POP-E04-cobranca-bancaria.md) | Cobranca bancaria |
| [POP-E05](../pops/POP-E05-liquidar-fatura.md) | Liquidar fatura |
| [POP-F05](../pops/POP-F05-bloqueio-financeiro-ctrc.md) | Bloqueio financeiro ctrc |
