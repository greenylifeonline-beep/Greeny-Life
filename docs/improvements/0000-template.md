# 0000 — receipt template (copy, renumber, fill every section)

## Compared
- branch: <branch>
- main: <merged-ref sha>

## Change summary
What changed and why, in terms a reviewer can verify.

### How measured

<!-- EVIDENCE CONTRACT: this exact H3 header, commands in a ```bash fence.
     Commands are RE-RUN VERBATIM against merged main by `govern score`;
     they must be hermetic (no live services, no wall-clock luck) and must
     fail loudly when the claim is false. A receipt without this block can
     never be scored and earns nothing. -->

```bash
pytest tests/test_example.py -q
```

## Metric delta
The measured before/after, or the invariant now enforced.

## Verdict
improvement

## Confidence
0.9

## change_class
tooling
