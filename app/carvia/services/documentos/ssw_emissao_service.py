"""
SswEmissaoService — Orquestrador de emissao automatica de CTe SSW.

Responsabilidades:
- Validar inputs e preparar CarviaEmissaoCte
- Converter medidas de moto CM → M
- Enfileirar job RQ para execucao Playwright
- Importar XML/PDF resultantes no sistema

Nao executa Playwright diretamente — delega ao job RQ.
"""
import logging
import os
import re

from app import db

logger = logging.getLogger(__name__)


# Padroes de erro SSW capturados do DOM/dialogs
ERROS_SSW = {
    r'rota\s+n[aã]o\s+cadastrada': 'ROTA_NAO_CADASTRADA',
    r'bloqueado|inadimplente|falta\s+de\s+pagamento': 'CLIENTE_BLOQUEADO',
    r'GNRE|guia\s+GNRE': 'GNRE_OBRIGATORIA',
    r'rejeit': 'SEFAZ_REJEITADO',
    r'n[aã]o\s+autorizado': 'SEFAZ_NAO_AUTORIZADO',
    r'n[aã]o\s+encontrad': 'NAO_ENCONTRADO',
    r'chave.*inv[aá]lid|inv[aá]lid.*chave': 'CHAVE_INVALIDA',
}


