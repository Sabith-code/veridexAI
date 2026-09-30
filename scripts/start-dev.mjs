import { spawn } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import * as searxng from '../desktop/searxng.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');
const userDataDir = process.env.DATA_DIR || path.join(os.homedir(), 'AppData', 'Roaming', 'Simplicity');

const ensureDataDir = () => {
  const dataRoot = path.join(userDataDir, 'data');
  const logRoot = path.join(userDataDir, 'logs');
  fs.mkdirSync(dataRoot, { recursive: true });
  fs.mkdirSync(logRoot, { recursive: true });

  const configPath = path.join(dataRoot, 'config.json');
  if (!fs.existsSync(configPath)) {
    fs.writeFileSync(
      configPath,
      JSON.stringify(
        {
          version: 1,
          setupComplete: false,
          preferences: {},
          personalization: {},
          modelProviders: [],
          search: { searxngURL: '' },
        },
        null,
        2,
      ),
    );
  }

  return { dataRoot, configPath };
};

const persistSearxngURL = (searxngURL) => {
  const { configPath } = ensureDataDir();
  try {
    const raw = fs.readFileSync(configPath, 'utf8');
    const config = raw ? JSON.parse(raw) : { search: {} };
    config.search = { ...(config.search ?? {}), searxngURL };
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
  } catch (error) {
    console.error('Failed to persist the resolved SearXNG URL to config.json:', error);
  }
};

const startSearchBackend = async () => {
  try {
    const url = await searxng.start(userDataDir, (message) => {
      console.log(`[SearXNG] ${message}`);
    });
    persistSearxngURL(url);
    console.log(`[SearXNG] Ready at ${url}`);
    return url;
  } catch (error) {
    console.error('Failed to start the bundled SearXNG backend for development:', error);
    return null;
  }
};

const portIsOpen = (port) =>
  new Promise((resolve) => {
    const socket = net.createConnection({ host: '127.0.0.1', port });
    socket.once('connect', () => {
      socket.destroy();
      resolve(true);
    });
    socket.once('error', () => {
      resolve(false);
    });
  });

const isNextServerRunning = async () => {
  for (const port of [3000, 3001, 3002]) {
    if (await portIsOpen(port)) {
      return true;
    }
  }
  return false;
};

const runNextDev = async () => {
  if (await isNextServerRunning()) {
    console.log('[Next.js] A dev server is already running on localhost; reusing the existing process.');
    return;
  }

  const env = {
    ...process.env,
    DATA_DIR: userDataDir,
    NODE_ENV: 'development',
  };

  const nextScript = path.join(repoRoot, 'node_modules', 'next', 'dist', 'bin', 'next');

  const child = spawn(process.execPath, [nextScript, 'dev'], {
    cwd: repoRoot,
    stdio: 'inherit',
    env,
  });

  child.on('exit', (code) => {
    process.exit(code ?? 0);
  });

  child.on('error', (error) => {
    console.error('Failed to start Next.js dev server:', error);
    process.exit(1);
  });
};

await ensureDataDir();
await startSearchBackend();
await runNextDev();
