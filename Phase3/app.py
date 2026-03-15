import streamlit as st
import json
import os
import sys
import pandas as pd
from datetime import datetime

# Add parent directory to path for imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, ".."))

from Phase1.scraper import fetch_reviews, save_reviews
from Phase2.analyzer import GeminiAnalyzer
from Phase4.email_generator import generate_html_email
from Phase4.mailer import send_pulse_email
from dotenv import load_dotenv

# Page configuration
st.set_page_config(
    page_title="INDMoney Weekly Pulse",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for INDMoney-themed look
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main {
        background-color: #F8FAFC;
        padding-top: 2rem;
    }

    /* Global Card styling */
    .stMetric, .theme-card, .quote-card, .action-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 20px;
    }

    /* INDMoney Specific Accents */
    .stButton>button {
        background-color: #00b8b0;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        border: none;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #009993;
        border: none;
        color: white;
        transform: translateY(-1px);
    }

    .theme-card {
        border-left: 6px solid #00b8b0;
    }

    .quote-card {
        font-style: italic;
        color: #334155;
        border-left: 4px solid #1a365d;
        background-color: #F1F5F9;
    }

    .action-card {
        background-color: #F0FDFA;
        border-color: #00b8b0;
    }

    h1, h2, h3 {
        color: #0F172A;
        font-weight: 700;
    }

    .stMetric label {
        color: #64748B !important;
        font-weight: 500 !important;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }

    .sync-badge {
        background-color: #E0F2FE;
        color: #0284C7;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

def load_local_data():
    """Loads existing reviews and analyzer report if they exist."""
    reviews_data = []
    report = None

    if os.path.exists("../reviews.json"):
        with open("../reviews.json", "r", encoding="utf-8") as f:
            reviews_data = json.load(f)

    if os.path.exists("../Phase2/pulse_report.json"):
        with open("../Phase2/pulse_report.json", "r", encoding="utf-8") as f:
            report = json.load(f)

    return reviews_data, report

def main():
    # Load existing data on startup
    load_dotenv()
    existing_reviews, existing_report = load_local_data()

    # Initialize session state from files if not already set
    if 'report' not in st.session_state and existing_report:
        st.session_state['report'] = existing_report

    if 'reviews_count' not in st.session_state:
        st.session_state['reviews_count'] = len(existing_reviews)

    if 'avg_rating' not in st.session_state:
        st.session_state['avg_rating'] = pd.DataFrame(existing_reviews)['rating'].mean() if existing_reviews else 0

    st.sidebar.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <div style="background-color: #1a365d; width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; margin-right: 12px;">
                <span style="color: white; font-weight: 800; font-size: 20px;">I</span>
            </div>
            <h2 style="margin: 0; font-size: 24px; color: #0F172A;">INDMoney Pulse</h2>
        </div>
    """, unsafe_allow_html=True)

    app_id = st.sidebar.text_input("App ID", value="in.indwealth")
    weeks = st.sidebar.slider("Weeks to analyze", 1, 12, 12)

    # Debug Info (Small)
    st.sidebar.markdown(f"""
        <div style="font-size: 0.7em; color: #64748B; margin-top: 20px;">
            Local Data: {'Found' if os.path.exists('../reviews.json') else 'Not Found'}<br>
            App ID: {app_id}
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="sync-badge">Last Synced: {datetime.now().strftime("%I:%M %p")}</div>', unsafe_allow_html=True)
    st.title("Weekly Pulse Report")
    st.markdown("<p style='color: #64748B; margin-top: -10px;'>High-impact insights from user feedback.</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Check for API Key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.sidebar.warning("No Gemini API Key found in `.env`")

    if st.sidebar.button("Sync & Analyze"):
        with st.spinner("Fetching latest reviews..."):
            reviews_data = fetch_reviews(app_id=app_id, weeks=weeks)
            save_reviews(reviews_data, filename="../reviews.json")

            if not reviews_data:
                st.sidebar.error("No reviews found matching filters. (Try increasing 'Weeks' or check App ID)")
            else:
                st.sidebar.success(f"Fetched {len(reviews_data)} high-quality reviews!")

        if api_key:
            with st.spinner("Analyzing with Gemini AI..."):
                analyzer = GeminiAnalyzer(api_key=api_key)
                report = analyzer.analyze_reviews(reviews_data)

                # Save report to Phase 2 directory as per architecture
                report_path = os.path.join("..", "Phase2", "pulse_report.json")
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=4)

                st.session_state['report'] = report
        else:
            st.error("Cannot run AI analysis without Gemini API Key.")

        st.session_state['reviews_count'] = len(reviews_data)
        st.session_state['avg_rating'] = pd.DataFrame(reviews_data)['rating'].mean() if reviews_data else 0

    # Display Report
    if 'report' in st.session_state:
        report = st.session_state['report']

        # Executive Summary
        if "pulse_summary" in report:
            st.markdown(f"""
            <div style="background-color: #F8FAFC; padding: 20px; border-radius: 10px; border-left: 5px solid #1a365d; margin-bottom: 25px;">
                <h4 style="margin-top: 0; color: #1a365d;">Executive Summary</h4>
                <p style="font-size: 1.1em; color: #334155;">{report['pulse_summary']}</p>
            </div>
            """, unsafe_allow_html=True)

        # Top Stats
        col1, col2, col3 = st.columns(3)
        reviews_count = st.session_state.get('reviews_count', 0)
        avg_rating = st.session_state.get('avg_rating', 0)
        pulse_date = datetime.now().strftime("%d %b, %Y")

        with col1:
            st.markdown(f"""
                <div class="stMetric">
                    <div style="color: #64748B; font-size: 0.9em; font-weight: 500; margin-bottom: 8px;">Total Reviews Analyzed</div>
                    <div style="color: #0F172A; font-size: 2.2em; font-weight: 700;">{reviews_count}</div>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="stMetric">
                    <div style="color: #64748B; font-size: 0.9em; font-weight: 500; margin-bottom: 8px;">Average Rating</div>
                    <div style="color: #0F172A; font-size: 2.2em; font-weight: 700;">{avg_rating:.2f}</div>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div class="stMetric">
                    <div style="color: #64748B; font-size: 0.9em; font-weight: 500; margin-bottom: 8px;">Pulse Date</div>
                    <div style="color: #0F172A; font-size: 1.8em; font-weight: 700; white-space: nowrap;">{pulse_date}</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("### Top Feedback Themes")
        themes = report.get('themes', [])
        if themes:
            theme_cols = st.columns(len(themes))
            for i, theme in enumerate(themes):
                sentiment = theme.get('sentiment', 'Neutral')
                border_colors = {
                    "Positive": "#22C55E",
                    "Negative": "#EF4444",
                    "Neutral": "#F59E0B"
                }
                border = border_colors.get(sentiment, "#94A3B8")

                with theme_cols[i]:
                    st.markdown(f"""
                    <div style="background-color: #FFFFFF; padding: 24px; border-radius: 16px; border: 1px solid #E2E8F0; border-top: 6px solid {border}; height: 100%; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                        <h4 style="margin-top: 0; color: #0F172A; margin-bottom: 8px;">{theme['name']}</h4>
                        <p style="color: #475569; font-size: 0.9em; line-height: 1.5;">{theme['description']}</p>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px; border-top: 1px solid #F1F5F9; padding-top: 12px;">
                            <span style="font-weight: 600; color: {border}; font-size: 0.85em;">{sentiment.upper()}</span>
                            <span style="color: #64748B; font-size: 0.8em; font-weight: 500;">Impact: {theme.get('impact_score', 'N/A')}/10</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### User Voices")
            for quote in report.get('top_quotes', []):
                st.markdown(f"""
                <div class="quote-card">
                    "{quote}"
                </div>
                """, unsafe_allow_html=True)

        with col_right:
            st.markdown("### Growth Roadmap")
            for idea in report.get('action_ideas', []):
                st.markdown(f"""
                <div class="action-card">
                    <span style="color: #00b8b0; font-weight: 700; margin-right: 8px;">-</span> {idea}
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("Generate Premium HTML Email"):
            with st.spinner("Generating premium draft..."):
                st.success("Premium HTML email draft generated!")
                html_email = generate_html_email(report)
                st.session_state['last_html_email'] = html_email

                # Save for Phase 4 records
                with open("../Phase4/email_draft.html", "w", encoding="utf-8") as f:
                    f.write(html_email)

        if 'last_html_email' in st.session_state:
            html_email = st.session_state['last_html_email']
            st.markdown("---")
            st.write("### Email Preview")
            st.components.v1.html(html_email, height=600, scrolling=True)

            with st.expander("View Source HTML"):
                st.code(html_email, language="html")

            st.markdown("---")
            if st.button("Send Pulse to My Email"):
                with st.spinner("Sending email..."):
                    base_dir = os.path.dirname(os.path.abspath(__file__))

                    reviews_json_path = os.path.join(base_dir, "..", "reviews.json")
                    attachment_path = os.path.join(base_dir, "..", "reviews_report.csv")

                    if os.path.exists(reviews_json_path):
                        with open(reviews_json_path, "r", encoding="utf-8") as f:
                            reviews_data = json.load(f)

                        # Sanitize: Remove PII
                        df = pd.DataFrame(reviews_data)
                        cols_to_keep = ['content', 'rating', 'at', 'thumbs_up', 'version']
                        df_sanitized = df[[c for c in cols_to_keep if c in df.columns]]
                        df_sanitized.to_csv(attachment_path, index=False, encoding='utf-8-sig')

                    result = send_pulse_email(
                        st.session_state['last_html_email'],
                        attachment_path=attachment_path,
                        preamble="Hi Team, your weekly INDMoney review pulse is ready, highlighting key users' feedback and issues to focus on."
                    )

                    if isinstance(result, tuple):
                        success, message = result
                    else:
                        success = result
                        message = "Check SMTP settings in .env" if not success else "Success"

                    if success:
                        st.success(f"Pulse sent to {os.getenv('RECIPIENT_EMAIL')}!")
                    else:
                        st.error(f"Failed to send email: {message}")
                        st.info("Ensure you are using a Google App Password and your .env is correctly saved.")

if __name__ == "__main__":
    main()
