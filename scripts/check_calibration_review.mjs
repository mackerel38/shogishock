import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync('reports/response_calibration/review.html', 'utf8');
if (!html.includes('人間の実際の選択率とモデル予測の比較')) throw Error('human-facing heading missing');
if (html.includes('abstain=true') || html.includes('exact_support=')) throw Error('internal label leaked');
for (const [, href] of html.matchAll(/href="([^"]+\.kif)"/g)) {
  const path = new URL(href, `file://${process.cwd()}/reports/response_calibration/review.html`);
  if (!fs.existsSync(path)) throw Error(`missing KIF ${path}`);
}
console.log('Human-facing heading and prose checks passed; KIF links resolved. This is not GUI visual QA.');
