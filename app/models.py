import bcrypt
import ormar
import databases
import sqlalchemy
from enum import Enum
from datetime import datetime
from typing import Optional

sqlite_file_name = "todo.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = sqlalchemy.create_engine(sqlite_url)  # type: ignore
base_ormar_config = ormar.OrmarConfig(
    metadata=sqlalchemy.MetaData(),  # type: ignore
    database=databases.Database(sqlite_url),
    engine=engine,  # type: ignore
)


class UserModel(ormar.Model):
    ormar_config = base_ormar_config.copy(tablename="users")

    id: int = ormar.Integer(primary_key=True)  # type: ignore
    user_name: str = ormar.String(min_length=3, max_length=12, unique=True)  # type: ignore
    pwd: str = ormar.String(max_length=120)  # type: ignore

    @staticmethod
    def generate_hash_password(password: str):
        """Hashes a password using bcrypt."""
        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters long.')
        if len(password) > 16:
            raise ValueError('Password must be at most 16 characters long.')
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, plain_password):
        """Verifies a password against a hashed password."""
        return bcrypt.checkpw(plain_password.encode('utf-8'), self.pwd.encode('utf-8'))
    
class Importance(int, Enum):
    NONE = 0
    LOW = 1
    MIDDLE = 2
    HIGH = 3



class TagModel(ormar.Model):
    ormar_config = base_ormar_config.copy(tablename="tags", constraints=[ormar.UniqueColumns("name", "user")])
    id: int = ormar.Integer(primary_key=True, required=True)  # type: ignore
    name: str = ormar.String(index=True, max_length=100)  # type: ignore
    color: str = ormar.String(index=True, max_length=7, min_length=7, default='1111111')  # type: ignore
    user: UserModel = ormar.ForeignKey(UserModel, related_name='tag_list')

class TodoModel(ormar.Model):
    ormar_config = base_ormar_config.copy(tablename="todos")

    id: int = ormar.Integer(primary_key=True, required=True)  # type: ignore
    item: str = ormar.String(index=True, max_length=1000)  # type: ignore
    create_time: datetime = ormar.DateTime(default=datetime.now)  # type: ignore

    plan_time: Optional[datetime] = ormar.DateTime(nullable=True)  # type: ignore
    content: Optional[str] = ormar.String(nullable=True, max_length=5000)  # type: ignore
    user: UserModel = ormar.ForeignKey(UserModel, related_name='todo_list')
    importance: Importance = ormar.Enum(enum_class=Importance, default=Importance.NONE.value)
    tags: Optional[list[TagModel]] = ormar.ManyToMany(TagModel)

    @property
    def importance_enum(self) -> Importance:
        return Importance(self.importance)

    @importance_enum.setter
    def importance_enum(self, value: Importance):
        self.importance = value.value  # type: ignore