class SswEmissaoService:
    """Orquestra emissao de CTe no SSW e importacao dos resultados."""

    @staticmethod
    def preparar_emissao(nf_id, placa, cnpj_tomador, frete_valor,
                         data_vencimento, medidas_motos, usuario):
        """Valida inputs, cria CarviaEmissaoCte, enfileira job RQ.

        Args:
            nf_id: ID da CarviaNf
            placa: Placa coleta (default ARMAZEM)
            cnpj_tomador: CNPJ do tomador para fatura 437
            frete_valor: Valor do frete em R$
            data_vencimento: Data vencimento fatura (date ou None)
            medidas_motos: Lista de [{modelo_id, qtd}] ou None
            usuario: Username do usuario autenticado

        Returns:
            dict com {emissao_id, job_id, status}

        Raises:
            ValueError para inputs invalidos
        """
        from app.carvia.models import CarviaNf, CarviaEmissaoCte

        # 1. Validar NF
        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            raise ValueError(f"NF {nf_id} nao encontrada")
        if nf.status != 'ATIVA':
            raise ValueError(f"NF {nf_id} nao esta ATIVA (status={nf.status})")
        if not nf.chave_acesso_nf or len(nf.chave_acesso_nf) != 44:
            raise ValueError(
                f"NF {nf_id} nao possui chave de acesso valida "
                f"(tem {len(nf.chave_acesso_nf or '')} digitos, precisa 44)"
            )

        # 2. Verificar mutex (emissao em andamento para esta NF)
        em_andamento = CarviaEmissaoCte.query.filter(
            CarviaEmissaoCte.nf_id == nf_id,
            CarviaEmissaoCte.status.in_(['PENDENTE', 'EM_PROCESSAMENTO']),
        ).first()
        if em_andamento:
            raise ValueError(
                f"Ja existe emissao em andamento para NF {nf_id} "
                f"(emissao_id={em_andamento.id}, status={em_andamento.status})"
            )

        # 3. Validar CNPJ tomador (se fornecido)
        cnpj_limpo = None
        if cnpj_tomador:
            cnpj_limpo = re.sub(r'\D', '', cnpj_tomador)
            if len(cnpj_limpo) != 14:
                raise ValueError(f"CNPJ tomador invalido: {cnpj_tomador}")

        # 4. Converter medidas de moto
        medidas_json = None
        if medidas_motos:
            medidas_json = SswEmissaoService.montar_medidas(medidas_motos)

        # 5. Criar registro de emissao
        emissao = CarviaEmissaoCte(
            nf_id=nf_id,
            status='PENDENTE',
            placa=placa or 'ARMAZEM',
            cnpj_tomador=cnpj_limpo,
            frete_valor=frete_valor,
            data_vencimento=data_vencimento if hasattr(data_vencimento, 'strftime') else None,
            medidas_json=medidas_json,
            criado_por=usuario,
        )
        db.session.add(emissao)
        db.session.flush()  # Obter ID

        # 7. Enfileirar job RQ
        from app.portal.workers import enqueue_job
        from app.carvia.workers.ssw_cte_jobs import emitir_cte_ssw_job

        job = enqueue_job(
            emitir_cte_ssw_job,
            emissao.id,
            queue_name='ssw_carvia',
            timeout='10m',
        )
        emissao.job_id = job.id
        db.session.commit()

        logger.info(
            "Emissao CTe SSW enfileirada: emissao_id=%s, nf_id=%s, job_id=%s",
            emissao.id, nf_id, job.id
        )

        return {
            'emissao_id': emissao.id,
            'job_id': job.id,
            'status': 'PENDENTE',
        }

    @staticmethod
    def preparar_emissao_lote(nf_ids, placa, cnpj_tomador, frete_valor,
                              data_vencimento, medidas_motos, usuario):
        """Cria N emissoes individuais na fila RQ (uma por NF).

        Returns:
            list de dicts [{nf_id, emissao_id, status}] ou {nf_id, erro}
        """
        resultados = []
        for nf_id in nf_ids:
            try:
                resultado = SswEmissaoService.preparar_emissao(
                    nf_id=nf_id,
                    placa=placa,
                    cnpj_tomador=cnpj_tomador,
                    frete_valor=frete_valor,
                    data_vencimento=data_vencimento,
                    medidas_motos=medidas_motos,
                    usuario=usuario,
                )
                resultado['nf_id'] = nf_id
                resultados.append(resultado)
            except (ValueError, Exception) as e:
                resultados.append({
                    'nf_id': nf_id,
                    'erro': str(e),
                    'status': 'ERRO',
                })
        return resultados

    @staticmethod
    def montar_medidas(medidas_input):
        """Converte [{modelo_id, qtd}] em [{comp_m, larg_m, alt_m, qtd}].

        Busca CarviaModeloMoto por ID e converte CM para M (/100).

        Args:
            medidas_input: Lista de dicts [{modelo_id: int, qtd: int}]

        Returns:
            Lista de dicts [{comp_m, larg_m, alt_m, qtd}]

        Raises:
            ValueError se modelo nao encontrado ou inativo
        """
        from app.carvia.models import CarviaModeloMoto

        medidas = []
        for item in medidas_input:
            modelo_id = item.get('modelo_id')
            qtd = item.get('qtd', 1)

            if not modelo_id:
                raise ValueError("modelo_id obrigatorio em cada item de medidas")

            modelo = db.session.get(CarviaModeloMoto, modelo_id)
            if not modelo:
                raise ValueError(f"Modelo de moto {modelo_id} nao encontrado")
            if not modelo.ativo:
                raise ValueError(f"Modelo de moto {modelo_id} ({modelo.nome}) esta inativo")

            medidas.append({
                'modelo_id': modelo_id,
                'modelo_nome': modelo.nome,
                'comp_m': round(float(modelo.comprimento) / 100, 3),
                'larg_m': round(float(modelo.largura) / 100, 3),
                'alt_m': round(float(modelo.altura) / 100, 3),
                'qtd': int(qtd),
            })

        return medidas

    @staticmethod
    def detectar_erro_ssw(resultado):
        """Analisa resultado do script para detectar erros SSW conhecidos.

        Verifica em: dialogs[*]['msg'], body do resultado, body da 101.

        Args:
            resultado: dict retornado por emitir_cte() ou gerar_fatura()

        Returns:
            String descritiva do erro ou None se nenhum detectado
        """
        textos_para_verificar = []

        # Coletar dialogs
        for dialog in resultado.get('dialogs', []):
            textos_para_verificar.append(dialog.get('msg', ''))
        for dialog in resultado.get('resultado', {}).get('dialogs', []):
            textos_para_verificar.append(dialog.get('msg', ''))

        # Body da consulta 101
        consulta = resultado.get('consulta_101', {})
        if isinstance(consulta, dict):
            textos_para_verificar.append(consulta.get('body', ''))

        # Body do SEFAZ
        sefaz = resultado.get('sefaz', {})
        if isinstance(sefaz, dict):
            textos_para_verificar.append(sefaz.get('body', ''))

        # Erro explicito
        if resultado.get('erro'):
            textos_para_verificar.append(str(resultado['erro']))

        # Verificar contra padroes conhecidos
        texto_completo = ' '.join(textos_para_verificar).lower()
        for padrao, codigo in ERROS_SSW.items():
            if re.search(padrao, texto_completo, re.IGNORECASE):
                # Extrair contexto (ate 200 chars ao redor do match)
                m = re.search(padrao, texto_completo, re.IGNORECASE)
                start = max(0, m.start() - 50)
                end = min(len(texto_completo), m.end() + 150)
                contexto = texto_completo[start:end].strip()
                return f"{codigo}: {contexto}"

        return None

    @staticmethod
    def importar_resultado_cte(emissao, resultado_cte):
        """Pos-emissao: importa XML do CTe no sistema.

        Se o XML foi baixado (path em resultado), processa via
        ImportacaoService para criar/enriquecer CarviaOperacao.

        Args:
            emissao: CarviaEmissaoCte
            resultado_cte: dict retornado por emitir_cte()
        """
        xml_path = resultado_cte.get('xml')
        if not xml_path:
            # Tentar extrair do consulta_101
            consulta = resultado_cte.get('consulta_101', {})
            if isinstance(consulta, dict):
                xml_path = consulta.get('xml')

        if xml_path and os.path.exists(xml_path):
            emissao.xml_path = xml_path
            try:
                from app.carvia.services.parsers.importacao_service import ImportacaoService
                svc = ImportacaoService()

                # Processar XML como importacao CarVia
                with open(xml_path, 'rb') as f:
                    from werkzeug.datastructures import FileStorage
                    file_storage = FileStorage(
                        stream=f,
                        filename=os.path.basename(xml_path),
                        content_type='text/xml',
                    )
                    resultado_import = svc.processar_arquivos([file_storage])

                # Vincular operacao criada
                if resultado_import and resultado_import.get('operacoes'):
                    ops = resultado_import['operacoes']
                    if ops:
                        emissao.operacao_id = ops[0].id if hasattr(ops[0], 'id') else None
                        logger.info(
                            "CTe XML importado: emissao=%s, operacao=%s",
                            emissao.id, emissao.operacao_id
                        )
            except Exception as e:
                logger.error("Erro ao importar XML CTe: %s", e)
                emissao.erro_ssw = (emissao.erro_ssw or '') + f"\nImport XML: {e}"

        # Salvar path do DACTE se disponivel
        dacte_path = resultado_cte.get('dacte')
        if not dacte_path:
            consulta = resultado_cte.get('consulta_101', {})
            if isinstance(consulta, dict):
                dacte_path = consulta.get('dacte')
        if dacte_path:
            emissao.dacte_path = dacte_path

        db.session.flush()

    @staticmethod
    def importar_resultado_fatura(emissao, resultado_fatura):
        """Pos-fatura: importa PDF da fatura no sistema.

        Processa via ImportacaoService como fatura PDF SSW
        para criar CarviaFaturaCliente.

        Args:
            emissao: CarviaEmissaoCte
            resultado_fatura: dict retornado por gerar_fatura()
        """
        pdf_path = resultado_fatura.get('fatura_pdf')
        if pdf_path and os.path.exists(pdf_path):
            emissao.fatura_pdf_path = pdf_path
            try:
                from app.carvia.services.parsers.importacao_service import ImportacaoService
                svc = ImportacaoService()

                with open(pdf_path, 'rb') as f:
                    from werkzeug.datastructures import FileStorage
                    file_storage = FileStorage(
                        stream=f,
                        filename=os.path.basename(pdf_path),
                        content_type='application/pdf',
                    )
                    resultado_import = svc.processar_arquivos([file_storage])

                logger.info(
                    "Fatura PDF importada: emissao=%s, fatura=%s",
                    emissao.id, emissao.fatura_numero
                )
            except Exception as e:
                logger.error("Erro ao importar PDF fatura: %s", e)
                emissao.erro_ssw = (emissao.erro_ssw or '') + f"\nImport Fatura: {e}"

        db.session.flush()

