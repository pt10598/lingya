const $=id=>document.getElementById(id);
const TS=window.TongState;
let state=TS.parse(location.search),pages=0,names={},latestSignature='',offeredSignature='',sequence=0;
const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e};
const today=()=>new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Taipei'});
function time(s){return s?new Date(s).toLocaleString('zh-TW',{timeZone:'Asia/Taipei',hour12:false}):'尚未同步'}
function external(text,url,cls){let e=node('a',text,cls);try{const u=new URL(url);if(!['https:','http:'].includes(u.protocol))return node('span',text,cls);e.href=u.href;e.target='_blank';e.rel='noopener noreferrer';return e}catch{return node('span',text,cls)}}
function detailLink(it,text){const a=node('a',text,'details-link');a.href='/events/'+encodeURIComponent(it.id)+'?back='+encodeURIComponent('/'+(TS.query(state)?'?'+TS.query(state):''));return a}
function card(it){
 const event=it.category==='活動課程',benefit=it.category==='補助福利';
 const c=node('article','', 'card '+(event?'event-card':benefit?'benefit-card':'notice-card'));
 c.append(node('h3',it.title));
 const facts=node('div','','card-facts');
 if(event){let dateText='日期尚未確認，點開看說明';if(it.starts)dateText=it.starts.replaceAll('-','／')+(it.ends&&it.ends!==it.starts?' 至 '+it.ends.replaceAll('-','／'):'');facts.append(node('p','活動日期：'+dateText));if(it.ends&&it.ends<today())facts.append(node('p','這個活動已結束','ended-label'))}
 else if(benefit&&it.deadline)facts.append(node('p',(it.deadline<today()?'公告截止日已過：':'公告截止日：')+it.deadline.replaceAll('-','／')));
 else if(it.published)facts.append(node('p','公告日期：'+it.published.replaceAll('-','／')));
 if(event)facts.append(node('p','地點：'+(it.location||'尚未提供，請查看官方公告')));
 if(it.source)facts.append(node('p','發布單位：'+(names[it.source]||it.source),'source-label'));
 c.append(facts,detailLink(it,event?'看活動詳情':benefit?'看補助說明':'看通知內容'));return c
}
function applyUI(){
 for(const k of ['q','source','category','scope','when'])if($(k))$(k).value=state[k];
 for(const b of document.querySelectorAll('[data-view]')){const active=b.dataset.view===state.view;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active))}
 for(const b of document.querySelectorAll('[data-when]')){const active=b.dataset.when===state.when;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active))}
 for(const b of document.querySelectorAll('#agency-buttons button')){const active=b.dataset.source===state.source;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active))}
 $('quick-times').hidden=state.view!=='events';$('home-sections').hidden=!TS.home(state);$('latest-panel').open=!TS.home(state);$('latest-panel').classList.toggle('results-open',!TS.home(state));
 $('results-title').textContent=({all:'最新消息',events:'活動清單',benefits:'補助與福利',notices:'生活通知'})[state.view];
 $('result-note').textContent=state.view==='events'?'這裡先顯示尚未結束的活動。日期不清楚的，會另外標示。':'點開消息，可看詳細內容與官方原文。';
 const labels=[];if(state.q)labels.push('正在找：'+state.q);if(state.source)labels.push('單位：'+(names[state.source]||state.source));if(state.category)labels.push(state.category);if(state.scope)labels.push(state.scope==='local'?'本區機關／提及本區':'全市適用');if(state.when)labels.push($('when').selectedOptions[0]?.textContent||state.when);
 $('active-filters').replaceChildren(...labels.map(x=>node('span',x,'active-chip')));$('clear').hidden=!labels.length&&state.view==='all';
 if(state.source||state.category||state.scope)$('advanced-filters').open=true;
}
function saveURL(replace=false){const q=TS.query(state);const u='/'+(q?'?'+q:'')+location.hash;history[replace?'replaceState':'pushState']({q},'',u)}
async function load({scroll=false}={}){
 const seq=++sequence;applyUI();$('count').textContent='讀取中…';
 try{const r=await fetch('/api/news?'+TS.query(state));if(!r.ok)throw Error();const d=await r.json();if(seq!==sequence)return;
 pages=d.pages;if(d.page!==state.page){state.page=d.page;saveURL(true)}
 $('items').replaceChildren(...d.items.map(card));$('count').textContent=`共 ${d.total} 則`;
 if(!d.items.length){const empty=node('div','','empty');empty.append(node('p',state.view==='events'?'目前沒有符合條件的活動。未提供日期或來源尚未同步的資訊，也可能未出現在這個篩選中。':'目前沒有符合這組條件的資訊，試著減少篩選或更換關鍵字。'));const clear=node('button','清除篩選');clear.onclick=()=>change({view:'all',q:'',source:'',category:'',scope:'',when:''});empty.append(clear);if(state.view==='events'){const unknown=node('button','查看日期待確認活動');unknown.onclick=()=>change({when:'undated'});empty.append(unknown)}$('items').append(empty)}
 $('page').textContent=pages?`${state.page} / ${pages}`:'0 / 0';$('prev').disabled=state.page<=1;$('next').disabled=state.page>=pages;
 if(scroll){$('results').scrollIntoView({block:'start',behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches?'auto':'smooth'});$('results').focus({preventScroll:true})}
 }catch{if(seq!==sequence)return;$('count').textContent='讀取失敗';$('items').replaceChildren(node('div','暫時無法讀取資料，請稍後重試。','empty'))}
}
function change(patch,{scroll=false}={}){state={...state,...patch,page:patch.page||1};saveURL();load({scroll})}
async function homeSections(){
 async function fill(id,params,label){try{const r=await fetch('/api/news?'+params);if(!r.ok)throw Error();const d=await r.json();$(id).replaceChildren(...d.items.slice(0,2).map(card));if(!d.items.length)$(id).append(node('div',label,'empty'))}catch{$(id).replaceChildren(node('p','暫時無法讀取，請使用上方查詢。','note'))}}
 await Promise.allSettled([fill('featured-events','view=events&when=upcoming','目前沒有已確認日期的近期活動，可到活動頁查看日期待確認消息。'),fill('featured-benefits','view=benefits','目前沒有已收錄的補助公告。')]);
 try{const r=await fetch('/api/highlights');if(!r.ok)return;const d=await r.json();$('important').replaceChildren();for(const i of d.items){const a=node('a',i.title,'important-row');a.href='/events/'+encodeURIComponent(i.id);a.append(node('span','點開看通知','notice-action'));$('important').append(a)}$('important-section').hidden=!d.items.length}catch{}
}
async function sourceStatus(initial=false){try{const r=await fetch('/api/sources');if(!r.ok)throw Error();const d=await r.json();
 let signature='';try{const revision=await fetch('/api/revision');if(revision.ok)signature=(await revision.json()).revision}catch{}
 const dates=d.map(s=>s.last_success).filter(Boolean).sort();const bad=d.filter(s=>['失敗','部分成功'].includes(s.status)).length;
 $('last').textContent=(dates.length?'最近成功同步 '+time(dates.at(-1)):'尚未成功同步')+(bad?' · 部分來源更新延遲':'');
 if(initial){$('source').replaceChildren(node('option','所有單位'));$('source').firstChild.value='';$('agency-buttons').replaceChildren();
 for(const s of [{id:'',name:'全部單位'},...d]){if(s.id){names[s.id]=s.name;const o=node('option',s.name);o.value=s.id;$('source').append(o)}const b=node('button',s.name,'agency-button');b.type='button';b.dataset.source=s.id;b.onclick=()=>change({source:s.id});$('agency-buttons').append(b)}
 $('source-list').replaceChildren();for(const s of d){const c=node('div','','source');c.append(node('strong',s.name),node('span',s.status==='失敗'?'更新延遲':s.status,'status'+(s.status==='失敗'?' bad':'')),node('p','最後成功 '+time(s.last_success)),external('官方入口 ↗',s.url));$('source-list').append(c)}latestSignature=signature;
 }else if(signature&&latestSignature&&signature!==latestSignature&&signature!==offeredSignature){offeredSignature=signature;$('refresh-news').hidden=false}
 if(initial)applyUI();
 }catch{$('last').textContent='來源狀態暫時無法取得，已收錄資料仍可查詢。'}}
