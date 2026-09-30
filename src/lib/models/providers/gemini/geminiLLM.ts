import OpenAILLM, { OpenAIConfig } from '../openai/openaiLLM';
import {
  GenerateTextInput,
  GenerateTextOutput,
  StreamTextOutput,
} from '../../types';
import { ChatCompletionTool } from 'openai/resources/index.mjs';
import z from 'zod';
import { parse } from 'partial-json';

const DEPRECATED_GEMINI_MODELS: Record<string, string> = {
  'models/gemini-2.5-pro': 'models/gemini-flash-latest',
  'gemini-2.5-pro': 'models/gemini-flash-latest',
  'models/gemini-2.5-flash': 'models/gemini-flash-latest',
  'gemini-2.5-flash': 'models/gemini-flash-latest',
  'models/gemini-1.5-pro': 'models/gemini-flash-latest',
  'gemini-1.5-pro': 'models/gemini-flash-latest',
  'models/gemini-1.5-flash': 'models/gemini-flash-latest',
  'gemini-1.5-flash': 'models/gemini-flash-latest',
  'models/gemini-2.0-flash': 'models/gemini-flash-latest',
  'gemini-2.0-flash': 'models/gemini-flash-latest',
};

const FALLBACK_MODELS = [
  'models/gemini-flash-latest',
  'models/gemini-flash-lite-latest',
  'models/gemini-3.8-flash',
  'models/gemini-3.5-flash',
];

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

class GeminiLLM extends OpenAILLM {
  constructor(config: OpenAIConfig) {
    const resolvedModel =
      DEPRECATED_GEMINI_MODELS[config.model] || config.model;

    const rawBaseURL =
      config.baseURL ||
      'https://generativelanguage.googleapis.com/v1beta/openai/';
    const baseURL = rawBaseURL.endsWith('/') ? rawBaseURL : `${rawBaseURL}/`;

    super({
      ...config,
      model: resolvedModel,
      baseURL,
    });
  }

  private getCandidateModels(): string[] {
    const list = [this.config.model, ...FALLBACK_MODELS];
    return Array.from(new Set(list));
  }

