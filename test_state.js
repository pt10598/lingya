const assert=require('node:assert/strict');const S=require('./static/state.js');
const s=S.parse('?view=events&q=%E8%A6%AA%E5%AD%90&source=lingya-office&page=3&when=weekend');
assert.equal(s.q,'親子');assert.equal(s.page,3);assert.deepEqual(S.parse(S.query(s)),s);
assert.equal(S.parse('?page=-2&view=bad').page,1);assert.equal(S.parse('?page=999999').page,10000);
assert.equal(S.home(S.parse('')),true);assert.equal(S.home(s),false);
assert.equal(S.parse('?q='+encodeURIComponent('a'.repeat(200))).q.length,120);
console.log('URL state: round-trip, filters, pagination and input bounds passed');
