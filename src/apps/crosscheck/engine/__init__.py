"""Motor de conferência do Contraprova.

Puro Python, sem Django: lê EFD ICMS/IPI e XML fiscal em streaming, prepara os dados num
SQLite temporário em disco e compara por junção. Nada aqui conhece escritório, usuário ou
banco do CICA; é por isso que o motor se testa sozinho e roda no worker sem estourar a
memória.
"""
