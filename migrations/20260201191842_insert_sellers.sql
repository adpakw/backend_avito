-- +goose Up
-- +goose StatementBegin
INSERT INTO sellers (id, is_verified) VALUES
(1, True),
(2, False),
(3, True);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
-- +goose StatementEnd
