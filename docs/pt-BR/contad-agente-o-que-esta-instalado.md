# O que está instalado no servidor da CONTAD

> **RASCUNHO PARA A CLIENTE, NÃO ENVIADO.** Atende ao pedido da reunião de 24/11/2026 [41:32–43:09]
> ("se me questionarem, preciso saber responder"). Revisar antes de enviar. Fonte técnica:
> [`docs/contad-agente-oficial-windows-server.md`](../contad-agente-oficial-windows-server.md).
> Os itens marcados com (confirmar) devem ser conferidos pelo responsável antes do envio.

## Em uma frase

É um programa da CICA que **só lê** algumas informações do banco de dados do Domínio e as envia, por
conexão segura, para a CICA usar na conciliação. Ele **não grava, não altera e não apaga nada** no Domínio.

## O que é

- Nome: **Agente CICA** (serviço do Windows `CicaAgent`), versão 1.0.13, instalado em 17/11/2026 no servidor SVAPL02.
- Roda como serviço do Windows, inicia sozinho com o servidor e fica em segundo plano.
- Foi instalado por um pacote de instalação padrão do Windows (MSI).

## Como acessa o Domínio

- Usa o **usuário externo do Domínio** que a CONTAD forneceu, com permissão **somente de leitura**.
  Esse usuário nem consegue entrar no Domínio para operar.
- Faz apenas **consultas fixas**, definidas pela CICA e conferidas por código; não aceita consultas livres.

## O que ele lê

- Cadastro das empresas da carteira.
- Lançamentos do Razão da conta bancária, do mês que vocês pedirem na tela da CICA.
- Títulos a pagar e a receber (parcelas e baixas) da empresa e do mês pedidos.
- Itens do extrato bancário registrados no Domínio, quando pedidos.

Ele só busca o que for pedido pela tela da CICA, por empresa e mês.

## Para onde envia

- Somente para o sistema da CICA, pela internet, com **conexão criptografada (HTTPS)**.
- **Nenhuma porta de entrada** foi aberta no servidor: é sempre o agente que chama a CICA, nunca o contrário.
- A senha do usuário do Domínio e a identidade do agente ficam **protegidas pelo próprio Windows** no servidor
  e não são enviadas à CICA.

## O que ele não faz

- Não grava, não altera e não apaga dados do Domínio.
- Não reinicia o servidor nem o Domínio.
- Não instala outros programas.

## Como parar ou remover

- **Parar:** em *Serviços* do Windows, parar o serviço `CicaAgent`. A CICA deixa de receber dados; nada no
  Domínio é afetado.
- **Remover:** pelo Painel de Controle do Windows, como qualquer programa instalado (confirmar o nome exibido
  na lista antes de enviar).

## Atualizações

A versão instalada já busca qualquer mês a partir de setembro de 2026; outubro e os meses seguintes não exigem
atualização. Quando uma atualização for necessária, ela preserva a configuração e não exige refazer a conexão;
combinaremos o melhor momento com vocês antes de aplicá-la.
