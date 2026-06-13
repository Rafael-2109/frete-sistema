"""
Service de conversao de extrato bancario SRM Bank (PDF) para OFX.

PROBLEMA QUE RESOLVE
--------------------
Extratos do SRM Bank (Banco 533) vem em PDF e NAO possuem FITID (identificador
unico de transacao do padrao OFX). Sem FITID, o importador nativo do Odoo nao
consegue deduplicar transacoes. Este service reconstroi um FITID *sintetico
deterministico* a partir de (Data, Hora, Sinal, Valor, Saldo-apos), gerando um
arquivo OFX que o importador nativo do Odoo consome com dedup garantido pela
constraint UNIQUE de `account.bank.statement.line.unique_import_id`.

GARANTIA DE CONSISTENCIA (por que da pra confiar no parse)
---------------------------------------------------------
1. SINAL pela COLUNA, nao pela cadeia. O sinal (credito/debito) e' lido pela
   coordenada X do valor no PDF (coluna Credito x0~=366, Debito x0~=432, Saldo
   x1~=549). Isso e' imune ao agrupamento "ENVIO DE TED + TARIFA" que o banco
   faz, que quebra a ordem cronologica estrita dentro do dia.
2. SALDO como CHECKSUM. A linha "SALDO" de cada dia (saldo_dia) e' a fonte de
   verdade do fechamento; a validacao POR DIA encadeia saldo_dia[D-1] ->
   saldo_dia[D] conferindo a soma das transacoes do dia, com tolerancia TOL_DIA
   (R$ 0,05) para o ruido de arredondamento interno do SRM. Acima da tolerancia
   o arquivo e' REJEITADO inteiro (nunca converte parse parcial).

FITID SINTETICO (deterministico e estavel entre PDFs)
-----------------------------------------------------
    {YYYYMMDD}{HHMMSS|000000}-{C|D}{valor_centavos}-S{[-]saldo_centavos}-{occ}
- Depende apenas de atributos da propria transacao -> estavel se o mesmo
  lancamento aparecer em PDFs de periodos sobrepostos.
- `occ` = indice de ocorrencia para tuplas identicas no mesmo dia (cobre o caso
  teorico de par +X/-X/+X). Nos 4 extratos reais, occ e' sempre 0.

CONSUMIDORES
------------
- CLI: `app/financeiro/scripts/importar_extrato_pdf_srm.py` (--check / --ofx)
- Web: `app/financeiro/routes/conversor_extrato_srm.py` (upload -> download OFX)

O OFX gerado e' importado pela tela nativa do Odoo (Conciliacao Bancaria ->
Importar Extrato) no journal cujo bank_account_id casa com a conta do PDF
(ex.: journal 1055 "SRM GARANTIDA", conta 0000142844).
"""
import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

import pdfplumber

# ---------------------------------------------------------------------------
# Constantes de layout do PDF SRM Bank (coordenadas validadas nos 4 extratos)
# ---------------------------------------------------------------------------
# Limites de x0 para classificar a coluna de cada valor numerico.
X_CREDITO_MAX = 410.0   # coluna Credito: x0 ~= 366
X_DEBITO_MAX = 490.0    # coluna Debito:  x0 ~= 432
# acima de X_DEBITO_MAX -> coluna Saldo (x0 ~= 506-523, x1 ~= 549.6)

# O SRM arredonda o saldo para 2 casas na exibicao; a soma das transacoes de um
# dia pode divergir do saldo de fechamento em ate ~1 centavo (ruido interno do
# banco). TOL_DIA absorve esse ruido sem mascarar transacao faltando (a menor
# transacao real e' de varios reais).
TOL_DIA = Decimal('0.05')

# Valor monetario com sinal opcional (saldo pode ser negativo: '-0,00').
RE_VALOR = re.compile(r'^-?\d{1,3}(?:\.\d{3})*,\d{2}$')
RE_DATA = re.compile(r'^\d{2}/\d{2}/\d{4}$')
RE_HORA = re.compile(r'^\d{2}:\d{2}:\d{2}$')
RE_CONTA = re.compile(r'Conta:\s*(\d+)')
RE_AGENCIA = re.compile(r'Ag[eê]ncia:\s*(\d+)')
RE_BANCO = re.compile(r'Banco:\s*(\d+)')
RE_PERIODO = re.compile(r'Per[ií]odo:\s*(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})')


