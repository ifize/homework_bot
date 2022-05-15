class StatusCodeError(Exception):
    def __init__(self, *args: object):
        super().__init__(args)
        self.status_code = args[0]

    def str(self):
        return f'Сбой запроса к эндпоинту. Статус: {self.status_code}'
