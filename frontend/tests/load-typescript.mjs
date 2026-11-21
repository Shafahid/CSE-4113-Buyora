import { readFile } from "node:fs/promises";
import ts from "typescript";

// Resolve local imports into data URLs so tests need no runner dependency or
// generated files. React is injected only when testing the external store.
export function createTypeScriptLoader(overrides = {}) {
  const cache = new Map();
  async function moduleUrl(url) {
    if (cache.has(url.href)) return cache.get(url.href);
    const source = await readFile(url, "utf8");
    let { outputText } = ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
    });
    const imports = [...outputText.matchAll(/(?:from\s*|import\s*)["']([^"']+)["']/g)];
    for (const match of imports) {
      const name = match[1];
      const resolved = overrides[name] ?? (name.startsWith(".") ? await moduleUrl(new URL(name + ".ts", url)) : null);
      if (resolved) outputText = outputText.replaceAll(`"${name}"`, JSON.stringify(resolved)).replaceAll(`'${name}'`, JSON.stringify(resolved));
    }
    outputText += `\n//# sourceURL=${url.href}\n`;
    const result = "data:text/javascript;base64," + Buffer.from(outputText).toString("base64");
    cache.set(url.href, result);
    return result;
  }
  return async (path) => import(await moduleUrl(new URL(path, import.meta.url)));
}
