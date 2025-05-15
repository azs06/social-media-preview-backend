import os
import google.generativeai as genai
from flask import Blueprint, request, jsonify
import json # Import json for safer parsing
import re # Import re for fallback score extraction

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Configure the Gemini API key
try:
    # Attempt to load .env if it exists (for local development)
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    
    gemini_api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    if not gemini_api_key:
        print("Warning: GOOGLE_GEMINI_API_KEY not found in environment variables. AI scoring will not work.")
    else:
        genai.configure(api_key=gemini_api_key)
except ImportError:
    # dotenv not installed, try to get key directly (for production environments where .env might not be used)
    gemini_api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    if not gemini_api_key:
        print("Warning: GOOGLE_GEMINI_API_KEY not found and python-dotenv not installed. AI scoring will not work.")
    else:
        genai.configure(api_key=gemini_api_key)
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    gemini_api_key = None # Ensure it's None if configuration fails

@api_bp.route("/score_post", methods=["POST"])
def score_post():
    if not gemini_api_key:
        return jsonify({"error": "AI scoring is currently unavailable. API key not configured or configuration failed."}), 503

    try:
        data = request.get_json()
        if not data or "post_text" not in data or "platform" not in data:
            return jsonify({"error": "Missing post_text or platform in request"}), 400

        post_text = data["post_text"]
        platform = data["platform"]

        if not post_text.strip():
            return jsonify({"error": "Post content cannot be empty."}), 400

        model = genai.GenerativeModel("gemini-1.5-flash-latest")

        prompt = f"""
Analyze the following social media post intended for {platform.capitalize()}.

Post content:"{post_text}"
Provide a performance score from 0 to 100 based on the following criteria:
1.  Engagement Potential (likes, comments, shares).
2.  Clarity (clear, concise, understandable).
3.  Message Quality (valuable, informative, or entertaining for {platform.capitalize()}).
4.  Hashtag Effectiveness (relevance, visibility, or if beneficial if absent).

Return your response ONLY as a valid JSON object with two keys: "score" (an integer between 0 and 100) and "feedback" (a brief string, max 150 characters, explaining the score and offering 1-2 concise improvement suggestions).

Example JSON Response:
{{
  "score": 85,
  "feedback": "Great clarity. Consider adding a question to boost engagement."
}}
"""

        response = model.generate_content(prompt)
        
        cleaned_response_text = response.text.strip()
        # Remove markdown JSON block delimiters if present
        if cleaned_response_text.startswith("```json"):
            cleaned_response_text = cleaned_response_text[7:]
        if cleaned_response_text.endswith("```"):
            cleaned_response_text = cleaned_response_text[:-3]
        cleaned_response_text = cleaned_response_text.strip() # Ensure no leading/trailing whitespace

        try:
            # Use json.loads for safer and more standard JSON parsing
            result_data = json.loads(cleaned_response_text)
            if not isinstance(result_data.get("score"), int) or not (0 <= result_data.get("score") <= 100):
                raise ValueError("Score is not a valid integer between 0 and 100.")
            if not isinstance(result_data.get("feedback"), str):
                raise ValueError("Feedback is not a string.")
            return jsonify(result_data), 200
        except (json.JSONDecodeError, ValueError) as parse_error:
            print(f"Error parsing Gemini response as JSON: {parse_error}. Raw text: [{response.text}] Cleaned text: [{cleaned_response_text}]")
            # Fallback: try to extract score with regex, provide generic feedback
            score_match = re.search(r'"score":\s*(\d+)', cleaned_response_text)
            score = int(score_match.group(1)) if score_match and (0 <= int(score_match.group(1)) <= 100) else 50
            feedback_text = "AI analysis was partially successful. Could not fully parse detailed feedback from the AI. Please try rephrasing your post."
            
            # Try to extract feedback if a score was found
            if score_match:
                feedback_match = re.search(r'"feedback":\s*"(.*?)"', cleaned_response_text, re.DOTALL)
                if feedback_match:
                    feedback_text = feedback_match.group(1).strip()
            
            return jsonify({"score": score, "feedback": feedback_text}), 200 # Still return 200 but with fallback data

    except genai.types.generation_types.BlockedPromptException as bpe:
        print(f"Gemini API request blocked: {bpe}")
        return jsonify({"error": "Your request was blocked by the AI for safety reasons. Please modify your post content."}), 400
    except Exception as e:
        print(f"An unexpected error occurred in /score_post: {e}")
        return jsonify({"error": "An unexpected error occurred while scoring the post."}), 500


