"""
Generates synthetic FIR reports, CDR records, financial transactions,
surveillance reports, social media intel, criminal history records, and
intel agency reports — all sharing a consistent entity roster (3 cells +
2 bridges) so the resulting knowledge graph has real, validatable structure.

Deliberately includes realistic data-quality problems the pipeline must
resolve — this is the actual "fragmented, unstructured, distributed"
problem from the PS, not just narrative variety:
  - Name variants across sources (nicknames, initials, handles)
  - Inconsistent phone number formatting
  - Missing/null fields in unstructured sources
  - Realistic FIR boilerplate (IPC sections) around the actual narrative
  - A few uncorroborated one-off mentions (real tip lines include dead ends)
"""
import csv
import json
import random
from datetime import datetime, timedelta

random.seed(42)

# ---- Shared entity pool -----------------------------------------------
PEOPLE = [
    {"name": "Rahul Sharma", "phone": "9876543210", "vehicle": "MP09AB1234", "group": "A"},
    {"name": "Vikram Singh", "phone": "9123456780", "vehicle": "MP09XY5678", "group": "A"},
    {"name": "Amit Verma", "phone": "9988776655", "vehicle": "MP04CD9012", "group": "A"},
    {"name": "Suresh Yadav", "phone": "9871234560", "vehicle": None, "group": "B"},
    {"name": "Deepak Rao", "phone": "9012345678", "vehicle": "MP09EF3456", "group": "B"},
    {"name": "Manoj Tiwari", "phone": "9765432109", "vehicle": None, "group": "B"},
    {"name": "Ravi Kumar", "phone": "9345678901", "vehicle": "MP04GH7890", "group": "C"},
    {"name": "Sanjay Mehta", "phone": "9456789012", "vehicle": None, "group": "C"},
]

GROUPS = {"A": [p for p in PEOPLE if p["group"] == "A"],
          "B": [p for p in PEOPLE if p["group"] == "B"],
          "C": [p for p in PEOPLE if p["group"] == "C"]}

BY_NAME = {p["name"]: p for p in PEOPLE}

BRIDGES = [
    (BY_NAME["Vikram Singh"], BY_NAME["Suresh Yadav"]),   # bridges A <-> B
    (BY_NAME["Deepak Rao"], BY_NAME["Ravi Kumar"]),        # bridges B <-> C
]

def pick_pair(same_group_prob=0.88, bridge_prob=0.07):
    r = random.random()
    if r < bridge_prob:
        return random.choice(BRIDGES)
    if r < bridge_prob + same_group_prob:
        group = random.choice(list(GROUPS.values()))
        if len(group) >= 2:
            return tuple(random.sample(group, 2))
    return tuple(random.sample(PEOPLE, 2))

LOCATIONS = ["Malviya Nagar", "Rajwada", "Vijay Nagar", "Bhawarkuan", "Sudama Nagar"]
ORGS = ["Shree Traders", "Om Logistics", "Balaji Enterprises"]

# ---- Name variants (the real entity-resolution problem) -----------------
# Structured/official sources (CDR, transactions, criminal history) always
# use the canonical name — that's realistic, since those come from KYC/
# telecom records. Narrative sources (FIR, surveillance, social media) are
# where variants show up, because those come from human observation and
# informal reporting. This alias map is written out as ground truth so the
# resolution step can be validated, same way ground_truth_entities.json
# validates the community structure.
NAME_VARIANTS = {
    "Rahul Sharma": ["R. Sharma", "Rahul S."],
    "Vikram Singh": ["V. Singh", "Vicky Singh"],
    "Amit Verma": ["A. Verma"],
    "Suresh Yadav": ["S. Yadav", "Suresh Y."],
    "Deepak Rao": ["D. Rao"],
    "Manoj Tiwari": ["M. Tiwari", "Manoj T."],
    "Ravi Kumar": ["R. Kumar"],
    "Sanjay Mehta": ["S. Mehta", "Sanjay M."],
}

HANDLES = {p["name"]: f"@{p['name'].split()[0].lower()}_{random.randint(10,99)}" for p in PEOPLE}

def narrative_name(person, variant_prob=0.3):
    """Returns the canonical name most of the time, a known variant
    sometimes — simulates how the same person gets referred to
    inconsistently across informal reports."""
    name = person["name"]
    if random.random() < variant_prob and name in NAME_VARIANTS:
        return random.choice(NAME_VARIANTS[name])
    return name

