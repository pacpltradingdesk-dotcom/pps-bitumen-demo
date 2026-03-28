import google.generativeai as genai
from PIL import Image
import json
import typing_extensions

# Define the output schema for structured JSON response
class TradeAnalysis(typing_extensions.TypedDict):
    decision: str
    confidence_score: str
    market_status: str
    reasoning: str
    entry_trigger: str
    exit_price: str
    target: str
    factors: dict

def analyze_charts(image_files, api_key):
    """
    Sends the images to Google Gemini Flash/Pro for analysis.
    """
    genai.configure(api_key=api_key)
    
    # Use Gemini 1.5 Pro for best vision capabilities, or Flash for speed/cost.
    # User requested Pro or 4o.
    model = genai.GenerativeModel('gemini-1.5-pro',
        generation_config={"response_mime_type": "application/json", "response_schema": TradeAnalysis}
    )

    # Process images: Open them using PIL
    pil_images = []
    
    # We expect a list of 12 items. Some might be None.
    # The Prompt expects slots 1-12. We should label them or just provide them in order.
    # Providing them in order is easiest for the model if we instruct it.
    
    valid_images = []
    for idx, file_obj in enumerate(image_files):
        if file_obj:
            img = Image.open(file_obj)
            valid_images.append(f"Image {idx+1} (Slot {idx+1})")
            valid_images.append(img)
        else:
            valid_images.append(f"Image {idx+1} (Slot {idx+1}) - MISSING")
            # We can't send text as "image" part easily mixed in strict list sometimes, 
            # but Gemini handles mixed content [text, img, text, img].
            
    # Construct the System Prompt
    system_prompt = """
    ROLE: You are a Senior Hedge Fund Algorithm specializing in Nifty 50 Constituent Analysis.
    
    INPUT: You have received up to 12 images of 5-minute charts.
    - Image 1: Nifty 50 Index (The Market)
    - Image 2: Bank Nifty (The Sector)
    - Image 3: HDFC Bank (Heavyweight 1 - CRITICAL)
    - Image 4: Reliance Industries (Heavyweight 2 - CRITICAL)
    - Images 5-12: Other Constituents (ICICI, Infosys, etc.)

    YOUR TASK: Determine if the Nifty 50 (Image 1) is a BUY, SELL, or NO TRADE based on the support of its constituents.
    
    ALGORITHMIC RULES:
    1. The Veto Rule: If Image 1 (Nifty) looks Bullish, BUT Image 3 (HDFC) and Image 4 (Reliance) are hitting resistance or looking Bearish -> Signal = NO TRADE / TRAP DETECTED.
    2. The Confirmation Rule: If Image 1 is breaking out, AND Images 3, 4, and 5 are also breaking out -> Signal = HIGH PROBABILITY BUY.
    3. Volume Check: Look for large volume bars at breakout points in the images to confirm validity.

    OUTPUT EXPECTATION:
    Return a JSON object with the following fields:
    - decision: [BUY, SELL, WAIT, NO TRADE, HIGH PROBABILITY BUY, TRAP DETECTED]
    - confidence_score: e.g. "85%"
    - market_status: e.g. "BEARISH CONFLUENCE", "BULLISH BREAKOUT"
    - entry_trigger: Specific price or condition (e.g. "Close above 21500")
    - exit_price: Stop loss suggestions.
    - target: Likely target based on structure.
    - factors: A dictionary containing brief analysis for these 6 keys:
        - "Nifty_View": Analysis of Image 1.
        - "BankNifty_View": Analysis of Image 2.
        - "HDFC_Bank": Analysis of Image 3.
        - "Reliance": Analysis of Image 4.
        - "Overall_Constituents": Summary of Images 5-12.
        - "Technical_Confluence": Volume/Pattern confirmation.
    """

    # Combine prompt and images
    content = [system_prompt] + valid_images

    response = model.generate_content(content)
    
    try:
        # Parse JSON
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        # Fallback if strict JSON fails (though schema usually enforces it)
        return None
