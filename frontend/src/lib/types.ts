export interface ProductCardData {
  ps_number: string;
  name: string;
  brand: string;
  price: string;
  rating: string;
  review_count: string;
  in_stock: boolean;
  image_url: string;
  source_url: string;
  installation_difficulty?: string;
  installation_time?: string;
  symptoms_fixed?: string[];
  description?: string;
  mfg_part_number?: string;
  appliance_type?: string;
  video_url?: string;
}

export interface CompatibilityResultData {
  compatible: boolean | null;
  confidence: "verified" | "not_in_data" | "part_not_found";
  part_number: string;
  model_number: string;
  part_name?: string;
  part_brand?: string;
  price?: string;
  message: string;
  source_url?: string;
}

export interface DiagnosisCause {
  cause: string;
  description: string;
  recommended_parts: string[];
  likelihood: string;
  linked_parts?: string[];
  source_url?: string;
}

export interface DiagnosisRecommendedPart {
  ps_number: string;
  name: string;
  brand: string;
  price: string;
  rating: string;
  in_stock: boolean;
  image_url: string;
  source_url: string;
}

export interface DiagnosisData {
  symptom: string;
  causes: DiagnosisCause[];
  recommended_parts: DiagnosisRecommendedPart[];
  follow_up_questions: string[];
  knowledge_snippets?: {
    content: string;
    source_type: string;
    title: string;
    url: string;
  }[];
  appliance_type?: string;
  matched_symptom?: string;
}

export type ContentBlock =
  | { type: "text"; text: string }
  | { type: "product_card"; data: ProductCardData }
  | { type: "compatibility_result"; data: CompatibilityResultData }
  | { type: "diagnosis"; data: DiagnosisData }
  | { type: "status"; text: string };

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: ContentBlock[];
  timestamp: number;
  isStreaming?: boolean;
  suggestions?: string[];
}

export interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  error: string | null;
  statusText: string | null;
}

export type ChatAction =
  | { type: "ADD_USER_MESSAGE"; message: Message }
  | { type: "ADD_ASSISTANT_MESSAGE"; message: Message }
  | { type: "APPEND_TEXT_DELTA"; text: string }
  | { type: "ADD_CONTENT_BLOCK"; block: ContentBlock }
  | { type: "SET_STATUS"; text: string }
  | { type: "SET_SUGGESTIONS"; options: string[] }
  | { type: "SET_ERROR"; error: string }
  | { type: "FINALIZE_STREAM" }
  | { type: "CLEAR_MESSAGES" };