  async *streamText(
    input: GenerateTextInput,
  ): AsyncGenerator<StreamTextOutput> {
    const openaiTools: ChatCompletionTool[] = [];
    input.tools?.forEach((tool) => {
      openaiTools.push({
        type: 'function',
        function: {
          name: tool.name,
          description: tool.description,
          parameters: z.toJSONSchema(tool.schema),
        },
      });
    });

    const candidates = this.getCandidateModels();
    let stream: any = null;
    let lastError: any = null;

    for (const model of candidates) {
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          stream = await this.openAIClient.chat.completions.create({
            model,
            messages: this.convertToOpenAIMessages(input.messages),
            tools: openaiTools.length > 0 ? openaiTools : undefined,
            temperature:
              input.options?.temperature ??
              this.config.options?.temperature ??
              1.0,
            top_p: input.options?.topP ?? this.config.options?.topP,
            max_completion_tokens:
              input.options?.maxTokens ?? this.config.options?.maxTokens,
            stop:
              input.options?.stopSequences ??
              this.config.options?.stopSequences,
            frequency_penalty:
              input.options?.frequencyPenalty ??
              this.config.options?.frequencyPenalty,
            presence_penalty:
              input.options?.presencePenalty ??
              this.config.options?.presencePenalty,
            stream: true,
            stream_options: { include_usage: true },
          });
          break;
        } catch (err: any) {
          lastError = err;
          const status = err?.status ?? err?.statusCode;
          if (status === 503 || status === 429) {
            console.warn(
              `Gemini model ${model} returned ${status}. Retrying (attempt ${attempt + 1})...`,
            );
            await sleep(1500 * (attempt + 1));
          } else {
            break;
          }
        }
      }
      if (stream) break;
    }

    if (!stream) {
      const status = lastError?.status ?? lastError?.statusCode;
      if (status === 503) {
        throw new Error(
          'Gemini is currently experiencing high demand (503). Please retry in a few moments, or switch to OpenRouter (NVIDIA Nemotron free).',
        );
      }
      throw lastError || new Error('Failed to create Gemini completion stream.');
    }

    let recievedToolCalls: { name: string; id: string; arguments: string }[] =
      [];

    for await (const chunk of stream) {
      if (chunk.choices && chunk.choices.length > 0) {
        const toolCalls = chunk.choices[0].delta.tool_calls;
        yield {
          contentChunk: chunk.choices[0].delta.content || '',
          toolCallChunk:
            toolCalls?.map((tc: any) => {
              if (!recievedToolCalls[tc.index]) {
                const call = {
                  name: tc.function?.name!,
                  id: tc.id!,
                  arguments: tc.function?.arguments || '',
                };
                recievedToolCalls.push(call);
                return { ...call, arguments: parse(call.arguments || '{}') };
              } else {
                const existingCall = recievedToolCalls[tc.index];
                existingCall.arguments += tc.function?.arguments || '';
                return {
                  ...existingCall,
                  arguments: parse(existingCall.arguments),
                };
              }
            }) || [],
          done: chunk.choices[0].finish_reason !== null,
          additionalInfo: {
            finishReason: chunk.choices[0].finish_reason,
          },
        };
      }

      if (chunk.usage) {
        this.recordUsage({
          inputTokens: chunk.usage.prompt_tokens ?? 0,
          outputTokens: chunk.usage.completion_tokens ?? 0,
          cachedInputTokens:
            chunk.usage.prompt_tokens_details?.cached_tokens ?? 0,
        });
      }
    }
  }

  async generateText(
    input: GenerateTextInput,
  ): Promise<GenerateTextOutput> {
    const candidates = this.getCandidateModels();
    let lastError: any = null;

    for (const model of candidates) {
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          const res = await this.openAIClient.chat.completions.create({
            model,
            messages: this.convertToOpenAIMessages(input.messages),
            temperature:
              input.options?.temperature ??
              this.config.options?.temperature ??
              1.0,
            top_p: input.options?.topP ?? this.config.options?.topP,
            max_completion_tokens:
              input.options?.maxTokens ?? this.config.options?.maxTokens,
            stop:
              input.options?.stopSequences ??
              this.config.options?.stopSequences,
            frequency_penalty:
              input.options?.frequencyPenalty ??
              this.config.options?.frequencyPenalty,
            presence_penalty:
              input.options?.presencePenalty ??
              this.config.options?.presencePenalty,
          });

          if (res.usage) {
            this.recordUsage({
              inputTokens: res.usage.prompt_tokens ?? 0,
              outputTokens: res.usage.completion_tokens ?? 0,
              cachedInputTokens:
                res.usage.prompt_tokens_details?.cached_tokens ?? 0,
            });
          }

          if (res.choices && res.choices.length > 0) {
            return {
              content: res.choices[0].message.content!,
              toolCalls:
                res.choices[0].message.tool_calls
                  ?.map((tc) => {
                    if (tc.type === 'function') {
                      return {
                        name: tc.function.name,
                        id: tc.id,
                        arguments: JSON.parse(tc.function.arguments),
                      };
                    }
                  })
                  .filter((tc): tc is NonNullable<typeof tc> => tc !== undefined) || [],
              additionalInfo: {
                finishReason: res.choices[0].finish_reason,
              },
            };
          }
        } catch (err: any) {
          lastError = err;
          const status = err?.status ?? err?.statusCode;
          if (status === 503 || status === 429) {
            console.warn(
              `Gemini generateText model ${model} returned ${status}. Retrying...`,
            );
            await sleep(1500 * (attempt + 1));
          } else {
            break;
          }
        }
      }
    }

    throw lastError || new Error('No response from Gemini.');
  }
}

export default GeminiLLM;
