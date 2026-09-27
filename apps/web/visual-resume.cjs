const {chromium,expect}=require('@playwright/test');
const fs=require('fs');const path=require('path');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chromium'});const page=await browser.newPage({viewport:{width:1280,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 const dir=path.resolve(__dirname,'../../artifacts/result-redesign')+'/';const result=JSON.parse(fs.readFileSync(dir+'live-result.json','utf8'));
 await page.route('**/api/live/intake',r=>r.fulfill({json:result.intake}));await page.route('**/api/live/analyze',r=>r.fulfill({json:result}));await page.goto((process.env.VISUAL_BASE_URL || 'http://127.0.0.1:3000')+'/analyze');await page.locator('#resume-upload').setInputFiles(dir+'resume.pdf');for(const name of ['Continue to target role','Continue to public sources','Continue to review','Start live analysis'])await page.getByRole('button',{name,exact:true}).click();await page.getByRole('region',{name:'Live candidate dossier',exact:true}).waitFor();


 await page.getByText(/Detailed .* review & job requirements/).click();
 for(const width of [1440,1280,1024,390]) {
  await page.setViewportSize({width,height:900});
  await page.getByRole('region',{name:'Detailed resume analysis',exact:true}).evaluate(el=>scrollTo({top:el.getBoundingClientRect().top+scrollY-140,behavior:'instant'}));
  await page.screenshot({animations:'disabled',path:dir+'resume-review-'+width+'.png'});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Overflow '+width);
 }
 await page.setViewportSize({width:390,height:900});
 await page.getByRole('region',{name:'Detailed resume analysis',exact:true}).locator('summary').first().click();
 await page.screenshot({animations:'disabled',path:dir+'resume-skill-mobile.png'});
 if(errors.length)throw new Error(JSON.stringify(errors)); console.log(JSON.stringify({errors,viewports:[1440,1280,1024,390]})); await browser.close();
})();
