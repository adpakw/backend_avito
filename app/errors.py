class ModelIsNotAvailable(Exception):
    """Ошибка указывает на то, что модель либо не подкачена, либо не обучена."""
    pass


class ErrorInPrediction(Exception):
    """Ошибка указывает на то, что ошибку в процессе предикта."""
    pass
