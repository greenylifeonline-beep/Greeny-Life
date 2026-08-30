#!/usr/bin/env node
"use strict";
/**
 * Isolated `next build` entry. Installs distDir injection, then runs Next's CLI.
 * Never binds a port. Never kills the live next-server.
 */
process.env.NODE_ENV = process.env.NODE_ENV || "production";
process.env.NEXT_RUNTIME = process.env.NEXT_RUNTIME || "nodejs";
process.env.GL004_ISOLATED_DIST = process.env.GL004_ISOLATED_DIST || ".next-gl004-proof";

require("./gl004-isolated-dist-preload.cjs");

process.argv = [process.argv[0], require.resolve("next/dist/bin/next"), "build", ...process.argv.slice(2)];
require("next/dist/bin/next");
