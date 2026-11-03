import { describe, it, expect } from 'vitest';
import { availableRows, resolveBest, pickDefaultModel } from './catalog';
import { MinimalProvider } from './types';

describe('catalog with OpenRouter and Ollama', () => {
  const providers: MinimalProvider[] = [
    {
      id: 'p-ollama',
      name: 'ollama',
      type: 'ollama',
      chatModels: [{ key: 'qwen2.5:7b', name: 'qwen2.5:7b' }],
      embeddingModels: [{ key: 'nomic-embed-text', name: 'nomic-embed-text' }],
    },
    {
      id: 'p-openrouter',
      name: 'openrouter',
      type: 'openai',
      chatModels: [
        { key: 'openai/gpt-4o', name: 'OpenAI: GPT-4o' },
        { key: 'openai/gpt-4o-mini', name: 'OpenAI: GPT-4o mini' },
        { key: 'anthropic/claude-3.5-sonnet', name: 'Anthropic: Claude 3.5 Sonnet' },
        { key: 'anthropic/claude-3.7-sonnet', name: 'Anthropic: Claude 3.7 Sonnet' },
        { key: 'deepseek/deepseek-r1', name: 'DeepSeek: R1' },
        { key: 'deepseek/deepseek-chat', name: 'DeepSeek: V3' },
        {
          key: 'nvidia/nemotron-3.5-lightning:free',
          name: 'NVIDIA: Nemotron 3.5 Lightning (free)',
        },
      ],
      embeddingModels: [],
    },
  ];

  it('resolves OpenRouter models in availableRows', () => {
    const rows = availableRows(providers);
    const rowNames = rows.map((r) => r.row.name);

    expect(rowNames).toContain('Local (Ollama)');
    expect(rowNames).toContain('GPT-4o');
    expect(rowNames).toContain('GPT-4o mini');
    expect(rowNames).toContain('Claude Sonnet 5');
    expect(rowNames).toContain('Claude 3.7 Sonnet');
    expect(rowNames).toContain('DeepSeek R1');
    expect(rowNames).toContain('DeepSeek V3');
    expect(rowNames).toContain('Nemotron 3.5 (Free)');

    const nemotron = rows.find((r) => r.row.id === 'nvidia-nemotron-free');
    expect(nemotron?.free).toBe(true);
    expect(nemotron?.key).toBe('nvidia/nemotron-3.5-lightning:free');
  });

  it('resolves Best to OpenRouter Claude or GPT-4o instead of Ollama', () => {
    const best = resolveBest(providers);
    expect(best).not.toBeNull();
    expect(best?.providerId).toBe('p-openrouter');
    expect(best?.key).toBe('anthropic/claude-3.7-sonnet');
  });

  it('picks OpenRouter as default model', () => {
    const defaultModel = pickDefaultModel(providers);
    expect(defaultModel?.providerId).toBe('p-openrouter');
  });
});
