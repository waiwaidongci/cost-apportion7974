from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker,DeclarativeBase
from src.config.settings import DATABASE_URL
class Base(DeclarativeBase): pass
engine=create_engine(DATABASE_URL,pool_pre_ping=True)
Session=sessionmaker(bind=engine,expire_on_commit=False)
def database():
 with Session() as db: yield db
def ensure_schema():
 Base.metadata.create_all(engine)
 with engine.begin() as conn:
  conn.execute(text("ALTER TABLE allocationruns ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'cost'"))
