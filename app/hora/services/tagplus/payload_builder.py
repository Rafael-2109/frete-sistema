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

    # --------------------------------------------------------------
    # Public
    # --------------------------------------------------------------
    def build(self, venda: 'HoraVenda') -> dict:
        if not venda.itens:
            raise PayloadBuilderError('venda_sem_itens', 'Venda sem itens.')

        if venda.forma_pagamento in (None, '', 'NAO_INFORMADO'):
            raise PayloadBuilderError(
                'forma_pagamento_ausente',
                'Forma de pagamento nao informada — preencher antes de emitir.'
            )
        if venda.forma_pagamento == 'MISTO':
            raise PayloadBuilderError(
                'pagamento_misto_nao_suportado',
                'Pagamento MISTO nao suportado na v1 — emitir manualmente.'
            )

        destinatario_id = self._resolver_destinatario(venda)

        cliente_uf = self._consultar_uf_cliente(destinatario_id)
        emitente_uf = self._uf_emitente(venda)
        cfop = self._cfop_por_uf(cliente_uf, emitente_uf, venda)

        itens = self._montar_itens(venda)
        faturas = self._montar_faturas(venda)

        loja_label = self._loja_label(venda)
        valor_desconto = sum(
            (i.desconto_aplicado or Decimal('0') for i in venda.itens),
            Decimal('0'),
        )
        valor_nota = sum(
            (i.preco_final for i in venda.itens),
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
        payload = {
            'tipo': 'S',
            'finalidade_emissao': 1,            # Normal (CONFIRMAR fiscal HORA — ver §15.1).
            'consumidor_final': True,
            'indicador_presenca': 1,            # Presencial (loja fisica).
            'tipo_emissao': 1,                  # Normal (nao contingencia).
            'modalidade_frete': 9,              # Sem frete (cliente leva).
            'data_emissao': agora_utc_naive().isoformat(timespec='seconds'),
            'data_entrada_saida': date.today().isoformat(),
            'cfop': cfop,                       # mascara 9.999 obrigatoria.
            'destinatario': destinatario_id,
            'itens': itens,
            'faturas': faturas,
            'valor_desconto': self._round2_float(valor_desconto),
            'valor_nota': self._round2_float(valor_nota),
            'inf_contribuinte': (
                f'Venda #{venda.id} | Loja: {loja_label} | '
                f'Vendedor: {venda.vendedor or "-"}'
            ),
            'numero_pedido': str(venda.id),
        }
        return payload

    # --------------------------------------------------------------
    # Destinatario (cliente TagPlus)
    # --------------------------------------------------------------
    def _resolver_destinatario(self, venda: 'HoraVenda') -> int:
        cpf = self._so_digitos(venda.cpf_cliente)
        if not cpf or len(cpf) != 11:
            raise PayloadBuilderError(
                'cpf_invalido',
                f'CPF invalido na venda {venda.id}: {venda.cpf_cliente!r}',
            )

        # 1) Localizar via busca livre + match local exato.
        # Doc (guia.md:118-124): `?q=<termo>` faz LIKE %termo% nos campos
        # principais (nome, cpf, razao_social, etc.). E o unico mecanismo de
        # busca documentado que esta garantido pela API.
        # NAO usar `?cpf_cnpj=` — nao e filtro valido, TagPlus ignora e devolve
        # a colecao paginada toda, causando falso positivo de "ambiguidade".
        # `fields=*` garante que TODOS os campos voltem (cpf pode ter nome
        # diferente em cada conta — `cpf` ou `cpf_cnpj`).
        r = self.api.get(
            '/clientes',
            params={'q': cpf, 'fields': '*', 'per_page': 30},
        )
        if r.status_code == 200:
            try:
                resultados = r.json()
            except ValueError:
                resultados = []
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

            if len(matches) == 1:
                return int(matches[0]['id'])
            if len(matches) > 1:
                raise PayloadBuilderError(
                    'destinatario_ambiguo',
                    f'CPF {cpf} encontrado em {len(matches)} clientes no TagPlus '
                    f'(IDs: {[m.get("id") for m in matches]}). '
                    f'Resolver manualmente no portal antes de emitir.',
                )
            # 0 matches -> nao existe ainda, criar via POST abaixo.

        # 2) Cria.
        # Schema TagPlus Cliente PF (doc_tagplus.md:506-525, 716-744): apenas
        # campos confirmados sao enviados (TagPlus retorna 422 com "Campo
        # adicional nao permitido" se enviar campos fora do schema).
        # Campos do schema: tipo, razao_social, cpf, cnpj, ativo, codigo,
        # exterior, enderecos[].
        # NAO ENVIAR: nome (use razao_social), email/telefone (nao confirmados
        # no schema de Cliente embutido na resposta da NFe — sao campos de
        # Funcionario/Vendedor, nao Cliente).
        body: dict = {
            'tipo': 'F',
            'razao_social': (venda.nome_cliente or '').strip(),
            'cpf': cpf,
        }

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
            cid = created.get('id') if isinstance(created, dict) else None
            if cid:
                return int(cid)
            raise PayloadBuilderError(
                'cliente_criado_sem_id',
                f'POST /clientes status {r2.status_code} sem id na resposta: {r2.text[:200]}',
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

    # Cache de sessao para lookups de cidade (evita N+1 em batch).
    _cache_id_cidade: dict[tuple[str, str], int | None] = {}

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
                'produto': str(map_.tagplus_produto_id),  # codigo string do produto no TagPlus
                'qtd': 1,
                'valor_unitario': self._round2_float(vi.preco_tabela_referencia),
                'valor_acrescimo': 0,
                'valor_desconto': self._round2_float(vi.desconto_aplicado or Decimal('0')),
                'detalhes': f'Chassi: {chassi} / Motor: {motor}',
            })
        return itens

    # --------------------------------------------------------------
    # Faturas
    # --------------------------------------------------------------
    def _montar_faturas(self, venda: 'HoraVenda') -> list[dict]:
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
        return [{
            'forma_pagamento': int(forma_map.tagplus_forma_id),
            'parcelas': [{
                'documento': str(venda.id),
                'valor_parcela': self._round2_float(valor_total),
                'data_vencimento': (venda.data_venda or date.today()).isoformat(),
            }],
        }]

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
