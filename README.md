# Backend Avito

## Управление зависимостями
В проекте используется ```uv``` для управления зависимостями и виртуальными окружениями.

Файл ```pyproject.toml``` заменяет ```requirements.txt``` и содержит все настройки проекта.

## БД
Чтобы поднять PostgreSQL
```bash
docker-compose up -d
```

Для того чтобы залезть в контейнер и проверить БД
```bash
docker exec -it CONTAINER_NAME bash

psql -U postgres -d POSTGRES_DB -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
```

## Миграции
Для миграций используется [goose](https://github.com/pressly/goose) 
```bash
# Создание миграции 
goose -dir migrations create {migration_name} sql

# Затем пишем в созданном файле логику миграции

# Запуск миграции
make migration
```

## Запуск проекта
```bash
uv pip install -r pyproject.toml

uv sync

# запуск сервиса
make run

# для тестов
make test
```