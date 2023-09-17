import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, select, func
from sqlalchemy.orm import sessionmaker, Session, aliased
from sqlalchemy.ext.declarative import declarative_base
import databases

DATABASE_URL = "sqlite:///./test4.db"

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
    subject = Column(String)


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


class Event(Base):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True, index=True)
    day = Column(String)
    time = Column(String)
    user_type = Column(String)
    id_user = Column(Integer)
    id_teacher = Column(Integer)
    name_teacher = Column(String)
    subject = Column(String)


# Определение Pydantic моделей для валидации входных данных и ответов

class GroupStudentCreate(BaseModel):
    student_id: int
    group_id: int

class ParentStudentCreate(BaseModel):
    id_parent: int
    id_student: int

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
    subject: str


class EventCreate(BaseModel):
    day: str
    time: str
    user_type: str
    id_user: int
    id_teacher: int
    name_teacher: str
    subject: str

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
    subject: str


class EventResponse(BaseModel):
    id: int
    day: str
    time: str
    user_type: str
    id_user: int
    id_teacher: int
    name_teacher: str
    subject: str

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# ...


# Роуты для работы с данными
@app.get("/get_parent_id/")
async def get_parent_id_by_name(parent_name: str):
    query = Parent.__table__.select().where(Parent.__table__.c.name == parent_name)
    result = await database.fetch_one(query)

    if result is None:
        return {}

    return {"parent_id": result["id"]}


@app.get("/get_student_id/")
async def get_student_by_name(student_name: str):
    query = select([Student.id]).where(Student.name == student_name)
    result = await database.fetch_one(query)

    if result:
        return {"student_id": result["id"]}
    else:
        return {}

@app.get("/get_group_id/")
async def get_group_id_by_name(group_name: str):
    query = Group.__table__.select().where(Group.__table__.c.group_name == group_name)
    result = await database.fetch_one(query)

    if result is None:
        return {}

    return {"group_id": result["id"]}

@app.get("/get_teacher_id/")
async def get_teacher_id_by_name(teacher_name: str):
    query = Teacher.__table__.select().where(Teacher.__table__.c.name == teacher_name)
    result = await database.fetch_one(query)

    if result is None:
        return {}

    return {"teacher_id": result["id"]}


@app.get("/get_event_by_user/")
async def get_event_by_user(user_type: str, user_id: int):
    if user_type not in ["parent", "student"]:
        return {}

    user_events = select([Event.day, Event.time, Event.name_teacher, Event.subject]).where(Event.user_type == user_type, Event.id_user == user_id)

    results = await database.fetch_all(user_events)

    return results


# Регистрация студента
@app.post("/register/student/", response_model=StudentResponse)
async def register_student(student: StudentCreate, group: str, parent_login: str):
    try:
        # Вставляем данные о студенте в таблицу students
        query = Student.__table__.insert().values(
            name=student.name,
            login=student.login,
            password=student.password
        )

        login = student.login

        student_query = select([func.count()]).select_from(Student.__table__).where(Student.login == login)
        student_count = await database.fetch_val(student_query)

        # Подсчитываем количество записей в таблице Parent, где login совпадает
        parent_query = select([func.count()]).select_from(Parent.__table__).where(Parent.login == login)
        parent_count = await database.fetch_val(parent_query)

        # Подсчитываем количество записей в таблице Teacher, где login совпадает
        teacher_query = select([func.count()]).select_from(Teacher.__table__).where(Teacher.login == login)
        teacher_count = await database.fetch_val(teacher_query)

        total_count = student_count + parent_count + teacher_count

        fl = total_count > 0

        if not fl:
            last_record_id = await database.execute(query)

            # Получаем информацию о зарегистрированном студенте
            student = await database.fetch_one(
                Student.__table__.select().where(Student.id == last_record_id)
            )

            # Получаем ID группы по её имени
            g_id = await get_group_id_by_name(group)
            g_id = g_id.get("group_id")

            # Добавляем запись в таблицу group_students
            query = GroupStudent.__table__.insert().values(
                group_id=g_id,
                student_id=student.id
            )
            await database.execute(query)

            # Получаем ID родителя по его логину
            p_id = await get_parent_id_by_name(parent_login)
            p_id = p_id.get('parent_id')

            # Добавляем запись в таблицу parent_students
            query = ParentStudent.__table__.insert().values(
                id_parent=p_id,
                id_student=student.id
            )
            await database.execute(query)

            return StudentResponse(id=student.id, name=student.name, login=student.login)

        else:
            raise HTTPException(status_code=505, detail="This login already exists")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/create_event/", response_model=EventCreate)
async def create_event(event: EventCreate):
    query = Event.__table__.insert().values(**event.dict())
    await database.execute(query)
    return event


# Регистрация родителя
@app.post("/register/parent/", response_model=ParentResponse)
async def register_parent(parent: ParentCreate):
    query = Parent.__table__.insert().values(**parent.dict())
    login = parent.login

    student_query = select([func.count()]).select_from(Student.__table__).where(Student.login == login)
    student_count = await database.fetch_val(student_query)

    # Подсчитываем количество записей в таблице Parent, где login совпадает
    parent_query = select([func.count()]).select_from(Parent.__table__).where(Parent.login == login)
    parent_count = await database.fetch_val(parent_query)

    # Подсчитываем количество записей в таблице Teacher, где login совпадает
    teacher_query = select([func.count()]).select_from(Teacher.__table__).where(Teacher.login == login)
    teacher_count = await database.fetch_val(teacher_query)

    total_count = student_count + parent_count + teacher_count

    fl = total_count > 0

    if not fl:
        last_record_id = await database.execute(query)
        parent = await database.fetch_one(Parent.__table__.select().where(Parent.id == last_record_id))
        return parent
    else:
        raise HTTPException(status_code=500, detail="This login already exists")


async def getIds(groups):
    query = select([Group.id]).where(Group.group_name.in_(groups))
    group_ids = await database.fetch_all(query)
    return group_ids

# Регистрация учителя
@app.post("/register/teacher/", response_model=TeacherResponse)
async def register_teacher(teacher: TeacherCreate, groups: list[str]):
    query = Teacher.__table__.insert().values(**teacher.dict())

    login = teacher.login

    student_query = select([func.count()]).select_from(Student.__table__).where(Student.login == login)
    student_count = await database.fetch_val(student_query)

    # Подсчитываем количество записей в таблице Parent, где login совпадает
    parent_query = select([func.count()]).select_from(Parent.__table__).where(Parent.login == login)
    parent_count = await database.fetch_val(parent_query)

    # Подсчитываем количество записей в таблице Teacher, где login совпадает
    teacher_query = select([func.count()]).select_from(Teacher.__table__).where(Teacher.login == login)
    teacher_count = await database.fetch_val(teacher_query)

    total_count = student_count + parent_count + teacher_count

    fl = total_count > 0

    if not fl:
        last_record_id = await database.execute(query)
        teacher = await database.fetch_one(Teacher.__table__.select().where(Teacher.id == last_record_id))

        ids = await getIds(groups)
        for (elem,) in ids:
            query = TeacherGroup.__table__.insert().values(teacher_id=teacher.id, group_id=elem)
            await database.execute(query)

        return teacher

    else:
        raise HTTPException(status_code=500, detail="This login already exists")


    #инициализация полей в таблицу Teacher_group






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


@app.get("/get_event/")
async def get_event(teacher_id: int):
    query = Event.__table__.select().where(Event.id_teacher == teacher_id)
    results = await database.fetch_all(query)

    if results:
        return results
    else:
        return {}


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
