"""Helpers de formatacao BR<->Decimal compartilhados entre rotas do modulo
Motos Assai (fast-follow pos-review Spec 2 — dedupe de 3 copias identicas:
`_br` em `estoque_peca.py`/`compra_peca.py` e `_br_decimal` em `peca.py`).

NAO mudar o comportamento de parsing — Task 10/11/12 ja calibraram o
tratamento de malformado (InvalidOperation/ValueError propagados pelo caller).
"""


def br_para_decimal_str(s):
    """Converte string BR ('1.234,50') para string decimal-ponto ('1234.50').

    Assume qualquer '.' como separador de milhar e ',' como decimal. String
    vazia/None -> None (caller decide se e obrigatorio ou opcional).
    """
    s = (s or '').strip().replace('.', '').replace(',', '.')
    return s or None


def decimal_para_br(d):
    """Formata um Decimal para string BR (vírgula decimal), round-trip com
    `br_para_decimal_str`.

    Ex: Decimal('12.5000') -> '12,50'. NÃO insere separador de milhar —
    `br_para_decimal_str` assume que qualquer '.' é separador de milhar, então
    incluí-lo aqui quebraria o round-trip (era exatamente o bug: `str(Decimal)`
    usa '.' como decimal, não milhar).
    """
    if d is None:
        return ''
    texto = format(d, 'f')  # notação fixa, nunca científica
    if '.' in texto:
        inteiro, frac = texto.split('.')
        frac = frac.rstrip('0')
        if len(frac) < 2:
            frac = frac.ljust(2, '0')
    else:
        inteiro, frac = texto, '00'
    return f'{inteiro},{frac}'
