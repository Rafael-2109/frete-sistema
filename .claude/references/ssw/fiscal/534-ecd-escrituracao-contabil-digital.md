# Opção 534 — ECD (Escrituração Contábil Digital)

> **Módulo**: Fiscal
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Gera o arquivo de Escrituração Contábil Digital (ECD) do SPED, incluindo Livro Diário Auxiliar (A), Livro Diário (R) e Livro Diário Geral (G).

## Quando Usar
- Entrega anual ou periódica do ECD conforme obrigação acessória da Receita Federal
- Geração de arquivos para períodos não anuais (requer Livro A + Livro R)
- Geração de arquivos para períodos anuais (Livro G completo)
- Substituição de arquivo já enviado (retificação)

## Pré-requisitos
- Validador ECD instalado (disponível no site do SPED)
- Plano de Contas configurado (opção 540)
- Lançamentos contábeis finalizados para o período
- Dados do contabilista responsável
- Dados do diretor/responsável legal
- NIRE (Número de Identificação do Registro de Empresa) da Junta Comercial

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Período | Sim | Período contábil (mês/ano) para geração do arquivo |
| Tipo de Escrituração | Sim | 0 = Original; 1 = Substituto (retificação) |
| Número do Recibo Anterior | Condicional | Obrigatório apenas se tipo = 1 (retificação) |
| Número do Livro | Sim | Número sequencial do Livro |
| NIRE | Sim | Fornecido pela Junta Comercial do Estado |
| Data Arquivamento | Sim | Data de arquivamento dos atos constitutivos |
| Data Arquivo Conversão | Condicional | Se empresa mudou de Sociedade Simples para Empresária |
| Dados do Contabilista | Sim | Nome, CPF, CRC, telefone, email |
| Dados do Diretor | Sim | Nome, CPF, cargo |
| Código HASH | Condicional | Obrigatório apenas para Livro Diário (R) — gerado pelo Validador |

## Fluxo de Uso

### Para Período NÃO Anual
1. **Gerar Livro Diário Auxiliar (A)**:
   - Acessar opção 534
   - Preencher dados obrigatórios
   - Clicar em "LIVRO DIÁRIO AUXILIAR (A)" no rodapé
   - Salvar arquivo no computador
   - Importar no Validador ECD (opção "Escrituração Contábil")
   - Em "Gerenciar Requerimento", copiar o código HASH gerado

2. **Gerar Livro Diário (R)**:
   - Retornar à opção 534
   - Informar código HASH obtido na etapa anterior
   - Clicar em "LIVRO DIÁRIO (R)" no rodapé
   - Salvar arquivo no computador
   - Testar no Validador ECD
   - **Este arquivo deve ser enviado à Receita**

### Para Período Anual
1. **Gerar Livro Diário Geral (G)**:
   - Acessar opção 534
   - Preencher dados obrigatórios
   - Clicar em "DIÁRIO GERAL (G)" no rodapé
   - NÃO necessita código HASH
   - Salvar arquivo no computador
   - Testar no Validador ECD
   - **Este arquivo deve ser enviado à Receita**

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 540 | Plano de Contas — estrutura utilizada na geração dos registros |
| 559 | Saldo das Contas / Fechamento — transferência de saldos do sistema anterior |
| 570 | ECF (Escrituração Contábil Fiscal) — requer importação do ECD no validador |
| 564 | SPED FCONT (até 2015) — substituído pelas opções 534 e 570 |

## Observações e Gotchas
- **Livro A não é enviado**: Serve apenas para gerar código HASH usado no Livro R
- **Código HASH**: Campo deve ficar vazio na geração do Livro A, preenchido na geração do Livro R
- **Período anual vs não anual**: Livro G (anual) não precisa de HASH; Livro R (não anual) precisa
- **Transferência de saldos**: Saldos do Plano de Contas do sistema anterior são transferidos via registros I200 e I250. Para que ocorra a transferência, é necessário informar a conta do sistema anterior na opção 559 / Informar Saldo
- **FCONT descontinuado**: Opção 564 (FCONT) foi substituída e deve ser usada apenas para retificações de anos anteriores a 2015
- **Último FCONT**: 2015, referente ao ano-calendário 2014, apenas para empresas tributadas pelo lucro real que não optaram pela extinção do RTT em 2014
- **Validação obrigatória**: Todo arquivo gerado deve ser testado no Validador ECD antes do envio à Receita
- **Assinatura digital**: Arquivo enviado deve conter assinatura digital válida
