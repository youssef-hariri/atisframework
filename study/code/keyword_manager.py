# keyword_manager.py
import json
import re
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
from deepseek_client import DeepSeekClient

class KeywordManager:
    def __init__(self, deepseek_client: DeepSeekClient):
        self.client = deepseek_client
        self.keyword_dict = {
            "Act": self._get_base_act_keywords(),
            "Train": self._get_base_train_keywords(),
            "Inquire": self._get_base_inquire_keywords(),
            "Standardize": self._get_base_standardize_keywords()
        }
        self.phrase_frequencies = defaultdict(int)
    
    def _get_base_act_keywords(self) -> Set[str]:
        return {"implement", "establish", "create", "build", "set up",
                "initiate", "deploy", "enact", "put in place", "roll out",
                "action", "intervene", "decision", "decide", "lead"}
    
    def _get_base_train_keywords(self) -> Set[str]:
        return {"train", "upskill", "educate", "learn", "develop",
                "coach", "mentor", "teach", "workshop", "course",
                "skill", "capacity", "competency", "development",
                "training", "education", "learning"}
    
    def _get_base_inquire_keywords(self) -> Set[str]:
        return {"ask", "question", "inquire", "investigate", "explore",
                "understand", "clarify", "seek", "probe", "examine",
                "research", "study", "analyze", "gather", "collect",
                "feedback", "consult", "discuss", "dialogue"}
    
    def _get_base_standardize_keywords(self) -> Set[str]:
        return {"standardize", "document", "framework", "protocol",
                "process", "procedure", "template", "systematize",
                "formalize", "structure", "guideline", "policy",
                "consistent", "uniform", "repeatable", "record"}
    
    def build_from_json_files(self, json_files: List[str], sample_size: int = 5) -> Dict[str, List[str]]:
        """Build dynamic keyword dictionary from sample JSON files"""
        all_phrases = defaultdict(set)
        
        # Process sample files
        for file_path in json_files[:sample_size]:
            with open(file_path, 'r') as f:
                try:
                    data = json.load(f)
                    
                    # Extract quotes from enriched JSON structure
                    quotes = self._extract_quotes_from_json(data)
                    
                    for quote in quotes:
                        if quote and len(quote.strip()) > 20:  # Meaningful quotes only
                            phrases = self.client.extract_keyword_phrases(quote)
                            
                            # Add phrases to collections
                            for pillar, phrase_list in phrases.items():
                                pillar_name = pillar.split("_")[0].title()
                                if pillar_name in ["Act", "Train", "Inquire", "Standardize"]:
                                    for phrase in phrase_list:
                                        # Clean and add phrase
                                        clean_phrase = self._clean_phrase(phrase)
                                        if clean_phrase and len(clean_phrase) > 2:
                                            all_phrases[pillar_name].add(clean_phrase)
                                            self.phrase_frequencies[clean_phrase] += 1
                
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error processing {file_path}: {e}")
                    continue
        
        # Merge with base keywords
        for pillar in self.keyword_dict:
            self.keyword_dict[pillar].update(all_phrases.get(pillar, set()))
        
        # Convert sets to sorted lists (most frequent first)
        final_dict = {}
        for pillar, keyword_set in self.keyword_dict.items():
            # Sort by frequency (descending), then alphabetically
            sorted_keywords = sorted(
                keyword_set,
                key=lambda x: (self.phrase_frequencies.get(x, 0), x),
                reverse=True
            )
            final_dict[pillar] = sorted_keywords[:50]  # Keep top 50
        
        return final_dict
    
    def _extract_quotes_from_json(self, data):
        """Extract quotes from various JSON structures"""
        quotes = []
        
        if isinstance(data, list):
            # List of items
            for item in data:
                if isinstance(item, dict):
                    quote = item.get('expert_quote', item.get('quote', item.get('Expert Quote (Slang)', '')))
                    if quote:
                        quotes.append(quote)
        elif isinstance(data, dict):
            # Single item
            quote = data.get('expert_quote', data.get('quote', data.get('Expert Quote (Slang)', '')))
            if quote:
                quotes.append(quote)
            
            # Check for nested lists
            for key, value in data.items():
                if isinstance(value, list) and key in ['quotes', 'interview_segments', 'data']:
                    for item in value:
                        if isinstance(item, dict):
                            nested_quote = item.get('expert_quote', item.get('quote', item.get('Expert Quote (Slang)', '')))
                            if nested_quote:
                                quotes.append(nested_quote)
        
        return quotes
    
    def _clean_phrase(self, phrase: str) -> str:
        """Clean extracted phrases"""
        phrase = phrase.lower().strip()
        phrase = re.sub(r'[^\w\s-]', '', phrase)  # Remove special chars
        phrase = re.sub(r'\s+', ' ', phrase)  # Normalize whitespace
        return phrase
    
    def detect_pillars_keyword(self, quote: str) -> List[str]:
        """Detect ATIS pillars using keyword matching"""
        quote_lower = quote.lower()
        detected = []
        
        for pillar, keywords in self.keyword_dict.items():
            for keyword in keywords:
                # Check if keyword appears as whole word
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, quote_lower):
                    detected.append(pillar)
                    break  # Found at least one for this pillar
        
        return list(set(detected))  # Remove duplicates
    
    def save_keyword_dict(self, filepath: str):
        """Save keyword dictionary to file"""
        with open(filepath, 'w') as f:
            json.dump({k: list(v) for k, v in self.keyword_dict.items()}, f, indent=2)
    
    def load_keyword_dict(self, filepath: str):
        """Load keyword dictionary from file"""
        with open(filepath, 'r') as f:
            loaded_dict = json.load(f)
            self.keyword_dict = {k: set(v) for k, v in loaded_dict.items()}
