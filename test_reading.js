const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
function check(blocked=false){
 const a={attrs:{},setAttribute(k,v){this.attrs[k]=v}},b={attrs:{},setAttribute(k,v){this.attrs[k]=v}};
 const root={dataset:{}},store={'lingyatong-text-size':'large'};
 const ctx=vm.createContext({document:{documentElement:root,getElementById:id=>id==='font-normal'?a:b},localStorage:{getItem(k){if(blocked)throw Error('blocked');return store[k]},setItem(k,v){if(blocked)throw Error('blocked');store[k]=v}}});
 vm.runInContext(fs.readFileSync('static/reading.js','utf8'),ctx);
 assert.equal(root.dataset.textSize,blocked?'normal':'large');a.onclick();assert.equal(root.dataset.textSize,'normal');assert.equal(a.attrs['aria-pressed'],'true');b.onclick();assert.equal(root.dataset.textSize,'large');assert.equal(b.attrs['aria-pressed'],'true');if(!blocked)assert.equal(store['lingyatong-text-size'],'large');
}
check();check(true);console.log('Font size controls passed: restore, normal/large toggle, aria state and blocked-storage fallback');
