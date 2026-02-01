-- +goose Up
-- +goose StatementBegin
CREATE TABLE IF NOT EXISTS advertisements (
    seller_id INTEGER NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category INTEGER NOT NULL,
    images_qty INTEGER DEFAULT 0 NOT NULL
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
-- +goose StatementEnd
