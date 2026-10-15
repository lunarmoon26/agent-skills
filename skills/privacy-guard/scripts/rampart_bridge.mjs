// Optional local adapter; no upstream code or model weights are vendored.
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

export function codePointOffset(text, utf16Offset) {
  if (!Number.isInteger(utf16Offset) || utf16Offset < 0 || utf16Offset > text.length ||
      (utf16Offset > 0 && utf16Offset < text.length &&
       /[\uD800-\uDBFF]/.test(text[utf16Offset - 1]) && /[\uDC00-\uDFFF]/.test(text[utf16Offset]))) {
    throw new Error('invalid offset');
  }
  return [...text.slice(0, utf16Offset)].length;
}

async function main() {
  const [rampartPath, transformersPath, modelPath] = process.argv.slice(2);
  if (!rampartPath || !transformersPath || !modelPath || process.argv.length !== 5) {
    throw new Error('invalid arguments');
  }
  // Keep library logging out of the JSON protocol (parent suppresses stderr).
  console.log = (...args) => console.error(...args);
  const { env } = await import(pathToFileURL(resolve(transformersPath)).href);
  env.allowRemoteModels = false;
  env.allowLocalModels = true;
  env.useBrowserCache = false;
  env.useFSCache = false;
  const { detectHeuristics, premask, projectMaskedSpan, loadNerClassifier, detectNer } =
    await import(pathToFileURL(resolve(rampartPath)).href);
  let input = '';
  for await (const chunk of process.stdin) {
    input += chunk;
    if (Buffer.byteLength(input) > 80 * 1024 * 1024) throw new Error('oversize input');
  }
  const { text } = JSON.parse(input);
  if (typeof text !== 'string') throw new Error('invalid request');
  const classifier = await loadNerClassifier({ model: resolve(modelPath), device: 'cpu', minScore: 0.4 });
  const projection = premask(text, detectHeuristics(text));
  const spans = await detectNer(projection.masked, classifier, 0.4);
  const output = spans.map(s => projectMaskedSpan(s, text, projection)).filter(Boolean).map(s => ({
    start: codePointOffset(text, s.start), end: codePointOffset(text, s.end), label: s.label, score: s.score,
  }));
  process.stdout.write(JSON.stringify(output));
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(() => { process.stderr.write('local detector failed\n'); process.exitCode = 2; });
}
