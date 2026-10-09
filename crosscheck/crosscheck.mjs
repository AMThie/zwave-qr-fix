// Cross-check zwave_qr_fix against the reference parser of Z-Wave JS.
//
// Usage: node crosscheck.mjs vectors.json
// The vectors are produced by generate_vectors.py.

import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { parseQRCodeString } from "@zwave-js/core";

const INVALID_QR_CODE = 1406; // ZWaveErrorCodes.Security2CC_InvalidQRCode

const require = createRequire(import.meta.url);
const { version } = require("@zwave-js/core/package.json");
const vectors = JSON.parse(readFileSync(process.argv[2], "utf8"));

let failures = 0;
let notes = 0;

for (const v of vectors) {
  let result;
  let error;
  try {
    result = await parseQRCodeString(v.input);
  } catch (e) {
    if (e?.code !== INVALID_QR_CODE) throw e;
    error = e;
  }

  const accepted = error === undefined;
  if (accepted !== v.accepted) {
    const msg = `${v.name}: expected ${v.accepted ? "accept" : "reject"}, got ${
      accepted ? "accept" : `reject (${error.message})`
    }`;
    if (v.informational) {
      notes++;
      console.log(`note  ${msg}`);
    } else {
      failures++;
      console.log(`FAIL  ${msg}`);
    }
    continue;
  }

  for (const [key, expected] of Object.entries(v.fields ?? {})) {
    const actual = result[key];
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
      failures++;
      console.log(
        `FAIL  ${v.name}: ${key} = ${JSON.stringify(actual)}, expected ${JSON.stringify(expected)}`,
      );
    }
  }
}

console.log(
  `@zwave-js/core ${version}: ${vectors.length} vectors, ${failures} failures, ${notes} notes`,
);
process.exitCode = failures ? 1 : 0;
