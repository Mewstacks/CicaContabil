# Agente Domínio local

O agente é propositalmente separado do Hub web. Ele só deve operar dentro da rede do escritório, com uma credencial ODBC **somente leitura**, para sincronizar empresas, catálogo de acumuladores e histórico necessário à classificação.

Ele não armazena nem recebe certificados A1/PFX, senhas de certificado, credenciais Serpro ou XML fiscal. A conexão de saída usa um certificado técnico mTLS confiado pela CA privada do Hub e distinto de qualquer certificado fiscal.

Antes de instalação, valide as consultas contra uma cópia homologada do banco Domínio; nomes de tabelas e permissões diferem por instalação. O esqueleto em `hub_agent.py` usa consultas constantes e não tem qualquer comando de escrita.

## Runtime do serviço

O instalador oficial é [`install-windows-service.ps1`](install-windows-service.ps1). Ele faz o enrollment por código de uso único, cifra a configuração com DPAPI antes de gravá-la em `C:\ProgramData\HubContador\agent-config.dpapi`, restringe as ACLs a `LOCAL SERVICE`, `SYSTEM` e administradores e registra o host nativo `HubContadorDominioAgent` no Windows SCM. **Nenhum segredo é aceito por argumento de linha de comando nem impresso.**

Execute somente em PowerShell elevado, a partir do ambiente Python que contém o extra `dominio-agent`:

```powershell
uv sync --extra dominio-agent
.\agent\install-windows-service.ps1 -SystemDsn Dominio64 -HubUrl https://hub.exemplo.com -Label 'Servidor Domínio' -CaFile C:\HubContador\mtls\ca.pem -CertificateFile C:\HubContador\mtls\agent.pem -PrivateKeyFile C:\HubContador\mtls\agent.key
```

O prompt solicita o código de enrollment; ele não deve ser colocado em script, variável persistente, CI ou ticket. DPAPI em escopo de máquina depende da ACL para limitar leitura a contas confiáveis: administradores locais continuam sendo administradores e fazem parte da fronteira de confiança do servidor.

`python -m agent.runner` continua disponível apenas para o probe supervisionado e não deve ser usado como serviço em produção.

| Variável | Finalidade |
| --- | --- |
| `HUB_AGENT_DSN` | Apenas o nome do DSN de sistema Windows; não aceita `UID`, senha ou string de conexão. |
| `HUB_AGENT_HUB_URL` | Origem HTTPS do HubContador. |
| `HUB_AGENT_ID` e `HUB_AGENT_SHARED_SECRET` | Identidade após enrollment; o segredo também cifra a fila local. |
| `HUB_AGENT_CA_FILE`, `HUB_AGENT_CERTIFICATE_FILE`, `HUB_AGENT_PRIVATE_KEY_FILE` | Material técnico mTLS protegido por ACL local. |
| `HUB_AGENT_QUEUE_PATH` | Fila AES-GCM, padrão `C:\ProgramData\HubContador\agent-queue.bin`. |
| `HUB_AGENT_INTERVAL_SECONDS` | Intervalo entre ciclos, de 10 a 86.400 segundos; padrão 300. |

Antes de registrar o serviço, execute uma vez no console protegido:

```powershell
python -m agent.runner --once
```

O comando mostra somente `status` e quantidade de empresas. Em queda de rede, o snapshot mascarado fica na fila cifrada e o próximo ciclo o reenvia **antes** de abrir ODBC novamente. Não execute duas instâncias para o mesmo dispositivo; o instalador definitivo deve configurar reinício do serviço e ACL apenas para sua conta técnica.

## Fluxo de instalação assistida

1. O owner gera um código de enrollment de uso único, válido por no máximo 60 minutos.
2. O instalador recebe CA do Hub, certificado de cliente e chave privada do agente. A chave fica fora do repositório e do perfil de usuário.
3. O instalador envia código, rótulo, fingerprint e SHA-256 do certificado para `POST /api/v1/intelligence/agent/enroll/` via HTTPS. O Hub devolve identidade e segredo uma única vez; armazene-os no Gerenciador de Credenciais do Windows ou cofre equivalente.
4. `sync_client.py` exige TLS 1.2+, valida CA/hostname do Hub e apresenta o certificado de cliente em cada snapshot. HMAC continua como defesa contra replay; não substitui mTLS. A fila local de `local_queue.py` mantém payloads cifrados enquanto a rede estiver indisponível.
5. Se o dispositivo for revogado, o Hub rejeita imediatamente os próximos envios.

O agente nunca aceita conexões de entrada, nunca recebe SQL, nem recebe senha ODBC do Hub. Ele usa o DSN local configurado pelo instalador e uma lista de consultas fixa.

No Cobalchini, usar [edge-agent-mtls.conf](../deploy/nginx/edge-agent-mtls.conf) no proxy HTTPS. O contêiner `web` permanece em loopback; o proxy verifica o certificado, remove headers do cliente e só então encaminha a identidade verificada. O Hub rejeita sync sem essa prova em produção.

Configure telemetria CRMew apenas por variáveis de ambiente. Crie projetos distintos para `hub-web`, `hub-worker` e `dominio-agent`; mantenha a sondagem externa desligada até aprovação operacional.
