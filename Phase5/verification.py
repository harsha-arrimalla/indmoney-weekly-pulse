import json
import os
import re

def verify_pipeline():
    print("[*] Starting INDMoney Weekly Pulse Verification...")

    # 1. Check Phase 1: Data
    reviews_path = "../reviews.json"
    if os.path.exists(reviews_path):
        with open(reviews_path, "r", encoding="utf-8") as f:
            reviews = json.load(f)
            print(f"[OK] Phase 1: Found {len(reviews)} reviews in reviews.json")
            if len(reviews) > 0:
                # Check for emojis in content (simple check)
                emoji_pattern = re.compile("[\U00010000-\U0010ffff]", flags=re.UNICODE)
                has_emoji = any(emoji_pattern.search(r['content']) for r in reviews[:100])
                if not has_emoji:
                    print("     [OK] Cleaned data looks emoji-free (sampled).")
    else:
        print("[FAIL] Phase 1: reviews.json NOT found.")

    # 2. Check Phase 2: AI Report
    report_path = "../Phase2/pulse_report.json"
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
            required_keys = ["pulse_summary", "themes", "top_quotes", "action_ideas"]
            if all(k in report for k in required_keys):
                print("[OK] Phase 2: AI Pulse Report is valid and contains all architectural components.")
                # PII Check (Basic)
                pii_risk = False
                for quote in report['top_quotes']:
                    if re.search(r'\d{10}', quote): pii_risk = True
                if not pii_risk:
                    print("     [OK] Basic PII safety check passed.")
            else:
                print("[FAIL] Phase 2: AI Pulse Report is missing required fields.")
    else:
        print("[FAIL] Phase 2: pulse_report.json NOT found.")

    # 3. Check Phase 4: Email
    email_path = "../Phase4/email_draft.html"
    if os.path.exists(email_path):
        print("[OK] Phase 4: Premium HTML Email draft found.")
    else:
        print("[FAIL] Phase 4: email_draft.html NOT found.")

    print("\nSystem Verification Complete!")

if __name__ == "__main__":
    verify_pipeline()
