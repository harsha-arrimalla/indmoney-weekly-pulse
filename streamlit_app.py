import streamlit as st
import json
import os
import sys
import pandas as pd
from datetime import datetime
from Phase1.scraper import fetch_reviews, save_reviews
from Phase2.analyzer import get_analyzer
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
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
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
        box-shadow: 0 4px 12px rgba(0, 184, 176, 0.2);
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
        display: inline-block;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

def load_local_data():
    """Loads existing reviews and analyzer report if they exist."""
    reviews_data = []
    report = None

    # Paths relative to root
    reviews_path = "reviews.json"
    report_path = os.path.join("Phase2", "pulse_report.json")

    if os.path.exists(reviews_path):
        with open(reviews_path, "r", encoding="utf-8") as f:
            reviews_data = json.load(f)

    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

    return reviews_data, report

def get_secret(key, default=None):
    """Helper to get secret from st.secrets or environment variable."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)

def main():
    # Load environment variables if .env exists (local run)
    if os.path.exists(".env"):
        load_dotenv()

    # Load existing data on startup
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

    st.sidebar.markdown('<p style="color: #0F172A; font-weight: 600; margin-bottom: 0;">Play Store App ID</p>', unsafe_allow_html=True)
    app_id = st.sidebar.text_input("App ID", value="in.indwealth", label_visibility="collapsed")
    st.sidebar.markdown('<p style="color: #0F172A; font-weight: 600; margin-bottom: 0;">Review Period (weeks)</p>', unsafe_allow_html=True)
    weeks = st.sidebar.slider("Weeks to analyze", 1, 12, 12, label_visibility="collapsed", help="How many weeks of reviews to fetch and analyze")

    # Debug Info (Small)
    st.sidebar.markdown(f"""
        <div style="font-size: 0.7em; color: #64748B; margin-top: 20px;">
            Local Data: {'Found' if os.path.exists('reviews.json') else 'Not Found'}<br>
            App ID: {app_id}
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="sync-badge">Last Synced: {datetime.now().strftime("%I:%M %p")}</div>', unsafe_allow_html=True)
    st.title("Weekly Pulse Report")
    st.markdown("<p style='color: #64748B; margin-top: -10px; font-size: 1.1em;'>High-impact insights from user feedback.</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Check for API Keys (Secrets compatible)
    groq_key = get_secret("GROQ_API_KEY")
    gemini_key = get_secret("GOOGLE_API_KEY") or get_secret("GEMINI_API_KEY")
    has_api_key = groq_key or gemini_key

    if not has_api_key:
        st.sidebar.warning("No API Key found. Set GROQ_API_KEY or GOOGLE_API_KEY in Streamlit Secrets or .env")

    if st.sidebar.button("Sync & Analyze"):
        with st.spinner("Fetching latest reviews..."):
            reviews_data = fetch_reviews(app_id=app_id, weeks=weeks)
            # Save to standard root path
            save_reviews(reviews_data, filename="reviews.json")

            if not reviews_data:
                st.sidebar.error("No reviews found matching filters. (Try increasing 'Weeks' or check App ID)")
            else:
                st.sidebar.success(f"Fetched {len(reviews_data)} high-quality reviews!")

        if has_api_key:
            provider = "Groq" if groq_key else "Gemini"
            with st.spinner(f"Analyzing with {provider} AI..."):
                try:
                    analyzer = get_analyzer(groq_key=groq_key, gemini_key=gemini_key)
                    report = analyzer.analyze_reviews(reviews_data)

                    # Save report
                    report_path = os.path.join("Phase2", "pulse_report.json")
                    os.makedirs(os.path.dirname(report_path), exist_ok=True)
                    with open(report_path, "w", encoding="utf-8") as f:
                        json.dump(report, f, indent=4)

                    st.session_state['report'] = report
                except Exception as e:
                    st.error(f"Error analyzing with {provider} AI: {e}")
        else:
            st.error("Cannot run AI analysis without an API Key.")

        st.session_state['reviews_count'] = len(reviews_data)
        st.session_state['avg_rating'] = pd.DataFrame(reviews_data)['rating'].mean() if reviews_data else 0

    # Display Report
    if 'report' in st.session_state:
        report = st.session_state['report']

        # Executive Summary
        if "pulse_summary" in report:
            st.markdown(f"""
            <div style="background-color: #F8FAFC; padding: 24px; border-radius: 12px; border-left: 6px solid #1a365d; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                <h4 style="margin-top: 0; color: #1a365d; font-size: 1.2em; font-weight: 700;">Executive Summary</h4>
                <p style="font-size: 1.1em; color: #334155; line-height: 1.6;">{report['pulse_summary']}</p>
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
                    <div style="color: #64748B; font-size: 0.9em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Total Reviews Analyzed</div>
                    <div style="color: #0F172A; font-size: 2.5em; font-weight: 800; letter-spacing: -0.02em;">{reviews_count}</div>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="stMetric">
                    <div style="color: #64748B; font-size: 0.9em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Average Rating</div>
                    <div style="color: #0F172A; font-size: 2.5em; font-weight: 800; letter-spacing: -0.02em;">{avg_rating:.2f}</div>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div class="stMetric">
                    <div style="color: #64748B; font-size: 0.9em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Pulse Date</div>
                    <div style="color: #0F172A; font-size: 1.8em; font-weight: 800; letter-spacing: -0.02em; padding-top: 8px; white-space: nowrap;">{pulse_date}</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("### Top Feedback Themes")
        themes = report.get('themes', [])
        if themes:
            theme_cols = st.columns(len(themes))
            for i, theme in enumerate(themes):
                sentiment = theme.get('sentiment', 'Neutral')
                sentiment_colors = {
                    "Positive": "#F0FDF4",
                    "Negative": "#FEF2F2",
                    "Neutral": "#FFFBEB"
                }
                border_colors = {
                    "Positive": "#22C55E",
                    "Negative": "#EF4444",
                    "Neutral": "#F59E0B"
                }
                bg = sentiment_colors.get(sentiment, "#F8FAFC")
                border = border_colors.get(sentiment, "#94A3B8")

                with theme_cols[i]:
                    st.markdown(f"""
                    <div style="background-color: #FFFFFF; padding: 24px; border-radius: 16px; border: 1px solid #E2E8F0; border-top: 6px solid {border}; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); transition: transform 0.2s;">
                        <h4 style="margin-top: 0; color: #0F172A; margin-bottom: 12px; font-size: 1.1em;">{theme['name']}</h4>
                        <p style="color: #475569; font-size: 0.95em; line-height: 1.5;">{theme['description']}</p>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 20px; border-top: 1px solid #F1F5F9; padding-top: 16px;">
                            <span style="font-weight: 700; color: {border}; font-size: 0.85em; background-color: {bg}; padding: 4px 12px; border-radius: 20px;">{sentiment.upper()}</span>
                            <span style="color: #64748B; font-size: 0.85em; font-weight: 600; background-color: #F1F5F9; padding: 4px 10px; border-radius: 6px;">Impact: {theme.get('impact_score', 'N/A')}/10</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### Voice of the User")
            for quote in report.get('top_quotes', []):
                st.markdown(f"""
                <div class="quote-card">
                    <span style="font-size: 1.2em; color: #94A3B8; margin-right: 4px;">"</span>{quote}<span style="font-size: 1.2em; color: #94A3B8; margin-left: 4px;">"</span>
                </div>
                """, unsafe_allow_html=True)

        with col_right:
            st.markdown("### Strategic Roadmap")
            for idea in report.get('action_ideas', []):
                st.markdown(f"""
                <div class="action-card">
                    <div style="display: flex; align-items: flex-start;">
                        <span style="color: #00b8b0; font-weight: 800; font-size: 1.2em; margin-right: 12px; line-height: 1.2;">-</span>
                        <span style="color: #1E293B; font-size: 1.05em; font-weight: 500; line-height: 1.5;">{idea}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        col_email_1, col_email_2 = st.columns([1, 1])
        with col_email_1:
            if st.button("Generate Premium HTML Email"):
                with st.spinner("Generating premium draft..."):
                    html_email = generate_html_email(report)
                    st.session_state['last_html_email'] = html_email

                    # Save for Phase 4 records
                    email_draft_path = os.path.join("Phase4", "email_draft.html")
                    os.makedirs(os.path.dirname(email_draft_path), exist_ok=True)
                    with open(email_draft_path, "w", encoding="utf-8") as f:
                        f.write(html_email)
                    st.success("Premium HTML email draft generated & saved to Phase4/email_draft.html!")

        if 'last_html_email' in st.session_state:
            html_email = st.session_state['last_html_email']
            st.markdown("---")
            st.write("### Email Preview")
            st.components.v1.html(html_email, height=600, scrolling=True)

            with st.expander("View Source HTML"):
                st.code(html_email, language="html")

            st.markdown("---")
            st.markdown("### Dispatch Pulse")

            # Simple form to send email
            with st.form("send_email_form"):
                recipient_email = st.text_input("Recipient Email", value=get_secret('RECIPIENT_EMAIL', ''))
                submit_button = st.form_submit_button("Send Pulse to Email")

                if submit_button:
                    with st.spinner("Sending email..."):
                        # Standard paths in root
                        reviews_json_path = "reviews.json"
                        attachment_path = "reviews_report.csv"

                        if os.path.exists(reviews_json_path):
                            with open(reviews_json_path, "r", encoding="utf-8") as f:
                                reviews_data = json.load(f)

                            # Sanitize: Remove PII (userName, reviewId)
                            df = pd.DataFrame(reviews_data)
                            cols_to_keep = ['content', 'rating', 'at', 'thumbs_up', 'version']
                            df_sanitized = df[[c for c in cols_to_keep if c in df.columns]]
                            df_sanitized.to_csv(attachment_path, index=False, encoding='utf-8-sig')

                        # Temporarily override environment var for the mailer if set
                        if recipient_email:
                            os.environ["RECIPIENT_EMAIL"] = recipient_email

                        try:
                            result = send_pulse_email(
                                st.session_state['last_html_email'],
                                attachment_path=attachment_path,
                                preamble="Hi Team, your weekly INDMoney review pulse is ready, highlighting key users' feedback and issues to focus on."
                            )

                            if isinstance(result, tuple):
                                success, message = result
                            else:
                                success = result
                                message = "Check SMTP settings" if not success else "Success"

                            if success:
                                st.success(f"Pulse sent successfully to {recipient_email}!")
                            else:
                                st.error(f"Failed to send email: {message}")
                        except ValueError:
                            st.error("SMTP not configured. Add SMTP_SERVER, SENDER_EMAIL, SENDER_PASSWORD, and RECIPIENT_EMAIL to your Streamlit Secrets or .env file.")
                        except Exception as e:
                            st.error(f"Failed to send email: {e}")

if __name__ == "__main__":
    main()
