# RAIOS Adaptive Model Lab

Generated: 2026-08-15T21:51:44.2025689+02:00

## Hardware

Total RAM: 7.8 GB
Free RAM at start: 0.67 GB
Free Disk: 106.6 GB

## Fast Lane

Model: deepseek-r1:1.5b
Class: INTERACTIVE
Tokens/sec: 19.45
Context tested: 2048
RAM after inference: 1.63 GB

## Deep Lane

Model: deepseek-r1:7b
Class: NOT_TESTED
Tokens/sec: 0
RAM after inference: 0 GB

## Router Decision

Interactive:
deepseek-local-fast

Deep reasoning:
deepseek-local-fast

Batch:
deepseek-local-fast

Privacy:
LOCAL_ONLY

## Architecture

FAST LANE
→ lightweight local work

DEEP LANE
→ difficult/background work if resource-safe

Future compute node
→ larger models

No paid model API is required.
