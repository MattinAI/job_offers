from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import settings

# Add connection pool settings
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,           
    max_overflow=settings.DATABASE_MAX_OVERFLOW,        
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,       
    pool_recycle=settings.DATABASE_POOL_RECYCLE,       
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  