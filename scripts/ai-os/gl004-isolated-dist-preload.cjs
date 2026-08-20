"use strict";
/**
 * Child-process only. Injects GL004_ISOLATED_DIST into Next loadConfig
 * before the module compiles. Does not listen. Does not touch live `.next`.
 * Law: ISOLATED_BUILD_NE_SECOND_RUNTIME.
 */
const Module = require("module");

function install() {
  const dist = process.env.GL004_ISOLATED_DIST;
  if (!dist) {
    throw new Error("GL004_ISOLATED_DIST unset");
  }
  const origCompile = Module.prototype._compile;
  if (origCompile.__gl004Injected) {
    return;
  }
  function gl004Compile(content, filename) {
    const norm = String(filename).replace(/\\/g, "/");
    if (norm.endsWith("/next/dist/server/config.js")) {
      const needle =
        "async function loadConfig(phase, dir, { customConfig, rawConfig, silent = true, reportExperimentalFeatures, reactProductionProfiling, debugPrerender, bundler } = {}) {";
      if (!content.includes(needle)) {
        throw new Error("GL004_PRELOAD_NEEDLE_MISS");
      }
      const inject =
        needle +
        "\n        if (process.env.GL004_ISOLATED_DIST) { customConfig = Object.assign({}, customConfig || {}, { distDir: process.env.GL004_ISOLATED_DIST }); }\n";
      content = content.replace(needle, inject);
    }
    return origCompile.call(this, content, filename);
  }
  gl004Compile.__gl004Injected = true;
  Module.prototype._compile = gl004Compile;
}

install();
