# Abreviacoes de Produto

## Tipo Materia Prima (tipo_materia_prima)

Busca **EXATA** para evitar falsos positivos.

| Abreviacao | Valor | Descricao |
|------------|-------|-----------|
| CI | CI | Cogumelo Inteiro |
| CF | CF | Cogumelo Fatiado |
| AZ VF | AZ VF | Azeitona Verde Fatiada |
| AZ PF | AZ PF | Azeitona Preta Fatiada |
| AZ VI | AZ VI | Azeitona Verde Inteira |
| AZ PI | AZ PI | Azeitona Preta Inteira |
| AZ VR | AZ VR | Azeitona Verde Recheada |
| AZ VSC | AZ VSC | Azeitona Verde Sem Caroco |

### Aliases Curtos

| Alias | Significado | Busca |
|-------|-------------|-------|
| VF | Verde Fatiada | LIKE '%VF%' |
| PF | Preta Fatiada | LIKE '%PF%' |

---

## Tipo Embalagem (tipo_embalagem)

Busca **LIKE** para capturar variacoes.

| Abreviacao | Valor | Descricao |
|------------|-------|-----------|
| BARRICA | BARRICA | Barrica |
| BR | BARRICA | Barrica (alias) |
| BD | BD% | Balde |
| BALDE | BD% | Balde |
| POUCH | POUCH% | Pouch |
| SACHET | SACHET% | Sachet |
| VIDRO | VIDRO% | Vidro |
| VD | VIDRO% | Vidro (alias) |
| GALAO | GALAO% | Galao |
| GL | GALAO% | Galao (alias) |

---

## Categorias/Marcas (categoria_produto)

Busca **EXATA**.

| Abreviacao | Valor | Descricao |
|------------|-------|-----------|
| CAMPO BELO | CAMPO BELO | Marca Campo Belo |
| MEZZANI | MEZZANI | Marca Mezzani |
| BENASSI | BENASSI | Marca Benassi |
| IMPERIAL | IMPERIAL | Marca Imperial |
| INDUSTRIA | INDUSTRIA | Destinado a industria |
| IND | INDUSTRIA | Industria (alias) |

---

## Exemplos de Combinacao

O script suporta combinar multiplas abreviacoes:

| Termo de Busca | Interpretacao |
|----------------|---------------|
| "AZ VF pouch" | Azeitona Verde Fatiada em Pouch |
| "CI mezzani" | Cogumelo Inteiro Mezzani |
| "balde industria" | Balde para Industria |
| "pf vidro" | Preta Fatiada em Vidro |

---

## Como Funciona a Deteccao

1. **Tokeniza** o termo de busca
2. **Detecta combinacoes** de 2 tokens primeiro (ex: "AZ VF")
3. **Detecta tokens individuais** restantes
4. **Aplica filtros** no campo correto (tipo_materia_prima, tipo_embalagem, categoria_produto)
5. **Busca parcial** para tokens nao reconhecidos como abreviacao

---

## Expansao

Para adicionar novas abreviacoes, atualizar:

1. `ABREVIACOES_PRODUTO` em `resolver_produto.py`
2. Esta documentacao
3. Testar com `resolver_produto.py --termo "nova_abreviacao"`
