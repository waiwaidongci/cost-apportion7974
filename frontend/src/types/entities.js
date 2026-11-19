// API实体字段约定：来源{id,natural_key,data}、口径{id,version,data}、报告{id,kind,status,snapshot,checksum,result,approved}、计划{next_at,enabled}、汇率报价与境外底稿{id,natural_key,data}。
export const ENTITY_KEYS=['sources','policies','runs','schedules','deliveries','fxquotes','fxexpenses'];
