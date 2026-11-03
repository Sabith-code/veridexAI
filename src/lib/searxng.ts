import configManager from './config';
import { getSearxngURL } from './config/serverRegistry';

export interface SearxngSearchOptions {
  categories?: string[];
  engines?: string[];
  language?: string;
  pageno?: number;
}

interface SearxngSearchResult {
  title: string;
  url: string;
  img_src?: string;
  thumbnail_src?: string;
  thumbnail?: string;
  content?: string;
  author?: string;
  iframe_src?: string;
}

const getDataDir = () => process.env.DATA_DIR || process.cwd();

async function ensureLocalSearxng() {
  try {
    const searxngModule = await import('../../desktop/searxng.mjs');
    const startedURL = await searxngModule.start(getDataDir(), (message: string) => {
      console.log(`[SearXNG] ${message}`);
    });

    configManager.updateConfig('search.searxngURL', startedURL);
    return startedURL;
  } catch (err) {
    console.error('Failed to start the bundled local SearXNG backend:', err);
    return null;
  }
}

async function resolveConfiguredSearxngURL() {
  let configuredURL = getSearxngURL();
  const trimmed = configuredURL?.trim();

  if (!trimmed) {
    return (await ensureLocalSearxng()) || '';
  }

  try {
    const probe = await fetch(new URL(`${trimmed.replace(/\/$/, '')}/search?format=json&q=healthcheck`), {
      signal: AbortSignal.timeout(1500),
    });

    if (probe.ok || probe.status < 500) {
      return trimmed;
    }
  } catch {
    // The configured SearXNG URL is stale or down — start the bundled local
    // backend and persist the resolved URL so the browser dev server keeps
    // working even when Electron is not running.
  }

  return (await ensureLocalSearxng()) || trimmed;
}

export const searchSearxng = async (
  query: string,
  opts?: SearxngSearchOptions,
) => {
  const resolvedURL = await resolveConfiguredSearxngURL();

  if (!resolvedURL) {
    throw new Error(
      'SearXNG is not configured and the bundled local search backend could not be started.',
    );
  }

  const url = new URL(`${resolvedURL.replace(/\/$/, '')}/search?format=json`);
  url.searchParams.append('q', query);

  if (opts) {
    Object.keys(opts).forEach((key) => {
      const value = opts[key as keyof SearxngSearchOptions];
      if (Array.isArray(value)) {
        url.searchParams.append(key, value.join(','));
        return;
      }
      url.searchParams.append(key, value as string);
    });
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const res = await fetch(url, {
      signal: controller.signal,
    });

    if (!res.ok) {
      throw new Error(
        `SearXNG request failed at ${resolvedURL} with status ${res.status}: ${res.statusText}`,
      );
    }

    const data = await res.json();

    const results: SearxngSearchResult[] = Array.isArray(data?.results)
      ? data.results
      : [];
    const suggestions: string[] = Array.isArray(data?.suggestions)
      ? data.suggestions
      : [];

    return { results, suggestions };
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new Error(`SearXNG search timed out at ${resolvedURL}`);
    }
    if (err instanceof Error) {
      const message = err.message.startsWith('SearXNG')
        ? err.message
        : `SearXNG search failed at ${resolvedURL}: ${err.message}`;
      throw new Error(message);
    }
    throw new Error(`SearXNG search failed at ${resolvedURL}`);
  } finally {
    clearTimeout(timeoutId);
  }
};
