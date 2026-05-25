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
    CODES_COMPENSACAO_NO_BP_ATIVO,
    CODES_COMPENSACAO_NO_BP_ATIVO_PREFIXES,
    CODES_J100_COD_AGL_SUP_REDIRECT,
    CONTADOR_CPF,
    CONTADOR_DT_CRC,
    CONTADOR_EMAIL,
    COD_PLAN_REF,
    CONTADOR_CRC,
    CONTADOR_FONE,
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
    mapa_aglutinacao_dre: Dict[str, str] = None,
) -> List[str]:
    """
    Plano de Contas (I050) + Plano Referencial Receita (I051) + I052 INTERCALADOS.

    V1.6: emite tambem I052 (mapeamento de aglutinacao) apos I050 sintetica
    que aparece em J100/J150 como COD_AGL. PVA exige: "codigo de aglutinacao
    detalhe da demonstracao contabil deve estar em pelo menos um registro I052".

    Args:
        codes_aglutinacao: set de codes do plano que serao usados como COD_AGL
                           em J100 (BP — autorreferencia: COD_AGL = code da
                           propria conta). Para cada I050 com code nesta lista,
                           emite I052 com COD_AGL = code.
        mapa_aglutinacao_dre: V28 (2026-05-16) — dict {code_analitica: cod_agl_dre}
                              vinculando contas analiticas de resultado aos codes
                              detalhe do J150 (ex: '9.1.1', '9.2.2'). Para cada
                              conta com code neste mapa, emite I052 adicional com
                              COD_AGL = cod_agl_dre. PVA exige que codes detalhe
                              do J150 estejam em pelo menos 1 I052.

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
    mapa_dre = mapa_aglutinacao_dre or {}

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
            # V1.7 (revisado em V22 2026-05-15): filtrar referenciais invalidos.
            # Manual ECD Leiaute 9 + ground truth (SPED contadora aceito RFB) confirma
            # codes com ATE 6 niveis hierarquicos (5 pontos), ex: '3.01.01.01.02.05'.
            # Filtro original (>4 pontos) invalidava 923 codes validos.
            # Novo limite: pontos > 5 (= 7+ niveis = invalido RFB). Ver INCONSISTENCIAS_ODOO.md CAT 21.
            # '99.99' continua excluido (placeholders sem code real na Tabela 11 RFB).
            if cod_ref:
                pontos = cod_ref.count('.')
                tem_placeholder = '99.99' in cod_ref
                if pontos > 5 or tem_placeholder:
                    cod_ref = ''  # invalida -> nao emite I051
            if cod_ref:
                linhas.append(contador.emit(formatar_registro([
                    'I051',                                    # 1 REG
                    '',                                        # 2 COD_CCUS (vazio)
                    cod_ref,                                   # 3 COD_CTA_REF
                ])))

        # V1.6 — I052 para conta usada como COD_AGL no J100 (BP)
        # V1.9 (2026-05-15): SO emite I052 para analitica detalhe (tipo='A').
        # Bug V18: emitia I052 para sinteticas tambem porque codes_agl recebia
        # codes de sinteticas que aparecem em J100 como totalizadores (T).
        # PVA reprovou 552 erros "I052 em sintetica" + 236 "code agl. e totalizador".
        # Manual ECD: I052 vincula contas DETALHE da escrituracao ao codigo de
        # aglutinacao das demonstracoes. Sinteticas ja SAO o totalizador.
        # Ver SPED_ECD_PLANO.md CATEGORIA 1 + CATEGORIA 4.
        if c['code'] in codes_agl and c.get('tipo') == 'A':
            linhas.append(contador.emit(formatar_registro([
                'I052',                                        # 1 REG
                '',                                            # 2 COD_CCUS (vazio)
                c['code'],                                     # 3 COD_AGL (autorreferencia BP)
            ])))

        # V28 (CAT 5/20 fix 2026-05-16) — I052 para conta de resultado vinculada
        # a code DRE detalhe (J150). PVA exige que codes detalhe da DRE estejam
        # em pelo menos 1 I052 — caso contrario reclama 5 erros "code agl detalhe
        # deve estar em pelo menos um I052" + warnings de hierarquia incompleta.
        if c.get('tipo') == 'A' and c['code'] in mapa_dre:
            linhas.append(contador.emit(formatar_registro([
                'I052',                                        # 1 REG
                '',                                            # 2 COD_CCUS (vazio)
                mapa_dre[c['code']],                           # 3 COD_AGL (code DRE detalhe ex: 9.1.1)
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


def construir_I150_I155(saldos_mensais: dict, _plano_consolidado: List[dict],
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

            # V26 (2026-05-16): skip codes zerados (consistencia com filtro CAT 25
            # aplicado ao I050). Sem isso, I155 emite linhas para codes que foram
            # excluidos do plano (ex: conta `2.1.03.001.099` "Implantacao Contas a
            # Pagar" — existe no Odoo mas tem todos os meses zerados), e PVA reclama
            # "Conta informada deve existir no plano de contas e ser analitica" (5
            # erros V25 PVA).
            if (abs(sd.get('saldo_inicial', 0) or 0) < 0.01 and
                abs(sd.get('debit', 0) or 0) < 0.01 and
                abs(sd.get('credit', 0) or 0) < 0.01 and
                abs(sd.get('saldo_final', 0) or 0) < 0.01):
                continue

            # V22 (2026-05-15): IND_DC derivado do SINAL do balance Odoo, nao do account_type.
            # Manual ECD Leiaute 9 (validado contra PVA V21): VL_SLD_INI/FIN sempre positivo,
            # IND_DC indica D (devedor: balance>0) ou C (credor: balance<0). PVA calcula
            # saldo_fin_assinalado = (+/-)VL_SLD_INI + DEB - CRED e compara com VL_SLD_FIN.
            # Logica antiga (V1.0..V21) usava ACCOUNT_TYPE_TO_NAT para inverter sinal —
            # bugava 188 contas onde saldo Odoo era anormal vs natural (ex: 1130600001
            # 'ADIANTAMENTOS A FORNECEDORES' com account_type=liability_payable mas
            # balance Odoo positivo +R$3.3M). Ver SPED_ECD_PLANO.md CATEGORIA 3.
            saldo_ini = sd.get('saldo_inicial', 0) or 0
            saldo_fin = sd.get('saldo_final', 0) or 0

            ind_dc_ini = 'D' if saldo_ini > 0 else ('C' if saldo_ini < 0 else '')
            ind_dc_fin = 'D' if saldo_fin > 0 else ('C' if saldo_fin < 0 else '')

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

            # I250 — Partidas (9 campos conforme Manual ECD Leiaute 9):
            # REG | COD_CTA | COD_CCUS | VL_DC | IND_DC | NUM_ARQ | COD_HIST_PAD | HIST | COD_PART
            #
            # V1.8 (2026-05-15): SEMPRE emitir 1 I250 SEM COD_CCUS por partida.
            # Decisao do usuario apos analise PVA V17:
            #   "No SPED nao vai centro de custo".
            # Causa raiz V17: NACOM tem 1 plano analitico por filial; o Odoo retorna
            # analytic_distribution achatado de TODOS os planos. Como cada plano soma
            # 100%, o achatado somava >100% (ate 500-600%), o split proporcional
            # multiplicava o valor e o reajuste no ultimo CCUS gerava VL_DC negativo
            # gigante (Manual ECD: VL_DC deve ser SEMPRE positivo, sinal vem do IND_DC).
            # PVA rejeitou 13 partidas com erro "Conteudo do campo invalido".
            #
            # ccus_distribuicao da line ainda e calculada (sem custo extra) mas
            # ignorada aqui. Se EMITIR_CCUS_SPED for ligada no futuro, restaurar
            # logica de split conforme git history (commit anterior a V1.8).
            yield contador.emit(formatar_registro([
                'I250', code, '', formatar_valor(valor), indicador, '', '', hist, cod_part,
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


def _balanco_a_partir_de_saldos_mensais(saldos_mensais: dict,
                                          plano_consolidado: List[dict]) -> dict:
    """
    V23 (CAT 23) — Deriva balanco analiticas a partir de `saldos_mensais` do I155.

    Garante que J100 (Balanco Patrimonial) use exatamente os mesmos saldos do
    I155 (Saldos Periodicos), conforme exigido pelo PVA.

    Returns:
        dict {code: {'saldo_inicial', 'saldo_final', 'account_type', 'name'}}
            saldo_inicial = saldo_inicial do PRIMEIRO mes do periodo (cronologico)
            saldo_final   = saldo_final do ULTIMO mes do periodo (cronologico)
    """
    if not saldos_mensais:
        return {}

    meses_ordenados = sorted(saldos_mensais.keys())
    primeiro_mes = saldos_mensais[meses_ordenados[0]]
    ultimo_mes = saldos_mensais[meses_ordenados[-1]]

    por_code_ini = primeiro_mes.get('por_code', {})
    por_code_fin = ultimo_mes.get('por_code', {})

    code_to_at = {c['code']: c.get('account_type', '') for c in plano_consolidado}
    code_to_name = {c['code']: c.get('name', '') for c in plano_consolidado}

    # Conjunto de codes que aparecem em qualquer um dos dois meses
    all_codes = set(por_code_ini.keys()) | set(por_code_fin.keys())

    balanco = {}
    for code in all_codes:
        saldo_ini = (por_code_ini.get(code, {}) or {}).get('saldo_inicial', 0) or 0
        saldo_fin = (por_code_fin.get(code, {}) or {}).get('saldo_final', 0) or 0
        balanco[code] = {
            'saldo_inicial': saldo_ini,
            'saldo_final': saldo_fin,
            'account_type': code_to_at.get(code, ''),
            'name': code_to_name.get(code, ''),
        }

    return balanco


def construir_J005_unico(params: dict, contador: ContadorRegistros) -> str:
    """
    V29 (2026-05-16) — fix CAT 22 (J005 sem par J100+J150):

    Emite 1 unico J005 com ID_DEM=1 e CAB_DEM vazio, cobrindo BP+DRE juntos.
    Padrao confirmado no SPED da contadora (ground truth aceito pela RFB):
        |J005|01012024|31122024|1||

    Bug V28 e anteriores: emitia 2 J005 separados (ID_DEM=1 BP + ID_DEM=2 DRE).
    PVA reclamava "Deve existir pelo menos 1 J100 (Balanco) e 1 J150 (DRE)
    para cada J005" — porque cada J005 separado nao tinha o outro tipo.

    V35 (CAT 35 — 2026-05-24): DT_INI sempre 01/01/AAAA (exercicio social inteiro),
    nao date_ini do periodo SPED. Manual ECD: J005 deve cobrir exercicio completo,
    nao recorte semestral. Contadora 2S 2024 emite |J005|01012024|31122024|...
    independente de o SPED ser do 2S. V34 e anteriores emitiam |01072024| (errado).

    Layout J005 5 campos (Manual ECD Leiaute 9):
        REG | DT_INI | DT_FIN | ID_DEM | CAB_DEM
    """
    # V35: forcar DT_INI = 01/01 do ano do date_ini (exercicio social inteiro)
    from datetime import date as _date
    date_ini_real = params['date_ini']
    j005_dt_ini = _date(date_ini_real.year, 1, 1)
    return contador.emit(formatar_registro([
        'J005',                                                # 1 REG
        formatar_data(j005_dt_ini),                            # 2 DT_INI (V35: 01/01/AAAA)
        formatar_data(params['date_fim']),                     # 3 DT_FIN
        '1',                                                   # 4 ID_DEM (1 — cobre BP+DRE como contadora)
        '',                                                    # 5 CAB_DEM (vazio — padrao contadora)
    ]))


def construir_J005_J100(balanco_consolidado: dict, plano_consolidado: List[dict],
                        params: dict, contador: ContadorRegistros,
                        saldos_mensais: dict = None) -> List[str]:
    """
    Balanco Patrimonial: J005 (cabecalho BP) + J100 (linhas).

    V1.6: refatorado para usar CODES REAIS do plano de contas (1, 11, 111, 11101...)
    em vez de codes inventados (BP_ATIVO, BP_ATIVO_01). Resolve erros PVA:
    - "código de aglutinação detalhe deve estar em pelo menos um I052"
    - "código de aglutinação superior nao existe"
    - "saldo final ≠ inicial + débitos - créditos"

    Saldos INICIAIS agora preenchidos (vinha 0,00).

    V23 (2026-05-16) — fix CAT 23 (J100 saldos != I155):
    Quando `saldos_mensais` e passado, deriva o balanco do I155 em vez de usar
    `balanco_consolidado`. PVA exige consistencia interna entre J100 e I155 — se
    saldos diferem, reporta "J100.VL_CTA_FIN/INI != saldo calculado I155".
    Apos fix CAT 3 (V22), I155 ficou correto (IND_DC pelo sinal do balance),
    mas J100 continuava com saldo legado divergente. Esta correcao alinha as
    duas fontes: saldo_inicial = primeiro mes (1o.07) saldo_inicial,
    saldo_final = ultimo mes (12/2024) saldo_final.

    Args:
        balanco_consolidado: dict legado {code: {'saldo_inicial', 'saldo_final', 'account_type'}}.
                             Usado apenas se `saldos_mensais` for None.
        plano_consolidado: lista com sinteticas+analiticas com hierarquia (cod_sup, nivel).
        saldos_mensais: dict {YYYY-MM: {por_code: {code: {saldo_inicial, saldo_final, ...}}}}
                        Se passado, sobrescreve balanco_consolidado.
    """
    linhas = []

    # V29 (2026-05-16): J005 NAO mais emitido aqui. Emitido em service.py via
    # construir_J005_unico (1 J005 ID_DEM=1 cobre BP+DRE — padrao contadora aceito RFB).
    # Bug V28 PVA: "Deve existir 1 J100 e 1 J150 para cada J005" quando emitia 2 J005.

    # V23: derivar balanco analiticas dos saldos mensais (consistencia com I155)
    balanco_fonte = balanco_consolidado
    if saldos_mensais:
        balanco_fonte = _balanco_a_partir_de_saldos_mensais(saldos_mensais, plano_consolidado)
        # Log diff para diagnostico (so contas com diferenca relevante)
        if balanco_consolidado:
            diffs = 0
            for code, novo in balanco_fonte.items():
                antigo = balanco_consolidado.get(code, {})
                d_ini = abs(float(novo.get('saldo_inicial', 0) or 0) - float(antigo.get('saldo_inicial', 0) or 0))
                d_fin = abs(float(novo.get('saldo_final', 0) or 0) - float(antigo.get('saldo_final', 0) or 0))
                if d_ini > 0.01 or d_fin > 0.01:
                    diffs += 1
            logger.info(f'[J100 V23] Balanco derivado de I155 substitui balanco_consolidado em {diffs} codes (consistencia PVA).')

    # Heuristica de classificacao por code (para sinteticas sem account_type)
    def _classe_pelo_code(code: str) -> str:
        """Retorna 'asset' ou 'liability_or_equity' baseado no primeiro digito do code.
        V1.7: ignora codes 3, 4, 5+ (resultado, custos, compensacao) — nao vao para BP.
        V33 (CAT 32): excecao para CODES_COMPENSACAO_NO_BP_ATIVO (codes exatos das
        sinteticas) e _PREFIXES (analiticas 5101*) — contadora NACOM inclui
        compensacao no Ativo (recuperacao judicial)."""
        if not code:
            return ''
        if code in CODES_COMPENSACAO_NO_BP_ATIVO:
            return 'asset'
        if any(code.startswith(p) for p in CODES_COMPENSACAO_NO_BP_ATIVO_PREFIXES):
            return 'asset'
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
        compensacao tem natureza propria (COD_NAT=05) e fica fora do BP.

        V30 (CAT 6 fix 2026-05-16): SINTETICAS sempre classificadas via
        `_classe_pelo_code` (hierarquia do code) — NUNCA via account_type.
        Razao: sinteticas geradas em data.py herdam account_type da PRIMEIRA
        filha encontrada (`_gerar_hierarquia_sintetica`). Quando a filha tem
        cadastro Odoo incompativel (ex: 1130700001 ADIANT SALARIOS classificada
        como `expense` por bug de cadastro — INCONSIST. 5), a sintetica
        herdava 'expense' e era excluida do BP, deixando outras analiticas
        patrimoniais da mesma sub-arvore orfas no J100 (cod_sup nao existe).
        Para sinteticas, code prefix e dado puro do Odoo e nao ambiguo.
        Analiticas continuam usando account_type (autoritativo — proprio da conta).

        V33 (CAT 32 — 2026-05-24): excecao para CODES_COMPENSACAO_NO_BP_ATIVO.
        Contadora NACOM (recuperacao judicial) classifica codes 510101/510102
        como ATIVO (COD_AGL_SUP=115 ESTOQUES) totalizando R$ 27M. Sem isso,
        J100 fecha com diff de R$ 19,97M (REGRA_VALIDA_ATIVO_PASSIVO_FIN reprova).
        """
        code = (conta.get('code') or '').strip()
        # V33: excecao ANTES do filtro 5xx — codes/prefixes de compensacao no BP
        if code in CODES_COMPENSACAO_NO_BP_ATIVO:
            return 'asset'
        if any(code.startswith(p) for p in CODES_COMPENSACAO_NO_BP_ATIVO_PREFIXES):
            return 'asset'
        if code.startswith(('5', '6', '7', '8', '9')):
            return ''  # compensacao ou contas extra-balanco
        # V30: sinteticas SEMPRE pelo code (herdam account_type errado da filha)
        if conta.get('tipo') == 'S':
            return _classe_pelo_code(code)
        at = (conta.get('account_type') or '').strip()
        if at.startswith('asset'):
            return 'asset'
        if at.startswith(('liability', 'equity')):
            return 'liability_or_equity'
        if not at:
            # Analitica sem account_type (raro) — fallback pelo code
            return _classe_pelo_code(code)
        return ''  # resultado, ignorar

    # V30 (CAT 6 fix 2026-05-16): consistencia interna J100 sintetica T == soma filhas D.
    # ANTES: `calcular_saldos_hierarquicos` recebia plano_consolidado COMPLETO e propagava
    # saldos de TODAS as analiticas para as sinteticas, INCLUSIVE analiticas com
    # account_type=expense/income (excluidas do J100 por `_classe_da_conta`). Resultado:
    # sintetica T mostrava saldo > soma das filhas D emitidas. PVA reclamava
    # "totalizador != soma" e "cod_agl_sup nao existe" (analiticas orfas apontando
    # para sintetica nao emitida).
    # AGORA: filtrar plano por classe patrimonial ANTES de propagar — sinteticas
    # so recebem saldos de analiticas patrimoniais (que serao emitidas no J100).
    # Sinteticas continuam todas para preservar a arvore de cod_sup.
    plano_para_propagacao = [
        c for c in plano_consolidado
        if c.get('tipo') == 'S' or _classe_da_conta(c) != ''
    ]

    # V35 (CAT 12 — 2026-05-24): aplicar redirect cod_sup p/ J100 ANTES de
    # propagar saldos. Sem isso, saldo de 510101/510102 sobe pela arvore '5'
    # (compensacao raiz) e NUNCA chega em '1 ATIVO'. Resultado: Ativo nivel 1
    # nao inclui R$ 19,9M de compensacao, balanco nao bate. Com redirect na
    # propagacao, 510101 sobe via 115 -> 11 -> 1 e saldo agrega no Ativo total.
    # Aplicado APENAS na copia para J100 — plano original I050 mantem cod_sup real.
    plano_para_propagacao_j100 = []
    for c in plano_para_propagacao:
        if c['code'] in CODES_J100_COD_AGL_SUP_REDIRECT:
            c_redir = c.copy()
            c_redir['cod_sup'] = CODES_J100_COD_AGL_SUP_REDIRECT[c['code']]
            plano_para_propagacao_j100.append(c_redir)
        else:
            plano_para_propagacao_j100.append(c)

    # V1.6: calcular saldos hierarquicos (sintetica = soma das analiticas filhas)
    # V30: usa plano filtrado para que sinteticas batam com filhas emitidas
    # V35: plano com cod_sup J100-redirecionado para 510101/510102
    saldos_hierarquicos = calcular_saldos_hierarquicos(balanco_fonte, plano_para_propagacao_j100)

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

        # Determinar IND_GRP_BAL (A=Ativo, P=Passivo+PL) + natural fallback p/ saldo=0
        classe = _classe_da_conta(conta)
        if classe == 'asset':
            ind_grp = IND_GRP_BAL_ATIVO
            ind_dc_natural = 'D'
        else:
            ind_grp = IND_GRP_BAL_PASSIVO
            ind_dc_natural = 'C'

        # IND_COD_AGL: T se sintetica, D se analitica
        ind_cod_agl = IND_COD_AGL_TOTAL if conta.get('tipo') == 'S' else IND_COD_AGL_DETALHE

        # V23 (CAT 23): IND_DC pelo SINAL do balance (consistente com I155 fix CAT 3 V22).
        # V24 (2026-05-16) fix: quando saldo == 0, usar natureza (D para Ativo, C para
        # Passivo/PL). PVA rejeita IND_DC vazio em J100 ("Campo obrigatorio nao preenchido"
        # IND_DC_BAL_I/F) — 35 erros V23 vieram de contas com saldo inicial 0 ou final 0.
        # Antes V22 a logica antiga (natural com inversao) sempre retornava D ou C,
        # protegendo implicitamente esse caso.
        def _ind_dc_v24(saldo, natural):
            if saldo > 0:
                return 'D'
            if saldo < 0:
                return 'C'
            return natural

        ind_dc_ini = _ind_dc_v24(s['saldo_inicial'], ind_dc_natural)
        ind_dc_fin = _ind_dc_v24(s['saldo_final'], ind_dc_natural)

        # V35 (CAT 12 — 2026-05-24): redirect cod_sup p/ compensacao colocar
        # como filha de 115 ESTOQUES (dentro do Ativo), eliminando 3a raiz
        # IND_GRP_BAL=A. Alinha com contadora.
        cod_sup_j100 = CODES_J100_COD_AGL_SUP_REDIRECT.get(code) or conta.get('cod_sup', '')

        linhas.append(contador.emit(formatar_registro([
            'J100',                                            # 1 REG
            code,                                              # 2 COD_AGL (codigo do plano)
            ind_cod_agl,                                       # 3 IND_COD_AGL (T/D)
            str(conta.get('nivel', 1)),                        # 4 NIVEL_AGL
            cod_sup_j100,                                      # 5 COD_AGL_SUP (V35: redirect 510101->115)
            ind_grp,                                           # 6 IND_GRP_BAL
            remover_acentos(conta.get('name', '')),            # 7 DESCR_COD_AGL
            formatar_valor(abs(s['saldo_inicial'])),           # 8 VL_CTA_INI (V1.6: REAL)
            ind_dc_ini,                                        # 9 IND_DC_CTA_INI
            formatar_valor(abs(s['saldo_final'])),             # 10 VL_CTA_FIN
            ind_dc_fin,                                        # 11 IND_DC_CTA_FIN
            '',                                                # 12 NOTA_EXP_REF
        ])))

    return linhas


