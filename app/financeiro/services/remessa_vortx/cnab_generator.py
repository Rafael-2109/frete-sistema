from app.financeiro.services.remessa_vortx.layout_vortx import (
    BANCO, BANCO_NOME, RAZAO_SOCIAL, CONVENIO, AGENCIA,
    CONTA_SEM_DV, CONTA_DV, CARTEIRA, SISTEMA_ID,
    CONTA_GRAFENO_HEADER, LINE_WIDTH, SEPARATOR,
    id_empresa_detalhe,
)


class CnabVortxGenerator:
    """Gerador de arquivo CNAB 400 para o banco VORTX (código 310)."""

    def __init__(self, data_geracao: str, seq_remessa: int = 1):
        self._data_geracao = data_geracao
        self._seq_remessa = seq_remessa
        self._boletos: list = []

    def adicionar_boleto(self, boleto: dict):
        self._boletos.append(boleto)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pad(self, value: str, width: int, fillchar: str = ' ', align: str = 'left') -> str:
        """Pad a string to exactly `width` chars, truncating if necessary."""
        value = str(value) if value is not None else ''
        if align == 'left':
            return value[:width].ljust(width, fillchar)
        else:
            return value[:width].rjust(width, fillchar)

    # ------------------------------------------------------------------
    # Line builders
    # ------------------------------------------------------------------

    def _montar_header(self, seq: int) -> str:
        line = [' '] * LINE_WIDTH

        # [0] = '0', [1] = '1', [2:9] = 'REMESSA', [9:11] = '01'
        line[0] = '0'
        line[1] = '1'
        line[2:9] = list('REMESSA')
        line[9:11] = list('01')

        # [11:26] = 'COBRANCA' ljust 15
        cobranca = 'COBRANCA'.ljust(15)
        line[11:26] = list(cobranca)

        # [26:46] = CONTA_GRAFENO_HEADER (20 chars)
        line[26:46] = list(CONTA_GRAFENO_HEADER)

        # [46:76] = RAZAO_SOCIAL ljust 30
        razao = RAZAO_SOCIAL[:30].ljust(30)
        line[46:76] = list(razao)

        # [76:79] = '310'
        line[76:79] = list(BANCO)

        # [79:94] = BANCO_NOME ljust 15
        banco_nome = BANCO_NOME[:15].ljust(15)
        line[79:94] = list(banco_nome)

        # [94:100] = data_geracao (6 chars)
        line[94:100] = list(self._data_geracao[:6])

        # [108:110] = 'MX'
        line[108:110] = list(SISTEMA_ID)

        # [110:117] = seq_remessa zfill 7
        line[110:117] = list(str(self._seq_remessa).zfill(7))

        # [394:400] = seq zfill 6
        line[394:400] = list(str(seq).zfill(6))

        return ''.join(line)

    def _montar_detalhe(self, boleto: dict, seq: int) -> str:
        line = [' '] * LINE_WIDTH

        # [0] = '1'
        line[0] = '1'

        # [1:20] = '00000 00000 0000000' (zeros+spaces, 19 chars)
        line[1:20] = list('00000 00000 0000000')

        # [20:37] = id_empresa_detalhe() (17 chars)
        line[20:37] = list(id_empresa_detalhe())

        # [37:62] = nosso_antigo ljust 25
        nosso_antigo = boleto.get('nosso_antigo', '')
        line[37:62] = list(nosso_antigo[:25].ljust(25))

        # [62:65] = '310'
        line[62:65] = list(BANCO)

        # [65] = '0' (multa flag)
        line[65] = '0'

        # [66:70] = '0000'
        line[66:70] = list('0000')

        # [70:81] = nosso_numero (11 digits)
        nosso_numero = boleto.get('nosso_numero', '').zfill(11)
        line[70:81] = list(nosso_numero[:11])

        # [81] = dac
        line[81] = str(boleto.get('nosso_numero_dac', '0'))

        # [82:92] = '0' * 10
        line[82:92] = list('0' * 10)

        # [92] = '0', [93] = ' '
        line[92] = '0'
        line[93] = ' '

        # [94:104] = ' ' * 10
        line[94:104] = list(' ' * 10)

        # [104] = '0', [105] = ' '
        line[104] = '0'
        line[105] = ' '

        # [106:108] = '01' (ocorrencia)
        line[106:108] = list('01')

        # [108:110] = '01' (instrucao)
        line[108:110] = list('01')

        # [110:120] = nf_documento ljust 10
        nf_doc = boleto.get('nf_documento', '')
        line[110:120] = list(nf_doc[:10].ljust(10))

        # [120:126] = vencimento DDMMAA
        vencimento = boleto.get('vencimento', '000000')
        line[120:126] = list(vencimento[:6])

        # [126:139] = valor_centavos zfill 13
        valor = boleto.get('valor_centavos', '0')
        line[126:139] = list(str(valor)[:13].zfill(13))

        # [139:142] = '000'
        line[139:142] = list('000')

        # [142:147] = '00000'
        line[142:147] = list('00000')

        # [147:149] = '01' (especie)
        line[147:149] = list('01')

        # [149] = 'N' (aceite)
        line[149] = 'N'

        # [150:156] = emissao
        emissao = boleto.get('emissao', '000000')
        line[150:156] = list(emissao[:6])

        # [156:160] = '0000'
        line[156:160] = list('0000')

        # [160:173] = '0' * 13 (mora)
        line[160:173] = list('0' * 13)

        # [173:179] = '000000'
        line[173:179] = list('000000')

        # [179:218] = zeros (desconto+IOF+abatimento, 3x13)
        line[179:218] = list('0' * 39)

        # [218:220] = tipo_inscricao
        tipo_inscricao = boleto.get('tipo_inscricao', '02')
        line[218:220] = list(tipo_inscricao[:2])

        # [220:234] = cnpj_cpf rjust 14 with '0'
        cnpj_cpf = boleto.get('cnpj_cpf', '').rjust(14, '0')
        line[220:234] = list(cnpj_cpf[:14])

        # [234:274] = nome_sacado ljust 40
        nome = boleto.get('nome_sacado', '')
        line[234:274] = list(nome[:40].ljust(40))

        # [274:314] = endereco ljust 40
        endereco = boleto.get('endereco', '')
        line[274:314] = list(endereco[:40].ljust(40))

        # [314:326] = ' ' * 12 (mensagem)
        line[314:326] = list(' ' * 12)

        # [326:331] = cep_prefixo
        cep_prefixo = boleto.get('cep_prefixo', '')
        line[326:331] = list(cep_prefixo[:5].ljust(5))

        # [331:334] = cep_sufixo
        cep_sufixo = boleto.get('cep_sufixo', '')
        line[331:334] = list(cep_sufixo[:3].ljust(3))

        # [334:394] = ' ' * 60 (sacador avalista)
        line[334:394] = list(' ' * 60)

        # [394:400] = seq zfill 6
        line[394:400] = list(str(seq).zfill(6))

        return ''.join(line)

    def _montar_email(self, email: str, seq: int) -> str:
        line = [' '] * LINE_WIDTH

        # [0] = '2'
        line[0] = '2'

        # [1:321] = email ljust 320
        email_padded = email[:320].ljust(320)
        line[1:321] = list(email_padded)

        # rest is spaces (already initialized)

        # [394:400] = seq zfill 6
        line[394:400] = list(str(seq).zfill(6))

        return ''.join(line)

    def _montar_trailer(self, seq: int) -> str:
        line = [' '] * LINE_WIDTH

        # [0] = '9'
        line[0] = '9'

        # rest spaces (already initialized)

        # [394:400] = seq zfill 6
        line[394:400] = list(str(seq).zfill(6))

        return ''.join(line)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def gerar(self) -> list:
        """Returns list of 400-char strings: header + (detalhe+email?) pairs + trailer."""
        if not self._boletos:
            raise ValueError('Nenhum boleto adicionado')

        lines = []
        seq = 1

        # Header
        lines.append(self._montar_header(seq))
        seq += 1

        # Detail + optional email for each boleto
        for boleto in self._boletos:
            lines.append(self._montar_detalhe(boleto, seq))
            seq += 1

            email = boleto.get('email', '').strip()
            if email:
                lines.append(self._montar_email(email, seq))
                seq += 1

        # Trailer
        lines.append(self._montar_trailer(seq))

        return lines

    def gerar_bytes(self) -> bytes:
        """Joins lines with CRLF and encodes as latin-1."""
        lines = self.gerar()
        content = SEPARATOR.join(lines) + SEPARATOR
        return content.encode('latin-1')
