from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

app = FastAPI()

# Настройка подключения к SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# Создаем движок для работы с базой данных
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Создаем сессию для работы с базой данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем базовый класс для моделей SQLAlchemy
Base = declarative_base()

# Модель для пользователя (SQLAlchemy)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

# Модель для записи (SQLAlchemy)
class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(String)
    date = Column(DateTime, default=datetime.utcnow)
    summary = Column(String, nullable=True)

# Pydantic модели для пользователей и записей

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr

    class Config:
        orm_mode = True

class EntryResponse(BaseModel):
    id: int
    title: str
    content: str
    date: datetime
    summary: Optional[str] = None

    class Config:
        orm_mode = True

# Создаем таблицы, если их нет
Base.metadata.create_all(bind=engine)

# Вспомогательная база данных для пользователей
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CRUD операции для пользователей
@app.post("/register/", response_model=UserResponse)
def register(user: UserCreate, db: SessionLocal = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = User(email=user.email, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/login/")
def login(user: UserCreate, db: SessionLocal = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or db_user.password != user.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful"}

@app.post("/reset-password/")
def reset_password(email: EmailStr, db: SessionLocal = Depends(get_db)):
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Email not found")
    return {"message": f"Password reset link sent to {email}"}

# CRUD операции для записей
@app.post("/entries/", response_model=EntryResponse)
def create_entry(entry: EntryResponse, db: SessionLocal = Depends(get_db)):
    db_entry = Entry(**entry.dict())
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

@app.get("/entries/{entry_id}", response_model=EntryResponse)
def read_entry(entry_id: int, db: SessionLocal = Depends(get_db)):
    db_entry = db.query(Entry).filter(Entry.id == entry_id).first()
    if db_entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return db_entry

@app.put("/entries/{entry_id}", response_model=EntryResponse)
def update_entry(entry_id: int, updated_entry: EntryResponse, db: SessionLocal = Depends(get_db)):
    db_entry = db.query(Entry).filter(Entry.id == entry_id).first()
    if db_entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    db_entry.title = updated_entry.title
    db_entry.content = updated_entry.content
    db_entry.summary = updated_entry.summary
    db.commit()
    db.refresh(db_entry)
    return db_entry

@app.delete("/entries/{entry_id}")
def delete_entry(entry_id: int, db: SessionLocal = Depends(get_db)):
    db_entry = db.query(Entry).filter(Entry.id == entry_id).first()
    if db_entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    db.delete(db_entry)
    db.commit()
    return {"message": "Entry deleted"}

@app.get("/entries/", response_model=List[EntryResponse])
def list_entries(db: SessionLocal = Depends(get_db)):
    entries = db.query(Entry).all()
    return entries

# Модель для загрузки изображений
class Image(BaseModel):
    entry_id: int
    filename: str

# Папка для хранения изображений
IMAGE_DIR = "images"
os.makedirs(IMAGE_DIR, exist_ok=True)

@app.post("/entries/{entry_id}/images/")
async def upload_image(entry_id: int, file: UploadFile = File(...)):
    file_location = f"{IMAGE_DIR}/{entry_id}_{file.filename}"
    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())
    return {"message": f"Image uploaded to {file_location}"}

@app.delete("/entries/{entry_id}/images/{filename}")
def delete_image(entry_id: int, filename: str):
    file_location = f"{IMAGE_DIR}/{entry_id}_{filename}"
    if os.path.exists(file_location):
        os.remove(file_location)
        return {"message": f"Image {filename} deleted"}
    return {"error": "Image not found"}
