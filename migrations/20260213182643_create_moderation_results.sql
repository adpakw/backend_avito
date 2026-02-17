-- +goose Up
-- +goose StatementBegin
CREATE TABLE IF NOT EXISTS moderation_results (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES advertisements(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'completed', 'failed')),
    is_violation BOOLEAN,
    probability FLOAT,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
-- +goose StatementEnd
