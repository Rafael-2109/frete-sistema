"""
Validador read-only de arquivos CNAB 400 contra padrao VORTX/310.

Nao altera o arquivo. Apenas executa o checklist completo do protocolo
(/memories/empresa/protocolos/remessa_cnab400_vortx_310.md) e retorna
o resultado item-a-item para exibicao em UI.

Checks executados:
  Header:
    H1. Banco (pos 077-079) == '310'
    H2. Nome banco (pos 080-094) == 'VORTX DTVM     '
    H3. Codigo transmissao (pos 027-046) == CONTA_GRAFENO_HEADER

  Cada Detalhe (linha tipo '1'):
    D1. Banco (pos 063-065) == '310'
    D2. Multa flag (pos 066) in {'0', '2'}
    D3. DAC (pos 082) == calcular_dac_nosso_numero(carteira, NN)
    D4. Vencimento (pos 121-126) > data_ref (futuro)
"""
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from app.financeiro.services.remessa_vortx.cnab_parser import (
    parse_arquivo,
    get_field,
    is_header,
    is_detalhe,
    parse_vencimento,
)
from app.financeiro.services.remessa_vortx.dac_calculator import calcular_dac_nosso_numero
from app.financeiro.services.remessa_vortx.layout_vortx import (
    BANCO,
    BANCO_NOME,
    CONTA_GRAFENO_HEADER,
    CARTEIRA,
)


@dataclass
class CheckItem:
    """Um item de verificacao individual."""
    grupo: str        # 'header' | 'detalhe'
    descricao: str
    esperado: str
    encontrado: str
    ok: bool
    posicao: str = ''
    linha: int = 0    # 1-indexed

    def to_dict(self) -> dict:
        return {
            'grupo': self.grupo,
            'descricao': self.descricao,
            'esperado': self.esperado,
            'encontrado': self.encontrado,
            'ok': self.ok,
            'posicao': self.posicao,
            'linha': self.linha,
        }


@dataclass
class TituloResumo:
    """Resumo de validacao de um titulo (linha de detalhe)."""
    linha: int
    nosso_numero: str
    vencimento: str   # DDMMAA original
    valor_centavos: str
    ok: bool
    problemas: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'linha': self.linha,
            'nosso_numero': self.nosso_numero,
            'vencimento': self.vencimento,
            'valor_centavos': self.valor_centavos,
            'ok': self.ok,
            'problemas': self.problemas,
        }


@dataclass
class ResultadoValidacao:
    total_linhas: int = 0
    qtd_titulos: int = 0
    qtd_titulos_ok: int = 0
    checks: List[CheckItem] = field(default_factory=list)
    titulos: List[TituloResumo] = field(default_factory=list)
    erros: List[str] = field(default_factory=list)
    banco_origem: str = ''

    @property
    def todos_ok(self) -> bool:
        return (
            not self.erros
            and all(c.ok for c in self.checks)
            and self.qtd_titulos > 0
        )

    @property
    def qtd_checks_falha(self) -> int:
        return sum(1 for c in self.checks if not c.ok)

    def to_dict(self) -> dict:
        return {
            'total_linhas': self.total_linhas,
            'qtd_titulos': self.qtd_titulos,
            'qtd_titulos_ok': self.qtd_titulos_ok,
            'qtd_checks_falha': self.qtd_checks_falha,
            'todos_ok': self.todos_ok,
            'banco_origem': self.banco_origem,
            'erros': self.erros,
            'checks': [c.to_dict() for c in self.checks],
            'titulos': [t.to_dict() for t in self.titulos],
        }


