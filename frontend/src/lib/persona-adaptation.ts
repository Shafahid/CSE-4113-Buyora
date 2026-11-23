import type { Draft, Persona, Product } from "./demo-data";

// Ignore saved version IDs: saving the same editor contents must not invalidate
// the pending generation request. Include every editable input that affects it.
export function personaInputSignature(draft: Draft, product?: Product) {
  const { headline, body, offer, cta, hashtags, platform } = draft.post;
  const facts = product && { id: product.id, name: product.name, price: product.price, category: product.category, description: product.description, features: product.features, warranty: product.warranty, delivery: product.delivery, returns: product.returns };
  return JSON.stringify({ product: facts, post: { headline, body, offer, cta, hashtags, platform }, audience: draft.audience, language: draft.language, personas: draft.personas });
}

export function applyAdaptedPersonas(draft: Draft, profiles: Persona[], signature: string, product?: Product): Draft {
  if (personaInputSignature(draft, product) !== signature) return draft;
  const selected = new Set(draft.personas.map((p) => p.id));
  if (profiles.length !== selected.size || new Set(profiles.map((p) => p.id)).size !== selected.size || profiles.some((p) => !selected.has(p.id))) {
    throw new Error("Generated profiles did not match your selected personas.");
  }
  const byId = new Map(profiles.map((p) => [p.id, p]));
  const pool = draft.availablePersonas ?? draft.personas;
  return { ...draft, personas: draft.personas.map((p) => byId.get(p.id)!), availablePersonas: pool.map((p) => byId.get(p.id) ?? p), personaAdaptation: undefined };
}
