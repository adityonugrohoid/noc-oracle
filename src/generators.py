import os
import google.generativeai as genai
from dotenv import load_dotenv
import pathlib

# Load environment variables
load_dotenv()

def generate_manual():
    """
    Generates a realistic technical manual for 'Orbit-5G Base Station' using Gemini.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        return

    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # Use a model that supports content generation (Gemini 1.5 Pro or Flash)
    # Using 'gemini-1.5-flash' for speed/cost efficiency for this task, 
    # or 'gemini-1.5-pro' for higher quality if needed. 
    # Architecture doc mentions 'Gemini-1.5-Pro', so let's stick to a robust model or let it default.
    # Using 'gemini-2.0-flash-lite' as it is available in the environment.
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
    except Exception as e:
        print(f"Error initializing model: {e}")
        return

    prompt = """
    You are a Senior Technical Writer and Solutions Architect for a telecommunications company. 
    Your task is to create a realistic **Troubleshooting Manual** for a fictional device called the **'Orbit-5G Base Station'** running **'NebulaOS'**.

    The output **must** be valid Markdown.
    
    Structure the manual into exactly these 3 sections:
    1. **Hardware Alarms**: Create 5 distinct error codes (e.g., 'E-101: Power Unit Failure').
    2. **Software Alarms**: Create 5 distinct error codes (e.g., 'S-505: Handover Timeout').
    3. **Connectivity Issues**: Create 5 distinct connectivity scenarios.

    For **EACH** error code or scenario, you must provide:
    *   **Description**: A technical explanation of what went wrong.
    *   **Resolution Procedure**: A numbered list of steps to resolve the issue. Be specific and technical (e.g., "Check voltage at test point TP4", "Run command `nebula-cli reset-interface`").

    Do not include any conversational filler. Output ONLY the Markdown content starting with the title.
    """

    print("Generating manual using Gemini... this may take a few seconds.")
    try:
        response = model.generate_content(prompt)
        content = response.text
        
        # Define output path
        output_dir = pathlib.Path("data/manuals")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "orbit_5g_guide.md"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"Success! Manual saved to: {output_file}")
        
    except Exception as e:
        print(f"Error during generation: {e}")

if __name__ == "__main__":
    generate_manual()
