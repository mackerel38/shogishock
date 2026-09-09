// DOM-only regression check; not a claim of browser visual inspection.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
for (const side of ['sente','gote']) {
  const html=fs.readFileSync(`reports/reach_pilot/report_${side}.html`,'utf8');
  const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
  const data=JSON.parse(scripts[0]), elements=new Map();
  const get=id=>{if(!elements.has(id))elements.set(id,{textContent:'',innerHTML:'',value:'',addEventListener(){}});return elements.get(id)};
  get('data').textContent=scripts[0];get('sort').value='pass_sensitivity';
  const ctx=vm.createContext({document:{getElementById:get},console});
  vm.runInContext(scripts[1],ctx);
  assert(data.rows.every(r=>r.attacker_side===side));
  assert.equal((get('cards').innerHTML.match(/<article /g)||[]).length,data.rows.length);
  assert.equal((get('cards').innerHTML.match(/<svg /g)||[]).length,2*data.rows.length);
  assert(!get('cards').innerHTML.includes('undefined'));
  for(const r of data.rows)assert(get('plots').innerHTML.includes(`href="#${r.candidate_id}"`));
  get('sort').value='ply';vm.runInContext('render()',ctx);
  assert(get('reach').innerHTML.includes('sample reach'));
  console.log(`${side}: ${data.rows.length} cards, boards, plot anchors, sorting OK`);
}
