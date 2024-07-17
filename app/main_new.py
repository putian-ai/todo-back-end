import ormar
import databases
import sqlalchemy
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from contextlib import asynccontextmanager
from typing import Generic, TypeVar, Sequence
from fastapi.middleware.cors import CORSMiddleware


sqlite_file_name = "todo.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = sqlalchemy.create_engine(sqlite_url)  # type: ignore
base_ormar_config = ormar.OrmarConfig(
    metadata=sqlalchemy.MetaData(),  # type: ignore
    database=databases.Database(sqlite_url),
    engine=engine,  # type: ignore
)


class User(ormar.Model):
    ormar_config = base_ormar_config.copy(tablename="users")

    id: int = ormar.Integer(primary_key=True) # type: ignore
    user_name: str = ormar.String(min_length=3, max_length=12) # type: ignore
    pwd: str = ormar.String(min_length=3, max_length=12) # type: ignore



async def init_db_and_tables():
    base_ormar_config.metadata.drop_all(engine)
    base_ormar_config.metadata.create_all(engine)
    init_users = ['Harry', 'Leo', 'Amy', 'Alvin']
    for user_name in init_users:
        user = User(user_name=user_name, pwd='123456')
        await user.save()
    init_todos = [
        "Code",
        "Groceries",
        "Clean",
        "Call",
        "Bills",
        "Walk",
        "Report",
        "Doctor",
        "Plants",
        "Read",
        "Library",
        "Trash",
        "Laundry",
        "Desk"
    ]
    init_todo_user_ids = [1, 2, 3, 4]
    # with Session(engine) as session:
    #     for i in range(len(init_todos)):
    #         init_todo = init_todos[i]
    #         init_todo_user_id = init_todo_user_ids[i % 4]
    #         user = session.exec(select(User).where(User.id == init_todo_user_id)).first()
    #         todo = Todo(item=init_todo, plan_time=datetime.now(), user_id=init_todo_user_id, user=user)  # type: ignore
    #         session.add(todo)
    #     session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserDto(BaseModel):
    user_name: str
    pwd: str


@app.post("/create_users/", tags=['user'])
async def create_user(userDto: UserDto) -> User:
    user = User(user_name=userDto.user_name, pwd=userDto.pwd)
    await user.save()
    return user
