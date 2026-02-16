# Opção 138 — Estorno de Baixa/Entrega e Resgate de CTRC

> **Módulo**: Comercial
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Efetua o estorno de ocorrências do tipo baixa/entrega e de resgate de CTRC, permitindo que a operação volte a ficar ativa. Suporta estorno individual ou em lote via arquivo CSV.

## Quando Usar
- Baixa/entrega foi atribuída incorretamente ao CTRC
- Resgate de mercadoria (código SSW 88) precisa ser cancelado
- Correção de erro operacional em lote (múltiplos CTRCs)
- Reativação de operação de CTRC que foi finalizada prematuramente

## Pré-requisitos
- **CTRC com ocorrência estornável**: Deve ter ocorrência do tipo BAIXA/ENTREGA ou código SSW 88 (Resgate)
- **Permissão de acesso**: Operação crítica requer permissões adequadas
- **Opção 455**: Para geração de arquivo CSV no formato 2 (opcional, se estorno em lote)
- **Opção 428**: Pacote de arquivamento (se já gerado, CTRC não será retirado dele após estorno)

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CTRC (com DV) | Condicional | Sigla, número e dígito verificador do CTRC (obrigatório se estorno individual) |
| Motivo | Sim | Justificativa do estorno |
| Arquivo | Condicional | Arquivo CSV para estorno em lote (obrigatório se estorno em lote) |

### Layouts do Arquivo CSV (estorno em lote)
| Layout | Descrição |
|--------|-----------|
| Layout 1 | 1 coluna: Chave CT-e (44 dígitos). Sem cabeçalho. |
| Layout 2 | 2 colunas: CTRC (série, número com DV no formato XXX999999-9) e data de autorização (DD/MM/AAAA). Mesmo formato gerado pela opção 455. Sem cabeçalho. |

## Fluxo de Uso

### Estorno Individual
1. Acessar opção 138
2. Informar CTRC (com DV) no formato: sigla + número + dígito verificador
3. Informar motivo do estorno (obrigatório)
4. Clicar em **►** para confirmar estorno
5. Sistema estorna ocorrência:
   - Operação do CTRC volta a ficar ativa
   - Ocorrência perde o código
   - Texto da ocorrência é mantido como instrução (sem código)

### Estorno em Lote
1. Preparar arquivo CSV conforme um dos layouts:
   - **Layout 1**: 1 coluna com chave CT-e (44 dígitos)
   - **Layout 2**: 2 colunas (CTRC série/número/DV + data autorização DD/MM/AAAA)
2. Acessar opção 138
3. Fazer upload do arquivo CSV
4. Informar motivo do estorno (obrigatório)
5. Clicar em **►** para confirmar estorno em lote
6. Sistema processa todos os CTRCs do arquivo:
   - Cada CTRC tem operação reativada
   - Ocorrências perdem código
   - Textos são mantidos como instruções

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 455 | Gera arquivo CSV no formato do Layout 2 (para estorno em lote) |
| 428 | Pacote de arquivamento (CTRC não é retirado dele após estorno) |
| 033 | Atribuição de ocorrências (oposta ao estorno) |

## Observações e Gotchas
- **Ocorrências estornáveis**: Apenas BAIXA/ENTREGA e código SSW 88 (Resgate de mercadoria) podem ser estornados
- **Efeito do estorno**:
  - Operação do CTRC volta a ficar ativa
  - Ocorrência perde o código (não é mais rastreável como ocorrência formal)
  - Texto é mantido como instrução (sem código)
- **Parcerias SSW**: Se transportadoras envolvidas usarem SSW, estorno pode ser comandado por qualquer uma delas → estorno ocorre em **todos os CTRCs da cadeia de subcontratação** que estejam com ocorrências do tipo Baixa/Entrega
- **Pacote de arquivamento**: Estorno **NÃO retira** CTRC de Pacote de Arquivamento já gerado (opção 428)
- **Arquivo sem cabeçalho**: Arquivos CSV devem ser enviados sem linha de cabeçalho
- **Formato do CTRC no Layout 2**: XXX999999-9 (série + número + traço + DV)
- **Motivo obrigatório**: Sempre informar justificativa do estorno para rastreabilidade
- **Operação crítica**: Usar com cuidado, pois reativa operações que estavam finalizadas
- **Manutenção do histórico**: Texto da ocorrência é preservado como instrução, mantendo rastreabilidade

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-D05](../pops/POP-D05-baixa-entrega.md) | Baixa entrega |
| [POP-D06](../pops/POP-D06-registrar-ocorrencias.md) | Registrar ocorrencias |
