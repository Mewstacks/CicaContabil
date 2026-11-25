# Documentos escaneados na tela de fechamento — análise para decisão (25/11/2026)

> Preparado pelo executor (Claude Code) a pedido do responsável (“grupo 1”, 25/11/2026). **Não é decisão:** a
> escolha envolve guarda de dados pessoais da cliente (LGPD, Q-24/Q-49/Q-65 abertas) e possível custo de
> máquina, que são do responsável. Contexto: D-412 (OCR local pelo comando) e D-413 item 4 (fora da tela pelo
> limite de 30 s da requisição).

## O problema, com números

| Item | Valor |
|---|---|
| Scans de outubro da SURIA | 2 PDFs: 50 páginas (43,7 MB) e 7 páginas (6,0 MB) |
| OCR por página | 1,5 s numa máquina Apple M5; numa `shared-cpu-1x` do Fly deve ser várias vezes mais lento (não medido) |
| Limite da requisição web | 30 s (gunicorn `--timeout 30`) |
| Worker | 1 máquina `shared-cpu-1x`/512 MB, **uma tarefa por vez**, limite de 270 s por tarefa; é o mesmo worker que processa os extratos e a conciliação |
| Conteúdo dos scans | Boletos, recibos, DANFE e CT-e: nomes, CPF/CNPJ, valores e, nos recibos de distribuição, dados dos sócios |

Hoje a tela não guarda nada (D-413): os arquivos vivem só durante a requisição. Qualquer caminho que leve o
OCR para fora da requisição precisa guardar o arquivo por algum tempo ou mudar onde o OCR roda.

## Opções

### A. Continuar pelo comando (como hoje)
- A pessoa da CICA roda `simular_multifontes --documentos` na própria máquina e entrega os relatórios.
- **Prós:** nenhum dado guardado no servidor; nenhum custo; já validado com outubro (47 de 47 documentos de
  pagamento encontrados).
- **Contras:** a CONTAD não usa sozinha; depende de alguém da CICA a cada mês.

### B. OCR página a página, sem guardar nada no servidor (recomendada)
- O navegador separa o PDF em páginas (biblioteca `pdf-lib`, MIT, servida pelo próprio CICA) e envia **uma
  página por requisição**. O servidor faz o OCR daquela página dentro dos 30 s, devolve só os campos lidos
  (tipo, valor, vencimento, CNPJ, número) e descarta a imagem. No fim, a simulação recebe os campos, não os
  arquivos.
- **Prós:** continua valendo a D-413 (nada guardado); não ocupa o worker da conciliação; sem custo de máquina.
- **Contras:** a pessoa precisa manter a página aberta (50 páginas × alguns segundos cada); mais código no
  navegador; a leitura de cada página precisa caber nos 30 s na máquina web (medir antes de prometer).
- **Risco a medir primeiro:** tempo de OCR de uma página na `shared-cpu-1x`. Se passar de ~20 s, a opção cai.

### C. Fila no worker, com guarda temporária
- O PDF é enviado uma vez, guardado no armazenamento privado (como os extratos), processado em lotes de
  páginas pelo worker e **apagado ao terminar**; ficam só os campos lidos, com prazo de retenção.
- **Prós:** a pessoa pode fechar a página; caminho já usado pelos extratos.
- **Contras:** guarda dados pessoais da cliente no servidor por algum tempo (exige decidir prazo e base
  legal, Q-24/Q-49/Q-65); 50 páginas podem ocupar o único worker por vários minutos, atrasando a conciliação de
  outros clientes, a menos que se crie uma fila separada ou se aumente a máquina (**custo**, exige
  autorização).

## Recomendação

1. **Medir** o OCR de uma página na máquina web de produção (ou numa máquina igual), sem dados da cliente:
   uma página sintética. Custo zero; exige só autorização para o teste no ambiente.
2. Se couber com folga nos 30 s, seguir com a **opção B**: mantém a regra de não guardar nada e não mexe no
   worker.
3. Se não couber, decidir entre **A** (sem custo, depende da CICA) e **C** (exige definir guarda e,
   provavelmente, custo de máquina).

## O que precisa do responsável

- Autorizar a medição em produção (passo 1) — ou indicar outra máquina igual.
- Se a escolha for C: prazo de guarda dos scans e dos campos lidos, e se aceita custo de uma máquina ou fila
  separada para o OCR.
