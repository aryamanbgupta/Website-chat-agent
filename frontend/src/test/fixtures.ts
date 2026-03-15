import type {
  ProductCardData,
  CompatibilityResultData,
  DiagnosisData,
  DiagnosisCause,
  DiagnosisRecommendedPart,
  Message,
  ContentBlock,
} from '@/lib/types';

export function makeProductCard(overrides: Partial<ProductCardData> = {}): ProductCardData {
  return {
    ps_number: 'PS11752778',
    name: 'Refrigerator Water Inlet Valve',
    brand: 'Whirlpool',
    price: '47.82',
    rating: '4.5',
    review_count: '123',
    in_stock: true,
    image_url: 'https://example.com/part.jpg',
    source_url: 'https://partselect.com/PS11752778',
    ...overrides,
  };
}

export function makeCompatibilityResult(
  overrides: Partial<CompatibilityResultData> = {},
): CompatibilityResultData {
  return {
    compatible: true,
    confidence: 'verified',
    part_number: 'PS11752778',
    model_number: 'WDT780SAEM1',
    message: 'This part is compatible with your model.',
    ...overrides,
  };
}

export function makeDiagnosisCause(overrides: Partial<DiagnosisCause> = {}): DiagnosisCause {
  return {
    cause: 'Faulty Water Inlet Valve',
    description: 'The valve may be stuck or defective.',
    recommended_parts: ['PS11752778'],
    likelihood: 'High',
    ...overrides,
  };
}

export function makeDiagnosisRecommendedPart(
  overrides: Partial<DiagnosisRecommendedPart> = {},
): DiagnosisRecommendedPart {
  return {
    ps_number: 'PS11752778',
    name: 'Water Inlet Valve',
    brand: 'Whirlpool',
    price: '47.82',
    rating: '4.5',
    in_stock: true,
    image_url: 'https://example.com/part.jpg',
    source_url: 'https://partselect.com/PS11752778',
    ...overrides,
  };
}

export function makeDiagnosis(overrides: Partial<DiagnosisData> = {}): DiagnosisData {
  return {
    symptom: 'Ice maker not working',
    causes: [makeDiagnosisCause()],
    recommended_parts: [makeDiagnosisRecommendedPart()],
    follow_up_questions: ['When did the issue start?'],
    ...overrides,
  };
}

export function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: 'msg-1',
    role: 'assistant',
    content: [{ type: 'text', text: 'Hello' }],
    timestamp: Date.now(),
    ...overrides,
  };
}

export function makeTextBlock(text: string): ContentBlock {
  return { type: 'text', text };
}

export function makeProductCardBlock(
  overrides: Partial<ProductCardData> = {},
): ContentBlock {
  return { type: 'product_card', data: makeProductCard(overrides) };
}

export function makeCompatibilityBlock(
  overrides: Partial<CompatibilityResultData> = {},
): ContentBlock {
  return { type: 'compatibility_result', data: makeCompatibilityResult(overrides) };
}

export function makeDiagnosisBlock(overrides: Partial<DiagnosisData> = {}): ContentBlock {
  return { type: 'diagnosis', data: makeDiagnosis(overrides) };
}
