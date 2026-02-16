# Opção 209 — Troca Veículos e/ou Motoristas de MDF-e

> **Módulo**: Comercial / Operacional
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função
Permite a troca de veículos (cavalo) e/ou motoristas de um MDF-e (Manifesto Eletrônico de Documentos Fiscais) já emitido, encerrando o documento original e gerando novos manifestos operacionais com os novos dados.

## Quando Usar
- Quando houver necessidade de substituir veículo durante o transporte
- Quando motorista precisar ser substituído em meio à viagem
- Para corrigir veículo ou motorista informado incorretamente
- Em situações de quebra de veículo ou indisponibilidade de motorista

## Pré-requisitos
- MDF-e já autorizado pela SEFAZ (chave válida)
- Novos veículos/motoristas devidamente cadastrados no sistema
- Validações necessárias para emissão de novo MDF-e devem ser atendidas
- Opção 025 disponível para autorização do novo MDF-e

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Chave MDF-e | Sim | Código de barras (44 dígitos) do MDF-e cujos veículos/motoristas devem ser trocados |
| Novos veículos | Condicional | Placas dos novos veículos (cavalo e carretas, se aplicável) |
| Novos motoristas | Condicional | Dados dos novos motoristas |

## Fluxo de Uso
1. **Informar chave do MDF-e**:
   - Inserir código de barras do MDF-e na tela inicial
   - Sistema traz CTRCs vinculados ao MDF-e informado
2. **Informar novos dados**:
   - Informar placa do novo cavalo (se trocar veículo)
   - Informar dados do novo motorista (se trocar motorista)
   - Ou ambos (troca simultânea)
3. **Validação automática**:
   - Sistema aplica todas as liberações e validações
   - Validações são as mesmas da emissão de novo MDF-e
4. **Encerramento e geração**:
   - MDF-e original é encerrado automaticamente
   - Manifestos operacionais do MDF-e original recebem chegada na unidade atual
   - Novos Manifestos Operacionais são gerados (opção 209)
   - Novo MDF-e é autorizado via opção 025
5. **Preservação de dados**:
   - Numeração de Gaiolas e Pallets é mantida
   - CTRCs continuam os mesmos

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 025 | Autorização do novo MDF-e gerado |
| Sistema SEFAZ | Encerramento do MDF-e original e autorização do novo |

## Observações e Gotchas
- **Encerramento automático**: O MDF-e original é encerrado automaticamente pelo sistema (não requer ação manual)
- **Chegada automática**: Os Manifestos Operacionais do MDF-e original recebem chegada na unidade do usuário
- **Validações rigorosas**: Todas as validações de emissão de MDF-e são aplicadas (veículos cadastrados, motoristas válidos, documentação em dia, etc.)
- **Numeração preservada**: Gaiolas e Pallets mantêm a numeração original (não são renumerados)
- **CTRCs inalterados**: Os conhecimentos de transporte permanecem os mesmos, apenas mudam de manifesto
- **Processo em 2 etapas**:
  1. Opção 209 gera novos Manifestos Operacionais
  2. Opção 025 autoriza o novo MDF-e junto à SEFAZ
- **Unidade de referência**: A chegada dos Manifestos Operacionais antigos ocorre na unidade do usuário logado
- **Chave de 44 dígitos**: Use o código de barras completo do MDF-e (não apenas o número)
- **Liberações**: Verifique se há permissões/liberações necessárias antes da execução (consulte administrador)
