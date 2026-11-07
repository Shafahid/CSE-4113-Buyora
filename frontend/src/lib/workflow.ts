import type { Draft, Product, Report } from "./demo-data";

export function postError(draft: Draft, product: Product | undefined): string {
  if (!product || product.archived || product.id !== draft.productId)
    return "Choose an active product before running the simulation.";
  if (draft.post.productId !== product.id)
    return "The post belongs to a different product. Choose your product again.";
  if (!draft.post.headline.trim() || draft.post.body.trim().length < 20)
    return "Add a headline and write a caption of at least 20 characters.";
  return "";
}
export function simulationError(
  draft: Draft,
  product: Product | undefined,
): string {
  const invalidPost = postError(draft, product);
  if (invalidPost) return invalidPost;
  if (draft.personas.length < 2 || draft.personas.length > 8)
    return "Choose between 2 and 8 buyer personas.";
  if (new Set(draft.personas.map((p) => p.id)).size !== draft.personas.length)
    return "Each buyer persona must have its own identity. Regenerate the sample set.";
  if (
    draft.personas.some(
      (p) =>
        ![p.name, p.role, p.age, p.location, p.need].every((v) => v.trim()),
    )
  )
    return "Complete the name, buyer type, age, location, and needs for each persona.";
  return "";
}
export function comparisonSelection(
  reports: Report[],
  leftId: string,
  rightId: string,
) {
  const completed = reports.filter(
    (r) =>
      r.reactions.length > 0 &&
      r.reactions.every((x) => x.status === "complete"),
  );
  const requestedRight = completed.find((r) => r.id === rightId);
  const left =
    completed.find((r) => r.id === leftId) ||
    completed.find((r) => r.id !== requestedRight?.id) ||
    completed[0];
  const right = requestedRight || completed.find((r) => r.id !== left?.id);
  return { reports: completed, left, right };
}
