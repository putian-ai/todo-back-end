import sqlite3
import bcrypt
import ormar
import databases
import sqlalchemy
from enum import Enum
from datetime import datetime, timedelta
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from contextlib import asynccontextmanager
from typing import Generic, Optional, TypeVar, Sequence
from fastapi.middleware.cors import CORSMiddleware
from authx import AuthX, AuthXConfig, RequestToken, TokenPayload


sqlite_file_name = "todo.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = sqlalchemy.create_engine(sqlite_url)  # type: ignore
base_ormar_config = ormar.OrmarConfig(
    metadata=sqlalchemy.MetaData(),  # type: ignore
    database=databases.Database(sqlite_url),
    engine=engine,  # type: ignore
)


T = TypeVar('T')


class UserModel(ormar.Model):
    ormar_config = base_ormar_config.copy(tablename="users")

    id: int = ormar.Integer(primary_key=True)  # type: ignore
    user_name: str = ormar.String(min_length=3, max_length=12)  # type: ignore
    pwd: str = ormar.String(min_length=3, max_length=12)  # type: ignore

    def set_hash_password(self, password: str):
        """Hashes a password using bcrypt."""
        salt = bcrypt.gensalt()
        self.pwd = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, hashed_password):
        """Verifies a password against a hashed password."""
        return bcrypt.checkpw(self.password.encode('utf-8'), hashed_password.encode('utf-8'))


class LoginForm(BaseModel):
    username: str
    password: str


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


class Tag(BaseModel):
    id: int
    name: str
    color: str


class User(BaseModel):
    id: int
    user_name: str


class Todo(BaseModel):
    id: int
    item: str
    create_time: datetime
    plan_time: Optional[datetime]
    content: Optional[str]
    importance: Importance
    user: User
    tags: Optional[list[Tag]]


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


class UserDto(BaseModel):
    user_name: str
    pwd: str


class TagDto(BaseModel):
    user_id: int
    todo_id: int
    name: str
    color: str = Field(max_length=7, min_length=7)


class TodoDto(BaseModel):
    item: str
    plan_time: str
    user_id: int
    content: str
    importance: Importance

    @field_validator('plan_time')
    @classmethod
    def parse_plan_time(cls, value: str | None) -> datetime:
        if value:
            return datetime.strptime(value, TIME_FORMAT)
        return value  # type: ignore


class UpdateTodoDto(BaseModel):
    item: str
    plan_time: str
    content: str
    importance: Importance

    @field_validator('plan_time')
    @classmethod
    def parse_plan_time(cls, value: str):
        if value:
            return datetime.strptime(value, TIME_FORMAT)
        return value


TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class PaginateModel(BaseModel, Generic[T]):
    page: int
    per_page: int
    total_items: int
    items: Sequence[T]


async def pagniate_todos(page: int, per_page: int) -> PaginateModel[TodoModel]:
    total_items = await TodoModel.objects.count()
    todos = await TodoModel.objects.limit(per_page).offset((page-1)*per_page).all()
    return PaginateModel(
        page=page,
        per_page=per_page,
        total_items=total_items,
        items=todos
    )


async def init_db_and_tables():
    base_ormar_config.metadata.drop_all(engine)
    base_ormar_config.metadata.create_all(engine)
    init_users = ['Harry', 'Leo', 'Amy', 'Alvin']
    for user_name in init_users:
        user = UserModel(user_name=user_name, pwd='123456')
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

    for i in range(len(init_todos)):
        init_todo = init_todos[i]
        init_todo_user_id = init_todo_user_ids[i % 4]
        user = await UserModel.objects.get(id=init_todo_user_id)
        tag, _ = await TagModel.objects.get_or_create(name="a", color="#000000", user=user)
        todo = TodoModel(item=init_todo, plan_time=datetime.now(),
                         user=user, content="Hello", importance=Importance.MIDDLE)  # type: ignore
        await todo.save()
        await todo.tags.add(tag)  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
security = AuthX()


config = AuthXConfig(
    JWT_ALGORITHM="HS256",
    JWT_SECRET_KEY="PUTIAN_NB",
    JWT_TOKEN_LOCATION=["headers"]
)

