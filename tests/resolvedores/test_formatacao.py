"""TDD — formatadores de sugestao (puros, sem banco).

Port de resolver_entidades.py: formatar_sugestao_pedido (:1356), formatar_sugestao_produto (:1389).
A branch 'multiplos' de formatar_sugestao_pedido CORRIGE um bug latente do monolito
(', '.join sobre dicts -> TypeError): agora junta os num_pedido dos candidatos (decisao Rafael 2026-06-01).
"""
from app.resolvedores.formatacao import formatar_sugestao_pedido, formatar_sugestao_produto


class TestFormatarSugestaoPedido:
    def test_nao_encontrado_retorna_orientacao(self):
        info = {'estrategia': 'NAO_ENCONTRADO', 'termo_original': 'xyz'}
        msg = formatar_sugestao_pedido(info)
        assert msg is not None
        assert 'xyz' in msg
        assert 'nao encontrado' in msg.lower()

    def test_sucesso_simples_retorna_none(self):
        info = {'estrategia': 'NUMERO_EXATO', 'termo_original': 'VCD1', 'multiplos_encontrados': False}
        assert formatar_sugestao_pedido(info) is None

    def test_multiplos_lista_num_pedidos(self):
        # Correcao do bug: candidatos sao dicts; a msg deve conter os num_pedido (nao quebrar).
        info = {
            'estrategia': 'NUMERO_PARCIAL',
            'termo_original': '123',
            'multiplos_encontrados': True,
            'pedidos_candidatos': [
                {'num_pedido': 'VCD123', 'cliente': 'A'},
                {'num_pedido': 'VCD124', 'cliente': 'B'},
            ],
        }
        msg = formatar_sugestao_pedido(info)
        assert msg is not None
        assert 'VCD123' in msg and 'VCD124' in msg

    def test_multiplos_um_candidato_nao_quebra(self):
        info = {
            'estrategia': 'NUMERO_PARCIAL',
            'termo_original': '123',
            'multiplos_encontrados': True,
            'pedidos_candidatos': [{'num_pedido': 'VCD123', 'cliente': 'A'}],
        }
        msg = formatar_sugestao_pedido(info)
        assert 'VCD123' in msg


class TestFormatarSugestaoProduto:
    def test_nao_encontrado_retorna_orientacao(self):
        info = {'encontrado': False, 'multiplos': False, 'termo_original': 'xyz'}
        msg = formatar_sugestao_produto(info)
        assert msg is not None
        assert 'xyz' in msg

    def test_multiplos_lista_candidatos(self):
        info = {
            'encontrado': False, 'multiplos': True, 'termo_original': 'azeitona',
            'candidatos': [
                {'cod_produto': 'AZ1', 'nome_produto': 'AZEITONA VERDE'},
                {'cod_produto': 'AZ2', 'nome_produto': 'AZEITONA PRETA'},
            ],
        }
        msg = formatar_sugestao_produto(info)
        assert 'AZ1' in msg and 'AZ2' in msg

    def test_encontrado_retorna_none(self):
        info = {'encontrado': True, 'multiplos': False, 'termo_original': 'azeitona'}
        assert formatar_sugestao_produto(info) is None
