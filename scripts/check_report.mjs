// Execute portable report code against a minimal DOM, without a browser.
// This verifies rendering and handlers, not visual layout or browser behaviour.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
for (const side of ['sente','gote']) {
  const html=fs.readFileSync(`reports/pass_pilot/report_${side}.html`,'utf8');
  const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
  const data=JSON.parse(scripts[0]);
  assert(data.rows.every(r=>r.attacker_side===side));
  const elements=new Map();
  const get=id=>{if(!elements.has(id))elements.set(id,{textContent:'',innerHTML:'',value:'',hidden:false,addEventListener(){},scrollIntoView(){}});return elements.get(id)};
  get('data').textContent=scripts[0]; get('sort').value='pass_sensitivity';get('filter').value='all';
  const context=vm.createContext({document:{getElementById:get,addEventListener(){}},window:{addEventListener(){}},location:{hash:''},history:{replaceState(){}},console});
  vm.runInContext(scripts[1],context);
  assert(get('cards').innerHTML.includes('候補前'));
  assert(get('raw').innerHTML.includes('data-pick='));
  const id=data.rows[0].candidate_id;
  vm.runInContext(`pick(${JSON.stringify(id)})`,context);
  assert(get('picked').innerHTML.includes(`selected-${id}`));
  get('filter').value='check';vm.runInContext('render()',context);
  assert(get('count').textContent.startsWith(`${data.rows.filter(r=>r.is_check).length}件`));
  get('filter').value='all';get('query').value=id;vm.runInContext('render()',context);
  assert(get('count').textContent.startsWith('1件'));
  console.log(`${side}: embedded data, chart links, board markup, selection and filtering OK (${data.rows.length} rows)`);
}
