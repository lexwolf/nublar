# TODO — AFM Tools Refactor Follow-ups

## ⚠️ Dependencies
- [ ] Decide whether SciPy dependency is acceptable for reproducibility
  - Currently used in `preprocess.py` and `segmentation.py`
  - If not acceptable → plan fallback (e.g. NumPy-only implementation)

## ⚠️ Baseline Definition
- [ ] Document and justify baseline choice:
  - Currently: `estimate_baseline(z, q=0.30)`
  - Needs explanation in Methods section OR parameterization

## ⚠️ Smoothing Parameter
- [ ] Make Gaussian smoothing explicit:
  - Currently fixed: `sigma=1.0`
  - Consider:
    - exposing as CLI parameter
    - documenting physical meaning

## ⚠️ Unit Robustness
- [ ] Handle non-µm scans safely:
  - `dx_nm` / `dy_nm` may be `None`
  - Add validation or fallback conversion
  - Avoid `float(None)` crashes

## ⚠️ Derived Observables Consistency
- [ ] Move `derived_reff_nm` into `features.py`
  - Keep all physical definitions in one place
  - Avoid duplication across scripts

## 🧪 (Optional but useful)
- [ ] Add minimal sanity checks:
  - e.g. warning if coverage > 1 or density = 0
- [ ] Add quick consistency plot helpers (optional)

---

## 🧠 Reminder

Do NOT change physics silently while addressing these.
All changes must be:
- explicit
- documented
- reproducible
