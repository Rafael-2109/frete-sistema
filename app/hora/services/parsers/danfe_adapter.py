"""Adapter fino sobre o parser DANFE da CarVia para uso no módulo HORA.

**Regra (app/hora/CLAUDE.md)**: não duplicar parser. Reusar
`app/carvia/services/parsers/danfe_pdf_parser.parsear_danfe_pdf` e traduzir
o resultado para o formato esperado pelos services de ingestão HORA.

Parser CarVia:
- Camada 1: regex.
- Camada 2: LLM Haiku (campos faltantes).
- Camada 3: LLM Sonnet (fallback).
- Veículos (chassi/motor/cor): extração dedicada via LLM da seção DADOS ADICIONAIS.

Entrada: bytes de PDF DANFE.
Saída: dict no formato HORA (separando header da NF e itens por chassi).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.carvia.services.parsers.danfe_pdf_parser import parsear_danfe_pdf

logger = logging.getLogger(__name__)


class DanfeParseError(Exception):
    """Erro irrecuperável ao parsear DANFE para HORA."""


def _normalizar_chassi(chassi: str) -> str:
    """Chassi em maiúsculas e sem espaços/hífens externos.

    Tamanho máximo permitido em `hora_moto.numero_chassi` é 30 (VARCHAR(30)).
    """
    if not chassi:
        return ''
    return chassi.strip().upper().replace(' ', '')


def _sanitizar_cnpj(cnpj: Optional[str]) -> Optional[str]:
    """Remove pontuação de CNPJ (deixa só dígitos). Preserva tamanho limitado a 20."""
    if not cnpj:
        return None
    digitos = ''.join(c for c in cnpj if c.isdigit())
    return digitos[:20] or None


def _sanitizar_cpf(documento: Optional[str]) -> Optional[str]:
    """Formata documento como CPF (XXX.XXX.XXX-XX) quando tem 11 digitos.

    Se ja tem pontuacao certa, preserva. Se e CNPJ (14 digitos), retorna None
    (caller decide o que fazer).
    """
    if not documento:
        return None
    digitos = ''.join(c for c in documento if c.isdigit())
    if len(digitos) != 11:
        return None
    return f'{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}'


def parse_danfe_to_hora_payload(
    pdf_bytes: bytes,
    nome_arquivo_origem: Optional[str] = None,
) -> Dict:
    """Parseia DANFE PDF e retorna payload pronto para o service de NF entrada.

    Args:
        pdf_bytes: conteúdo binário do PDF DANFE.
        nome_arquivo_origem: nome do arquivo para logging (opcional).

    Returns:
        {
            'nf': {  # campos de HoraNfEntrada
                'chave_44': str,
                'numero_nf': str,
                'serie_nf': Optional[str],
                'cnpj_emitente': str,
                'nome_emitente': Optional[str],
                'cnpj_destinatario': str,
                'data_emissao': date,
                'valor_total': Decimal,
                'parser_usado': 'danfe_pdf_parser_v1',
            },
            'itens': [
                {  # kwargs para HoraNfEntradaItem + sementes de HoraMoto
                    'numero_chassi': str,
                    'numero_motor': Optional[str],
                    'modelo_texto_original': Optional[str],
                    'cor_texto_original': Optional[str],
                    'ano_modelo': Optional[int],
                    'preco_real': Decimal,
                },
                ...
            ],
            'meta': {
                'metodo_extracao': 'REGEX' | 'HAIKU' | 'SONNET',
                'confianca': float,
                'arquivo_origem': Optional[str],
            },
        }

    Raises:
        DanfeParseError: quando campos obrigatórios ausentes.
    """
    from decimal import Decimal

    if not pdf_bytes:
        raise DanfeParseError("pdf_bytes vazio")

    resultado = parsear_danfe_pdf(pdf_bytes=pdf_bytes)

    chave = resultado.get('chave_acesso_nf')
    numero = resultado.get('numero_nf')
    cnpj_emit = _sanitizar_cnpj(resultado.get('cnpj_emitente'))
    cnpj_dest = _sanitizar_cnpj(resultado.get('cnpj_destinatario'))
    data_emissao = resultado.get('data_emissao')
    valor_total = resultado.get('valor_total')

    obrigatorios = {
        'chave_acesso_nf': chave,
        'numero_nf': numero,
        'cnpj_emitente': cnpj_emit,
        'data_emissao': data_emissao,
        'valor_total': valor_total,
    }
    faltantes = [k for k, v in obrigatorios.items() if not v]
    if faltantes:
        raise DanfeParseError(
            f"Campos obrigatórios ausentes após parser: {faltantes} "
            f"(arquivo={nome_arquivo_origem})"
        )

    if len(chave) != 44:
        raise DanfeParseError(
            f"chave_acesso_nf inválida (tamanho={len(chave)}, esperado=44)"
        )

    veiculos_raw: List[Dict] = resultado.get('veiculos') or []
    if not veiculos_raw:
        raise DanfeParseError(
            f"Nenhum veículo extraído do DANFE (arquivo={nome_arquivo_origem}). "
            f"Confira se é NF de moto e se o parser CarVia está ativo."
        )

    # Distribui valor_total proporcionalmente pelos veículos (fallback quando
    # parser não traz preço unitário).
    try:
        valor_total_dec = Decimal(str(valor_total))
    except Exception as exc:
        raise DanfeParseError(f"valor_total inválido: {valor_total!r} ({exc})")
    num_veiculos = len(veiculos_raw)
    preco_unitario_fallback = (
        (valor_total_dec / num_veiculos).quantize(Decimal('0.01'))
        if num_veiculos > 0
        else Decimal('0.00')
    )

    itens: List[Dict] = []
    for v in veiculos_raw:
        chassi_norm = _normalizar_chassi(v.get('chassi') or '')
        if not chassi_norm:
            logger.warning(
                "Veículo sem chassi ignorado (arquivo=%s): %s",
                nome_arquivo_origem, v,
            )
            continue
        if len(chassi_norm) > 30:
            raise DanfeParseError(
                f"Chassi excede 30 chars: {chassi_norm!r} (len={len(chassi_norm)})"
            )
        itens.append({
            'numero_chassi': chassi_norm,
            'numero_motor': v.get('numero_motor') or None,
            'modelo_texto_original': v.get('modelo') or None,
            'cor_texto_original': v.get('cor') or None,
            'ano_modelo': v.get('ano_modelo') or None,
            'preco_real': preco_unitario_fallback,
        })

    if not itens:
        raise DanfeParseError("Após filtrar chassis inválidos, nenhum item restou")

    # Destinatario: na NF de Entrada (Motochefe -> HORA) e B2B com CNPJ da
    # matriz; na NF de Saida (HORA -> consumidor) e pessoa fisica com CPF.
    # O parser CarVia ja suporta CPF via get_cnpj_destinatario (P5 fix).
    # Aqui separamos em campos tipados para consumo pelo service HORA.
    dest_digits = (
        ''.join(c for c in (resultado.get('cnpj_destinatario') or '') if c.isdigit())
    )
    cpf_destinatario = _sanitizar_cpf(dest_digits) if len(dest_digits) == 11 else None

    return {
        'nf': {
            'chave_44': chave,
            'numero_nf': numero,
            'serie_nf': resultado.get('serie_nf'),
            'cnpj_emitente': cnpj_emit,
            'nome_emitente': resultado.get('nome_emitente'),
            'cnpj_destinatario': cnpj_dest or '',
            # Campos tipados para NF de saida (destinatario pessoa fisica):
            'cpf_destinatario': cpf_destinatario,
            'nome_destinatario': resultado.get('nome_destinatario'),
            'data_emissao': data_emissao,
            'valor_total': valor_total_dec,
            'parser_usado': 'danfe_pdf_parser_v1',
            # Soma da quantidade declarada nos itens produto com NCM 8711*.
            # Comparado com len(itens) no detalhe da NF para sinalizar
            # inconsistencia do DANFE (ex: NF 36928 declarou MT-GIGA UN=1
            # mas listou 2 chassis nos Dados Adicionais).
            'qtd_declarada_itens': resultado.get('qtd_declarada_itens_veiculo'),
        },
        'itens': itens,
        'meta': {
            'metodo_extracao': resultado.get('metodo_extracao', 'REGEX'),
            'confianca': resultado.get('confianca', 0.0),
            'arquivo_origem': nome_arquivo_origem,
        },
    }
