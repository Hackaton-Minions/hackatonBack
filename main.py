from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
import databases

DATABASE_URL = "sqlite:///./test.db"

database = databases.Database(DATABASE_URL)
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()




# Определение моделей данных SQLAlchemy
class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    login = Column(String, unique=True, index=True)
    password = Column(String)


class Parent(Base):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    login = Column(String, unique=True, index=True)
    password = Column(String)

class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    login = Column(String, unique=True, index=True)
    password = Column(String)

class ParentStudent(Base):
    __tablename__ = "parent_students"

    id_parent = Column(Integer, ForeignKey("parents.id"), primary_key=True)
    id_student = Column(Integer, ForeignKey("students.id"), primary_key=True)

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    group_name = Column(String, index=True)

class TeacherGroup(Base):
    __tablename__ = "teacher_groups"

    teacher_id = Column(Integer, ForeignKey("teachers.id"), primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)

class GroupStudent(Base):
    __tablename__ = "group_students"

    student_id = Column(Integer, ForeignKey("students.id"), primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)

# Определение Pydantic моделей для валидации входных данных и ответов
class StudentCreate(BaseModel):
    name: str
    login: str
    password: str
class GroupCreate(BaseModel):
    group_name: str

class ParentCreate(BaseModel):
    name: str
    login: str
    password: str

class TeacherCreate(BaseModel):
    name: str
    login: str
    password: str

class StudentResponse(BaseModel):
    id: int
    name: str
    login: str

class ParentResponse(BaseModel):
    id: int
    name: str
    login: str

class TeacherResponse(BaseModel):
    id: int
    name: str
    login: str

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# ...

# Роуты для работы с данными
async def get_parent_id_by_name(parent_name: str):
    query = Parent.__table__.select().where(Parent.__table__.c.login == parent_name)
    result = await database.fetch_one(query)

    if result is None:
        raise HTTPException(status_code=404, detail="Parent not found")

    return result["id"]

async def get_group_id_by_name(group_name: str):
    query = Group.__table__.select().where(Group.__table__.c.group_name == group_name)
    result = await database.fetch_one(query)

    if result is None:
        raise HTTPException(status_code=404, detail="Group not found")

    return result["id"]
# Регистрация студента
@app.post("/register/student/", response_model=StudentResponse)
async def register_student(student: StudentCreate, group = str, parent_login=str):
    query = Student.__table__.insert().values(**student.dict())
    last_record_id = await database.execute(query)

    student = await database.fetch_one(Student.__table__.select().where(Student.id == last_record_id))

    #инициализация полей student_group

    g_id = await get_group_id_by_name(group)
    query = GroupStudent.__table__.insert().values(group_id=g_id, student_id=student.id)
    await database.execute(query)


    p_id = await get_parent_id_by_name(parent_login)
    query = ParentStudent.__table__.insert().values(id_parent = p_id, id_student = student.id)
    await database.execute(query)

    return student

# Регистрация родителя
@app.post("/register/parent/", response_model=ParentResponse)
async def register_parent(parent: ParentCreate):
    query = Parent.__table__.insert().values(**parent.dict())
    last_record_id = await database.execute(query)
    parent = await database.fetch_one(Parent.__table__.select().where(Parent.id == last_record_id))
    return parent

async def getIds(groups):
    query = select([Group.id]).where(Group.group_name.in_(groups))
    group_ids = await database.fetch_all(query)
    return group_ids

# Регистрация учителя
@app.post("/register/teacher/", response_model=TeacherResponse)
async def register_teacher(teacher: TeacherCreate, groups: list[str]):
    query = Teacher.__table__.insert().values(**teacher.dict())
    last_record_id = await database.execute(query)
    teacher = await database.fetch_one(Teacher.__table__.select().where(Teacher.id == last_record_id))


    #инициализация полей в таблицу Teacher_group


    ids = await getIds(groups)
    for (elem,) in ids:
        query = TeacherGroup.__table__.insert().values(teacher_id=teacher.id, group_id=elem)
        await database.execute(query)

    return teacher

# Получение учителей ребенка через родителя
@app.get("/teachers_by_parent/{parent_id}", response_model=list[TeacherResponse])
async def get_teachers_by_parent(parent_id: int):
    query = (
        select([Teacher])
        .join(TeacherGroup, TeacherGroup.c.teacher_id == Teacher.id)
        .join(Group, Group.id == TeacherGroup.c.group_id)
        .join(GroupStudent, GroupStudent.c.group_id == Group.id)
        .join(Student, Student.id == GroupStudent.c.student_id)
        .join(ParentStudent, ParentStudent.c.id_student == Student.id)
        .where(ParentStudent.c.id_parent == parent_id)
    )
    teachers = await database.fetch_all(query)
    return teachers


# Геттер для студентов
@app.get("/students/", response_model=list[StudentResponse])
async def get_students(skip: int = 0, limit: int = 10):
    query = Student.__table__.select().offset(skip).limit(limit)
    students = await database.fetch_all(query)
    return students

# Геттер для родителей
@app.get("/parents/", response_model=list[ParentResponse])
async def get_parents(skip: int = 0, limit: int = 10):
    query = Parent.__table__.select().offset(skip).limit(limit)
    parents = await database.fetch_all(query)
    return parents

# Геттер для учителей
@app.get("/teachers/", response_model=list[TeacherResponse])
async def get_teachers(skip: int = 0, limit: int = 10):
    query = Teacher.__table__.select().offset(skip).limit(limit)
    teachers = await database.fetch_all(query)
    return teachers
# ...
@app.post("/groups/create/")
async def create_group(group: GroupCreate):
    query = Group.__table__.insert().values(group_name=group.group_name)
    group_id = await database.execute(query)
    return {"id": group_id, **group.dict()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)
