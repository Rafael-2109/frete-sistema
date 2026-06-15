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

ESTRUTURA DE UM REGISTRO (e por que o FAVORECIDO precisa de look-ahead)
-----------------------------------------------------------------------
Cada registro ocupa ate 4 linhas visuais, NA ORDEM:
    1. TIPO        ex.: 'ENVIO DE TED' / 'RECEBIMENTO DE PIX QRCODE'
                   -> aparece INLINE na linha de valor OU em UMA linha de texto
                      IMEDIATAMENTE ACIMA dela.
    2. VALOR       '[DD/MM/YYYY] <valor> <saldo>' (ancora: 1 registro = 1 linha de valor)
    3. HORA+FAVOR. 'HH:MM:SS [cod_banco_3dig] FAVORECIDO ...' (TED/PIX/transf)
    4. DETALHES    continuacao do nome do favorecido e/ou identificadores
                   (E2E do PIX, hash interno) e/ou 'COD.: xxxx'.
Como o TIPO da linha 1 vem ACIMA do valor, a montagem usa look-ahead de 1 linha:
uma linha de texto cujo SUCESSOR e' um valor SEM tipo inline e' o tipo desse
proximo registro; caso contrario e' continuacao/detalhe do registro corrente.
O favorecido (linha 3 + continuacao textual) vai para o campo OFX <NAME> e
tambem para o <MEMO>; E2E/hash sao identificadores, nao favorecido.

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
# Tipo/favorecido/continuacao ficam na coluna de lancamento (x0 ~= 118). Linhas
# de texto fora dela (rodape de ouvidoria centralizado em x0 ~= 232, etc.) NAO
# sao detalhe de transacao e devem ser ignoradas na montagem.
X_DESCRICAO_MAX = 130.0

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

# Identificadores que aparecem nas linhas de detalhe e NAO sao favorecido:
# E2E do PIX ('E' + 31 alfanumericos) e hash interno do SRM (32 hexadecimais).
RE_E2E = re.compile(r'^E[0-9A-Za-z]{31}$')
RE_HASH = re.compile(r'^[0-9A-Fa-f]{32}$')
# Codigo de instituicao (3 digitos) que prefixa o favorecido na linha de hora.
RE_COD_BANCO = re.compile(r'^\d{3}$')


def _dec(texto):
    """'1.861,69' -> Decimal('1861.69')"""
    return Decimal(texto.replace('.', '').replace(',', '.'))


