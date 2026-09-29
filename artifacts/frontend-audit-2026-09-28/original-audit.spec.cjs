const {test,expect}=require('@playwright/test');
const fs=require('fs');
const result=JSON.parse(fs.readFileSync('C:/Users/yoray/Projects/CandidateX-main/artifacts/result-redesign/live-result.json','utf8'));
const picture='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6rYkAAAAASUVORK5CYII=';
function candidateFixture(dossier=result.dossier, extra={}) {
 return {id:dossier.candidate_id,display_name:'Audit Candidate',role:'backend',has_completed_dossier:true,rci:dossier.rci,coverage:dossier.coverage,has_meaningful_conflict:false,created_at:'2026-09-28T00:00:00Z',source:'live',manifest:{candidate_id:dossier.candidate_id,full_name:'Audit Candidate',primary_email:'audit@example.invalid',picture,declared_skills:[],github_usernames:[],github_repositories:[],deployment_urls:[],portfolio_urls:[],extraction_metadata:{}},dossier,graph:result.graph,...extra};
}
async function openFull(page,candidate) {
 await page.addInitScript(c=>localStorage.setItem('cci_hr_saved_candidates',JSON.stringify([c])),candidate);
 await page.goto('/hr');await page.getByRole('button',{name:'View Audit Candidate',exact:true}).click();
 await page.getByRole('button',{name:'Open full technical dossier',exact:true}).click();await page.getByRole('button',{name:'Executive Overview',exact:true}).waitFor();
}
result.intake.manifest.display_name='Audit Candidate';
result.intake.manifest.picture=picture;result.intake.picture=picture;
result.intake.manifest.github_urls=[];result.intake.manifest.shared_document_urls=['https://drive.google.com/file/d/audit/view'];
function log(probe,data){console.log('AUDIT '+JSON.stringify({probe,...data}));}
test.beforeEach(async({page,context,baseURL})=>{
 await context.addCookies([{name:'cx_auth',value:'audit%40example.invalid',url:baseURL}]);
 await page.route('**/api/**',r=>r.fulfill({status:503,json:{detail:'Read-only audit intercept; no backend operation performed'}}));
 await page.route('**/health',r=>r.fulfill({json:{status:'ok'}}));
});
async function intake(page){
 await page.route('**/api/live/intake',r=>r.fulfill({json:result.intake}));
 await page.goto('/analyze');
 await page.getByRole('button',{name:'Sign out',exact:true}).waitFor();
 await page.locator('#resume-upload').setInputFiles({name:'audit.pdf',mimeType:'application/pdf',buffer:Buffer.from('mocked audit resume')});
 await page.getByRole('button',{name:'Continue to target role',exact:true}).click();
}
async function review(page){
 await page.getByRole('button',{name:'Continue to public sources',exact:true}).click();
 await page.getByRole('button',{name:'Continue to review',exact:true}).click();
}
test('live state, source status, storage failures, and photo keyboard behavior',async({page},info)=>{
 const bodies=[];
 await page.addInitScript(()=>{const original=Storage.prototype.setItem;Storage.prototype.setItem=function(key,value){if(key==='cci_hr_saved_candidates')throw new DOMException('Audit quota failure','QuotaExceededError');return original.call(this,key,value)};});
 await page.route('**/api/live/analyze',r=>{bodies.push(r.request().postDataJSON());return r.fulfill({json:result})});
 await page.route('**/api/live/fetch-link',r=>r.fulfill({json:{url:'https://drive.google.com/file/d/audit/view',status:'access_restricted',detail:'Permission required',file_count:0,files:[]}}));
 await intake(page);
 log('forged_auth_cookie',{accessible:await page.locator('#live-jd').isVisible()});
 await page.locator('#jd-upload').setInputFiles({name:'audit.txt',mimeType:'text/plain',buffer:Buffer.from('AUDIT_PREVIOUS_JD requires Python and PostgreSQL engineering.')});
 await expect(page.getByTestId('jd-file-card')).toBeVisible();
 log('text_jd_storage_claim',{card:await page.getByTestId('jd-file-card').innerText()});
 await page.getByRole('button',{name:'Continue to public sources',exact:true}).click();
 await page.getByRole('button',{name:'Fetch files & get data',exact:true}).click();
 await expect(page.getByText(/Files & data fetched/)).toBeVisible();
 log('restricted_cloud_result',{status:await page.getByText(/Files & data fetched/).innerText()});
 await page.getByRole('button',{name:'Continue to review',exact:true}).click();
 await page.getByRole('button',{name:'Start live analysis',exact:true}).click();
 await expect(page.getByRole('region',{name:'Live candidate dossier',exact:true})).toBeVisible();
 log('failed_save_reported_success',{success:await page.getByText(/Candidate profile for Audit Candidate saved to HR/).count(),stored:await page.evaluate(()=>localStorage.getItem('cci_hr_saved_candidates'))});
 const photo=page.getByRole('button',{name:'View full photo of Audit Candidate',exact:true});
 await photo.focus();await page.keyboard.press('Enter');
 const lightbox=page.getByRole('dialog',{name:'Profile photo of Audit Candidate',exact:true});await expect(lightbox).toBeVisible();
 log('photo_focus_initial',{inside:await lightbox.evaluate(e=>e.contains(document.activeElement))});
 await page.keyboard.press('Tab');log('photo_focus_tab',{inside:await lightbox.evaluate(e=>e.contains(document.activeElement))});
 await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'Run another analysis',exact:true}).click();
 await page.locator('#resume-upload').setInputFiles({name:'second.pdf',mimeType:'application/pdf',buffer:Buffer.from('second mocked resume')});
 await page.getByRole('button',{name:'Continue to target role',exact:true}).click();
 log('new_run_jd_ui',{fileCards:await page.getByTestId('jd-file-card').count(),text:await page.locator('#live-jd').inputValue()});
 await review(page);await page.getByRole('button',{name:'Start live analysis',exact:true}).click();await expect.poll(()=>bodies.length).toBe(2);
 log('new_run_jd_payload',{first:bodies[0].jd_text,second:bodies[1].jd_text,jobId:bodies[1].job_id});
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Toggle navigation'}).click();
 log('mobile_signout',{visible:await page.getByRole('button',{name:'Sign out',exact:true}).isVisible(),navigation:await page.getByRole('navigation',{name:'Primary navigation'}).innerText()});
});
test('analysis may start while the uploaded JD is still parsing',async({page})=>{
 let finish;const gate=new Promise(resolve=>{finish=resolve});let payload;
 await page.route('**/api/live/parse-jd',async r=>{await gate;await r.fulfill({json:{text:'AUDIT_PENDING_JD requires frontend testing',filename:'pending.pdf',job_id:'audit-job'}})});
 await page.route('**/api/live/analyze',r=>{payload=r.request().postDataJSON();return r.fulfill({json:result})});
 await intake(page);await page.locator('#jd-upload').setInputFiles({name:'pending.pdf',mimeType:'application/pdf',buffer:Buffer.from('mocked pending job document')});
 await expect(page.getByText('Extracting text from document…',{exact:true})).toBeVisible();
 log('pending_jd_continue',{enabled:await page.getByRole('button',{name:'Continue to public sources',exact:true}).isEnabled()});
 await review(page);await page.getByRole('button',{name:'Start live analysis',exact:true}).click();await expect.poll(()=>Boolean(payload)).toBe(true);
 log('pending_jd_analysis',{jd:payload.jd_text,jobId:payload.job_id});finish();
});
test('workspace upload linkage, failed parse, and resume identity',async({page})=>{
 let parseBody,pipelineBody;
 await page.route('**/api/v1/jobs/upload',r=>r.fulfill({json:{id:'audit-uploaded-job',title:'Audit role',canonical_role:'backend',requirements_count:1,file_name:'job.pdf',is_active:true,created_at:new Date().toISOString()}}));
 await page.route('**/api/v1/jobs/parse',r=>{parseBody=r.request().postDataJSON();return r.fulfill({status:503,json:{detail:'Audit parser failure'}})});
 await page.route('**/api/v1/pipeline/run',r=>{pipelineBody=r.request().postDataJSON();return r.fulfill({json:{status:'failed',error:'Audit stops before persistence',stages:[]}})});
 const fresh=structuredClone(result.intake);fresh.candidate_id='99999999-9999-4999-8999-999999999999';fresh.manifest.display_name='New Audit Person';fresh.manifest.email='';fresh.manifest.github_urls=[];fresh.manifest.deployment_urls=[];fresh.manifest.claimed_skills=[];
 await page.route('**/api/live/intake',r=>r.fulfill({json:fresh}));
 await page.goto('/workspace');await page.getByRole('button',{name:'New Evaluation Run pipeline',exact:true}).click();
 await page.locator('#jd-file-upload-input').setInputFiles({name:'job.pdf',mimeType:'application/pdf',buffer:Buffer.from('mock job')});
 await expect(page.getByText('Stored in backend',{exact:true})).toBeVisible();
 const notes=page.getByRole('textbox',{name:/Additional recruiter notes/});await notes.fill('AUDIT_NOTES');
 log('job_notes_control',{visibleValue:await notes.inputValue()});
 await page.getByRole('button',{name:'Extract Requirements Preview',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Extracted Requirements (4)',exact:true})).toBeVisible();
 log('failed_jd_parse',{request:parseBody,shown:await page.getByRole('heading',{name:/Extracted Requirements/}).innerText(),alerts:await page.getByRole('alert').allTextContents()});
 await page.getByRole('button',{name:'Confirm role profile',exact:true}).click();
 const priorEmail=await page.getByRole('textbox',{name:'Primary Email',exact:true}).inputValue();
 await page.locator('input[type=file]').setInputFiles({name:'new-candidate.pdf',mimeType:'application/pdf',buffer:Buffer.from('mock different person')});
 await expect(page.getByRole('textbox',{name:'Candidate Full Name',exact:true})).toHaveValue('New Audit Person');
 log('resume_old_data',{priorEmail,afterEmail:await page.getByRole('textbox',{name:'Primary Email',exact:true}).inputValue(),buttons:await page.getByRole('button',{name:/Run|Launch|Start/}).allTextContents()});
 const submit=page.locator('form button[type=submit]');await submit.click();await expect.poll(()=>Boolean(pipelineBody)).toBe(true);
 log('resume_and_jd_pipeline',{id:pipelineBody.candidate_id,expectedId:fresh.candidate_id,jd:pipelineBody.jd_text,jobId:pipelineBody.job_id,repoCount:pipelineBody.repo_urls?.length,claims:pipelineBody.declared_claims});
});
test('candidate review retains data across signout and overflows on mobile',async({page},info)=>{
 const candidate={id:result.dossier.candidate_id,display_name:'Audit Candidate',role:'backend',has_completed_dossier:true,rci:result.dossier.rci,coverage:result.dossier.coverage,has_meaningful_conflict:false,created_at:'2026-09-28T00:00:00Z',source:'live',manifest:{candidate_id:result.dossier.candidate_id,full_name:'Audit Candidate',primary_email:'audit@example.invalid',picture,declared_skills:[],github_usernames:[],github_repositories:[],deployment_urls:[],portfolio_urls:[],extraction_metadata:{}},dossier:result.dossier,graph:result.graph};
 await page.addInitScript(c=>localStorage.setItem('cci_hr_saved_candidates',JSON.stringify([c])),candidate);
 await page.goto('/hr');await page.getByRole('button',{name:'View Audit Candidate',exact:true}).click();
 await page.getByRole('button',{name:'Open full technical dossier',exact:true}).click();await page.getByRole('button',{name:'Executive Overview',exact:true}).waitFor();
 await page.setViewportSize({width:390,height:844});
 const dialog=page.getByRole('dialog').first();
 log('mobile_full_dossier',{page:await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})),dialog:await dialog.evaluate(e=>({width:e.clientWidth,scrollWidth:e.scrollWidth})),lastTab:await page.getByRole('button',{name:'Evidence & Audit',exact:true}).boundingBox()});
 await page.screenshot({path:info.outputPath('mobile-full-dossier.png')});
 await page.setViewportSize({width:1440,height:1000});await page.getByRole('button',{name:/View full photo/}).click();
 log('nested_photo',{dialogs:await page.getByRole('dialog').allTextContents(),photoClickBlocked:await page.getByRole('button',{name:'Close photo',exact:true}).evaluate(e=>{const r=e.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)!==e})});
 await page.keyboard.press('Escape');await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'Sign out',exact:true}).click();
 log('signout_retention',{saved:await page.evaluate(()=>JSON.parse(localStorage.getItem('cci_hr_saved_candidates')||'[]').map(c=>c.display_name)),hrStillVisible:await page.getByRole('button',{name:'View Audit Candidate',exact:true}).isVisible()});
});

