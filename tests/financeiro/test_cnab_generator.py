import pytest
from app.financeiro.services.remessa_vortx.cnab_generator import CnabVortxGenerator


class TestCnabVortxGenerator:

    def _boleto_exemplo(self):
        return {
            'nf_documento': '146774/002',
            'vencimento': '110526',
            'valor_centavos': '0000000508836',
            'emissao': '060426',
            'tipo_inscricao': '02',
            'cnpj_cpf': '53779178000149',
            'nome_sacado': 'P P ALIM E REPRESENTACOES LTDA EPP',
            'endereco': 'Q ASR NE 25, 212 NORTE, ALAMEDA CENTRAL,',
            'cep_prefixo': '77006',
            'cep_sufixo': '308',
            'email': 'pepalimentos07@gmail.com',
            'nosso_numero': '00000000001',
            'nosso_numero_dac': '9',
        }

    def _make_generator(self):
        return CnabVortxGenerator(data_geracao='150426', seq_remessa=1)

    def test_gera_arquivo_com_header_detalhe_trailer(self):
        gen = self._make_generator()
        gen.adicionar_boleto(self._boleto_exemplo())
        lines = gen.gerar()
        # header + detalhe + email + trailer = 4
        assert len(lines) == 4

    def test_todas_linhas_tem_400_chars(self):
        gen = self._make_generator()
        gen.adicionar_boleto(self._boleto_exemplo())
        lines = gen.gerar()
        for i, line in enumerate(lines):
            assert len(line) == 400, f'Linha {i} tem {len(line)} chars, esperado 400'

    def test_header_banco_310(self):
        gen = self._make_generator()
        gen.adicionar_boleto(self._boleto_exemplo())
        lines = gen.gerar()
        header = lines[0]
        assert header[76:79] == '310'

    def test_header_conta_grafeno(self):
        gen = self._make_generator()
        gen.adicionar_boleto(self._boleto_exemplo())
        lines = gen.gerar()
        header = lines[0]
        assert header[26:46] == '00000000000000109575'

    def test_detalhe_id_empresa(self):
        gen = self._make_generator()
        gen.adicionar_boleto(self._boleto_exemplo())
        lines = gen.gerar()
        detalhe = lines[1]
        assert detalhe[20:37] == '00210000101095757'

    def test_detalhe_nosso_numero_e_dac(self):
        gen = self._make_generator()
        gen.adicionar_boleto(self._boleto_exemplo())
        lines = gen.gerar()
        detalhe = lines[1]
        assert detalhe[70:81] == '00000000001'
        assert detalhe[81] == '9'

    def test_detalhe_valor(self):
        gen = self._make_generator()
        gen.adicionar_boleto(self._boleto_exemplo())
        lines = gen.gerar()
        detalhe = lines[1]
        assert detalhe[126:139] == '0000000508836'

    def test_trailer_tipo_9(self):
        gen = self._make_generator()
        gen.adicionar_boleto(self._boleto_exemplo())
        lines = gen.gerar()
        trailer = lines[-1]
        assert trailer[0] == '9'
        # rest (except seq at end) should be spaces
        assert trailer[1:394].strip() == ''

    def test_sequencial_correto(self):
        gen = self._make_generator()
        gen.adicionar_boleto(self._boleto_exemplo())
        lines = gen.gerar()
        for i, line in enumerate(lines):
            expected_seq = str(i + 1).zfill(6)
            assert line[394:400] == expected_seq, (
                f'Linha {i}: seq esperado {expected_seq}, got {line[394:400]}'
            )

    def test_sem_boleto_levanta_erro(self):
        gen = self._make_generator()
        with pytest.raises(ValueError):
            gen.gerar()

    def test_gerar_bytes_retorna_binario(self):
        gen = self._make_generator()
        gen.adicionar_boleto(self._boleto_exemplo())
        result = gen.gerar_bytes()
        assert isinstance(result, bytes)
        assert b'310' in result
        assert b'\r\n' in result

    def test_boleto_sem_email_gera_sem_registro_2(self):
        gen = self._make_generator()
        boleto = self._boleto_exemplo()
        boleto['email'] = ''
        gen.adicionar_boleto(boleto)
        lines = gen.gerar()
        # header + detalhe + trailer = 3 (no email line)
        assert len(lines) == 3
        assert lines[0][0] == '0'
        assert lines[1][0] == '1'
        assert lines[2][0] == '9'
