import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from backend.db.models import Base

# Ortam değişkenlerinden (.env) Postgres bilgilerini çekiyoruz (Bulamazsa varsayılanları kullanır)
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.environ.get("POSTGRES_HOST", "postgres")
DB_NAME = os.environ.get("POSTGRES_DB", "smartdata")

# Dinamik bağlantı URL'sini oluştur
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db() -> None:
    Base.metadata.create_all(engine)

def get_session() -> Session:
    return SessionLocal()