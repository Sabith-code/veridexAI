import { UIConfigField } from '@/lib/config/types';
import { getConfiguredModelProviderById } from '@/lib/config/serverRegistry';
import { Model, ModelList, ProviderMetadata } from '../../types';
import BaseModelProvider from '../../base/provider';
import BaseEmbedding from '../../base/embedding';
import BaseLLM from '../../base/llm';
import OpenRouterLLM from './openrouterLLM';
import OpenAIEmbedding from '../openai/openaiEmbedding';

interface OpenRouterConfig {
  apiKey: string;
  baseURL?: string;
}

const defaultChatModels: Model[] = [
  { name: 'Claude 3.7 Sonnet', key: 'anthropic/claude-3.7-sonnet' },
  { name: 'Claude 3.5 Sonnet', key: 'anthropic/claude-3.5-sonnet' },
  { name: 'GPT-4o', key: 'openai/gpt-4o' },
  { name: 'GPT-4o mini', key: 'openai/gpt-4o-mini' },
  { name: 'DeepSeek R1', key: 'deepseek/deepseek-r1' },
  { name: 'DeepSeek V3', key: 'deepseek/deepseek-chat' },
  { name: 'Gemini 2.0 Flash', key: 'google/gemini-2.0-flash-001' },
  { name: 'Llama 3.3 70B', key: 'meta-llama/llama-3.3-70b-instruct' },
];

const defaultEmbeddingModels: Model[] = [];

const providerConfigFields: UIConfigField[] = [
  {
    type: 'password',
    name: 'API Key',
    key: 'apiKey',
    description: 'Your OpenRouter API key',
    required: true,
    placeholder: 'sk-or-v1-...',
    env: 'OPENROUTER_API_KEY',
    scope: 'server',
  },
  {
    type: 'string',
    name: 'Base URL',
    key: 'baseURL',
    description: 'OpenRouter base URL',
    required: false,
    placeholder: 'https://openrouter.ai/api/v1',
    default: 'https://openrouter.ai/api/v1',
    env: 'OPENROUTER_BASE_URL',
    scope: 'server',
  },
];

class OpenRouterProvider extends BaseModelProvider<OpenRouterConfig> {
  constructor(id: string, name: string, config: OpenRouterConfig) {
    super(id, name, {
      ...config,
      baseURL: config.baseURL || 'https://openrouter.ai/api/v1',
    });
  }

  async getDefaultModels(): Promise<ModelList> {
    return {
      embedding: defaultEmbeddingModels,
      chat: defaultChatModels,
    };
  }

  async getModelList(): Promise<ModelList> {
    const configProvider = getConfiguredModelProviderById(this.id);
    const configuredChatModels = configProvider?.chatModels ?? [];
    const configuredEmbeddingModels = configProvider?.embeddingModels ?? [];

    const dedupeModels = (models: Model[]) => {
      const seen = new Set<string>();
      return models.filter((model) => {
        if (!model?.key || seen.has(model.key)) return false;
        seen.add(model.key);
        return true;
      });
    };

    const baseUrl = (this.config.baseURL || 'https://openrouter.ai/api/v1').replace(/\/+$/, '');

    try {
      const response = await fetch(`${baseUrl}/models`, {
        headers: {
          Authorization: `Bearer ${this.config.apiKey}`,
          'Content-Type': 'application/json',
          'HTTP-Referer': 'http://localhost:3000',
          'X-Title': 'Veridex',
        },
      });

      if (response.ok) {
        const payload: any = await response.json();
        const remoteModels: Model[] = Array.isArray(payload?.data)
          ? payload.data
              .map((entry: any) => {
                const key = typeof entry?.id === 'string' ? entry.id : null;
                if (!key) return null;
                return {
                  key,
                  name: entry?.name || key,
                };
              })
              .filter(Boolean)
          : [];

        if (remoteModels.length > 0) {
          return {
            embedding: dedupeModels([
              ...defaultEmbeddingModels,
              ...configuredEmbeddingModels,
            ]),
            chat: dedupeModels([
              ...defaultChatModels,
              ...remoteModels,
              ...configuredChatModels,
            ]),
          };
        }
      }
    } catch (error) {
      console.warn('[OpenRouterProvider] Remote discovery failed, using default models:', error);
    }

    return {
      embedding: dedupeModels([
        ...defaultEmbeddingModels,
        ...configuredEmbeddingModels,
      ]),
      chat: dedupeModels([...defaultChatModels, ...configuredChatModels]),
    };
  }

  async loadChatModel(key: string): Promise<BaseLLM<any>> {
    return new OpenRouterLLM({
      apiKey: this.config.apiKey,
      model: key,
      baseURL: this.config.baseURL || 'https://openrouter.ai/api/v1',
    });
  }

  async loadEmbeddingModel(key: string): Promise<BaseEmbedding<any>> {
    return new OpenAIEmbedding({
      apiKey: this.config.apiKey,
      model: key,
      baseURL: this.config.baseURL || 'https://openrouter.ai/api/v1',
    });
  }

  static getProviderConfigFields(): UIConfigField[] {
    return providerConfigFields;
  }

  static getProviderMetadata(): ProviderMetadata {
    return {
      key: 'openrouter',
      name: 'OpenRouter',
    };
  }
}

export default OpenRouterProvider;
