from sqlalchemy import Column,Integer,String,JSON
from src.config.database import Base
class FxQuote(Base):
 __tablename__='fxquotes'
 id=Column(Integer,primary_key=True); natural_key=Column(String(120),unique=True); data=Column(JSON,nullable=False)
class FxExpense(Base):
 __tablename__='fxexpenses'
 id=Column(Integer,primary_key=True); natural_key=Column(String(120),unique=True); data=Column(JSON,nullable=False)
