import unittest
from app import create_app, db
from app.pedidos.models import Pedido
from app.vinculos.models import CidadeAtendida
from app.localidades.models import Cidade
from app.tabelas.models import TabelaFrete
from app.transportadoras.models import Transportadora
from app.veiculos.models import Veiculo
from app.utils.frete_simulador import (
    calcular_fretes_possiveis,
    calcular_frete_por_cnpj,
    agrupar_por_cnpj,
    deve_calcular_frete,
    obter_cidade_destino
)

class TestCotacao(unittest.TestCase):
    def setUp(self):
        """Configuração inicial para cada teste"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.criar_dados_base()

    def tearDown(self):
        """Limpeza após cada teste"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def criar_dados_base(self):
        """Cria dados básicos para os testes"""
        # 1. Criar cidades
        self.cidade_sp = Cidade(
            nome="São Paulo",
            uf="SP",
            icms=0.12,
            codigo_ibge="3550308",
            substitui_icms_por_iss=False
        )
        self.cidade_guarulhos = Cidade(
            nome="Guarulhos",
            uf="SP",
            icms=0.12,
            codigo_ibge="3518800",
            substitui_icms_por_iss=False
        )
        self.cidade_jarinu = Cidade(
            nome="Jarinu",
            uf="SP",
            icms=0.12,
            codigo_ibge="3525102",
            substitui_icms_por_iss=False
        )
        db.session.add_all([self.cidade_sp, self.cidade_guarulhos, self.cidade_jarinu])

        # 2. Criar veículos
        self.veiculos = [
            Veiculo(nome="FIORINO", peso_maximo=600),
            Veiculo(nome="VAN/HR", peso_maximo=1500),
            Veiculo(nome="3/4", peso_maximo=3000),
            Veiculo(nome="TOCO", peso_maximo=6000),
            Veiculo(nome="TRUCK", peso_maximo=12000),
            Veiculo(nome="CARRETA", peso_maximo=25000)
        ]
        db.session.add_all(self.veiculos)

        # 3. Criar transportadora
        self.transportadora = Transportadora(
            razao_social="TESTE TRANSPORTES LTDA",
            cnpj="00000000000100",
            cidade="São Paulo",
            uf="SP"
        )
        db.session.add(self.transportadora)

        # 4. Criar tabelas de frete
        self.tabelas = []
        modalidades = ["FIORINO", "VAN/HR", "3/4", "TOCO", "TRUCK", "CARRETA"]
        
        for modalidade in modalidades:
            # Tabela para carga direta
            self.tabelas.append(TabelaFrete(
                transportadora=self.transportadora,
                nome_tabela="ROTA 1",
                modalidade=modalidade,
                tipo_carga="DIRETA",
                valor_kg=0.50,
                frete_minimo_peso=100.00,
                percentual_gris=0.3,
                valor_despacho=50.00,
                uf_origem="SP",
                uf_destino="SP",
                criado_por="TESTE"
            ))

        # Tabela para carga fracionada
        self.tabelas.append(TabelaFrete(
            transportadora=self.transportadora,
            nome_tabela="FRACIONADA",
            tipo_carga="FRACIONADA",
            modalidade="FRETE PESO",
            valor_kg=0.80,
            frete_minimo_peso=50.00,
            percentual_gris=0.3,
            valor_despacho=30.00,
            uf_origem="SP",
            uf_destino="SP",
            criado_por="TESTE"
        ))

        db.session.add_all(self.tabelas)

        # 5. Criar vínculos de cidades atendidas
        self.vinculos = []
        for cidade in [self.cidade_sp, self.cidade_guarulhos, self.cidade_jarinu]:
            self.vinculos.append(CidadeAtendida(
                transportadora=self.transportadora,
                cidade=cidade,
                nome_tabela="ROTA 1",
                uf=cidade.uf,
                codigo_ibge=cidade.codigo_ibge
            ))
            if cidade == self.cidade_sp:
                self.vinculos.append(CidadeAtendida(
                    transportadora=self.transportadora,
                    cidade=cidade,
                    nome_tabela="FRACIONADA",
                    uf=cidade.uf,
                    codigo_ibge=cidade.codigo_ibge
                ))

        db.session.add_all(self.vinculos)
        db.session.commit()

    def test_calculo_frete_simples(self):
        """Testa o cálculo de frete para um único pedido"""
        # Criar um pedido de teste
        pedido = Pedido(
            num_pedido="TESTE001",
            nome_cidade="São Paulo",
            cod_uf="SP",
            cnpj_cpf="12345678000100",
            peso_total=1000,
            valor_saldo_total=5000.00
        )
        db.session.add(pedido)
        db.session.commit()

        # Calcular fretes possíveis
        resultados = calcular_fretes_possiveis(
            cidade_destino=pedido.nome_cidade,
            uf_destino=pedido.cod_uf,
            peso=pedido.peso_total,
            valor=pedido.valor_saldo_total
        )

        # Validações
        self.assertTrue(len(resultados) > 0, "Deveria retornar opções de frete")
        for resultado in resultados:
            self.assertIn('valor_total', resultado, "Resultado deve conter valor_total")
            self.assertIn('transportadora', resultado, "Resultado deve conter transportadora")
            self.assertIn('modalidade', resultado, "Resultado deve conter modalidade")
            self.assertIn('tipo', resultado, "Resultado deve conter tipo")

    def test_agrupamento_pedidos(self):
        """Testa o agrupamento de pedidos por CNPJ/cidade"""
        # Criar pedidos de teste
        pedidos = [
            Pedido(
                num_pedido="TESTE001",
                nome_cidade="São Paulo",
                cod_uf="SP",
                cnpj_cpf="11111111000100",
                peso_total=1000,
                valor_saldo_total=5000.00
            ),
            Pedido(
                num_pedido="TESTE002",
                nome_cidade="São Paulo",
                cod_uf="SP",
                cnpj_cpf="11111111000100",
                peso_total=500,
                valor_saldo_total=2500.00
            ),
            Pedido(
                num_pedido="TESTE003",
                nome_cidade="Guarulhos",
                cod_uf="SP",
                cnpj_cpf="22222222000100",
                peso_total=750,
                valor_saldo_total=3750.00
            )
        ]
        db.session.add_all(pedidos)
        db.session.commit()

        grupos = agrupar_por_cnpj(pedidos)
        
        # Validações
        self.assertEqual(len(grupos), 2, "Deveria ter 2 grupos distintos")
        
        # Verificar grupo São Paulo
        grupo_sp = grupos.get(("11111111000100", "São Paulo"))
        self.assertIsNotNone(grupo_sp, "Deveria existir grupo de São Paulo")
        self.assertEqual(len(grupo_sp), 2, "Grupo SP deveria ter 2 pedidos")
        
        # Verificar grupo Guarulhos
        grupo_guarulhos = grupos.get(("22222222000100", "Guarulhos"))
        self.assertIsNotNone(grupo_guarulhos, "Deveria existir grupo de Guarulhos")
        self.assertEqual(len(grupo_guarulhos), 1, "Grupo Guarulhos deveria ter 1 pedido")

    def test_calculo_frete_multiplos_pedidos(self):
        """Testa o cálculo de frete para múltiplos pedidos"""
        # Criar pedidos de teste com mesmo CNPJ e cidade
        pedidos = [
            Pedido(
                num_pedido="TESTE001",
                nome_cidade="São Paulo",
                cod_uf="SP",
                cnpj_cpf="11111111000100",
                peso_total=1000,
                valor_saldo_total=5000.00
            ),
            Pedido(
                num_pedido="TESTE002",
                nome_cidade="São Paulo",
                cod_uf="SP",
                cnpj_cpf="11111111000100",
                peso_total=500,
                valor_saldo_total=2500.00
            )
        ]
        db.session.add_all(pedidos)
        db.session.commit()

        resultados = calcular_frete_por_cnpj(pedidos)

        # Validações
        self.assertTrue(len(resultados) > 0, "Deveria retornar opções de frete")
        for resultado in resultados:
            self.assertIn('valor_total_grupo', resultado, "Resultado deve conter valor_total_grupo")
            self.assertIn('rateio', resultado, "Resultado deve conter rateio")
            self.assertEqual(len(resultado['rateio']), 2, "Rateio deve conter 2 pedidos")

    def test_validacao_capacidade_veiculo(self):
        """Testa a validação de capacidade dos veículos"""
        # Criar pedido com peso acima da capacidade de alguns veículos
        pedido = Pedido(
            num_pedido="TESTE001",
            nome_cidade="São Paulo",
            cod_uf="SP",
            cnpj_cpf="12345678000100",
            peso_total=2000,  # Acima da capacidade da FIORINO e VAN/HR
            valor_saldo_total=10000.00
        )
        db.session.add(pedido)
        db.session.commit()

        resultados = calcular_fretes_possiveis(
            cidade_destino=pedido.nome_cidade,
            uf_destino=pedido.cod_uf,
            peso=pedido.peso_total,
            valor=pedido.valor_saldo_total
        )

        # Validações
        modalidades_encontradas = [r['modalidade'] for r in resultados]
        self.assertNotIn("FIORINO", modalidades_encontradas, "FIORINO não deveria aparecer (peso excede capacidade)")
        self.assertNotIn("VAN/HR", modalidades_encontradas, "VAN/HR não deveria aparecer (peso excede capacidade)")
        self.assertIn("3/4", modalidades_encontradas, "3/4 deveria aparecer (peso dentro da capacidade)")

if __name__ == '__main__':
    unittest.main() 