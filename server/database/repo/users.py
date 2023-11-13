from uuid import UUID

from server.database.repo.base_repo_module import BaseRepoModule
from server.database.models import users as users_models
from server.database.schemas import users as users_schemas
from server.database.entities import users as users_entities
from server.database.db_context import DBContext
from sqlalchemy import update


class UserRepoModule(BaseRepoModule):
    def get_by_id(self, ctx: DBContext, user_id: UUID) -> users_models.User:
        user = (
            ctx.session.query(users_models.User)
            .filter(users_models.User.id == user_id)
            .first()
        )
        return user and user.as_entity()

    def get_by_email(self, ctx: DBContext, email: str) -> users_models.User:
        user = (
            ctx.session.query(users_models.User)
            .filter(users_models.User.email == email)
            .first()
        )
        return user and user.as_entity()

    def get_by_username(self, ctx: DBContext, username: str) -> users_models.User:
        user = (
            ctx.session.query(users_models.User)
            .filter(users_models.User.username == username)
            .first()
        )
        return user and user.as_entity()

    def get_by_token(self, ctx: DBContext, token: str) -> users_models.User:
        user = (
            ctx.session.query(users_models.User)
            .filter(users_models.User.token == token)
            .first()
        )
        return user

    def every(self, ctx: DBContext, skip: int = 0, limit: int = 100):
        return map(
            users_models.User.as_entity,
            ctx.session.query(users_models.User).offset(skip).limit(limit).all(),
        )

    def update_data(self, ctx: DBContext, user: users_entities.User):
        """
        Function for updating data in database. Don't use for updating settings
        """
        ctx.session.execute(
            update(users_models.User)
            .where(users_models.User.id == user.id)
            .values(user.data_to_dict())
        )
        ctx.session.commit()
        return user

    def insert(self, ctx: DBContext, user: users_entities.User):
        db_user = users_models.User.from_entity(user)
        ctx.session.add(db_user)
        ctx.session.commit()
        ctx.session.refresh(db_user)
        return user
