from rest_framework.exceptions import APIException


class DatabaseOperationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class HeadAlreadyExists(APIException):
    status_code = 400
    default_detail = "Головной отдел уже существует."
    default_code = "head_already_exists"


class HeadDeleteForbidden(APIException):
    status_code = 400
    default_detail = "Нельзя удалить единственный головной отдел."
    default_code = "head_delete_forbidden"


class EmployeeCountError(APIException):
    status_code = 400
    default_detail = "Недопустимое количество сотрудников для данного типа точки."
    default_code = "employee_count_error"
