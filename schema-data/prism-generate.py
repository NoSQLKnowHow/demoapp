"""
============================================================================
PRISM: LLM Content Generator (One-Time)
============================================================================
Generates realistic maintenance logs and inspection reports using an LLM
and saves them as JSON files in the data/ directory.

This script is intended to be run ONCE (or whenever you want to regenerate
the content). The output files are then loaded by prism-seed.py on every
database setup, avoiding repeated LLM calls and costs.

Supported LLM providers (set LLM_PROVIDER in .env):
    - oci       : OCI Generative AI
    - claude    : Anthropic Claude API
    - openai    : OpenAI API

Usage:
    python prism-generate.py

Output:
    data/maintenance_logs.json
    data/inspection_reports.json

Requires:
    - python-dotenv
    - Provider-specific SDK (oci, anthropic, or openai)
    - Environment variables (see .env)
============================================================================
"""

import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

# LLM Provider: "oci", "claude", or "openai"
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "oci").lower().strip()

# OCI Generative AI
OCI_COMPARTMENT_ID = os.environ.get("OCI_COMPARTMENT_ID")
OCI_GENAI_ENDPOINT = os.environ.get("OCI_GENAI_ENDPOINT", "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com")
OCI_GENAI_MODEL = os.environ.get("OCI_GENAI_MODEL", "meta.llama-3.2-90b-vision-instruct")

# Anthropic Claude
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

# Output directory
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Target counts
TARGET_MAINTENANCE_LOGS = 300
TARGET_INSPECTION_REPORTS = 60

# ============================================================================
# Asset Data (mirrors prism-seed.py so we know what to generate content for)
# ============================================================================

DISTRICTS = [
    {"name": "Harbor District", "classification": "industrial"},
    {"name": "Meridian Heights", "classification": "residential"},
    {"name": "Ironworks Quarter", "classification": "industrial"},
    {"name": "Central Commons", "classification": "mixed-use"},
    {"name": "Greenfield Park", "classification": "residential"},
    {"name": "Riverside Corridor", "classification": "commercial"},
    {"name": "Northgate Industrial", "classification": "industrial"},
]

# (name, asset_type, district_index, specifications)
ASSETS = [
    ("Harbor Bridge", "bridge", 0, {"spanLength_m": 485, "loadCapacity_t": 5000, "laneCount": 4, "material": "steel-concrete composite", "deckWidth_m": 22}),
    ("Meridian Overpass", "bridge", 1, {"spanLength_m": 210, "loadCapacity_t": 3500, "laneCount": 2, "material": "pre-stressed concrete", "clearance_m": 5.2}),
    ("Riverside Pedestrian Bridge", "bridge", 5, {"spanLength_m": 165, "loadCapacity_t": 500, "laneCount": 0, "material": "steel cable-stayed", "deckWidth_m": 4.5}),
    ("Substation Gamma", "substation", 2, {"voltageRating_kv": 132, "transformerCount": 3, "peakCapacity_mw": 250, "coolingType": "ONAN/ONAF"}),
    ("Substation Delta", "substation", 6, {"voltageRating_kv": 66, "transformerCount": 2, "peakCapacity_mw": 120, "coolingType": "ONAF"}),
    ("Substation Epsilon", "substation", 3, {"voltageRating_kv": 33, "transformerCount": 4, "peakCapacity_mw": 80, "coolingType": "ONAN"}),
    ("Pipeline North-7", "pipeline", 6, {"diameter_mm": 600, "material": "ductile iron", "pressureRating_kpa": 1200, "length_km": 12.4}),
    ("Pipeline South-3", "pipeline", 4, {"diameter_mm": 400, "material": "HDPE", "pressureRating_kpa": 800, "length_km": 8.1}),
    ("Harbor Outfall Main", "pipeline", 0, {"diameter_mm": 900, "material": "reinforced concrete", "pressureRating_kpa": 400, "length_km": 3.2}),
    ("Central Gas Distribution", "pipeline", 3, {"diameter_mm": 200, "material": "steel", "pressureRating_kpa": 700, "length_km": 6.8}),
    ("Harbor Bridge Sensor Array A", "sensor", 0, {"sensorTypes": ["accelerometer", "strain gauge", "thermocouple"], "sampleRate_hz": 100, "channels": 24}),
    ("Harbor Bridge Sensor Array B", "sensor", 0, {"sensorTypes": ["accelerometer", "strain gauge", "displacement"], "sampleRate_hz": 100, "channels": 18}),
    ("Flood Gauge Station R1", "sensor", 5, {"sensorTypes": ["ultrasonic level", "doppler flow", "rain gauge"], "sampleRate_hz": 1, "channels": 6}),
    ("Air Quality Monitor NI-01", "sensor", 6, {"sensorTypes": ["PM2.5", "PM10", "NO2", "SO2", "O3", "CO"], "sampleRate_hz": 0.1, "channels": 8}),
    ("Seismic Station CC-01", "sensor", 3, {"sensorTypes": ["triaxial accelerometer"], "sampleRate_hz": 200, "channels": 3}),
    ("Comms Tower Alpha", "communication_tower", 1, {"height_m": 65, "antennaCount": 12, "coverageRadius_km": 8}),
    ("Comms Tower Beta", "communication_tower", 6, {"height_m": 45, "antennaCount": 8, "coverageRadius_km": 5}),
    ("Harbor Relay Station", "communication_tower", 0, {"height_m": 35, "antennaCount": 6, "coverageRadius_km": 15}),
    ("Ironworks Water Treatment Plant", "treatment_plant", 2, {"capacity_mld": 120, "treatmentLevel": "tertiary", "processType": "activated sludge with UV disinfection"}),
    ("Riverside Pump Station", "pump_station", 5, {"pumpCount": 4, "totalCapacity_ls": 2500, "backupPower": "diesel generator"}),
    ("Greenfield Booster Station", "pump_station", 4, {"pumpCount": 3, "totalCapacity_ls": 800, "backupPower": "diesel generator"}),
    ("Harbor Seawall Section A", "retaining_wall", 0, {"length_m": 450, "height_m": 6.5, "material": "reinforced concrete with steel sheet piling"}),
    ("Meridian Cut Retaining Wall", "retaining_wall", 1, {"length_m": 280, "height_m": 8.0, "material": "mechanically stabilized earth"}),
    ("Northern Reservoir", "reservoir", 6, {"capacity_ml": 85, "depth_m": 12, "coverType": "floating cover"}),
    ("Greenfield Solar Array", "solar_installation", 4, {"peakCapacity_kw": 2400, "panelCount": 6000, "inverterType": "string"}),
    ("Northgate Freight Terminal", "rail_terminal", 6, {"trackCount": 6, "maxTrainLength_m": 800, "craneCapacity_t": 50}),
]

