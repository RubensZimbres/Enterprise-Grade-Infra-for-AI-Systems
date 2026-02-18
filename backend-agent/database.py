from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# Get DB URL from settings (loaded from Secret Manager)
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Configure connection pooling for db-g1-small (approx 25-50 max connections)
# 20 instances * 5 pool = 100 (potential over-subscription, but safe with low concurrency per instance)
# Realistically, typical load will be lower.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,  # Wait 30s for a connection before failing
    pool_recycle=1800,  # Recycle connections every 30 mins
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
