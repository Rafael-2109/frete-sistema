"""
DACTE Generator Service — Gera PDF de DACTE a partir de CT-e XML
================================================================

Fluxo: XML bytes → CTeXMLParserCarvia → template HTML → WeasyPrint → PDF bytes

Fallback: Se nao tem XML, gera representacao simplificada com dados do banco.
"""

import logging
from io import BytesIO
from typing import Optional

from flask import render_template

logger = logging.getLogger(__name__)


class DacteGeneratorService:
    """Gera DACTE PDF para operacoes e subcontratos CarVia"""

    def gerar_dacte_pdf(self, tipo: str, entity_id: int) -> bytes:
        """Gera PDF do DACTE para uma entidade CarVia.

        Args:
            tipo: 'operacao' ou 'subcontrato'
            entity_id: ID da entidade

        Returns:
            bytes do PDF gerado

        Raises:
            ValueError: se entidade nao encontrada
        """
        from weasyprint import HTML

        # Tentar extrair dados do XML primeiro
        dados = self._extrair_dados_xml(tipo, entity_id)
        simplificado = False

        if dados is None:
            # Fallback: dados do banco
            dados = self._extrair_dados_banco(tipo, entity_id)
            simplificado = True

        # Gerar barcode SVG da chave de acesso
        barcode_svg = ''
        chave = dados.get('cte_chave_acesso') or ''
        if len(chave) == 44:
            barcode_svg = self._gerar_barcode_svg(chave)
            dados['chave_formatada'] = self._formatar_chave_acesso(chave)
        else:
            dados['chave_formatada'] = chave or ''

        # Renderizar HTML
        html_content = render_template(
            'carvia/dacte_pdf.html',
            dados=dados,
            barcode_svg=barcode_svg,
            simplificado=simplificado,
        )

        # Gerar PDF
        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)

        return pdf_buffer.getvalue()

    def _extrair_dados_xml(self, tipo: str, entity_id: int) -> Optional[dict]:
        """Extrai dados do XML armazenado no storage.

        Returns:
            dict com dados DACTE ou None se XML indisponivel
        """
        entity = self._buscar_entidade(tipo, entity_id)
        xml_path = getattr(entity, 'cte_xml_path', None)

        if not xml_path:
            return None

        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()
            xml_bytes = storage.download_file(xml_path)

            if not xml_bytes:
                logger.warning(
                    f"XML nao encontrado no storage para {tipo} {entity_id}: {xml_path}"
                )
                return None

            from app.carvia.services.cte_xml_parser_carvia import CTeXMLParserCarvia
            parser = CTeXMLParserCarvia(xml_bytes)
            dados = parser.get_todas_informacoes_dacte()

            # Garantir que temos a chave de acesso
            if not dados.get('cte_chave_acesso') and hasattr(entity, 'cte_chave_acesso'):
                dados['cte_chave_acesso'] = entity.cte_chave_acesso

            return dados

        except Exception as e:
            logger.error(f"Erro ao parsear XML do {tipo} {entity_id}: {e}")
            return None

    def _extrair_dados_banco(self, tipo: str, entity_id: int) -> dict:
        """Extrai dados disponiveis no banco para DACTE simplificado.

        Returns:
            dict com dados basicos da entidade
        """
        entity = self._buscar_entidade(tipo, entity_id)

        dados = {
            'cte_numero': getattr(entity, 'cte_numero', None),
            'cte_chave_acesso': getattr(entity, 'cte_chave_acesso', None),
            'cte_valor': getattr(entity, 'cte_valor', None),
            'cte_data_emissao': (
                entity.cte_data_emissao.strftime('%Y-%m-%dT%H:%M:%S')
                if getattr(entity, 'cte_data_emissao', None)
                else None
            ),
            'tipo_cte': None,
            'tipo_cte_descricao': 'Normal',
            # Participantes basicos
            'emitente': {},
            'remetente': {},
            'destinatario': {},
            # NFs
            'nfs_referenciadas': [],
            # Impostos
            'impostos': {},
            # Campos extras vazios
            'serie': None,
            'cfop': None,
            'natureza_operacao': None,
            'modal': None,
            'forma_pagamento': None,
            'protocolo': {},
            'tomador': {},
            'endereco_emitente': {},
            'endereco_remetente': {},
            'endereco_destinatario': {},
            'ie_emitente': None,
            'ie_remetente': None,
            'ie_destinatario': None,
            'componentes_prestacao': [],
            'produto_predominante': None,
            'quantidades_carga': [],
            'observacoes_complementares': None,
            'info_adicional_fisco': None,
        }

        if tipo == 'operacao':
            dados.update({
                'uf_origem': entity.uf_origem,
                'cidade_origem': entity.cidade_origem,
                'uf_destino': entity.uf_destino,
                'cidade_destino': entity.cidade_destino,
                'valor_mercadoria': float(entity.valor_mercadoria) if entity.valor_mercadoria else None,
                'peso_bruto': float(entity.peso_bruto) if entity.peso_bruto else None,
                'peso_cubado': float(entity.peso_cubado) if entity.peso_cubado else None,
            })
            dados['remetente'] = {
                'cnpj': entity.cnpj_cliente,
                'nome': entity.nome_cliente,
            }
        elif tipo == 'subcontrato':
            operacao = entity.operacao if hasattr(entity, 'operacao') else None
            if operacao:
                dados.update({
                    'uf_origem': operacao.uf_origem,
                    'cidade_origem': operacao.cidade_origem,
                    'uf_destino': operacao.uf_destino,
                    'cidade_destino': operacao.cidade_destino,
                    'valor_mercadoria': float(operacao.valor_mercadoria) if operacao.valor_mercadoria else None,
                    'peso_bruto': float(operacao.peso_bruto) if operacao.peso_bruto else None,
                    'peso_cubado': float(operacao.peso_cubado) if operacao.peso_cubado else None,
                })

            if entity.transportadora:
                dados['emitente'] = {
                    'cnpj': entity.transportadora.cnpj,
                    'nome': entity.transportadora.razao_social,
                }

        return dados

    def _buscar_entidade(self, tipo: str, entity_id: int):
        """Busca entidade no banco por tipo e ID.

        Raises:
            ValueError: se tipo invalido ou entidade nao encontrada
        """
        from app import db

        if tipo == 'operacao':
            from app.carvia.models import CarviaOperacao
            entity = db.session.get(CarviaOperacao, entity_id)
            if not entity:
                raise ValueError(f'Operacao {entity_id} nao encontrada')
        elif tipo == 'subcontrato':
            from app.carvia.models import CarviaSubcontrato
            entity = db.session.get(CarviaSubcontrato, entity_id)
            if not entity:
                raise ValueError(f'Subcontrato {entity_id} nao encontrada')
        else:
            raise ValueError(f'Tipo invalido: {tipo}. Use "operacao" ou "subcontrato"')

        return entity

    def _gerar_barcode_svg(self, chave_acesso: str) -> str:
        """Gera barcode Code128 como SVG inline para a chave de acesso.

        Args:
            chave_acesso: String de 44 digitos

        Returns:
            String SVG do barcode
        """
        try:
            import barcode
            from barcode.writer import SVGWriter

            code128 = barcode.get('code128', chave_acesso, writer=SVGWriter())
            svg_buffer = BytesIO()
            code128.write(svg_buffer, options={
                'module_width': 0.2,
                'module_height': 8,
                'write_text': False,
                'quiet_zone': 1,
            })
            svg_buffer.seek(0)
            return svg_buffer.read().decode('utf-8')

        except Exception as e:
            logger.warning(f"Erro ao gerar barcode para chave {chave_acesso[:10]}...: {e}")
            return ''

    @staticmethod
    def _formatar_chave_acesso(chave: str) -> str:
        """Formata chave de acesso em blocos de 4 digitos.

        Args:
            chave: String de 44 digitos

        Returns:
            String formatada: '1234 5678 9012 ...'
        """
        if not chave:
            return ''
        return ' '.join(chave[i:i + 4] for i in range(0, len(chave), 4))

    @staticmethod
    def _formatar_cnpj(cnpj: str) -> str:
        """Formata CNPJ para exibicao: XX.XXX.XXX/XXXX-XX"""
        if not cnpj:
            return ''
        digits = ''.join(c for c in cnpj if c.isdigit())
        if len(digits) == 14:
            return (
                f'{digits[:2]}.{digits[2:5]}.{digits[5:8]}'
                f'/{digits[8:12]}-{digits[12:]}'
            )
        return cnpj

    @staticmethod
    def _formatar_valor(valor) -> str:
        """Formata valor para exibicao no formato brasileiro.

        Args:
            valor: float ou None

        Returns:
            String formatada: '1.234,56'
        """
        if valor is None:
            return '0,00'
        try:
            valor_f = float(valor)
            # Separador de milhar com ponto, decimal com virgula
            inteiro = int(valor_f)
            decimal = abs(valor_f - inteiro)
            parte_decimal = f'{decimal:.2f}'[2:]  # '0.56' -> '56'
            parte_inteira = f'{inteiro:,}'.replace(',', '.')
            return f'{parte_inteira},{parte_decimal}'
        except (ValueError, TypeError):
            return '0,00'
