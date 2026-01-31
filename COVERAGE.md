# Cobertura de Testes - OLX Monitor

> Última atualização: 2026-01-31

## Resumo

| Total de Testes | Tempo de Execução | Cobertura Geral |
|-----------------|-------------------|-----------------|
| 158 | ~4.17s | 69% |

## Cobertura por Módulo

| Módulo | Cobertura | Status | Importância |
|--------|-----------|--------|-------------|
| scheduler.py | 73% | 🟡 | 🔴 Crítico - coração da aplicação |
| scraper.py | 53% | 🟡 | 🔴 Crítico - parsing do OLX |
| database.py | 69% | 🟡 | 🟡 Médio - queries e persistência |
| validators.py | 84% | ✅ | 🟡 Médio - validação de inputs |
| notifications.py | 73% | 🟡 | 🟡 Médio - push notifications |
| logger.py | 73% | 🟡 | 🟢 Baixo - logging |
| exceptions.py | 100% | ✅ | 🟢 Baixo - exceções customizadas |
| delivery.py | 96% | ✅ | 🟢 Baixo - feature secundária |
| images.py | 75% | ✅ | 🟢 Baixo - download de imagens |

## Arquivos de Teste

```
tests/
├── conftest.py           # Fixtures compartilhadas
├── test_database.py      # CRUD operations
├── test_notifications.py # Push notifications
├── test_scheduler.py     # Jobs e tarefas
├── test_scraper.py       # Parsing HTML
└── test_validators.py    # Validação inputs
```

## Comandos

```bash
# Rodar todos os testes
./venv/bin/pytest tests/

# Rodar com cobertura detalhada
./venv/bin/pytest tests/ --cov=services --cov-report=term-missing

# Rodar teste específico
./venv/bin/pytest tests/test_scheduler.py -v
```

## Meta de Cobertura

- 🔴 Crítico: >= 70%
- 🟡 Médio: >= 50%
- 🟢 Baixo: >= 30%
