import json
import os
from datetime import datetime, timedelta
from google_play_scraper import Sort, reviews
import pandas as pd
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# For consistent results
DetectorFactory.seed = 0

def is_english(text):
    try:
        return detect(text) == 'en'
    except LangDetectException:
        return False

def fetch_reviews(app_id='in.indwealth', weeks=12):
    """
    Fetches reviews for the given app_id from the last N weeks.
    Includes filters: 10+ words, no emojis, English only, no duplicates.
    """
    print(f"Fetching reviews for {app_id}...")

    # Calculate the date limit
    limit_date = datetime.now() - timedelta(weeks=weeks)

    all_reviews = []
    seen_review_ids = set()
    continuation_token = None

    # Fetch reviews in batches
    while True:
        result, continuation_token = reviews(
            app_id,
            lang='en', # language
            country='in', # country
            sort=Sort.NEWEST, # newest first
            count=100, # batch size
            continuation_token=continuation_token
        )

        # Filter by date and quality
        for review in result:
            review_date = review['at']
            if review_date < limit_date:
                # We've reached reviews older than our limit
                print(f"Reached limit date: {review_date}")
                return all_reviews

            review_id = review['reviewId']
            content = review['content'] or ""

            # 1. Duplicate Filter
            if review_id in seen_review_ids:
                continue

            # 2. Quality Filter: 10+ words
            word_count = len(content.split())
            if word_count < 10:
                continue

            # 3. Quality Filter: No emojis
            has_emoji = any(ord(char) > 0xffff for char in content)
            if has_emoji:
                continue

            # 4. Language Filter: English only
            if not is_english(content):
                continue

            # Store relevant fields
            all_reviews.append({
                'review_id': review_id,
                'user_name': review['userName'],
                'content': content,
                'rating': review['score'],
                'thumbs_up': review['thumbsUpCount'],
                'version': review['reviewCreatedVersion'],
                'at': review['at'].isoformat(),
                'reply': review['replyContent'],
                'replied_at': review['repliedAt'].isoformat() if review['repliedAt'] else None
            })
            seen_review_ids.add(review_id)

            # Stop once we have exactly 500 reviews
            if len(all_reviews) >= 500:
                print(f"Reached target dataset size: {len(all_reviews)}")
                return all_reviews

        print(f"Fetched {len(all_reviews)} high-quality reviews so far...")

        if not continuation_token:
            break

    return all_reviews

def save_reviews(reviews_data, filename=None):
    if filename is None:
        # Default to reviews.json in the current working directory
        filename = 'reviews.json'

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(reviews_data, f, ensure_ascii=False, indent=4)
    print(f"Saved {len(reviews_data)} reviews to {os.path.abspath(filename)}")

if __name__ == "__main__":
    # Test fetch for INDmoney
    reviews_list = fetch_reviews(weeks=12)
    save_reviews(reviews_list)

    # Simple summary
    if reviews_list:
        df = pd.DataFrame(reviews_list)
        print("\nSummary Statistics:")
        print(f"Total Reviews: {len(df)}")
        print(f"Average Rating: {df['rating'].mean():.2f}")
        print("\nSuccessfully fetched, filtered, and saved data.")
