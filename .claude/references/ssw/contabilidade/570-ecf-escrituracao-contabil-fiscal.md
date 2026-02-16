# Opção 570 — ECF (Escrituração Contábil Fiscal)

> **Módulo**: Contabilidade
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Gera o arquivo de Escrituração Contábil Fiscal (ECF) do SPED, incluindo ECF padrão e ECF Livro Caixa (para empresas tributadas pelo Lucro Presumido).

## Quando Usar
- Entrega anual do ECF conforme obrigação acessória da Receita Federal
- Retificação de arquivo ECF já enviado
- Geração de Livro Caixa para empresas no Lucro Presumido

## Pré-requisitos
- Validador ECF instalado (disponível no site do SPED)
- Arquivo ECD (opção 534) gerado e assinado digitalmente para o mesmo período
- Plano de Contas configurado (opção 540)
- Lançamentos contábeis finalizados para o período
- Dados do contabilista responsável
- Dados do diretor/responsável legal
- Definição do regime de tributação (Lucro Real ou Lucro Presumido)

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Finalidade do Arquivo | Sim | N = Normal (envio original); S = Substituto (retificação) |
| Forma de Tributação | Sim | R = Lucro Real; P = Lucro Presumido |
| Período | Sim | Período contábil para geração (mês/ano) |
| Dados do Contabilista | Sim | Nome, CPF, CRC, telefone, email |
| Dados do Diretor | Sim | Nome, CPF, cargo do responsável legal |

## Fluxo de Uso

### ECF Padrão
1. Gerar ECD (opção 534) para o mesmo período e assinar digitalmente
2. Acessar opção 570
3. Preencher campos obrigatórios:
   - Finalidade: N (normal) ou S (substituto)
   - Forma de Tributação: R (Lucro Real) ou P (Lucro Presumido)
   - Período contábil
   - Dados do contabilista
   - Dados do diretor
4. Clicar em "ECF" no rodapé
5. Salvar arquivo gerado
6. Importar arquivo ECD no Validador ECF
7. Importar arquivo ECF no Validador ECF
8. Complementar informações de lucro destinado a sócios/acionistas diretamente no validador
9. Conferir registros validados com relatórios contábeis
10. Transmitir à Receita Federal

### ECF Livro Caixa (Lucro Presumido)
1. Garantir que extrato de bancos e caixas está atualizado (opção 456)
2. Acessar opção 570
3. Preencher campos obrigatórios com Forma de Tributação = P (Lucro Presumido)
4. Clicar em "ECF LIVRO CAIXA" no rodapé
5. Sistema lista toda movimentação de bancos e caixas
6. Salvar arquivo gerado
7. Validar no Validador ECF
8. Transmitir à Receita Federal

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 534 | ECD — arquivo deve ser gerado e assinado ANTES da geração do ECF |
| 540 | Plano de Contas — estrutura utilizada na geração |
| 456 | Extrato Bancário — base para ECF Livro Caixa |
| 562 | DRE — relatório para conferência dos dados do ECF |
| 561 | Balanço Patrimonial — relatório para conferência dos dados do ECF |
| 529 | Balancete de Verificação — relatório para conferência dos dados do ECF |
| 548 | Livro Razão — relatório para conferência dos dados do ECF |
| 545 | Livro Diário — relatório para conferência dos dados do ECF |

## Observações e Gotchas
- **ECD obrigatório primeiro**: Arquivo ECD (opção 534) deve ser gerado e assinado ANTES de gerar o ECF
- **Importação no validador**: ECD deve ser importado primeiro, depois ECF
- **Complementação manual**: Informações de lucro destinado a cada sócio/acionista devem ser complementadas manualmente no Validador ECF (não são importadas do SSW por questões de sigilo)
- **Conferência obrigatória**: Registros validados devem ser conferidos com relatórios contábeis (DRE, Balanço, Balancete, Livro Razão, Livro Diário)
- **ECF Livro Caixa**: Exclusivo para empresas no Lucro Presumido; lista toda movimentação financeira
- **Extrato atualizado**: Para ECF Livro Caixa, garantir que opção 456 (extrato bancário) esteja completa e correta
- **Regime de tributação**: Deve corresponder ao regime real da empresa; não pode ser alterado arbitrariamente
- **Assinatura digital**: Arquivo final deve conter assinatura digital válida antes do envio
- **Retificação**: Para retificar, usar Finalidade = S e informar dados corretos; arquivo anterior será substituído
