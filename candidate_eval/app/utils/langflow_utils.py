# app/utils/langflow_utils.py
import json
import re
from typing import List, Dict, Any

def parse_skills_response(skills_text: str) -> List[Dict[str, Any]]:
    """
    Parse the skills text response from LangFlow into structured data.
    The expected format is a JSON string with skills array.
    """
    try:
        # Try to parse as JSON directly
        data = json.loads(skills_text)
        if isinstance(data, dict) and "skills" in data:
            return data["skills"]
    except json.JSONDecodeError:
        # If direct JSON parsing fails, try to extract JSON from text
        json_pattern = r'```json\s*(.*?)\s*```'
        match = re.search(json_pattern, skills_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict) and "skills" in data:
                    return data["skills"]
            except json.JSONDecodeError:
                pass
    
    # If all parsing attempts fail, return empty list
    return []