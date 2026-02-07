"""
Service de Importação de Carga Inicial - Sistema MotoChefe
Data: 14/10/2025

OBJETIVO:
- Importar dados históricos de planilhas Excel
- Validar integridade referencial e regras de negócio
- Aplicar UPSERT para permitir re-execução
- Parar na primeira falha crítica

FASES DE IMPORTAÇÃO (6 fases sequenciais):
1. Configurações Base (equipes, transportadoras, empresas, custos)
2. Cadastros Dependentes (vendedores, modelos, tabelas de preço)
3. Produtos e Clientes (clientes, motos, despesas)
4. Pedidos e Vendas (pedidos, itens, auditoria)
5. Financeiro (títulos, comissões, títulos a pagar)
6. Logística (embarques, embarque_pedidos, movimentações)
"""
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import func
import traceback

from app import db
from app.utils.timezone import agora_utc_naive
from app.motochefe.models import (
    # Cadastros
    EquipeVendasMoto, VendedorMoto, TransportadoraMoto, ClienteMoto,
    EmpresaVendaMoto, CrossDocking, TabelaPrecoEquipe, TabelaPrecoCrossDocking,
    # Produtos
    ModeloMoto, Moto,
    # Vendas
    PedidoVendaMoto, PedidoVendaMotoItem, PedidoVendaAuditoria,
    # Financeiro
    TituloFinanceiro, ComissaoVendedor, TituloAPagar, MovimentacaoFinanceira,
    # Logística
    EmbarqueMoto, EmbarquePedido,
    # Operacional
    CustosOperacionais, DespesaMensal
)

# Services para funções automáticas
from app.motochefe.services.titulo_service import gerar_titulos_com_fifo_parcelas
from app.motochefe.services.titulo_a_pagar_service import (
    criar_titulo_a_pagar_movimentacao,
    criar_titulo_a_pagar_montagem
)
from app.motochefe.services.comissao_service import gerar_comissao_moto


class ResultadoImportacao:
    """Classe para armazenar resultado de importação"""
    def __init__(self):
        self.sucesso = False
        self.mensagem = ""
        self.total_linhas = 0
        self.inseridos = 0
        self.atualizados = 0
        self.erros = []
        self.avisos = []

    def to_dict(self):
        return {
            'sucesso': self.sucesso,
            'mensagem': self.mensagem,
            'total_linhas': self.total_linhas,
            'inseridos': self.inseridos,
            'atualizados': self.atualizados,
            'erros': self.erros,
            'avisos': self.avisos
        }


