import OpenAI from 'openai';
import OpenAILLM from '../openai/openaiLLM';
import { GenerateObjectInput } from '../../types';
import { repairJson } from '@toolsycc/json-repair';
import z from 'zod';

type OpenRouterConfig = {
  apiKey: string;
  model: string;
  baseURL?: string;
};

class OpenRouterLLM extends OpenAILLM {
  constructor(config: OpenRouterConfig) {
    super({
      ...config,
      baseURL: config.baseURL || 'https://openrouter.ai/api/v1',
    });

    this.openAIClient = new OpenAI({
      apiKey: this.config.apiKey,
      baseURL: this.config.baseURL || 'https://openrouter.ai/api/v1',
      defaultHeaders: {
        'HTTP-Referer': 'http://localhost:3000',
        'X-Title': 'Veridex',
      },
    });
  }

  // Graceful fallback for models on OpenRouter that don't support strict json_schema
  async generateObject<T>(input: GenerateObjectInput): Promise<T> {
    try {
      return await super.generateObject(input);
    } catch (err: any) {
      const response = await this.openAIClient.chat.completions.create({
        model: this.config.model,
        messages: [
          ...this.convertToOpenAIMessages(input.messages),
          {
            role: 'system',
            content: `You MUST return ONLY a valid JSON object matching this schema:\n${JSON.stringify(z.toJSONSchema(input.schema))}`,
          },
        ],
        response_format: { type: 'json_object' },
        temperature: input.options?.temperature ?? 0.2,
      });

      if (response.usage) {
        this.recordUsage({
          inputTokens: response.usage.prompt_tokens ?? 0,
          outputTokens: response.usage.completion_tokens ?? 0,
          cachedInputTokens: response.usage.prompt_tokens_details?.cached_tokens ?? 0,
        });
      }

      if (response.choices && response.choices.length > 0) {
        const raw = response.choices[0].message.content || '{}';
        const repaired = repairJson(raw, { extractJson: true }) as string;
        return input.schema.parse(JSON.parse(repaired)) as T;
      }

      throw err;
    }
  }
}

export default OpenRouterLLM;
