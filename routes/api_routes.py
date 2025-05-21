import os
import google.generativeai as genai
from flask import Blueprint, request, jsonify
import json # Import json for safer parsing
import re # Import re for fallback score extraction
import base64
import io

# Attempt to import Pillow (PIL)
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow (PIL) library not installed. Image processing features will be disabled.")

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
        if not data:
            return jsonify({"error": "Invalid JSON payload."}), 400
        
        post_text = data.get("post_text")
        platform = data.get("platform")
        image_base64 = data.get("image_base64") # Optional base64 encoded image string

        if not post_text or not isinstance(post_text, str) or not post_text.strip():
            return jsonify({"error": "post_text is required and cannot be empty."}), 400
        if not platform or not isinstance(platform, str) or not platform.strip():
            return jsonify({"error": "platform is required and cannot be empty."}), 400

        model = genai.GenerativeModel("gemini-1.5-flash-latest")

        # --- Prepare content for Gemini ---
        gemini_content_parts = []
        
        # Part 1: Initial instruction
        instruction_intro = f"Analyze the following social media post intended for {platform.capitalize()}."
        gemini_content_parts.append(instruction_intro)
        
        # Part 2: Post text
        gemini_content_parts.append(f"Post text: \"{post_text}\"")

        # Part 3: Image (if provided and PIL is available)
        pil_image_object = None
        if image_base64 and isinstance(image_base64, str) and image_base64.strip():
            if not PIL_AVAILABLE:
                return jsonify({"error": "Image processing is unavailable on the server (Pillow library missing)."}), 501 # 501 Not Implemented
            try:
                # Decode base64 string to bytes
                image_bytes = base64.b64decode(image_base64)
                if not image_bytes: # Handle empty string after decode
                    raise ValueError("Decoded image data is empty.")
                # Create a PIL Image object from bytes
                pil_image_object = Image.open(io.BytesIO(image_bytes))
                # You can optionally specify the format if known, e.g., pil_image_object.format = "JPEG"
                # Add image-related text and the image object to the prompt parts
                gemini_content_parts.append("The post also includes this image:")
                gemini_content_parts.append(pil_image_object) # Pass the PIL image object
            except base64.binascii.Error:
                return jsonify({"error": "Invalid base64 image data provided."}), 400
            except UnidentifiedImageError: # Specific PIL error for unrecognized image formats
                 return jsonify({"error": "Could not identify or open the provided image format."}), 400
            except ValueError as ve: # Catch empty decoded data
                 print(f"Image processing ValueError: {ve}")
                 return jsonify({"error": "Invalid image data: decoded data is empty."}), 400
            except Exception as e: # Catch other PIL/IO errors
                print(f"Error processing image: {e}")
                # Do not return here, proceed without image if processing fails, or return error:
                return jsonify({"error": f"Could not process the provided image: {str(e)}"}), 400
        
        # Part 4: Criteria and JSON format instruction
        # Determine if visual appeal criterion should be specifically mentioned
        visual_appeal_criterion = "5.  Visual Appeal (if an image is provided, how well it complements the text and grabs attention. If no image, ignore this criterion or score neutrally)." \
                                  if pil_image_object else "5. Visual Appeal (No image provided, this criterion will be scored neutrally or ignored)."

        criteria_and_format_instruction = f"""
Based on the provided content (text and image, if any), provide a performance score from 0 to 100 using the following criteria:
1.  Engagement Potential (likes, comments, shares).
2.  Clarity (clear, concise, understandable).
3.  Message Quality (valuable, informative, or entertaining for {platform.capitalize()}).
4.  Hashtag Effectiveness (relevance, visibility, or if beneficial if absent).
{visual_appeal_criterion}

Return your response ONLY as a valid JSON object. The JSON object must have two keys:
- "score": An integer between 0 and 100.
- "feedback": A brief string (max 150 characters) explaining the score and offering 1-2 concise general improvement suggestions.

If the "score" is below 60, ALSO include a third key in the JSON object:
- "content_suggestions": A string containing 1-2 specific, actionable suggestions for alternative post content (text and, if applicable, image ideas) that would likely achieve a higher score. This should be more detailed than the general 'feedback'. Make these suggestions creative and engaging for {platform.capitalize()}.

Example JSON Response (score >= 60):
{{
  "score": 85,
  "feedback": "Great clarity and strong visual. Consider adding a question to boost engagement."
}}

Example JSON Response (score < 60, with image):
{{
  "score": 45,
  "feedback": "Post lacks clarity and visual is mismatched. Hashtags are too generic.",
  "content_suggestions": "Try rephrasing the text to focus on a single key benefit. For example: 'Struggling with X? Our new Y offers a simple solution! ✨ Check it out [link] #ProblemSolved #{platform.lower()}Tips'. For the image, consider a before-and-after shot or a graphic highlighting the main feature that is bright and clear."
}}

Example JSON Response (score < 60, no image):
{{
  "score": 50,
  "feedback": "The message is a bit unclear and hashtags could be more specific.",
  "content_suggestions": "Consider clarifying the main call to action. For example: 'Discover how our new service Z can save you time! Learn more and sign up today: [link]. #SaveTime #{platform.lower()}Solutions'. Adding an engaging graphic or short video could also help if possible."
}}
"""
        gemini_content_parts.append(criteria_and_format_instruction)
        # --- End of content preparation ---

        response = model.generate_content(gemini_content_parts) # Pass the list of parts
        
        cleaned_response_text = response.text.strip()
        # Remove markdown JSON block delimiters if present
        if cleaned_response_text.startswith("```json"):
            cleaned_response_text = cleaned_response_text[7:]
        if cleaned_response_text.endswith("```"):
            cleaned_response_text = cleaned_response_text[:-3]
        cleaned_response_text = cleaned_response_text.strip()

        try:
            result_data = json.loads(cleaned_response_text)
            score = result_data.get("score")
            feedback = result_data.get("feedback")
            
            if not isinstance(score, int) or not (0 <= score <= 100):
                raise ValueError("Score is not a valid integer between 0 and 100.")
            if not isinstance(feedback, str):
                raise ValueError("Feedback is not a string.")

            response_payload = {"score": score, "feedback": feedback}
            
            # Check for content_suggestions. It's expected if score < 60,
            # but can also be present if AI provides it anyway.
            content_suggestions = result_data.get("content_suggestions")
            if isinstance(content_suggestions, str) and content_suggestions.strip():
                response_payload["content_suggestions"] = content_suggestions
            elif score < 60 and (content_suggestions is None or not str(content_suggestions).strip()):
                 print(f"Warning: Score is {score} (<60) but 'content_suggestions' is missing or invalid in AI response: '{content_suggestions}'")
                 # Optionally, you could add a default message here if suggestions are strictly expected but missing
                 # response_payload["content_suggestions"] = "The AI did not provide specific content suggestions despite the low score."


            return jsonify(response_payload), 200
        
        except (json.JSONDecodeError, ValueError) as parse_error:
            print(f"Error parsing Gemini response as JSON: {parse_error}. Raw text: [{response.text}] Cleaned text: [{cleaned_response_text}]")
            
            # Fallback: try to extract score, feedback, and suggestions with regex
            extracted_score_val = None
            score_match = re.search(r'"score":\s*(\d+)', cleaned_response_text)
            if score_match:
                try:
                    val = int(score_match.group(1))
                    if 0 <= val <= 100:
                        extracted_score_val = val
                except ValueError:
                    pass # Not a valid int

            feedback_text = "AI analysis was partially successful. Could not fully parse detailed feedback from the AI."
            # Regex for feedback: capture content within quotes, stopping before next key or end of object
            feedback_match = re.search(r'"feedback":\s*"(.*?)"(?=\s*,\s*"|\s*})', cleaned_response_text, re.DOTALL)
            if feedback_match:
                extracted_feedback = feedback_match.group(1).strip().replace('\\"', '"') # Handle escaped quotes
                if extracted_feedback: # Ensure feedback is not empty
                    feedback_text = extracted_feedback
            
            if extracted_score_val is None: # If score couldn't be extracted at all
                 print(f"Fallback failed: Could not extract a valid score. Raw response: {cleaned_response_text}")
                 return jsonify({"error": "AI analysis failed to produce a valid score. Please try again or rephrase your post."}), 500

            final_fallback_response = {"score": extracted_score_val, "feedback": feedback_text}
            
            # Attempt to extract content_suggestions in fallback if score < 60
            if extracted_score_val < 60:
                # Regex for suggestions: similar to feedback
                suggestions_match = re.search(r'"content_suggestions":\s*"(.*?)"(?=\s*,\s*"|\s*})', cleaned_response_text, re.DOTALL)
                if suggestions_match:
                    extracted_suggestions = suggestions_match.group(1).strip().replace('\\"', '"')
                    if extracted_suggestions:
                        final_fallback_response["content_suggestions"] = extracted_suggestions
            
            return jsonify(final_fallback_response), 200

    except genai.types.generation_types.BlockedPromptException as bpe:
        print(f"Gemini API request blocked: {bpe}")
        # It's helpful to see what part of the prompt might have caused the block, if available
        # print(f"Blocked prompt parts: {bpe.prompt}") # This might not be available or too verbose
        return jsonify({"error": "Your request was blocked by the AI for safety reasons. Please modify your post content and/or image."}), 400
    except Exception as e:
        # Log the full traceback for unexpected errors
        import traceback
        print(f"An unexpected error occurred in /score_post: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "An unexpected error occurred while scoring the post."}), 500

# It's good practice to define UnidentifiedImageError if it's not always available
# or rely on the general Exception for PIL errors if preferred.
# For this context, assuming PIL.UnidentifiedImageError is available if PIL is.
try:
    from PIL import UnidentifiedImageError
except ImportError:
    # Define a dummy UnidentifiedImageError if PIL is not fully featured or older version
    class UnidentifiedImageError(Exception):
        pass

