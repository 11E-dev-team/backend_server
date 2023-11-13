from sqlalchemy.orm import Session
from uuid import UUID, uuid4
import dataclasses
from dataclasses import asdict
from datetime import datetime
from server.database.schemas.users import UserCreate


def hash_password(password: str):
    return password + "debug_not_really_hashed"  # FIXME


@dataclasses.dataclass
class User:
    id: UUID
    email: str
    hashed_password: str
    username: str
    token: str | None
    token_expiration_date: datetime | None
    display_name: str | None = None
    settings: str = dataclasses.field(default_factory=dict)

    @classmethod
    def create(cls, user: UserCreate):
        hashed_password = hash_password(user.password)

        new_user = cls(
            id=uuid4(),
            email=user.email,
            username=user.username,
            hashed_password=hashed_password,
            display_name=user.display_name,
            settings={},
            token=None,
            token_expiration_date=None,
        )
        return new_user

    def data_to_dict(self) -> dict:
        """
        Returns dict with data
        """
        data_dict = asdict(self)
        data_dict.pop("settings")
        return data_dict
