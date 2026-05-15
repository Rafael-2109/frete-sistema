# -*- coding: utf-8 -*-
"""
Construtores dos Blocos do SPED ECD Centralizado
=================================================

Funcoes para gerar cada bloco do arquivo SPED ECD Leiaute 9 com formato
EXATO segundo Manual ECD da Receita Federal.

Mitigacoes aplicadas (do pre-mortem):
- R1: J930 com 12 campos na ordem correta + IND_RESP_LEGAL + COD_ASSIN valido
- R2: I050 DT_ALT em DDMMAAAA (nao YYYYMMDD)
- R7: I350/I355 condicional (encerramento de exercicio)
- R8: J100 IND_GRP_BAL='A'/'P', IND_COD_AGL='T'/'D', 2 niveis 1, validacao Ativo=Passivo
- R9: J150 ordem correta + NU_ORDEM funcional
- R10: encoding Latin-1 com normalizacao Unicode + warning quando substituicao
- R11: pipe interno escapado
- R15: 2 J005 separados (BP + DRE)
- R16: ContadorRegistros incremental (nao itera array em RAM)

Autor: Sistema de Fretes
Data: 2026-05-14
Referencias: Manual ECD Leiaute 9 (Receita Federal), VRI Consulting (verificacao layout campo a campo)
"""

import logging
import unicodedata
from datetime import date
from typing import Dict, Iterable, List, Optional

from app.relatorios_fiscais.services.sped_ecd_constantes import (
    ACCOUNT_TYPE_TO_NAT,
    CNPJ_MATRIZ,
    CONTADOR_CPF,
    CONTADOR_EMAIL,
    COD_PLAN_REF,
    CONTADOR_CRC,
    CONTADOR_NOME,
    CONTADOR_NUM_SEQ_CRC,
    CONTADOR_UF_CRC,
    IDENT_MF,
    IND_CENTRALIZADA,
    IND_COD_AGL_DETALHE,
    IND_COD_AGL_TOTAL,
    IND_ESC,
    IND_ESC_CONS,
    IND_FIN_ESC,
    IND_GRANDE_PORTE,
    IND_GRP_BAL_ATIVO,
    IND_GRP_BAL_PASSIVO,
    IND_MUDANC_PC,
    LEIAUTE_VERSAO,
    PLANO_REFERENCIAL,
    QUALIFICACAO_CONTADOR,
    SOCIO_CPF,
    SOCIO_NOME,
    TIP_ECD,
    saldo_natural_dc,
)

logger = logging.getLogger(__name__)


# ============================================================
# HELPERS DE FORMATACAO
# ============================================================

def remover_acentos(texto: Optional[str]) -> str:
    """
    Normaliza texto para SPED: remove acentos, normaliza Unicode, tudo MAIUSCULO.
    V1.7: garante que caracteres SAO Latin-1 puros sem `?`.

    Mapeamento extras para caracteres Unicode comuns nao-Latin-1:
    - smart quotes -> ASCII quotes
    - em-dash, en-dash -> -
    - bullets -> *
    - setas (->, →, ←) -> -
    - copyright, registered, trademark -> (C), (R), (TM)
    - aspas/apostrofes Unicode -> '
    - outros chars Unicode -> espaco
    """
    if not texto:
        return ''
    # Substituicoes explicitas (mais comum -> ASCII)
    substituicoes = {
        '‘': "'", '’': "'", '‚': "'", '‛': "'",  # smart single quotes
        '“': '"', '”': '"', '„': '"', '‟': '"',  # smart double quotes
        '–': '-', '—': '-', '―': '-',                  # en-dash, em-dash, horizontal bar
        '•': '*', '‣': '*', '◦': '*',                  # bullets
        '…': '...',                                              # ellipsis
        ' ': ' ',                                                # nbsp
        '←': '<-', '→': '->', '↑': '^', '↓': 'v', # setas
        '©': '(C)', '®': '(R)', '™': '(TM)',           # marcas
        '°': 'o', '±': '+/-', '¼': '1/4', '½': '1/2', '¾': '3/4',
    }
    for k, v in substituicoes.items():
        texto = texto.replace(k, v)
    # NFKD decompoe acentos (e -> e + combinador)
    nfkd = unicodedata.normalize('NFKD', texto)
    # Remove combinadores (categoria Mn = Mark, Nonspacing)
    sem_acentos = ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')
    # Filtrar para Latin-1 puro: cada char deve caber em 1 byte Latin-1
    # Substitui chars fora do Latin-1 por espaco (em vez de '?')
    limpo_latin1 = []
    for c in sem_acentos:
        if c == ' ' or c.isprintable():
            try:
                c.encode('latin-1')
                limpo_latin1.append(c)
            except UnicodeEncodeError:
                limpo_latin1.append(' ')  # substitui por espaco (nao por ?)
    return ''.join(limpo_latin1).upper().strip()


def formatar_registro(campos: List) -> str:
    """
    Formata uma linha do SPED: |campo1|campo2|...|

    Mitigacao R11: substitui `|` interno por espaco (pipe e separador).
    Mitigacao R10: trata None, False, ''.
    """
    out = []
    for c in campos:
        if c is None or c is False:
            out.append('')
        elif isinstance(c, (int, float)):
            out.append(str(c))
        else:
            s = str(c).replace('|', ' ').replace('\r', ' ').replace('\n', ' ')
            out.append(s)
    return '|' + '|'.join(out) + '|'


def formatar_valor(valor: Optional[float], casas: int = 2) -> str:
    """
    Formata valor monetario para SPED: virgula decimal, sem separador de milhar.
    Sinal negativo prefixado.
    """
    if valor is None:
        return '0,00'
    valor = float(valor)
    if abs(valor) < 0.01:
        return '0,00'
    s = f'{abs(valor):.{casas}f}'.replace('.', ',')
    return f'-{s}' if valor < 0 else s


def formatar_data(d) -> str:
    """Converte date/datetime/str ISO para DDMMAAAA (formato SPED)."""
    if d is None or d is False:
        return ''
    if isinstance(d, str):
        # Pode vir 'YYYY-MM-DD' (date) ou 'YYYY-MM-DD HH:MM:SS' (datetime)
        try:
            from datetime import datetime
            if 'T' in d or ' ' in d:
                return datetime.fromisoformat(d.split(' ')[0].split('T')[0]).strftime('%d%m%Y')
            return datetime.strptime(d[:10], '%Y-%m-%d').strftime('%d%m%Y')
        except (ValueError, TypeError):
            return ''
    return d.strftime('%d%m%Y')