test('followup recovery and remember preference',async({page,context})=>{
 await context.clearCookies();const mutations=[];
 page.on('request',r=>{if(r.method()==='POST')mutations.push(r.url())});
 await page.goto('/login');await page.getByRole('button',{name:'Forgot password?',exact:true}).click();
 await page.locator('#forgot-email').fill('audit@example.invalid');await page.getByRole('button',{name:'Send reset link',exact:true}).click();
 await expect(page.getByText(/we have dispatched a secure recovery token/)).toBeVisible();
 log('fake_password_recovery',{mutationRequests:mutations,notice:await page.getByText(/we have dispatched a secure recovery token/).innerText()});
 await page.keyboard.press('Escape');log('forgot_escape',{dialogStillVisible:await page.getByRole('dialog').isVisible()});
 await page.goto('/login');await page.getByRole('button',{name:'Use authorized demo credentials',exact:true}).click();
 await page.getByRole('checkbox',{name:'Remember this device for 30 days',exact:true}).uncheck();
 await page.getByRole('button',{name:'Sign in to workspace',exact:true}).click();await expect(page).toHaveURL(/\/workspace/);
 const cookies=await context.cookies();log('remember_unchecked',{stored:await page.evaluate(()=>!!localStorage.getItem('cx_auth_session')),cookieLifetimeDays:(cookies.find(c=>c.name==='cx_auth').expires-Date.now()/1000)/86400});
});

