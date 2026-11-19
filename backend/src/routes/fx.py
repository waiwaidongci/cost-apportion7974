from fastapi import APIRouter,Depends
from src.config.database import database
from src.controllers.auth import current,editor
from src.models.fx import FxQuote,FxExpense
from src.schemas.requests import DataInput,RunInput
from src.services.fxstore import save_fx_quote,save_fx_expense,delete_fx_quote,delete_fx_expense
from src.services.report import submit_fx
from src.utils.serialize import row
router=APIRouter()
@router.get('/fx-quotes')
def quotes(db=Depends(database),u=Depends(current)): return [row(x) for x in db.query(FxQuote).order_by(FxQuote.id).all()]
@router.post('/fx-quotes')
def create_quote(b:DataInput,db=Depends(database),u=Depends(editor)): return row(save_fx_quote(db,u,b.data))
@router.put('/fx-quotes/{id}')
def update_quote(id:int,b:DataInput,db=Depends(database),u=Depends(editor)): return row(save_fx_quote(db,u,b.data,id))
@router.delete('/fx-quotes/{id}')
def remove_quote(id:int,db=Depends(database),u=Depends(editor)): return delete_fx_quote(db,u,id)
@router.get('/fx-expenses')
def expenses(db=Depends(database),u=Depends(current)): return [row(x) for x in db.query(FxExpense).order_by(FxExpense.id).all()]
@router.post('/fx-expenses')
def create_expense(b:DataInput,db=Depends(database),u=Depends(editor)): return row(save_fx_expense(db,u,b.data))
@router.put('/fx-expenses/{id}')
def update_expense(id:int,b:DataInput,db=Depends(database),u=Depends(editor)): return row(save_fx_expense(db,u,b.data,id))
@router.delete('/fx-expenses/{id}')
def remove_expense(id:int,db=Depends(database),u=Depends(editor)): return delete_fx_expense(db,u,id)
@router.post('/fx-runs')
def create_run(b:RunInput,db=Depends(database),u=Depends(editor)): return row(submit_fx(db,u,b))
