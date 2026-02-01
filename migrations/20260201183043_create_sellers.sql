-- +goose Up
-- +goose StatementBegin
CREATE TABLE IF NOT EXISTS sellers (
    id SERIAL PRIMARY KEY,
    is_verified BOOLEAN NOT NULL
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
-- +goose StatementEnd
