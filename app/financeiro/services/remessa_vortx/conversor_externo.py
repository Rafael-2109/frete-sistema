"""
Conversor de arquivos CNAB 400 externos (BMP/274 ou VORTX/310 com erros)
para padrao VORTX/310 correto.

Aplica 7 patches byte-a-byte validados via protocolo armazenado em memoria
do Agente (/memories/empresa/protocolos/remessa_cnab400_vortx_310.md):

  Header:
    1. pos 077-079 = '310'                          (codigo banco)
    2. pos 080-094 = 'VORTX DTVM     '              (nome banco, 15 chars)
    3. pos 027-046 = CONTA_GRAFENO_HEADER           (codigo transmissao)

  Detalhe (cada linha tipo '1'):
    4. pos 063-065 = '310'                          (codigo banco)
    5. pos 066    = '0' ou '2'                      (multa flag — VORTX rejeita '1')
    6. pos 082    = DAC recalculado                 (algoritmo VORTX proprietario)

  Verificacao (sem patch):
    7. pos 121-126 = data DDMMAA > data_ref         (vencimento futuro)

Origem: sessao "REMESSA VORTX FINAL" (Marcus, 04/05/2026) + protocolo validado
byte-a-byte contra arquivo aceito pelo banco Vortx DTVM.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from app.financeiro.services.remessa_vortx.cnab_parser import (
    parse_arquivo,
    serializar_arquivo,
    replace_field,
    get_field,
    is_header,
    is_detalhe,
    detectar_banco_origem,
    parse_vencimento,
)
from app.financeiro.services.remessa_vortx.dac_calculator import calcular_dac_nosso_numero
from app.financeiro.services.remessa_vortx.layout_vortx import (
    BANCO,
    BANCO_NOME,
    CONTA_GRAFENO_HEADER,
    CARTEIRA,
)


# Configuracao do banco BMP (origem antiga). Usado apenas para deteccao/relatorio.
BANCO_BMP = '274'
NOME_BANCO_BMP = 'BMPMONEYPLUS'


@dataclass
class Alteracao:
    """Representa uma alteracao byte-a-byte aplicada em uma linha."""
    linha: int       # 1-indexed
    tipo_linha: str  # 'header' | 'detalhe' | 'outro'
    campo: str
    posicao: str     # ex: '077-079'
    de: str
    para: str

    def to_dict(self) -> dict:
        return {
            'linha': self.linha,
            'tipo_linha': self.tipo_linha,
            'campo': self.campo,
            'posicao': self.posicao,
            'de': self.de,
            'para': self.para,
        }


@dataclass
class ResultadoConversao:
    arquivo_bytes: bytes
    banco_origem: str
    qtd_titulos: int = 0
    alteracoes: List[Alteracao] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)

    @property
    def qtd_alteracoes(self) -> int:
        return len(self.alteracoes)

    @property
    def alteracoes_por_campo(self) -> dict:
        """Agrega alteracoes por campo para resumo."""
        agg: dict = {}
        for a in self.alteracoes:
            agg[a.campo] = agg.get(a.campo, 0) + 1
        return agg

    def to_dict_resumo(self) -> dict:
        return {
            'banco_origem': self.banco_origem,
            'qtd_titulos': self.qtd_titulos,
            'qtd_alteracoes': self.qtd_alteracoes,
            'alteracoes_por_campo': self.alteracoes_por_campo,
            'avisos': self.avisos,
        }


def converter(
    arquivo_bytes: bytes,
    multa_codigo: str = '2',
    data_ref: Optional[date] = None,
) -> ResultadoConversao:
    """Converte arquivo CNAB 400 para padrao VORTX/310 correto.

    Args:
        arquivo_bytes: bytes do arquivo .rem (pode ser BMP/274 ou VORTX/310-com-erros).
        multa_codigo: '0' (sem multa, usa config plataforma) ou '2' (usa percentual do
            arquivo nas pos 067-070). VORTX rejeita silenciosamente '1' (valido em BMP).
        data_ref: data de referencia para verificar vencimentos. Default: hoje (Brasil).

    Returns:
        ResultadoConversao com bytes corrigidos, lista de alteracoes e avisos.

    Raises:
        ValueError: se arquivo invalido (tamanho de linha, encoding) ou multa_codigo
            fora de {'0', '2'}.
    """
    if multa_codigo not in ('0', '2'):
        raise ValueError("multa_codigo deve ser '0' (sem multa) ou '2' (percentual).")

    if data_ref is None:
        from app.utils.timezone import agora_brasil_naive
        data_ref = agora_brasil_naive().date()

    lines, sep = parse_arquivo(arquivo_bytes)
    banco_origem = detectar_banco_origem(lines)

    alteracoes: List[Alteracao] = []
    avisos: List[str] = []
    qtd_titulos = 0

    nome_banco_padrao = BANCO_NOME[:15].ljust(15)

    for idx, line in enumerate(lines):
        if is_header(line):
            # Patch 1: codigo banco header
            valor = get_field(line, 76, 79)
            if valor != BANCO:
                line = replace_field(line, 76, 79, BANCO)
                alteracoes.append(Alteracao(idx + 1, 'header', 'codigo_banco', '077-079', valor, BANCO))

            # Patch 2: nome banco header
            valor = get_field(line, 79, 94)
            if valor != nome_banco_padrao:
                line = replace_field(line, 79, 94, nome_banco_padrao)
                alteracoes.append(Alteracao(idx + 1, 'header', 'nome_banco', '080-094', valor, nome_banco_padrao))

            # Patch 3: codigo de transmissao
            valor = get_field(line, 26, 46)
            if valor != CONTA_GRAFENO_HEADER:
                line = replace_field(line, 26, 46, CONTA_GRAFENO_HEADER)
                alteracoes.append(Alteracao(
                    idx + 1, 'header', 'codigo_transmissao', '027-046', valor, CONTA_GRAFENO_HEADER
                ))

            lines[idx] = line

        elif is_detalhe(line):
            qtd_titulos += 1

            # Patch 4: codigo banco detalhe
            valor = get_field(line, 62, 65)
            if valor != BANCO:
                line = replace_field(line, 62, 65, BANCO)
                alteracoes.append(Alteracao(idx + 1, 'detalhe', 'codigo_banco', '063-065', valor, BANCO))

            # Patch 5: multa flag
            valor = get_field(line, 65, 66)
            if valor != multa_codigo:
                line = replace_field(line, 65, 66, multa_codigo)
                alteracoes.append(Alteracao(idx + 1, 'detalhe', 'multa_flag', '066', valor, multa_codigo))

            # Patch 6: recalcular DAC
            nosso_numero = get_field(line, 70, 81)
            dac_atual = get_field(line, 81, 82)
            if nosso_numero.isdigit() and len(nosso_numero) == 11:
                try:
                    dac_correto = calcular_dac_nosso_numero(CARTEIRA, nosso_numero)
                    if dac_atual != dac_correto:
                        line = replace_field(line, 81, 82, dac_correto)
                        alteracoes.append(Alteracao(
                            idx + 1, 'detalhe', f'dac_nn_{nosso_numero}', '082', dac_atual, dac_correto
                        ))
                except ValueError as e:
                    avisos.append(f'Linha {idx + 1}: erro ao calcular DAC ({nosso_numero}): {e}')
            else:
                avisos.append(
                    f'Linha {idx + 1}: nosso numero invalido "{nosso_numero}" — DAC nao recalculado.'
                )

            # Verificacao 7: vencimento (apenas alerta, nao altera)
            venc_str = get_field(line, 120, 126)
            try:
                venc_dt = parse_vencimento(venc_str)
                if venc_dt <= data_ref:
                    avisos.append(
                        f'Linha {idx + 1}: vencimento {venc_dt.strftime("%d/%m/%Y")} '
                        f'<= data atual ({data_ref.strftime("%d/%m/%Y")}) — '
                        f'VORTX rejeita titulos vencidos.'
                    )
            except ValueError as e:
                avisos.append(f'Linha {idx + 1}: vencimento invalido: {e}')

            lines[idx] = line

    arquivo_final = serializar_arquivo(lines, sep)
    return ResultadoConversao(
        arquivo_bytes=arquivo_final,
        banco_origem=banco_origem,
        qtd_titulos=qtd_titulos,
        alteracoes=alteracoes,
        avisos=avisos,
    )