class ImportacaoCargaInicialService:
    """Service centralizado para importação de carga inicial"""

    # ============================================================
    # HELPERS - Conversão e Validação
    # ============================================================

    @staticmethod
    def converter_data(valor):
        """Converte valor para date, aceitando diversos formatos"""
        if pd.isna(valor) or valor is None or valor == '':
            return None

        if isinstance(valor, (date, datetime)):
            return valor if isinstance(valor, date) else valor.date()

        # Tentar parser string
        try:
            if isinstance(valor, str):
                # Formatos comuns: dd/mm/yyyy, yyyy-mm-dd
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                    try:
                        return datetime.strptime(valor, fmt).date()
                    except ValueError:
                        continue
            return None
        except Exception as e:
            print(f"Erro ao converter data: {e}")
            print(traceback.format_exc())
            return None

    @staticmethod
    def converter_decimal(valor, casas_decimais=2):
        """Converte valor para Decimal"""
        if pd.isna(valor) or valor is None or valor == '':
            return Decimal('0')

        try:
            # Remover símbolos de moeda e espaços
            if isinstance(valor, str):
                valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
            return Decimal(str(valor)).quantize(Decimal(f'0.{"0" * casas_decimais}'))
        except Exception as e:
            print(f"Erro ao converter decimal: {e}")
            print(traceback.format_exc())
            return Decimal('0')

    @staticmethod
    def converter_inteiro(valor, padrao=0):
        """Converte valor para inteiro"""
        if pd.isna(valor) or valor is None or valor == '':
            return padrao
        try:
            return int(valor)
        except Exception as e:
            print(f"Erro ao converter inteiro: {e}")
            return padrao

    @staticmethod
    def converter_boolean(valor):
        """Converte valor para boolean"""
        if pd.isna(valor) or valor is None or valor == '':
            return False

        if isinstance(valor, bool):
            return valor

        if isinstance(valor, str):
            return valor.upper() in ['SIM', 'TRUE', 'VERDADEIRO', '1', 'S', 'V']

        return bool(valor)

    @staticmethod
    def limpar_cnpj(cnpj):
        """Remove caracteres especiais de CNPJ/CPF"""
        if pd.isna(cnpj) or cnpj is None:
            return None
        return str(cnpj).replace('.', '').replace('/', '').replace('-', '').strip()

    @staticmethod
    def validar_cnpj_obrigatorio(cnpj, linha, campo='CNPJ'):
        """Valida se CNPJ está preenchido"""
        if not cnpj or cnpj == '':
            raise ValueError(f"Linha {linha}: {campo} é obrigatório")
        return cnpj

    @staticmethod
    def converter_string(valor):
        """
        Converte valor para string, tratando NaN do pandas
        Retorna None se vazio ou NaN
        """
        if pd.isna(valor) or valor is None or valor == '':
            return None

        valor_str = str(valor).strip()

        # Verificar se é 'nan' (caso-insensitivo) ou vazio
        if valor_str.lower() == 'nan' or valor_str == '':
            return None

        return valor_str

    # ============================================================
    # FASE 1: CONFIGURAÇÕES BASE
    # ============================================================

    @staticmethod
    def importar_equipes_vendas(df, usuario='sistema'):
        """
        Importa equipes de vendas

        Colunas esperadas:
        - equipe_vendas (obrigatório)
        - responsavel_movimentacao (NACOM)
        - custo_movimentacao (decimal)
        - incluir_custo_movimentacao (boolean)
        - tipo_precificacao (TABELA ou CUSTO_MARKUP)
        - markup (decimal)
        - tipo_comissao (FIXA_EXCEDENTE ou PERCENTUAL)
        - valor_comissao_fixa (decimal)
        - percentual_comissao (decimal)
        - comissao_rateada (boolean)
        - permitir_montagem (boolean)
        - permitir_prazo (boolean)
        - permitir_parcelamento (boolean)
        """
        resultado = ResultadoImportacao()
        resultado.total_linhas = len(df)

        try:
            for idx, row in df.iterrows():
                linha = idx + 2  # +2 porque Excel começa em 1 e tem header

                # Validação obrigatória
                nome = str(row.get('equipe_vendas', '')).strip()
                if not nome:
                    raise ValueError(f"Linha {linha}: Nome da equipe é obrigatório")

                # UPSERT
                equipe = EquipeVendasMoto.query.filter_by(equipe_vendas=nome).first()

                if equipe:
                    # Atualizar
                    resultado.atualizados += 1
                    equipe.atualizado_por = usuario
                    equipe.atualizado_em = agora_utc_naive()
                else:
                    # Inserir
                    equipe = EquipeVendasMoto()
                    equipe.equipe_vendas = nome
                    equipe.criado_por = usuario
                    resultado.inseridos += 1

                # Preencher campos
                equipe.responsavel_movimentacao = row.get('responsavel_movimentacao')
                equipe.custo_movimentacao = ImportacaoCargaInicialService.converter_decimal(
                    row.get('custo_movimentacao', 0)
                )
                equipe.incluir_custo_movimentacao = ImportacaoCargaInicialService.converter_boolean(
                    row.get('incluir_custo_movimentacao', False)
                )
                equipe.tipo_precificacao = row.get('tipo_precificacao', 'TABELA')
                equipe.markup = ImportacaoCargaInicialService.converter_decimal(
                    row.get('markup', 0)
                )
                equipe.tipo_comissao = row.get('tipo_comissao', 'FIXA_EXCEDENTE')
                equipe.valor_comissao_fixa = ImportacaoCargaInicialService.converter_decimal(
                    row.get('valor_comissao_fixa', 0)
                )
                equipe.percentual_comissao = ImportacaoCargaInicialService.converter_decimal(
                    row.get('percentual_comissao', 0), casas_decimais=2
                )
                equipe.comissao_rateada = ImportacaoCargaInicialService.converter_boolean(
                    row.get('comissao_rateada', True)
                )
                equipe.permitir_montagem = ImportacaoCargaInicialService.converter_boolean(
                    row.get('permitir_montagem', True)
                )
                equipe.permitir_prazo = ImportacaoCargaInicialService.converter_boolean(
                    row.get('permitir_prazo', False)
                )
                equipe.permitir_parcelamento = ImportacaoCargaInicialService.converter_boolean(
                    row.get('permitir_parcelamento', False)
                )
                equipe.ativo = True

                db.session.add(equipe)

            db.session.commit()
            resultado.sucesso = True
            resultado.mensagem = f"✅ Equipes importadas com sucesso: {resultado.inseridos} novas, {resultado.atualizados} atualizadas"

        except Exception as e:
            db.session.rollback()
            resultado.sucesso = False
            resultado.mensagem = f"❌ Erro ao importar equipes: {str(e)}"
            resultado.erros.append(str(e))
            resultado.erros.append(traceback.format_exc())

        return resultado

    @staticmethod
    def importar_transportadoras(df, usuario='sistema'):
        """
        Importa transportadoras

        Colunas esperadas:
        - transportadora (obrigatório)
        - cnpj
        - telefone
        - chave_pix
        - banco
        - cod_banco
        - agencia
        - conta
        """
        resultado = ResultadoImportacao()
        resultado.total_linhas = len(df)

        try:
            for idx, row in df.iterrows():
                linha = idx + 2

                nome = str(row.get('transportadora', '')).strip()
                if not nome:
                    raise ValueError(f"Linha {linha}: Nome da transportadora é obrigatório")

                # UPSERT
                transp = TransportadoraMoto.query.filter_by(transportadora=nome).first()

                if transp:
                    resultado.atualizados += 1
                    transp.atualizado_por = usuario
                    transp.atualizado_em = agora_utc_naive()
                else:
                    transp = TransportadoraMoto()
                    transp.transportadora = nome
                    transp.criado_por = usuario
                    resultado.inseridos += 1

                transp.cnpj = ImportacaoCargaInicialService.limpar_cnpj(row.get('cnpj'))
                transp.telefone = row.get('telefone')
                transp.chave_pix = row.get('chave_pix')
                transp.banco = row.get('banco')
                transp.cod_banco = row.get('cod_banco')
                transp.agencia = row.get('agencia')
                transp.conta = row.get('conta')
                transp.ativo = True

                db.session.add(transp)

            db.session.commit()
            resultado.sucesso = True
            resultado.mensagem = f"✅ Transportadoras importadas: {resultado.inseridos} novas, {resultado.atualizados} atualizadas"

        except Exception as e:
            db.session.rollback()
            resultado.sucesso = False
            resultado.mensagem = f"❌ Erro: {str(e)}"
            resultado.erros.append(str(e))

        return resultado

    @staticmethod
    def importar_empresas(df, usuario='sistema'):
        """
        Importa empresas vendedoras (contas bancárias)

        Colunas esperadas:
        - empresa (obrigatório)
        - cnpj_empresa
        - chave_pix
        - banco
        - cod_banco
        - agencia
        - conta
        - tipo_conta (FABRICANTE, OPERACIONAL, MARGEM_SOGIMA)
        - baixa_compra_auto (boolean)
        - saldo (decimal - inicial)
        """
        resultado = ResultadoImportacao()
        resultado.total_linhas = len(df)

        try:
            for idx, row in df.iterrows():
                linha = idx + 2

                nome = str(row.get('empresa', '')).strip()
                if not nome:
                    raise ValueError(f"Linha {linha}: Nome da empresa é obrigatório")

                # UPSERT por nome
                empresa = EmpresaVendaMoto.query.filter_by(empresa=nome).first()

                if empresa:
                    resultado.atualizados += 1
                    empresa.atualizado_por = usuario
                    empresa.atualizado_em = agora_utc_naive()
                else:
                    empresa = EmpresaVendaMoto()
                    empresa.empresa = nome
                    empresa.criado_por = usuario
                    resultado.inseridos += 1

                empresa.cnpj_empresa = ImportacaoCargaInicialService.limpar_cnpj(row.get('cnpj_empresa'))
                empresa.chave_pix = row.get('chave_pix')
                empresa.banco = row.get('banco')
                empresa.cod_banco = row.get('cod_banco')
                empresa.agencia = row.get('agencia')
                empresa.conta = row.get('conta')
                empresa.tipo_conta = row.get('tipo_conta')
                empresa.baixa_compra_auto = ImportacaoCargaInicialService.converter_boolean(
                    row.get('baixa_compra_auto', False)
                )
                empresa.saldo = ImportacaoCargaInicialService.converter_decimal(
                    row.get('saldo', 0)
                )
                empresa.ativo = True

                db.session.add(empresa)

            db.session.commit()
            resultado.sucesso = True
            resultado.mensagem = f"✅ Empresas importadas: {resultado.inseridos} novas, {resultado.atualizados} atualizadas"

        except Exception as e:
            db.session.rollback()
            resultado.sucesso = False
            resultado.mensagem = f"❌ Erro: {str(e)}"
            resultado.erros.append(str(e))

        return resultado

    @staticmethod
    def importar_crossdocking(df, usuario='sistema'):
        """
        Importa CrossDocking (APENAS 1 REGISTRO GENÉRICO)

        Colunas: mesmas de EquipeVendasMoto
        """
        resultado = ResultadoImportacao()
        resultado.total_linhas = len(df)

        try:
            # Garantir apenas 1 registro
            if len(df) > 1:
                resultado.avisos.append("⚠️ CrossDocking deve ter apenas 1 registro. Usando primeira linha.")

            row = df.iloc[0]

            nome = str(row.get('nome', 'CrossDocking Genérico')).strip()

            # UPSERT
            cd = CrossDocking.query.first()  # Busca o único registro

            if cd:
                resultado.atualizados += 1
                cd.atualizado_por = usuario
                cd.atualizado_em = agora_utc_naive()
            else:
                cd = CrossDocking()
                cd.criado_por = usuario
                resultado.inseridos += 1

            cd.nome = nome
            cd.descricao = row.get('descricao')
            cd.responsavel_movimentacao = row.get('responsavel_movimentacao')
            cd.custo_movimentacao = ImportacaoCargaInicialService.converter_decimal(
                row.get('custo_movimentacao', 0)
            )
            cd.incluir_custo_movimentacao = ImportacaoCargaInicialService.converter_boolean(
                row.get('incluir_custo_movimentacao', False)
            )
            cd.tipo_precificacao = row.get('tipo_precificacao', 'TABELA')
            cd.markup = ImportacaoCargaInicialService.converter_decimal(row.get('markup', 0))
            cd.tipo_comissao = row.get('tipo_comissao', 'FIXA_EXCEDENTE')
            cd.valor_comissao_fixa = ImportacaoCargaInicialService.converter_decimal(
                row.get('valor_comissao_fixa', 0)
            )
            cd.percentual_comissao = ImportacaoCargaInicialService.converter_decimal(
                row.get('percentual_comissao', 0), 2
            )
            cd.comissao_rateada = ImportacaoCargaInicialService.converter_boolean(
                row.get('comissao_rateada', True)
            )
            cd.permitir_montagem = ImportacaoCargaInicialService.converter_boolean(
                row.get('permitir_montagem', True)
            )
            cd.ativo = True

            db.session.add(cd)
            db.session.commit()

            resultado.sucesso = True
            resultado.mensagem = f"✅ CrossDocking configurado com sucesso"

        except Exception as e:
            db.session.rollback()
            resultado.sucesso = False
            resultado.mensagem = f"❌ Erro: {str(e)}"
            resultado.erros.append(str(e))

        return resultado

    @staticmethod
    def importar_custos_operacionais(df, usuario='sistema'):
        """
        Importa custos operacionais (APENAS 1 REGISTRO ATIVO)

        Colunas esperadas:
        - custo_montagem (decimal)
        - custo_movimentacao_devolucao (decimal)
        - data_vigencia_inicio (date)
        """
        resultado = ResultadoImportacao()
        resultado.total_linhas = len(df)

        try:
            if len(df) > 1:
                resultado.avisos.append("⚠️ Custos Operacionais deve ter apenas 1 registro ativo. Usando primeira linha.")

            row = df.iloc[0]

            # Inativar custos antigos
            CustosOperacionais.query.update({'ativo': False, 'data_vigencia_fim': date.today()})

            # Criar novo
            custos = CustosOperacionais()
            custos.custo_montagem = ImportacaoCargaInicialService.converter_decimal(
                row.get('custo_montagem', 0)
            )
            custos.custo_movimentacao_devolucao = ImportacaoCargaInicialService.converter_decimal(
                row.get('custo_movimentacao_devolucao', 0)
            )
            custos.data_vigencia_inicio = ImportacaoCargaInicialService.converter_data(
                row.get('data_vigencia_inicio')
            ) or date.today()
            custos.data_vigencia_fim = None
            custos.ativo = True
            custos.criado_por = usuario

            db.session.add(custos)
            db.session.commit()

            resultado.inseridos = 1
            resultado.sucesso = True
            resultado.mensagem = f"✅ Custos operacionais configurados"

        except Exception as e:
            db.session.rollback()
            resultado.sucesso = False
            resultado.mensagem = f"❌ Erro: {str(e)}"
            resultado.erros.append(str(e))

        return resultado

    # ============================================================
    # FASE 2: CADASTROS DEPENDENTES
    # ============================================================

    @staticmethod
    def importar_vendedores(df, usuario='sistema'):
        """
        Importa vendedores

        Colunas esperadas:
        - vendedor (obrigatório)
        - equipe_vendas (obrigatório - nome da equipe)
        """
        resultado = ResultadoImportacao()
        resultado.total_linhas = len(df)

        try:
            for idx, row in df.iterrows():
                linha = idx + 2

                nome = str(row.get('vendedor', '')).strip()
                nome_equipe = str(row.get('equipe_vendas', '')).strip()

                if not nome:
                    raise ValueError(f"Linha {linha}: Nome do vendedor é obrigatório")
                if not nome_equipe:
                    raise ValueError(f"Linha {linha}: Equipe de vendas é obrigatória")

                # Buscar equipe
                equipe = EquipeVendasMoto.query.filter_by(equipe_vendas=nome_equipe, ativo=True).first()
                if not equipe:
                    raise ValueError(f"Linha {linha}: Equipe '{nome_equipe}' não encontrada")

                # UPSERT
                vendedor = VendedorMoto.query.filter_by(vendedor=nome).first()

                if vendedor:
                    resultado.atualizados += 1
                    vendedor.atualizado_por = usuario
                    vendedor.atualizado_em = agora_utc_naive()
                else:
                    vendedor = VendedorMoto()
                    vendedor.vendedor = nome
                    vendedor.criado_por = usuario
                    resultado.inseridos += 1

                vendedor.equipe_vendas_id = equipe.id
                vendedor.ativo = True

                db.session.add(vendedor)

            db.session.commit()
            resultado.sucesso = True
            resultado.mensagem = f"✅ Vendedores importados: {resultado.inseridos} novos, {resultado.atualizados} atualizados"

        except Exception as e:
            db.session.rollback()
            resultado.sucesso = False
            resultado.mensagem = f"❌ Erro: {str(e)}"
            resultado.erros.append(str(e))

        return resultado

    @staticmethod
    def importar_modelos(df, usuario='sistema'):
        """
        Importa modelos de motos

        Colunas esperadas:
        - nome_modelo (obrigatório)
        - potencia_motor (obrigatório - ex: '1000W', '2000W')
        - autopropelido (boolean)
        - preco_tabela (decimal - obrigatório)
        - descricao
        """
        resultado = ResultadoImportacao()
        resultado.total_linhas = len(df)

        try:
            for idx, row in df.iterrows():
                linha = idx + 2

                nome = str(row.get('nome_modelo', '')).strip()
                potencia = str(row.get('potencia_motor', '')).strip()

                if not nome:
                    raise ValueError(f"Linha {linha}: Nome do modelo é obrigatório")
                if not potencia:
                    raise ValueError(f"Linha {linha}: Potência do motor é obrigatória")

                preco = ImportacaoCargaInicialService.converter_decimal(row.get('preco_tabela'))
                if preco <= 0:
                    raise ValueError(f"Linha {linha}: Preço de tabela deve ser maior que zero")

                # UPSERT por nome_modelo
                modelo = ModeloMoto.query.filter_by(nome_modelo=nome).first()

                if modelo:
                    resultado.atualizados += 1
                    modelo.atualizado_por = usuario
                    modelo.atualizado_em = agora_utc_naive()
                else:
                    modelo = ModeloMoto()
                    modelo.nome_modelo = nome
                    modelo.criado_por = usuario
                    resultado.inseridos += 1

                modelo.potencia_motor = potencia
                modelo.autopropelido = ImportacaoCargaInicialService.converter_boolean(
                    row.get('autopropelido', False)
                )
                modelo.preco_tabela = preco
                modelo.descricao = row.get('descricao')
                modelo.ativo = True

                db.session.add(modelo)

            db.session.commit()
            resultado.sucesso = True
            resultado.mensagem = f"✅ Modelos importados: {resultado.inseridos} novos, {resultado.atualizados} atualizados"

        except Exception as e:
            db.session.rollback()
            resultado.sucesso = False
            resultado.mensagem = f"❌ Erro: {str(e)}"
            resultado.erros.append(str(e))

        return resultado

    # ============================================================
    # FASE 3: PRODUTOS E CLIENTES
    # ============================================================

    @staticmethod
    def importar_clientes(df, usuario='sistema'):
        """
        Importa clientes

        Colunas esperadas:
        - cnpj_cliente (obrigatório)
        - cliente (opcional - se vazio, usa 'CLIENTE_{cnpj}' temporariamente)
        - vendedor (obrigatório - nome do vendedor)
        - crossdocking (boolean)
        - endereco_cliente, numero_cliente, complemento_cliente
        - bairro_cliente, cidade_cliente, estado_cliente, cep_cliente
        - telefone_cliente, email_cliente

        ⚠️ DICA: Deixe 'cliente' vazio e execute o script de atualização pela Receita Federal
        depois para preencher automaticamente nome e endereço.
        """
        resultado = ResultadoImportacao()
        resultado.total_linhas = len(df)

        try:
            for idx, row in df.iterrows():
                linha = idx + 2

                cnpj = ImportacaoCargaInicialService.limpar_cnpj(row.get('cnpj_cliente'))
                nome = ImportacaoCargaInicialService.converter_string(row.get('cliente'))
                nome_vendedor = ImportacaoCargaInicialService.converter_string(row.get('vendedor'))

                ImportacaoCargaInicialService.validar_cnpj_obrigatorio(cnpj, linha, 'CNPJ do cliente')

                # ✅ Se nome vazio, usar CNPJ como identificador temporário
                if not nome:
                    nome = f'CLIENTE_{cnpj}'  # Nome provisório será substituído pela Receita Federal

                if not nome_vendedor:
                    raise ValueError(f"Linha {linha}: Vendedor é obrigatório")

                # ✅ Converter para MAIÚSCULA para busca case-insensitive
                nome_vendedor_upper = nome_vendedor.upper()

                # Buscar vendedor (case-insensitive)
                vendedor = VendedorMoto.query.filter(
                    func.upper(VendedorMoto.vendedor) == nome_vendedor_upper,
                    VendedorMoto.ativo == True
                ).first()
                if not vendedor:
                    raise ValueError(f"Linha {linha}: Vendedor '{nome_vendedor}' não encontrado")

                # UPSERT por CNPJ
                cliente = ClienteMoto.query.filter_by(cnpj_cliente=cnpj).first()

                if cliente:
                    resultado.atualizados += 1
                    cliente.atualizado_por = usuario
                    cliente.atualizado_em = agora_utc_naive()
                else:
                    cliente = ClienteMoto()
                    cliente.cnpj_cliente = cnpj
                    cliente.criado_por = usuario
                    resultado.inseridos += 1

                cliente.cliente = nome
                cliente.vendedor_id = vendedor.id
                cliente.crossdocking = ImportacaoCargaInicialService.converter_boolean(
                    row.get('crossdocking', False)
                )
                # ✅ Usar converter_string para evitar 'nan' do pandas
                cliente.endereco_cliente = ImportacaoCargaInicialService.converter_string(row.get('endereco_cliente'))
                cliente.numero_cliente = ImportacaoCargaInicialService.converter_string(row.get('numero_cliente'))
                cliente.complemento_cliente = ImportacaoCargaInicialService.converter_string(row.get('complemento_cliente'))
                cliente.bairro_cliente = ImportacaoCargaInicialService.converter_string(row.get('bairro_cliente'))
                cliente.cidade_cliente = ImportacaoCargaInicialService.converter_string(row.get('cidade_cliente'))
                cliente.estado_cliente = ImportacaoCargaInicialService.converter_string(row.get('estado_cliente'))
                cliente.cep_cliente = ImportacaoCargaInicialService.converter_string(row.get('cep_cliente'))
                cliente.telefone_cliente = ImportacaoCargaInicialService.converter_string(row.get('telefone_cliente'))
                cliente.email_cliente = ImportacaoCargaInicialService.converter_string(row.get('email_cliente'))
                cliente.ativo = True

                db.session.add(cliente)

            db.session.commit()
            resultado.sucesso = True
            resultado.mensagem = f"✅ Clientes importados: {resultado.inseridos} novos, {resultado.atualizados} atualizados"

        except Exception as e:
            db.session.rollback()
            resultado.sucesso = False
            resultado.mensagem = f"❌ Erro: {str(e)}"
            resultado.erros.append(str(e))

        return resultado

    @staticmethod
    def importar_motos(df, usuario='sistema'):
        """
        Importa motos (chassi único)

        Colunas esperadas:
        - numero_chassi (obrigatório - PK)
        - numero_motor (único)
        - nome_modelo (obrigatório)
        - cor (obrigatório)
        - ano_fabricacao
        - nf_entrada (obrigatório)
        - data_nf_entrada (obrigatório)
        - data_entrada (obrigatório)
        - fornecedor (obrigatório)
        - custo_aquisicao (decimal - obrigatório)
        - observacao
        - pallet

        ⚠️ CAMPOS GERENCIADOS AUTOMATICAMENTE (NÃO INCLUIR NO EXCEL):
        - status: Sempre inicia como 'DISPONIVEL' (alterado pelo sistema em pedidos/devoluções)
        - status_pagamento_custo: Sempre inicia como 'PENDENTE' (alterado ao efetuar pagamentos)
        - empresa_pagadora_id: Sempre NULL (preenchido ao efetuar pagamentos)
        - reservado: Calculado automaticamente baseado no status
        """
        resultado = ResultadoImportacao()
        resultado.total_linhas = len(df)

        try:
            for idx, row in df.iterrows():
                linha = idx + 2

                # ✅ Usar converter_string para evitar 'nan' do pandas
                chassi = ImportacaoCargaInicialService.converter_string(row.get('numero_chassi'))
                nome_modelo = ImportacaoCargaInicialService.converter_string(row.get('nome_modelo'))

                if not chassi:
                    raise ValueError(f"Linha {linha}: Número do chassi é obrigatório")
                if not nome_modelo:
                    raise ValueError(f"Linha {linha}: Modelo é obrigatório")

                # ✅ Converter para MAIÚSCULA para evitar problemas de case
                nome_modelo = nome_modelo.upper()

                # Buscar modelo (case-insensitive)
                modelo = ModeloMoto.query.filter(
                    func.upper(ModeloMoto.nome_modelo) == nome_modelo,
                    ModeloMoto.ativo == True
                ).first()
                if not modelo:
                    raise ValueError(f"Linha {linha}: Modelo '{nome_modelo}' não encontrado")

                # Validar campos obrigatórios
                if not row.get('nf_entrada'):
                    raise ValueError(f"Linha {linha}: NF de entrada é obrigatória")
                if not row.get('fornecedor'):
                    raise ValueError(f"Linha {linha}: Fornecedor é obrigatório")

                custo = ImportacaoCargaInicialService.converter_decimal(row.get('custo_aquisicao'))
                if custo <= 0:
                    raise ValueError(f"Linha {linha}: Custo de aquisição deve ser maior que zero")

                # UPSERT por chassi
                moto = Moto.query.filter_by(numero_chassi=chassi).first()

                if moto:
                    resultado.atualizados += 1
                    moto.atualizado_por = usuario
                    moto.atualizado_em = agora_utc_naive()
                else:
                    moto = Moto()
                    moto.numero_chassi = chassi
                    moto.criado_por = usuario
                    resultado.inseridos += 1

                # Motor (validar unique se preenchido)
                # ✅ Usar converter_string para evitar 'nan' do pandas
                motor = ImportacaoCargaInicialService.converter_string(row.get('numero_motor'))
                if motor:
                    # Validar unicidade apenas se motor foi preenchido
                    existe_motor = Moto.query.filter(
                        Moto.numero_motor == motor,
                        Moto.numero_chassi != chassi
                    ).first()
                    if existe_motor:
                        raise ValueError(f"Linha {linha}: Número de motor '{motor}' já existe em outro chassi")
                    moto.numero_motor = motor
                else:
                    # Se motor vazio, deixar NULL (permite múltiplos NULL no banco)
                    moto.numero_motor = None

                moto.modelo_id = modelo.id
                moto.cor = row.get('cor', 'SEM COR')
                moto.ano_fabricacao = ImportacaoCargaInicialService.converter_inteiro(
                    row.get('ano_fabricacao')
                )
                moto.nf_entrada = row.get('nf_entrada')
                moto.data_nf_entrada = ImportacaoCargaInicialService.converter_data(
                    row.get('data_nf_entrada')
                ) or date.today()
                moto.data_entrada = ImportacaoCargaInicialService.converter_data(
                    row.get('data_entrada')
                ) or date.today()
                moto.fornecedor = row.get('fornecedor')
                moto.custo_aquisicao = custo
                # ✅ Usar converter_string para evitar 'nan' do pandas
                moto.observacao = ImportacaoCargaInicialService.converter_string(row.get('observacao'))
                moto.pallet = ImportacaoCargaInicialService.converter_string(row.get('pallet'))

                # ✅ CAMPOS GERENCIADOS AUTOMATICAMENTE - SEMPRE VALORES PADRÃO NA IMPORTAÇÃO
                moto.status = 'DISPONIVEL'  # Sempre disponível na entrada
                moto.status_pagamento_custo = 'PENDENTE'  # Sempre pendente na entrada
                moto.reservado = False  # Nunca reservado na entrada
                moto.empresa_pagadora_id = None  # Sem empresa pagadora na entrada
                moto.ativo = True

                db.session.add(moto)

            db.session.commit()
            resultado.sucesso = True
            resultado.mensagem = f"✅ Motos importadas: {resultado.inseridos} novas, {resultado.atualizados} atualizadas"

        except Exception as e:
            db.session.rollback()
            resultado.sucesso = False
            resultado.mensagem = f"❌ Erro: {str(e)}"
            resultado.erros.append(str(e))

        return resultado

    # ============================================================
    # GERAÇÃO DE TEMPLATES EXCEL
    # ============================================================

    @staticmethod
    def gerar_template_fase1():
        """Gera arquivo Excel com templates da Fase 1"""
        with pd.ExcelWriter('/tmp/motochefe_fase1_templates.xlsx', engine='openpyxl') as writer:
            # Equipes
            df_equipes = pd.DataFrame(columns=[
                'equipe_vendas', 'responsavel_movimentacao', 'custo_movimentacao',
                'incluir_custo_movimentacao', 'tipo_precificacao', 'markup',
                'tipo_comissao', 'valor_comissao_fixa', 'percentual_comissao',
                'comissao_rateada', 'permitir_montagem', 'permitir_prazo', 'permitir_parcelamento'
            ])
            df_equipes.to_excel(writer, sheet_name='1_Equipes', index=False)

            # Transportadoras
            df_transp = pd.DataFrame(columns=[
                'transportadora', 'cnpj', 'telefone', 'chave_pix',
                'banco', 'cod_banco', 'agencia', 'conta'
            ])
            df_transp.to_excel(writer, sheet_name='2_Transportadoras', index=False)

            # Empresas
            df_empresas = pd.DataFrame(columns=[
                'empresa', 'cnpj_empresa', 'chave_pix', 'banco', 'cod_banco',
                'agencia', 'conta', 'tipo_conta', 'baixa_compra_auto', 'saldo'
            ])
            df_empresas.to_excel(writer, sheet_name='3_Empresas', index=False)

            # CrossDocking
            df_cd = pd.DataFrame(columns=[
                'nome', 'descricao', 'responsavel_movimentacao', 'custo_movimentacao',
                'incluir_custo_movimentacao', 'tipo_precificacao', 'markup',
                'tipo_comissao', 'valor_comissao_fixa', 'percentual_comissao',
                'comissao_rateada', 'permitir_montagem'
            ])
            df_cd.to_excel(writer, sheet_name='4_CrossDocking', index=False)

            # Custos
            df_custos = pd.DataFrame(columns=[
                'custo_montagem', 'custo_movimentacao_devolucao', 'data_vigencia_inicio'
            ])
            df_custos.to_excel(writer, sheet_name='5_Custos', index=False)

        return '/tmp/motochefe_fase1_templates.xlsx'

    @staticmethod
    def gerar_template_fase2():
        """Gera arquivo Excel com templates da Fase 2"""
        with pd.ExcelWriter('/tmp/motochefe_fase2_templates.xlsx', engine='openpyxl') as writer:
            # Vendedores
            df_vend = pd.DataFrame(columns=['vendedor', 'equipe_vendas'])
            df_vend.to_excel(writer, sheet_name='1_Vendedores', index=False)

            # Modelos
            df_mod = pd.DataFrame(columns=[
                'nome_modelo', 'potencia_motor', 'autopropelido', 'preco_tabela', 'descricao'
            ])
            df_mod.to_excel(writer, sheet_name='2_Modelos', index=False)

        return '/tmp/motochefe_fase2_templates.xlsx'

    @staticmethod
    def gerar_template_fase3():
        """Gera arquivo Excel com templates da Fase 3"""
        with pd.ExcelWriter('/tmp/motochefe_fase3_templates.xlsx', engine='openpyxl') as writer:
            # Clientes
            df_cli = pd.DataFrame(columns=[
                'cnpj_cliente', 'cliente', 'vendedor', 'crossdocking',
                'endereco_cliente', 'numero_cliente', 'complemento_cliente',
                'bairro_cliente', 'cidade_cliente', 'estado_cliente', 'cep_cliente',
                'telefone_cliente', 'email_cliente'
            ])
            df_cli.to_excel(writer, sheet_name='1_Clientes', index=False)

            # Motos - ⚠️ REMOVIDOS: status, status_pagamento_custo, empresa_pagadora
            # Esses campos são gerenciados automaticamente pelo sistema
            df_motos = pd.DataFrame(columns=[
                'numero_chassi', 'numero_motor', 'nome_modelo', 'cor', 'ano_fabricacao',
                'nf_entrada', 'data_nf_entrada', 'data_entrada', 'fornecedor',
                'custo_aquisicao', 'observacao', 'pallet'
            ])
            df_motos.to_excel(writer, sheet_name='2_Motos', index=False)

        return '/tmp/motochefe_fase3_templates.xlsx'
