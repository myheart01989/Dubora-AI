import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import { createProxyMiddleware } from 'http-proxy-middleware';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;
const FASTAPI_PORT = 8000;

app.use(cors());

// Spawn the Python FastAPI backend on port 8000
console.log('[Server] Starting Python FastAPI backend on port ' + FASTAPI_PORT + '...');
const pythonProcess = spawn('python3', [
  '-m', 'uvicorn',
  'app.main:app',
  '--host', '127.0.0.1',
  '--port', String(FASTAPI_PORT)
], {
  cwd: __dirname,
  env: {
    ...process.env,
    PYTHONPATH: __dirname,
  },
  stdio: 'inherit'
});

pythonProcess.on('error', (err) => {
  console.error('[Python Backend Error]', err);
});

pythonProcess.on('exit', (code, signal) => {
  console.log(`[Python Backend exited with code ${code} and signal ${signal}]`);
});

process.on('exit', () => {
  pythonProcess.kill();
});

// Proxy /api requests to FastAPI backend
const apiProxy = createProxyMiddleware({
  target: `http://127.0.0.1:${FASTAPI_PORT}`,
  changeOrigin: true,
  ws: true,
});

app.use('/api', apiProxy);

// Serve static frontend assets
const frontendDir = path.join(__dirname, 'frontend');
app.use('/static', express.static(frontendDir));

// Serve index.html at root
app.get('/', (req, res) => {
  res.sendFile(path.join(frontendDir, 'index.html'));
});

// Also serve health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', proxyTo: `http://127.0.0.1:${FASTAPI_PORT}` });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[Server] Web Application running on http://0.0.0.0:${PORT}`);
});
