(function(root){
const views=['all','events','benefits','notices'];
const whens=['','week','weekend','upcoming','undated','past'];
function parse(search){const p=new URLSearchParams(search);const n=Number(p.get('page'));return {view:views.includes(p.get('view'))?p.get('view'):'all',q:(p.get('q')||'').trim().slice(0,120),source:(p.get('source')||'').slice(0,100),category:(p.get('category')||'').slice(0,30),scope:['local','citywide'].includes(p.get('scope'))?p.get('scope'):'',when:whens.includes(p.get('when'))?p.get('when'):'',page:Number.isInteger(n)&&n>0?Math.min(n,10000):1}}
function query(s){const p=new URLSearchParams();for(const k of ['view','q','source','category','scope','when','page'])if(s[k]&&!(k==='view'&&s[k]==='all')&&!(k==='page'&&s[k]===1))p.set(k,String(s[k]));return p.toString()}
function home(s){return s.view==='all'&&!s.q&&!s.source&&!s.category&&!s.scope&&!s.when&&s.page===1}
const api={parse,query,home};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.TongState=api;
})(typeof window==='undefined'?{}:window);
