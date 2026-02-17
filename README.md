# Backend Avito

## Управление зависимостями
В проекте используется ```uv``` для управления зависимостями и виртуальными окружениями.

Файл ```pyproject.toml``` заменяет ```requirements.txt``` и содержит все настройки проекта.

## Переменные окружения
В проекте используются переменные окружения, чтобы использовать их полноценно скопируйте содержимое `.env.example` в `.env`

## Инфра
Поднимаем инфру в докер контейнерах через docker-compose
```bash
docker-compose up -d
```

## БД
**PostgreSQL** поднимается через docker-compose

Для того чтобы залезть в контейнер и проверить БД
```bash
docker exec -it backend_avito_postgres bash

psql -U postgres -d backend_avito -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
```

### Миграции
Для миграций используется [goose](https://github.com/pressly/goose) 
```bash
# Запуск миграции
make migration
```

## Брокер сообщений
В качестве брокера используется **Redpanda** (**Kafka**-совместимый брокер), поднимается через docker-compose. 
- Брокер будет доступен на `localhost:9092`
- Веб-консоль для просмотра топиков и сообщений — на http://localhost:8080


## Запуск проекта
```bash
uv pip install -r pyproject.toml

uv sync

# запуск сервиса
make run

# для тестов
make test
```