def _centavos(valor):
    """Decimal('1861.69') -> '186169' (string de centavos, sem sinal)."""
    q = (valor.copy_abs() * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return str(int(q))


def _eh_identificador(texto):
    """True se o texto e' um identificador de detalhe (E2E do PIX ou hash interno),
    nunca um nome de favorecido."""
    t = texto.strip()
    return bool(RE_E2E.match(t) or RE_HASH.match(t))


def _extrair_favorecido(tokens_apos_hora):
    """
    Da linha de hora 'HH:MM:SS [cod_banco] FAVORECIDO ...', recebe os tokens JA
    SEM a hora e retorna o nome do favorecido, descartando o codigo de instituicao
    de 3 digitos quando presente.
        ['756', 'NACOM', 'GOYA', 'COMERCIAL', 'LTDA'] -> 'NACOM GOYA COMERCIAL LTDA'
        ['FRANK', 'ROGERIO', 'HOMEM']                 -> 'FRANK ROGERIO HOMEM'
        []                                            -> ''
    """
    toks = list(tokens_apos_hora)
    if toks and RE_COD_BANCO.match(toks[0]):
        toks = toks[1:]
    return ' '.join(toks).strip()


class Transacao:
    __slots__ = ('data', 'hora', 'tipo', 'valor', 'saldo', 'descricao',
                 'favorecido', 'detalhes', 'cod', '_occ')

    def __init__(self, data, tipo, valor, saldo, descricao):
        self.data = data          # 'DD/MM/YYYY'
        self.hora = None          # 'HH:MM:SS' ou None
        self.tipo = tipo          # 'C' ou 'D'
        self.valor = valor        # Decimal positivo
        self.saldo = saldo        # Decimal (saldo apos a transacao)
        self.descricao = descricao  # tipo do lancamento (ex.: 'ENVIO DE TED')
        self.favorecido = None    # nome da contraparte (TED/PIX/transf), se houver
        self.detalhes = []        # identificadores extras (E2E do PIX, hash)
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


def _eh_valor_sem_tipo_inline(ws):
    """
    True se a linha visual `ws` e' uma linha de transacao (valor de movimento +
    saldo) que NAO carrega o tipo do lancamento inline. Usado como look-ahead:
    quando a proxima linha satisfaz isto, a linha de texto corrente e' o TIPO
    desse proximo registro (e nao continuacao do registro atual).
    """
    cols = [c for c in (_classificar(w) for w in ws) if c]
    valor_mov = [c for c in cols if c[0] in ('C', 'D')]
    valor_saldo = [c for c in cols if c[0] == 'S']
    if not (valor_mov and valor_saldo):
        return False
    inline = [w['text'] for w in ws
              if not RE_VALOR.match(w['text']) and not RE_DATA.match(w['text'])]
    return not inline


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

        # 1) Coletar as linhas de movimentacao (descartando cabecalho/rodape e
        #    extraindo o SALDO ANTERIOR), preservando a ordem de leitura. A
        #    montagem precisa olhar a PROXIMA linha (look-ahead), por isso a
        #    materializamos antes de iterar.
        linhas = []
        for page in pdf.pages:
            for ws in _agrupar_linhas(page.extract_words()):
                texto = ' '.join(w['text'] for w in ws)
                if texto.startswith(('Extrato da conta', 'Emitido em', 'NACOM GOYA',
                                     'Banco:', 'Agência:', 'Conta:', 'Período:',
                                     'Movimentações', 'Data Lançamento', 'R$',
                                     'Os dados acima', 'Conforme Res')):
                    continue
                # Rodape de ouvidoria: a linha "Conforme Res ... WhatsApp:" quebra e
                # continua em "(11) ...; E-mail: ...". Filtra ambas (continuacao por conteudo).
                if 'Ouvidoria' in texto or 'E-mail:' in texto:
                    continue
                if texto.startswith('SALDO ANTERIOR'):
                    vals = [c for c in (_classificar(w) for w in ws) if c]
                    if vals:
                        meta['saldo_anterior'] = vals[-1][1]
                    continue
                linhas.append(ws)

        # 2) Montar as transacoes. O TIPO do lancamento vem ACIMA da linha de
        #    valor (quando nao esta inline) e o FAVORECIDO vem ABAIXO (linha de
        #    hora + continuacao textual). Estado:
        tipo_pendente = None     # tipo de UMA linha que precede um valor sem tipo inline
        atual = None             # transacao corrente (recebe os detalhes ABAIXO do valor)
        coletando_fav = False    # acumulando a continuacao textual do nome do favorecido?

        for i, ws in enumerate(linhas):
            primeiro = ws[0]['text']
            texto = ' '.join(w['text'] for w in ws)
            cols = [c for c in (_classificar(w) for w in ws) if c]
            valor_mov = [c for c in cols if c[0] in ('C', 'D')]
            valor_saldo = [c for c in cols if c[0] == 'S']
            tem_data = bool(RE_DATA.match(primeiro)) and ws[0]['x0'] < 90
            tem_hora = bool(RE_HORA.match(primeiro))

            # Linha "DD/MM/YYYY SALDO <valor>" -> fecha o dia e reinicia o contexto
            if tem_data and 'SALDO' in texto and not valor_mov:
                data_corrente = primeiro
                if cols:
                    saldo_dia[data_corrente] = cols[-1][1]
                tipo_pendente = None
                atual = None
                coletando_fav = False
                continue

            # Linha de transacao: 1 valor de movimento + 1 saldo
            if valor_mov and valor_saldo:
                inline = ' '.join(
                    w['text'] for w in ws
                    if not RE_VALOR.match(w['text']) and not RE_DATA.match(w['text'])
                ).strip()
                tipo = inline or (tipo_pendente or '')
                tipo_pendente = None
                if tem_data:
                    data_corrente = primeiro
                if data_corrente is None:
                    raise ValueError(
                        f'{rotulo}: transacao sem data de contexto: {texto!r}')
                atual = Transacao(data_corrente,
                                  valor_mov[0][0],           # 'C'|'D' pela coluna
                                  valor_mov[0][1].copy_abs(),  # sinal vem da coluna
                                  valor_saldo[-1][1],          # saldo pode ser negativo
                                  tipo)
                transacoes.append(atual)
                coletando_fav = False
                continue

            # Linha de hora -> hora + favorecido da transacao corrente
            if tem_hora:
                if atual is not None:
                    atual.hora = primeiro
                    fav = _extrair_favorecido([w['text'] for w in ws[1:]])
                    if fav:
                        atual.favorecido = fav
                        coletando_fav = True
                continue

            # Linha 'COD.: xxxx' -> ref da transacao corrente
            if texto.startswith('COD.'):
                if atual is not None:
                    atual.cod = texto.split(':', 1)[-1].strip()
                continue

            # Linha sem valores: ou e' o TIPO do PROXIMO registro (quando a proxima
            # linha e' um valor sem tipo inline) ou e' continuacao/detalhe do atual.
            if not cols:
                # Texto fora da coluna de lancamento = rodape/ruido, nunca detalhe.
                if ws[0]['x0'] >= X_DESCRICAO_MAX:
                    continue
                prox = linhas[i + 1] if i + 1 < len(linhas) else None
                if prox is not None and _eh_valor_sem_tipo_inline(prox):
                    tipo_pendente = texto
                    coletando_fav = False
                    continue
                if atual is not None:
                    if _eh_identificador(texto):
                        atual.detalhes.append(texto.strip())
                        coletando_fav = False
                    elif coletando_fav:
                        atual.favorecido = f'{atual.favorecido} {texto}'.strip()
                    else:
                        atual.descricao = f'{atual.descricao} {texto}'.strip()

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
        # MEMO completo: tipo | favorecido | identificadores | COD
        partes = [t.descricao]
        if t.favorecido:
            partes.append(t.favorecido)
        partes.extend(t.detalhes)
        if t.cod:
            partes.append(f'COD {t.cod}')
        memo = _sanitizar(' | '.join(p for p in partes if p))
        add('<STMTTRN>')
        add(f'<TRNTYPE>{trntype}')
        add(f'<DTPOSTED>{t.data_iso}120000')
        add(f'<TRNAMT>{t.signed}')
        add(f'<FITID>{t.fitid()}')
        # <NAME> (A-32): nome da contraparte -> o Odoo usa para casar o parceiro.
        if t.favorecido:
            add(f'<NAME>{_sanitizar(t.favorecido, limite=32)}')
        add(f'<MEMO>{memo}')
        add('</STMTTRN>')
    add('</BANKTRANLIST>')
    add(f'<LEDGERBAL><BALAMT>{saldo_final}<DTASOF>{dt_fim}120000</LEDGERBAL>')
    add('</STMTRS></STMTTRNRS></BANKMSGSRSV1>')
    add('</OFX>')
    return '\n'.join(linhas)
