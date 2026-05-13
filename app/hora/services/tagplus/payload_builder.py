"""Tradutor HoraVenda -> JSON do POST /nfes do TagPlus.

Schema da API: scripts/doc_tagplus.md:142-489.
Detalhes do desenho: app/hora/EMISSAO_NFE_ENGENHARIA.md secao 4.

Responsabilidades:
1. Resolver destinatario (GET /clientes ou POST /clientes).
2. Montar itens[] com chassi/motor em "detalhes" do item (linha do DANFE).
3. Montar faturas[] via HoraTagPlusFormaPagamentoMap.
4. CFOP por UF (5.403 intra / 6.403 inter — venda de mercadoria com ST,
   contribuinte substituido. Mascara obrigatoria 9.999).
5. Sanitizar (Decimal -> float, arredondar para 2 casas).
"""
from __future__ import annotations

import logging
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from app.hora.models.tagplus import (
    HoraTagPlusConta,
    HoraTagPlusFormaPagamentoMap,
    HoraTagPlusProdutoMap,
)
from app.hora.services.tagplus.api_client import ApiClient
from app.utils.timezone import agora_utc_naive

if TYPE_CHECKING:
    from app.hora.models.venda import HoraVenda

logger = logging.getLogger(__name__)


class PayloadBuilderError(Exception):
    """Erro de pre-condicao no payload (cliente ambiguo, mapa ausente, etc.)."""

    def __init__(self, code: str, message: str):
        super().__init__(f'[{code}] {message}')
        self.code = code
        self.message = message