INSPECTABLE_TYPES = (
    "bridge", "substation", "pipeline", "treatment_plant",
    "pump_station", "retaining_wall", "communication_tower",
    "solar_installation", "reservoir"
)

# ============================================================================
# LLM Prompts
# ============================================================================

MAINTENANCE_LOG_SYSTEM_PROMPT = """You are a technical writer generating realistic maintenance log entries for a smart city infrastructure management system called CityPulse. Each log entry is a narrative description of maintenance work performed, an incident observed, or a routine inspection finding.

Guidelines:
- Write in the voice of a field technician or maintenance engineer documenting their work.
- Include specific technical details: measurements, part numbers, conditions observed, actions taken.
- Vary the tone: some entries are routine ("replaced filter, all nominal"), some are concerning ("discovered hairline crack in weld joint"), some are urgent ("emergency callout for water main break").
- Reference realistic infrastructure components: valves, sensors, transformers, pumps, joints, bearings, coatings, cathodic protection, etc.
- Include environmental context where relevant: weather conditions, time of day, access difficulties.
- Each narrative should be 3-8 sentences long.
- Do NOT include any headers, bullet points, or formatting. Write as a single paragraph of plain text."""

MAINTENANCE_LOG_USER_PROMPT = """Generate {count} unique maintenance log narratives for the following infrastructure asset:

Asset Name: {asset_name}
Asset Type: {asset_type}
District: {district_name}
Specifications: {specifications}

Generate a mix of severities:
- ~60% routine (scheduled maintenance, normal readings, minor adjustments)
- ~25% warning (early signs of degradation, recommended follow-up, approaching thresholds)
- ~15% critical (failures, emergency repairs, safety concerns)

Return your response as a JSON array of objects, each with:
- "severity": one of "routine", "warning", "critical"
- "narrative": the log entry text (plain paragraph, no formatting)
- "days_ago": a random number between 1 and 730 representing when this log was written

Return ONLY the JSON array, no other text."""

INSPECTION_REPORT_SYSTEM_PROMPT = """You are a senior infrastructure inspector generating formal inspection reports for a smart city infrastructure management system called CityPulse. Reports include a summary and detailed findings.

Guidelines:
- Write in formal, professional language appropriate for engineering inspection reports.
- The summary should be 2-4 sentences providing an overall assessment.
- Each finding should be specific, actionable, and reference observable conditions.
- Include measurements, locations on the structure, and comparisons to standards where appropriate.
- Recommendations should be concrete: "replace", "monitor quarterly", "schedule repair within 30 days", etc.
- Grades: A (excellent), B (good, minor issues), C (fair, maintenance needed), D (poor, significant issues), F (critical, immediate action)."""

