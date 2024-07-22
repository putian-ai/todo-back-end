import ormar
import databases
import sqlalchemy
from enum import Enum
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from contextlib import asynccontextmanager
from typing import Generic, Optional, TypeVar, Sequence
from fastapi.middleware.cors import CORSMiddleware


sqlite_file_name = "todo.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = sqlalchemy.create_engine(sqlite_url)  # type: ignore
base_ormar_config = ormar.OrmarConfig(
    metadata=sqlalchemy.MetaData(),  # type: ignore
    database=databases.Database(sqlite_url),
    engine=engine,  # type: ignore
)


T = TypeVar('T')


class User(ormar.Model):
    ormar_config = base_ormar_config.copy(tablename="users")

    id: int = ormar.Integer(primary_key=True)  # type: ignore
    user_name: str = ormar.String(min_length=3, max_length=12)  # type: ignore
    pwd: str = ormar.String(min_length=3, max_length=12)  # type: ignore
    

class IMPORTANCE(int, Enum):
    NONE = 0
    LOW = 1
    MIDDLE = 2
    HIGH = 3


class Todo(ormar.Model):
    ormar_config = base_ormar_config.copy(tablename="todos")

    id: int = ormar.Integer(primary_key=True, required=True)  # type: ignore
    item: str = ormar.String(index=True, max_length=1000)  # type: ignore
    create_time: datetime = ormar.DateTime(default=datetime.now())  # type: ignore

    plan_time: Optional[datetime] = ormar.DateTime(nullable=True)  # type: ignore
    content: Optional[str] = ormar.String(nullable=True, max_length=5000)  # type: ignore
    user_id: int = ormar.Integer(default=None, foreign_key="user.id")  # type: ignore
    user: User = ormar.ForeignKey(User, related_name='todo_list')
    importance: int = ormar.Integer(default=IMPORTANCE.NONE.value) # type: ignore
    
    @property
    def importance_enum(self) -> IMPORTANCE:
        return IMPORTANCE(self.importance)

    @importance_enum.setter
    def importance_enum(self, value: IMPORTANCE):
        self.importance = value.value



class UserDto(BaseModel):
    user_name: str
    pwd: str


class TodoDto(BaseModel):
    item: str
    plan_time: str
    user_id: int
    content: str
    importance: IMPORTANCE

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
    importance: IMPORTANCE
    
    
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


async def pagniate_todos(page: int, per_page: int) -> PaginateModel[Todo]:
    total_items = await Todo.objects.count()
    todos = await Todo.objects.limit(per_page).offset((page-1)*per_page).all()
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
    for i in range(len(init_todos)):
        init_todo = init_todos[i]
        init_todo_user_id = init_todo_user_ids[i % 4]
        user = await User.objects.get(id=init_todo_user_id)
        todo = Todo(item=init_todo, plan_time=datetime.now(), user_id=init_todo_user_id, user=user, content="Hello", importance = IMPORTANCE.MIDDLE)  # type: ignore
        await todo.save()


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


@app.post("/create_users/", tags=['user'])
async def create_user(userDto: UserDto) -> User:
    user = User(user_name=userDto.user_name, pwd=userDto.pwd)
    await user.save()
    return user


