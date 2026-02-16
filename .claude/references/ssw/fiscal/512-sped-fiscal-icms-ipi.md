# Opção 512 — SPED Fiscal ICMS/IPI

> **Módulo**: Fiscal
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Gera o arquivo SPED Fiscal ICMS/IPI para envio ao fisco. O bloqueio ocorre automaticamente durante a geração, impedindo alterações retroativas nos lançamentos de entrada (despesas) e CTRBs.

## Quando Usar
- Obrigação mensal para empresas sujeitas ao regime de apuração do ICMS e/ou IPI
- Geração do arquivo digital para transmissão à SEFAZ
- Fechamento fiscal do período para garantir integridade dos dados já enviados

## Pré-requisitos
- Lançamentos de entrada (despesas) e CTRBs finalizados para o período
- Validador SPED Fiscal instalado (disponível no site da Receita Federal)
- Período contábil/fiscal ainda não fechado (primeira geração) ou reaberto (correções)

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Período | Sim | Mês/ano de apuração fiscal (formato MM/AAAA) |
| Unidade | Sim | Unidade com Inscrição Estadual que será incluída no arquivo |

## Fluxo de Uso
1. Acessar opção 512
2. Informar período de apuração (mês/ano)
3. Selecionar unidade(s) pela Inscrição Estadual
4. Gerar arquivo SPED Fiscal ICMS/IPI
5. Sistema automaticamente fecha o período fiscal (opção 567) para as unidades com mesma Inscrição Estadual
6. Salvar arquivo gerado
7. Validar no Validador SPED Fiscal da Receita
8. Transmitir arquivo à SEFAZ

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 567 | Fechamento do período fiscal — bloqueado automaticamente ao gerar SPED Fiscal ICMS |
| 496 | Arquivo SINTEGRA — também fecha período fiscal por Inscrição Estadual |
| 515 | SPED Contribuições PIS/COFINS — fechamento por raiz de CNPJ |
| 587 | SPED REINF — fechamento por raiz de CNPJ |

## Observações e Gotchas
- **Fechamento automático**: Ao gerar o arquivo, o sistema fecha automaticamente o período fiscal (opção 567) para as unidades com a mesma Inscrição Estadual
- **Bloqueio de alterações**: Após fechamento, lançamentos de entrada (despesas) e CTRBs não podem ser alterados para evitar divergências com arquivos enviados
- **Critério de fechamento**: Fecha por Inscrição Estadual (diferente do SPED Contribuições que fecha por raiz de CNPJ)
- **Usuários SSW**: Equipe SSW não consegue fazer fechamento fiscal pela opção 567
- **Reabertura**: Para corrigir dados, é necessário reabrir o período fiscal pela opção 567 antes de gerar arquivo substituto

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-G04](../pops/POP-G04-relatorios-contabilidade.md) | Relatorios contabilidade |