INSPECTION_REPORT_USER_PROMPT = """Generate {count} unique inspection reports for the following infrastructure asset:

Asset Name: {asset_name}
Asset Type: {asset_type}
District: {district_name}
Specifications: {specifications}

Generate a mix of grades:
- ~30% grade A or B
- ~50% grade C
- ~20% grade D or F

For each report, generate between 2 and 5 findings.

Return your response as a JSON array of objects, each with:
- "inspector": a realistic full name
- "overall_grade": one of "A", "B", "C", "D", "F"
- "summary": the report summary (2-4 sentences, plain text)
- "days_ago": a random number between 1 and 1095 representing when this inspection was performed
- "findings": an array of objects, each with:
  - "category": a category like "structural", "electrical", "mechanical", "corrosion", "safety", "drainage", "coating"
  - "severity": one of "low", "medium", "high", "critical"
  - "description": the finding description (1-3 sentences)
  - "recommendation": the recommended action (1-2 sentences)

Return ONLY the JSON array, no other text."""


# ============================================================================
# LLM Provider Abstraction
# ============================================================================

def init_llm_client():
    """
    Initialize and return the LLM client based on the configured provider.
    Returns a callable: generate(system_prompt, user_prompt) -> str
    """
    provider = LLM_PROVIDER

    if provider == "oci":
        return _init_oci_client()
    elif provider == "claude":
        return _init_claude_client()
    elif provider == "openai":
        return _init_openai_client()
    else:
        print(f"ERROR: Unknown LLM_PROVIDER '{provider}'. Must be 'oci', 'claude', or 'openai'.")
        sys.exit(1)


def _init_oci_client():
    """Initialize OCI Generative AI and return a generate function."""
    import oci

    config = oci.config.from_file()
    client = oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=OCI_GENAI_ENDPOINT
    )

    def generate(system_prompt, user_prompt):
        chat_request = oci.generative_ai_inference.models.ChatDetails(
            compartment_id=OCI_COMPARTMENT_ID,
            serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
                model_id=OCI_GENAI_MODEL
            ),
            chat_request=oci.generative_ai_inference.models.GenericChatRequest(
                messages=[
                    oci.generative_ai_inference.models.SystemMessage(content=[
                        oci.generative_ai_inference.models.TextContent(text=system_prompt)
                    ]),
                    oci.generative_ai_inference.models.UserMessage(content=[
                        oci.generative_ai_inference.models.TextContent(text=user_prompt)
                    ])
                ],
                max_completion_tokens=4096,
                temperature=1,
                top_p=0.9
            )
        )
        response = client.chat(chat_request)
        return response.data.chat_response.choices[0].message.content[0].text

    print(f"  Provider: OCI Generative AI")
    print(f"  Model:    {OCI_GENAI_MODEL}")
    return generate


def _init_claude_client():
    """Initialize Anthropic Claude and return a generate function."""
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def generate(system_prompt, user_prompt):
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_completion_tokens=4096,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return message.content[0].text

    print(f"  Provider: Anthropic Claude")
    print(f"  Model:    {ANTHROPIC_MODEL}")
    return generate


def _init_openai_client():
    """Initialize OpenAI and return a generate function."""
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)

    def generate(system_prompt, user_prompt):
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=4096,
            temperature=1,
        )
        return response.choices[0].message.content

    print(f"  Provider: OpenAI")
    print(f"  Model:    {OPENAI_MODEL}")
    return generate


