# Optional offline Rampart adapter

The deterministic CLI is usable without a model. Rampart supplies extra contextual
NER; it is not a secrets scanner or a reliable detector of Chinese/non-Latin names.
The engine does not blanket-redact URLs or retain Rampart's reversible session map.

The bridge uses Rampart's premasking, windowing, offset recovery and span repair,
then returns original-text spans to the Python engine. Its offsets are converted
from JavaScript UTF-16 to Unicode code points. Each invocation handles one input;
model startup is repeated across files (batching/GPU acceleration is future work).

## Setup (explicit, online provisioning only)

Use Node 22+ or Bun. In a separate local directory install exact dependencies:

```sh
npm install --save-exact @nationaldesignstudio/rampart@0.1.3 @huggingface/transformers@3.7.5
```

Keep the generated lockfile, installed dependencies, and model directory local.
Obtain Rampart's complete model assets through an explicitly approved download or
a trusted local checkout. The runtime itself never downloads assets. Verify the
model's source/license and record SHA-256 for **every** model/tokenizer/config file
used, plus the bridge and dependency lockfile. Provisioning is not performed by
loading the skill. Example `ner` configuration (replace all placeholders):

```json
{
  "version": 1,
  "ner": {
    "command": [
      "node", "/installed/skill/scripts/rampart_bridge.mjs",
      "/local/dependencies/node_modules/@nationaldesignstudio/rampart/dist/index.js",
      "/local/dependencies/node_modules/@huggingface/transformers/dist/transformers.node.mjs",
      "/local/models/rampart"
    ],
    "artifacts": {
      "/local/models/rampart/onnx/model_q4.onnx": "REPLACE_WITH_64_HEX_SHA256",
      "/local/models/rampart/tokenizer.json": "REPLACE_WITH_64_HEX_SHA256"
    },
    "timeout_seconds": 120
  }
}
```

Resolve the Transformers entrypoint from the installed package rather than assuming
the example filename exists. Rampart and bridge must resolve the **same** installed
Transformers instance. For trusted local source checkouts, Bun may load Rampart's
`index.ts`. The command and artifact paths belong in a local policy, not public docs
containing a personal absolute path. The example is incomplete until **all** used
assets/dependency identities are pinned.

Inference uses CPU and sets `allowRemoteModels=false`, `local_files_only` behavior
through the global Transformers environment, and disables external data downloads.
An unsupported artifact/backend or missing asset fails the scan. No automatic
fallback. Execute in a network-disabled sandbox for a stronger offline boundary;
the parent cannot prove that an arbitrary custom command never uses the network.

## Attribution and verification status

Rampart is by National Design Studio, https://github.com/nationaldesignstudio/rampart,
CC BY 4.0. The design was inspected at commit
`95798af5b0e71759e06f912d0a8b719f31744b20`. No Rampart source or model weights are
vendored here; the bridge imports its public API. Retain upstream attribution and
license when distributing dependencies/model assets.

The bridge is covered by protocol/offset tests; actual ONNX inference requires
locally provisioned dependencies and complete weights. Do not claim model coverage
based only on rules/protocol tests. GPU/CPU finding parity and corpus-specific
recall are not established by this skill.
