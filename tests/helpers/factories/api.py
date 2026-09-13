from typing import Any


class ApiFactoryHelper:
    @classmethod
    def hex_id(cls, value: int | str) -> str:
        if isinstance(value, str):
            return value
        return f"{value:032x}"

    @classmethod
    def login_request(cls, username: str = "TEST", password: str | None = None) -> dict[str, Any]:
        return {"username": username, "password": password or "TEST"}
