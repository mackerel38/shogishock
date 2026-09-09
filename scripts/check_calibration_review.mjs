import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync('reports/response_calibration/review.html', 'utf8');
const sfens = [...html.matchAll(/data-sfen="([^"]+)"/g)].map(m => m[1]);
const elements = sfens.map(sfen => ({ getAttribute: () => sfen, innerHTML: '' }));
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
for (const script of scripts) vm.runInNewContext(script[1], {document: {querySelectorAll: () => elements}});
if (elements.length !== 6 || elements.some(e => !e.innerHTML.includes('<svg'))) throw Error('board render failure');
for (const [, href] of html.matchAll(/href="([^"]+\.kif)"/g)) {
  const path = new URL(href, `file://${process.cwd()}/reports/response_calibration/review.html`);
  if (!fs.existsSync(path)) throw Error(`missing KIF ${path}`);
}
console.log('Six board SVGs rendered; three KIF links resolved. This is not GUI visual QA.');