@app.post("/create_todos/", tags=['todo'])
async def create_todo(todoDto: TodoDto) -> Todo:
    user = await User.objects.get_or_none(id=todoDto.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User does not exist!")

    todo = Todo(item=todoDto.item, plan_time=todoDto.plan_time, user_id=todoDto.user_id, content=todoDto.content, importance = todoDto.importance.value)

    await todo.save()
    return todo


@app.get("/get_todos/", tags=['todo'])
# page: int, per_page: int
async def read_todos(page: int, per_page: int) -> PaginateModel[Todo]:
    skip = (page - 1) * per_page
    limit = per_page
    total_items = await Todo.objects.count()
    items = await Todo.objects.order_by(Todo.create_time.asc()).offset(skip).limit(limit).all()  # type: ignore
    return PaginateModel[Todo](page=page, items=items, per_page=per_page, total_items=total_items)


@app.delete("/delete_todos/{todo_id}", tags=['todo'])
async def delete_todos(todo_id: int):
    todo = await Todo.objects.get_or_none(id=todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    await todo.delete()
    return {"detail": "Todo deleted successfully"}


@app.post("/update_todos/{todo_id}", tags=['todo'])
async def update_todos(updateDto: UpdateTodoDto, todo_id: int) -> Todo:
    todo = await Todo.objects.get_or_none(id=todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    todo.item = updateDto.item
    if updateDto.plan_time:
        todo.plan_time = updateDto.plan_time  # type: ignore
    todo.content = updateDto.content  # type: ignore
    todo.importance = updateDto.importance # type: ignore

    await todo.update()
    return todo


@app.get("/get_user_by_todo/{todo_id}", tags=['apis'])
async def get_user_by_todo(todo_id: int) -> User:
    todo = await Todo.objects.select_related('user').get_or_none(id=todo_id)
    if not todo or not todo.user:
        raise HTTPException(status_code=404, detail="Todo or User not found")
    return todo.user


@app.get("/get_todos_by_user/{user_id}", tags=['apis'])
async def read_todos_by_user(page: int, per_page: int, user_id: int) -> PaginateModel[Todo]:
    skip = (page - 1) * per_page
    limit = per_page
    total_items = await Todo.objects.filter(user_id=user_id).count()
    items = await Todo.objects.filter(user_id=user_id).offset(skip).limit(limit).all()
    if not items:
        raise HTTPException(status_code=404, detail="User not found or no todos for this user")
    return PaginateModel[Todo](page=page, items=items, per_page=per_page, total_items=total_items)


@app.get("/get_todos_by_item_name/{item_name}", tags=['apis'], description="Get todos by the item name")
async def get_todos_by_item_name(item_name: str, page: int, per_page: int) -> PaginateModel[Todo]:
    skip = (page - 1) * per_page
    limit = per_page
    total_items = await Todo.objects.filter(item__icontains=item_name).count()
    items = await Todo.objects.filter(item__icontains=item_name).offset(skip).limit(limit).all()
    return PaginateModel[Todo](page=page, items=items, per_page=per_page, total_items=total_items)

@app.get("/get_todos_by_item_importance/{item_importance}", tags=['apis'], description="Get todos by the item importance")
async def get_todos_by_importance(item_importance: IMPORTANCE, page: int, per_page: int) -> PaginateModel[Todo]:
    skip = (page - 1) * per_page
    limit = per_page
    
    query = Todo.objects.filter(importance = item_importance.value)
    total_items = await query.count()
    items = await query.offset(skip).limit(limit).all()

    return PaginateModel[Todo](page=page, items=items, per_page=per_page, total_items= total_items)


@app.get("/get_todos_by_plan_time/{plan_time_str}", tags=['apis'], description="Get todos by the plan time")
async def get_todo_by_plan_time(plan_time_str: str, page: int, per_page: int) -> PaginateModel[Todo]:
    skip = (page - 1) * per_page
    limit = per_page

    if plan_time_str == "null":
        total_items = await Todo.objects.filter(plan_time=None).count()
        items = await Todo.objects.filter(plan_time=None).offset(skip).limit(limit).all()
    else:
        if len(plan_time_str) == len('2024-06-06 11'):
            plan_time_start = datetime.strptime(plan_time_str, "%Y-%m-%d %H")
            plan_time_end = plan_time_start + timedelta(hours=1)
        elif len(plan_time_str) == len('2024-06-06'):
            plan_time_start = datetime.strptime(plan_time_str, "%Y-%m-%d")
            plan_time_end = plan_time_start + timedelta(days=1)
        else:
            raise HTTPException(status_code=400, detail="Plan time format invalid!")

        total_items = await Todo.objects.filter(plan_time__gt=plan_time_start, plan_time__lt=plan_time_end).count()
        items = await Todo.objects.filter(plan_time__gt=plan_time_start, plan_time__lt=plan_time_end).offset(skip).limit(limit).all()

    return PaginateModel[Todo](page=page, items=items, per_page=per_page, total_items=total_items)
