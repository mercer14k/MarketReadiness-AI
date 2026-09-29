import { test, expect } from '../../apps/web/node_modules/@playwright/test';
import AxeBuilder from '../../apps/web/node_modules/@axe-core/playwright';

test('portfolio → evidence → scenario → transfers → grounded brief', async ({page}) => {
  const errors: string[] = []; page.on('pageerror',e => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Deployment readiness.'})).toBeVisible();
  await expect(page.getByText('85%',{exact:true}).first()).toBeVisible();
  await page.screenshot({path:'../../docs/images/portfolio.png',fullPage:true});
  await page.screenshot({path:'../../docs/images/overview.png'});
  await page.getByRole('button',{name:'View Austin evidence'}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByText('10 days late',{exact:true})).toBeVisible();
  await page.screenshot({path:'../../docs/images/market-evidence.png'});
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button',{name:'Run a scenario'}).click();
  await page.getByRole('button',{name:'Run comparison',exact:true}).click();
  await expect(page.getByText('Change',{exact:true})).toBeVisible();
  await page.screenshot({path:'../../docs/images/scenario.png',fullPage:true});
  await page.getByRole('button',{name:'Transfer planner',exact:true}).click();
  await expect(page.getByRole('heading',{name:/Feasible transfers/})).toBeVisible();
  await expect(page.getByRole('button',{name:'Inspect'}).first()).toBeVisible();
  await page.getByRole('button',{name:'Inspect'}).first().click();
  await expect(page.getByRole('heading',{name:'Transfer evidence'})).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Readiness brief',exact:true}).click();
  await page.getByRole('button',{name:'Generate brief'}).click();
  await expect(page.getByText('DETERMINISTIC NARRATIVE')).toBeVisible();
  await expect(page.getByText('Material constraints need attention',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Demand forecast',exact:true}).click();
  await expect(page.getByText('Backtest MAE',{exact:true})).toBeVisible();
  await expect(page.getByRole('img',{name:/Fourteen-day/})).toBeVisible();
  expect(errors).toEqual([]);
});

test('filters, import errors, keyboard and responsive layout', async ({page}) => {
  await page.goto('/');
  await page.getByRole('textbox',{name:'Search markets'}).fill('Phoenix');
  await expect(page.getByRole('button',{name:'Phoenix',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Austin',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Data & provenance'}).click();
  await expect(page.getByText('RAW RECORDS',{exact:true})).toBeVisible();
  await page.getByLabel('Import JSON dataset').setInputFiles({name:'broken.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({id:'browser-invalid',markets:[]}))});
  await expect(page.getByText('Rejected',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Portfolio overview'}).click();
  await expect(page.getByText('85%',{exact:true}).first()).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  await expect(page.getByRole('heading',{name:'Deployment readiness.'})).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await expect.poll(() => page.locator('aside').evaluate(el => el.getBoundingClientRect().right)).toBeLessThanOrEqual(0);
  await page.screenshot({path:'../../docs/images/mobile.png',fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'Toggle navigation'}).click();
  await page.getByRole('button',{name:'Architecture',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Built on evidence.'})).toBeVisible();
});

test('portfolio has no serious or critical accessibility violations', async ({page}) => {
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Deployment readiness.'})).toBeVisible();
  const results = await new AxeBuilder({page}).analyze();
  expect(results.violations.filter(v => ['serious','critical'].includes(v.impact || ''))).toEqual([]);
});
