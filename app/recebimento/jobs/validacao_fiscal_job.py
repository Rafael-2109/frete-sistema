"""
Job de Validacao Fiscal de Recebimento - FASE 1
================================================

Executado pelo scheduler a cada 30 minutos.
Busca NFs de compra novas e executa validacao fiscal.

Fluxo:
1. Buscar DFEs de compra nao validados no Odoo
2. Para cada DFE:
   a) Registrar na tabela de controle (validacao_fiscal_dfe)
   b) Executar validacao fiscal (service)
   c) Atualizar status

Referencia: .claude/references/RECEBIMENTO_MATERIAIS.md
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from app import db
from app.recebimento.models import ValidacaoFiscalDfe
from app.recebimento.services.validacao_fiscal_service import ValidacaoFiscalService
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

# Configuracoes
JANELA_MINUTOS = 120  # Buscar DFEs das ultimas 2 horas

# CNPJs do grupo a serem ignorados (empresas proprias - Nacom, Goya)
# Formato: prefixo do CNPJ (8 primeiros digitos)
CNPJS_IGNORAR = [
    '61724241',  # Nacom
    '18467441',  # Goya
]


class ValidacaoFiscalJob:
    """
    Job para validacao fiscal automatica de NFs de compra.

    Integra com scheduler existente.
    """

    def __init__(self):
        self.odoo = None
        self.service = ValidacaoFiscalService()

    def _get_odoo(self):
        """Obtem conexao Odoo lazy"""
        if self.odoo is None:
            self.odoo = get_odoo_connection()
            if not self.odoo.authenticate():
                raise Exception("Falha na autenticacao com Odoo")
        return self.odoo

    def executar(self, minutos_janela: int = None) -> Dict[str, Any]:
        """
        Executa job de validacao fiscal.

        Args:
            minutos_janela: Janela de tempo em minutos (default: JANELA_MINUTOS)

        Returns:
            {
                'sucesso': bool,
                'dfes_encontrados': int,
                'dfes_validados': int,
                'dfes_aprovados': int,
                'dfes_bloqueados': int,
                'dfes_primeira_compra': int,
                'dfes_erro': int,
                'erro': str | None
            }
        """
        janela = minutos_janela or JANELA_MINUTOS

        resultado = {
            'sucesso': True,
            'dfes_encontrados': 0,
            'dfes_validados': 0,
            'dfes_aprovados': 0,
            'dfes_bloqueados': 0,
            'dfes_primeira_compra': 0,
            'dfes_erro': 0,
            'erro': None
        }

        try:
            logger.info(f"Iniciando validacao fiscal (janela: {janela} minutos)...")

            # 1. Buscar DFEs de compra nao validados
            dfes = self._buscar_dfes_pendentes(janela)
            resultado['dfes_encontrados'] = len(dfes)

            if not dfes:
                logger.info("Nenhum DFE de compra pendente encontrado")
                return resultado

            logger.info(f"Encontrados {len(dfes)} DFEs de compra para validar")

            # 2. Processar cada DFE
            for dfe in dfes:
                try:
                    res = self._processar_dfe(dfe)
                    resultado['dfes_validados'] += 1

                    if res['status'] == 'aprovado':
                        resultado['dfes_aprovados'] += 1
                    elif res['status'] == 'bloqueado':
                        resultado['dfes_bloqueados'] += 1
                    elif res['status'] == 'primeira_compra':
                        resultado['dfes_primeira_compra'] += 1
                    elif res['status'] == 'erro':
                        resultado['dfes_erro'] += 1

                except Exception as e:
                    logger.error(f"Erro ao processar DFE {dfe.get('id')}: {e}")
                    resultado['dfes_erro'] += 1
                    # Atualizar status para erro
                    self._atualizar_status_dfe(
                        dfe.get('id'),
                        'erro',
                        erro_msg=str(e)
                    )

            logger.info(
                f"Validacao fiscal concluida: "
                f"validados={resultado['dfes_validados']}, "
                f"aprovados={resultado['dfes_aprovados']}, "
                f"bloqueados={resultado['dfes_bloqueados']}, "
                f"primeira_compra={resultado['dfes_primeira_compra']}, "
                f"erros={resultado['dfes_erro']}"
            )

        except Exception as e:
            logger.error(f"Erro no job de validacao fiscal: {e}")
            resultado['sucesso'] = False
            resultado['erro'] = str(e)

        return resultado

    def _buscar_dfes_pendentes(self, minutos_janela: int) -> List[Dict]:
        """
        Busca DFEs de compra que ainda nao foram validados.

        Criterios:
        - Tipo: compra (l10n_br_tipo_pedido = 'compra')
        - Estado: done (processado)
        - Data de emissao: dentro da janela
        - Nao existe registro em validacao_fiscal_dfe OU status='pendente'
        """
        odoo = self._get_odoo()

        # Calcular data limite
        data_limite = datetime.utcnow() - timedelta(minutes=minutos_janela)
        data_limite_str = data_limite.strftime('%Y-%m-%d %H:%M:%S')

        # Buscar DFEs de compra no Odoo
        # l10n_br_status = '04' significa processado/concluido
        # nfe_infnfe_ide_finnfe != '4' exclui devolucoes (4 = devolucao de mercadoria)
        # is_cte = False exclui CTe (Conhecimento de Transporte)
        filtro = [
            ['l10n_br_tipo_pedido', '=', 'compra'],
            ['l10n_br_status', '=', '04'],
            ['nfe_infnfe_ide_finnfe', '!=', '4'],  # Excluir devolucoes
            ['is_cte', '=', False],  # Apenas NF-e (excluir CTe)
            ['write_date', '>=', data_limite_str]
        ]

        dfes_odoo = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            filtro,
            fields=[
                'id', 'name', 'nfe_infnfe_ide_nnf',
                'protnfe_infnfe_chnfe',
                'nfe_infnfe_emit_cnpj', 'nfe_infnfe_emit_xnome',
                'write_date'
            ],
            limit=100  # Limitar por execucao
        )

        # Ordenar por write_date decrescente (localmente, pois API nao suporta order)
        if dfes_odoo:
            dfes_odoo.sort(key=lambda x: x.get('write_date', ''), reverse=True)

        if not dfes_odoo:
            return []

        # Filtrar CNPJs do grupo (empresas proprias - Nacom, Goya)
        # Isso e feito localmente pois Odoo nao suporta NOT LIKE facilmente
        dfes_filtrados = []
        for dfe in dfes_odoo:
            cnpj = dfe.get('nfe_infnfe_emit_cnpj', '')
            cnpj_limpo = ''.join(c for c in cnpj if c.isdigit())

            # Verificar se o CNPJ pertence a alguma empresa do grupo
            cnpj_ignorar = False
            for prefixo in CNPJS_IGNORAR:
                if cnpj_limpo.startswith(prefixo):
                    cnpj_ignorar = True
                    logger.debug(f"DFE {dfe.get('id')} ignorado: CNPJ {cnpj_limpo} pertence ao grupo")
                    break

            if not cnpj_ignorar:
                dfes_filtrados.append(dfe)

        dfes_odoo = dfes_filtrados

        # Filtrar os que ainda nao foram validados ou estao pendentes
        dfe_ids = [d['id'] for d in dfes_odoo]

        # Buscar registros existentes na tabela de controle
        registros_existentes = ValidacaoFiscalDfe.query.filter(
            ValidacaoFiscalDfe.odoo_dfe_id.in_(dfe_ids),
            ValidacaoFiscalDfe.status.notin_(['pendente', 'erro'])
        ).all()

        ids_ja_processados = {r.odoo_dfe_id for r in registros_existentes}

        # Retornar apenas os que nao foram processados
        dfes_pendentes = [d for d in dfes_odoo if d['id'] not in ids_ja_processados]

        return dfes_pendentes

    def _processar_dfe(self, dfe: Dict) -> Dict[str, Any]:
        """
        Processa um DFE: registra controle e executa validacao.

        Returns:
            {'status': str, 'detalhes': Dict}
        """
        dfe_id = dfe.get('id')
        numero_nf = dfe.get('nfe_infnfe_ide_nnf')
        chave_nfe = dfe.get('protnfe_infnfe_chnfe')
        cnpj = dfe.get('nfe_infnfe_emit_cnpj', '')
        razao = dfe.get('nfe_infnfe_emit_xnome', '')

        # Limpar CNPJ
        cnpj_limpo = ''.join(c for c in cnpj if c.isdigit())

        logger.info(f"Processando DFE {dfe_id} - NF {numero_nf} ({razao})")

        # 1. Criar/atualizar registro de controle
        registro = self._registrar_controle(
            dfe_id=dfe_id,
            numero_nf=numero_nf,
            chave_nfe=chave_nfe,
            cnpj=cnpj_limpo,
            razao=razao
        )

        # 2. Executar validacao fiscal
        resultado = self.service.validar_nf(dfe_id)

        # 3. Atualizar status do controle
        status = resultado.get('status', 'erro')

        registro.status = status
        registro.total_linhas = resultado.get('linhas_validadas', 0)
        registro.linhas_divergentes = len(resultado.get('divergencias', []))
        registro.linhas_primeira_compra = len(resultado.get('primeira_compra', []))
        registro.linhas_aprovadas = (
            registro.total_linhas -
            registro.linhas_divergentes -
            registro.linhas_primeira_compra
        )
        registro.validado_em = datetime.utcnow()
        registro.atualizado_em = datetime.utcnow()

        if resultado.get('erro'):
            registro.erro_mensagem = resultado['erro']

        db.session.commit()

        logger.info(
            f"DFE {dfe_id} validado: status={status}, "
            f"linhas={registro.total_linhas}, "
            f"divergencias={registro.linhas_divergentes}, "
            f"primeira_compra={registro.linhas_primeira_compra}"
        )

        return {'status': status, 'detalhes': resultado}

    def _registrar_controle(
        self,
        dfe_id: int,
        numero_nf: str,
        chave_nfe: str,
        cnpj: str,
        razao: str
    ) -> ValidacaoFiscalDfe:
        """
        Cria ou atualiza registro na tabela de controle.
        """
        # Verificar se ja existe
        registro = ValidacaoFiscalDfe.query.filter_by(odoo_dfe_id=dfe_id).first()

        if registro:
            registro.status = 'validando'
            registro.atualizado_em = datetime.utcnow()
        else:
            registro = ValidacaoFiscalDfe(
                odoo_dfe_id=dfe_id,
                numero_nf=numero_nf,
                chave_nfe=chave_nfe,
                cnpj_fornecedor=cnpj,
                razao_fornecedor=razao,
                status='validando'
            )
            db.session.add(registro)

        db.session.commit()
        return registro

    def _atualizar_status_dfe(
        self,
        dfe_id: int,
        status: str,
        erro_msg: str = None
    ):
        """Atualiza status de um DFE na tabela de controle"""
        registro = ValidacaoFiscalDfe.query.filter_by(odoo_dfe_id=dfe_id).first()
        if registro:
            registro.status = status
            registro.erro_mensagem = erro_msg
            registro.atualizado_em = datetime.utcnow()
            db.session.commit()


# Funcao de conveniencia para uso no scheduler
def executar_validacao_fiscal(minutos_janela: int = None) -> Dict[str, Any]:
    """
    Funcao de conveniencia para executar o job de validacao fiscal.
    Usada pelo scheduler.

    Args:
        minutos_janela: Janela de tempo em minutos

    Returns:
        Resultado da execucao
    """
    job = ValidacaoFiscalJob()
    return job.executar(minutos_janela)
