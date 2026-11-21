// Generated from FastAPI OpenAPI; do not edit by hand.
// Regenerate from backend: uv run python scripts/export_frontend_contract.py
export type ApiSchemas = {
  "AgeRange": { "min": number; "max"?: number | null; };
  "AudienceSettings": { "location"?: string | null; "age_range"?: ApiSchemas["AgeRange"] | null; "interests"?: Array<string> | null; "purchasing_preference"?: "cash_on_delivery" | "online_payment" | "in_store_pickup" | null; "budget_sensitivity"?: "low" | "medium" | "high" | null; "product_needs"?: string | null; };
  "Body_upload_product_image_products__product_id__images_post": { "file": string; };
  "Characteristics": { "label"?: string | null; "age_range"?: ApiSchemas["PersonaAgeRange"] | null; [key: string]: unknown; };
  "Credentials": { "email": string; "password": string; };
  "HTTPValidationError": { "detail"?: Array<ApiSchemas["ValidationError"]>; };
  "HealthResponse": { "status"?: "ok"; };
  "ImageCreated": { "id": number; "product_id": number; "sort_order": number; };
  "ImageResponse": { "id": number; "sort_order": number; "url": string; };
  "PersonaAgeRange": { "min"?: number | null; "max"?: number | null; };
  "PersonaCreate": { "name": string; "characteristics"?: ApiSchemas["Characteristics"]; "needs"?: Array<string>; "preferences"?: Array<string>; "budget_sensitivity"?: "low" | "medium" | "high" | null; "is_selected"?: boolean; };
  "PersonaResponse": { "id": number; "simulation_id": number; "name": string; "characteristics": { [key: string]: unknown; }; "needs": Array<string>; "preferences": Array<string>; "budget_sensitivity": string | null; "is_selected": boolean; };
  "PersonaUpdate": { "name"?: string | null; "characteristics"?: ApiSchemas["Characteristics"] | null; "needs"?: Array<string> | null; "preferences"?: Array<string> | null; "budget_sensitivity"?: "low" | "medium" | "high" | null; "is_selected"?: boolean | null; };
  "PostDetail": { "id": number; "product_id": number; "created_at": string; "latest_version": ApiSchemas["VersionResponse"]; };
  "PostListItem": { "id": number; "product_id": number; "latest_version_id": number; "version_number": number; "headline": string; "platform": string; };
  "ProductCreate": { "name": string; "category": string; "price": number | string; "description"?: string | null; "features"?: Array<string>; "warranty"?: string | null; "delivery_info"?: string | null; "return_policy"?: string | null; };
  "ProductDetail": { "name": string; "category": string; "price": string; "description"?: string | null; "features"?: Array<string>; "warranty"?: string | null; "delivery_info"?: string | null; "return_policy"?: string | null; "id": number; "seller_id": number; "currency": string; "status": string; "images": Array<ApiSchemas["ImageResponse"]>; };
  "ProductResponse": { "name": string; "category": string; "price": string; "description"?: string | null; "features"?: Array<string>; "warranty"?: string | null; "delivery_info"?: string | null; "return_policy"?: string | null; "id": number; "seller_id": number; "currency": string; "status": string; };
  "ProductUpdate": { "name"?: string | null; "category"?: string | null; "price"?: number | string | null; "description"?: string | null; "features"?: Array<string> | null; "warranty"?: string | null; "delivery_info"?: string | null; "return_policy"?: string | null; "status"?: "active" | "archived" | null; };
  "PublicUser": { "id": number; "email": string; "display_name": string; };
  "Registration": { "email": string; "password": string; "display_name": string; };
  "SimulationCreate": { "post_version_id": number; "audience_settings"?: ApiSchemas["AudienceSettings"]; "language"?: "en" | "bn"; };
  "SimulationResponse": { "id": number; "post_version_id": number; "audience_settings": ApiSchemas["AudienceSettings"]; "language": "en" | "bn"; "status": string; };
  "SimulationUpdate": { "audience_settings"?: ApiSchemas["AudienceSettings"] | null; "language"?: "en" | "bn" | null; };
  "ValidationError": { "loc": Array<string | number>; "msg": string; "type": string; "input"?: unknown; "ctx"?: Record<string, unknown>; };
  "VersionInput": { "headline": string; "body": string; "offer"?: string | null; "call_to_action"?: string | null; "hashtags"?: Array<string>; "platform": string; };
  "VersionResponse": { "headline": string; "body": string; "offer"?: string | null; "call_to_action"?: string | null; "hashtags"?: Array<string>; "platform": string; "id": number; "post_id": number; "version_number": number; "created_at": string; };
};
