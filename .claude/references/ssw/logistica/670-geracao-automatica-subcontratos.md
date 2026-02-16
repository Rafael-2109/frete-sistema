# Opção 670 — Parâmetros para Geração Automática de Subcontratos

> **Módulo**: Logística
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Configura geração automática de subcontratos no parceiro subcontratado com a saída do veículo na subcontratante.

## Quando Usar
- Para automatizar a geração de subcontratos em transportadora parceira que também usa SSW
- Quando a subcontratante dá saída de Manifesto para unidade operada por parceiro subcontratado

## Pré-requisitos
- Parceiro subcontratado deve usar o Sistema SSW
- Configuração prévia desta opção 670

## Campos / Interface

### Tela Inicial
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Unidade destino do Manifesto | Sim | Unidade destino do Manifesto operado pela subcontratada |

### Tela Seguinte
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Destino dos CTRCs | Sim | Unidade destino dos CTRCs enviados ao subcontratado |
| Domínio | Sim | Domínio SSW da transportadora subcontratada |
| Unidade | Sim | Unidade da subcontratada onde será gerado subcontrato |
| Tipo | Sim | C (subcontrato fiscal) ou L (subcontrato não-fiscal) |
| Placa | Sim | Placa de coleta do subcontrato (ARMAZÉM = carga deixada no armazém) |
| Mercadoria | Sim | Código de mercadoria para emissão do subcontrato |
| Espécie | Sim | Código da espécie de mercadoria |
| Sigla da transportadora | Sim | Sigla da subcontratante cadastrada na subcontratada (opção 485) |

## Fluxo de Uso
1. Configurar processo automatizado pela opção 670
2. Informar unidade destino do Manifesto
3. Parametrizar dados da subcontratada (domínio, unidade, tipo, placa, etc.)
4. Subcontratante dá saída do Manifesto (opção 025) para unidade operada por parceiro
5. Subcontratos correspondentes aos CT-es são gerados automaticamente no SSW da subcontratada
6. Subcontratada gera os subcontratos (opção 007 ou opção 008)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 025 | Saída do Manifesto - dispara geração automática de subcontratos |
| 007 | Geração de subcontratos na subcontratada |
| 008 | Geração de subcontratos na subcontratada |
| 485 | Cadastro da sigla da subcontratante |

## Observações e Gotchas
- **Benefícios**: A geração antecipada dos subcontratos permite ao subcontratado planejar e adiantar sua operação
- **Requisito crítico**: Parceiro subcontratado DEVE usar o Sistema SSW
- **Sigla necessária**: É necessário cadastrar sigla da subcontratante no domínio da subcontratada (opção 485) para identificar CNPJ da subcontratante que pagará os subcontratos
- **Placa ARMAZÉM**: Indica que subcontratante deixará a carga no armazém da subcontratada
- **Automação completa**: Geração ocorre automaticamente com a saída do veículo (opção 025)
- **Tipos de subcontrato**: C (fiscal, com documento fiscal) ou L (não-fiscal, apenas controle)
