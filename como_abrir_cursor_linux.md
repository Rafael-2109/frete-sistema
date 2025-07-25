# Como abrir o Cursor no Linux (WSL2)

## Opção 1: Direto do terminal Linux
```bash
cd /home/rafaelnascimento/projetos/frete_sistema
cursor .
```

## Opção 2: Do Windows PowerShell/CMD
```bash
wsl cd /home/rafaelnascimento/projetos/frete_sistema && cursor .
```

## Opção 3: Criar um alias no Linux
Adicione ao seu ~/.bashrc:
```bash
echo "alias frete='cd /home/rafaelnascimento/projetos/frete_sistema && cursor .'" >> ~/.bashrc
source ~/.bashrc
```
Depois é só digitar: `frete`

## Opção 4: Abrir o Cursor no Windows e navegar
1. Abra o Cursor normalmente
2. File > Open Folder
3. Digite o caminho: `\\wsl$\Ubuntu\home\rafaelnascimento\projetos\frete_sistema`

## Nota importante:
- O Cursor precisa estar instalado e configurado no PATH do Linux
- Se não estiver, instale com: `curl -fsSL https://cursor.sh/install.sh | sh`