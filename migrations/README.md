# Миграции
Для миграций используется [goose](https://github.com/pressly/goose) 
```bash
# Создание миграции 
goose -dir migrations create {migration_name} sql

# Затем пишем в созданном файле логику миграции

# Запуск миграции
make migration
```