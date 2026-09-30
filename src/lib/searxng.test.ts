import { beforeEach, describe, expect, it, vi } from 'vitest';

const startMock = vi.fn();
const updateConfigMock = vi.fn();
const getSearxngURLMock = vi.fn();

vi.mock('@/lib/config/serverRegistry', () => ({
  getSearxngURL: () => getSearxngURLMock(),
  __esModule: true,
}));

vi.mock('@/lib/config', () => ({
  default: {
    updateConfig: (...args: any[]) => updateConfigMock(...args),
  },
  __esModule: true,
}));

vi.mock('../../desktop/searxng.mjs', () => ({
  start: (...args: any[]) => startMock(...args),
  isServing: vi.fn(async () => false),
  __esModule: true,
}));

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import { searchSearxng } from './searxng';

describe('searchSearxng', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSearxngURLMock.mockReturnValue('http://127.0.0.1:59913');
  });

  it('starts the local SearXNG instance and persists the resolved URL when the configured URL is down', async () => {
    startMock.mockResolvedValue('http://127.0.0.1:45011');
    fetchMock
      .mockRejectedValueOnce(new Error('connect ECONNREFUSED 127.0.0.1:59913'))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          results: [{ title: 'Sherlock Holmes', url: 'https://example.com', content: 'Detective' }],
          suggestions: [],
        }),
      });

    const result = await searchSearxng('Who is Sherlock Holmes?');

    expect(startMock).toHaveBeenCalledTimes(1);
    expect(updateConfigMock).toHaveBeenCalledWith('search.searxngURL', 'http://127.0.0.1:45011');
    expect(result.results).toHaveLength(1);
    expect(result.results[0].url).toBe('https://example.com');
  });

  it('returns empty arrays instead of crashing when SearXNG returns no result payload', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });

    const result = await searchSearxng('test query');

    expect(result.results).toEqual([]);
    expect(result.suggestions).toEqual([]);
  });
});
