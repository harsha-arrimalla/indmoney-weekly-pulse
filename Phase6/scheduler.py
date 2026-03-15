import os
import sys
import json
import time
from datetime import datetime

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Phase1.scraper import fetch_reviews, save_reviews
from Phase2.analyzer import get_analyzer
from Phase4.email_generator import generate_html_email
from Phase4.mailer import send_pulse_email
import pandas as pd
from dotenv import load_dotenv

def run_weekly_pulse():
    print(f"\n--- Starting Scheduled Pulse: {datetime.now()} ---")
    load_dotenv()

    try:
        # Phase 1: Scrape
        print("[1/4] Fetching latest reviews...")
        reviews = fetch_reviews(app_id="in.indwealth", weeks=12)
        save_reviews(reviews)

        # Phase 2: Analyze
        print("[2/4] Analyzing with AI...")
        analyzer = get_analyzer()
        report = analyzer.analyze_reviews(reviews)

        report_path = os.path.join(os.path.dirname(__file__), '..', 'Phase2', 'pulse_report.json')
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)

        # Phase 4.1: Generate Email
        print("[3/4] Generating HTML report...")
        html = generate_html_email(report)

        # Prepare attachments
        print("[4/4] Dispatching email with Excel-friendly attachment...")

        # Save as CSV for better previewing (Sanitized)
        df = pd.DataFrame(reviews)
        cols_to_keep = ['content', 'rating', 'at', 'thumbs_up', 'version']
        df_sanitized = df[[c for c in cols_to_keep if c in df.columns]]

        csv_path = os.path.join(os.path.dirname(__file__), '..', 'reviews_report.csv')
        df_sanitized.to_csv(csv_path, index=False, encoding='utf-8-sig')

        success, message = send_pulse_email(
            html,
            attachment_path=csv_path,
            preamble="Hi Team, your weekly INDMoney review pulse is ready, highlighting key users' feedback and issues to focus on."
        )

        if success:
            print("[OK] Weekly Pulse successfully sent!")
        else:
            print("[FAIL] Pipeline completed but email failed to send.")

    except Exception as e:
        print(f"[ERROR] Critical Error in Scheduler: {e}")

if __name__ == "__main__":
    # If run directly, execute immediately
    run_weekly_pulse()
