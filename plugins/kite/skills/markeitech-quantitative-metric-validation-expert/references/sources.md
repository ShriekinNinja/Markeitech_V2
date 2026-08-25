# Sources And Provenance

Research cut: 2026-08-25. Tracked Markeitech metric and Stage 9 contracts are controlling.
Refresh exact library/version sources when used.

- [BIPM SI Brochure](https://www.bipm.org/en/publications/si-brochure): unit and dimension
  discipline; not finance-specific metric meaning.
- [NumPy floating-point error handling](https://numpy.org/doc/stable/reference/routines.err.html):
  explicit divide/invalid/overflow policy; verify pinned local behavior.
- [pandas rolling API](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.rolling.html):
  window/default comparison only; not a universal Markeitech definition.
- [TA-Lib function stability](https://ta-lib.org/functions/stability.html): initialization classes
  and parity questions; TA-Lib is not selected as a dependency.
- [NIST/SEMATECH handbook](https://www.itl.nist.gov/div898/handbook/): reproducible diagnostics;
  select only methods appropriate to the claim.

This role adopts formula/window/warmup/numerical and diagnostic material from the preserved
`kite-advisor-quant-metric-validation` candidate. Its broader statistical and causal-model claims
remain with the statistical-learning advisor. No third-party skill content is copied.
