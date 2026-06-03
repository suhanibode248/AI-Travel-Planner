import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import bcrypt

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    password = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    trips = relationship("SavedTrip", back_populates="user")

class SavedTrip(Base):
    __tablename__ = 'saved_trip'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    share_id = Column(String(12), unique=True, nullable=False)
    destination = Column(String(200), nullable=False)
    days = Column(Integer)
    budget = Column(Integer)
    trip_type = Column(String(50))
    plan_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="trips")

# Setup SQLite database connection
DB_URI = "sqlite:///voyager.db"
engine = create_engine(DB_URI, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    # Seed admin user if not exists
    with get_db() as db:
        if not db.query(User).filter_by(username="admin").first():
            hashed = hash_password("admin123")
            admin_user = User(username="admin", email="admin@voyager.ai", name="Admin", password=hashed)
            db.add(admin_user)
            db.commit()

from contextlib import contextmanager
@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
