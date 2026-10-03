# deepseek_client.py
import json
import time
import logging
from typing import List, Dict, Any
import requests
from config import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekClient:
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def make_api_call(self, messages: List[Dict], max_tokens: int = 500) -> Dict:
        """Make API call to DeepSeek"""
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API call failed: {e}")
            raise
    
    def extract_atis_pillars(self, quote: str) -> List[str]:
        """Extract ATIS pillars from a single quote"""
        system_prompt = """You are a precise qualitative coding assistant. 
        Analyze interview quotes and identify management approaches.
        Always return valid JSON arrays without explanations."""
        
        user_prompt = f"""
        Analyze this quote from an AI professional:
        
        "{quote}"
        
        Identify which of these FOUR management approaches (ATIS pillars) are mentioned or implied:
        
        1. ACT - Taking action, implementing, establishing, making decisions
        2. TRAIN - Building capability, education, upskilling, development
        3. INQUIRE - Asking questions, investigating, seeking understanding
        4. STANDARDIZE - Creating frameworks, documenting, establishing procedures
        
        Return ONLY a JSON array of pillar names that are clearly present.
        Examples: ["Act", "Train"] or ["Inquire"] or [] if none.
        
        JSON format only, no other text:"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            result = self.make_api_call(messages)
            content = result["choices"][0]["message"]["content"].strip()
            
            # Clean and parse JSON
            content = content.replace("```json", "").replace("```", "").strip()
            if content.startswith("[") and content.endswith("]"):
                pillars = json.loads(content)
                # Normalize casing
                normalized = []
                for pillar in pillars:
                    if pillar.lower() == "act":
                        normalized.append("Act")
                    elif pillar.lower() == "train":
                        normalized.append("Train")
                    elif pillar.lower() == "inquire":
                        normalized.append("Inquire")
                    elif pillar.lower() == "standardize":
                        normalized.append("Standardize")
                return normalized
            return []
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"Failed to parse response for quote: {e}")
            return []
    
    def extract_keyword_phrases(self, quote: str) -> Dict[str, List[str]]:
        """Extract actual phrases used in quote for each pillar"""
        system_prompt = """Extract exact phrases from interview quotes.
        Return only valid JSON without explanations."""
        
        user_prompt = f"""
        Extract all phrases from this quote that relate to management approaches:
        
        "{quote}"
        
        Categorize them into:
        1. ACT - Action, implementation, decision-making phrases
        2. TRAIN - Learning, education, skill development phrases
        3. INQUIRE - Questioning, investigation, understanding phrases
        4. STANDARDIZE - Documentation, framework, procedure phrases
        
        Return JSON with this exact structure:
        {{
          "act_phrases": [],
          "train_phrases": [],
          "inquire_phrases": [],
          "standardize_phrases": []
        }}
        
        Extract EXACT phrases as they appear. If none, return empty array.
        
        JSON only, no other text:"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            result = self.make_api_call(messages)
            content = result["choices"][0]["message"]["content"].strip()
            content = content.replace("```json", "").replace("```", "").strip()
            
            phrases = json.loads(content)
            return phrases
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to extract phrases: {e}")
            return {"act_phrases": [], "train_phrases": [],
                    "inquire_phrases": [], "standardize_phrases": []}
