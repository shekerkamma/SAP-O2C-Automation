"""
Centralized visual branding constants for chart generation.

All chart helpers reference this module so colour palette, typography,
and sizing can be updated in ONE place across the entire agent team.
"""

# ── Primary palette (SAP-inspired corporate tones) ────────────────────
BLUE       = "#0070C0"         # Primary accent – data bars, positive
DARK_BLUE  = "#003366"         # Secondary accent – headers, emphasis
TEAL       = "#4BC0C0"         # Success / healthy / green-equivalent
CORAL      = "#E74C3C"         # Danger / risk / shortfall
AMBER      = "#F39C12"         # Warning / in-progress / amber status
PURPLE     = "#8E44AD"         # Category accent 1
GREEN      = "#27AE60"         # Positive delta
LIGHT_GREY = "#BDC3C7"         # Neutral / inactive / no-data

# Transparent versions for bar fills
BLUE_T     = "rgba(0,112,192,0.75)"
TEAL_T     = "rgba(75,192,192,0.70)"
CORAL_T    = "rgba(231,76,60,0.70)"
AMBER_T    = "rgba(243,156,18,0.70)"
PURPLE_T   = "rgba(142,68,173,0.70)"
GREEN_T    = "rgba(39,174,96,0.70)"

# ── Semantic colour mappings ──────────────────────────────────────────
RAG = {
    "RED":   CORAL,
    "AMBER": AMBER,
    "GREEN": TEAL,
}

STATUS_COLORS = {
    "completed":  TEAL,
    "in_process": AMBER,
    "open":       BLUE,
    "blocked":    CORAL,
}

# "Above threshold" vs "below threshold" pair
ABOVE_THRESHOLD = BLUE
BELOW_THRESHOLD = CORAL

# Stacked / comparison pairs
STOCK_COLOR    = BLUE             # current stock
DEMAND_COLOR   = CORAL            # demand / shortfall
STOCK_COLOR_T  = BLUE_T
DEMAND_COLOR_T = CORAL_T

# ── Pie / doughnut palette (up to 10 segments) ───────────────────────
PIE_PALETTE = [
    BLUE, CORAL, AMBER, TEAL, PURPLE,
    GREEN, LIGHT_GREY, "#2980B9", "#D35400", "#1ABC9C",
]

# ── Chart-type-specific defaults ─────────────────────────────────────
BAR_PRIMARY     = BLUE_T          # default single-series bar colour
BAR_SECONDARY   = PURPLE_T        # second series (e.g. quantity)
BAR_REVENUE     = TEAL_T          # revenue-specific bars

# ── Layout defaults ──────────────────────────────────────────────────
CHART_WIDTH  = 600
CHART_HEIGHT = 360
CHART_BG     = "white"

# ── Font defaults ────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI, Helvetica, Arial, sans-serif"
LABEL_FONT_SIZE = 10
TITLE_FONT_SIZE = 12
DATALABEL_FONT_SIZE = 9
LEGEND_FONT_SIZE = 10
