# Documentos escaneados na tela de fechamento — análise para decisão (25/11/2026)

> Preparado pelo executor (Claude Code) a pedido do responsável (“grupo 1”, 25/11/2026). **Não é decisão:** a
> escolha envolve guarda de dados pessoais da cliente (LGPD, Q-24/Q-49/Q-65 abertas) e possível custo de
> máquina, que são do responsável. Contexto: D-412 (OCR local pelo comando) e D-413 item 4 (fora da tela pelo
> limite de 30 s da requisição).

## O problema, com números

| Item | Valor |
|---|---|
| Scans de outubro da SURIA | 2 PDFs: 50 páginas (43,7 MB) e 7 páginas (6,0 MB) |
| OCR por página | 1,5 s numa máquina Apple M5; **na máquina web de produção, ~6 s por passada e ~12 s com as duas** (V-479, página sintética) |
| Cota de CPU da `shared-cpu-1x` | 6,25% contínuo, com saldo de rajada de no máximo 500 s (5 s logo após um deploy); sem saldo, a máquina inteira fica limitada a 6,25% |
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
- **Medido (V-479):** uma página cabe (~12 s no pior caso), mas o mês inteiro não: 57 páginas são ~340 s de
  CPU, o que esgota o saldo de rajada da máquina web; depois disso cada página leva ~90 s (estoura os 30 s) e o
  site fica lento para todos os escritórios. **Na máquina web atual, a opção cai.** Só volta com uma máquina
  própria para o OCR (custo, exige autorização).

### C. Fila no worker, com guarda temporária
- O PDF é enviado uma vez, guardado no armazenamento privado (como os extratos), processado em lotes de
  páginas pelo worker e **apagado ao terminar**; ficam só os campos lidos, com prazo de retenção.
- **Prós:** a pessoa pode fechar a página; caminho já usado pelos extratos.
- **Contras:** guarda dados pessoais da cliente no servidor por algum tempo (exige decidir prazo e base
  legal, Q-24/Q-49/Q-65); 50 páginas podem ocupar o único worker por vários minutos, atrasando a conciliação de
  outros clientes, a menos que se crie uma fila separada ou se aumente a máquina (**custo**, exige
  autorização).

### D. OCR no navegador, sem guardar nada e sem CPU do servidor
- O navegador da pessoa faz o OCR com `tesseract.js` (Apache-2.0; o mesmo motor Tesseract compilado para
  WebAssembly), com o modelo `por` servido pelo próprio CICA. O servidor recebe só os campos lidos, como na B.
- **Prós:** nada guardado (D-413); nenhum custo; não usa a cota de CPU do servidor nem o worker.
- **Contras:** depende do computador da pessoa; download inicial de 5,8 MB (script, núcleo WASM e modelo,
  uma vez); mais código no navegador (inclusive converter o PDF em imagem, com pdf.js).
- **Validado localmente (D-423, V-480):** com o mesmo modelo, a simulação de outubro dá os mesmos 184
  movimentos e **46 de 47** pagamentos com documento (o nativo acha 47; cada motor erra dígitos da linha
  digitável em boletos diferentes). No navegador da M5, ~0,9 s por página — as 57 páginas em ~1 a 2 minutos.
- **Falta medir:** um computador comum de escritório (deve ser algumas vezes mais lento) e a conversão do PDF
  no navegador.

## Recomendação

1. ~~Medir o OCR na máquina web de produção~~ — feito (D-422, V-479): a página cabe, o mês não cabe na cota
   de CPU da máquina web. A opção B só com máquina própria (custo).
2. ~~Validar a opção D localmente~~ — feito (D-423, V-480): qualidade equivalente (46 contra 47) e tempo
   bom na M5.
3. **Recomendação: opção D.** Mantém a regra de não guardar nada, não tem custo e não usa a CPU do servidor.
   Antes de prometer prazo à CONTAD, abrir a página de teste num computador comum do escritório (CICA ou
   CONTAD) para medir o tempo real. Se ficar lento demais, cair para **A**; **B ou C** só com máquina própria
   (custo).

## O que precisa do responsável

- ~~Autorizar a medição em produção~~ — autorizada e feita em 25/11 (D-422).
- ~~Autorizar a validação local da opção D~~ — autorizada e feita em 25/11 (D-423).
- Escolher a opção (recomendada: D) e autorizar a implementação, que fica numa decisão própria.
- Se a escolha for C: prazo de guarda dos scans e dos campos lidos, e se aceita custo de uma máquina ou fila
  separada para o OCR.
