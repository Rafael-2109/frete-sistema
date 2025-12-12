# Abreviacoes de Produtos

Mapeamento de abreviacoes para busca inteligente de produtos.

> **Quando usar:** Consulte este arquivo quando precisar resolver abreviacoes de produtos informadas pelo usuario ou construir buscas no catalogo.

---

A funcao `resolver_produto()` usa busca inteligente com abreviacoes mapeadas.

## Abreviacoes Suportadas (busca EXATA nos campos corretos)

| Abreviacao | Campo | Tipo Busca | Significado |
|------------|-------|------------|-------------|
| **CI** | tipo_materia_prima | EXATO | Cogumelo Inteiro |
| **CF** | tipo_materia_prima | EXATO | Cogumelo Fatiado |
| **AZ VF** | tipo_materia_prima | EXATO | Azeitona Verde Fatiada |
| **AZ PF** | tipo_materia_prima | EXATO | Azeitona Preta Fatiada |
| **AZ VI** | tipo_materia_prima | EXATO | Azeitona Verde Inteira |
| **AZ VSC** | tipo_materia_prima | EXATO | Azeitona Verde Sem Caroco |
| **BR** | tipo_embalagem | EXATO→BARRICA | Barrica |
| **BD** | tipo_embalagem | LIKE BD% | Balde |
| **GL** | tipo_embalagem | LIKE GALAO% | Galao |
| **VD** | tipo_embalagem | LIKE VIDRO% | Vidro |
| **POUCH** | tipo_embalagem | LIKE POUCH% | Pouch |
| **SACHET** | tipo_embalagem | LIKE SACHET% | Sachet |
| **MEZZANI** | categoria_produto | EXATO | Marca Mezzani |
| **BENASSI** | categoria_produto | EXATO | Marca Benassi |
| **IND** | categoria_produto | EXATO→INDUSTRIA | Industria |

---

## Exemplos de busca

- "ci" → Cogumelo Inteiro (busca EXATA, nao encontra "INTENSA")
- "az vf bd" → Azeitona Verde Fatiada em Balde
- "br mezzani" → Barrica Mezzani
