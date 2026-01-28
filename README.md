# Backend Avito

## Управление зависимостями
В проекте используется ```uv``` для управления зависимостями и виртуальными окружениями.

Файл ```pyproject.toml``` заменяет ```requirements.txt``` и содержит все настройки проекта.

## Запуск проекта
```
uv pip install -r pyproject.toml

uv sync

# запуск сервиса
make run

# для тестов
make test
```