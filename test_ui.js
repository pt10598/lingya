// Run the real frontend against a small DOM/fetch harness (not a browser rendering test).
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class El{
 constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.dataset={};this.hidden=false;this.textContent='';this.attrs={};this.classList={toggle(){}}}
 append(...x){this.children.push(...x)}replaceChildren(...x){this.children=x}get firstChild(){return this.children[0]}get selectedOptions(){return [{textContent:this.value}]}
 setAttribute(k,v){this.attrs[k]=v}scrollIntoView(){this.scrolled=true}focus(){this.focused=true}
}
const ids=['q','source','category','scope','when','items','count','results','results-title','result-note','quick-times','home-sections','active-filters','clear','advanced-filters','prev','next','page','source-list','agency-buttons','last','refresh-news','featured-events','featured-benefits','important','important-section','search-form','all-events','all-benefits'];
const els=Object.fromEntries(ids.map(id=>[id,new El()]));
const views=['all','events','benefits','notices'].map(view=>{const e=new El('button');e.dataset.view=view;return e});
const whens=['','week','weekend','undated','past'].map(when=>{const e=new El('button');e.dataset.when=when;return e});
const win={SITE:{short:'苓雅',district:'苓雅區'},events:{},addEventListener(n,fn){this.events[n]=fn}};
const location={search:'',hash:''};const history={pushState(s,t,url){const u=new URL(url,'https://test.example');location.search=u.search;location.hash=u.hash},replaceState(s,t,url){this.pushState(s,t,url)}};
let revision='one',poll;
const row={id:'1',title:'親子活動',category:'活動課程',source:'lingya-office',published:'2026-10-20',starts:'2026-10-24',ends:'2026-10-24',summary:'活動內容',url:'https://example.org/event',topics:['親子'],location:'苓雅區某場館'};
async function fetch(url){const u=new URL(url,'https://test.example');let d;if(u.pathname==='/api/sources')d=[{id:'lingya-office',name:'苓雅區公所',status:'成功',last_success:'2026-10-20T00:00:00Z',url:'https://example.org/'}];else if(u.pathname==='/api/revision')d={revision};else if(u.pathname==='/api/highlights')d={items:[]};else d={items:[row],total:1,page:1,pages:1};return {ok:true,json:async()=>d}}
const context=vm.createContext({window:win,document:{getElementById:id=>els[id],createElement:tag=>new El(tag),querySelectorAll:sel=>sel==='[data-view]'?views:sel==='[data-when]'?whens:sel==='#agency-buttons button'?els['agency-buttons'].children:[]},location,history,fetch,URL,URLSearchParams,Date,console,setInterval:fn=>{poll=fn}});
vm.runInContext(fs.readFileSync('static/state.js','utf8'),context);vm.runInContext(fs.readFileSync('static/app.js','utf8'),context);
const settle=async()=>{for(let i=0;i<12;i++)await new Promise(setImmediate)};
(async()=>{
 await settle();assert.equal(els['items'].children.length,1);assert.equal(els['agency-buttons'].children.length,2);
 views[1].onclick();await settle();assert.match(location.search,/view=events/);assert.equal(els['quick-times'].hidden,false);
 els.q.value='親子';els['search-form'].onsubmit({preventDefault(){}});await settle();assert.match(location.search,/q=/);
 const href=els['items'].children[0].children.find(x=>x.className==='details-link').href;assert.match(href,/back=/);
 els.q.value='尚未送出的輸入';revision='two';await poll();await settle();assert.equal(els.q.value,'尚未送出的輸入');assert.equal(els['refresh-news'].hidden,false);
 await els['refresh-news'].onclick();await settle();assert.equal(els['refresh-news'].hidden,true);
 els.clear.onclick();await settle();assert.equal(location.search,'');assert.equal(els['home-sections'].hidden,false);
 location.search='?view=benefits&q=扶助';win.events.popstate();await settle();assert.equal(els.q.value,'扶助');assert.equal(els['results-title'].textContent,'補助與福利');
 console.log('Frontend flow passed: view tabs, search, return URL, non-destructive polling, refresh, clear and history');
})().catch(e=>{console.error(e);process.exitCode=1});
