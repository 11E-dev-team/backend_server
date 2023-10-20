from sqlalchemy.orm import Session
from uuid import UUID, uuid4
import dataclasses
from server.database.schemas.users import UserCreate


@dataclasses.dataclass
class User:
    id: UUID
    email: str
    hashed_password: str
    settings: str = "{}"

    @classmethod
    def create(cls, user: UserCreate):
        hashed_password = user.password + "debug_not_really_hashed"

        new_user = cls(
            id=uuid4(),
            email=user.email,
            hashed_password=hashed_password,
            settings=user.settings,
        )
        return new_user