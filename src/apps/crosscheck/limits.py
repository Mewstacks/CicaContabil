"""Tetos do Contraprova.

Existem para que uma conferência caiba no worker do Fly (512 MB, ~110 MB livres, tarefa
com limite de 300 s) e no processo web (~27 MB livres). O motor processa 60 mil documentos
e 10 mil XML em ~8 s (teste de desempenho), então os números abaixo têm folga; mudar um
deles pede repetir `tests/test_crosscheck_performance.py`.
"""

from __future__ import annotations

from datetime import timedelta

MiB = 1024 * 1024

#: Cada arquivo SPED. Acima disso o escritório divide por estabelecimento.
MAX_SPED_BYTES = 150 * MiB
#: Cada ZIP de XML enviado.
MAX_ZIP_BYTES = 300 * MiB
#: XML solto (e cada XML dentro de um ZIP): o teto da NF-e é muito menor que isto.
MAX_XML_BYTES = 2 * MiB
#: Quantos XML soltos cabem numa requisição (`DATA_UPLOAD_MAX_NUMBER_FILES` é 100).
MAX_LOOSE_XML_PER_REQUEST = 100
#: Soma dos XML soltos de uma requisição: o processo web tem ~27 MB livres e o Django guarda
#: em memória cada arquivo de até 2,5 MiB, então o teto é por soma, não só por arquivo.
MAX_LOOSE_XML_BYTES_PER_REQUEST = 30 * MiB
#: Exportação do Domínio (CSV/XLSX).
MAX_DOMINIO_BYTES = 25 * MiB
#: Soma de todos os arquivos de uma conferência.
MAX_RUN_BYTES = 600 * MiB
#: XML por conferência, somando todos os arquivos.
MAX_XML_PER_RUN = 10_000
#: Conferências ativas (na fila ou rodando) por escritório: o worker é um só.
MAX_ACTIVE_RUNS_PER_OFFICE = 2
#: Achados guardados no banco por conferência; o restante vai só para o XLSX.
MAX_FINDINGS_STORED = 50_000

#: D-302: arquivos de entrada somem 24 h depois do fim; achados e relatório, 90 dias.
INPUT_RETENTION = timedelta(hours=24)
RESULT_RETENTION = timedelta(days=90)
#: Rascunho sem movimento: nunca "termina", então a regra de D-302 conta a partir da última
#: alteração e dá três dias para quem junta os arquivos aos poucos.
DRAFT_RETENTION = timedelta(hours=72)
#: Muda quando a lógica de conferência muda; entra na impressão digital das entradas para que
#: um resultado antigo nunca seja devolvido no lugar de uma conferência com a regra nova.
ENGINE_VERSION = 1
#: A tarefa renova o arrendamento a cada atualização de andamento.
RUN_LEASE = timedelta(minutes=8)
#: Uma conferência na fila há mais que isto sem o worker pegar é reenviada pelo recuperador.
QUEUE_RECOVERY_AFTER = timedelta(minutes=10)
MAX_ATTEMPTS = 3
