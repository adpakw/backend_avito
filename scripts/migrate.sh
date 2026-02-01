#!/bin/bash

source .env

DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}?sslmode=disable"

goose -dir migrations postgres "${DATABASE_URL}" up