#!/usr/bin/env python3
"""
Script para atualizar COVERAGE.md com dados atuais
"""

import subprocess
import re
from datetime import datetime
from pathlib import Path


def get_coverage_data():
    """Roda pytest com coverage e extrai os dados"""
    result = subprocess.run(
        ['./venv/bin/pytest', 'tests/', '--cov=services', '--cov-report=term', '-q'],
        capture_output=True,
        text=True
    )

    output = result.stdout + result.stderr

    # Extrair contagem de testes
    test_match = re.search(r'(\d+) passed', output)
    test_count = test_match.group(1) if test_match else '?'

    # Extrair tempo
    time_match = re.search(r'in ([\d.]+)s', output)
    time_taken = time_match.group(1) if time_match else '?'

    # Extrair cobertura por módulo
    coverage = {}
    for line in output.split('\n'):
        match = re.match(r'services/(\w+)\.py\s+\d+\s+\d+\s+(\d+)%', line)
        if match:
            module = match.group(1)
            percent = int(match.group(2))
            coverage[module] = percent

    # Calcular cobertura geral
    total_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
    total_coverage = total_match.group(1) if total_match else '?'

    return {
        'test_count': test_count,
        'time': time_taken,
        'total': total_coverage,
        'modules': coverage
    }


def get_status(percent):
    """Retorna emoji de status baseado na cobertura"""
    if percent >= 75:
        return '✅'
    elif percent >= 40:
        return '🟡'
    else:
        return '❌'


def get_importance(module):
    """Retorna importância do módulo"""
    importance = {
        'scheduler': ('🔴 Crítico', 'coração da aplicação'),
        'scraper': ('🔴 Crítico', 'parsing do OLX'),
        'database': ('🟡 Médio', 'queries e persistência'),
        'validators': ('🟡 Médio', 'validação de inputs'),
        'notifications': ('🟡 Médio', 'push notifications'),
        'logger': ('🟢 Baixo', 'logging'),
        'exceptions': ('🟢 Baixo', 'exceções customizadas'),
        'delivery': ('🟢 Baixo', 'feature secundária'),
        'images': ('🟢 Baixo', 'download de imagens'),
    }
    return importance.get(module, ('🟢 Baixo', ''))


def generate_markdown(data):
    """Gera o conteúdo do COVERAGE.md"""
    today = datetime.now().strftime('%Y-%m-%d')

    # Ordenar módulos por importância e cobertura
    module_order = ['scheduler', 'scraper', 'database', 'validators', 'notifications', 'logger', 'exceptions', 'delivery', 'images']

    modules_table = ""
    for module in module_order:
        percent = data['modules'].get(module, 0)
        status = get_status(percent)
        importance, desc = get_importance(module)
        desc_text = f" - {desc}" if desc else ""
        modules_table += f"| {module}.py | {percent}% | {status} | {importance}{desc_text} |\n"

    return f"""# Cobertura de Testes - OLX Monitor

> Última atualização: {today}

## Resumo

| Total de Testes | Tempo de Execução | Cobertura Geral |
|-----------------|-------------------|-----------------|
| {data['test_count']} | ~{data['time']}s | {data['total']}% |

## Cobertura por Módulo

| Módulo | Cobertura | Status | Importância |
|--------|-----------|--------|-------------|
{modules_table}
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
"""


def main():
    print("📊 Atualizando cobertura...")

    data = get_coverage_data()
    content = generate_markdown(data)

    coverage_file = Path(__file__).parent.parent / 'COVERAGE.md'
    coverage_file.write_text(content)

    print(f"✅ COVERAGE.md atualizado ({data['test_count']} testes, {data['total']}% cobertura)")


if __name__ == '__main__':
    main()