def _dec(texto):
    """'1.861,69' -> Decimal('1861.69')"""
    return Decimal(texto.replace('.', '').replace(',', '.'))


def _centavos(valor):
    """Decimal('1861.69') -> '186169' (string de centavos, sem sinal)."""
    q = (valor.copy_abs() * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return str(int(q))


class Transacao:
    __slots__ = ('data', 'hora', 'tipo', 'valor', 'saldo', 'descricao', 'cod', '_occ')

    def __init__(self, data, tipo, valor, saldo, descricao):
        self.data = data          # 'DD/MM/YYYY'
        self.hora = None          # 'HH:MM:SS' ou None
        self.tipo = tipo          # 'C' ou 'D'
        self.valor = valor        # Decimal positivo
        self.saldo = saldo        # Decimal (saldo apos a transacao)
        self.descricao = descricao
        self.cod = None
        self._occ = 0

    @property
    def signed(self):
        return self.valor if self.tipo == 'C' else -self.valor

    @property
    def data_iso(self):
        d, m, a = self.data.split('/')
        return f'{a}{m}{d}'

    def fitid(self):
        hora = (self.hora or '000000').replace(':', '')
        sinal_saldo = '-' if self.saldo < 0 else ''
        return (f'{self.data_iso}{hora}-{self.tipo}{_centavos(self.valor)}'
                f'-S{sinal_saldo}{_centavos(self.saldo)}-{self._occ}')


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def _classificar(token):
    """Retorna ('C'|'D'|'S', Decimal) se o token e' um valor monetario, senao None."""
    if not RE_VALOR.match(token['text']):
        return None
    x0 = token['x0']
    if x0 < X_CREDITO_MAX:
        col = 'C'
    elif x0 < X_DEBITO_MAX:
        col = 'D'
    else:
        col = 'S'
    return col, _dec(token['text'])


def _agrupar_linhas(words, tol=2.5):
    """Agrupa words por linha visual (mesmo 'top' com tolerancia)."""
    linhas = defaultdict(list)
    for w in words:
        linhas[round(w['top'] / tol)].append(w)
    for chave in sorted(linhas):
        yield sorted(linhas[chave], key=lambda x: x['x0'])


def parse_pdf(fonte, nome=None):
    """
    Parseia o extrato e retorna dict:
        {nome, conta, agencia, banco, periodo_ini, periodo_fim, saldo_anterior,
         transacoes: [Transacao], saldo_dia: {data: Decimal}}

    `fonte` pode ser um caminho (str) OU um file-like binario (ex.: stream de
    upload Flask / BytesIO) — pdfplumber.open aceita ambos, evitando gravar em
    disco no fluxo web. `nome` rotula o extrato nas mensagens de erro/relatorio.
    """
    rotulo = nome or (fonte if isinstance(fonte, str) else 'extrato')
    meta = {'nome': rotulo, 'conta': None, 'agencia': None, 'banco': None,
            'periodo_ini': None, 'periodo_fim': None, 'saldo_anterior': None}
    transacoes = []
    saldo_dia = {}      # data -> saldo de fechamento do dia (linha SALDO, fonte de verdade)
    data_corrente = None

    with pdfplumber.open(fonte) as pdf:
        # Cabecalho (texto plano da pagina 1)
        cab = pdf.pages[0].extract_text() or ''
        for regex, chave in ((RE_CONTA, 'conta'), (RE_AGENCIA, 'agencia'),
                             (RE_BANCO, 'banco')):
            m = regex.search(cab)
            if m:
                meta[chave] = m.group(1)
        mper = RE_PERIODO.search(cab)
        if mper:
            meta['periodo_ini'], meta['periodo_fim'] = mper.group(1), mper.group(2)

        for page in pdf.pages:
            for ws in _agrupar_linhas(page.extract_words()):
                primeiro = ws[0]['text']
                texto = ' '.join(w['text'] for w in ws)

                # Ignorar cabecalho/rodape
                if texto.startswith(('Extrato da conta', 'Emitido em', 'NACOM GOYA',
                                     'Banco:', 'Agência:', 'Conta:', 'Período:',
                                     'Movimentações', 'Data Lançamento', 'R$',
                                     'Os dados acima', 'Conforme Res')):
                    continue
                if 'Ouvidoria' in texto:
                    continue

                # SALDO ANTERIOR (saldo de abertura do arquivo)
                if texto.startswith('SALDO ANTERIOR'):
                    vals = [c for c in (_classificar(w) for w in ws) if c]
                    if vals:
                        meta['saldo_anterior'] = vals[-1][1]
                    continue

                tem_data = RE_DATA.match(primeiro) and ws[0]['x0'] < 90
                tem_hora = RE_HORA.match(primeiro)

                # Linha "DD/MM/YYYY SALDO <valor>"
                if tem_data and 'SALDO' in texto:
                    data_corrente = primeiro
                    vals = [c for c in (_classificar(w) for w in ws) if c]
                    if vals:
                        saldo_dia[data_corrente] = vals[-1][1]
                    continue

                # Linha de hora -> metadado da transacao anterior
                if tem_hora:
                    if transacoes:
                        transacoes[-1].hora = primeiro
                    continue

                cols = [c for c in (_classificar(w) for w in ws) if c]
                valor_mov = [c for c in cols if c[0] in ('C', 'D')]
                valor_saldo = [c for c in cols if c[0] == 'S']

                # Linha de transacao: tem 1 valor de movimento + 1 saldo
                if valor_mov and valor_saldo:
                    tipo = valor_mov[0][0]
                    valor = valor_mov[0][1].copy_abs()  # sinal vem da coluna
                    saldo = valor_saldo[-1][1]           # saldo pode ser negativo
                    if tem_data:
                        data_corrente = primeiro
                    if data_corrente is None:
                        raise ValueError(
                            f'{rotulo}: transacao sem data de contexto: {texto!r}')
                    # descricao = tokens nao numericos, sem data
                    desc_tokens = [w['text'] for w in ws
                                   if not RE_VALOR.match(w['text'])
                                   and not RE_DATA.match(w['text'])]
                    transacoes.append(Transacao(data_corrente, tipo, valor, saldo,
                                                ' '.join(desc_tokens).strip()))
                    continue

                # Linha 'COD.: xxxx' -> anexa ref a transacao anterior
                if texto.startswith('COD.') and transacoes:
                    transacoes[-1].cod = texto.split(':', 1)[-1].strip()
                    continue

                # Demais linhas = continuacao de descricao
                if transacoes and not cols:
                    transacoes[-1].descricao = (
                        f'{transacoes[-1].descricao} {texto}').strip()

    # Calcular occ deterministico (tuplas identicas no mesmo dia)
    vistos = defaultdict(int)
    for t in transacoes:
        chave = (t.data, t.hora, t.tipo, t.valor, t.saldo)
        t._occ = vistos[chave]
        vistos[chave] += 1

    meta['transacoes'] = transacoes
    meta['saldo_dia'] = saldo_dia
    return meta


# ---------------------------------------------------------------------------
# Validacao
# ---------------------------------------------------------------------------
def _dias_ordenados(datas):
    def chave(d):
        dd, mm, aa = d.split('/')
        return (aa, mm, dd)
    return sorted(datas, key=chave)


def saldo_fechamento(parsed):
    """Saldo de fechamento do extrato = linha SALDO do dia mais recente."""
    dias = _dias_ordenados(parsed['saldo_dia'].keys())
    return parsed['saldo_dia'][dias[-1]] if dias else None


def validar(parsed):
    """
    Retorna (ok: bool, erros: [str], warnings: [str], resumo: dict).

    Fonte de verdade do saldo de fechamento de cada dia = linha "SALDO" do PDF
    (saldo_dia), nao o saldo da transacao que carrega a data: o SRM agrupa
    "ENVIO DE TED + TARIFA" colocando a data na linha do ENVIO, mas a TARIFA
    (mais recente) e' quem fecha o dia.

    Validacao POR DIA (fatal acima de TOL_DIA) encadeia saldo_dia[D-1] ->
    saldo_dia[D] conferindo a soma das transacoes do dia. Pela identidade
    telescopica, a soma dos diffs diarios == diff global, entao a checagem
    global e' informativa (drift de arredondamento do banco).
    """
    erros, warnings = [], []
    transacoes = parsed['transacoes']
    saldo_ant = parsed['saldo_anterior']
    saldo_dia = parsed['saldo_dia']

    creditos = sum((t.valor for t in transacoes if t.tipo == 'C'), Decimal('0'))
    debitos = sum((t.valor for t in transacoes if t.tipo == 'D'), Decimal('0'))

    if saldo_ant is None:
        erros.append('SALDO ANTERIOR nao encontrado no PDF.')
        saldo_ant = Decimal('0')
    if not transacoes:
        erros.append('Nenhuma transacao parseada.')
        return False, erros, warnings, {}
    if not saldo_dia:
        erros.append('Nenhuma linha "SALDO" de dia encontrada.')
        return False, erros, warnings, {}

    # Toda transacao tem de pertencer a um dia com linha SALDO
    dias_trans = {t.data for t in transacoes}
    orfaos = dias_trans - set(saldo_dia)
    if orfaos:
        erros.append(f'Transacoes em dias sem linha SALDO: {sorted(orfaos)}')

    por_dia = defaultdict(lambda: {'C': Decimal('0'), 'D': Decimal('0')})
    for t in transacoes:
        por_dia[t.data][t.tipo] += t.valor

    # VALIDACAO POR DIA (base = todos os dias com linha SALDO, em ordem cronologica)
    dias = _dias_ordenados(saldo_dia.keys())
    abertura = saldo_ant
    for d in dias:
        esperado = abertura + por_dia[d]['C'] - por_dia[d]['D']
        fechamento = saldo_dia[d]
        diff = fechamento - esperado
        if abs(diff) > TOL_DIA:
            erros.append(
                f'Dia {d}: cadeia diaria nao fecha. abertura({abertura}) + '
                f'C({por_dia[d]["C"]}) - D({por_dia[d]["D"]}) = {esperado} != '
                f'SALDO({fechamento}). Diferenca: {diff} '
                f'(acima da tolerancia {TOL_DIA} -> transacao faltando/errada).')
        elif diff:
            warnings.append(
                f'Dia {d}: SALDO({fechamento}) difere da soma das transacoes '
                f'({esperado}) em {diff} [arredondamento do banco - tolerado].')
        abertura = fechamento

    saldo_final = saldo_dia[dias[-1]]

    # CHECAGEM GLOBAL (informativa - drift acumulado de arredondamento)
    esperado_global = saldo_ant + creditos - debitos
    if (esperado_global != saldo_final
            and abs(esperado_global - saldo_final) > TOL_DIA * len(dias)):
        erros.append(
            f'Cadeia GLOBAL inconsistente: SALDO_ANTERIOR({saldo_ant}) + C'
            f'({creditos}) - D({debitos}) = {esperado_global} != saldo final '
            f'({saldo_final}). Diferenca {esperado_global - saldo_final} excede '
            f'drift esperado de arredondamento.')

    # Colisoes de FITID (devem ser 0)
    fitids = defaultdict(int)
    for t in transacoes:
        fitids[t.fitid()] += 1
    colisoes = {k: v for k, v in fitids.items() if v > 1}
    if colisoes:
        erros.append(f'FITIDs duplicados ({len(colisoes)}): '
                     f'{list(colisoes)[:3]}...')

    resumo = {
        'nome': parsed.get('nome'),
        'conta': parsed['conta'], 'banco': parsed['banco'],
        'periodo': f"{parsed['periodo_ini']} a {parsed['periodo_fim']}",
        'periodo_ini': parsed['periodo_ini'], 'periodo_fim': parsed['periodo_fim'],
        'n_transacoes': len(transacoes),
        'saldo_anterior': saldo_ant, 'saldo_final': saldo_final,
        'creditos': creditos, 'debitos': debitos,
        'com_hora': sum(1 for t in transacoes if t.hora),
        'sem_hora': sum(1 for t in transacoes if not t.hora),
    }
    return (not erros), erros, warnings, resumo


def analisar_continuidade(parseds):
    """
    Dada uma lista de extratos parseados (e validos), ordena por periodo inicial
    e compara, para cada par sequencial, o saldo de fechamento do anterior com o
    SALDO ANTERIOR do seguinte. Retorna lista de dicts:
        {de, para, fim, ini, continuo, gap}
    """
    def chave(p):
        ini = p.get('periodo_ini') or '01/01/0001'
        return tuple(reversed(ini.split('/')))

    ordenados = sorted(parseds, key=chave)
    resultado = []
    for pa, pb in zip(ordenados, ordenados[1:]):
        fim = saldo_fechamento(pa)
        ini = pb.get('saldo_anterior')
        gap = (ini - fim) if (fim is not None and ini is not None) else None
        resultado.append({
            'de': pa.get('nome'), 'para': pb.get('nome'),
            'fim': fim, 'ini': ini,
            'continuo': gap == 0, 'gap': gap,
        })
    return resultado


# ---------------------------------------------------------------------------
# Geracao de OFX (SGML 1.0.2 - consumido pelo importador nativo do Odoo)
# ---------------------------------------------------------------------------
def _sanitizar(texto, limite=255):
    texto = ' '.join(texto.split())
    texto = texto.replace('&', 'e').replace('<', '(').replace('>', ')')
    return texto[:limite]


def gerar_ofx(parsed):
    """Retorna o conteudo OFX (str) para o extrato parseado."""
    transacoes = parsed['transacoes']
    conta = parsed['conta']
    banco = parsed['banco']
    # ordem cronologica crescente (mais antiga primeiro)
    ordenadas = list(reversed(transacoes))
    dt_ini = ordenadas[0].data_iso
    dt_fim = ordenadas[-1].data_iso
    # saldo de fechamento = linha SALDO do dia mais recente (fonte de verdade)
    saldo_final = saldo_fechamento(parsed)

    linhas = []
    add = linhas.append
    add('OFXHEADER:100')
    add('DATA:OFXSGML')
    add('VERSION:102')
    add('SECURITY:NONE')
    add('ENCODING:USASCII')
    add('CHARSET:1252')
    add('COMPRESSION:NONE')
    add('OLDFILEUID:NONE')
    add('NEWFILEUID:NONE')
    add('')
    add('<OFX>')
    add('<SIGNONMSGSRSV1><SONRS><STATUS><CODE>0<SEVERITY>INFO</STATUS>')
    add(f'<DTSERVER>{dt_fim}120000<LANGUAGE>POR</SONRS></SIGNONMSGSRSV1>')
    add('<BANKMSGSRSV1><STMTTRNRS>')
    add('<TRNUID>1<STATUS><CODE>0<SEVERITY>INFO</STATUS>')
    add('<STMTRS><CURDEF>BRL')
    add(f'<BANKACCTFROM><BANKID>{banco}<ACCTID>{conta}'
        '<ACCTTYPE>CHECKING</BANKACCTFROM>')
    add(f'<BANKTRANLIST><DTSTART>{dt_ini}000000<DTEND>{dt_fim}235959')
    for t in ordenadas:
        trntype = 'CREDIT' if t.tipo == 'C' else 'DEBIT'
        memo = _sanitizar(t.descricao + (f' COD {t.cod}' if t.cod else ''))
        add('<STMTTRN>')
        add(f'<TRNTYPE>{trntype}')
        add(f'<DTPOSTED>{t.data_iso}120000')
        add(f'<TRNAMT>{t.signed}')
        add(f'<FITID>{t.fitid()}')
        add(f'<MEMO>{memo}')
        add('</STMTTRN>')
    add('</BANKTRANLIST>')
    add(f'<LEDGERBAL><BALAMT>{saldo_final}<DTASOF>{dt_fim}120000</LEDGERBAL>')
    add('</STMTRS></STMTTRNRS></BANKMSGSRSV1>')
    add('</OFX>')
    return '\n'.join(linhas)
