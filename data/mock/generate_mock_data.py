"""
Generates synthetic FIR reports, CDR records, and financial transactions
that share a consistent set of entities, so the resulting knowledge graph
actually has connected structure worth analyzing.
"""
import csv
import json
import random
from datetime import datetime, timedelta

random.seed(42)

# ---- Shared entity pool -----------------------------------------------
PEOPLE = [
    {"name": "Rahul Sharma", "phone": "9876543210", "vehicle": "MP09AB1234"},
    {"name": "Vikram Singh", "phone": "9123456780", "vehicle": "MP09XY5678"},
    {"name": "Amit Verma", "phone": "9988776655", "vehicle": "MP04CD9012"},
    {"name": "Suresh Yadav", "phone": "9871234560", "vehicle": None},
    {"name": "Deepak Rao", "phone": "9012345678", "vehicle": "MP09EF3456"},
    {"name": "Manoj Tiwari", "phone": "9765432109", "vehicle": None},
    {"name": "Ravi Kumar", "phone": "9345678901", "vehicle": "MP04GH7890"},
    {"name": "Sanjay Mehta", "phone": "9456789012", "vehicle": None},
]

LOCATIONS = ["Malviya Nagar", "Rajwada", "Vijay Nagar", "Bhawarkuan", "Sudama Nagar"]

ORGS = ["Shree Traders", "Om Logistics", "Balaji Enterprises"]

# ---- 1. Synthetic FIR-style text reports -------------------------------
fir_templates = [
    "Suspect {p1} was seen near {loc} with vehicle {veh}, contacted {phone}.",
    "Complainant reported {p1} and {p2} meeting near {loc} on suspicious grounds.",
    "{p1} allegedly linked to {org}, frequently seen at {loc}.",
    "Informant states {p1} received a call from {phone2} while at {loc}.",
    "{p1} aur {p2} {loc} mein mile the, dono ka phone number record kiya gaya hai.",
]

fir_reports = []
for i in range(25):
    p1, p2 = random.sample(PEOPLE, 2)
    loc = random.choice(LOCATIONS)
    org = random.choice(ORGS)
    template = random.choice(fir_templates)
    text = template.format(
        p1=p1["name"], p2=p2["name"], loc=loc,
        veh=p1["vehicle"] or "unknown", phone=p1["phone"],
        phone2=p2["phone"], org=org
    )
    fir_reports.append({"doc_id": f"FIR-{1000+i}", "text": text, "date": str(datetime(2026,7,1) + timedelta(days=i))})

with open("fir_reports.json", "w") as f:
    json.dump(fir_reports, f, indent=2)

# ---- 2. Synthetic CDR (Call Detail Records) ----------------------------
with open("cdr.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["caller_number", "receiver_number", "timestamp", "duration_sec", "tower_location"])
    base_time = datetime(2026, 7, 1)
    for i in range(200):
        caller, receiver = random.sample(PEOPLE, 2)
        # occasionally make one number call very frequently -> anomaly signal
        if i % 15 == 0:
            caller = PEOPLE[0]
        ts = base_time + timedelta(minutes=random.randint(0, 40000))
        writer.writerow([caller["phone"], receiver["phone"], ts.isoformat(),
                          random.randint(10, 900), random.choice(LOCATIONS)])

# ---- 3. Synthetic financial transactions -------------------------------
with open("transactions.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sender_name", "receiver_name", "amount", "timestamp", "transaction_type"])
    base_time = datetime(2026, 7, 1)
    for i in range(120):
        sender, receiver = random.sample(PEOPLE, 2)
        # structuring pattern: repeated amounts just under 50,000 threshold
        if i % 10 == 0:
            amount = random.randint(45000, 49999)
        else:
            amount = random.randint(500, 40000)
        ts = base_time + timedelta(hours=random.randint(0, 700))
        writer.writerow([sender["name"], receiver["name"], amount, ts.isoformat(),
                          random.choice(["UPI", "NEFT", "CASH"])])

# ---- 4. Ground-truth entity map (for validating entity resolution later)
with open("ground_truth_entities.json", "w") as f:
    json.dump(PEOPLE, f, indent=2)

print(f"Generated {len(fir_reports)} FIR reports, 200 CDR rows, 120 transactions.")
print("Files: fir_reports.json, cdr.csv, transactions.csv, ground_truth_entities.json")
