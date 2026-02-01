-- +goose Up
-- +goose StatementBegin
INSERT INTO advertisements (seller_id, id, name, description, category, images_qty) VALUES
(1, 1, 'Ноутбук Dell', 'Мощный ноутбук для работы и игр', 5, 2),
(2, 2, 'iPhone 13', 'Смартфон в идеальном состоянии', 3, 4),
(1, 3, 'Книги по программированию', 'Коллекция книг по Python и ML', 2, 1),
(3, 4, 'Велосипед горный', 'Отличный велосипед для активного отдыха', 7, 3),
(2, 5, 'Дом', 'Участок с домом в Одинцово', 9, 1);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
-- +goose StatementEnd
