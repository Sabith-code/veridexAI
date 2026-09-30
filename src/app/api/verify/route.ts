import { spawn } from 'node:child_process';
import { z } from 'zod';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const bodySchema = z.object({
  query: z.string().optional(),
  answer: z.string().min(1),
  sources: z.array(z.object({
    content: z.string(),
    metadata: z.object({ title: z.string().nullable().optional(), url: z.string().nullable().optional() }).optional(),
  })),
  backend: z.enum(['ollama', 'laya', 'hybrid']).optional(),
});

const TIMEOUT_MS = 360_000;
const pythonExecutable = process.env.PYTHON_EXECUTABLE?.trim() || 'python';

export async function POST(req: Request) {
  let requestBody: unknown;
  try {
    requestBody = await req.json();
  } catch {
    return Response.json({ message: 'Request body must be valid JSON.' }, { status: 400 });
  }
  const parsed = bodySchema.safeParse(requestBody);
  if (!parsed.success) return Response.json({ message: 'Invalid verification request.' }, { status: 400 });
  const input = {
    query: parsed.data.query ?? '',
    answer: parsed.data.answer,
    sources: parsed.data.sources.map((source) => ({
      content: source.content,
      title: source.metadata?.title ?? null,
      url: source.metadata?.url ?? null,
    })),
    backend: parsed.data.backend ?? process.env.VERIFICATION_BACKEND ?? 'hybrid',
  };
  try {
    const output = await new Promise<string>((resolve, reject) => {
      const child = spawn(pythonExecutable, ['-m', 'verification.bridge'], {
        cwd: process.cwd(),
        env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
        windowsHide: true,
        stdio: ['pipe', 'pipe', 'pipe'],
      });
      let stdout = '';
      let stderr = '';
      const timer = setTimeout(() => {
        child.kill();
        reject(new Error('Verification timed out.'));
      }, TIMEOUT_MS);
      child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
      child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
      child.on('error', (error) => { clearTimeout(timer); reject(error); });
      child.on('close', (code) => {
        clearTimeout(timer);
        if (code === 0) resolve(stdout.trim());
        else reject(new Error(stderr.trim() || `Verification bridge exited with code ${code ?? 'unknown'}.`));
      });
      child.stdin.end(JSON.stringify(input));
    });
    try {
      return Response.json(JSON.parse(output));
    } catch (error) {
      console.error('Verification bridge returned invalid JSON.', { error, output });
      return Response.json({ message: 'Verification bridge returned invalid JSON.' }, { status: 502 });
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Verification failed.';
    console.error('Verification bridge failed.', message);
    const status = message === 'Verification timed out.' ? 504 : 500;
    return Response.json({ message: status === 504 ? message : `Verification failed: ${message}` }, { status });
  }
}