def formatar_dt_alt(create_date_iso: Optional[str], dt_ini_periodo: date) -> str:
    """
    Formata DT_ALT do I050 em DDMMAAAA, garantindo que nao seja posterior
    ao inicio do periodo SPED (evita warning PVA).
    Mitigacao R2.
    """
    from datetime import datetime
    try:
        s = (create_date_iso or '2010-01-01')[:10]
        dt_create = datetime.strptime(s, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        dt_create = date(2010, 1, 1)
    dt_final = min(dt_create, dt_ini_periodo)
    return dt_final.strftime('%d%m%Y')


# ============================================================
# CONTADOR DE REGISTROS (mitigacao R16)
# ============================================================

class ContadorRegistros:
    """
    Conta registros SPED durante a geracao para emitir 9900 corretos.
    Evita iteracao em array gigante em memoria.
    """

    def __init__(self):
        self._counts = {}

    def emit(self, registro: str) -> str:
        """Conta e retorna o registro (passthrough)."""
        # Extrair tipo do registro: |0000|... -> '0000'
        if not registro or len(registro) < 6:
            return registro
        reg_type = registro[1:5]  # caractere 1-4 entre os pipes
        self._counts[reg_type] = self._counts.get(reg_type, 0) + 1
        return registro

    def build_9900(self) -> List[str]:
        """
        Gera os registros 9900 com contagem de cada tipo.
        Inclui auto-contagem dos 9900, 9990, 9999 que serao adicionados.
        """
        # +3 para 9900 (auto-referencia), 9990 (1 unico), 9999 (1 unico)
        n_9900_total = len(self._counts) + 3
        self._counts['9900'] = n_9900_total
        self._counts['9990'] = 1
        self._counts['9999'] = 1

        return [
            formatar_registro(['9900', reg, str(qtde)])
            for reg, qtde in sorted(self._counts.items())
        ]

    def total_linhas_arquivo(self) -> int:
        """Total de linhas do arquivo (para 9999)."""
        return sum(self._counts.values())


# ============================================================
# BLOCO 0 — Abertura e identificacao
# ============================================================

def construir_bloco_0(matriz_data: dict, params: dict, contador: ContadorRegistros) -> List[str]:
    """
    Bloco 0 do SPED ECD: abertura do arquivo + identificacao da empresa.
    Para CENTRALIZADA: emite 0000 com IDENT_MF=M, IND_CENTRALIZADA=0.
    NAO emite 0020 (que e exclusivo para descentralizada).
    """
    linhas = []

    # ------------------------------------------------------------
    # 0000 — Abertura do arquivo digital (23 campos)
    # ------------------------------------------------------------
    nire = matriz_data.get('nire', '')
    linhas.append(contador.emit(formatar_registro([
        '0000',                                                # 1 REG
        'LECD',                                                # 2 LECD (literal)
        formatar_data(params['date_ini']),                     # 3 DT_INI
        formatar_data(params['date_fim']),                     # 4 DT_FIN
        remover_acentos(matriz_data.get('razao_social', matriz_data.get('name', ''))),  # 5 NOME
        matriz_data.get('cnpj', CNPJ_MATRIZ),                  # 6 CNPJ matriz (sem mascara)
        matriz_data.get('uf', 'SP'),                           # 7 UF
        matriz_data.get('ie', ''),                             # 8 IE
        matriz_data.get('cod_mun', ''),                        # 9 COD_MUN (IBGE)
        matriz_data.get('im', ''),                             # 10 IM
        '',                                                    # 11 IND_SIT_ESP (vazio = Regular)
        '0',                                                   # 12 IND_SIT_INI_PER (0=Regular)
        '1' if nire else '0',                                  # 13 IND_NIRE (1 se tem)
        IND_FIN_ESC,                                           # 14 IND_FIN_ESC
        '',                                                    # 15 COD_HASH_SUB (so substituicao)
        IND_GRANDE_PORTE,                                      # 16 IND_GRANDE_PORTE
        TIP_ECD,                                               # 17 TIP_ECD
        '',                                                    # 18 COD_SCP (Sociedade em Conta de Participacao)
        IDENT_MF,                                              # 19 IDENT_MF (M=Matriz)
        IND_ESC_CONS,                                          # 20 IND_ESC_CONS (N=sem bloco K)
        IND_CENTRALIZADA,                                      # 21 IND_CENTRALIZADA (0=Centralizada)
        IND_MUDANC_PC,                                         # 22 IND_MUDANC_PC
        COD_PLAN_REF,                                          # 23 COD_PLAN_REF (1=Lucro Real)
    ])))

    # ------------------------------------------------------------
    # 0001 — Abertura do bloco 0
    # ------------------------------------------------------------
    linhas.append(contador.emit(formatar_registro([
        '0001',                                                # 1 REG
        '0',                                                   # 2 IND_DAD (0=com dados)
    ])))

    # ------------------------------------------------------------
    # 0007 — Outras Inscricoes Cadastrais (OBRIGATORIO no Leiaute 9)
    # ------------------------------------------------------------
    # Manual ECD: PVA exige ao menos 1 registro 0007. Emitimos a Inscricao
    # Estadual da matriz (Fazenda do estado da matriz como instituicao).
    # COD_ENT_REF aceita UF (Fazenda Estadual) ou codigos 00-04 (BC/SUSEP/CVM/ANTT).
    ie_matriz = matriz_data.get('ie', '').strip()
    if ie_matriz:
        linhas.append(contador.emit(formatar_registro([
            '0007',                                            # 1 REG
            matriz_data.get('uf', 'SP'),                       # 2 COD_ENT_REF (UF = Fazenda Estadual)
            ie_matriz,                                         # 3 COD_INSCR (Inscricao Estadual)
        ])))

    # Modalidade centralizada NAO usa 0020 (omitido propositalmente)

    # ------------------------------------------------------------
    # 0990 — Encerramento do bloco 0
    # ------------------------------------------------------------
    qtde_bloco_0 = len(linhas) + 1  # inclui o proprio 0990
    linhas.append(contador.emit(formatar_registro([
        '0990',                                                # 1 REG
        str(qtde_bloco_0),                                     # 2 QTD_LIN_0
    ])))

    return linhas


# ============================================================
# BLOCO I — Plano de contas e lancamentos contabeis
# ============================================================

def construir_bloco_I_abertura(params: dict, matriz_data: dict, contador: ContadorRegistros) -> List[str]:
    """Cabecalho do bloco I: I001, I010, I030."""
    linhas = []

    # I001 — Abertura do bloco I
    linhas.append(contador.emit(formatar_registro([
        'I001',                                                # 1 REG
        '0',                                                   # 2 IND_DAD (0=com dados)
    ])))

    # I010 — Identificacao da escrituracao contabil
    linhas.append(contador.emit(formatar_registro([
        'I010',                                                # 1 REG
        IND_ESC,                                               # 2 IND_ESC (G=Diario Completo)
        LEIAUTE_VERSAO,                                        # 3 COD_VER_LC (9.00)
    ])))

    # I030 — Termo de Abertura do Livro (12 campos conforme Manual ECD Leiaute 9)
    # Ref: http://sped.rfb.gov.br/estatico/2D/.../Manual_ECD_Leiaute9.pdf
    # Bug historico: emitia 10 campos -> PVA rejeitava com "quantidade de campos
    # diferente do especificado no layout". Adicionados DT_ARQ_CONV (10),
    # DESC_MUN (11) e DT_EX_SOCIAL (12, obrigatorio).
    linhas.append(contador.emit(formatar_registro([
        'I030',                                                # 1  REG
        'TERMO DE ABERTURA',                                   # 2  DNRC_ABERT (literal)
        '1',                                                   # 3  NUM_ORD (sequencial do livro, >0)
        remover_acentos('Livro Diario (Completo, sem escrituracao auxiliar).'),  # 4 NAT_LIVR
        '1',                                                   # 5  QTD_LIN (placeholder — atualizado no encerramento)
        remover_acentos(matriz_data.get('razao_social', '')),  # 6  NOME
        matriz_data.get('nire', ''),                           # 7  NIRE (opcional)
        matriz_data.get('cnpj', CNPJ_MATRIZ),                  # 8  CNPJ
        formatar_data(params.get('date_arq_reg')),             # 9  DT_ARQ (opcional)
        '',                                                    # 10 DT_ARQ_CONV (conversao S/S -> empresaria - vazio)
        remover_acentos(matriz_data.get('nome_municipio', '')),# 11 DESC_MUN (municipio - opcional)
        formatar_data(params.get('date_fim')),                 # 12 DT_EX_SOCIAL (data fim exercicio - OBRIGATORIO)
    ])))

    return linhas


def construir_0150(participantes: List[dict], contador: ContadorRegistros) -> List[str]:
    """
    Tabela de Cadastro do Participante (0150) — V1.1 mitigacao R13.

    Emitido APENAS se houver participantes. PVA exige se I250 usar COD_PART.

    participantes: lista de dicts vinda de buscar_participantes_periodo()
    """
    linhas = []
    for p in participantes:
        linhas.append(contador.emit(formatar_registro([
            '0150',                                            # 1 REG
            p['cod_part'],                                     # 2 COD_PART (CNPJ ou CPF, sem mascara)
            remover_acentos(p['name'])[:100],                  # 3 NOME (max 100)
            p.get('cod_pais', '01058'),                        # 4 COD_PAIS (01058 = Brasil)
            p['cnpj_cpf'] if len(p['cnpj_cpf']) == 14 else '', # 5 CNPJ (so se PJ - 14 digitos)
            p['cnpj_cpf'] if len(p['cnpj_cpf']) == 11 else '', # 6 CPF (so se PF - 11 digitos)
            p.get('ie', ''),                                   # 7 IE
            p.get('cod_mun', ''),                              # 8 COD_MUN (IBGE)
            p.get('suframa', ''),                              # 9 SUFRAMA
            remover_acentos(p.get('endereco', ''))[:60],       # 10 ENDERECO
            p.get('num', '')[:10],                             # 11 NUM
            remover_acentos(p.get('complemento', ''))[:60],    # 12 COMPL
            remover_acentos(p.get('bairro', ''))[:60],         # 13 BAIRRO
        ])))
    return linhas


def construir_I050(plano_consolidado: List[dict], params: dict, contador: ContadorRegistros) -> List[str]:
    """
    Plano de Contas (I050) — APENAS I050, sem I051.

    DEPRECATED para uso direto no service: prefira construir_I050_com_I051()
    que intercala I051 logo apos cada I050 analitico (sequencia exigida pelo PVA,
    ja que o I051 nao carrega COD_CTA — vinculo e por posicao).

    Mantida para retrocompatibilidade / testes que isolam o I050.

    plano_consolidado: lista de dicts {code, nivel, nat, tipo (S/A), name, cod_sup, dt_alt}
    Espera-se que ja venha com hierarquia sintetica + analiticas, ordenado por code.
    """
    linhas = []

    for c in plano_consolidado:
        # V1.2: usar l10n_br_cod_nat real do Odoo (99% cobertura) com fallback no account_type
        nat = c.get('cod_nat_odoo') or ACCOUNT_TYPE_TO_NAT.get(c.get('account_type', ''), '99')
        linhas.append(contador.emit(formatar_registro([
            'I050',                                            # 1 REG
            c.get('dt_alt') or formatar_dt_alt(c.get('create_date'), params['date_ini']),  # 2 DT_ALT (DDMMAAAA)
            nat,                                               # 3 COD_NAT (01-09)
            c['tipo'],                                         # 4 IND_CTA (S/A)
            str(c['nivel']),                                   # 5 NIVEL (1-N)
            c['code'],                                         # 6 COD_CTA
            c.get('cod_sup', ''),                              # 7 COD_CTA_SUP
            remover_acentos(c.get('name', '')),                # 8 CTA (nome)
        ])))

    return linhas


def construir_I050_com_I051(
    plano_consolidado: List[dict],
    params: dict,
    contador: ContadorRegistros,
    codes_aglutinacao: set = None,
) -> List[str]:
    """
    Plano de Contas (I050) + Plano Referencial Receita (I051) + I052 INTERCALADOS.

    V1.6: emite tambem I052 (mapeamento de aglutinacao) apos I050 sintetica
    que aparece em J100/J150 como COD_AGL. PVA exige: "codigo de aglutinacao
    detalhe da demonstracao contabil deve estar em pelo menos um registro I052".

    Args:
        codes_aglutinacao: set de codes do plano que serao usados como COD_AGL
                           em J100/J150. Para cada I050 com code nesta lista,
                           emite I052 apos I051 (ou apos I050 se sem I051).

    O PVA exige que o I051 venha LOGO APOS o I050 da conta analitica
    correspondente — pois o I051 nao carrega COD_CTA (so REG | COD_CCUS |
    COD_CTA_REF, 3 campos). O vinculo e implicito pela sequencia.

    Bug historico: o service emitia TODOS os I050 e depois TODOS os I051 em
    blocos separados. Mesmo com a quantidade de campos correta, o PVA nao
    conseguiria mapear o I051 a uma conta. Esta funcao corrige isso emitindo
    I050 + I051 + I052 para cada conta em sequencia.
    """
    linhas = []
    codes_agl = codes_aglutinacao or set()

    for c in plano_consolidado:
        # I050 — sempre emitido (sintetica ou analitica)
        nat = c.get('cod_nat_odoo') or ACCOUNT_TYPE_TO_NAT.get(c.get('account_type', ''), '99')
        linhas.append(contador.emit(formatar_registro([
            'I050',                                            # 1 REG
            c.get('dt_alt') or formatar_dt_alt(c.get('create_date'), params['date_ini']),  # 2 DT_ALT
            nat,                                               # 3 COD_NAT
            c['tipo'],                                         # 4 IND_CTA (S/A)
            str(c['nivel']),                                   # 5 NIVEL
            c['code'],                                         # 6 COD_CTA
            c.get('cod_sup', ''),                              # 7 COD_CTA_SUP
            remover_acentos(c.get('name', '')),                # 8 CTA
        ])))

        # I051 — apenas se for conta analitica com mapeamento referencial VALIDO
        if c.get('tipo') == 'A':
            cod_ref = c.get('conta_referencial_odoo') or PLANO_REFERENCIAL.get(c.get('account_type', ''), '')
            # V1.7: filtrar referenciais invalidos (mais de 5 niveis nao existem
            # no plano oficial RFB; codigos com '99.99' sao placeholders).
            # No Odoo CIEL IT, 923 das 1770 contas com referencial estao com
            # >5 niveis (invalido). Sem este filtro, PVA reprova 923 vezes.
            if cod_ref:
                niveis = cod_ref.count('.')
                tem_placeholder = '99.99' in cod_ref
                if niveis > 4 or tem_placeholder:
                    cod_ref = ''  # invalida -> nao emite I051
            if cod_ref:
                linhas.append(contador.emit(formatar_registro([
                    'I051',                                    # 1 REG
                    '',                                        # 2 COD_CCUS (vazio)
                    cod_ref,                                   # 3 COD_CTA_REF
                ])))

        # V1.6 — I052 para conta usada como COD_AGL no J100/J150
        if c['code'] in codes_agl:
            linhas.append(contador.emit(formatar_registro([
                'I052',                                        # 1 REG
                '',                                            # 2 COD_CCUS (vazio)
                c['code'],                                     # 3 COD_CTA (a propria conta)
            ])))

    return linhas


def construir_I051(plano_consolidado: List[dict], contador: ContadorRegistros) -> List[str]:
    """
    Plano Referencial Receita (I051) — apenas para contas analiticas.

    V1.2: usa l10n_br_conta_referencial REAL do Odoo CIEL IT (87% cobertura).
    Para os 13% sem mapeamento no Odoo, faz fallback via account_type.
    """
    linhas = []

    for c in plano_consolidado:
        if c.get('tipo') != 'A':
            continue  # so analiticas
        # V1.2: prioridade para mapeamento real do Odoo
        cod_ref = c.get('conta_referencial_odoo') or PLANO_REFERENCIAL.get(c.get('account_type', ''), '')
        if not cod_ref:
            continue  # sem mapeamento — pular (Receita aceita parcial)
        # I051 — Layout 9 do Manual ECD tem 3 campos (REG | COD_CCUS | COD_CTA_REF).
        # Bug historico: emitia 4 campos com COD_CTA extra, causando rejeicao PVA
        # ("quantidade de campos diferente do especificado no layout"). O vinculo
        # do I051 com a conta e dado pela SEQUENCIA: deve vir logo apos o I050 da
        # conta a que se refere (vide service.py — emissao intercalada I050+I051).
        linhas.append(contador.emit(formatar_registro([
            'I051',                                            # 1 REG
            '',                                                # 2 COD_CCUS (vazio — mapeamento sem CC)
            cod_ref,                                           # 3 COD_CTA_REF (codigo do plano referencial RFB)
        ])))

    return linhas


def construir_I100(plano_ccus: List[dict], params: dict, contador: ContadorRegistros) -> List[str]:
    """
    Tabela de Cadastro de Centros de Custo (I100) — V1.1 mitigacao R14.

    plano_ccus: lista de dicts {code, name, plan_name, dt_alt}
    """
    linhas = []
    for ccus in plano_ccus:
        # DT_ALT em DDMMAAAA
        dt_alt = formatar_dt_alt(ccus.get('dt_alt'), params['date_ini'])
        linhas.append(contador.emit(formatar_registro([
            'I100',                                            # 1 REG
            dt_alt,                                            # 2 DT_ALT (DDMMAAAA)
            ccus['code'],                                      # 3 COD_CCUS
            remover_acentos(ccus.get('name', ''))[:60],        # 4 CCUS (nome)
        ])))
    return linhas


def construir_I150_I155(saldos_mensais: dict, plano_consolidado: List[dict],
                        contador: ContadorRegistros) -> List[str]:
    """
    Saldos Periodicos (mensais) — I150 cabecalho + I155 detalhe por conta.

    saldos_mensais: dict {
        'YYYY-MM': {
            'date_ini': date,
            'date_fim': date,
            'por_code': {
                code: {'saldo_inicial': X, 'debit': Y, 'credit': Z, 'saldo_final': W}
            }
        }
    }
    """
    linhas = []

    # Mapa code -> account_type para indicador D/C correto (R5 mitigacao)
    code_to_type = {c['code']: c['account_type'] for c in plano_consolidado}

    for mes_key in sorted(saldos_mensais.keys()):
        mes_dados = saldos_mensais[mes_key]

        # I150 — cabecalho do periodo mensal
        linhas.append(contador.emit(formatar_registro([
            'I150',                                            # 1 REG
            formatar_data(mes_dados['date_ini']),              # 2 DT_INI
            formatar_data(mes_dados['date_fim']),              # 3 DT_FIN
        ])))

        # I155 — detalhe por conta (uma linha POR CODE, nao por account_id)
        por_code = mes_dados.get('por_code', {})
        for code in sorted(por_code.keys()):
            sd = por_code[code]
            account_type = code_to_type.get(code, '')
            ind_natural = saldo_natural_dc(account_type)

            # Indicador D/C do saldo: depende do sinal vs natureza
            saldo_ini = sd.get('saldo_inicial', 0) or 0
            saldo_fin = sd.get('saldo_final', 0) or 0

            ind_dc_ini = ind_natural if saldo_ini >= 0 else ('C' if ind_natural == 'D' else 'D')
            ind_dc_fin = ind_natural if saldo_fin >= 0 else ('C' if ind_natural == 'D' else 'D')

            linhas.append(contador.emit(formatar_registro([
                'I155',                                        # 1 REG
                code,                                          # 2 COD_CTA
                '',                                            # 3 COD_CCUS (vazio - sem CC)
                formatar_valor(abs(saldo_ini)),                # 4 VL_SLD_INI
                ind_dc_ini,                                    # 5 IND_DC_INI
                formatar_valor(sd.get('debit', 0) or 0),       # 6 VL_DEB
                formatar_valor(sd.get('credit', 0) or 0),      # 7 VL_CRED
                formatar_valor(abs(saldo_fin)),                # 8 VL_SLD_FIN
                ind_dc_fin,                                    # 9 IND_DC_FIN
            ])))

    return linhas


def construir_I200_I250(lancamentos_iter: Iterable[dict], _plano_consolidado: List[dict],
                         contador: ContadorRegistros) -> Iterable[str]:
    """
    Lancamentos contabeis (I200 cabecalho + I250 partidas).

    Generator: emite linha por linha (mitigacao R3 - sem acumular em memoria).

    lancamentos_iter: iterable de dicts com:
        {
            'num': sequencial NUM_LCTO,
            'date': date,
            'lines': [{
                'code': str (resolvido para code consolidado),
                'debit': float,
                'credit': float,
                'name': str,
                'partner_name': str,
            }, ...]
        }
    """
    for lcto in lancamentos_iter:
        # Calcular VL_LCTO (valor total = soma dos debitos OU creditos, ambos iguais)
        lines = lcto.get('lines', [])
        vl_lcto = sum(float(ln.get('debit') or 0) for ln in lines)
        if vl_lcto == 0:
            vl_lcto = sum(float(ln.get('credit') or 0) for ln in lines)
        if vl_lcto == 0:
            continue  # pula lancamento zerado (sem efeito)

        # I200 — cabecalho do lancamento (6 campos conforme Manual ECD Leiaute 9)
        # Bug historico: emitia 5 campos -> PVA rejeitava com "quantidade de campos
        # diferente do especificado no layout". Adicionado DT_LCTO_EXT (campo 6,
        # nao-obrigatorio — usado apenas para lancamentos extemporaneos IND_LCTO='X').
        yield contador.emit(formatar_registro([
            'I200',                                            # 1 REG
            str(lcto['num']),                                  # 2 NUM_LCTO (sequencial)
            formatar_data(lcto['date']),                       # 3 DT_LCTO
            formatar_valor(vl_lcto),                           # 4 VL_LCTO
            'N',                                               # 5 IND_LCTO (N=Normal)
            '',                                                # 6 DT_LCTO_EXT (vazio — so se IND_LCTO=X)
        ]))

        # I250 — partidas do lancamento
        for ln in lines:
            debit = float(ln.get('debit') or 0)
            credit = float(ln.get('credit') or 0)
            if abs(debit) < 0.01 and abs(credit) < 0.01:
                continue  # pula linha zerada (R6)

            valor = debit if debit > 0 else credit
            indicador = 'D' if debit > 0 else 'C'
            code = ln.get('code') or '999'
            # V1.6: HIST com move_name no prefixo (padrao Odoo: "SIC/2024/04571: descricao").
            # Se name e ref vierem vazios, usar move_name como hist. Se nem isso,
            # placeholder anti-reprovacao PVA.
            move_name = (ln.get('move_name') or '').strip()
            name_part = (ln.get('name') or ln.get('ref') or '').strip()
            if move_name and name_part:
                hist_raw = f'{move_name}: {name_part}'
            elif move_name:
                hist_raw = move_name
            elif name_part:
                hist_raw = name_part
            else:
                hist_raw = f'LANCAMENTO CONTA {code}'  # placeholder ultimo recurso
            hist = remover_acentos(hist_raw[:600])    # HIST max ~600 chars
            cod_part = ln.get('cod_part', '')

            # V1.2: SPLIT de CCUS — emitir N I250s proporcionais
            distribuicao = ln.get('ccus_distribuicao') or []

            # I250 — Partidas (9 campos conforme Manual ECD Leiaute 9):
            # REG | COD_CTA | COD_CCUS | VL_DC | IND_DC | NUM_ARQ | COD_HIST_PAD | HIST | COD_PART
            # Bug historico: emitia 8 campos (faltava COD_HIST_PAD entre NUM_ARQ e HIST).
            if not distribuicao:
                # Sem CCUS — emitir 1 I250 unico sem COD_CCUS
                yield contador.emit(formatar_registro([
                    'I250', code, '', formatar_valor(valor), indicador, '', '', hist, cod_part,
                ]))
            elif len(distribuicao) == 1:
                # 1 CCUS (100%) — emitir 1 I250 com COD_CCUS direto (sem rateio)
                cod_ccus = distribuicao[0][0]
                yield contador.emit(formatar_registro([
                    'I250', code, cod_ccus, formatar_valor(valor), indicador, '', '', hist, cod_part,
                ]))
            else:
                # SPLIT: emitir N I250s com VALORES PROPORCIONAIS
                # Mitigacao code-review BLOCKER #2: pre-calcula valores e soma == valor.
                # Pula partidas < 0.01 ANTES de alocar centavos (evita desbalanceio).
                valores_pre = []
                soma_pre = 0.0
                for cod_ccus, pct in distribuicao:
                    v = round(valor * (pct / 100.0), 2)
                    if abs(v) < 0.01:
                        continue  # pula partida insignificante
                    valores_pre.append((cod_ccus, v))
                    soma_pre += v

                if not valores_pre:
                    # Todos centavos seriam < 0.01 — emitir 1 I250 unico com primeiro CCUS
                    yield contador.emit(formatar_registro([
                        'I250', code, distribuicao[0][0], formatar_valor(valor),
                        indicador, '', '', hist, cod_part,
                    ]))
                else:
                    # Re-alocar centavos restantes (valor - soma_pre) ao ULTIMO partida emitida
                    diff = round(valor - soma_pre, 2)
                    if abs(diff) >= 0.01:
                        ult_cod, ult_v = valores_pre[-1]
                        valores_pre[-1] = (ult_cod, round(ult_v + diff, 2))

                    for cod_ccus, v_partida in valores_pre:
                        yield contador.emit(formatar_registro([
                            'I250', code, cod_ccus, formatar_valor(v_partida), indicador, '',
                            '', hist, cod_part,
                        ]))


def construir_I350_I355(saldos_resultado: dict, plano_consolidado: List[dict],
                        params: dict, contador: ContadorRegistros) -> List[str]:
    """
    Saldos das Contas de Resultado Antes do Encerramento (I350/I355).
    SO emitir se DT_FIM = 31/12 (encerramento de exercicio). Mitigacao R7.

    saldos_resultado: dict {code: {'saldo': X, 'account_type': Y}}
    """
    date_fim = params['date_fim']
    if not (date_fim.month == 12 and date_fim.day == 31):
        return []  # so emite no encerramento

    linhas = []

    # I350 — cabecalho da data de encerramento
    linhas.append(contador.emit(formatar_registro([
        'I350',                                                # 1 REG
        formatar_data(date_fim),                               # 2 DT_RES
    ])))

    # I355 — saldos das contas de resultado por code consolidado
    code_to_type = {c['code']: c['account_type'] for c in plano_consolidado}
    for code in sorted(saldos_resultado.keys()):
        sd = saldos_resultado[code]
        account_type = sd.get('account_type', code_to_type.get(code, ''))
        saldo = sd.get('saldo', 0) or 0
        ind_natural = saldo_natural_dc(account_type)
        ind_dc = ind_natural if saldo >= 0 else ('C' if ind_natural == 'D' else 'D')

        linhas.append(contador.emit(formatar_registro([
            'I355',                                            # 1 REG
            code,                                              # 2 COD_CTA
            '',                                                # 3 COD_CCUS (vazio)
            formatar_valor(abs(saldo)),                        # 4 VL_CTA
            ind_dc,                                            # 5 IND_DC
        ])))

    return linhas


def construir_I990(contador_bloco_I: int) -> str:
    """Encerramento do bloco I."""
    return formatar_registro([
        'I990',
        str(contador_bloco_I + 1),  # +1 para incluir o proprio I990
    ])


# ============================================================
# BLOCO J — Demonstracoes contabeis (BP, DRE) e signatarios
# ============================================================

def construir_J001(contador: ContadorRegistros) -> str:
    """J001 — Abertura do bloco J."""
    return contador.emit(formatar_registro([
        'J001',                                                # 1 REG
        '0',                                                   # 2 IND_DAD (0=com dados)
    ]))


def calcular_saldos_hierarquicos(
    balanco_analiticas: dict,
    plano_consolidado: List[dict],
) -> Dict[str, dict]:
    """
    V1.6: a partir do balanco das contas ANALITICAS, calcula saldos das
    SINTETICAS somando as analiticas descendentes (propagacao por cod_sup).

    Args:
        balanco_analiticas: dict {code: {'saldo_inicial', 'saldo_final', ...}}
                            so contem analiticas (vem de calcular_balanco_consolidado).
        plano_consolidado: lista com sinteticas+analiticas (cada uma com cod_sup).

    Returns:
        dict {code: {'saldo_inicial', 'saldo_final', 'name', 'account_type', 'tipo', 'nivel', 'cod_sup'}}
        Inclui TODOS os codes do plano (sintet+anal) com saldos calculados.
    """
    # Index do plano por code
    plano_by_code = {c['code']: c for c in plano_consolidado}

    saldos = {}

    # 1. Inicializar saldos das analiticas (sao folhas)
    for c in plano_consolidado:
        saldos[c['code']] = {
            'saldo_inicial': 0.0,
            'saldo_final': 0.0,
            'code': c['code'],
            'name': c.get('name', ''),
            'account_type': c.get('account_type', ''),
            'tipo': c.get('tipo', 'A'),
            'nivel': c.get('nivel', 1),
            'cod_sup': c.get('cod_sup', ''),
        }

    # 2. Saldos das analiticas vem do balanco_analiticas
    for code, bal in balanco_analiticas.items():
        if code in saldos:
            saldos[code]['saldo_inicial'] = float(bal.get('saldo_inicial', 0) or 0)
            saldos[code]['saldo_final'] = float(bal.get('saldo_final', 0) or 0)

    # 3. Propagar para ancestrais (todos os cod_sup ate raiz)
    for c in plano_consolidado:
        if c.get('tipo') != 'A':
            continue
        s_anal = saldos.get(c['code'])
        if not s_anal:
            continue
        if abs(s_anal['saldo_inicial']) < 0.01 and abs(s_anal['saldo_final']) < 0.01:
            continue
        # Subir pela arvore via cod_sup
        cur_sup = c.get('cod_sup', '')
        visitados = set()
        while cur_sup and cur_sup not in visitados:
            visitados.add(cur_sup)
            slot = saldos.get(cur_sup)
            if slot is None:
                break
            slot['saldo_inicial'] += s_anal['saldo_inicial']
            slot['saldo_final'] += s_anal['saldo_final']
            sup_conta = plano_by_code.get(cur_sup)
            cur_sup = sup_conta.get('cod_sup', '') if sup_conta else ''

    return saldos


def construir_J005_J100(balanco_consolidado: dict, plano_consolidado: List[dict],
                        params: dict, contador: ContadorRegistros) -> List[str]:
    """
    Balanco Patrimonial: J005 (cabecalho BP) + J100 (linhas).

    V1.6: refatorado para usar CODES REAIS do plano de contas (1, 11, 111, 11101...)
    em vez de codes inventados (BP_ATIVO, BP_ATIVO_01). Resolve erros PVA:
    - "código de aglutinação detalhe deve estar em pelo menos um I052"
    - "código de aglutinação superior nao existe"
    - "saldo final ≠ inicial + débitos - créditos"

    Saldos INICIAIS agora preenchidos (vinha 0,00).

    Args:
        balanco_consolidado: dict {code: {'saldo_inicial', 'saldo_final', 'account_type'}}
                             ja com saldo inicial calculado (calcular_balanco_consolidado).
        plano_consolidado: lista com sinteticas+analiticas com hierarquia (cod_sup, nivel).
    """
    linhas = []

    # J005 — Cabecalho da Demonstracao (1 = BP)
    linhas.append(contador.emit(formatar_registro([
        'J005',                                                # 1 REG
        formatar_data(params['date_ini']),                     # 2 DT_INI
        formatar_data(params['date_fim']),                     # 3 DT_FIN
        '1',                                                   # 4 ID_DEM (1=BP)
        remover_acentos('BALANCO PATRIMONIAL'),                # 5 CAB_DEM
    ])))

    # V1.6: calcular saldos hierarquicos (sintetica = soma das analiticas filhas)
    saldos_hierarquicos = calcular_saldos_hierarquicos(balanco_consolidado, plano_consolidado)

    # Heuristica de classificacao por code (para sinteticas sem account_type)
    def _classe_pelo_code(code: str) -> str:
        """Retorna 'asset' ou 'liability_or_equity' baseado no primeiro digito do code.
        V1.7: ignora codes 3, 4, 5+ (resultado, custos, compensacao) — nao vao para BP."""
        if not code:
            return ''
        if code.startswith('1'):
            return 'asset'
        if code.startswith('2'):
            return 'liability_or_equity'  # passivo + PL (codes 2x no plano NACOM)
        # 3, 4, 5+: resultado/custos/compensacao — fora do balanco patrimonial
        return ''

    # Determinar classe patrimonial de cada code (asset / liability+equity / nao-patrimonial)
    def _classe_da_conta(conta) -> str:
        """Retorna 'asset', 'liability_or_equity' ou '' (nao patrimonial).

        V1.7: codes 5+ (contas de compensacao no plano NACOM, ex: REMESSA
        INDUSTRIALIZACAO, BONIFICACAO etc.) sao excluidos do balanco mesmo
        que account_type seja 'asset_current' ou 'liability_current'.
        Odoo CIEL IT classifica mal essas contas; o Manual ECD diz que
        compensacao tem natureza propria (COD_NAT=09) e fica fora do BP."""
        code = (conta.get('code') or '').strip()
        if code.startswith(('5', '6', '7', '8', '9')):
            return ''  # compensacao ou contas extra-balanco
        at = (conta.get('account_type') or '').strip()
        if at.startswith('asset'):
            return 'asset'
        if at.startswith(('liability', 'equity')):
            return 'liability_or_equity'
        if not at:
            # Sintetica gerada — usa o primeiro digito do code
            return _classe_pelo_code(code)
        return ''  # resultado, ignorar

    # Filtrar plano so patrimoniais (asset_*, liability_*, equity_*, + sinteticas 1x/2x)
    # E ordenar por code asc para hierarquia visual no PVA
    plano_patrimonial = sorted(
        [c for c in plano_consolidado if _classe_da_conta(c)],
        key=lambda c: c['code']
    )

    # Validacao Ativo = Passivo + PL
    total_ativo = saldos_hierarquicos.get('1', {}).get('saldo_final', 0)
    total_passivo_pl = saldos_hierarquicos.get('2', {}).get('saldo_final', 0)
    diff = abs(abs(total_ativo) - abs(total_passivo_pl))
    if diff > 0.01:
        logger.warning(
            f'BALANCO NAO BATE: Ativo={total_ativo:.2f} vs Passivo+PL={abs(total_passivo_pl):.2f} '
            f'(diff={diff:.2f}). Verificar consolidacao das companies.'
        )

    # Emitir J100 para cada conta patrimonial com saldo
    for conta in plano_patrimonial:
        code = conta['code']
        s = saldos_hierarquicos.get(code)
        if not s:
            continue
        # Pular contas sem movimento E sem saldo
        if abs(s['saldo_inicial']) < 0.01 and abs(s['saldo_final']) < 0.01:
            continue

        # Determinar IND_GRP_BAL (A=Ativo, P=Passivo+PL)
        classe = _classe_da_conta(conta)
        if classe == 'asset':
            ind_grp = IND_GRP_BAL_ATIVO
            ind_dc_natural = 'D'
        else:
            ind_grp = IND_GRP_BAL_PASSIVO
            ind_dc_natural = 'C'

        # IND_COD_AGL: T se sintetica, D se analitica
        ind_cod_agl = IND_COD_AGL_TOTAL if conta.get('tipo') == 'S' else IND_COD_AGL_DETALHE

        # IND_DC baseado em sinal (saldo negativo inverte natureza)
        def _ind_dc(saldo, natural):
            if saldo >= 0:
                return natural
            return 'C' if natural == 'D' else 'D'

        ind_dc_ini = _ind_dc(s['saldo_inicial'], ind_dc_natural)
        ind_dc_fin = _ind_dc(s['saldo_final'], ind_dc_natural)

        linhas.append(contador.emit(formatar_registro([
            'J100',                                            # 1 REG
            code,                                              # 2 COD_AGL (codigo do plano)
            ind_cod_agl,                                       # 3 IND_COD_AGL (T/D)
            str(conta.get('nivel', 1)),                        # 4 NIVEL_AGL
            conta.get('cod_sup', ''),                          # 5 COD_AGL_SUP
            ind_grp,                                           # 6 IND_GRP_BAL
            remover_acentos(conta.get('name', '')),            # 7 DESCR_COD_AGL
            formatar_valor(abs(s['saldo_inicial'])),           # 8 VL_CTA_INI (V1.6: REAL)
            ind_dc_ini,                                        # 9 IND_DC_CTA_INI
            formatar_valor(abs(s['saldo_final'])),             # 10 VL_CTA_FIN
            ind_dc_fin,                                        # 11 IND_DC_CTA_FIN
            '',                                                # 12 NOTA_EXP_REF
        ])))

    return linhas


def construir_J005_J150(dre_consolidado: dict, params: dict,
                         contador: ContadorRegistros) -> List[str]:
    """
    DRE: J005 (cabecalho DRE) + J150 (linhas).

    Mitigacao R9: ordem dos campos correta + NU_ORDEM funcional (Receitas, Custos, Despesas).
    Mitigacao R15: J005 com ID_DEM='2' (DRE).

    dre_consolidado: dict {code: {'saldo': X, 'account_type': Y, 'name': Z}}
    """
    linhas = []

    # J005 — Cabecalho DRE
    linhas.append(contador.emit(formatar_registro([
        'J005',                                                # 1 REG
        formatar_data(params['date_ini']),                     # 2 DT_INI
        formatar_data(params['date_fim']),                     # 3 DT_FIN
        '2',                                                   # 4 ID_DEM (2=DRE)
        remover_acentos('DEMONSTRACAO DO RESULTADO DO EXERCICIO'),  # 5 CAB_DEM
    ])))

    # Calcular agrupamentos por funcao DRE
    receita_bruta = sum(
        abs(s['saldo']) for s in dre_consolidado.values()
        if s.get('account_type') == 'income'
    )
    receita_outras = sum(
        abs(s['saldo']) for s in dre_consolidado.values()
        if s.get('account_type') == 'income_other'
    )
    custo_direto = sum(
        abs(s['saldo']) for s in dre_consolidado.values()
        if s.get('account_type') == 'expense_direct_cost'
    )
    despesa_geral = sum(
        abs(s['saldo']) for s in dre_consolidado.values()
        if s.get('account_type') == 'expense'
    )
    despesa_deprec = sum(
        abs(s['saldo']) for s in dre_consolidado.values()
        if s.get('account_type') == 'expense_depreciation'
    )

    receita_total = receita_bruta + receita_outras
    despesa_total = custo_direto + despesa_geral + despesa_deprec
    resultado_liquido = receita_total - despesa_total

    # J150 — em ordem funcional DRE (13 campos conforme Manual ECD Leiaute 9)
    # Layout: REG | NU_ORDEM | COD_AGL | IND_COD_AGL | NIVEL_AGL | COD_AGL_SUP |
    #         DESCR_COD_AGL | VL_CTA_INI | IND_DC_CTA_INI | VL_CTA_FIN |
    #         IND_DC_CTA_FIN | IND_GRP_DRE | NOTA_EXP_REF
    # Bug historico: emitia 10 campos com ordem ERRADA (COD_AGL como NU_ORDEM,
    # 'P'/'A' como IND_GRP_DRE — oficial e 'D'/'R'). PVA reprovava o bloco J inteiro.
    nu_ordem = 1
    # Tupla: (cod_agl, descr, valor, ind_dc, ind_grp_dre)
    # IND_GRP_DRE: R=Receita, D=Despesa (oficial Leiaute 9)
    grupos_dre = [
        ('DRE_REC_BRUTA', 'RECEITA OPERACIONAL BRUTA', receita_bruta, 'C', 'R'),
        ('DRE_REC_OUTRAS', 'OUTRAS RECEITAS', receita_outras, 'C', 'R'),
        ('DRE_REC_TOTAL', 'RECEITA TOTAL', receita_total, 'C', 'R'),
        ('DRE_CUSTO_DIR', 'CUSTO DIRETO DAS VENDAS', custo_direto, 'D', 'D'),
        ('DRE_DESP_GERAL', 'DESPESAS OPERACIONAIS', despesa_geral, 'D', 'D'),
        ('DRE_DESP_DEPREC', 'DEPRECIACAO E AMORTIZACAO', despesa_deprec, 'D', 'D'),
        ('DRE_DESP_TOTAL', 'CUSTOS E DESPESAS TOTAIS', despesa_total, 'D', 'D'),
        ('DRE_RESULT_LIQ', 'RESULTADO LIQUIDO DO EXERCICIO',
         abs(resultado_liquido), 'C' if resultado_liquido >= 0 else 'D',
         'R' if resultado_liquido >= 0 else 'D'),
    ]

    for cod_agl, descr, valor, ind_dc, ind_grp_dre in grupos_dre:
        if abs(valor) < 0.01:
            continue
        is_total = 'TOTAL' in descr or 'LIQ' in descr
        linhas.append(contador.emit(formatar_registro([
            'J150',                                            # 1  REG
            str(nu_ordem),                                     # 2  NU_ORDEM (numero!)
            cod_agl,                                           # 3  COD_AGL
            IND_COD_AGL_TOTAL if is_total else IND_COD_AGL_DETALHE,  # 4 IND_COD_AGL (T/D)
            '1' if is_total else '2',                          # 5  NIVEL_AGL
            '',                                                # 6  COD_AGL_SUP
            remover_acentos(descr),                            # 7  DESCR_COD_AGL
            '',                                                # 8  VL_CTA_INI (vazio — sem saldo anterior)
            '',                                                # 9  IND_DC_CTA_INI (vazio)
            formatar_valor(valor),                             # 10 VL_CTA_FIN (valor do periodo)
            ind_dc,                                            # 11 IND_DC_CTA_FIN
            ind_grp_dre,                                       # 12 IND_GRP_DRE (R=Receita, D=Despesa)
            '',                                                # 13 NOTA_EXP_REF (vazio)
        ])))
        nu_ordem += 1

    return linhas


def construir_J800(notas_explicativas: str, contador: ContadorRegistros) -> List[str]:
    """
    Outras Informacoes (J800) — V1.1 mitigacao.

    Notas Explicativas das Demonstracoes Contabeis em formato RTF.
    Se vazio, retorna lista vazia (J800 e opcional).
    """
    linhas = []
    if not notas_explicativas or not notas_explicativas.strip():
        return linhas

    # Mitigacao code-review BLOCKER #3: escape RTF de chars reservados
    # `\` -> `\\`, `{` -> `\{`, `}` -> `\}`, `\n` -> `\par `
    texto_normalizado = remover_acentos(notas_explicativas)
    texto_escapado = (
        texto_normalizado
        .replace('\\', '\\\\')
        .replace('{', '\\{')
        .replace('}', '\\}')
        .replace('\n', '\\par ')
    )
    # Converter texto plano para RTF basico
    rtf_basico = '{\\rtf1\\ansi\\deff0 ' + texto_escapado + '}'
    # SPED ECD aceita texto em RTF no campo TXT
    linhas.append(contador.emit(formatar_registro([
        'J800',                                                # 1 REG
        rtf_basico[:8000],                                     # 2 TXT (RTF, max recomendado 8000)
        'NOTAS_EXP',                                           # 3 IDENT_NOTA (identificador)
    ])))
    return linhas


def construir_J900(matriz_data: dict, params: dict, contador: ContadorRegistros) -> str:
    """
    J900 — Termo de Encerramento do Livro (8 campos conforme Manual ECD Leiaute 9).

    Layout: REG | DNRC_ENCER | NUM_ORD | NAT_LIVRO | NOME | QTD_LIN |
            DT_INI_ESCR | DT_FIN_ESCR

    Bug historico: emitia 5 campos (faltavam NOME, DT_INI_ESCR, DT_FIN_ESCR) —
    PVA reprovava o bloco J. Dados devem estar em sincronia com o I030.
    """
    return contador.emit(formatar_registro([
        'J900',                                                # 1 REG
        'TERMO DE ENCERRAMENTO',                               # 2 DNRC_ENCER (literal)
        '1',                                                   # 3 NUM_ORD (sincronizado com I030)
        remover_acentos('Livro Diario (Completo, sem escrituracao auxiliar).'),  # 4 NAT_LIVRO
        remover_acentos(matriz_data.get('razao_social', '')),  # 5 NOME (sincronizado com I030)
        '999999',                                              # 6 QTD_LIN (placeholder — total linhas)
        formatar_data(params.get('date_ini')),                 # 7 DT_INI_ESCR
        formatar_data(params.get('date_fim')),                 # 8 DT_FIN_ESCR
    ]))


def construir_J930(params: dict, contador: ContadorRegistros) -> List[str]:
    """
    Identificacao dos Signatarios (J930).
    Mitigacao R1: layout 12 campos correto.

    V1.2: CONTADOR_CPF e CONTADOR_EMAIL agora sao constantes fixas.

    params:
        qualif_socio: codigo de qualificacao do socio (001-999)
    """
    linhas = []

    # ------------------------------------------------------------
    # CONTADOR (NAO e responsavel legal) — V1.2: dados fixos
    # ------------------------------------------------------------
    linhas.append(contador.emit(formatar_registro([
        'J930',                                                # 1 REG
        remover_acentos(CONTADOR_NOME),                        # 2 IDENT_NOM (NOME PRIMEIRO!)
        CONTADOR_CPF,                                          # 3 IDENT_CPF_CNPJ (CPF fixo - 41832597890)
        'CONTADOR',                                            # 4 IDENT_QUALIF (texto)
        QUALIFICACAO_CONTADOR,                                 # 5 COD_ASSIN (900=Contabilista, 3 digits)
        CONTADOR_CRC,                                          # 6 IND_CRC (1SP041472)
        CONTADOR_EMAIL,                                        # 7 EMAIL (fixo)
        '',                                                    # 8 FONE (opcional)
        CONTADOR_UF_CRC,                                       # 9 UF_CRC (SP)
        CONTADOR_NUM_SEQ_CRC,                                  # 10 NUM_SEQ_CRC (SP/2026/041472 COMPLETO)
        '',                                                    # 11 DT_CRC (DDMMAAAA - opcional)
        'N',                                                   # 12 IND_RESP_LEGAL (N = Contador NAO e resp. legal)
    ])))

    # ------------------------------------------------------------
    # SOCIO (E o responsavel legal — IND_RESP_LEGAL='S')
    # ------------------------------------------------------------
    qualif_socio = (params.get('qualif_socio') or '205').strip()  # default 205=Administrador

    linhas.append(contador.emit(formatar_registro([
        'J930',                                                # 1 REG
        remover_acentos(SOCIO_NOME),                           # 2 IDENT_NOM
        SOCIO_CPF,                                             # 3 IDENT_CPF_CNPJ
        'SOCIO/REPRESENTANTE LEGAL',                           # 4 IDENT_QUALIF (texto)
        qualif_socio,                                          # 5 COD_ASSIN (3 digits)
        '',                                                    # 6 IND_CRC (vazio para nao-contador)
        CONTADOR_EMAIL,                                        # 7 EMAIL (mesmo email contato)
        '',                                                    # 8 FONE
        '',                                                    # 9 UF_CRC
        '',                                                    # 10 NUM_SEQ_CRC
        '',                                                    # 11 DT_CRC
        'S',                                                   # 12 IND_RESP_LEGAL (S = sim, este e responsavel legal)
    ])))

    return linhas


def construir_J990(contador_bloco_J: int) -> str:
    """Encerramento do bloco J."""
    return formatar_registro([
        'J990',
        str(contador_bloco_J + 1),  # +1 inclui o proprio J990
    ])


# ============================================================
# BLOCO 9 — Controle e encerramento (mitigacao R16)
# ============================================================

def construir_bloco_9(contador: ContadorRegistros) -> List[str]:
    """
    Bloco 9: 9001 + 9900 (contagem por tipo) + 9990 + 9999.

    Mitigacao R16/R17: usa ContadorRegistros incremental (nao itera array em RAM).
    """
    linhas = []

    # 9001 — Abertura do bloco 9
    linhas.append(contador.emit(formatar_registro([
        '9001',                                                # 1 REG
        '0',                                                   # 2 IND_DAD
    ])))

    # 9900 — Contagem por tipo de registro
    # build_9900() ja adiciona auto-contagem dos 9900/9990/9999
    for linha_9900 in contador.build_9900():
        linhas.append(linha_9900)
        # Nao recontar (build_9900 ja incluiu na contagem total)

    # 9990 — Encerramento do bloco 9
    qtde_bloco_9 = len(linhas) + 1  # inclui o proprio 9990
    linhas.append(formatar_registro([
        '9990',
        str(qtde_bloco_9),
    ]))

    # 9999 — Encerramento do arquivo digital
    total_arquivo = contador.total_linhas_arquivo()
    linhas.append(formatar_registro([
        '9999',
        str(total_arquivo),
    ]))

    return linhas
