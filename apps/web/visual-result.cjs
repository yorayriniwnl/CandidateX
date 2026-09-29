const {chromium,expect}=require('@playwright/test');
const fs=require('fs');const path=require('path');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chromium'});const page=await browser.newPage({viewport:{width:1280,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 const dir=path.resolve(__dirname,'../../artifacts/result-redesign')+'/';const result=JSON.parse(fs.readFileSync(dir+'live-result.json','utf8'));
 await page.route('**/api/live/intake',r=>r.fulfill({json:result.intake}));await page.route('**/api/live/analyze',r=>r.fulfill({json:result}));await page.goto((process.env.VISUAL_BASE_URL || 'http://127.0.0.1:3000')+'/analyze');await page.locator('#resume-upload').setInputFiles(dir+'resume.pdf');for(const name of ['Continue to target role','Continue to public sources','Continue to review','Start live analysis'])await page.getByRole('button',{name,exact:true}).click();await page.getByRole('region',{name:'Live candidate dossier',exact:true}).waitFor();

 for(const width of [1440,1280,1024,390]){await page.setViewportSize({width,height:900});await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({animations:'disabled',path:dir+'after-'+width+'.png'});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Overflow at '+width);}
 async function capture(id, name) { await page.locator(id).evaluate(el=>window.scrollTo({top:el.getBoundingClientRect().top+scrollY-140,behavior:'instant'})); await expect(page.getByRole('navigation',{name:'Dossier sections'}).locator('[aria-current]')).toHaveAttribute('href', id); await page.screenshot({animations:'disabled',path:dir+name+'.png'}); }
 await page.setViewportSize({width:1280,height:900});await page.locator('#capabilities').getByRole('button',{name:/Backend Engineering/}).click();await capture('#capabilities', 'capabilities');
 await page.getByRole('region',{name:'Observed engineering signals'}).getByRole('button').first().click();await expect(page.getByRole('dialog')).toBeVisible();await page.screenshot({animations:'disabled',path:dir+'inspector.png'});await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);
 await page.locator('#claims').getByRole('button').first().click();await capture('#claims', 'claims');
 await page.locator('#sources summary').filter({hasText:/Engineering fingerprint & technical details/}).click();await capture('#sources', 'repository');
 await page.getByRole('button',{name:/Inspect all evidence/}).click();await page.getByLabel('Search evidence',{exact:true}).fill('celery');await capture('#evidence', 'ledger');
 await capture('#interview', 'interview');const invalidAnchors = await page.locator('#result-start a[href^="#"]').evaluateAll(links=>links.filter(a=>!document.getElementById(a.getAttribute('href').slice(1))).map(a=>a.getAttribute('href'))); if(errors.length || invalidAnchors.length)throw new Error(JSON.stringify({errors,invalidAnchors}));console.log(JSON.stringify({errors,invalidAnchors,viewports:[1440,1280,1024,390]}));await browser.close();
})();

