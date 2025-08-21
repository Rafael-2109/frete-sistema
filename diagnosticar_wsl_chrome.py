#!/usr/bin/env python3
"""
Diagnóstico completo de conectividade WSL -> Chrome Windows
"""

import subprocess
import socket
import requests
import sys
import os

def executar_comando(cmd):
    """Executa comando e retorna output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2)
        return result.stdout.strip()
    except:
        return None

def testar_porta(host, porta=9222):
    """Testa se uma porta está aberta"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, porta))
        sock.close()
        return result == 0
    except:
        return False

def testar_chrome_api(host):
    """Testa API do Chrome"""
    try:
        url = f"http://{host}:9222/json/version"
        response = requests.get(url, timeout=1)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

print("\n" + "="*60)
print("DIAGNÓSTICO DE CONECTIVIDADE WSL -> CHROME WINDOWS")
print("="*60)

# 1. Detectar versão do WSL
print("\n1️⃣ VERSÃO DO WSL:")
wsl_version = executar_comando("wsl.exe -l -v 2>/dev/null | grep -i running || echo 'WSL2'")
print(f"   {wsl_version or 'WSL2 (assumindo)'}")

# 2. Encontrar IPs possíveis do Windows
print("\n2️⃣ PROCURANDO IP DO WINDOWS HOST:")

ips_para_testar = []

# Método 1: nameserver do resolv.conf
ip1 = executar_comando("cat /etc/resolv.conf | grep nameserver | awk '{print $2}'")
if ip1:
    print(f"   Método 1 (resolv.conf): {ip1}")
    ips_para_testar.append(ip1)

# Método 2: Gateway padrão
ip2 = executar_comando("ip route | grep default | awk '{print $3}'")
if ip2:
    print(f"   Método 2 (gateway): {ip2}")
    ips_para_testar.append(ip2)

# Método 3: host.docker.internal (se Docker instalado)
try:
    docker_ip = socket.gethostbyname('host.docker.internal')
    print(f"   Método 3 (Docker): {docker_ip}")
    ips_para_testar.append(docker_ip)
except:
    pass

# Método 4: Variável de ambiente WSL
wsl_host = os.environ.get('WSL_HOST')
if wsl_host:
    print(f"   Método 4 (WSL_HOST): {wsl_host}")
    ips_para_testar.append(wsl_host)

# Método 5: PowerShell do Windows
ps_ip = executar_comando("powershell.exe -Command '(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias \"vEthernet (WSL)\").IPAddress' 2>/dev/null")
if ps_ip and not ps_ip.startswith("Get-NetIPAddress"):
    print(f"   Método 5 (PowerShell): {ps_ip}")
    ips_para_testar.append(ps_ip)

# Adicionar localhost também
ips_para_testar.extend(['localhost', '127.0.0.1', 'host.local'])

# Remover duplicatas
ips_para_testar = list(dict.fromkeys(ips_para_testar))

print(f"\n   IPs a testar: {ips_para_testar}")

# 3. Testar conectividade
print("\n3️⃣ TESTANDO CONECTIVIDADE NA PORTA 9222:")

ip_funcionando = None

for ip in ips_para_testar:
    if not ip:
        continue
    
    print(f"\n   Testando {ip}:9222...")
    
    # Teste 1: Socket
    if testar_porta(ip, 9222):
        print(f"      ✅ Porta aberta!")
        
        # Teste 2: API Chrome
        info = testar_chrome_api(ip)
        if info:
            print(f"      ✅ Chrome API respondendo!")
            print(f"      Browser: {info.get('Browser', 'N/A')}")
            print(f"      Protocol: {info.get('Protocol-Version', 'N/A')}")
            ip_funcionando = ip
            break
        else:
            print(f"      ⚠️ Porta aberta mas API não responde")
    else:
        print(f"      ❌ Porta fechada ou inacessível")

# 4. Resultado e solução
print("\n" + "="*60)
print("RESULTADO:")
print("="*60)

if ip_funcionando:
    print(f"\n✅ SUCESSO! Chrome acessível em: {ip_funcionando}:9222")
    print("\n🔧 SOLUÇÃO - Atualize seus arquivos:")
    
    print(f"""
1. Edite o arquivo 'testar_chrome_wsl.py' e mude a linha:
   DE:  response = requests.get('http://localhost:9222/json/version', timeout=2)
   PARA: response = requests.get('http://{ip_funcionando}:9222/json/version', timeout=2)

2. Edite 'app/portal/browser_manager_simples.py' e mude:
   DE:  options.add_experimental_option("debuggerAddress", "localhost:9222")
   PARA: options.add_experimental_option("debuggerAddress", "{ip_funcionando}:9222")

3. Ou crie uma variável de ambiente:
   export CHROME_HOST={ip_funcionando}
   echo "export CHROME_HOST={ip_funcionando}" >> ~/.bashrc
""")
    
    # Salvar IP em arquivo para uso posterior
    with open('.chrome_host', 'w') as f:
        f.write(ip_funcionando)
    print(f"\n✅ IP salvo em .chrome_host: {ip_funcionando}")
    
else:
    print("\n❌ NÃO FOI POSSÍVEL CONECTAR AO CHROME!")
    print("\n📋 CHECKLIST DE PROBLEMAS:")
    print("""
1. ✓ Chrome está rodando no Windows com --remote-debugging-port=9222?
   
2. ✓ Firewall do Windows está bloqueando?
   No Windows (como Admin):
   netsh advfirewall firewall add rule name="Chrome Debug" dir=in action=allow protocol=TCP localport=9222
   
3. ✓ WSL está no modo NAT? Tente modo Bridge:
   No Windows (como Admin):
   - Edite .wslconfig em %USERPROFILE%
   - Adicione:
     [wsl2]
     networkingMode=bridged
   - Reinicie WSL: wsl --shutdown
   
4. ✓ Antivírus bloqueando? Desative temporariamente para testar.
   
5. ✓ Use o Chrome no modo sem sandbox:
   chrome.exe --remote-debugging-port=9222 --no-sandbox --disable-gpu
""")

print("\n" + "="*60)
sys.exit(0 if ip_funcionando else 1)