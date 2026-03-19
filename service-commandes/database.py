from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@postgres-commandes:5432/commandes_db"
)

def create_engine_with_retry(url, retries=10, delay=3):
    for i in range(retries):
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                print("✅ Connecté à PostgreSQL !")
                return engine
        except Exception as e:
            print(f"⏳ Tentative {i+1}/{retries} - PostgreSQL pas prêt : {e}")
            time.sleep(delay)
    raise Exception("❌ Impossible de se connecter à PostgreSQL")

engine = create_engine_with_retry(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
