# Opção 927 — Tabela de Ocorrências de Parceiros (Padrão Proceda 3.0)

> **Módulo**: Cadastros/Integração
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função
Cadastrar tabela de ocorrências de parceiros subcontratados para permitir importação de arquivos formato TXT padrão Proceda 3.0 e atualização automática de ocorrências de CTRCs no SSW.

## Quando Usar
Necessário quando:
- Transportadora trabalha com parceiros subcontratados que enviam ocorrências via arquivo TXT padrão Proceda 3.0
- Precisa importar e processar ocorrências de CTRCs enviadas por parceiros
- Quer automatizar atualização de status de CTRCs com base em eventos de parceiros

## Pré-requisitos
- Parceiros subcontratados cadastrados (opção 408)
- Tabela de ocorrências do parceiro cadastrada nesta opção 927
- Arquivo TXT formato Proceda 3.0 enviado pelo parceiro
- CTRCs cadastrados no SSW com CNPJ remetente + Série e Número da NF

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ Parceiro | Sim | CNPJ do parceiro subcontratado |
| Código ocorrência parceiro | Sim | Código da ocorrência usado pelo parceiro no arquivo TXT |
| Ocorrência SSW | Sim | Ocorrência correspondente no SSW (mapeamento) |

## Fluxo de Uso

### Configuração inicial (executar uma vez por parceiro)
1. Acessar opção 927
2. Informar CNPJ do parceiro subcontratado
3. Cadastrar mapeamento de ocorrências:
   - Para cada código de ocorrência usado pelo parceiro no arquivo TXT
   - Informar ocorrência correspondente no SSW
4. Salvar tabela de mapeamento

### Importação de ocorrências (opção 600)
5. Receber arquivo TXT formato Proceda 3.0 do parceiro
6. Acessar opção 600 (Recepcionar ocorrências de parceiros padrão Proceda 3.0)
7. Selecionar arquivo TXT
8. Sistema importa arquivo e:
   - Localiza CTRC usando CNPJ remetente + Série e Número da NF
   - Busca ocorrência SSW correspondente na tabela da opção 927
   - Atualiza ocorrência do CTRC automaticamente
9. Conferir CTRCs atualizados

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 600 | Recepcionar ocorrências de parceiros — usa tabela da opção 927 para importar arquivos TXT |
| 408 | Cadastro de parceiros — parceiros devem estar cadastrados |

## Observações e Gotchas

- **Padrão Proceda 3.0**: Arquivo deve estar no formato TXT padrão Proceda 3.0 — outros formatos não são aceitos pela opção 600

- **Mapeamento obrigatório**: Tabela de ocorrências do parceiro DEVE estar cadastrada na opção 927 ANTES de importar arquivo pela opção 600 — sem mapeamento, sistema não consegue atualizar CTRCs

- **Identificação de CTRC**: Sistema verifica no arquivo:
  1. **CNPJ remetente**
  2. **Série da Nota Fiscal**
  3. **Número da Nota Fiscal**
  - Os três campos são usados em conjunto para localizar CTRC no SSW

- **Mapeamento 1:1**: Cada código de ocorrência do parceiro deve ter exatamente 1 ocorrência SSW correspondente — não há suporte para mapeamento N:1 ou 1:N

- **Múltiplos parceiros**: Cada parceiro pode ter sua própria tabela de mapeamento — sistema identifica parceiro pelo CNPJ no arquivo

- **Atualização automática**: Após importação bem-sucedida, ocorrências dos CTRCs são atualizadas automaticamente — não requer confirmação manual

- **Validação**: Se CTRC não for encontrado (CNPJ remetente + Série + Número NF não batem), ocorrência do arquivo é ignorada — conferir relatório de importação para identificar registros não processados

- **Sobrescrita**: Se CTRC já possui ocorrência, ela será sobrescrita pela nova ocorrência do arquivo — não há histórico de ocorrências anteriores
