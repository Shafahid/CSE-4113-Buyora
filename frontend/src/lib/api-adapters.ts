import type { ApiSchemas } from "./api-schema";
import type { Post, Product } from "./demo-data";

export function productFromApi(value: ApiSchemas["ProductResponse"] | ApiSchemas["ProductDetail"]): Product {
  const images = "images" in value ? value.images : [];
  return {
    id: String(value.id), name: value.name, category: value.category, price: Number(value.price),
    description: value.description ?? "", features: value.features?.join("\n") ?? "",
    warranty: value.warranty ?? "", delivery: value.delivery_info ?? "", returns: value.return_policy ?? "",
    archived: value.status === "archived", image: images[0]?.url ?? "", art: "tote",
    images: images.map((image) => ({ id: String(image.id), url: image.url })),
  };
}
export function productToApi(value: Product): ApiSchemas["ProductCreate"] {
  return {
    name: value.name.trim(), category: value.category, price: value.price.toFixed(2),
    description: value.description || null, features: value.features.split(/\r?\n/).map((s) => s.trim()).filter(Boolean),
    warranty: value.warranty || null, delivery_info: value.delivery || null, return_policy: value.returns || null,
  };
}
export function postToApi(value: Post): ApiSchemas["VersionInput"] {
  return {
    headline: value.headline.trim(), body: value.body.trim(), offer: value.offer || null,
    call_to_action: value.cta || null, hashtags: value.hashtags.split(/[\s,]+/).filter(Boolean), platform: value.platform,
  };
}
export function postFromApi(detail: ApiSchemas["PostDetail"], versions: ApiSchemas["VersionResponse"][] = []): Post {
  const latest = detail.latest_version;
  return {
    id: String(detail.id), productId: String(detail.product_id), headline: latest.headline, body: latest.body,
    offer: latest.offer ?? "", cta: latest.call_to_action ?? "", hashtags: latest.hashtags?.join(" ") ?? "", platform: latest.platform,
    latestVersionId: String(latest.id), latestVersionCreatedAt: latest.created_at, versionNumber: latest.version_number,
    versions: versions.filter((v) => v.id !== latest.id).sort((a, b) => a.version_number - b.version_number).map((v) => ({
      id: String(v.id), body: v.body, createdAt: v.created_at, versionNumber: v.version_number,
      headline: v.headline, offer: v.offer ?? "", cta: v.call_to_action ?? "", hashtags: v.hashtags?.join(" ") ?? "", platform: v.platform,
    })),
  };
}