# V35 (CAT 36 — 2026-05-24): Mapeamento account_type Odoo -> COD_AGL detalhe DRE.
# Estrutura J150 reconfigurada conforme tabela enviada pela contadora Tamiris
# (sessao web user_id=44 em 2026-05-18, ground truth alinhado com SPED 2S 2024).
#
# Tabela da contadora tem 18 linhas, 5 niveis (1,3,4,5 — pula nivel 2), estrutura:
#   9 RESULTADOS -> 9.3 RESULTADO -> 9.3.1 RESULTADO OPERACIONAL
#                                  -> 9.3.1.1 RES OP BRUTO      (income)
#                                  -> 9.3.1.2 DEVOLUCOES        (sem account_type)
#                                  -> 9.3.1.3 CMV               (expense_direct_cost)
#                -> 9.4 DESPESAS OPERACIONAIS -> 9.4.2 DESP ADM/COM
#                                              -> 9.4.2.1 DESP ADM (expense + expense_depreciation*)
#                                              -> 9.4.2.2 DESP COM (sem account_type)
#                -> 9.5 RESULTADO FINANCEIRO -> 9.5.1.1 REC FIN (sem)
#                                            -> 9.5.2.1 DESP ADM (sem)
#                                            -> 9.5.3.1 OUTRAS REC OP (income_other)
#                                            -> 9.5.3.2 OUTRAS DESP FIN (sem)
#
# Mapeamento confirmado pela Tamiris (sessao 613):
#   - expense_depreciation -> 9.4.2.1 (Despesas Administrativas)
#
# PENDENCIAS aguardando resposta da Tamiris:
#   - Linha 4 (9.3.1.1): tipo D (Detalhe) conforme tabela; manter assim
#   - Linha 7 (9.4): valor 16117672 era cola acidental; sera calculado dos saldos
#   - Codes detalhe sem account_type Odoo (9.3.1.2 devolucoes, 9.4.2.2 comerciais,
#     9.5.1.1 rec fin, 9.5.2.1 desp adm, 9.5.3.2 outras desp fin) terao valor 0
#     e serao SKIPPED pelo filtro `if abs(valor) < 0.01 and nivel != 1`. PVA deve
#     aceitar so as linhas com valor.
DRE_ACCOUNT_TYPE_TO_COD_AGL = {
    'income':              '9.3.1.1',  # RECEITA OPERACIONAL BRUTA
    'income_other':        '9.5.3.1',  # OUTRAS RECEITAS OPERACIONAIS
    'expense_direct_cost': '9.3.1.3',  # CUSTOS DOS PRODUTOS E MERCADORIAS VENDIDAS
    'expense':             '9.4.2.1',  # DESPESAS ADMINISTRATIVAS
    'expense_depreciation':'9.4.2.1',  # DESPESAS ADMINISTRATIVAS (confirmado Tamiris 2026-05-18)
}