class PayloadBuilder:
    """Monta payload completo do POST /nfes a partir de HoraVenda."""

    def __init__(self, conta: HoraTagPlusConta):
        self.conta = conta
        self.api = ApiClient(conta)
        # Cache de lookups de cidade — POR INSTANCIA. Antes era class-level
        # (mutavel compartilhada entre todos os PayloadBuilder do processo)
        # e cacheava `None` em falha transiente, envenenando emissoes
        # subsequentes para a mesma cidade. Ver R1 do code review 2026-04-30.
        self._cache_id_cidade: dict[tuple[str, str], int | None] = {}

    # --------------------------------------------------------------
    # Public
    # --------------------------------------------------------------
    def build(self, venda: 'HoraVenda') -> dict:
        if not venda.itens and not getattr(venda, 'itens_peca', []):
            raise PayloadBuilderError('venda_sem_itens', 'Venda sem itens (motos nem pecas).')

        # Multi-formas (migration hora_34, 2026-05-07): se venda tem
        # `pagamentos`, valida e usa essa lista. Senao, fallback ao campo
        # legacy `venda.forma_pagamento` (1 forma unica).
        pagamentos_lista = list(getattr(venda, 'pagamentos', []) or [])
        if pagamentos_lista:
            # Validacao de coerencia: soma == valor_total.
            soma_pag = sum(
                (Decimal(str(p.valor)) for p in pagamentos_lista),
                Decimal('0'),
            )
            valor_total_dec = Decimal(str(venda.valor_total or 0))
            if abs(soma_pag - valor_total_dec) > Decimal('0.01'):
                raise PayloadBuilderError(
                    'pagamentos_soma_divergente',
                    f'Soma dos pagamentos (R$ {soma_pag}) difere do valor total '
                    f'(R$ {valor_total_dec}). Pedido em status incompleto.'
                )
        else:
            if venda.forma_pagamento in (None, '', 'NAO_INFORMADO'):
                raise PayloadBuilderError(
                    'forma_pagamento_ausente',
                    'Forma de pagamento nao informada — preencher antes de emitir.'
                )
            if venda.forma_pagamento == 'MISTO':
                raise PayloadBuilderError(
                    'pagamento_misto_legacy',
                    'Venda legacy marcada como MISTO sem detalhamento — '
                    'editar pagamentos antes de emitir.'
                )

        destinatario_id = self._resolver_destinatario(venda)

        cliente_uf = self._consultar_uf_cliente(destinatario_id)
        emitente_uf = self._uf_emitente(venda)
        cfop = self._cfop_por_uf(cliente_uf, emitente_uf, venda)

        itens = self._montar_itens(venda)
        faturas = self._montar_faturas(venda)

        loja_label = self._loja_label(venda)
        # Soma motos + pecas em valor_desconto e valor_nota.
        # Pecas: desconto_aplicado e POR UNIDADE; preco_final e o TOTAL da linha.
        valor_desconto = sum(
            (i.desconto_aplicado or Decimal('0') for i in venda.itens),
            Decimal('0'),
        ) + sum(
            (
                (Decimal(str(p.desconto_aplicado or 0)) * Decimal(str(p.qtd)))
                for p in (getattr(venda, 'itens_peca', []) or [])
            ),
            Decimal('0'),
        )
        valor_nota = sum(
            (i.preco_final for i in venda.itens),
            Decimal('0'),
        ) + sum(
            (Decimal(str(p.preco_final or 0)) for p in (getattr(venda, 'itens_peca', []) or [])),
            Decimal('0'),
        )

        # ----------------------------------------------------------
        # INVARIANTE: faturamento SEMPRE pela MATRIZ HORA.
        # ----------------------------------------------------------
        # Regra de negocio (2026-04-27): toda NFe da Lojas HORA sai com o CNPJ
        # da MATRIZ, mesmo que a venda fisica tenha sido feita em uma filial.
        # `loja_label` no `inf_contribuinte` apenas RASTREIA a loja fisica para
        # fins gerenciais; o emitente fiscal e a matriz.
        #
        # Implementacao: NAO incluir o campo `emitente` no payload. Conforme
        # `scripts/doc_tagplus.md`, o TagPlus usa automaticamente o emitente
        # padrao configurado na conta OAuth (singleton `HoraTagPlusConta`).
        # Como existe apenas 1 conta ativa no sistema, esse emitente padrao =
        # CNPJ da matriz cadastrado no portal TagPlus.
        #
        # NAO ADICIONAR `'emitente': ...` ou `'endereco_emitente': ...` aqui
        # ou em qualquer outro callsite. Multi-emitente NAO E SUPORTADO por
        # design — qualquer mudanca neste comportamento exige aprovacao
        # explicita do dono fiscal da HORA.
        # consumidor_final (TagPlus boolean — doc:320-322):
        # REGRA DE NEGOCIO (2026-05-07): 100% das NFe da Lojas HORA saem com
        # consumidor_final=True, independentemente de PF/PJ no destinatario.
        # Decisao do dono fiscal HORA (rafael6250@gmail.com). Substitui o
        # comportamento anterior que inferia via tipo de documento ou usava
        # venda.consumidor_final.
        # A coluna hora_venda.consumidor_final continua existindo (migration
        # hora_36) mas e ignorada — fica vestigial para retrocompat de dados
        # legados. Nao remover sem migration de drop coordenada.

        payload = {
            'tipo': 'S',
            'finalidade_emissao': 1,            # Normal (CONFIRMAR fiscal HORA — ver §15.1).
            'consumidor_final': True,
            'indicador_presenca': 1,            # Presencial (loja fisica).
            'tipo_emissao': 1,                  # Normal (nao contingencia).
            # TagPlus exige string ('0'-'4', '9') conforme doc:258-272.
            # venda.modalidade_frete tem default '9' (sem ocorrencia).
            'modalidade_frete': str(venda.modalidade_frete or '9'),
            # indicador_forma_pagamento (doc:3201-3205):
            #   0 = a vista (1 parcela), 1 = a prazo (>= 2 parcelas), 2 = outros.
            # Sem isso, TagPlus assume default 0 mesmo com parcelado, causando
            # divergencia na NFe (<pag><detPag><indPag> da SEFAZ).
            'indicador_forma_pagamento': 1 if (venda.numero_parcelas or 1) > 1 else 0,
            'data_emissao': agora_utc_naive().isoformat(timespec='seconds'),
            'data_entrada_saida': date.today().isoformat(),
            'cfop': cfop,                       # mascara 9.999 obrigatoria.
            'destinatario': destinatario_id,
            'itens': itens,
            'faturas': faturas,
            'valor_desconto': self._round2_float(valor_desconto),
            'valor_nota': self._round2_float(valor_nota),
            'inf_contribuinte': self._montar_inf_contribuinte(venda, loja_label),
            'numero_pedido': str(venda.id),
        }
        return payload

    # --------------------------------------------------------------
    # Informacoes complementares (inf_contribuinte)
    # --------------------------------------------------------------
    def _montar_inf_contribuinte(self, venda: 'HoraVenda', loja_label: str) -> str:
        """Monta o texto de `inf_contribuinte` (Informacoes Complementares).

        Estrutura (definida pelo dono fiscal HORA em 2026-05-13):

            Modelo: <nome> - <Autopropelido|Ciclomotor>
            Cor: <cor>
            Chassi: <chassi>

            (uma vez por item moto, na ordem do pedido)

            AUTOPROPELIDO:
            <bloco fixo de garantia e CONTRAN 996/2023>
            (exibido 1x se ha qualquer moto autopropelido=True)

            CICLOMOTOR:
            <bloco fixo de garantia, CNH e ATPV>
            (exibido 1x se ha qualquer moto autopropelido=False)

            Venda #<id> | Loja: <label> | Vendedor: <nome>
            (rastreio interno — mantido para auditoria gerencial)

        Pecas (HoraVendaItem peca, `venda.itens_peca`) NAO entram aqui — a
        spec cobre exclusivamente os itens-moto.

        Limite SEFAZ para `inf_contribuinte`: 5000 caracteres
        (TNFe v4.0 — `xCorpo` do `infCpl`). Loga warning se exceder.
        """
        partes: list[str] = []

        # 1) Lista de motos (Modelo / Cor / Chassi) — itera apenas itens-moto.
        tem_autopropelido = False
        tem_ciclomotor = False
        for vi in venda.itens:
            moto = vi.moto
            modelo_obj = moto.modelo if moto else None
            nome_modelo = (
                (modelo_obj.nome_modelo if modelo_obj else None)
                or '-'
            )
            # Default seguro: assume Autopropelido se o atributo nao existir
            # (modelos antigos antes da migration hora_41). Apos a migration
            # o campo e NOT NULL com DEFAULT TRUE.
            autop = bool(getattr(modelo_obj, 'autopropelido', True)) if modelo_obj else True
            rotulo_tipo = 'Autopropelido' if autop else 'Ciclomotor'
            if autop:
                tem_autopropelido = True
            else:
                tem_ciclomotor = True

            cor = (moto.cor if moto else None) or '-'
            chassi = vi.numero_chassi or '-'

            partes.append(f'Modelo: {nome_modelo} - {rotulo_tipo}')
            partes.append(f'Cor: {cor}')
            partes.append(f'Chassi: {chassi}')
            partes.append('')  # linha em branco entre motos

        # 2) Avisos por categoria — exibidos UMA vez cada, na ordem.
        if tem_autopropelido:
            partes.append('AUTOPROPELIDO:')
            partes.append('')
            partes.append(
                'GARANTIA CONTRA DEFEITOS DE FABRICACAO DE 6 MESES E 6 MESES '
                'DE GARANTIA ADICIONAL NO MOTOR, BATERIA E MODULO ELETRICO.'
            )
            partes.append('')
            partes.append(
                'VEICULO AUTOPROPELIDO/BICICLETA ELETRICA, CONFORME RESOLUCAO '
                '996/2023 CONTRAN, DISPENSA USO DE CNH E LICENCIAMENTO.'
            )
            partes.append('')

        if tem_ciclomotor:
            partes.append('CICLOMOTOR:')
            partes.append('')
            partes.append(
                'GARANTIA CONTRA DEFEITOS DE FABRICACAO DE 3 MESES E 9 MESES '
                'DE GARANTIA ADICIONAL NO MOTOR, BATERIA E MODULO ELETRICO'
            )
            partes.append('')
            partes.append('VEICULO CICLOMOTOR REQUER CNH E EMPLACAMENTO')
            partes.append('ATPV a ser emitido em ate 15 dias uteis da emissao da NF')
            partes.append('')

        # 3) Rastreio interno — sempre por ultimo, para nao atrapalhar a leitura
        #    fiscal do cliente. Mantem auditoria gerencial existente.
        partes.append(
            f'Venda #{venda.id} | Loja: {loja_label} | '
            f'Vendedor: {venda.vendedor or "-"}'
        )

        texto = '\n'.join(partes).rstrip()

        # Defesa-em-profundidade: SEFAZ aceita ate 5000 chars em xCorpo do infCpl.
        # Truncar e perigoso (corta texto fiscal) — preferimos log de warning
        # para detectar antes que vire problema em producao.
        if len(texto) > 5000:
            logger.warning(
                'inf_contribuinte da venda %s tem %d caracteres (>5000) — '
                'SEFAZ pode rejeitar. Revisar itens da venda.',
                venda.id, len(texto),
            )
        return texto

    # --------------------------------------------------------------
    # Destinatario (cliente TagPlus)
    # --------------------------------------------------------------
    def _resolver_destinatario(self, venda: 'HoraVenda') -> int:
        # Aceita PF (CPF, 11) ou PJ (CNPJ, 14). doc_tagplus.md:716-744
        # confirma que schema do Cliente expoe campos `cpf` E `cnpj` separados;
        # TagPlus discrimina PF/PJ por `tipo` ('F'/'J').
        from app.hora.services.tagplus._documento import (
            TIPO_CNPJ, normalizar_documento,
        )
        documento, tipo_doc = normalizar_documento(venda.cpf_cliente)
        if not tipo_doc:
            raise PayloadBuilderError(
                'cpf_invalido',
                f'Documento invalido na venda {venda.id}: '
                f'{venda.cpf_cliente!r} (esperado CPF com 11 ou CNPJ com 14 digitos)',
            )
        # Mantem nome de variavel `cpf` no resto da funcao para minimizar
        # diff — semanticamente eh "documento" (CPF ou CNPJ).
        cpf = documento
        is_pj = tipo_doc == TIPO_CNPJ

        # 1) Localizar via busca livre + match local exato.
        # NF #727 (venda #2, 2026-04-28) confirmou via response do POST /nfes que:
        #   - Em GET /clientes, cada objeto tem `id` (id_cliente) E `id_entidade`.
        #   - O campo `destinatario` do POST /nfes espera `id_entidade` (e NAO id_cliente).
        #     Comprovacao: response da NFe mostra "destinatario.id" = id_entidade do
        #     cliente, e "cliente.id"=654 vs "cliente.id_entidade"=674.
        #   - O matching anterior pegou um cliente com CPF DIFERENTE — bug de
        #     filtro local. Agora validamos CPF byte-a-byte pos-match.
        r = self.api.get(
            '/clientes',
            params={'q': cpf, 'fields': '*', 'per_page': 30},
        )
        if r.status_code == 200:
            try:
                resultados = r.json()
            except ValueError:
                resultados = []
            # Log do payload cru — fundamental para auditar matchings duvidosos.
            logger.info(
                'TagPlus GET /clientes?q=%s status=%s body_type=%s '
                'count_raw=%s',
                cpf, r.status_code, type(resultados).__name__,
                len(resultados) if isinstance(resultados, list) else
                (len(resultados.keys()) if isinstance(resultados, dict) else 0),
            )
            if isinstance(resultados, dict):
                resultados = (
                    resultados.get('data')
                    or resultados.get('clientes')
                    or resultados.get('results')
                    or []
                )

            # Match LOCAL exato pelo CPF (sanitizado para digitos), defesa contra
            # LIKE pegar match parcial em telefone/RG/codigo.
            matches: list[dict] = []
            if isinstance(resultados, list):
                for item in resultados:
                    if not isinstance(item, dict):
                        continue
                    raw = (
                        item.get('cpf')
                        or item.get('cpf_cnpj')
                        or item.get('cnpj')
                        or ''
                    )
                    if self._so_digitos(raw) == cpf:
                        matches.append(item)

            # Log de cada candidato bruto retornado pelo TagPlus (nao apenas matches).
            # Critico para investigar quando o match pega cliente de CPF diferente.
            for raw_item in (resultados if isinstance(resultados, list) else []):
                if isinstance(raw_item, dict):
                    logger.info(
                        'TagPlus /clientes?q=%s candidato: id=%r id_entidade=%r '
                        'cpf=%r cpf_cnpj=%r razao_social=%r codigo=%r tipo=%r',
                        cpf,
                        raw_item.get('id'),
                        raw_item.get('id_entidade'),
                        raw_item.get('cpf'),
                        raw_item.get('cpf_cnpj'),
                        raw_item.get('razao_social') or raw_item.get('nome'),
                        raw_item.get('codigo'),
                        raw_item.get('tipo'),
                    )

            if len(matches) == 1:
                m = matches[0]
                # Defesa-em-profundidade: revalidar CPF byte-a-byte. Apos NF #727
                # ter sido emitida para Dercio (CPF 500.685.551-72) quando o CPF
                # da venda era 393.754.958-76, NAO confiamos somente no filtro
                # acima — re-checamos antes de retornar o ID.
                cpf_match = self._so_digitos(
                    m.get('cpf') or m.get('cpf_cnpj') or m.get('cnpj') or ''
                )
                if cpf_match != cpf:
                    rotulo_doc = 'CNPJ' if is_pj else 'CPF'
                    logger.error(
                        'TagPlus _resolver_destinatario MATCH INVALIDO: '
                        '%s venda=%s != documento retornado=%s. Match=%r',
                        rotulo_doc, cpf, cpf_match, m,
                    )
                    raise PayloadBuilderError(
                        'cliente_match_invalido',
                        f'GET /clientes?q={cpf} retornou cliente com '
                        f'documento {cpf_match!r} (esperado {rotulo_doc} '
                        f'{cpf!r}). '
                        f'Match candidato: id={m.get("id")} '
                        f'id_entidade={m.get("id_entidade")} '
                        f'razao_social={m.get("razao_social") or m.get("nome")!r}. '
                        f'Investigar duplicidade/colisao no TagPlus.',
                    )

                # `destinatario` do POST /nfes espera SEMPRE o id_entidade.
                # id_cliente e id_entidade sao ID-spaces SEPARADOS no TagPlus —
                # confundi-los gera emissao para pessoa errada (NF #727 emitida
                # para Dercio quando destinatario era Rafael).
                #
                # Se o objeto retornado em GET /clientes nao expoe id_entidade,
                # fazemos follow-up GET /clientes/{id_cliente} para resolver.
                id_entidade = m.get('id_entidade')
                if not id_entidade and m.get('id'):
                    id_entidade = self._resolver_id_entidade(int(m['id']))
                if not id_entidade:
                    raise PayloadBuilderError(
                        'cliente_sem_id_entidade',
                        f'Cliente CPF={cpf} id_cliente={m.get("id")} sem '
                        f'id_entidade nem direto nem em GET /clientes/{{id}}. '
                        f'Match: {m!r}',
                    )
                logger.info(
                    'TagPlus _resolver_destinatario: cpf=%s id_cliente=%s '
                    'id_entidade=%s (destinatario) razao_social=%r',
                    cpf, m.get('id'), id_entidade,
                    m.get('razao_social') or m.get('nome'),
                )
                return int(id_entidade)
            if len(matches) > 1:
                rotulo_doc = 'CNPJ' if is_pj else 'CPF'
                raise PayloadBuilderError(
                    'destinatario_ambiguo',
                    f'{rotulo_doc} {cpf} encontrado em {len(matches)} clientes '
                    f'no TagPlus (IDs: '
                    f'{[(m.get("id"), m.get("id_entidade")) for m in matches]}). '
                    f'Resolver manualmente no portal antes de emitir.',
                )
            # 0 matches -> nao existe ainda, criar via POST abaixo.

        # 2) Cria.
        # Schema TagPlus Cliente (doc_tagplus.md:506-525, 716-744): apenas
        # campos confirmados sao enviados (TagPlus retorna 422 com "Campo
        # adicional nao permitido" se enviar campos fora do schema).
        # Campos do schema: tipo, razao_social, cpf, cnpj, ativo, codigo,
        # exterior, enderecos[].
        # tipo='F' (PF) usa cpf; tipo='J' (PJ) usa cnpj.
        # NAO ENVIAR: nome (use razao_social), email/telefone (nao confirmados
        # no schema de Cliente embutido na resposta da NFe — sao campos de
        # Funcionario/Vendedor, nao Cliente).
        body: dict = {
            'tipo': 'J' if is_pj else 'F',
            'razao_social': (venda.nome_cliente or '').strip(),
        }
        if is_pj:
            body['cnpj'] = cpf
        else:
            body['cpf'] = cpf

        # Endereco do destinatario — exigido pela SEFAZ na emissao.
        # Vendas DANFE legacy nao tem endereco (parser nao extrai). Vendas
        # criadas via /tagplus/pedido-venda/novo trazem todos os campos.
        endereco = self._montar_endereco_principal(venda)
        if endereco:
            body['enderecos'] = [endereco]

        r2 = self.api.post('/clientes', json=body)
        if r2.status_code in (200, 201):
            try:
                created = r2.json()
            except ValueError:
                created = {}

            id_cliente = None
            id_entidade = None
            if isinstance(created, dict):
                id_cliente = created.get('id')
                id_entidade = created.get('id_entidade')
                logger.info(
                    'TagPlus POST /clientes criou: id=%r id_entidade=%r '
                    'razao_social=%r tipo=%s documento=%r',
                    id_cliente, id_entidade,
                    created.get('razao_social') or created.get('nome'),
                    'J' if is_pj else 'F',
                    created.get('cnpj') if is_pj
                    else (created.get('cpf') or created.get('cpf_cnpj')),
                )

            if not id_entidade and id_cliente:
                id_entidade = self._resolver_id_entidade(int(id_cliente))

            if id_entidade:
                logger.info(
                    'TagPlus cliente novo tipo=%s documento=%s id_cliente=%s '
                    'id_entidade=%s (destinatario)',
                    'J' if is_pj else 'F', cpf, id_cliente, id_entidade,
                )
                return int(id_entidade)

            raise PayloadBuilderError(
                'cliente_criado_sem_id_entidade',
                f'POST /clientes status {r2.status_code} criou id_cliente={id_cliente} '
                f'mas nao retornou id_entidade nem direto nem via GET. '
                f'Body: {r2.text[:200]}',
            )
        raise PayloadBuilderError(
            'falha_criar_cliente',
            f'POST /clientes status {r2.status_code}: {r2.text[:300]}',
        )

    def _montar_endereco_principal(self, venda: 'HoraVenda') -> dict | None:
        """Monta dict de endereco para POST /clientes conforme schema TagPlus.

        Schema confirmado em doc_tagplus.md:984-1000 (object endereco):
            principal, exterior, cep, logradouro, numero, complemento,
            bairro, id_cidade (integer), pais, informacoes_adicionais,
            tipo_cadastro, id_entidade, id_endereco_entidade.

        `id_cidade` (integer) e o campo correto para localidade — TagPlus NAO
        aceita strings cidade/UF diretas. Resolvemos via lookup `/cidades?q=`
        com match local por nome+UF e cache de sessao.

        Retorna None se faltar dados minimos (CEP + logradouro + cidade + UF).
        Se lookup de id_cidade falhar, ainda retorna o endereco (TagPlus pode
        deduzir pelo CEP em alguns casos) com a cidade/UF em
        `informacoes_adicionais` como fallback.
        """
        cep = (venda.cep or '').strip()
        logradouro = (venda.endereco_logradouro or '').strip()
        cidade = (venda.endereco_cidade or '').strip()
        uf = (venda.endereco_uf or '').strip().upper()
        if not (cep and logradouro and cidade and uf):
            return None

        # CEP: TagPlus aceita formato livre, mas idiomatico com mascara.
        cep_digits = ''.join(c for c in cep if c.isdigit())
        cep_formatado = (
            f'{cep_digits[:5]}-{cep_digits[5:]}' if len(cep_digits) == 8 else cep
        )

        endereco: dict = {
            'principal': True,
            'cep': cep_formatado,
            'logradouro': logradouro,
            'numero': (venda.endereco_numero or '').strip() or 'S/N',
            'complemento': (venda.endereco_complemento or '').strip() or None,
            'bairro': (venda.endereco_bairro or '').strip() or None,
        }

        # Resolver id_cidade via /cidades. Sem id_cidade o endereco fica
        # incompleto (campo do schema), entao e tentativa best-effort.
        id_cidade = self._resolver_id_cidade(cidade, uf)
        if id_cidade:
            endereco['id_cidade'] = id_cidade
        else:
            # Fallback: cidade/UF em texto livre (TagPlus pode deduzir pelo CEP).
            endereco['informacoes_adicionais'] = f'{cidade}/{uf}'
            logger.warning(
                'Endereco sem id_cidade resolvido (cidade=%r uf=%s) — '
                'enviando informacoes_adicionais como fallback',
                cidade, uf,
            )

        return {k: v for k, v in endereco.items() if v is not None}

    def _resolver_id_cidade(self, cidade: str, uf: str) -> int | None:
        """Lookup `GET /cidades?q=<cidade>` com match local por nome+UF.

        Retorna `id` do TagPlus para o par (cidade, UF) ou None se nao achar.
        Cacheia por instancia para evitar lookups repetidos no mesmo build.
        """
        chave = (cidade.strip().upper(), uf.strip().upper())
        if chave in self._cache_id_cidade:
            return self._cache_id_cidade[chave]

        try:
            r = self.api.get('/cidades', params={'q': cidade, 'per_page': 50})
        except Exception as exc:
            logger.warning('Falha em GET /cidades?q=%r: %s', cidade, exc)
            self._cache_id_cidade[chave] = None
            return None

        if r.status_code != 200:
            logger.warning(
                'GET /cidades?q=%r status=%s body=%s',
                cidade, r.status_code, r.text[:200],
            )
            self._cache_id_cidade[chave] = None
            return None

        try:
            resultados = r.json()
        except ValueError:
            resultados = []
        if isinstance(resultados, dict):
            resultados = (
                resultados.get('data')
                or resultados.get('cidades')
                or resultados.get('results')
                or []
            )

        # Match local: nome igual + UF igual. Tenta varios nomes de campo
        # para UF (uf, sigla_uf, estado.sigla) por defesa.
        cidade_norm = cidade.strip().upper()
        uf_norm = uf.strip().upper()
        for item in resultados if isinstance(resultados, list) else []:
            if not isinstance(item, dict):
                continue
            nome_item = (item.get('nome') or item.get('descricao') or '').strip().upper()
            uf_item = (
                item.get('uf')
                or item.get('sigla_uf')
                or (item.get('estado') or {}).get('sigla')
                or (item.get('estado') or {}).get('uf')
                or ''
            )
            uf_item = (uf_item or '').strip().upper()
            if nome_item == cidade_norm and uf_item == uf_norm:
                cid = item.get('id')
                if cid is not None:
                    self._cache_id_cidade[chave] = int(cid)
                    return int(cid)

        self._cache_id_cidade[chave] = None
        return None

    def _resolver_id_entidade(self, id_cliente: int) -> int | None:
        """Faz GET /clientes/{id_cliente} para extrair id_entidade.

        TagPlus tem ID-spaces separados: id_cliente (path REST) e id_entidade
        (referencia em NFe.destinatario, vendedor.id_entidade, etc.). O search
        em GET /clientes pode nao expor id_entidade no objeto resumido — entao
        fazemos um GET completo do recurso para resolver.
        """
        try:
            r = self.api.get(f'/clientes/{id_cliente}')
        except Exception as exc:
            logger.warning(
                'GET /clientes/%s falhou: %s', id_cliente, exc,
            )
            return None
        if r.status_code != 200:
            logger.warning(
                'GET /clientes/%s status=%s body=%s',
                id_cliente, r.status_code, r.text[:200],
            )
            return None
        try:
            data = r.json() or {}
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        id_ent = data.get('id_entidade')
        logger.info(
            'TagPlus _resolver_id_entidade: id_cliente=%s -> id_entidade=%r '
            '(razao_social=%r cpf=%r)',
            id_cliente, id_ent,
            data.get('razao_social') or data.get('nome'),
            data.get('cpf') or data.get('cpf_cnpj'),
        )
        return int(id_ent) if id_ent else None

    def _consultar_uf_cliente(self, cliente_id: int) -> str | None:
        try:
            r = self.api.get(f'/clientes/{cliente_id}')
            if r.status_code == 200:
                data = r.json() or {}
                # TagPlus expoe enderecos[] ou endereco principal.
                if isinstance(data.get('enderecos'), list) and data['enderecos']:
                    return (data['enderecos'][0].get('uf') or '').upper() or None
                return (data.get('uf') or '').upper() or None
        except Exception as exc:
            logger.warning('Falha ao consultar UF do cliente %s: %s', cliente_id, exc)
        return None

    # --------------------------------------------------------------
    # Itens
    # --------------------------------------------------------------
    def _montar_itens(self, venda: 'HoraVenda') -> list[dict]:
        itens = []
        # 1. Itens MOTO (1 chassi por linha, qtd=1, detalhes = chassi/motor)
        for vi in venda.itens:
            modelo_id = vi.moto.modelo_id if vi.moto else None
            if modelo_id is None:
                raise PayloadBuilderError(
                    'item_sem_modelo',
                    f'Item {vi.id} sem moto/modelo associado — investigar.',
                )
            map_ = (
                HoraTagPlusProdutoMap.query
                .filter_by(modelo_id=modelo_id)
                .first()
            )
            if not map_:
                raise PayloadBuilderError(
                    'produto_nao_mapeado',
                    f'Modelo {modelo_id} sem mapeamento TagPlus. Configurar em '
                    f'/hora/tagplus/conta/mapeamento.',
                )
            chassi = vi.numero_chassi or '-'
            motor = (vi.moto.numero_motor if vi.moto else None) or '-'
            itens.append({
                # API exige `produto_servico` (422 confirma em 2026-04-28 venda #2).
                'produto_servico': str(map_.tagplus_produto_id),
                'qtd': 1,
                'valor_unitario': self._round2_float(vi.preco_tabela_referencia),
                'valor_acrescimo': 0,
                'valor_desconto': self._round2_float(vi.desconto_aplicado or Decimal('0')),
                'detalhes': f'Chassi: {chassi} / Motor: {motor}',
                'cfop': map_.cfop_default or '5.403',
            })

        # 2. Itens PECA (qtd > 1 OK, sem chassi, CFOP de peca)
        from app.hora.models import HoraTagPlusPecaMap
        for vp in getattr(venda, 'itens_peca', []) or []:
            peca_map = (
                HoraTagPlusPecaMap.query
                .filter_by(peca_id=vp.peca_id)
                .first()
            )
            if not peca_map:
                raise PayloadBuilderError(
                    'peca_nao_mapeada',
                    f'Peca {vp.peca.codigo_interno} (id={vp.peca_id}) sem mapeamento '
                    f'TagPlus. Configurar em /hora/pecas/cadastro/{vp.peca_id}/editar.',
                )
            cfop_peca = peca_map.cfop_default or vp.peca.cfop_default or '5.102'
            itens.append({
                'produto_servico': str(peca_map.tagplus_produto_id),
                'qtd': float(vp.qtd),
                'valor_unitario': self._round2_float(vp.preco_unitario_referencia),
                'valor_acrescimo': 0,
                'valor_desconto': self._round2_float(vp.desconto_aplicado or Decimal('0')),
                'cfop': cfop_peca,
            })

        return itens

    # --------------------------------------------------------------
    # Faturas
    # --------------------------------------------------------------
    def _montar_faturas(self, venda: 'HoraVenda') -> list[dict]:
        """Monta lista de faturas para o payload TagPlus.

        Multi-formas (hora_34): itera `venda.pagamentos`; cada pagamento vira
        uma entrada `{forma_pagamento, parcelas}`. Cada uma com seu proprio
        numero de parcelas. Documento das parcelas:
            "<venda_id>-p<pag_id>/<idx>" se 1+ pagamento;
            "<venda_id>/<idx>" para o caso legacy (1 forma sintetica).

        Legacy (sem pagamentos): mantem comportamento antigo (1 fatura unica
        usando venda.forma_pagamento + venda.numero_parcelas).
        """
        intervalo = max(1, int(venda.intervalo_parcelas_dias or 30))
        base_date = venda.data_venda or date.today()

        pagamentos_lista = list(getattr(venda, 'pagamentos', []) or [])

        if pagamentos_lista:
            # Pre-fetch de mapeamentos em 1 query.
            nomes = [p.forma_pagamento_hora for p in pagamentos_lista]
            mapas = (
                HoraTagPlusFormaPagamentoMap.query
                .filter(HoraTagPlusFormaPagamentoMap.forma_pagamento_hora.in_(nomes))
                .all()
            )
            mapas_por_nome = {m.forma_pagamento_hora: m for m in mapas}

            faturas: list[dict] = []
            for pag in pagamentos_lista:
                fmap = mapas_por_nome.get(pag.forma_pagamento_hora)
                if not fmap:
                    raise PayloadBuilderError(
                        'forma_pagamento_nao_mapeada',
                        f'forma_pagamento={pag.forma_pagamento_hora!r} sem '
                        f'mapeamento TagPlus. Configurar em '
                        f'/hora/tagplus/conta/formas-pagamento.',
                    )
                if fmap.exige_aut_id and not (pag.aut_id or '').strip():
                    raise PayloadBuilderError(
                        'aut_id_ausente',
                        f'forma {pag.forma_pagamento_hora} exige AUT/ID — '
                        f'preencher antes de emitir.',
                    )
                n = max(1, int(pag.numero_parcelas or 1))
                valor_pag = Decimal(str(pag.valor))
                doc_prefix = f'{venda.id}-p{pag.id}'
                parcelas = self._dividir_parcelas(
                    valor_pag, n, intervalo, base_date, doc_prefix,
                )
                faturas.append({
                    'forma_pagamento': int(fmap.tagplus_forma_id),
                    'parcelas': parcelas,
                })
            return faturas

        # ---------- Legacy: 1 forma unica via venda.forma_pagamento ----------
        forma_map = (
            HoraTagPlusFormaPagamentoMap.query
            .filter_by(forma_pagamento_hora=venda.forma_pagamento)
            .first()
        )
        if not forma_map:
            raise PayloadBuilderError(
                'forma_pagamento_nao_mapeada',
                f'forma_pagamento={venda.forma_pagamento!r} sem mapeamento TagPlus. '
                f'Configurar em /hora/tagplus/conta/formas-pagamento.',
            )

        valor_total = sum(
            (i.preco_final for i in venda.itens),
            Decimal('0'),
        )

        n = max(1, int(venda.numero_parcelas or 1))
        # Idempotencia: prefixa documento com 'L' (legacy) para evitar colisao
        # com o esquema multi-formas '<venda_id>-p<pag_id>/<idx>'. Caso a venda
        # legacy seja repuxada apos a migration hora_34 (que faz backfill em
        # hora_venda_pagamento), o reenvio ira pelo caminho multi-formas e usar
        # outro prefixo — TagPlus nao confunde com a parcela legacy.
        doc_prefix_legacy = f'L{venda.id}'
        parcelas = self._dividir_parcelas(
            valor_total, n, intervalo, base_date, doc_prefix_legacy,
        )

        return [{
            'forma_pagamento': int(forma_map.tagplus_forma_id),
            'parcelas': parcelas,
        }]

    def _dividir_parcelas(
        self,
        valor_total: Decimal,
        n: int,
        intervalo_dias: int,
        base_date: 'date',
        doc_prefix,
    ) -> list[dict]:
        """Divide `valor_total` em `n` parcelas iguais, ajustando ultima.

        Regra: cada parcela = round2(valor_total / n). Diferenca de
        arredondamento vai para a ULTIMA parcela.

        Args:
            doc_prefix: int (legacy) ou str (multi-formas: f"{venda_id}-p{pag_id}").
                Usado como prefixo do campo `documento` para idempotencia em
                eventual reenvio.
        """
        from datetime import timedelta

        if n <= 1:
            return [{
                'documento': str(doc_prefix),
                'valor_parcela': self._round2_float(valor_total),
                'data_vencimento': base_date.isoformat(),
            }]

        valor_total_dec = (
            valor_total if isinstance(valor_total, Decimal)
            else Decimal(str(valor_total))
        )
        parcela_base = (valor_total_dec / Decimal(n)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP,
        )
        parcelas = []
        soma = Decimal('0.00')
        for i in range(1, n):
            parcelas.append({
                'documento': f'{doc_prefix}/{i}',
                'valor_parcela': float(parcela_base),
                'data_vencimento': (base_date + timedelta(days=intervalo_dias * i)).isoformat(),
            })
            soma += parcela_base
        # Ultima parcela = total - soma das anteriores (corrige centavos).
        ultima = (valor_total_dec - soma).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP,
        )
        parcelas.append({
            'documento': f'{doc_prefix}/{n}',
            'valor_parcela': float(ultima),
            'data_vencimento': (base_date + timedelta(days=intervalo_dias * n)).isoformat(),
        })
        return parcelas

    # --------------------------------------------------------------
    # CFOP por UF
    # --------------------------------------------------------------
    def _cfop_por_uf(
        self,
        cliente_uf: str | None,
        emitente_uf: str | None,
        venda: 'HoraVenda',
    ) -> str:
        # Fallback: pegar cfop_default do primeiro item mapeado.
        primeiro_item = next(iter(venda.itens), None)
        map_ = None
        if primeiro_item and primeiro_item.moto:
            map_ = HoraTagPlusProdutoMap.query.filter_by(
                modelo_id=primeiro_item.moto.modelo_id,
            ).first()
        cfop_default = map_.cfop_default if map_ else '5.403'

        if not cliente_uf or not emitente_uf:
            return cfop_default

        if cliente_uf == emitente_uf:
            return '5.403'
        return '6.403'

    def _uf_emitente(self, venda: 'HoraVenda') -> str | None:
        if venda.loja and getattr(venda.loja, 'uf', None):
            return (venda.loja.uf or '').upper() or None
        return None

    # --------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------
    @staticmethod
    def _round2_float(value: Decimal | float | int | None) -> float:
        if value is None:
            return 0.0
        d = value if isinstance(value, Decimal) else Decimal(str(value))
        return float(d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    @staticmethod
    def _so_digitos(valor: str | None) -> str:
        return re.sub(r'\D', '', valor or '')

    @staticmethod
    def _loja_label(venda: 'HoraVenda') -> str:
        if venda.loja:
            return getattr(venda.loja, 'rotulo_display', None) or venda.loja.nome
        return '-'
