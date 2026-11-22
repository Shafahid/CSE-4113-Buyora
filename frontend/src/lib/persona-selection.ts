import type { Draft, Persona } from "./demo-data";

// The draft's personas are the selection sent to the API. The separate pool
// preserves edited/custom profiles when a checkbox is turned off.
export function personaChoices(draft: Draft, catalog: Persona[]): Persona[] {
  const profiles = new Map<string, Persona>();
  for (const profile of [...catalog, ...(draft.availablePersonas ?? []), ...draft.personas]) {
    profiles.set(profile.id, profile);
  }
  return [...profiles.values()];
}

export function setPersonaSelected(draft: Draft, profile: Persona, selected: boolean, limit: number): Draft {
  const included = draft.personas.some((p) => p.id === profile.id);
  if (selected && !included && draft.personas.length >= limit) {
    throw new Error(`Choose up to ${limit} buyer personas.`);
  }
  return {
    ...draft,
    availablePersonas: personaChoices(draft, [profile]),
    personas: selected
      ? included ? draft.personas : [...draft.personas, profile]
      : draft.personas.filter((p) => p.id !== profile.id),
  };
}
