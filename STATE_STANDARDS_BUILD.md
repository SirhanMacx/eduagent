# Build: 50-State Standards System

Add a comprehensive US state standards system to EDUagent so any teacher in any state gets output automatically aligned to their state's framework.

## File: eduagent/state_standards.py (new)

Build a complete data structure covering all 50 states + DC:

```python
STATE_STANDARDS_CONFIG = {
    "AL": {"name": "Alabama", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "AK": {"name": "Alaska", "math": "AK_MATH", "ela": "AK_ELA", "science": "AK_SCIENCE", "social_studies": "C3"},
    "AZ": {"name": "Arizona", "math": "CCSS_AZ", "ela": "CCSS_AZ", "science": "NGSS", "social_studies": "C3"},
    "AR": {"name": "Arkansas", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "CA": {"name": "California", "math": "CCSS_CA", "ela": "CCSS_CA", "science": "NGSS", "social_studies": "CA_HSS"},
    "CO": {"name": "Colorado", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "CT": {"name": "Connecticut", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "DE": {"name": "Delaware", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "DC": {"name": "District of Columbia", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "FL": {"name": "Florida", "math": "FL_BEST", "ela": "FL_BEST", "science": "FL_NGSSS", "social_studies": "FL_SS"},
    "GA": {"name": "Georgia", "math": "GA_MGSE", "ela": "GA_ELA", "science": "GA_SCIENCE", "social_studies": "C3"},
    "HI": {"name": "Hawaii", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "ID": {"name": "Idaho", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "IL": {"name": "Illinois", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "IN": {"name": "Indiana", "math": "IN_ALS", "ela": "IN_ALS", "science": "IN_ALS", "social_studies": "C3"},
    "IA": {"name": "Iowa", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "KS": {"name": "Kansas", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "KY": {"name": "Kentucky", "math": "KY_ACAS", "ela": "KY_ACAS", "science": "NGSS", "social_studies": "KY_SS"},
    "LA": {"name": "Louisiana", "math": "CCSS_LA", "ela": "CCSS_LA", "science": "NGSS", "social_studies": "C3"},
    "ME": {"name": "Maine", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "MD": {"name": "Maryland", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "MA": {"name": "Massachusetts", "math": "MA_CCSS", "ela": "MA_CCSS", "science": "MA_SCIENCE", "social_studies": "MA_HSS"},
    "MI": {"name": "Michigan", "math": "CCSS", "ela": "CCSS", "science": "MI_SCIENCE", "social_studies": "C3"},
    "MN": {"name": "Minnesota", "math": "MN_MATH", "ela": "CCSS", "science": "NGSS", "social_studies": "MN_SS"},
    "MS": {"name": "Mississippi", "math": "CCSS_MS", "ela": "CCSS_MS", "science": "NGSS", "social_studies": "C3"},
    "MO": {"name": "Missouri", "math": "MO_LEARN", "ela": "MO_LEARN", "science": "MO_SCIENCE", "social_studies": "C3"},
    "MT": {"name": "Montana", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "NE": {"name": "Nebraska", "math": "NE_MATH", "ela": "NE_ELA", "science": "NGSS", "social_studies": "NE_SS"},
    "NV": {"name": "Nevada", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "NH": {"name": "New Hampshire", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "NJ": {"name": "New Jersey", "math": "CCSS_NJ", "ela": "CCSS_NJ", "science": "NGSS", "social_studies": "NJ_SS"},
    "NM": {"name": "New Mexico", "math": "CCSS_NM", "ela": "CCSS_NM", "science": "NGSS", "social_studies": "C3"},
    "NY": {"name": "New York", "math": "NY_NGLS", "ela": "NY_NGLS", "science": "NGSS", "social_studies": "NY_SS"},
    "NC": {"name": "North Carolina", "math": "CCSS_NC", "ela": "CCSS_NC", "science": "NC_SCIENCE", "social_studies": "C3"},
    "ND": {"name": "North Dakota", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "OH": {"name": "Ohio", "math": "OH_MATH", "ela": "OH_ELA", "science": "OH_SCIENCE", "social_studies": "OH_SS"},
    "OK": {"name": "Oklahoma", "math": "OK_MATH", "ela": "OK_ELA", "science": "OK_SCIENCE", "social_studies": "OK_SS"},
    "OR": {"name": "Oregon", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "PA": {"name": "Pennsylvania", "math": "PA_CCSS", "ela": "PA_CCSS", "science": "PA_SCIENCE", "social_studies": "PA_SS"},
    "RI": {"name": "Rhode Island", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "SC": {"name": "South Carolina", "math": "SC_CCRS", "ela": "SC_CCRS", "science": "SC_SCIENCE", "social_studies": "SC_SS"},
    "SD": {"name": "South Dakota", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "TN": {"name": "Tennessee", "math": "TN_MATH", "ela": "TN_ELA", "science": "TN_SCIENCE", "social_studies": "C3"},
    "TX": {"name": "Texas", "math": "TX_TEKS", "ela": "TX_TEKS_ELA", "science": "TX_TEKS_SCI", "social_studies": "TX_TEKS_SS"},
    "UT": {"name": "Utah", "math": "CCSS_UT", "ela": "CCSS_UT", "science": "NGSS", "social_studies": "UT_SS"},
    "VT": {"name": "Vermont", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "VA": {"name": "Virginia", "math": "VA_SOL", "ela": "VA_SOL", "science": "VA_SOL_SCI", "social_studies": "VA_SOL_SS"},
    "WA": {"name": "Washington", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
    "WV": {"name": "West Virginia", "math": "WV_CSO", "ela": "WV_CSO", "science": "NGSS", "social_studies": "C3"},
    "WI": {"name": "Wisconsin", "math": "CCSS", "ela": "CCSS", "science": "WI_SCIENCE", "social_studies": "WI_SS"},
    "WY": {"name": "Wyoming", "math": "CCSS", "ela": "CCSS", "science": "NGSS", "social_studies": "C3"},
}

FRAMEWORK_DESCRIPTIONS = {
    "CCSS": "Common Core State Standards",
    "NY_NGLS": "New York Next Generation Learning Standards",
    "NY_SS": "New York K-12 Social Studies Framework",
    "TX_TEKS": "Texas Essential Knowledge and Skills (TEKS)",
    "TX_TEKS_ELA": "Texas TEKS - English Language Arts",
    "TX_TEKS_SCI": "Texas TEKS - Science",
    "TX_TEKS_SS": "Texas TEKS - Social Studies",
    "VA_SOL": "Virginia Standards of Learning (SOL)",
    "VA_SOL_SCI": "Virginia SOL - Science",
    "VA_SOL_SS": "Virginia SOL - Social Studies",
    "NGSS": "Next Generation Science Standards",
    "C3": "C3 Framework for Social Studies",
    "FL_BEST": "Florida BEST Standards",
    "FL_NGSSS": "Florida Next Generation Sunshine State Standards (Science)",
    "FL_SS": "Florida Social Studies Standards",
    "IN_ALS": "Indiana Academic Standards",
    "MA_CCSS": "Massachusetts Curriculum Frameworks (CCSS-aligned)",
    "MA_SCIENCE": "Massachusetts Science and Technology/Engineering Standards",
    "MA_HSS": "Massachusetts History and Social Science Curriculum Framework",
    "CA_HSS": "California History-Social Science Framework",
    "CCSS_CA": "California Common Core State Standards",
    "OH_SS": "Ohio Social Studies Learning Standards",
    "PA_SS": "Pennsylvania Academic Standards - Social Studies",
    "NJ_SS": "New Jersey Student Learning Standards - Social Studies",
}
```

