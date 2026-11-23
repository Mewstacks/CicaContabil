# Capacidade da coleta por procuração (E5, 20/11/2026)

Fonte do código: [nfse_procuracao.py](../src/apps/hub/nfse_procuracao.py), [tasks_procuracao.py](../src/apps/hub/tasks_procuracao.py). Prova: [test_procuracao_capacity.py](../tests/test_procuracao_capacity.py). Custos: [proposta-precos.md](comercial/proposta-precos.md) §2.2 (valores de 20/11/2026, não aplicados).

## O que o teste de carga provou

| Medida | Resultado |
|---|---|
| Escolher quais e-CNPJ têm trabalho vencido | **1 consulta**, com 1 ou 25 escritórios |
| Próxima empresa de um e-CNPJ | no máximo 2 consultas, em carteira de 1.800 linhas |
| Contar o conjunto elegível | 1 consulta, sem carregar linhas |
| Uma chamada em voo por e-CNPJ | respeitado (`RUNNING` segura o e-CNPJ inteiro) |
| Semear as linhas de um escritório de 200 empresas | era **205 consultas** (uma por empresa); virou inserção em lote (menos de 20) |

O teste achou o defeito do último item antes de qualquer escritório grande: `seed_procuracao_syncs` rodava uma inserção por empresa a cada execução. Corrigido com `bulk_create` (a restrição `hub_unique_nfse_sync_company` mantém a idempotência).

## O que limita de verdade: o ritmo do ADN, não o banco

- Piso de **1 chamada por segundo por e-CNPJ** (prática do HubFedrizzi; o manual v1.1 não publica limite de taxa).
- Cadência por empresa: **1 h** em dia, **6 h** aguardando procuração, **24 h** sem movimento.
- Um e-CNPJ acompanha até `3.600 chamadas/h ÷ cadência`: **3.600 empresas em dia por hora**, em teoria. A Bianchi tem ~560 CNPJs.
- Uma chamada leva de 1 a 2 s (**HIPÓTESE**, ainda sem medida em produção). Um worker serial atende então 1.800 a 3.600 chamadas por hora. Escritórios diferentes se revezam: o encadeamento (`chain_procuracao_certificate`) pega a próxima empresa do mesmo e-CNPJ 1 s depois.

## O gargalo que existe hoje: o worker é um só e a fila legada o ocupa

`fly.toml`: worker `shared-cpu-1x` de 512 MB com `--concurrency=1`. A fila de A1 por empresa (legada, global e serial, ~30 s por CNPJ) já ocupa esse worker por horas. As tarefas da fila nova entram na mesma fila do Celery e esperariam atrás dela: **um escritório novo atrasaria a Bianchi, ou o contrário**. Regra L5 do plano: sem confirmação de custo, a fila nova não roda em produção.

### Decisão que depende do responsável (nada foi aplicado)

| Opção | Custo mensal | Efeito | Risco |
|---|---:|---|---|
| A. Segundo processo worker só para a fila de procuração (fila `procuracao`, `--concurrency=1`, 512 MB em gru) | **+R$ 36,32** (US$ 5,96) | isola os dois mundos; Bianchi não percebe nada | custo fixo novo |
| B. Mesmo worker com `--concurrency=2` | R$ 0,00 | divide o tempo | 512 MB já têm ~27 MB livres (nota de 09/10/2026) e o shell do worker morre por falta de memória acima de ~130 MB: **não recomendado** |
| C. Esperar o primeiro escritório pago antes de ligar a fila | R$ 0,00 | adia o custo | nada de procuração em produção até lá |

Recomendação: **A**, quando houver o piloto (Fedrizzi) ou o primeiro escritório pago. Para aplicar, três mudanças juntas e só com o seu OK: (1) `CELERY_TASK_ROUTES` em `base.py` mandando as tarefas `hub.*procuracao*` para uma fila própria (hoje não há roteamento; tudo vai para `CELERY_TASK_DEFAULT_QUEUE`); (2) um processo novo no `fly.toml`, `celery -A config worker -Q <fila> --concurrency=1` **sem** `--beat` (o beat continua só no worker atual); (3) a `[[vm]]` correspondente, 512 MB.

## Alarmes (feitos)

- `hub.check_procuracao_lane` (de hora em hora, só com a fila ligada): linhas vencidas há mais de 6 h viram `WARNING procuracao.lane_stalled` com a contagem e a idade da mais atrasada. O Sentry recolhe o aviso quando for ligado.
- `hub.notify_office_certificates` (diário): aviso dentro do produto ao dono e aos administradores quando o e-CNPJ do escritório vence em 30, 15, 7, 3 e 1 dia. Um aviso por limiar.
- `hub.notify_lost_procuracoes` (diário): empresa que tinha procuração e agora responde E2245.

## O que ainda precisa de medida real

1. Duração de uma chamada ao ADN em produção (a conta acima usa 1 a 2 s).
2. Memória do worker durante a fila de procuração (decide se a opção A cabe em 512 MB).
3. Conexões com o Neon: web e worker usam PgBouncer (iterator desligado); contar conexões abertas com 2 workers.
4. Valkey: a fila e a pausa por 429 usam o cache; conferir memória livre (256 MB).
