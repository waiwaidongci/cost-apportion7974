export const pages=[['overview','业务总览'],['sources','业务底稿'],['fxexpenses','境外底稿'],['fxquotes','汇率报价'],['policies','口径版本'],['runs','核算与复核'],['fxruns','折算核算'],['deliveries','定时交付'],['audit','过程留痕']];
export const currentPage=()=>location.hash.slice(1)||'overview';