Then implement these functions:

```python
def get_state_framework(state: str, subject: str) -> str:
    """Return framework code for a state+subject combination."""

def get_framework_description(framework_code: str) -> str:
    """Return human-readable framework name."""

def list_states() -> list[dict]:
    """Return sorted list of {"abbreviation": ..., "name": ...} for all states."""

def get_standards_context_for_prompt(state: str, subjects: list[str], grades: list[str]) -> str:
    """
    Generate a standards context string to inject into LLM prompts.
    Example output:
    'Standards Framework: New York Next Generation Learning Standards (NY_NGLS)
     Subject: Social Studies - NY K-12 Social Studies Framework (NY_SS)
     Grades: 8, 9, 10
     When generating content, align all objectives, assessments, and materials
     to these specific standards. Reference standard codes where applicable.'
    """
```

## Update: eduagent/models.py

Add `state: str = ""` to TeacherProfile (already has this, just verify).
Add `get_standards_context()` method to TeacherProfile that calls state_standards.py.

## Update: eduagent/api/templates/settings.html (or wherever config UI is)

Add to the teacher profile section:
- State dropdown: all 50 states + DC in alphabetical order by name
- When state selected, show framework info: "You'll use [Framework Name] for [Subject]"
- Multi-select for subjects: Math, ELA, Science, Social Studies, History, Economics, AP courses, etc.
- Grade level checkboxes: K 1 2 3 4 5 6 7 8 9 10 11 12

## Tests: tests/test_state_standards.py

Write tests:
- test_all_states_present: assert len(STATE_STANDARDS_CONFIG) >= 51 (50 states + DC)
- test_ny_framework: assert get_state_framework("NY", "social_studies") == "NY_SS"  
- test_tx_uses_teks: assert "TEKS" in get_state_framework("TX", "math")
- test_va_uses_sol: assert "SOL" in get_state_framework("VA", "math")
- test_fl_uses_best: assert "BEST" in get_state_framework("FL", "math")
- test_list_states_count: assert len(list_states()) >= 51
- test_standards_context_contains_framework: verify output string contains framework name

## After building:

1. python -m pytest tests/ -q (all must pass)
2. python -m ruff check eduagent/ --fix (clean)
3. git add -A && git commit -m "feat: 50-state standards config — auto-tailors to any US teacher by state"
4. git push origin main
5. openclaw system event --text "Done: 50-state standards — EDUagent now serves teachers in all 50 states" --mode now
