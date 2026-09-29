const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({testDir:'.',testMatch:'audit.spec.cjs',workers:1,timeout:65000,expect:{timeout:12000},outputDir:'audit-results',use:{baseURL:'http://127.0.0.1:3178',channel:'chromium',viewport:{width:1440,height:1000},reducedMotion:'reduce',trace:'retain-on-failure'},webServer:{command:'pnpm exec next start --hostname 127.0.0.1 --port 3178',url:'http://127.0.0.1:3178',reuseExistingServer:false,timeout:60000,env:{CCI_API_URL:'http://127.0.0.1:65530'}}});