test('followup deleting a freshly added draft',async({page})=>{
 await page.goto('/hr');await page.getByRole('button',{name:'Add Candidate',exact:true}).first().click();
 await page.getByRole('textbox',{name:'Full name',exact:true}).fill('Audit Remove Draft');
 await page.getByRole('checkbox',{name:/I have permission/}).check();await page.getByRole('button',{name:'Add local draft',exact:true}).click();
 await page.getByRole('button',{name:'View Audit Remove Draft',exact:true}).click();page.once('dialog',d=>d.accept());
 await page.getByRole('button',{name:'Delete draft',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 log('deleted_draft_retained',{rowStillVisible:await page.getByRole('button',{name:'View Audit Remove Draft',exact:true}).isVisible(),persisted:await page.evaluate(()=>JSON.parse(localStorage.getItem('cci_hr_saved_candidates')||'[]').some(c=>c.display_name==='Audit Remove Draft'))});
});

test('followup unknown evidence and full audit fallback',async({page})=>{
 const d=structuredClone(result.dossier);d.rci=null;d.coverage=0;d.is_insufficient_evidence=true;d.claims_corroboration=[];d.capability_conflicts={};d.evidence_records=[];
 Object.values(d.capability_estimates).forEach(e=>{e.is_observed=false;e.estimate=null;e.raw_evidence_count=0;e.effective_evidence_count=0});
 await openFull(page,candidateFixture(d));
 log('unknown_dossier_claims',{claimNotice:await page.getByText(/Claims Corroborated:/).innerText(),zeroText:await page.getByText('0.0',{exact:true}).count(),zeroPercent:await page.getByText('0%',{exact:true}).count()});
 await page.getByRole('button',{name:'Export report and audit options',exact:true}).click();
 const waitDownload=page.waitForEvent('download');await page.getByRole('button',{name:'Download Full Audit (HTML)',exact:true}).click();const download=await waitDownload;
 const data=fs.readFileSync(await download.path(),'utf8');log('audit_html_fallback',{filename:download.suggestedFilename(),bytes:data.length,content:data});
});

test('followup default interview scorecard',async({page})=>{
 let payload;
 await page.route('**/api/v1/overrides/interview-feedback',r=>{payload=r.request().postDataJSON();return r.fulfill({json:{candidate_id:result.dossier.candidate_id,interviewer_name:'Audit Interviewer',audit_event_id:'audit-only-not-persisted',recorded_at:'2026-09-28T00:00:00Z',evaluations_count:payload.probe_evaluations.length}})});
 await openFull(page,candidateFixture());await page.locator('button[data-tab-key="probes"]').click();await page.getByRole('button',{name:'Record Scorecard',exact:true}).click();
 await page.getByPlaceholder('e.g. Alex Morgan, Staff Software Engineer').fill('Audit Interviewer');
 await page.getByRole('button',{name:'Submit Scorecard to Audit Trail',exact:true}).click();await expect.poll(()=>!!payload).toBe(true);
 log('untouched_interview_payload',{count:payload.probe_evaluations.length,ratings:[...new Set(payload.probe_evaluations.map(p=>p.rating))],sampleNote:payload.probe_evaluations[0]?.notes,recommendation:payload.overall_recommendation});
});

test('followup inferred observed count',async({page})=>{
 const c=candidateFixture(result.dossier,{dossier:undefined,graph:undefined,coverage:0.86});
 await page.route('**/api/v1/dossier/'+c.id,r=>r.fulfill({json:result.dossier}));
 await page.addInitScript(c=>localStorage.setItem('cci_hr_saved_candidates',JSON.stringify([c])),c);
 await page.goto('/hr');const row=page.getByRole('row').filter({has:page.getByRole('button',{name:'View Audit Candidate',exact:true})});await row.waitFor();
 const rowText=await row.innerText();await page.getByRole('button',{name:'View Audit Candidate',exact:true}).click();await expect(page.getByText(/Observed: 6 \/ 12/)).toBeVisible();
 log('coverage_inferred_count',{row:rowText,subtitle:await page.getByText(/Observed: 6 \/ 12/).innerText()});
});

test('last comparison exports previous selection while loading',async({page})=>{
 const a={id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',display_name:'Audit Alpha',role:'backend',has_completed_dossier:true,rci:72,coverage:0.5};
 const b={...a,id:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',display_name:'Audit Beta',rci:81};
 await page.route('**/api/v1/candidates',r=>r.fulfill({json:[a,b]}));
 await page.route('**/api/v1/dossier/'+a.id,r=>r.fulfill({json:{...result.dossier,candidate_id:a.id,rci:72}}));
 let finish;const gate=new Promise(resolve=>{finish=resolve});
 await page.route('**/api/v1/dossier/'+b.id,async r=>{await gate;await r.fulfill({json:{...result.dossier,candidate_id:b.id,rci:81}})});
 await page.goto('/workspace');await page.getByRole('button',{name:'Compare Side by side',exact:true}).click();
 await page.getByRole('button',{name:/^Audit Alpha \(/}).click();await expect(page.getByRole('button',{name:'Download Matrix (.md)',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:/^Audit Beta \(/}).click();await expect(page.getByText('Loading comparative candidate dossiers...', {exact:true})).toBeVisible();
 const downloader=page.getByRole('button',{name:'Download Matrix (.md)',exact:true});
 log('comparison_pending_export_enabled',{enabled:await downloader.isEnabled(),selected:await page.locator('button[aria-pressed=true]').allTextContents()});
 const wait=page.waitForEvent('download');await downloader.click();const download=await wait;const content=fs.readFileSync(await download.path(),'utf8');
 log('comparison_pending_export_content',{hasAlpha:content.includes('Audit Alpha'),hasBeta:content.includes('Audit Beta')});finish();
});

test('last mobile dossier layout and insufficient evidence verdict',async({page},info)=>{
 const d=structuredClone(result.dossier);d.rci=95;d.coverage=0.02;d.is_insufficient_evidence=true;d.claims_corroboration=[];
 await openFull(page,candidateFixture(d));
 log('insufficient_high_score',{verdict:await page.getByText(/Candidate demonstrates authoritative/).innerText(),insufficient:d.is_insufficient_evidence,coverage:d.coverage});
 await page.setViewportSize({width:390,height:844});
 const lastTab=page.locator('button[data-tab-key=graph]');
 log('mobile_dossier_ancestors',{tab:await lastTab.boundingBox(),ancestors:await lastTab.evaluate(e=>{const all=[];for(let p=e.parentElement;p;p=p.parentElement){const s=getComputedStyle(p);all.push({tag:p.tagName,className:p.className,client:p.clientWidth,scroll:p.scrollWidth,overflowX:s.overflowX});}return all})});
 await page.screenshot({path:info.outputPath('mobile-dossier.png')});
 await lastTab.click({timeout:4000}).then(()=>log('mobile_last_tab',{clickable:true}),e=>log('mobile_last_tab',{clickable:false,error:e.message.split('\n')[0]}));
});

test('last nested photo controls remain behind native dialog',async({page})=>{
 await openFull(page,candidateFixture());await page.getByRole('button',{name:'View full photo of Audit Candidate',exact:true}).click();
 const close=page.getByRole('button',{name:'Close photo',exact:true});await expect(close).toBeVisible();
 log('nested_photo_hit',{hit:await close.evaluate(e=>{const r=e.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return {blocked:!e.contains(hit),target:hit?.tagName,targetText:hit?.textContent?.slice(0,70)}})});
 await close.click({timeout:2000}).then(()=>log('nested_photo_click',{clickable:true}),e=>log('nested_photo_click',{clickable:false,error:e.message.split('\n')[0]}));
});