def _calcular_grupos_dre_hierarquicos(dre_consolidado: dict):
    """
    V35 (CAT 36 fix 2026-05-24): calcula grupos DRE conforme estrutura da contadora.

    Estrutura (18 grupos, 5 niveis — pula nivel 2):

        9         T  1   -      RESULTADOS                       (raiz unica)
        9.3       T  3   9      RESULTADO
        9.3.1     T  4   9.3    RESULTADO OPERACIONAL
        9.3.1.1   D  5   9.3.1  RESULTADO OPERACIONAL BRUTO     <- income
        9.3.1.2   D  5   9.3.1  DEVOLUCOES DE VENDAS            (sem account_type)
        9.3.1.3   D  5   9.3.1  CMV                              <- expense_direct_cost
        9.4       T  3   9      DESPESAS OPERACIONAIS
        9.4.2     T  4   9.4    DESPESAS ADM E COMERCIAIS
        9.4.2.1   D  5   9.4.2  DESPESAS ADMINISTRATIVAS        <- expense + expense_depreciation
        9.4.2.2   D  5   9.4.2  DESPESAS COMERCIAIS              (sem account_type)
        9.5       T  3   9      RESULTADO FINANCEIRO
        9.5.1     T  4   9.5    RECEITAS FINANCEIRAS
        9.5.1.1   D  5   9.5.1  RECEITAS FINANCEIRAS             (sem)
        9.5.2     T  4   9.5    DESPESAS OPERACIONAIS
        9.5.2.1   D  5   9.5.2  DESPESAS ADMINISTRATIVAS         (sem)
        9.5.3     T  4   9.5    RECEITAS OPERACIONAIS
        9.5.3.1   D  5   9.5.3  OUTRAS RECEITAS OPERACIONAIS    <- income_other
        9.5.3.2   D  5   9.5.3  OUTRAS DESPESAS FINANCEIRAS      (sem)

    Soma com sinal: nivel 1 = receita - despesa = resultado_liquido.

    Returns:
        (grupos, mapa_i052):
            grupos: List[Tuple[cod_agl, descr, valor, ind_dc, ind_grp_dre, nivel, cod_sup, is_total]]
            mapa_i052: Dict[code_conta_analitica, cod_agl_detalhe_dre]
    """
    # Agrupamentos por account_type (somente os COM mapping Odoo)
    receita_op_bruta = sum(
        abs(s['saldo']) for s in dre_consolidado.values()
        if s.get('account_type') == 'income'
    )
    receita_outras_op = sum(
        abs(s['saldo']) for s in dre_consolidado.values()
        if s.get('account_type') == 'income_other'
    )
    cmv = sum(
        abs(s['saldo']) for s in dre_consolidado.values()
        if s.get('account_type') == 'expense_direct_cost'
    )
    despesa_adm = sum(
        abs(s['saldo']) for s in dre_consolidado.values()
        if s.get('account_type') in ('expense', 'expense_depreciation')
    )

    # Grupos sem account_type Odoo dedicado — ficam com 0 e sao puladas (skip valor < 0.01)
    devolucoes = 0.0
    despesa_comercial = 0.0
    receita_financeira = 0.0
    despesa_adm_fin = 0.0
    outras_despesas_fin = 0.0

    # Totalizadores (somam filhas com sinal)
    # 9.3.1 = RES OP BRUTO - DEVOLUCOES - CMV
    nivel_9_3_1 = receita_op_bruta - devolucoes - cmv
    nivel_9_3 = nivel_9_3_1
    # 9.4.2 = DESP ADM + DESP COM (ambos D)
    nivel_9_4_2 = despesa_adm + despesa_comercial
    nivel_9_4 = nivel_9_4_2
    # 9.5.1 = REC FIN (so receita)
    nivel_9_5_1 = receita_financeira
    # 9.5.2 = DESP ADM FIN
    nivel_9_5_2 = despesa_adm_fin
    # 9.5.3 = OUTRAS REC OP - OUTRAS DESP FIN
    nivel_9_5_3 = receita_outras_op - outras_despesas_fin
    # 9.5 = REC FIN - DESP ADM FIN + OUTRAS REC OP - OUTRAS DESP FIN
    nivel_9_5 = nivel_9_5_1 - nivel_9_5_2 + nivel_9_5_3
    # 9 = 9.3 - 9.4 + 9.5
    resultado_liquido = nivel_9_3 - nivel_9_4 + nivel_9_5

    # Helper para sinal IND_DC + IND_GRP_DRE
    def _sinal(valor, default_credor=True):
        """Retorna (ind_dc, ind_grp_dre) baseado no sinal e na natureza esperada."""
        if valor >= 0:
            return ('C', 'R') if default_credor else ('D', 'D')
        return ('D', 'D') if default_credor else ('C', 'R')

    # (cod_agl, descr, valor, ind_dc, ind_grp_dre, nivel, cod_sup, is_total)
    grupos = [
        # Nivel 1 (T) — raiz unica, resultado liquido
        ('9', 'RESULTADOS',
         abs(resultado_liquido),
         'C' if resultado_liquido >= 0 else 'D',
         'R' if resultado_liquido >= 0 else 'D',
         1, '', True),

        # === 9.3 RESULTADO (T nivel 3) ===
        ('9.3', 'RESULTADO',
         abs(nivel_9_3),
         'C' if nivel_9_3 >= 0 else 'D',
         'R' if nivel_9_3 >= 0 else 'D',
         3, '9', True),
        ('9.3.1', 'RESULTADO OPERACIONAL',
         abs(nivel_9_3_1),
         'C' if nivel_9_3_1 >= 0 else 'D',
         'R' if nivel_9_3_1 >= 0 else 'D',
         4, '9.3', True),
        ('9.3.1.1', 'RESULTADO OPERACIONAL BRUTO', receita_op_bruta, 'C', 'R', 5, '9.3.1', False),
        ('9.3.1.2', 'DEVOLUCOES DE VENDAS', devolucoes, 'D', 'D', 5, '9.3.1', False),
        ('9.3.1.3', 'CUSTOS DOS PRODUTOS E MERCADORIAS VENDIDAS', cmv, 'D', 'D', 5, '9.3.1', False),

        # === 9.4 DESPESAS OPERACIONAIS (T nivel 3) ===
        ('9.4', 'DESPESAS OPERACIONAIS', nivel_9_4, 'D', 'D', 3, '9', True),
        ('9.4.2', 'DESPESAS ADMINISTRATIVAS E COMERCIAIS', nivel_9_4_2, 'D', 'D', 4, '9.4', True),
        ('9.4.2.1', 'DESPESAS ADMINISTRATIVAS', despesa_adm, 'D', 'D', 5, '9.4.2', False),
        ('9.4.2.2', 'DESPESAS COMERCIAIS', despesa_comercial, 'D', 'D', 5, '9.4.2', False),

        # === 9.5 RESULTADO FINANCEIRO (T nivel 3) ===
        ('9.5', 'RESULTADO FINANCEIRO',
         abs(nivel_9_5),
         'C' if nivel_9_5 >= 0 else 'D',
         'R' if nivel_9_5 >= 0 else 'D',
         3, '9', True),
        ('9.5.1', 'RECEITAS FINANCEIRAS', nivel_9_5_1, 'C', 'R', 4, '9.5', True),
        ('9.5.1.1', 'RECEITAS FINANCEIRAS', receita_financeira, 'C', 'R', 5, '9.5.1', False),
        ('9.5.2', 'DESPESAS OPERACIONAIS', nivel_9_5_2, 'D', 'D', 4, '9.5', True),
        ('9.5.2.1', 'DESPESAS ADMINISTRATIVAS', despesa_adm_fin, 'D', 'D', 5, '9.5.2', False),
        ('9.5.3', 'RECEITAS OPERACIONAIS',
         abs(nivel_9_5_3),
         'C' if nivel_9_5_3 >= 0 else 'D',
         'R' if nivel_9_5_3 >= 0 else 'D',
         4, '9.5', True),
        ('9.5.3.1', 'OUTRAS RECEITAS OPERACIONAIS', receita_outras_op, 'C', 'R', 5, '9.5.3', False),
        ('9.5.3.2', 'OUTRAS DESPESAS FINANCEIRAS', outras_despesas_fin, 'D', 'D', 5, '9.5.3', False),
    ]

    # Mapa I052: cada conta analitica de resultado -> COD_AGL detalhe DRE
    mapa_i052 = {
        code: DRE_ACCOUNT_TYPE_TO_COD_AGL[s.get('account_type')]
        for code, s in dre_consolidado.items()
        if s.get('account_type') in DRE_ACCOUNT_TYPE_TO_COD_AGL
    }

    return grupos, mapa_i052


