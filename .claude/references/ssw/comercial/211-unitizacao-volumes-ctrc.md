# Opção 211 — Unitização de Volumes do CTRC

> **Módulo**: Comercial / Operacional
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função
Reduz a quantidade de volumes de um CTRC através de unitização (normalmente paletização), permitindo acondicionar mercadorias que se destinam ao mesmo local em menor quantidade de volumes utilizando pallet, saca, bag, gaiola, entre outros.

## Quando Usar
- Para consolidar volumes de um mesmo CTRC em pallets
- Para reduzir quantidade de volumes facilitando movimentação
- Para acondicionar volumes em sacas, bags, gaiolas ou outros recipientes
- Quando volumes unitizados possuem identificação própria (código do cliente)

## Pré-requisitos
- CTRC já autorizado
- Mercadorias destinadas ao mesmo local de entrega
- Nova quantidade de volumes deve ser igual ou menor que a quantidade atual
- SSWBar configurado (opcional, para reconhecer códigos dos volumes unitizados)

## Campos / Interface
### Tela Inicial (Localizar CTRC)
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CTRC (sem DV) | Alternativo | Número interno com série e número (sem dígito verificador) |
| N Fiscal | Alternativo | Nota fiscal da mercadoria |
| NR, NR1, NR2 | Alternativo | Código de barras dos volumes ou das Notas Fiscais |
| DACTE | Alternativo | Chave (código de barras de 44 dígitos) da DACTE |

### Tela Principal (Unitizar)
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Volumes | Sim | Nova quantidade de volumes (igual ou menor que a atual) |
| Identificar volumes | Não | Link para informar códigos de identificação dos volumes unitizados |

## Fluxo de Uso
1. **Localizar CTRC** (Tela Inicial):
   - Informar um dos critérios: CTRC, NF, NR/NR1/NR2 ou DACTE
   - Sistema localiza o CTRC autorizado
2. **Unitizar volumes** (Tela Principal):
   - Informar nova quantidade de volumes (menor ou igual à atual)
   - Opcionalmente: clicar em "Identificar volumes" para informar códigos
3. **Gravar unitização**:
   - Clicar em "Unitizar"
   - Sistema atualiza quantidade de volumes do CTRC
   - Informação da unitização é gravada nas ocorrências do CTRC

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| SSWBar | Reconhece códigos de identificação dos volumes unitizados |
| 609 | Cadastro de clientes embarcadores de e-commerce (unitização via EDI) |

## Observações e Gotchas
- **CTRCs com múltiplas NFs**: É possível unitizar mesmo quando há mais de uma Nota Fiscal. Neste caso, a NF utilizada será a do volume = 1
- **Identificação própria**: Se os volumes unitizados possuem código do cliente, informar via link "Identificar volumes" para reconhecimento pelo SSWBar
- **Registro de ocorrências**: A informação da unitização é automaticamente gravada nas ocorrências do CTRC
- **3 formas de unitização**:
  1. **Opção 211** (esta opção): Unitização manual de volumes de um único CTRC
  2. **SSWBar**: Unitização agrupando diversos CTRCs em gaiolas e pallets com impressão de etiquetas (facilita operação)
  3. **Opção 609**: Unitização via EDI para clientes embarcadores de e-commerce
- **Benefício operacional**: Reduz quantidade de volumes a serem movimentados, facilitando carga, descarga e armazenagem
- **Destino único**: Mercadorias devem ter o mesmo local de entrega para serem unitizadas
- **Não aumenta volumes**: Nova quantidade deve ser sempre igual ou menor (não permite aumentar)
- **CTRC autorizado**: Só é possível unitizar CTRCs já autorizados pela SEFAZ
