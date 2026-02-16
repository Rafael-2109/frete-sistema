# Opção 033 — Ocorrências de Transferência

> **Módulo**: Operacional — Gestão de Ocorrências
> **Páginas de ajuda**: 5 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Registra ocorrências em CTRCs durante o processo de transferência, permitindo comunicação entre unidades e rastreamento de pendências operacionais.

## Quando Usar
- Registrar problemas durante transferência (avarias, extravios, atrasos)
- Informar ocorrências para unidades origem/anterior
- Documentar pendências que impedem continuidade da operação

## Pré-requisitos
- Ocorrências cadastradas na opção 405
- CTRCs em transferência ou no armazém

## Campos / Interface
Não há formulário fixo — interface permite registrar código de ocorrência e observações conforme opção 405.

## Abas / Sub-telas
Opção oferece integração com:
- **Opção 108**: Instruções para Ocorrências (unidades origem/anterior)
- **Opção 133**: Minhas ocorrências (consulta de instruções recebidas)
- **Opção 943**: Liberar ocorrências finalizadoras para EDI
- **Opção 291**: Segregar volumes (movimentação com instrução)

## Fluxo de Uso
1. Identificar CTRC com problema durante transferência
2. Acessar opção 033
3. Selecionar código de ocorrência apropriado (opção 405)
4. Registrar observações complementares
5. Unidade origem/anterior visualiza via opção 108
6. Unidade origem/anterior fornece instruções (opção 108)
7. Unidade atual consulta instruções via opção 133

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 108 | Instruções para Ocorrências — unidade origem/anterior dá instruções |
| 133 | Minhas Ocorrências — consulta instruções recebidas |
| 038 | Ocorrências de entrega (complementar para entregas) |
| SSWMobile | Registro de ocorrências pelo motorista |
| 405 | Cadastro de códigos de ocorrência |
| 943 | Liberação de ocorrências finalizadoras para envio a clientes |
| 291 | Segregação de volumes com registro em ocorrências |
| 091 | Segregação de CTRCs com pendência |
| 101 | Visualização de histórico de ocorrências do CTRC |

## Observações e Gotchas
- **Última ocorrência**: Apenas a última ocorrência do CTRC é considerada para instrução
- **Código SSW**: Ocorrências trocadas entre parceiros SSW usam Código SSW (opção 405)
- **Visualização**: Unidade origem ou anterior visualiza conforme parametrização (opção 405)
- **Instruções obrigatórias**: Ao final do dia, nenhum CTRC com ocorrência deve restar sem instruções
- **Responsabilidade**: Ocorrências podem ser tipo Pendência do Cliente ou Responsabilidade da Transportadora
- **Ocorrências finalizadoras**: Algumas ocorrências são bloqueadas para envio ao cliente (marcadas como finalizadoras), liberadas apenas pela opção 943
- **Fale Conosco**: Campo permite filtrar CTRCs com informações registradas pelo cliente no site
- **Correio Eletrônico**: Opção 187 disponível para troca de mensagens, mas não deve ser usado para resolução de pendências (usar opção 108)
- **Segregação de volumes**: Opção 291 permite segregar capturando código de barras de todos os volumes, gravando instrução automática
- **Sem EDI para ocorrências pendentes**: CTRCs com ocorrência tipo PRÉ-ENTREGA não estão disponíveis para entrega

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-D06](../pops/POP-D06-registrar-ocorrencias.md) | Registrar ocorrencias |
