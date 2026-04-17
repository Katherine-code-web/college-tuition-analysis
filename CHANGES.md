# CHANGES.md

## 2026-04-17 — Stretch Tab, Scholarship Negotiator, Excluded-Schools Banner

---

### What Changed

#### `pages/8_Smart_Matcher.py`

1. **Excluded-schools banner** — Schools above budget × 1.2 are now captured before the
   hard filter. A visible `st.warning` banner appears at the top of results showing:
   - Count of schools excluded
   - Top 3 excluded schools by match score
   - Count of Stretch-qualifying schools
   Excluded schools are also logged to `st.session_state['excluded_by_budget']` as a list
   of dicts `{id, name, effective_price, match_score}` for downstream use.

2. **"Field earnings suppressed" explainer** — An `st.expander` was added below the
   summary line (visible when `n_suppressed > 0`) explaining why the U.S. Dept. of
   Education suppresses program-level earnings for cohorts < 30 students.

3. **Stretch tab** — A 4th tab "💰 Stretch" was added alongside Reach / Target / Safety.
   - Stretch is independent of admission classification (Reach/Target/Safety)
   - Sub-tiered: Tier 1 "NEGOTIABLE GAP" (COA ≤ budget × 1.3) and
     Tier 2 "AGGRESSIVE STRETCH" (1.3× < COA ≤ 1.8×)
   - "💬 Plan Negotiation" buttons route to the Scholarship Negotiator with pre-filled
     target school data via `st.session_state['negotiator_prefill']`

4. **COA resolution** — `_resolve_coa()` helper follows the spec priority:
   - International + any school → `tuition_out` first, then `net_price`
   - Domestic → `net_price`
   - Missing COA → exclude from Stretch, counted in `_n_suppressed_aid` banner

---

#### `pages/09_Scholarship_Negotiator.py` (NEW)

Multi-step wizard (Steps 1–7). Email template generator deferred.

- **Step 1:** Add 2–5 school offers (school name, sticker price, scholarship, deadline)
- **Step 2:** Pick one school as negotiation target; others become competitors
- **Step 3:** Enter selectivity data (admission rate, SAT avg, earnings, GPA 75th) →
  compute `estimate_selectivity_tier()` (1–10 proxy, not an official ranking)
- **Step 4–5:** `calculate_leverage()` → Plotly horizontal bar chart + colour-coded
  interpretation (Weak/Moderate/Strong)
- **Step 6:** `_suggested_ask()` → dollar amount + rationale bullets
- **Step 7:** Static action checklist (no email generator yet)

---

### Missing / Unverified Data Fields

The following College Scorecard fields are **not** currently pulled by `utils/api.py`
(`FIELDS` / `MATCHER_FIELDS`) and therefore **not available** in the Stretch tab:

| Spec Field | College Scorecard Column | Status |
|------------|--------------------------|--------|
| `SCH_AVG_INST_AID` | `latest.aid.median_grant.federal_title_iv` or `latest.aid.median_grant.total` | **Not pulled** — add to `MATCHER_FIELDS` |
| `PCT_INST_AID` | `latest.aid.students_with_any_loan_or_grant` or `latest.aid.pell_grant_rate` | **pell_rate is pulled** (used as proxy) |
| `COSTT4_A` (private total COA) | `latest.cost.attendance.academic_year` | **Not pulled** — currently using `tuition_out` / `net_price` as proxy |
| `COSTT4_OOS` (OOS total COA) | `latest.cost.attendance.academic_year` (OOS) | **Not pulled** — same proxy |

**Impact on Stretch tab:**
- Average institutional aid criterion (`avg_institutional_aid >= budget_gap × 0.7`) cannot
  be evaluated. Stretch filter currently uses only: COA range, match_score ≥ 7.0,
  pell_rate ≥ 0.3 (proxy for % receiving aid).
- Cards show "Avg. institutional aid: data unavailable" instead of a dollar figure.
- `Y schools had suppressed aid data` banner count reflects schools with null `pell_rate`.

**To fully implement the spec**, add these fields to `MATCHER_FIELDS` in `utils/api.py`:
```python
"latest.aid.median_grant.total",
"latest.cost.attendance.academic_year",
```
Then re-map in `matcher_result_to_row()`:
```python
"avg_inst_aid": r.get("latest.aid.median_grant.total"),
"coa_academic": r.get("latest.cost.attendance.academic_year"),
```

---

### Assumptions

1. **International student COA:** `tuition_out` (out-of-state tuition) is used as the
   best available proxy for COA. It does not include living expenses. The spec fallback
   of `TUITIONFEE_OUT + 18000` is not implemented because `18000` is an estimate; the
   current proxy avoids fabricating numbers.

2. **`pct_receiving_aid` proxy:** `pell_rate` (share of students receiving Pell grants)
   is used as the proxy for `PCT_INST_AID`. Pell grants are means-tested federal aid —
   a high pell_rate indicates the school serves students who need aid, not that
   institutional grants are available to international students (who are Pell-ineligible).
   This is a weak proxy. Flag for improvement once `latest.aid.students_with_any_loan_or_grant`
   is added to the pipeline.

3. **Selectivity tier `gpa_75th`:** College Scorecard does not publish graduate program
   GPA distributions. The `gpa_75th` field in the Scholarship Negotiator is user-entered
   (not fetched from an API). If left at 0, `profile_strength` is skipped and
   `peer_pressure` + `price_gap` are scaled up proportionally (44/56 weights).

4. **Stretch scoring of over-budget schools:** The over-budget DataFrame is scored
   using the same `score_schools_df()` as the main results. Match scores are relative to
   the over-budget subset only, which may not align with the main results ranking.

---

### Explicitly Deferred Items

- **Email template generator** (Step 7 of Scholarship Negotiator) — deferred to next
  iteration. Checklist includes a placeholder note.
- **yield_rate integration** — removed per spec (no reliable public data).
- **COSTT4_A / COSTT4_OOS** full COA pipeline — requires adding fields to `api.py`
  and re-testing (noted above).
- **H-1B sponsorship data** — mentioned in existing Smart Matcher TODO comment.
