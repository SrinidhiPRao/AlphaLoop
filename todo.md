# TODO — LLM‑Based Formulaic Alpha Research Framework

This file tracks the implementation status and next steps for the paper:
**LLM‑Based Formulaic Alpha Mining with Hybrid RL Frameworks**

---

## ✅ Completed (Infrastructure Backbone)

### Data Layer

- [x] OHLCV ingestion from **yfinance**
- [x] Long‑format panel storage: `(date, ticker) → features`
- [x] Local persistence (CSV)
- [x] Reproducible data loading

### Operator Engine (Appendix A compliant)

- [x] Cross‑Sectional Unary (xAbs, xLog)
- [x] Cross‑Sectional Binary (Add, Sub, Mul, Div, Greater, Less)
- [x] Time‑Series Unary (Ref, Mean, Med, Sum, Std, Var, Max, Min, Mad, Delta, WMA, EMA)
- [x] Time‑Series Binary (Cov, Corr)
- [x] Correct per‑ticker rolling semantics

### Expression Parsing & Evaluation

- [x] Safe AST‑based expression parser
- [x] Strict function‑only grammar (no infix ops)
- [x] Variable binding to panel data
- [x] Nested expression support
- [x] Invalid syntax rejection (parser‑level filtering)

### Backtesting Core

- [x] 20‑day forward return target
- [x] Daily cross‑sectional IC computation
- [x] Rank IC computation
- [x] IC / ICIR summary statistics
- [x] End‑to‑end run from expression → IC

---

## 🔄 In Progress / Next Immediate Steps

### Alpha Abstractions

- [ ] `Alpha` object (expression + cached Series)
- [ ] Alpha validity checks (NaN %, constant detection)
- [ ] Alpha normalization (z‑score / rank‑based)

### Alpha Set Evaluation

- [ ] Alpha set container (list of expressions)
- [ ] Cross‑sectional ensemble combination
- [ ] IC‑weighted alpha aggregation
- [ ] Alpha redundancy detection (pairwise corr)

---

## 🧠 RL‑Based Alpha Optimization (Paper Core)

### Environment Design

- [ ] State: current alpha set statistics
- [ ] Action: reweight / replace alpha
- [ ] Reward: IC / Rank IC improvement
- [ ] Episode definition

### Optimization Logic

- [ ] Alpha weight optimization loop
- [ ] Stability handling after LLM mutation
- [ ] Local‑optima detection

---

## 🤖 LLM Integration (Later Phase)

### Prompting

- [ ] Syntax‑template‑based few‑shot prompts
- [ ] Operator usage constraints
- [ ] Token‑length control

### LLM Usage Modes

- [ ] Single‑step alpha set generation
- [ ] Multi‑round alpha mutation
- [ ] Replace lowest‑weight alpha logic

### Output Handling

- [ ] Expression parsing & correction loop
- [ ] Invalid expression discard
- [ ] Diversity enforcement

---

## 📊 Experiments & Evaluation

### Dataset

- [ ] CSI300 constituent list
- [ ] Survivorship bias handling
- [ ] Trading calendar alignment

### Metrics

- [ ] ICIR
- [ ] Rank ICIR
- [ ] Rolling IC plots
- [ ] Alpha turnover analysis

### Baselines

- [ ] Random formula generator
- [ ] Genetic Programming baseline
- [ ] RL‑only baseline

---

## 🧪 Reproducibility & Engineering

- [ ] Configuration system (YAML/JSON)
- [ ] Experiment logging
- [ ] Seed control
- [ ] Result serialization

---

## 📎 Paper Alignment Checks

- [ ] Verify no training–test leakage
- [ ] Match window sizes exactly
- [ ] Validate IC computation method
- [ ] Confirm LLM model assumptions

---

## 🧭 Optional Extensions

- [ ] Portfolio backtesting (long–short)
- [ ] Transaction cost modeling
- [ ] Risk‑adjusted returns
- [ ] Alpha interpretability reports

---

**Current Status:**

> Infrastructure complete. Ready to implement alpha‑set logic and RL loop.

**Recommended Next Task:**

> Implement _Alpha Set + IC‑weighted ensemble evaluator_.
