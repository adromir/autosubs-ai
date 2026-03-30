const puppeteer = require('puppeteer');

(async () => {
  try {
    console.log("Launching browser...");
    const browser = await puppeteer.launch({ 
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors', '--disable-web-security']
    });
    const page = await browser.newPage();
    
    page.on('console', msg => console.log('[BROWSER_CONSOLE]:', msg.text()));
    page.on('pageerror', error => console.error('[BROWSER_EXCEPTION]:', error.message));
    page.on('requestfailed', request => {
      const fail = request.failure();
      console.log('[NETWORK_FAIL]:', fail ? fail.errorText : 'unknown', request.url());
    });
    
    console.log("Navigating to http://localhost:8000...");
    await page.goto('http://localhost:8000', { waitUntil: 'load', timeout: 5000 });
    
    await page.screenshot({path: 'debug.png'});
    console.log("Done checking.");
    
    // Optional: wait a tiny bit to catch late async errors
    await new Promise(r => setTimeout(r, 1000));
    
    await browser.close();
  } catch(e) {
    console.error("Puppeteer crashed:", e);
  }
})();