def validar(arquivo_bytes: bytes, data_ref: Optional[date] = None) -> ResultadoValidacao:
    """Valida arquivo CNAB 400 contra padrao VORTX/310.

    Args:
        arquivo_bytes: bytes do arquivo .rem
        data_ref: data de referencia para vencimentos. Default: hoje (Brasil).

    Returns:
        ResultadoValidacao com checks executados e resumo por titulo.
        Em caso de erro fatal de parse, retorna resultado com erros preenchidos.
    """
    if data_ref is None:
        from app.utils.timezone import agora_brasil_naive
        data_ref = agora_brasil_naive().date()

    resultado = ResultadoValidacao()
    nome_banco_padrao = BANCO_NOME[:15].ljust(15)

    try:
        lines, _ = parse_arquivo(arquivo_bytes)
    except ValueError as e:
        resultado.erros.append(str(e))
        return resultado

    resultado.total_linhas = len(lines)

    for idx, line in enumerate(lines):
        linha_1based = idx + 1

        if is_header(line):
            # H1 — banco
            v = get_field(line, 76, 79)
            resultado.banco_origem = v
            resultado.checks.append(CheckItem(
                grupo='header',
                descricao='Codigo do banco',
                esperado=BANCO,
                encontrado=v,
                ok=(v == BANCO),
                posicao='077-079',
                linha=linha_1based,
            ))
            # H2 — nome
            v = get_field(line, 79, 94)
            resultado.checks.append(CheckItem(
                grupo='header',
                descricao='Nome do banco',
                esperado=repr(nome_banco_padrao),
                encontrado=repr(v),
                ok=(v == nome_banco_padrao),
                posicao='080-094',
                linha=linha_1based,
            ))
            # H3 — codigo transmissao
            v = get_field(line, 26, 46)
            resultado.checks.append(CheckItem(
                grupo='header',
                descricao='Codigo de transmissao',
                esperado=CONTA_GRAFENO_HEADER,
                encontrado=v,
                ok=(v == CONTA_GRAFENO_HEADER),
                posicao='027-046',
                linha=linha_1based,
            ))

        elif is_detalhe(line):
            resultado.qtd_titulos += 1
            nn = get_field(line, 70, 81)
            venc_str = get_field(line, 120, 126)
            valor = get_field(line, 126, 139)
            problemas: List[str] = []
            titulo_ok = True

            # D1 — banco detalhe
            v = get_field(line, 62, 65)
            ok = v == BANCO
            if not ok:
                problemas.append(f"banco {v!r} (esperado {BANCO!r})")
                titulo_ok = False
            resultado.checks.append(CheckItem(
                grupo='detalhe',
                descricao=f'Banco do titulo (linha {linha_1based})',
                esperado=BANCO,
                encontrado=v,
                ok=ok,
                posicao='063-065',
                linha=linha_1based,
            ))

            # D2 — multa flag
            v = get_field(line, 65, 66)
            ok = v in ('0', '2')
            if not ok:
                problemas.append(f"multa {v!r} (esperado '0' ou '2')")
                titulo_ok = False
            resultado.checks.append(CheckItem(
                grupo='detalhe',
                descricao=f'Multa flag (linha {linha_1based})',
                esperado="'0' ou '2'",
                encontrado=v,
                ok=ok,
                posicao='066',
                linha=linha_1based,
            ))

            # D3 — DAC
            dac_atual = get_field(line, 81, 82)
            if nn.isdigit() and len(nn) == 11:
                try:
                    dac_esperado = calcular_dac_nosso_numero(CARTEIRA, nn)
                    ok = dac_atual == dac_esperado
                    if not ok:
                        problemas.append(
                            f"DAC {dac_atual!r} (esperado {dac_esperado!r} para NN {nn})"
                        )
                        titulo_ok = False
                    resultado.checks.append(CheckItem(
                        grupo='detalhe',
                        descricao=f'DAC Nosso Numero {nn} (linha {linha_1based})',
                        esperado=dac_esperado,
                        encontrado=dac_atual,
                        ok=ok,
                        posicao='082',
                        linha=linha_1based,
                    ))
                except ValueError as e:
                    titulo_ok = False
                    problemas.append(f"DAC: {e}")
                    resultado.checks.append(CheckItem(
                        grupo='detalhe',
                        descricao=f'DAC Nosso Numero {nn} (linha {linha_1based})',
                        esperado='valido',
                        encontrado=f'erro: {e}',
                        ok=False,
                        posicao='082',
                        linha=linha_1based,
                    ))
            else:
                titulo_ok = False
                problemas.append(f"Nosso numero invalido: {nn!r}")
                resultado.checks.append(CheckItem(
                    grupo='detalhe',
                    descricao=f'Nosso Numero (linha {linha_1based})',
                    esperado='11 digitos numericos',
                    encontrado=nn,
                    ok=False,
                    posicao='071-081',
                    linha=linha_1based,
                ))

            # D4 — vencimento
            try:
                venc_dt = parse_vencimento(venc_str)
                ok = venc_dt > data_ref
                if not ok:
                    problemas.append(
                        f"vencido {venc_dt.strftime('%d/%m/%Y')} <= hoje "
                        f"{data_ref.strftime('%d/%m/%Y')}"
                    )
                    titulo_ok = False
                resultado.checks.append(CheckItem(
                    grupo='detalhe',
                    descricao=f'Vencimento {venc_dt.strftime("%d/%m/%Y")} (linha {linha_1based})',
                    esperado=f'> {data_ref.strftime("%d/%m/%Y")}',
                    encontrado=venc_str,
                    ok=ok,
                    posicao='121-126',
                    linha=linha_1based,
                ))
            except ValueError as e:
                titulo_ok = False
                problemas.append(f"vencimento: {e}")
                resultado.checks.append(CheckItem(
                    grupo='detalhe',
                    descricao=f'Vencimento (linha {linha_1based})',
                    esperado='DDMMAA valido futuro',
                    encontrado=venc_str,
                    ok=False,
                    posicao='121-126',
                    linha=linha_1based,
                ))

            if titulo_ok:
                resultado.qtd_titulos_ok += 1

            resultado.titulos.append(TituloResumo(
                linha=linha_1based,
                nosso_numero=nn,
                vencimento=venc_str,
                valor_centavos=valor,
                ok=titulo_ok,
                problemas=problemas,
            ))

    return resultado
