import pydantic
from typing import Optional, Type
import re


class CreateUser(pydantic.BaseModel):
    username: str
    email: str
    password: str

    @pydantic.validator("password")
    @classmethod
    def validate_title(cls, value):
        if len(value) < 8:
            raise ValueError("Password is too short")
        return value

    @pydantic.validator("email")
    @classmethod
    def validate_email(cls, value):
        if not bool(re.fullmatch(r"[\w.-]+@[\w-]+\.[\w.]+", value)):
            raise ValueError("Email is invalid")
        return value


class UpdateUser(pydantic.BaseModel):
    username: Optional[str]
    email: Optional[str]
    password: Optional[str]

    @pydantic.validator("password")
    @classmethod
    def validate_title(cls, value):
        if len(value) < 8:
            raise ValueError("Password is too short")
        return value

    @pydantic.validator("email")
    @classmethod
    def validate_email(cls, value):
        if not bool(re.fullmatch(r"[\w.-]+@[\w-]+\.[\w.]+", value)):
            raise ValueError("Email is invalid")
        return value


VALIDATION_CLASS = Type[CreateUser] | Type[UpdateUser]
