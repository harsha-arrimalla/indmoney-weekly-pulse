import os
import json
from dotenv import load_dotenv

# Load environment variables from root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Common prompt template
PULSE_PROMPT_TEMPLATE = """
You are an expert product analyst at INDMoney. Your task is to transform {sample_size} user reviews into a high-impact 'Weekly Pulse' report.

Input Data:
{reviews_text}

Required Tasks:
1. Theme Generation: Identify 3-5 recurring themes (pain points, feature requests, or praise).
2. Review Sorting: For each theme, provide a concise summary of what users are saying.
3. Sentiment Analysis: Determine if the overall sentiment for each theme is Positive, Negative, or Neutral.
4. User Voices: Extract 3 verbatim quotes that are most representative of the general sentiment.
5. Growth Roadmap: Generate 3 actionable ideas for the Product/Growth teams.

Response Format (Strict JSON):
{{
    "pulse_summary": "A 2-sentence executive summary of this week's app health.",
    "themes": [
        {{
            "name": "Theme Title",
            "description": "Elaborate on what users are specifically experiencing under this theme.",
            "sentiment": "Positive/Negative/Neutral",
            "impact_score": 1-10
        }}
    ],
    "top_quotes": [
        "Quote 1",
        "Quote 2",
        "Quote 3"
    ],
    "action_ideas": [
        "Strategic Idea 1",
        "Strategic Idea 2",
        "Strategic Idea 3"
    ]
}}

Strict Guidelines:
- DO NOT include any PII (names, phone numbers, emails).
- If a quote contains PII, redact it (e.g., [Name]).
- Output ONLY the raw JSON.
"""


def _prepare_reviews(reviews_data):
    """Prepare review text for the prompt."""
    sample_size = min(len(reviews_data), 150)
    reviews_for_ai = [
        f"ID: {r.get('review_id')} | Rating: {r['rating']} | Content: {r['content']}"
        for r in reviews_data[:sample_size]
    ]
    reviews_text = "\n---\n".join(reviews_for_ai)
    return sample_size, reviews_text


def _clean_json_response(text_content):
    """Strip markdown fencing if present."""
    if text_content.startswith("```json"):
        text_content = text_content[7:]
    if text_content.startswith("```"):
        text_content = text_content[3:]
    if text_content.endswith("```"):
        text_content = text_content[:-3]
    return json.loads(text_content.strip())


class GroqAnalyzer:
    """Primary analyzer using Groq (Llama 3.3 70B)."""

    def __init__(self, api_key=None):
        from groq import Groq
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key not found. Please set GROQ_API_KEY in .env file.")
        self.client = Groq(api_key=self.api_key)

    def analyze_reviews(self, reviews_data):
        sample_size, reviews_text = _prepare_reviews(reviews_data)
        prompt = PULSE_PROMPT_TEMPLATE.format(sample_size=sample_size, reviews_text=reviews_text)

        completion = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional Product Analyst at a top fintech company."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)


class GeminiAnalyzer:
    """Fallback analyzer using Google Gemini."""

    def __init__(self, api_key=None):
        import google.generativeai as genai
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key not found. Please set GOOGLE_API_KEY in .env file.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            'gemini-2.0-flash',
            generation_config={"response_mime_type": "application/json"}
        )

    def analyze_reviews(self, reviews_data):
        sample_size, reviews_text = _prepare_reviews(reviews_data)
        prompt = PULSE_PROMPT_TEMPLATE.format(sample_size=sample_size, reviews_text=reviews_text)

        response = self.model.generate_content(prompt)
        return _clean_json_response(response.text)


def get_analyzer(groq_key=None, gemini_key=None):
    """Returns the best available analyzer: Groq first, Gemini as fallback."""
    groq_key = groq_key or os.getenv("GROQ_API_KEY")
    gemini_key = gemini_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    if groq_key:
        return GroqAnalyzer(api_key=groq_key)
    elif gemini_key:
        return GeminiAnalyzer(api_key=gemini_key)
    else:
        raise ValueError("No API key found. Set GROQ_API_KEY or GOOGLE_API_KEY in .env file.")


if __name__ == "__main__":
    try:
        with open('../reviews.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        analyzer = get_analyzer()
        report = analyzer.analyze_reviews(data)

        with open('pulse_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4)

        print(f"Pulse report generated using {type(analyzer).__name__}")
    except Exception as e:
        print(f"Error: {e}")
