import {request} from './client.js';
export const loadAll=async()=>Object.fromEntries(await Promise.all(['sources','periods','policies','runs','schedules','deliveries','audits','fx-quotes','fx-expenses'].map(async k=>[k.replace('-',''),await request('/'+k)])));
export const saveSource=(data,id)=>request('/sources'+(id?'/'+id:''),id?'PUT':'POST',{data});
export const savePolicy=data=>request('/policies','POST',{data});
export const submitRun=data=>request('/runs','POST',data);
export const approveRun=(id,note)=>request('/runs/'+id+'/approve','POST',{note});
export const saveFxQuote=(data,id)=>request('/fx-quotes'+(id?'/'+id:''),id?'PUT':'POST',{data});
export const saveFxExpense=(data,id)=>request('/fx-expenses'+(id?'/'+id:''),id?'PUT':'POST',{data});
export const submitFxRun=data=>request('/fx-runs','POST',data);