def format_phone(phone, messy_prob=0.4):
    """Real phone numbers show up in multiple formats across sources.
    The extraction regex has to tolerate this, not just match a single
    clean 10-digit pattern."""
    if random.random() >= messy_prob:
        return phone
    style = random.choice(["plus91", "plus91_space", "dashed"])
    if style == "plus91":
        return f"+91{phone}"
    if style == "plus91_space":
        return f"+91 {phone}"
    return f"{phone[:5]}-{phone[5:]}"

# ---- 1. Synthetic FIR-style text reports (with realistic boilerplate) --
IPC_SECTIONS = ["420", "406", "120B", "34", "384"]

fir_templates = [
    "Suspect {p1} was seen near {loc} with vehicle {veh}, contacted {phone}.",
    "Complainant reported {p1} and {p2} meeting near {loc} on suspicious grounds.",
    "{p1} allegedly linked to {org}, frequently seen at {loc}.",
    "Informant states {p1} received a call from {phone2} while at {loc}.",
    "{p1} aur {p2} {loc} mein mile the, dono ka phone number record kiya gaya hai.",
]

fir_reports = []
for i in range(25):
    p1, p2 = pick_pair()
    loc = random.choice(LOCATIONS)
    org = random.choice(ORGS)
    template = random.choice(fir_templates)
    narrative = template.format(
        p1=narrative_name(p1), p2=narrative_name(p2), loc=loc,
        veh=p1["vehicle"] or "unknown", phone=format_phone(p1["phone"]),
        phone2=format_phone(p2["phone"]), org=org
    )
    # Realistic FIR boilerplate wrapper around the actual narrative content.
    section = random.choice(IPC_SECTIONS)
    text = f"Case registered under Section {section} IPC. {narrative}"
    fir_reports.append({"doc_id": f"FIR-{1000+i}", "text": text,
                         "date": str(datetime(2026, 7, 1) + timedelta(days=i))})

# A couple of uncorroborated one-off tips: mention a PEOPLE member and a
# name that appears nowhere else in the dataset. Real tip lines include
# dead ends — the pipeline should extract these without them corrupting
# the cell/bridge structure Louvain is meant to recover.
NOISE_NAMES = ["Farhan Qureshi", "Priya Nair"]
for j, noise_name in enumerate(NOISE_NAMES):
    p1 = random.choice(PEOPLE)
    loc = random.choice(LOCATIONS)
    text = (f"Case registered under Section {random.choice(IPC_SECTIONS)} IPC. "
            f"Unverified tip: {narrative_name(p1)} possibly seen with unidentified "
            f"individual named {noise_name} near {loc}.")
    fir_reports.append({"doc_id": f"FIR-{1025+j}", "text": text,
                         "date": str(datetime(2026, 7, 26) + timedelta(days=j))})

with open("fir_reports.json", "w") as f:
    json.dump(fir_reports, f, indent=2)

# ---- 2. Synthetic CDR (unchanged — structured/official, canonical) -----
with open("cdr.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["caller_number", "receiver_number", "timestamp", "duration_sec", "tower_location"])
    base_time = datetime(2026, 7, 1)
    for i in range(200):
        caller, receiver = pick_pair()
        if i % 6 == 0 and receiver != PEOPLE[0]:
            caller = PEOPLE[0]
        ts = base_time + timedelta(minutes=random.randint(0, 40000))
        writer.writerow([caller["phone"], receiver["phone"], ts.isoformat(),
                          random.randint(10, 900), random.choice(LOCATIONS)])

# ---- 3. Synthetic financial transactions (unchanged — structured) ------
with open("transactions.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sender_name", "receiver_name", "amount", "timestamp", "transaction_type"])
    base_time = datetime(2026, 7, 1)
    for i in range(120):
        sender, receiver = pick_pair()
        if i % 10 == 0:
            amount = random.randint(45000, 49999)
        else:
            amount = random.randint(500, 40000)
        ts = base_time + timedelta(hours=random.randint(0, 700))
        writer.writerow([sender["name"], receiver["name"], amount, ts.isoformat(),
                          random.choice(["UPI", "NEFT", "CASH"])])

# ---- 4. Ground-truth entity map ----------------------------------------
with open("ground_truth_entities.json", "w") as f:
    json.dump(PEOPLE, f, indent=2)

# ---- 5. Synthetic surveillance reports (with missing fields) -----------
SURV_TEMPLATES = [
    "Subject {p1} observed entering premises near {loc} at approx {hour}:00, departed after {dur} minutes.",
    "Field team tracked {p1} to a meeting with {p2} at {loc}; no physical exchange observed.",
    "{p1} observed loading unmarked packages into vehicle {veh} outside {loc}.",
    "Surveillance of {p1} inconclusive; subject appeared to evade tail.",  # no location — realistic gap
]

