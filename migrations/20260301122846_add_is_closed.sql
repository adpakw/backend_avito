-- +goose Up
-- +goose StatementBegin
ALTER TABLE advertisements 
ADD COLUMN is_closed BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE advertisements SET is_closed = FALSE WHERE is_closed IS NULL;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
ALTER TABLE advertisements 
DROP COLUMN is_closed;
-- +goose StatementEnd