for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>change({view:b.dataset.view,q:'',source:'',scope:'',when:'',category:''},{scroll:true});
for(const b of document.querySelectorAll('[data-when]'))b.onclick=()=>change({view:'events',when:b.dataset.when,category:''});
$('search-form').onsubmit=e=>{e.preventDefault();change({q:$('q').value.trim().slice(0,120)})};
for(const k of ['scope','source','category','when'])$(k).onchange=()=>{const patch={[k]:$(k).value};if(k==='when'&&patch.when){patch.view='events';patch.category=''}if(k==='category'&&patch.category){patch.view='all';patch.when=''}change(patch)};
$('clear').onclick=()=>change({view:'all',q:'',source:'',category:'',scope:'',when:''});
$('all-events').onclick=()=>change({view:'events',when:'',category:'',q:'',source:'',scope:''},{scroll:true});
$('all-benefits').onclick=()=>change({view:'benefits',when:'',category:'',q:'',source:'',scope:''},{scroll:true});
$('prev').onclick=()=>change({page:state.page-1},{scroll:true});$('next').onclick=()=>change({page:state.page+1},{scroll:true});
$('refresh-news').onclick=async()=>{latestSignature=offeredSignature;$('refresh-news').hidden=true;await load();if(TS.home(state))homeSections()};
window.addEventListener('popstate',()=>{state=TS.parse(location.search);load()});
(async()=>{await sourceStatus(true);await load();homeSections();if(location.hash==='#results')$('results').scrollIntoView({block:'start'});})();
setInterval(()=>sourceStatus(false),60000);