auth = AuthX(config=config)
auth.handle_errors(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post('/login')
async def login(form: LoginForm):
    # Replace with your actual user validation logic
    if form.username == "test" and form.password == "test":
        access_token = security.create_access_token(sub=form.username)
        refresh_token = security.create_refresh_token(sub=form.username)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    raise HTTPException(status_code=401, detail="Bad username or password")


@app.post('/refresh')
async def refresh(refresh_token: TokenPayload = Depends(security.refresh_token_required)):
    new_access_token = security.create_access_token(sub=refresh_token.sub)
    return {"access_token": new_access_token}


@app.get('/protected')
async def protected_route(token: TokenPayload = Depends(security.access_token_required)):
    return {"message": "You have access to this protected resource"}


@app.post("/create_users/", tags=['user'], response_model=User)
async def create_user(userDto: UserDto) -> UserModel:
    if len(userDto.user_name) > 12 or len(userDto.user_name) < 3:
        raise HTTPException(status_code=400, detail="min_length=3, max_length=12")
    elif len(userDto.pwd) > 12 or len(userDto.pwd) < 3:
        raise HTTPException(status_code=400, detail="min_length=3, max_length=12")
    user = UserModel(user_name=userDto.user_name, pwd=userDto.pwd)
    await user.save()
    return user


@app.post("/create_tag/", tags=['tag'], response_model=Tag)
async def create_tag(tagDto: TagDto) -> TagModel:
    user = await UserModel.objects.get_or_none(id=tagDto.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User does not exist!!!!!!!!")
    try:
        tag, _ = await TagModel.objects.get_or_create(name=tagDto.name, user=user)
        todo = await TodoModel.objects.get_or_none(id=tagDto.todo_id)
        if not todo:
            raise HTTPException(status_code=400, detail="Todo does not exist!")

        await todo.tags.add(tag)  # type: ignore
        return tag
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail=f"{user.user_name} already has a tag named: {tagDto.name}")


@app.post("/create_todos/", tags=['todo'], response_model=Todo)
async def create_todo(todoDto: TodoDto) -> TodoModel:
    user = await UserModel.objects.get_or_none(id=todoDto.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User does not exist!")

    todo = TodoModel(item=todoDto.item, plan_time=todoDto.plan_time, user=todoDto.user_id, content=todoDto.content, importance=todoDto.importance.value)

    await todo.save()
    todo.user = user
    return todo


@app.get("/get_todos/", tags=['todo'], response_model=PaginateModel[Todo])
# page: int, per_page: int
async def read_todos(page: int, per_page: int) -> PaginateModel[TodoModel]:
    skip = (page - 1) * per_page
    limit = per_page
    total_items = await TodoModel.objects.count()
    items = await TodoModel.objects.order_by(TodoModel.create_time.asc()).offset(skip).limit(limit).select_related(['tags', 'user']).all()  # type: ignore
    return PaginateModel[TodoModel](page=page, items=items, per_page=per_page, total_items=total_items)


@app.delete("/delete_todos/{todo_id}", tags=['todo'])
async def delete_todos(todo_id: int):
    todo = await TodoModel.objects.get_or_none(id=todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    await todo.delete()
    return {"detail": "Todo deleted successfully"}


@app.delete("/delete_tag/{tag_id}", tags=['tag'])
async def delete_tags(tag_id: int):
    tag = await TagModel.objects.get_or_none(id=tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="tag not found")

    await tag.delete()
    return {"detail": "tag deleted successfully"}


@app.post("/update_todos/{todo_id}", tags=['todo'], response_model=Todo)
async def update_todos(updateDto: UpdateTodoDto, todo_id: int) -> TodoModel:
    todo = await TodoModel.objects.select_related('user').get_or_none(id=todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    todo.item = updateDto.item
    if updateDto.plan_time:
        todo.plan_time = updateDto.plan_time  # type: ignore
    todo.content = updateDto.content  # type: ignore
    todo.importance = updateDto.importance

    await todo.update()
    return todo


@app.get("/get_user_by_todo/{todo_id}", tags=['apis'], response_model=User)
async def get_user_by_todo(todo_id: int) -> UserModel:
    todo = await TodoModel.objects.select_related('user').get_or_none(id=todo_id)
    if not todo or not todo.user:
        raise HTTPException(status_code=404, detail="Todo or User not found")
    return todo.user


@app.get("/get_todos_by_user/{user_id}", tags=['apis'], response_model=PaginateModel[Todo])
async def read_todos_by_user(page: int, per_page: int, user_id: int) -> PaginateModel[TodoModel]:
    skip = (page - 1) * per_page
    limit = per_page
    total_items = await TodoModel.objects.filter(user=user_id).count()
    items = await TodoModel.objects.filter(user=user_id).select_related(['user', 'tags']).offset(skip).limit(limit).all()
    if not items:
        raise HTTPException(status_code=404, detail="User not found or no todos for this user")
    return PaginateModel[TodoModel](page=page, items=items, per_page=per_page, total_items=total_items)


@app.get("/get_todos_by_item_name/{item_name}", tags=['apis'], description="Get todos by the item name", response_model=PaginateModel[Todo])
async def get_todos_by_item_name(item_name: str, page: int, per_page: int) -> PaginateModel[TodoModel]:
    skip = (page - 1) * per_page
    limit = per_page
    total_items = await TodoModel.objects.filter(item__icontains=item_name).count()
    items = await TodoModel.objects.filter(item__icontains=item_name).select_related(['user', 'tags']).offset(skip).limit(limit).all()
    return PaginateModel[TodoModel](page=page, items=items, per_page=per_page, total_items=total_items)


@app.get("/get_todos_by_item_importance/{item_importance}", tags=['apis'], description="Get todos by the item importance", response_model=PaginateModel[Todo])
async def get_todos_by_importance(item_importance: Importance, page: int, per_page: int) -> PaginateModel[TodoModel]:
    skip = (page - 1) * per_page
    limit = per_page

    query = TodoModel.objects.filter(importance=item_importance)
    total_items = await query.count()
    items = await query.select_related(['user', 'tags']).offset(skip).limit(limit).all()

    return PaginateModel[TodoModel](page=page, items=items, per_page=per_page, total_items=total_items)


@app.get("/get_todo_by_todo_id/{todo_id}", tags=['apis'], description="Get todo by the todo_id", response_model=PaginateModel[Todo])
async def get_todo_by_todo_id(todo_id: int, page: int, per_page: int) -> PaginateModel[TodoModel]:
    skip = (page - 1) * per_page
    limit = per_page

    query = TodoModel.objects.filter(id=todo_id)
    total_items = await query.count()
    items = await query.select_related(['user', 'tags']).offset(skip).limit(limit).all()
    if not items:
        raise HTTPException(status_code=404, detail="Todo not found")

    return PaginateModel[TodoModel](page=page, items=items, per_page=per_page, total_items=total_items)


@app.get("/get_todos_by_plan_time/{plan_time_str}", tags=['apis'], description="Get todos by the plan time", response_model=PaginateModel[Todo])
async def get_todo_by_plan_time(plan_time_str: str, page: int, per_page: int) -> PaginateModel[TodoModel]:
    skip = (page - 1) * per_page
    limit = per_page

    if plan_time_str == "null":
        total_items = await TodoModel.objects.filter(plan_time=None).count()
        items = await TodoModel.objects.filter(plan_time=None).offset(skip).limit(limit).all()
    else:
        if len(plan_time_str) == len('2024-06-06 11'):
            plan_time_start = datetime.strptime(plan_time_str, "%Y-%m-%d %H")
            plan_time_end = plan_time_start + timedelta(hours=1)
        elif len(plan_time_str) == len('2024-06-06'):
            plan_time_start = datetime.strptime(plan_time_str, "%Y-%m-%d")
            plan_time_end = plan_time_start + timedelta(days=1)
        else:
            raise HTTPException(status_code=400, detail="Plan time format invalid!")

        total_items = await TodoModel.objects.filter(plan_time__gt=plan_time_start, plan_time__lt=plan_time_end).count()
        items = await TodoModel.objects.filter(plan_time__gt=plan_time_start, plan_time__lt=plan_time_end).offset(skip).limit(limit).all()

    return PaginateModel[TodoModel](page=page, items=items, per_page=per_page, total_items=total_items)