surveillance_reports = []
for i in range(15):
    p1, p2 = pick_pair()
    loc = random.choice(LOCATIONS) if random.random() > 0.15 else None  # ~15% missing location
    template = random.choice(SURV_TEMPLATES)
    text = template.format(p1=narrative_name(p1), p2=narrative_name(p2),
                            loc=loc or "an undisclosed location",
                            hour=random.randint(6, 23), dur=random.randint(5, 90),
                            veh=p1["vehicle"] or "an unmarked vehicle")
    ts = datetime(2026, 7, 1) + timedelta(days=random.randint(0, 28), hours=random.randint(0, 23))
    surveillance_reports.append({
        "doc_id": f"SURV-{2000+i}",
        "agent_id": f"AGT-{random.randint(100,199)}",
        "text": text,
        "location_confirmed": loc is not None,
        "date": str(ts),
    })

with open("surveillance_reports.json", "w") as f:
    json.dump(surveillance_reports, f, indent=2)

# ---- 6. Synthetic social media intel (noisiest, most variant-heavy) ----
SOCIAL_TEMPLATES = [
    "seen {p1} aur {p2} together near {loc} yesterday 👀",
    "{handle} posted a story tagged at {loc}",
    "heard {p1} doing kuch shady business with Om Logistics lately",
    "{handle} aur {handle2} ka group chat leak — dono {loc} ja rahe the",
    "does anyone know {p1}?? saw them around a lot this month",  # no location, low signal
]

social_media_posts = []
for i in range(20):
    p1, p2 = pick_pair()
    loc = random.choice(LOCATIONS)
    template = random.choice(SOCIAL_TEMPLATES)
    text = template.format(p1=narrative_name(p1, variant_prob=0.5),
                            p2=narrative_name(p2, variant_prob=0.5), loc=loc,
                            handle=HANDLES[p1["name"]], handle2=HANDLES[p2["name"]])
    ts = datetime(2026, 7, 1) + timedelta(days=random.randint(0, 28))
    social_media_posts.append({
        "doc_id": f"SOC-{3000+i}",
        "platform": random.choice(["X", "Instagram", "Facebook"]),
        "text": text,
        "date": str(ts),
    })

with open("social_media_posts.json", "w") as f:
    json.dump(social_media_posts, f, indent=2)

# ---- 7. Synthetic criminal history database (structured, canonical) ----
criminal_history = []
for p in PEOPLE:
    if random.random() < 0.6:
        criminal_history.append({
            "name": p["name"],
            "prior_convictions": random.randint(0, 3),
            "known_associates": [q["name"] for q in GROUPS[p["group"]] if q["name"] != p["name"]],
            "last_case_id": f"CASE-{random.randint(2020,2025)}-{random.randint(100,999)}",
        })

with open("criminal_history.json", "w") as f:
    json.dump(criminal_history, f, indent=2)

# ---- 8. Synthetic intel agency reports (higher-trust FIR variant) ------
INTEL_TEMPLATES = [
    "Source (reliability: {rel}) reports {p1} coordinating with {p2} on logistics near {loc}.",
    "Intercept suggests {p1} affiliated with {org}; activity concentrated around {loc}.",
]

intel_reports = []
for i in range(10):
    p1, p2 = pick_pair()
    loc = random.choice(LOCATIONS)
    org = random.choice(ORGS)
    template = random.choice(INTEL_TEMPLATES)
    text = template.format(p1=narrative_name(p1, variant_prob=0.15),
                            p2=narrative_name(p2, variant_prob=0.15),
                            loc=loc, org=org, rel=random.choice(["A", "B", "C"]))
    ts = datetime(2026, 7, 1) + timedelta(days=random.randint(0, 28))
    intel_reports.append({
        "doc_id": f"INTEL-{4000+i}",
        "classification": random.choice(["RESTRICTED", "CONFIDENTIAL"]),
        "confidence": round(random.uniform(0.5, 0.95), 2),
        "text": text,
        "date": str(ts),
    })

with open("intel_reports.json", "w") as f:
    json.dump(intel_reports, f, indent=2)

# ---- 9. Alias ground truth (for validating the resolution step) --------
alias_ground_truth = {name: variants for name, variants in NAME_VARIANTS.items()}
alias_ground_truth["_handles"] = HANDLES
with open("alias_ground_truth.json", "w") as f:
    json.dump(alias_ground_truth, f, indent=2)

print(f"Generated {len(fir_reports)} FIR reports, 200 CDR rows, 120 transactions,")
print(f"{len(surveillance_reports)} surveillance reports, {len(social_media_posts)} social posts,")
print(f"{len(criminal_history)} criminal history records, {len(intel_reports)} intel reports.")
print("Also wrote alias_ground_truth.json for validating entity resolution.")