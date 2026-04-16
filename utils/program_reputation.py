"""
Program reputation lookup for Smart Matcher — graduate mode.

When College Scorecard field-of-study earnings are suppressed (common for
graduate cohorts), the matcher uses these reputation tiers as a proxy for
program quality. Scores are 0.0–1.0, where 1.0 = top programs nationally.

⚠️ This table is manually maintained and based on commonly cited rankings
   (U.S. News, Poets & Quants, QS). It is NOT a substitute for official
   rankings. Update periodically — last reviewed April 2025.

Coverage: CIP 52 (Business/MBA), CIP 11 (CS/IT), CIP 14 (Engineering).
Schools not in this table receive a neutral score (None → 0.5 in ranking),
so absence from the table does NOT imply a bad program.
"""

# (unitid: int, cip_prefix: str) → tier 0.0–1.0
_SCORES: dict[tuple[int, str], float] = {

    # ── Business, Management & MBA (CIP 52) ───────────────────────────────────
    # Private (high selectivity, often suppressed data)
    (166683, "52"): 0.97,  # Boston University — Questrom
    (168148, "52"): 0.96,  # Babson College
    (191648, "52"): 0.95,  # New York University — Stern
    (130226, "52"): 0.95,  # Georgetown University — McDonough
    (130794, "52"): 0.93,  # Yale School of Management
    (217156, "52"): 0.92,  # University of Notre Dame — Mendoza
    (220978, "52"): 0.93,  # Vanderbilt — Owen

    # Public — top MBA/MS business programs (accessible to international students)
    (151351, "52"): 0.95,  # Indiana University — Kelley
    (228778, "52"): 0.94,  # UT Austin — McCombs
    (240444, "52"): 0.93,  # University of Wisconsin-Madison
    (199120, "52"): 0.92,  # UNC Chapel Hill — Kenan-Flagler
    (174066, "52"): 0.88,  # University of Minnesota — Carlson
    (204796, "52"): 0.87,  # Ohio State — Fisher
    (163286, "52"): 0.86,  # University of Maryland — Smith
    (214777, "52"): 0.85,  # Penn State — Smeal
    (228723, "52"): 0.85,  # Texas A&M — Mays
    (139959, "52"): 0.85,  # University of Georgia — Terry
    (236948, "52"): 0.84,  # University of Washington — Foster
    (134130, "52"): 0.83,  # University of Florida — Hough
    (215293, "52"): 0.82,  # University of Pittsburgh — Katz
    (104151, "52"): 0.82,  # Arizona State — Carey
    (171100, "52"): 0.80,  # Michigan State — Broad
    (145637, "52"): 0.80,  # UIUC — Gies
    (127060, "52"): 0.75,  # University of Colorado Boulder — Leeds
    (104717, "52"): 0.74,  # University of Arizona — Eller
    (218663, "52"): 0.72,  # University of South Carolina — Darla Moore
    (179566, "52"): 0.70,  # University of Missouri — Trulaske
    (153658, "52"): 0.68,  # Iowa State University
    (100751, "52"): 0.72,  # University of Alabama — Culverhouse
    (209542, "52"): 0.75,  # University of Oregon — Lundquist

    # ── Computer Science & IT (CIP 11) ────────────────────────────────────────
    # Private
    (211440, "11"): 0.99,  # Carnegie Mellon — SCS
    (166027, "11"): 0.98,  # MIT (grad EECS)
    (130794, "11"): 0.97,  # Yale
    (243744, "11"): 0.97,  # Stanford
    (190150, "11"): 0.97,  # Columbia
    (194824, "11"): 0.96,  # Cornell
    (215062, "11"): 0.96,  # University of Pennsylvania
    (170976, "11"): 0.95,  # University of Michigan

    # Public
    (139755, "11"): 0.99,  # Georgia Tech (OMSCS — top MS CS)
    (110635, "11"): 0.99,  # UC Berkeley
    (110662, "11"): 0.97,  # UCLA
    (228778, "11"): 0.97,  # UT Austin
    (145637, "11"): 0.96,  # UIUC
    (236948, "11"): 0.95,  # University of Washington
    (243780, "11"): 0.94,  # Purdue
    (166629, "11"): 0.90,  # UMass Amherst
    (163286, "11"): 0.88,  # University of Maryland
    (204796, "11"): 0.86,  # Ohio State
    (174066, "11"): 0.85,  # University of Minnesota
    (199120, "11"): 0.83,  # UNC Chapel Hill
    (171100, "11"): 0.83,  # Michigan State
    (104151, "11"): 0.80,  # Arizona State
    (228723, "11"): 0.82,  # Texas A&M
    (214777, "11"): 0.80,  # Penn State
    (240444, "11"): 0.82,  # Wisconsin-Madison

    # ── Engineering (CIP 14) ──────────────────────────────────────────────────
    # Private
    (211440, "14"): 0.99,  # Carnegie Mellon
    (166027, "14"): 0.99,  # MIT
    (243744, "14"): 0.98,  # Stanford
    (194824, "14"): 0.97,  # Cornell
    (215062, "14"): 0.95,  # University of Pennsylvania
    (170976, "14"): 0.95,  # University of Michigan

    # Public
    (139755, "14"): 0.98,  # Georgia Tech
    (145637, "14"): 0.97,  # UIUC
    (243780, "14"): 0.96,  # Purdue
    (110635, "14"): 0.98,  # UC Berkeley
    (110662, "14"): 0.96,  # UCLA
    (228778, "14"): 0.95,  # UT Austin
    (236948, "14"): 0.92,  # University of Washington
    (163286, "14"): 0.89,  # University of Maryland
    (204796, "14"): 0.87,  # Ohio State
    (171100, "14"): 0.86,  # Michigan State
    (174066, "14"): 0.83,  # University of Minnesota
    (228723, "14"): 0.85,  # Texas A&M
    (214777, "14"): 0.83,  # Penn State
    (104151, "14"): 0.80,  # Arizona State
    (240444, "14"): 0.83,  # Wisconsin-Madison
    (199120, "14"): 0.81,  # UNC Chapel Hill
    (170082, "14"): 0.82,  # Michigan Tech
}


def get_reputation_score(cip_prefix: str, target_degree: str, unitid: int) -> float | None:
    """
    Return a program reputation score (0.0–1.0) for the given school and field,
    or None if the school is not in the table.

    A score of None means "unknown, treat as neutral" — it is NOT a low score.
    The caller should fill None with 0.5 before ranking so unknown schools
    land in the middle rather than at the bottom.

    Arguments:
        cip_prefix:    2-digit CIP code string, e.g. "52"
        target_degree: degree level string, e.g. "Master's", "MBA"
        unitid:        integer IPEDS unit ID
    """
    return _SCORES.get((unitid, cip_prefix))
