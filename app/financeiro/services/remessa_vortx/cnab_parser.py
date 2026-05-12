"""
Parser/manipulador puro de arquivos CNAB 400 (BMP/VORTX).

Utilitarios independentes para ler, inspecionar e modificar linhas CNAB 400
sem dependencias do Odoo ou DB. Usado por conversor_externo.py e validador.py.

Layout CNAB 400:
    - Cada linha tem exatamente 400 caracteres
    - Separador: CRLF (\r\n) ou LF (\n) — detectado automaticamente
    - Encoding: latin-1
    - Tipos de linha (primeiro caractere):
        '0' = Header
        '1' = Detalhe (titulo)
        '2' = E-mail pagador (opcional)
        '3' = Split de pagamentos (opcional)
        '7' = Sacador avalista (opcional)
        '9' = Trailer
"""
from datetime import date, datetime
from typing import List, Tuple

LINE_WIDTH = 400


def parse_arquivo(arquivo_bytes: bytes) -> Tuple[List[str], str]:
    """Decodifica bytes (latin-1) e divide em linhas, detectando o separador.

    Returns:
        (lines, separador_detectado)

    Raises:
        ValueError: se alguma linha nao tiver exatamente 400 caracteres.
    """
    if b'\r\n' in arquivo_bytes:
        sep = '\r\n'
    elif b'\n' in arquivo_bytes:
        sep = '\n'
    else:
        sep = '\r\n'

    content = arquivo_bytes.decode('latin-1', errors='replace')
    lines = [line for line in content.split(sep) if line]

    if not lines:
        raise ValueError('Arquivo vazio ou sem linhas validas.')

    for i, line in enumerate(lines):
        if len(line) != LINE_WIDTH:
            raise ValueError(
                f'Linha {i + 1} tem {len(line)} caracteres, esperado {LINE_WIDTH}.'
            )

    return lines, sep


def serializar_arquivo(lines: List[str], separador: str = '\r\n') -> bytes:
    """Concatena linhas com separador e codifica em latin-1.
    Adiciona separador final (padrao CNAB)."""
    content = separador.join(lines) + separador
    return content.encode('latin-1')


def replace_field(line: str, start: int, end: int, value: str,
                  fillchar: str = ' ', align: str = 'left') -> str:
    """Substitui [start:end] da linha (0-indexed, end-exclusive) por value.

    Se value for menor que o campo, faz pad. Se for maior, trunca.
    align='left' (default) faz ljust. align='right' faz rjust.
    """
    width = end - start
    value = str(value) if value is not None else ''
    if len(value) > width:
        value = value[:width]
    elif len(value) < width:
        if align == 'right':
            value = value.rjust(width, fillchar)
        else:
            value = value.ljust(width, fillchar)
    return line[:start] + value + line[end:]


def get_field(line: str, start: int, end: int) -> str:
    """Retorna o conteudo de [start:end] (0-indexed, end-exclusive)."""
    return line[start:end]


def is_header(line: str) -> bool:
    """Linha header (tipo '0')."""
    return line[:1] == '0'


def is_detalhe(line: str) -> bool:
    """Linha de detalhe — titulo (tipo '1')."""
    return line[:1] == '1'


def is_trailer(line: str) -> bool:
    """Linha trailer (tipo '9')."""
    return line[:1] == '9'


def detectar_banco_origem(lines: List[str]) -> str:
    """Le o codigo do banco do header (pos 077-079, 0-indexed [76:79]).

    Raises:
        ValueError: se nao encontrar header.
    """
    header = next((l for l in lines if is_header(l)), None)
    if not header:
        raise ValueError('Header (linha tipo 0) nao encontrado no arquivo.')
    return get_field(header, 76, 79)


def parse_vencimento(venc_str: str) -> date:
    """Converte string DDMMAA (6 chars) para date.

    Raises:
        ValueError: se a string nao for valida.
    """
    if not (venc_str.isdigit() and len(venc_str) == 6):
        raise ValueError(f'Vencimento invalido: "{venc_str}" (esperado DDMMAA).')
    return datetime.strptime(venc_str, '%d%m%y').date()


def fmt_pos(start_0: int, end_0: int) -> str:
    """Formata posicoes 0-indexed [start:end] para notacao 1-indexed inclusiva."""
    return f'{start_0 + 1:03d}-{end_0:03d}'