def parse_json_response(response_text):
    """Extract and parse JSON from an LLM response, handling markdown code blocks."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


# ============================================================================
# Content Generation
# ============================================================================

def generate_maintenance_logs(generate_fn):
    """Generate maintenance log content for all assets. Returns a list of log dicts."""
    print(f"\nGenerating ~{TARGET_MAINTENANCE_LOGS} maintenance logs...")

    # Weight distribution
    weight_map = {
        "bridge": 5, "substation": 4, "pipeline": 4, "treatment_plant": 4,
        "pump_station": 3, "sensor": 2, "communication_tower": 2,
        "retaining_wall": 2, "reservoir": 2, "solar_installation": 2,
        "rail_terminal": 2
    }
    asset_weights = [(a, weight_map.get(a[1], 1)) for a in ASSETS]
    total_weight = sum(w for _, w in asset_weights)

    all_logs = []

    for asset, weight in asset_weights:
        asset_name, asset_type, district_idx, specs = asset
        district_name = DISTRICTS[district_idx]["name"]
        count = max(3, round(TARGET_MAINTENANCE_LOGS * weight / total_weight))

        print(f"  Generating {count} logs for {asset_name}...")

        prompt = MAINTENANCE_LOG_USER_PROMPT.format(
            count=count,
            asset_name=asset_name,
            asset_type=asset_type,
            district_name=district_name,
            specifications=json.dumps(specs, indent=2)
        )

        try:
            response = generate_fn(MAINTENANCE_LOG_SYSTEM_PROMPT, prompt)
            logs = parse_json_response(response)

            for log in logs:
                all_logs.append({
                    "asset_name": asset_name,
                    "severity": log["severity"],
                    "narrative": log["narrative"],
                    "days_ago": log.get("days_ago", 1),
                })

            print(f"    Got {len(logs)} logs.")

        except Exception as e:
            print(f"    ERROR: {e}")
            continue

    print(f"\n  Total maintenance logs generated: {len(all_logs)}")
    return all_logs


def generate_inspection_reports(generate_fn):
    """Generate inspection report content for inspectable assets. Returns a list of report dicts."""
    print(f"\nGenerating ~{TARGET_INSPECTION_REPORTS} inspection reports...")

    inspectable = [a for a in ASSETS if a[1] in INSPECTABLE_TYPES]
    reports_per_asset = max(2, TARGET_INSPECTION_REPORTS // len(inspectable))

    all_reports = []

    for asset in inspectable:
        asset_name, asset_type, district_idx, specs = asset
        district_name = DISTRICTS[district_idx]["name"]
        count = reports_per_asset

        print(f"  Generating {count} reports for {asset_name}...")

        prompt = INSPECTION_REPORT_USER_PROMPT.format(
            count=count,
            asset_name=asset_name,
            asset_type=asset_type,
            district_name=district_name,
            specifications=json.dumps(specs, indent=2)
        )

        try:
            response = generate_fn(INSPECTION_REPORT_SYSTEM_PROMPT, prompt)
            reports = parse_json_response(response)

            for report in reports:
                all_reports.append({
                    "asset_name": asset_name,
                    "inspector": report["inspector"],
                    "overall_grade": report["overall_grade"],
                    "summary": report["summary"],
                    "days_ago": report.get("days_ago", 1),
                    "findings": report.get("findings", []),
                })

            print(f"    Got {len(reports)} reports.")

        except Exception as e:
            print(f"    ERROR: {e}")
            continue

    print(f"\n  Total inspection reports generated: {len(all_reports)}")
    total_findings = sum(len(r["findings"]) for r in all_reports)
    print(f"  Total inspection findings generated: {total_findings}")
    return all_reports


# ============================================================================
# Main
# ============================================================================

def validate_config():
    """Validate that required configuration is present for the selected provider."""
    missing = []

    if LLM_PROVIDER == "oci":
        if not OCI_COMPARTMENT_ID:
            missing.append("OCI_COMPARTMENT_ID")
    elif LLM_PROVIDER == "claude":
        if not ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
    elif LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
    else:
        print(f"ERROR: Unknown LLM_PROVIDER '{LLM_PROVIDER}'. Must be 'oci', 'claude', or 'openai'.")
        sys.exit(1)

    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
        print(f"       (LLM_PROVIDER is set to '{LLM_PROVIDER}')")
        sys.exit(1)


def main():
    print("=" * 72)
    print("  PRISM: LLM Content Generator")
    print("=" * 72)
    print()
    print(f"  LLM Provider: {LLM_PROVIDER}")
    print(f"  Output dir:   {DATA_DIR}")
    print()

    validate_config()

    os.makedirs(DATA_DIR, exist_ok=True)

    print("Initializing LLM client...")
    generate_fn = init_llm_client()

    # Generate maintenance logs
    logs = generate_maintenance_logs(generate_fn)
    logs_path = os.path.join(DATA_DIR, "maintenance_logs.json")
    with open(logs_path, "w") as f:
        json.dump(logs, f, indent=2)
    print(f"\n  Saved {len(logs)} logs to {logs_path}")

    # Generate inspection reports
    reports = generate_inspection_reports(generate_fn)
    reports_path = os.path.join(DATA_DIR, "inspection_reports.json")
    with open(reports_path, "w") as f:
        json.dump(reports, f, indent=2)
    print(f"\n  Saved {len(reports)} reports to {reports_path}")

    print()
    print("=" * 72)
    print("  Content generation complete.")
    print("  Files saved to data/ directory.")
    print("  Next step: Run python prism-seed.py to load into database.")
    print("=" * 72)


if __name__ == "__main__":
    main()
