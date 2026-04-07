"""
Global comic/cartoon theme — inspired by bold illustration style.
Inject get_theme_css() into every page via st.markdown(..., unsafe_allow_html=True).
"""

def get_theme_css() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka+One&family=Nunito:wght@700;800;900&display=swap');

/* ── Root variables ─────────────────────────────────────────────────────── */
:root {
    --bg:        #FFF3E8;
    --orange:    #FF8C42;
    --red:       #E8503A;
    --pink:      #FFB5A0;
    --yellow:    #FFD166;
    --green:     #6BCB77;
    --blue:      #4D96FF;
    --purple:    #9B5DE5;
    --ink:       #1A1A1A;
    --white:     #FFFFFF;
    --shadow:    3px 3px 0px var(--ink);
    --radius:    12px;
    --border:    2.5px solid var(--ink);
}

/* ── Page background ────────────────────────────────────────────────────── */
.stApp {
    background-color: var(--bg) !important;
    background-image: radial-gradient(circle, #d4a57430 1px, transparent 1px);
    background-size: 28px 28px;
}

/* ── Global font ────────────────────────────────────────────────────────── */
html, body, [class*="css"], .stMarkdown, p, li, span, label {
    font-family: 'Nunito', sans-serif !important;
    font-weight: 700;
    color: var(--ink);
}
h1, h2, h3, h4 {
    font-family: 'Fredoka One', cursive !important;
    color: var(--ink) !important;
    letter-spacing: 0.5px;
}

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: var(--orange) !important;
    border-right: var(--border) !important;
}
[data-testid="stSidebar"] * {
    color: var(--white) !important;
}

/* ── Columns — prevent overlap without fighting Streamlit's flex layout ── */
[data-testid="stHorizontalBlock"] {
    gap: 16px !important;
    align-items: flex-start !important;
}
[data-testid="column"] {
    min-width: 0;
    overflow: visible !important;
}

/* ── Metric cards ───────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--white);
    border: var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 12px 16px !important;
    margin-bottom: 4px;
    position: relative;
    z-index: 0;
}
[data-testid="stMetricLabel"] {
    font-family: 'Nunito', sans-serif !important;
    font-weight: 800 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #555 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Fredoka One', cursive !important;
    font-size: 1.5rem !important;
    color: var(--ink) !important;
}

/* ── Buttons ────────────────────────────────────────────────────────────── */
.stButton > button {
    font-family: 'Fredoka One', cursive !important;
    font-size: 0.95rem !important;
    background-color: var(--yellow) !important;
    color: var(--ink) !important;
    border: var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
    transition: transform 0.1s, box-shadow 0.1s !important;
    padding: 6px 16px !important;
    position: relative;
    z-index: 1;
    margin-bottom: 2px;
}
.stButton > button:hover {
    transform: translate(-2px, -2px) !important;
    box-shadow: 5px 5px 0px var(--ink) !important;
    background-color: var(--orange) !important;
    color: var(--white) !important;
}
.stButton > button:active {
    transform: translate(2px, 2px) !important;
    box-shadow: 1px 1px 0px var(--ink) !important;
}
.stButton > button[kind="primary"] {
    background-color: var(--red) !important;
    color: var(--white) !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #c0392b !important;
}
.stButton > button:disabled {
    opacity: 0.45 !important;
    box-shadow: none !important;
    transform: none !important;
}

/* ── Link buttons ───────────────────────────────────────────────────────── */
.stLinkButton > a {
    font-family: 'Fredoka One', cursive !important;
    background-color: var(--blue) !important;
    color: var(--white) !important;
    border: var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
    text-decoration: none !important;
    transition: transform 0.1s, box-shadow 0.1s !important;
    padding: 6px 16px !important;
    display: inline-block;
}
.stLinkButton > a:hover {
    transform: translate(-2px, -2px) !important;
    box-shadow: 5px 5px 0px var(--ink) !important;
    background-color: var(--purple) !important;
}

/* ── Input & select ─────────────────────────────────────────────────────── */
.stTextInput > div > div > input {
    border: var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
    background: var(--white) !important;
    font-family: 'Nunito', sans-serif !important;
    font-weight: 700 !important;
    padding: 8px 12px !important;
}
.stTextInput > div > div > input:focus {
    box-shadow: 5px 5px 0px var(--ink) !important;
    outline: none !important;
}
.stSelectbox > div > div {
    border: var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--white) !important;
    font-family: 'Nunito', sans-serif !important;
    font-weight: 700 !important;
}

/* ── Chat input ─────────────────────────────────────────────────────────── */
[data-testid="stChatInput"] > div {
    border: var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
    background: var(--white) !important;
}

/* ── Chat messages ──────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: var(--white) !important;
    border: var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
    margin-bottom: 14px !important;
    padding: 12px 16px !important;
    position: relative;
    z-index: 0;
}

/* ── Alert boxes ────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border: var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
    font-family: 'Nunito', sans-serif !important;
    font-weight: 700 !important;
    margin-bottom: 8px !important;
    position: relative;
    z-index: 0;
}

/* ── Expanders ──────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
    background: var(--white) !important;
    margin-bottom: 10px !important;
    position: relative;
    z-index: 0;
}
[data-testid="stExpander"] summary {
    font-family: 'Fredoka One', cursive !important;
    font-size: 1rem !important;
}

/* ── Tabs ───────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: transparent !important;
    flex-wrap: wrap;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Fredoka One', cursive !important;
    font-size: 0.9rem !important;
    background: var(--white) !important;
    border: var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: 2px 2px 0px var(--ink) !important;
    color: var(--ink) !important;
    padding: 6px 14px !important;
}
.stTabs [aria-selected="true"] {
    background: var(--orange) !important;
    color: var(--white) !important;
    box-shadow: 3px 3px 0px var(--ink) !important;
}

/* ── Dataframe ──────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
    overflow: hidden;
    margin-bottom: 8px;
}

/* ── Dividers ───────────────────────────────────────────────────────────── */
hr {
    border: 2px dashed #D4A574 !important;
    margin: 24px 0 !important;
}

/* ── Slider ─────────────────────────────────────────────────────────────── */
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
    background: var(--orange) !important;
    border: 2px solid var(--ink) !important;
}

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb {
    background: var(--orange);
    border: 2px solid var(--ink);
    border-radius: 6px;
}

/* ── Block container spacing ────────────────────────────────────────────── */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
}

/* ── Prevent shadow overflow clipping ───────────────────────────────────── */
.element-container {
    overflow: visible !important;
    margin-bottom: 8px !important;
}
[data-testid="stVerticalBlock"] {
    overflow: visible !important;
    gap: 8px;
}
/* Ensure expander doesn't bleed across columns */
[data-testid="stExpander"] {
    width: 100% !important;
}
</style>
"""
