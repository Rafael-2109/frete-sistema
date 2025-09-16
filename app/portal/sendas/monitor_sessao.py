#!/usr/bin/env python3
"""
Monitor Automático de Sessões do Portal Sendas
Verifica validade e tenta renovar quando possível
"""

import os
import json
import jwt
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
from flask import current_app
from app import db
from app.models import Usuario
from app.utils.email import enviar_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MonitorSessaoSendas:
    """Monitor automático de sessões do Portal Sendas"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.sessions_dir = self.base_dir / "sessions"
        self.cookies_file = self.sessions_dir / "sendas_cookies.json"
        self.session_file = self.sessions_dir / "sendas_session.json"
        self.monitor_log = self.sessions_dir / "monitor.log"

        self.base_url = "https://plataforma.trizy.com.br"
        self.api_url = "https://api.trizy.com.br"

    def analisar_token_jwt(self, token: str) -> Dict:
        """
        Analisa token JWT e retorna informações de validade
        """
        try:
            # Decodifica sem verificar assinatura
            decoded = jwt.decode(token, options={"verify_signature": False})

            exp_timestamp = decoded.get('exp', 0)
            iat_timestamp = decoded.get('iat', 0)

            resultado = {
                'valido': False,
                'expira_em': None,
                'dias_restantes': 0,
                'precisa_renovar': True,
                'usuario_id': decoded.get('sub')
            }

            if exp_timestamp:
                exp_date = datetime.fromtimestamp(exp_timestamp)
                resultado['expira_em'] = exp_date
                resultado['valido'] = exp_date > datetime.now()

                if resultado['valido']:
                    tempo_restante = exp_date - datetime.now()
                    resultado['dias_restantes'] = tempo_restante.days
                    # Renovar se falta menos de 3 dias
                    resultado['precisa_renovar'] = tempo_restante < timedelta(days=3)

            return resultado

        except Exception as e:
            logger.error(f"Erro analisando JWT: {e}")
            return {'valido': False, 'erro': str(e)}

    def verificar_sessao_atual(self) -> Dict:
        """
        Verifica status completo da sessão atual
        """
        if not self.cookies_file.exists():
            return {
                'tem_sessao': False,
                'mensagem': 'Nenhuma sessão salva'
            }

        try:
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)

            # Procura token de acesso
            for cookie in cookies:
                if cookie.get('name') == 'trizy_access_token':
                    token_info = self.analisar_token_jwt(cookie.get('value', ''))
                    return {
                        'tem_sessao': True,
                        'token_info': token_info,
                        'valido': token_info.get('valido', False),
                        'precisa_renovar': token_info.get('precisa_renovar', True),
                        'dias_restantes': token_info.get('dias_restantes', 0)
                    }

            return {
                'tem_sessao': True,
                'valido': False,
                'mensagem': 'Token de acesso não encontrado'
            }

        except Exception as e:
            logger.error(f"Erro verificando sessão: {e}")
            return {
                'tem_sessao': False,
                'erro': str(e)
            }

    def testar_sessao_api(self) -> bool:
        """
        Testa se a sessão funciona fazendo requisição real
        """
        if not self.cookies_file.exists():
            return False

        try:
            with open(self.cookies_file, 'r') as f:
                cookies_list = json.load(f)

            # Converter para dict
            cookies_dict = {}
            access_token = None

            for cookie in cookies_list:
                if isinstance(cookie, dict):
                    name = cookie.get('name', '')
                    value = cookie.get('value', '')
                    cookies_dict[name] = value

                    if name == 'trizy_access_token':
                        access_token = value

            # Fazer requisição de teste
            session = requests.Session()

            for name, value in cookies_dict.items():
                session.cookies.set(name, value, domain='.trizy.com.br')

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Referer': f'{self.base_url}/#/terminal/painel'
            }

            if access_token:
                headers['Authorization'] = f'Bearer {access_token}'

            # Tentar acessar endpoint da API
            response = session.get(
                f'{self.api_url}/auth/validate',  # Endpoint hipotético de validação
                headers=headers,
                timeout=10
            )

            # Se não existir endpoint de validação, tentar outro
            if response.status_code == 404:
                response = session.get(
                    f'{self.base_url}/#/terminal/painel',
                    headers=headers,
                    allow_redirects=True,
                    timeout=10
                )

            # Verificar se não foi redirecionado para login
            if response.status_code == 200:
                if 'login' not in response.url.lower():
                    return True

            return False

        except Exception as e:
            logger.error(f"Erro testando sessão: {e}")
            return False

    def tentar_renovar_token(self) -> bool:
        """
        Tenta renovar o token usando refresh token se disponível
        """
        if not self.session_file.exists():
            return False

        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)

            # Procurar por refresh token no localStorage ou cookies
            local_storage = session_data.get('localStorage', {})
            refresh_token = None

            # Possíveis locais do refresh token
            for key in ['refresh_token', 'refreshToken', 'trizy_refresh_token']:
                if key in local_storage:
                    refresh_token = local_storage[key]
                    break

            if not refresh_token:
                logger.info("Refresh token não encontrado")
                return False

            # Tentar renovar
            response = requests.post(
                f'{self.api_url}/auth/refresh',
                json={'refresh_token': refresh_token},
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                new_token = data.get('access_token')

                if new_token:
                    # Atualizar cookies com novo token
                    self._atualizar_token(new_token)
                    logger.info("✅ Token renovado com sucesso!")
                    return True

            logger.warning(f"Renovação falhou: {response.status_code}")
            return False

        except Exception as e:
            logger.error(f"Erro tentando renovar: {e}")
            return False

    def _atualizar_token(self, novo_token: str):
        """Atualiza o token nos arquivos de sessão"""
        try:
            # Atualizar cookies
            if self.cookies_file.exists():
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)

                for cookie in cookies:
                    if cookie.get('name') == 'trizy_access_token':
                        cookie['value'] = novo_token
                        break

                with open(self.cookies_file, 'w') as f:
                    json.dump(cookies, f, indent=2)

            # Atualizar session
            if self.session_file.exists():
                with open(self.session_file, 'r') as f:
                    session_data = json.load(f)

                session_data['timestamp'] = datetime.now().isoformat()

                # Atualizar nos cookies da sessão também
                if 'cookies' in session_data:
                    for cookie in session_data['cookies']:
                        if cookie.get('name') == 'trizy_access_token':
                            cookie['value'] = novo_token
                            break

                with open(self.session_file, 'w') as f:
                    json.dump(session_data, f, indent=2)

        except Exception as e:
            logger.error(f"Erro atualizando token: {e}")

    def notificar_usuarios(self, tipo: str, detalhes: Dict):
        """
        Notifica usuários sobre status da sessão

        Args:
            tipo: 'expirando', 'expirada', 'renovada', 'erro'
            detalhes: Informações adicionais
        """
        try:
            # Buscar usuários admin para notificar
            usuarios_admin = Usuario.query.filter_by(is_admin=True, ativo=True).all()

            if tipo == 'expirando':
                assunto = f"⚠️ Sessão Sendas expira em {detalhes.get('dias', 0)} dias"
                mensagem = f"""
                A sessão do Portal Sendas está prestes a expirar.

                Dias restantes: {detalhes.get('dias', 0)}
                Expira em: {detalhes.get('expira_em', 'N/A')}

                Por favor, acesse o sistema e renove a sessão manualmente:
                {current_app.config.get('BASE_URL')}/portal/sendas/sessao
                """

            elif tipo == 'expirada':
                assunto = "❌ Sessão Sendas Expirada"
                mensagem = """
                A sessão do Portal Sendas expirou.

                É necessário fazer login manual para capturar novos tokens.

                Acesse: {}/portal/sendas/sessao
                """.format(current_app.config.get('BASE_URL'))

            elif tipo == 'renovada':
                assunto = "✅ Sessão Sendas Renovada"
                mensagem = f"""
                A sessão do Portal Sendas foi renovada automaticamente.

                Nova validade: {detalhes.get('nova_validade', 'N/A')}
                """

            else:  # erro
                assunto = "❌ Erro no Monitor de Sessão Sendas"
                mensagem = f"""
                Ocorreu um erro ao monitorar a sessão:

                {detalhes.get('erro', 'Erro desconhecido')}
                """

            # Enviar emails
            for usuario in usuarios_admin:
                if usuario.email:
                    enviar_email(
                        destinatario=usuario.email,
                        assunto=assunto,
                        corpo=mensagem
                    )

            # Registrar no log
            self._registrar_log(tipo, detalhes)

        except Exception as e:
            logger.error(f"Erro notificando usuários: {e}")

    def _registrar_log(self, tipo: str, detalhes: Dict):
        """Registra eventos no log do monitor"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'tipo': tipo,
                'detalhes': detalhes
            }

            # Ler log existente
            logs = []
            if self.monitor_log.exists():
                try:
                    with open(self.monitor_log, 'r') as f:
                        logs = json.load(f)
                except:
                    pass

            # Adicionar nova entrada
            logs.append(log_entry)

            # Manter apenas últimas 100 entradas
            logs = logs[-100:]

            # Salvar
            with open(self.monitor_log, 'w') as f:
                json.dump(logs, f, indent=2)

        except Exception as e:
            logger.error(f"Erro salvando log: {e}")

    def executar_monitoramento(self) -> Dict:
        """
        Executa ciclo completo de monitoramento

        Returns:
            Dict com resultado do monitoramento
        """
        logger.info("🔍 Iniciando monitoramento de sessão Sendas")

        # 1. Verificar status da sessão
        status = self.verificar_sessao_atual()

        if not status.get('tem_sessao'):
            logger.warning("Sem sessão salva")
            return {'sucesso': False, 'motivo': 'sem_sessao'}

        # 2. Se sessão válida, verificar se precisa renovar
        if status.get('valido'):
            dias_restantes = status.get('dias_restantes', 0)

            # Notificar se está expirando
            if dias_restantes <= 3:
                logger.warning(f"⚠️ Sessão expira em {dias_restantes} dias")

                # Tentar renovar automaticamente
                if self.tentar_renovar_token():
                    logger.info("✅ Token renovado automaticamente!")
                    self.notificar_usuarios('renovada', {
                        'nova_validade': datetime.now() + timedelta(days=30)
                    })
                    return {'sucesso': True, 'acao': 'renovado'}
                else:
                    # Não conseguiu renovar, notificar usuário
                    self.notificar_usuarios('expirando', {
                        'dias': dias_restantes,
                        'expira_em': status.get('token_info', {}).get('expira_em')
                    })
                    return {'sucesso': True, 'acao': 'notificado_expiracao'}

            # Testar se realmente funciona
            if self.testar_sessao_api():
                logger.info(f"✅ Sessão válida - {dias_restantes} dias restantes")
                return {'sucesso': True, 'dias_restantes': dias_restantes}
            else:
                logger.warning("⚠️ Token válido mas sessão não funciona")
                self.notificar_usuarios('erro', {
                    'erro': 'Token válido mas autenticação falhou'
                })
                return {'sucesso': False, 'motivo': 'sessao_invalida'}

        # 3. Sessão expirada
        else:
            logger.error("❌ Sessão expirada")
            self.notificar_usuarios('expirada', {})
            return {'sucesso': False, 'motivo': 'expirada'}


def executar_monitor_sessao():
    """
    Função para ser chamada pelo scheduler
    Deve ser executada a cada hora
    """
    try:
        monitor = MonitorSessaoSendas()
        resultado = monitor.executar_monitoramento()
        logger.info(f"Monitor executado: {resultado}")
        return resultado
    except Exception as e:
        logger.error(f"Erro no monitor: {e}")
        return {'sucesso': False, 'erro': str(e)}


if __name__ == "__main__":
    # Teste manual
    resultado = executar_monitor_sessao()
    print(json.dumps(resultado, indent=2, default=str))