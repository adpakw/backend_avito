# Backend Avito

## Управление зависимостями
В проекте используется ```Poetry``` для управления зависимостями и виртуальными окружениями.

Файл ```pyproject.toml``` заменяет ```requirements.txt``` и содержит все настройки проекта.

## Запуск проекта
```
poetry install

poetry shell
# или же poetry env activate

make run

# для тестов
make test
```