"""
============================================================================
PRISM: Seed Data Generator
============================================================================
Populates the Prism database with CityPulse sample data.

Structural data (districts, assets, connections, procedures) is defined
inline. Narrative content (maintenance logs, inspection reports, findings)
is generated using an LLM for realistic, semantically rich text.

Usage:
    python prism-seed.py

Requires:
    - python-oracledb
    - oci (OCI SDK for Generative AI)
    - Environment variables (see .env.example)
============================================================================
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta

import oracledb
import oci

# ============================================================================
# Configuration
# ============================================================================

ORACLE_DSN = os.environ.get("ORACLE_DSN")
ORACLE_USER = os.environ.get("ORACLE_USER", "prism")
ORACLE_PASSWORD = os.environ.get("ORACLE_PASSWORD")
ORACLE_WALLET_DIR = os.environ.get("ORACLE_WALLET_DIR")

OCI_COMPARTMENT_ID = os.environ.get("OCI_COMPARTMENT_ID")
OCI_GENAI_ENDPOINT = os.environ.get("OCI_GENAI_ENDPOINT", "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com")
OCI_GENAI_MODEL = os.environ.get("OCI_GENAI_MODEL", "meta.llama-3.2-90b-vision-instruct")

# Target counts
TARGET_MAINTENANCE_LOGS = 300
TARGET_INSPECTION_REPORTS = 60
FINDINGS_PER_REPORT_RANGE = (2, 5)

# ============================================================================
# Structural Data Definitions
# ============================================================================

DISTRICTS = [
    {
        "name": "Harbor District",
        "classification": "industrial",
        "population": 12400,
        "area_sq_km": 8.7,
        "description": "Waterfront industrial zone housing the city's primary port facilities, maritime infrastructure, and coastal monitoring systems."
    },
    {
        "name": "Meridian Heights",
        "classification": "residential",
        "population": 45200,
        "area_sq_km": 12.3,
        "description": "Primary residential district with mixed-density housing, neighborhood parks, and distributed utility infrastructure."
    },
    {
        "name": "Ironworks Quarter",
        "classification": "industrial",
        "population": 8900,
        "area_sq_km": 6.1,
        "description": "Heavy industrial zone containing power generation, water treatment, and waste management facilities."
    },
    {
        "name": "Central Commons",
        "classification": "mixed-use",
        "population": 31500,
        "area_sq_km": 4.2,
        "description": "City center with commercial towers, civic buildings, transit hubs, and high-density residential blocks."
    },
    {
        "name": "Greenfield Park",
        "classification": "residential",
        "population": 28700,
        "area_sq_km": 15.8,
        "description": "Suburban residential district with extensive green spaces, underground utility corridors, and distributed solar installations."
    },
    {
        "name": "Riverside Corridor",
        "classification": "commercial",
        "population": 19300,
        "area_sq_km": 5.4,
        "description": "Commercial and light industrial strip along the river, featuring warehousing, logistics facilities, and flood management infrastructure."
    },
    {
        "name": "Northgate Industrial",
        "classification": "industrial",
        "population": 5600,
        "area_sq_km": 9.9,
        "description": "Northern industrial park with chemical processing plants, rail freight terminals, and high-voltage power distribution."
    }
]

# Asset definitions: (name, asset_type, district_index, status, commissioned_date, description, specifications)
INFRASTRUCTURE_ASSETS = [
    # Bridges
    ("Harbor Bridge", "bridge", 0, "active", "1987-03-15",
     "Primary vehicular and pedestrian bridge spanning the harbor inlet. Four-lane capacity with dedicated pedestrian walkways.",
     {"spanLength_m": 485, "loadCapacity_t": 5000, "laneCount": 4, "material": "steel-concrete composite", "deckWidth_m": 22}),
    ("Meridian Overpass", "bridge", 1, "active", "2003-08-22",
     "Grade-separated highway overpass connecting Meridian Heights to Central Commons.",
     {"spanLength_m": 210, "loadCapacity_t": 3500, "laneCount": 2, "material": "pre-stressed concrete", "clearance_m": 5.2}),
    ("Riverside Pedestrian Bridge", "bridge", 5, "active", "2015-06-10",
     "Cable-stayed pedestrian and cyclist bridge crossing the river at Riverside Corridor.",
     {"spanLength_m": 165, "loadCapacity_t": 500, "laneCount": 0, "material": "steel cable-stayed", "deckWidth_m": 4.5}),

    # Substations
    ("Substation Gamma", "substation", 2, "active", "1995-11-01",
     "Primary high-voltage substation serving Ironworks Quarter and portions of Central Commons.",
     {"voltageRating_kv": 132, "transformerCount": 3, "peakCapacity_mw": 250, "coolingType": "ONAN/ONAF"}),
    ("Substation Delta", "substation", 6, "active", "2001-04-18",
     "Distribution substation for Northgate Industrial, handling heavy industrial loads.",
     {"voltageRating_kv": 66, "transformerCount": 2, "peakCapacity_mw": 120, "coolingType": "ONAF"}),
    ("Substation Epsilon", "substation", 3, "active", "2010-09-30",
     "Urban distribution substation embedded within Central Commons, serving commercial and residential loads.",
     {"voltageRating_kv": 33, "transformerCount": 4, "peakCapacity_mw": 80, "coolingType": "ONAN"}),

    # Pipelines
    ("Pipeline North-7", "pipeline", 6, "active", "1998-02-14",
     "High-pressure water main running from the northern reservoir through Northgate Industrial to Ironworks Quarter.",
     {"diameter_mm": 600, "material": "ductile iron", "pressureRating_kpa": 1200, "length_km": 12.4}),
    ("Pipeline South-3", "pipeline", 4, "active", "2005-07-20",
     "Medium-pressure distribution main serving Greenfield Park residential areas.",
     {"diameter_mm": 400, "material": "HDPE", "pressureRating_kpa": 800, "length_km": 8.1}),
    ("Harbor Outfall Main", "pipeline", 0, "active", "1992-12-05",
     "Treated wastewater outfall pipeline extending from the Ironworks treatment plant to the harbor discharge point.",
     {"diameter_mm": 900, "material": "reinforced concrete", "pressureRating_kpa": 400, "length_km": 3.2}),
    ("Central Gas Distribution", "pipeline", 3, "active", "2008-03-11",
     "Natural gas distribution network serving Central Commons commercial and residential buildings.",
     {"diameter_mm": 200, "material": "steel", "pressureRating_kpa": 700, "length_km": 6.8}),

    # Sensors
    ("Harbor Bridge Sensor Array A", "sensor", 0, "active", "2018-05-14",
     "Structural health monitoring array on Harbor Bridge north pylon. Measures vibration, strain, and temperature.",
     {"sensorTypes": ["accelerometer", "strain gauge", "thermocouple"], "sampleRate_hz": 100, "channels": 24, "powerSource": "solar"}),
    ("Harbor Bridge Sensor Array B", "sensor", 0, "active", "2018-05-14",
     "Structural health monitoring array on Harbor Bridge south pylon and deck midspan.",
     {"sensorTypes": ["accelerometer", "strain gauge", "displacement"], "sampleRate_hz": 100, "channels": 18, "powerSource": "solar"}),
    ("Flood Gauge Station R1", "sensor", 5, "active", "2016-01-20",
     "River level and flow rate monitoring station at the upstream boundary of Riverside Corridor.",
     {"sensorTypes": ["ultrasonic level", "doppler flow", "rain gauge"], "sampleRate_hz": 1, "channels": 6, "powerSource": "mains with battery backup"}),
    ("Air Quality Monitor NI-01", "sensor", 6, "active", "2020-11-08",
     "Continuous air quality monitoring station at the perimeter of Northgate Industrial.",
     {"sensorTypes": ["PM2.5", "PM10", "NO2", "SO2", "O3", "CO"], "sampleRate_hz": 0.1, "channels": 8, "powerSource": "mains"}),
    ("Seismic Station CC-01", "sensor", 3, "active", "2019-07-15",
     "Strong-motion seismic sensor installed at the base of the Central Commons transit hub.",
     {"sensorTypes": ["triaxial accelerometer"], "sampleRate_hz": 200, "channels": 3, "powerSource": "mains with UPS"}),

    # Communication Towers
    ("Comms Tower Alpha", "communication_tower", 1, "active", "2012-08-30",
     "Primary communications tower for Meridian Heights, hosting cellular, emergency services, and IoT network antennas.",
     {"height_m": 65, "antennaCount": 12, "coverageRadius_km": 8, "backhaul": "fiber"}),
    ("Comms Tower Beta", "communication_tower", 6, "active", "2014-03-22",
     "Industrial communications tower serving Northgate Industrial with SCADA telemetry and process control networks.",
     {"height_m": 45, "antennaCount": 8, "coverageRadius_km": 5, "backhaul": "fiber + microwave"}),
    ("Harbor Relay Station", "communication_tower", 0, "active", "2017-09-01",
     "Maritime communications relay providing VHF, AIS, and port operations connectivity.",
     {"height_m": 35, "antennaCount": 6, "coverageRadius_km": 15, "backhaul": "fiber"}),

    # Water Treatment
    ("Ironworks Water Treatment Plant", "treatment_plant", 2, "active", "1990-06-15",
     "Municipal wastewater treatment facility processing flows from Central Commons, Meridian Heights, and Ironworks Quarter.",
     {"capacity_mld": 120, "treatmentLevel": "tertiary", "processType": "activated sludge with UV disinfection", "sludgeHandling": "anaerobic digestion"}),

    # Pump Stations
    ("Riverside Pump Station", "pump_station", 5, "active", "2007-10-12",
     "Stormwater pump station managing flood risk along the Riverside Corridor.",
     {"pumpCount": 4, "totalCapacity_ls": 2500, "backupPower": "diesel generator", "activationTrigger": "river level > 4.2m"}),
    ("Greenfield Booster Station", "pump_station", 4, "active", "2009-01-28",
     "Water pressure booster station maintaining supply pressure across the elevated sections of Greenfield Park.",
     {"pumpCount": 3, "totalCapacity_ls": 800, "backupPower": "diesel generator", "activationTrigger": "pressure < 350 kPa"}),

    # Retaining Walls
    ("Harbor Seawall Section A", "retaining_wall", 0, "active", "1985-04-20",
     "Concrete seawall protecting Harbor District infrastructure from tidal and storm surge events.",
     {"length_m": 450, "height_m": 6.5, "material": "reinforced concrete with steel sheet piling", "designWaveHeight_m": 3.5}),
    ("Meridian Cut Retaining Wall", "retaining_wall", 1, "active", "2003-08-22",
     "Reinforced earth retaining wall along the highway cut for Meridian Overpass approaches.",
     {"length_m": 280, "height_m": 8.0, "material": "mechanically stabilized earth", "designLoad_kpa": 20}),

    # Reservoirs
    ("Northern Reservoir", "reservoir", 6, "active", "1978-09-10",
     "Primary potable water storage reservoir supplying the northern half of the city via Pipeline North-7.",
     {"capacity_ml": 85, "depth_m": 12, "coverType": "floating cover", "treatmentOnsite": false}),

    # Solar Installations
    ("Greenfield Solar Array", "solar_installation", 4, "active", "2021-02-15",
     "Distributed rooftop and ground-mount solar installation across Greenfield Park public buildings.",
     {"peakCapacity_kw": 2400, "panelCount": 6000, "inverterType": "string", "annualYield_mwh": 3800}),

    # Rail
    ("Northgate Freight Terminal", "rail_terminal", 6, "active", "1982-11-30",
     "Rail freight terminal handling bulk materials for Northgate Industrial facilities.",
     {"trackCount": 6, "maxTrainLength_m": 800, "craneCapacity_t": 50, "annualThroughput_t": 2500000}),
]

# Connections: (from_asset_name, to_asset_name, connection_type, description)
ASSET_CONNECTIONS = [
    # Sensor monitoring
    ("Harbor Bridge Sensor Array A", "Harbor Bridge", "monitors", "North pylon structural health monitoring"),
    ("Harbor Bridge Sensor Array B", "Harbor Bridge", "monitors", "South pylon and deck midspan monitoring"),
    ("Flood Gauge Station R1", "Riverside Pump Station", "monitors", "River level triggers pump activation"),
    ("Air Quality Monitor NI-01", "Northgate Freight Terminal", "monitors", "Perimeter air quality monitoring for freight operations"),
    ("Seismic Station CC-01", "Meridian Overpass", "monitors", "Strong-motion monitoring for structural assessment"),

    # Power supply
    ("Substation Gamma", "Ironworks Water Treatment Plant", "powers", "Primary power supply for treatment plant operations"),
    ("Substation Gamma", "Harbor Bridge", "powers", "Bridge lighting and sensor power supply"),
    ("Substation Delta", "Northgate Freight Terminal", "powers", "Power supply for terminal cranes and facilities"),
    ("Substation Delta", "Comms Tower Beta", "powers", "Power supply for industrial communications"),
    ("Substation Epsilon", "Seismic Station CC-01", "powers", "Mains power with UPS backup"),
    ("Greenfield Solar Array", "Greenfield Booster Station", "powers", "Supplementary solar power for booster pumps"),

    # Water flow
    ("Northern Reservoir", "Pipeline North-7", "feeds", "Potable water supply from reservoir to distribution"),
    ("Pipeline North-7", "Ironworks Water Treatment Plant", "feeds", "Raw water supply to treatment facility"),
    ("Pipeline South-3", "Greenfield Booster Station", "feeds", "Distribution main to pressure booster"),
    ("Ironworks Water Treatment Plant", "Harbor Outfall Main", "feeds", "Treated effluent discharge to harbor"),
    ("Riverside Pump Station", "Flood Gauge Station R1", "connects-to", "Pump station intake at gauge location"),

    # Communications
    ("Comms Tower Alpha", "Comms Tower Beta", "connects-to", "Microwave backhaul link between towers"),
    ("Comms Tower Beta", "Harbor Relay Station", "connects-to", "Network relay for port operations"),
    ("Comms Tower Alpha", "Harbor Bridge Sensor Array A", "connects-to", "IoT data backhaul from bridge sensors"),
    ("Comms Tower Alpha", "Harbor Bridge Sensor Array B", "connects-to", "IoT data backhaul from bridge sensors"),
    ("Comms Tower Beta", "Air Quality Monitor NI-01", "connects-to", "Telemetry data backhaul"),

    # Physical adjacency / structural support
    ("Harbor Seawall Section A", "Harbor Bridge", "supports", "Seawall protects bridge abutment foundations"),
    ("Meridian Cut Retaining Wall", "Meridian Overpass", "supports", "Retaining wall stabilizes overpass approach embankments"),

    # Pipeline network connections
    ("Central Gas Distribution", "Substation Epsilon", "connects-to", "Gas supply for backup generation at substation"),
    ("Pipeline North-7", "Pipeline South-3", "connects-to", "Interconnection valve at distribution junction"),
]

OPERATIONAL_PROCEDURES = [
    {
        "procedureId": "SOP-HV-001",
        "title": "High Voltage Substation Inspection Protocol",
        "category": "electrical",
        "version": "3.2",
        "lastRevised": "2025-11-15",
        "estimatedDuration_min": 180,
        "requiredPersonnel": 3,
        "applicableAssetTypes": ["substation"],
        "safetyChecklist": [
            "Verify all circuits de-energized and locked out",
            "Confirm grounding cables attached at all work points",
            "PPE inspection: arc-flash suit (min CAT 3), insulated gloves (Class 2), face shield",
            "Verify rescue equipment staged and accessible",
            "Confirm communication with control room established"
        ],
        "equipment": [
            "thermal imaging camera",
            "insulation resistance tester (megger)",
            "partial discharge detector",
            "oil sampling kit",
            "digital multimeter (CAT IV rated)"
        ],
        "steps": [
            {"order": 1, "action": "Perform visual inspection of all transformer bushings and insulators", "notes": "Document any discoloration, cracks, or oil leaks with photos"},
            {"order": 2, "action": "Conduct thermal scan of all bus connections and switchgear", "notes": "Flag any connection with temperature differential exceeding 10°C above ambient"},
            {"order": 3, "action": "Perform insulation resistance testing on each transformer winding", "notes": "Minimum acceptable reading: 1 GΩ at 5 kV test voltage"},
            {"order": 4, "action": "Collect oil samples from each transformer for dissolved gas analysis", "notes": "Use clean syringes; label with transformer ID and date"},
            {"order": 5, "action": "Inspect cooling systems: fans, radiators, oil pumps", "notes": "Run each fan group for 2 minutes and verify operation"},
            {"order": 6, "action": "Check protection relay settings and test trip circuits", "notes": "Do not perform live trip tests without control room authorization"},
            {"order": 7, "action": "Inspect earthing system and measure ground resistance", "notes": "Maximum acceptable ground resistance: 1 Ω"}
        ],
        "escalation": {
            "contact": "Grid Operations Center",
            "phone": "555-0142",
            "conditions": ["Evidence of active arcing", "Transformer oil level below minimum mark", "Ground fault detected", "Protection relay failure"]
        }
    },
    {
        "procedureId": "SOP-BR-001",
        "title": "Bridge Structural Assessment Procedure",
        "category": "structural",
        "version": "2.1",
        "lastRevised": "2025-08-20",
        "estimatedDuration_min": 240,
        "requiredPersonnel": 4,
        "applicableAssetTypes": ["bridge"],
        "safetyChecklist": [
            "Traffic management plan approved and signage deployed",
            "Fall protection harnesses inspected and worn by all personnel",
            "Under-bridge inspection platform pre-positioned and load-tested",
            "Marine traffic notified if working over navigable water",
            "Weather check: postpone if wind exceeds 40 km/h or lightning within 10 km"
        ],
        "equipment": [
            "Schmidt rebound hammer",
            "ultrasonic thickness gauge",
            "crack width comparator cards",
            "half-cell potential meter",
            "drone with high-resolution camera",
            "GPS-enabled measurement tools"
        ],
        "steps": [
            {"order": 1, "action": "Conduct drone survey of entire bridge deck and superstructure", "notes": "Capture ortho-mosaic imagery at minimum 2 cm/pixel resolution"},
            {"order": 2, "action": "Inspect all expansion joints for debris, damage, and alignment", "notes": "Measure joint gap at 3 points per joint and compare to design values"},
            {"order": 3, "action": "Perform concrete condition survey on substructure elements", "notes": "Use Schmidt hammer at 10 test points per pier; record rebound numbers"},
            {"order": 4, "action": "Measure crack widths on all visible cracks exceeding 0.1 mm", "notes": "Map crack locations on structural drawings; flag any crack > 0.3 mm"},
            {"order": 5, "action": "Conduct ultrasonic thickness measurements on steel elements", "notes": "Test at 5 points per member; flag any section loss exceeding 10%"},
            {"order": 6, "action": "Inspect bearing assemblies for corrosion, displacement, and lubrication", "notes": "Photograph each bearing; note any lateral displacement > 5 mm"},
            {"order": 7, "action": "Assess drainage system for blockages and erosion damage", "notes": "Flush each scupper and downpipe; verify discharge at outfall"},
            {"order": 8, "action": "Review and update sensor calibration records for installed monitoring equipment", "notes": "Cross-reference live sensor readings with manual measurements"}
        ],
        "escalation": {
            "contact": "Structural Engineering Division",
            "phone": "555-0187",
            "conditions": ["Any crack exceeding 1.0 mm width", "Section loss exceeding 25%", "Bearing displacement exceeding 15 mm", "Visible reinforcement corrosion"]
        }
    },
    {
        "procedureId": "SOP-PL-001",
        "title": "Pressurized Pipeline Integrity Assessment",
        "category": "pipeline",
        "version": "4.0",
        "lastRevised": "2025-10-02",
        "estimatedDuration_min": 300,
        "requiredPersonnel": 3,
        "applicableAssetTypes": ["pipeline"],
        "safetyChecklist": [
            "Pipeline depressurized and isolated at both ends (double block and bleed)",
            "Atmospheric monitoring: confirm no hazardous gases (LEL < 10%, O2 19.5-23.5%)",
            "Confined space entry permit obtained if entering valve chambers",
            "Traffic management in place for any road crossings",
            "Emergency shutdown procedure reviewed with all team members"
        ],
        "equipment": [
            "inline inspection pig launcher/receiver",
            "magnetic flux leakage (MFL) tool",
            "pipeline CCTV crawler",
            "ultrasonic wall thickness gauge",
            "pressure test pump and chart recorder"
        ],
        "steps": [
            {"order": 1, "action": "Verify pipeline isolation and depressurization at all boundary valves", "notes": "Record valve positions and lock-out/tag-out details"},
            {"order": 2, "action": "Launch CCTV inspection crawler from upstream access point", "notes": "Record video with distance counter; note any anomalies with timestamps"},
            {"order": 3, "action": "Perform ultrasonic wall thickness measurements at accessible locations", "notes": "Minimum 5 readings per pipe section; focus on bends and joints"},
            {"order": 4, "action": "Inspect all valve chambers for leaks, corrosion, and structural integrity", "notes": "Check valve stem packing, flange bolts, and chamber ventilation"},
            {"order": 5, "action": "Conduct hydrostatic pressure test at 1.5x operating pressure", "notes": "Hold for minimum 2 hours; acceptable pressure drop: < 0.5%"},
            {"order": 6, "action": "Inspect cathodic protection system: anodes, rectifiers, test stations", "notes": "Measure pipe-to-soil potential at each test station; target: -850 mV to -1200 mV (Cu/CuSO4)"},
            {"order": 7, "action": "Survey pipeline route for surface settlement, erosion, or third-party damage", "notes": "Walk full route; compare surface levels to baseline survey"}
        ],
        "escalation": {
            "contact": "Water Infrastructure Emergency Line",
            "phone": "555-0129",
            "conditions": ["Wall thickness below 60% of nominal", "Failed hydrostatic test", "Active leak detected", "Cathodic protection failure across multiple stations"]
        }
    },
    {
        "procedureId": "SOP-EM-001",
        "title": "Emergency Pipeline Leak Response",
        "category": "emergency",
        "version": "5.1",
        "lastRevised": "2026-01-10",
        "estimatedDuration_min": 0,
        "requiredPersonnel": 4,
        "applicableAssetTypes": ["pipeline", "pump_station"],
        "safetyChecklist": [
            "Establish exclusion zone: minimum 25 m radius from leak source",
            "Atmospheric monitoring continuous at exclusion zone boundary",
            "Emergency services notified if gas or hazardous material involved",
            "Downstream consumers notified of potential supply interruption",
            "PPE: waterproof suit, respiratory protection if gas risk, steel-toe boots"
        ],
        "equipment": [
            "pipe repair clamps (assorted sizes)",
            "portable pump for dewatering",
            "pipe freezing kit",
            "leak sealing compound",
            "portable generator and lighting"
        ],
        "steps": [
            {"order": 1, "action": "Assess leak severity and classify: Category 1 (spray/gush), Category 2 (steady flow), Category 3 (seep/weep)", "notes": "Category 1 requires immediate isolation; Categories 2-3 allow time for planned repair"},
            {"order": 2, "action": "Isolate the affected section using upstream and downstream valves", "notes": "Coordinate with SCADA control room for remote valve operations where available"},
            {"order": 3, "action": "Establish dewatering and containment at the leak site", "notes": "Prevent uncontrolled runoff into stormwater drains or waterways"},
            {"order": 4, "action": "Apply temporary repair (clamp, freeze, or seal) appropriate to pipe material and pressure", "notes": "Temporary repairs must be replaced with permanent repairs within 72 hours"},
            {"order": 5, "action": "Restore pressure gradually and monitor repaired section for 30 minutes", "notes": "Increase pressure in 25% increments; hold at each stage for 5 minutes"},
            {"order": 6, "action": "Document incident: location (GPS), pipe details, cause assessment, photos, repair method", "notes": "Submit incident report within 24 hours via CityPulse incident management system"}
        ],
        "escalation": {
            "contact": "Emergency Operations Center",
            "phone": "555-0911",
            "conditions": ["Category 1 leak on any main exceeding 300 mm diameter", "Any gas leak", "Contamination risk to potable supply", "Road collapse or sinkhole formation"]
        }
    },
    {
        "procedureId": "SOP-CT-001",
        "title": "Communications Tower Routine Maintenance",
        "category": "communications",
        "version": "2.0",
        "lastRevised": "2025-06-18",
        "estimatedDuration_min": 150,
        "requiredPersonnel": 2,
        "applicableAssetTypes": ["communication_tower"],
        "safetyChecklist": [
            "Tower climbing certification verified for all personnel",
            "Fall arrest system inspected: harness, lanyards, rope grabs",
            "RF exposure assessment completed; power reduction requested if needed",
            "Weather check: no climbing if wind > 50 km/h, rain, or electrical storms",
            "Rescue plan in place with qualified rescuer on standby"
        ],
        "equipment": [
            "cable analyzer (sweep tester)",
            "fiber optic power meter and OTDR",
            "torque wrench set",
            "coaxial connector toolkit",
            "tower-rated tool lanyard system"
        ],
        "steps": [
            {"order": 1, "action": "Inspect tower structure: legs, bracing, bolted connections, foundation", "notes": "Check for corrosion, loose bolts, cracked welds; torque-check sample of bolts"},
            {"order": 2, "action": "Inspect all antenna mounts, brackets, and alignment", "notes": "Verify azimuth and tilt settings match RF design specifications"},
            {"order": 3, "action": "Test all coaxial and fiber optic cable runs", "notes": "Sweep test coax for VSWR < 1.5:1; OTDR test fiber for splice loss < 0.1 dB"},
            {"order": 4, "action": "Inspect obstruction lighting: daytime and nighttime modes", "notes": "Replace any failed lamps immediately; verify photocell operation at dusk"},
            {"order": 5, "action": "Inspect grounding system from tower top to ground ring", "notes": "Measure ground resistance: maximum 5 Ω for telecommunications towers"},
            {"order": 6, "action": "Clean and inspect equipment shelter: HVAC, UPS, batteries, fire suppression", "notes": "Check battery terminal voltage and ambient temperature; clean air filters"}
        ],
        "escalation": {
            "contact": "Network Operations Center",
            "phone": "555-0165",
            "conditions": ["Structural member damage or missing bolts", "Obstruction lighting failure", "Ground resistance exceeding 10 Ω", "Equipment shelter temperature exceeding 35°C"]
        }
    },
    {
        "procedureId": "SOP-WTP-001",
        "title": "Water Treatment Plant Process Audit",
        "category": "water-treatment",
        "version": "3.0",
        "lastRevised": "2025-09-05",
        "estimatedDuration_min": 360,
        "requiredPersonnel": 3,
        "applicableAssetTypes": ["treatment_plant"],
        "safetyChecklist": [
            "Chemical handling PPE available: chemical-resistant gloves, goggles, face shield",
            "Safety showers and eyewash stations tested and accessible",
            "Atmospheric monitoring in enclosed process areas",
            "Chlorine gas detection system verified operational",
            "Emergency chemical spill kit staged at audit locations"
        ],
        "equipment": [
            "portable turbidity meter",
            "pH/ORP meter with calibration standards",
            "dissolved oxygen meter",
            "sample bottles (sterile and non-sterile)",
            "portable flow meter (ultrasonic)"
        ],
        "steps": [
            {"order": 1, "action": "Review SCADA trends for previous 30 days: flow, turbidity, pH, chlorine residual", "notes": "Flag any exceedances of regulatory limits or unusual trends"},
            {"order": 2, "action": "Inspect primary treatment: screens, grit removal, primary clarifiers", "notes": "Check scraper mechanisms, scum removal, and sludge blanket depth"},
            {"order": 3, "action": "Inspect secondary treatment: aeration basins, dissolved oxygen control, return sludge pumps", "notes": "Verify DO setpoints match process design; check diffuser performance"},
            {"order": 4, "action": "Inspect tertiary treatment and disinfection: filters, UV reactors, chlorination", "notes": "Check UV lamp intensity readings; verify chlorine dosing accuracy"},
            {"order": 5, "action": "Audit chemical storage and delivery systems", "notes": "Verify chemical inventory matches records; check containment bunds and delivery systems for leaks"},
            {"order": 6, "action": "Review laboratory QA/QC records and split-sample results", "notes": "Verify calibration records are current; check proficiency test results"},
            {"order": 7, "action": "Inspect sludge handling: digesters, dewatering, biogas systems", "notes": "Check digester gas production rates; inspect dewatering press performance"},
            {"order": 8, "action": "Review compliance reporting and regulatory correspondence", "notes": "Ensure all required reports submitted on time; note any outstanding corrective actions"}
        ],
        "escalation": {
            "contact": "Environmental Compliance Manager",
            "phone": "555-0134",
            "conditions": ["Effluent quality exceeding discharge permit limits", "Chemical spill or uncontrolled release", "UV disinfection system failure", "Biogas system anomaly"]
        }
    },
    {
        "procedureId": "SOP-FLD-001",
        "title": "Flood Event Response and Pump Station Operations",
        "category": "emergency",
        "version": "4.2",
        "lastRevised": "2025-12-01",
        "estimatedDuration_min": 0,
        "requiredPersonnel": 3,
        "applicableAssetTypes": ["pump_station", "sensor"],
        "safetyChecklist": [
            "Swift-water rescue team on standby if river level exceeds 5.0 m",
            "Exclusion zone established around pump station wet well",
            "Backup generator fuel level verified > 75%",
            "Communication with Emergency Operations Center established",
            "Road closure requests submitted to traffic management"
        ],
        "equipment": [
            "portable submersible pump (backup)",
            "sandbags and flood barriers",
            "portable generator",
            "water level data logger",
            "satellite phone (communications backup)"
        ],
        "steps": [
            {"order": 1, "action": "Activate flood monitoring protocol: 15-minute gauge readings, SCADA alarm monitoring", "notes": "Begin when river level exceeds 3.5 m at Flood Gauge Station R1"},
            {"order": 2, "action": "Pre-position portable pumps and flood barriers at known vulnerable locations", "notes": "Priority locations: Riverside Corridor underpass, Harbor District low points"},
            {"order": 3, "action": "Verify all permanent pump stations operational: run each pump for 2 minutes", "notes": "Check vibration levels and discharge pressure; switch to backup if anomaly detected"},
            {"order": 4, "action": "At trigger level (4.2 m), activate Riverside Pump Station in automatic mode", "notes": "Confirm SCADA is receiving pump status and discharge flow data"},
            {"order": 5, "action": "Deploy field crew to monitor overland flow paths and report blockages", "notes": "Focus on trash screens, culvert inlets, and road drainage grates"},
            {"order": 6, "action": "Post-event: inspect all pump stations, clear debris, reset systems", "notes": "Document high-water marks with GPS; photograph all flood damage"}
        ],
        "escalation": {
            "contact": "Emergency Operations Center",
            "phone": "555-0911",
            "conditions": ["River level exceeding 5.5 m (1% AEP event)", "Pump station failure during flood event", "Road inundation on arterial routes", "Threat to life or occupied buildings"]
        }
    },
    {
        "procedureId": "SOP-SW-001",
        "title": "Seawall and Retaining Wall Annual Inspection",
        "category": "structural",
        "version": "1.3",
        "lastRevised": "2025-07-22",
        "estimatedDuration_min": 200,
        "requiredPersonnel": 2,
        "applicableAssetTypes": ["retaining_wall"],
        "safetyChecklist": [
            "Tidal schedule reviewed: inspection during low tide for seawalls",
            "Fall protection for any work near wall crest or exposed edges",
            "Marine vessel exclusion zone if inspecting from water side",
            "Hard hat and high-visibility clothing at all times",
            "First aid kit with hypothermia blanket for waterside work"
        ],
        "equipment": [
            "crack monitoring pins and digital caliper",
            "ground-penetrating radar (GPR) unit",
            "survey-grade GPS for settlement measurements",
            "underwater camera (for seawall toe inspection)",
            "concrete coring drill (if sampling required)"
        ],
        "steps": [
            {"order": 1, "action": "Survey wall crest and toe levels using GPS; compare to baseline", "notes": "Flag any settlement exceeding 15 mm since last survey"},
            {"order": 2, "action": "Visual inspection of wall face: cracks, spalling, efflorescence, vegetation", "notes": "Map all defects on wall elevation drawings with chainage references"},
            {"order": 3, "action": "Install or read crack monitoring pins on active cracks", "notes": "Record crack width to 0.05 mm precision; note any change since last reading"},
            {"order": 4, "action": "Inspect drainage systems: weepholes, toe drains, backfill drainage", "notes": "Blocked weepholes indicate drainage failure and increased hydrostatic pressure"},
            {"order": 5, "action": "Conduct GPR survey along wall crest to detect voids or erosion behind wall", "notes": "Focus on sections near stormwater outfalls and tidal zones"},
            {"order": 6, "action": "For seawalls: inspect toe protection, armour units, and scour apron at low tide", "notes": "Photograph any displaced armour units; note scour depth measurements"}
        ],
        "escalation": {
            "contact": "Coastal Engineering Division",
            "phone": "555-0176",
            "conditions": ["Settlement exceeding 50 mm", "Active crack growth exceeding 0.5 mm/year", "Void detected behind wall face", "Scour depth exceeding design allowance"]
        }
    },
    {
        "procedureId": "SOP-SOL-001",
        "title": "Solar Installation Performance Audit",
        "category": "electrical",
        "version": "1.1",
        "lastRevised": "2025-05-30",
        "estimatedDuration_min": 120,
        "requiredPersonnel": 2,
        "applicableAssetTypes": ["solar_installation"],
        "safetyChecklist": [
            "DC isolation verified before any panel or string-level work",
            "Arc-flash PPE for inverter cabinet access",
            "Roof access safety: harness and anchor points for rooftop arrays",
            "No work on wet panels or during rain",
            "Verify fire isolation switches accessible and labeled"
        ],
        "equipment": [
            "IV curve tracer",
            "thermal imaging camera",
            "digital multimeter (CAT III rated)",
            "irradiance meter (pyranometer)",
            "insulation resistance tester"
        ],
        "steps": [
            {"order": 1, "action": "Review monitoring system data: production vs. expected yield for previous quarter", "notes": "Flag any string or inverter with output < 90% of expected"},
            {"order": 2, "action": "Conduct thermal survey of all accessible panel strings", "notes": "Identify hot spots indicating cell damage, bypass diode failure, or connection issues"},
            {"order": 3, "action": "Perform IV curve tracing on sample strings (minimum 10% of total)", "notes": "Compare to commissioning baseline; flag degradation > 2% per year"},
            {"order": 4, "action": "Inspect inverter operation: error logs, cooling fans, AC output quality", "notes": "Check THD < 5% and power factor > 0.95 at rated output"},
            {"order": 5, "action": "Inspect racking, mounting hardware, and grounding connections", "notes": "Check for corrosion, loose fasteners, and ground continuity"},
            {"order": 6, "action": "Clean panels if soiling losses exceed 5% (based on irradiance comparison)", "notes": "Use deionized water only; no abrasive cleaning agents"}
        ],
        "escalation": {
            "contact": "Renewable Energy Operations Manager",
            "phone": "555-0198",
            "conditions": ["Inverter failure or shutdown", "Ground fault detected in DC system", "Panel hot spot exceeding 30°C differential", "Production drop > 20% from baseline"]
        }
    }
]


# ============================================================================
# LLM Generation Prompts
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
# Database Operations
# ============================================================================

def get_connection():
    """Create and return an Oracle database connection."""
    if ORACLE_WALLET_DIR:
        return oracledb.connect(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_DSN,
            config_dir=ORACLE_WALLET_DIR,
            wallet_location=ORACLE_WALLET_DIR,
            wallet_password=ORACLE_PASSWORD
        )
    else:
        return oracledb.connect(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_DSN
        )


def insert_districts(cursor):
    """Insert district records."""
    print("Inserting districts...")
    for d in DISTRICTS:
        cursor.execute("""
            INSERT INTO districts (name, classification, population, area_sq_km, description)
            VALUES (:name, :classification, :population, :area_sq_km, :description)
        """, d)
    print(f"  Inserted {len(DISTRICTS)} districts.")


def insert_assets(cursor):
    """Insert infrastructure asset records. Returns a mapping of asset name to asset_id."""
    print("Inserting infrastructure assets...")
    asset_map = {}

    # First, get district IDs
    cursor.execute("SELECT district_id, name FROM districts")
    district_map = {row[1]: row[0] for row in cursor.fetchall()}

    for asset in INFRASTRUCTURE_ASSETS:
        name, asset_type, district_idx, status, comm_date, description, specs = asset
        district_name = DISTRICTS[district_idx]["name"]
        district_id = district_map[district_name]

        cursor.execute("""
            INSERT INTO infrastructure_assets
                (district_id, name, asset_type, status, commissioned_date, description, specifications)
            VALUES
                (:district_id, :name, :asset_type, :status,
                 TO_DATE(:commissioned_date, 'YYYY-MM-DD'), :description,
                 JSON(:specifications))
            RETURNING asset_id INTO :asset_id
        """, {
            "district_id": district_id,
            "name": name,
            "asset_type": asset_type,
            "status": status,
            "commissioned_date": comm_date,
            "description": description,
            "specifications": json.dumps(specs),
            "asset_id": cursor.var(oracledb.NUMBER)
        })
        asset_id = cursor.getimplicitresults()  # Get the returned asset_id
        asset_map[name] = cursor.var(oracledb.NUMBER).getvalue()

    # Re-fetch to get the actual mapping
    cursor.execute("SELECT asset_id, name FROM infrastructure_assets")
    asset_map = {row[1]: row[0] for row in cursor.fetchall()}

    print(f"  Inserted {len(INFRASTRUCTURE_ASSETS)} assets.")
    return asset_map


def insert_connections(cursor, asset_map):
    """Insert asset connection records."""
    print("Inserting asset connections...")
    count = 0
    for conn in ASSET_CONNECTIONS:
        from_name, to_name, conn_type, description = conn
        if from_name not in asset_map or to_name not in asset_map:
            print(f"  WARNING: Skipping connection '{from_name}' -> '{to_name}': asset not found")
            continue
        cursor.execute("""
            INSERT INTO asset_connections
                (from_asset_id, to_asset_id, connection_type, description)
            VALUES
                (:from_id, :to_id, :conn_type, :description)
        """, {
            "from_id": asset_map[from_name],
            "to_id": asset_map[to_name],
            "conn_type": conn_type,
            "description": description
        })
        count += 1
    print(f"  Inserted {count} connections.")


def insert_procedures(cursor):
    """Insert operational procedure documents into the JSON collection table."""
    print("Inserting operational procedures...")
    for proc in OPERATIONAL_PROCEDURES:
        cursor.execute("""
            INSERT INTO operational_procedures (data)
            VALUES (JSON(:doc))
        """, {"doc": json.dumps(proc)})
    print(f"  Inserted {len(OPERATIONAL_PROCEDURES)} procedures.")


# ============================================================================
# LLM Content Generation
# ============================================================================

def get_genai_client():
    """Create and return an OCI Generative AI inference client."""
    config = oci.config.from_file()
    return oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=OCI_GENAI_ENDPOINT
    )


def generate_with_llm(client, system_prompt, user_prompt):
    """Call the OCI Generative AI chat endpoint and return the response text."""
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
            max_tokens=4096,
            temperature=0.8,
            top_p=0.9
        )
    )

    response = client.chat(chat_request)
    return response.data.chat_response.choices[0].message.content[0].text


def parse_json_response(response_text):
    """Extract and parse JSON from an LLM response, handling markdown code blocks."""
    text = response_text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (the fences)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def generate_maintenance_logs(client, cursor, asset_map):
    """Generate and insert maintenance logs using the LLM."""
    print(f"\nGenerating {TARGET_MAINTENANCE_LOGS} maintenance logs via LLM...")

    # Get asset details for prompts
    cursor.execute("""
        SELECT a.asset_id, a.name, a.asset_type, a.specifications, d.name AS district_name
        FROM infrastructure_assets a
        JOIN districts d ON a.district_id = d.district_id
    """)
    assets = cursor.fetchall()

    # Distribute logs across assets (weighted toward more important/complex assets)
    asset_weights = []
    for asset in assets:
        asset_type = asset[2]
        weight = {
            "bridge": 5, "substation": 4, "pipeline": 4, "treatment_plant": 4,
            "pump_station": 3, "sensor": 2, "communication_tower": 2,
            "retaining_wall": 2, "reservoir": 2, "solar_installation": 2,
            "rail_terminal": 2
        }.get(asset_type, 1)
        asset_weights.append((asset, weight))

    total_weight = sum(w for _, w in asset_weights)
    total_inserted = 0

    for asset, weight in asset_weights:
        asset_id, asset_name, asset_type, specs, district_name = asset
        count = max(3, round(TARGET_MAINTENANCE_LOGS * weight / total_weight))

        print(f"  Generating {count} logs for {asset_name}...")

        prompt = MAINTENANCE_LOG_USER_PROMPT.format(
            count=count,
            asset_name=asset_name,
            asset_type=asset_type,
            district_name=district_name,
            specifications=json.dumps(json.loads(specs) if isinstance(specs, str) else specs, indent=2) if specs else "N/A"
        )

        try:
            response = generate_with_llm(client, MAINTENANCE_LOG_SYSTEM_PROMPT, prompt)
            logs = parse_json_response(response)

            for log in logs:
                log_date = datetime.now() - timedelta(days=log.get("days_ago", random.randint(1, 730)))
                cursor.execute("""
                    INSERT INTO maintenance_logs (asset_id, log_date, severity, narrative)
                    VALUES (:asset_id, :log_date, :severity, :narrative)
                """, {
                    "asset_id": asset_id,
                    "log_date": log_date,
                    "severity": log["severity"],
                    "narrative": log["narrative"]
                })
                total_inserted += 1

        except Exception as e:
            print(f"    ERROR generating logs for {asset_name}: {e}")
            continue

    print(f"  Total maintenance logs inserted: {total_inserted}")


def generate_inspection_reports(client, cursor, asset_map):
    """Generate and insert inspection reports and findings using the LLM."""
    print(f"\nGenerating {TARGET_INSPECTION_REPORTS} inspection reports via LLM...")

    # Focus on inspectable asset types
    inspectable_types = ("bridge", "substation", "pipeline", "treatment_plant",
                         "pump_station", "retaining_wall", "communication_tower",
                         "solar_installation", "reservoir")

    cursor.execute("""
        SELECT a.asset_id, a.name, a.asset_type, a.specifications, d.name AS district_name
        FROM infrastructure_assets a
        JOIN districts d ON a.district_id = d.district_id
        WHERE a.asset_type IN :types
    """, {"types": inspectable_types})
    assets = cursor.fetchall()

    # Distribute reports across assets
    reports_per_asset = max(2, TARGET_INSPECTION_REPORTS // len(assets))
    total_reports = 0
    total_findings = 0

    for asset in assets:
        asset_id, asset_name, asset_type, specs, district_name = asset
        count = reports_per_asset

        print(f"  Generating {count} reports for {asset_name}...")

        prompt = INSPECTION_REPORT_USER_PROMPT.format(
            count=count,
            asset_name=asset_name,
            asset_type=asset_type,
            district_name=district_name,
            specifications=json.dumps(json.loads(specs) if isinstance(specs, str) else specs, indent=2) if specs else "N/A"
        )

        try:
            response = generate_with_llm(client, INSPECTION_REPORT_SYSTEM_PROMPT, prompt)
            reports = parse_json_response(response)

            for report in reports:
                inspect_date = datetime.now() - timedelta(days=report.get("days_ago", random.randint(1, 1095)))

                cursor.execute("""
                    INSERT INTO inspection_reports
                        (asset_id, inspector, inspect_date, overall_grade, summary)
                    VALUES
                        (:asset_id, :inspector, :inspect_date, :overall_grade, :summary)
                    RETURNING report_id INTO :report_id
                """, {
                    "asset_id": asset_id,
                    "inspector": report["inspector"],
                    "inspect_date": inspect_date,
                    "overall_grade": report["overall_grade"],
                    "summary": report["summary"],
                    "report_id": cursor.var(oracledb.NUMBER)
                })
                report_id_var = cursor.var(oracledb.NUMBER)
                # Re-fetch report_id
                cursor.execute("SELECT MAX(report_id) FROM inspection_reports WHERE asset_id = :aid AND inspector = :insp",
                               {"aid": asset_id, "insp": report["inspector"]})
                report_id = cursor.fetchone()[0]

                for finding in report.get("findings", []):
                    cursor.execute("""
                        INSERT INTO inspection_findings
                            (report_id, category, severity, description, recommendation)
                        VALUES
                            (:report_id, :category, :severity, :description, :recommendation)
                    """, {
                        "report_id": report_id,
                        "category": finding["category"],
                        "severity": finding["severity"],
                        "description": finding["description"],
                        "recommendation": finding["recommendation"]
                    })
                    total_findings += 1

                total_reports += 1

        except Exception as e:
            print(f"    ERROR generating reports for {asset_name}: {e}")
            continue

    print(f"  Total inspection reports inserted: {total_reports}")
    print(f"  Total inspection findings inserted: {total_findings}")


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 72)
    print("  PRISM: Seed Data Generator")
    print("=" * 72)
    print()

    # Validate configuration
    missing = []
    if not ORACLE_DSN:
        missing.append("ORACLE_DSN")
    if not ORACLE_PASSWORD:
        missing.append("ORACLE_PASSWORD")
    if not OCI_COMPARTMENT_ID:
        missing.append("OCI_COMPARTMENT_ID")

    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
        print("Set these variables and re-run.")
        sys.exit(1)

    # Connect to database
    print("Connecting to Oracle database...")
    conn = get_connection()
    cursor = conn.cursor()
    print("  Connected.")

    # Insert structural data
    print("\n--- Phase 1: Structural Data ---")
    insert_districts(cursor)
    asset_map = insert_assets(cursor)
    insert_connections(cursor, asset_map)
    insert_procedures(cursor)
    conn.commit()
    print("\nStructural data committed.")

    # Generate narrative content via LLM
    print("\n--- Phase 2: LLM-Generated Content ---")
    print("Initializing OCI Generative AI client...")
    genai_client = get_genai_client()

    generate_maintenance_logs(genai_client, cursor, asset_map)
    conn.commit()
    print("Maintenance logs committed.")

    generate_inspection_reports(genai_client, cursor, asset_map)
    conn.commit()
    print("Inspection reports committed.")

    # Summary
    print("\n--- Summary ---")
    for table_name in ["districts", "infrastructure_assets", "operational_procedures",
                       "maintenance_logs", "inspection_reports", "inspection_findings",
                       "asset_connections"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  {table_name:30s} {count:>6d} rows")

    cursor.close()
    conn.close()

    print()
    print("=" * 72)
    print("  Seed data generation complete.")
    print("  Next step: Run python prism-ingest.py to vectorize content.")
    print("=" * 72)


if __name__ == "__main__":
    main()
