class ModelIsNotAvailable(Exception):
    """Ошибка указывает на то, что модель либо не подкачена, либо не обучена."""

    pass


class ErrorInPrediction(Exception):
    """Ошибка указывает на ошибку в процессе предикта."""

    pass


class SellerNotFoundError(Exception):
    """Ошибка указывает на то, что селлер в бд не найден"""

    pass


class AdvertisementNotFoundError(Exception):
    """Ошибка указывает на то, что объявление в бд не найден"""

    pass
