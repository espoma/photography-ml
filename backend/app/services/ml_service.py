from typing import List
import time
import random

def generate_tags(image_path: str) -> List[str]:
    """
    Mock ML service that generates tags for an image.
    In a real app, this would load a model (like CLIP or ResNet) and run inference.
    
    Args:
        image_path (str): The path to the image file on disk.
        
    Returns:
        List[str]: A list of predicted tags.
    """
    print(f"🤖 ML Service: Processing image at {image_path}...")
    
    # Simulate processing time (e.g., loading model, inference)
    time.sleep(0.5)
    
    # Mock logic: return some generic tags + maybe some random ones
    base_tags = ["ai_generated", "photography"]
    possible_tags = ["outdoor", "nature", "portrait", "landscape", "urban", "sunset", "macro"]
    
    # Pick 2 random tags
    random_tags = random.sample(possible_tags, 2)
    
    return base_tags + random_tags