def construir_J005_J150(dre_consolidado: dict, params: dict,
                         contador: ContadorRegistros) -> List[str]:
    """
    DRE: J005 (cabecalho DRE) + J150 (linhas).

    V28 (CAT 5/20 fix 2026-05-16): hierarquia explicita 3 niveis com COD_AGL_SUP
    populado. 1 raiz nivel 1 ('9' RESULTADO DO EXERCICIO). Codes detalhe (D) sao
    vinculados via I052 em `construir_I050_com_I051` (parametro `mapa_aglutinacao_dre`).

    Bug historico V27 e anteriores:
    - 2 linhas NIVEL_AGL=1 (PVA reclama "Nao deve existir mais de uma linha nivel 1")
    - COD_AGL_SUP vazio em TODAS as linhas (PVA reclama "Nao existe registro
      com cod_agl=cod_agl_sup", "So totalizadora pode ser sup")
    - is_total via string match BUGADO: `'TOTAL' in 'CUSTOS E DESPESAS TOTAIS'`
      retorna False (substring 'TOTAL' nao bate em 'TOTAIS')
    - Codes detalhe sem I052 (PVA reclama "code detalhe deve estar em pelo menos
      1 I052")

    Layout J150 13 campos (Manual ECD Leiaute 9):
        REG | NU_ORDEM | COD_AGL | IND_COD_AGL | NIVEL_AGL | COD_AGL_SUP |
        DESCR_COD_AGL | VL_CTA_INI | IND_DC_CTA_INI | VL_CTA_FIN |
        IND_DC_CTA_FIN | IND_GRP_DRE | NOTA_EXP_REF

    dre_consolidado: dict {code: {'saldo': X, 'account_type': Y, 'name': Z}}
    """
    linhas = []

    # V29 (2026-05-16): J005 NAO mais emitido aqui. Emitido em service.py via
    # construir_J005_unico (1 J005 ID_DEM=1 cobre BP+DRE — padrao contadora aceito RFB).

    grupos, _mapa = _calcular_grupos_dre_hierarquicos(dre_consolidado)

    nu_ordem = 1
    for cod_agl, descr, valor, ind_dc, ind_grp_dre, nivel, cod_sup, is_total in grupos:
        # Skip grupos com valor zero (mas SEMPRE emitir raiz nivel 1 mesmo zerada
        # para PVA validar estrutura: "deve existir linha nivel 1")
        if abs(valor) < 0.01 and nivel != 1:
            continue
        linhas.append(contador.emit(formatar_registro([
            'J150',                                            # 1  REG
            str(nu_ordem),                                     # 2  NU_ORDEM (numero!)
            cod_agl,                                           # 3  COD_AGL
            IND_COD_AGL_TOTAL if is_total else IND_COD_AGL_DETALHE,  # 4 IND_COD_AGL (T/D)
            str(nivel),                                        # 5  NIVEL_AGL
            cod_sup,                                           # 6  COD_AGL_SUP (V28: hierarquia explicita)
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
        CONTADOR_CRC,                                          # 6 IND_CRC (SP-1303041/O-9)
        CONTADOR_EMAIL,                                        # 7 EMAIL (fixo)
        CONTADOR_FONE,                                         # 8 FONE (V1.9: 1147059494 — obrigatorio para COD_ASSIN=900)
        CONTADOR_UF_CRC,                                       # 9 UF_CRC (SP)
        CONTADOR_NUM_SEQ_CRC,                                  # 10 NUM_SEQ_CRC (SP/2026/041472 COMPLETO)
        CONTADOR_DT_CRC,                                       # 11 DT_CRC (V1.9: 06072026 — obrigatorio para COD_ASSIN=900)
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
