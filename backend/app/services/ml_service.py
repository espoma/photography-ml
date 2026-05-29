from typing import List
import json
import mimetypes
from google import genai
from google.genai import types

# List of free-tier Gemini models to try in order (primary to fallback)
GEMINI_MODELS = [
    'gemini-2.5-flash',        # Primary: Latest and fastest
    'gemini-1.5-flash',        # Fallback 1: Reliable alternative
    'gemini-1.5-flash-8b',     # Fallback 2: Lightweight version
]

def generate_tags(image_path: str) -> List[str]:
    """
    ML service that uses Gemini to generate tags for an image.
    Tries multiple free-tier models with fallback.
    
    Args:
        image_path (str): The path to the image file on disk.
        
    Returns:
        List[str]: A list of predicted tags.
    """
    print(f"🤖 ML Service: Analyzing image at {image_path} with Gemini...")
    
    try:
        # Initialize the client. It automatically picks up GEMINI_API_KEY from the environment.
        client = genai.Client()
        
        # Read the image file
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            
        # Determine mime type
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg" # fallback
            
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        
        prompt = (
            "You are an expert photography assistant. Analyze this image and generate 5-10 highly descriptive keywords. "
            "Focus on lighting, mood, subject matter, and composition. Only use lowercase."
        )
        
        # Try each model in order
        last_error = None
        for model in GEMINI_MODELS:
            try:
                print(f"  Trying model: {model}")
                # We enforce a structured JSON output array of strings
                response = client.models.generate_content(
                    model=model,
                    contents=[image_part, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema={"type": "array", "items": {"type": "string"}}
                    )
                )
                
                # The response text should be a JSON array string
                tags = json.loads(response.text)
                print(f"✅ Successfully generated tags with {model}: {tags}")
                return tags
                
            except Exception as model_error:
                last_error = model_error
                print(f"  ⚠️  Model {model} failed: {model_error}")
                continue
        
        # If all models failed, raise the last error
        if last_error:
            raise last_error
        
    except Exception as e:
        print(f"❌ ML Service Error: {e}")
        # Fallback to some default tags if all API calls fail
        return ["ai_generated", "photography"]
