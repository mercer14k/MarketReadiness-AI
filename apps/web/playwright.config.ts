import {defineConfig} from '@playwright/test';
export default defineConfig({ testDir: '../../tests/e2e', testMatch: '**/*.spec.ts', fullyParallel: false, workers: 1, timeout: 45000,
  use: {baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:5173', viewport:{width:1440,height:1180}, headless:true,
    ...(process.env.PLAYWRIGHT_CHROME_PATH ? {launchOptions:{executablePath:process.env.PLAYWRIGHT_CHROME_PATH}} : {}),
    screenshot:'only-on-failure', trace:'retain-on-failure'},
  reporter: [['list'], ['html',{open:'never'}]] });
