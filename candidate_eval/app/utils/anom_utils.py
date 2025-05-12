# app/utils/anom_utils.py
from typing import Dict, List, Optional, Any, Union, Tuple, Set
import re

class SelectiveAnonymizer:
    """
    Utility for selectively anonymizing entities from Presidio based on custom rules.
    """

    @staticmethod
    def parse_presidio_output(output_text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parse the output from Presidio to separate the text from entity details.
        
        Args:
            output_text: The complete output from Presidio including text and entity details
            
        Returns:
            Tuple containing (original_text, entities_list)
        """
        # Split at the "--- Detected Entities ---" marker
        parts = output_text.split("--- Detected Entities ---")
        
        if len(parts) != 2:
            # No entities section found
            return output_text, []
        
        original_text = parts[0].strip()
        entities_section = parts[1].strip()
        
        # Parse entity information
        entities = []
        # Match patterns like: "1. CREDIT_CARD (1.00): '4095-2609-9393-4932' [position: 89-108]"
        entity_pattern = r'(\d+)\.\s+(\w+)\s+\(([\d\.]+)\):\s+\'(.*?)\'\s+\[position:\s+(\d+)-(\d+)\]'
        
        for match in re.finditer(entity_pattern, entities_section):
            idx, entity_type, score, text, start, end = match.groups()
            entities.append({
                "idx": int(idx),
                "entity_type": entity_type,
                "score": float(score),
                "text": text,
                "start": int(start),
                "end": int(end)
            })
        
        return original_text, entities
    
    @staticmethod
    def filter_entities_by_rules(entities: List[Dict[str, Any]], rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter entities based on custom rules.
        
        Args:
            entities: List of entity dictionaries from parse_presidio_output
            rules: Dictionary containing filtering rules
            
        Returns:
            Filtered list of entities
        """
        filtered_entities = []
        
        # Track first occurrences by entity type
        first_occurrence = {}
        
        for entity in entities:
            entity_type = entity["entity_type"]
            
            # Rule 1: If we want only the first occurrence of certain entity types
            if rules.get("first_occurrence_only", []) and entity_type in rules["first_occurrence_only"]:
                if entity_type not in first_occurrence:
                    first_occurrence[entity_type] = entity
                    filtered_entities.append(entity)
                continue
            
            # Rule 2: If we want all occurrences of certain entity types
            if rules.get("all_occurrences", []) and entity_type in rules["all_occurrences"]:
                filtered_entities.append(entity)
                continue
            
            # Rule 3: Entity types to always ignore
            if rules.get("ignore_types", []) and entity_type in rules["ignore_types"]:
                continue
        
        return filtered_entities
    
    @staticmethod
    def anonymize_selected_entities(text: str, entities: List[Dict[str, Any]], anonymization_format: str = "<{entity_type}>") -> str:
        """
        Anonymize only the selected entities in the text.
        
        Args:
            text: Original text
            entities: List of entities to anonymize
            anonymization_format: Format string for anonymized text, will replace {entity_type} with the entity type
            
        Returns:
            Text with selected entities anonymized
        """
        # Sort entities by start position in reverse order to avoid position shifts
        entities_sorted = sorted(entities, key=lambda e: e["start"], reverse=True)
        
        # Apply replacements
        for entity in entities_sorted:
            replacement = anonymization_format.format(entity_type=entity["entity_type"])
            text = text[:entity["start"]] + replacement + text[entity["end"]:]
        
        return text

    @staticmethod
    def process_presidio_output(
        output_text: str,
        rules: Dict[str, Any] = None,
        anonymization_format: str = "<{entity_type}>"
    ) -> str:
        """
        Process Presidio output to selectively anonymize entities based on rules.
        
        Args:
            output_text: Complete output from Presidio
            rules: Dictionary with filtering rules (default applies some common rules)
            anonymization_format: Format for anonymized text
            
        Returns:
            Text with selectively anonymized entities
        """
        # Default rules if none provided
        if rules is None:
            rules = {
                "first_occurrence_only": ["PERSON", "LOCATION"],
                "all_occurrences": ["EMAIL_ADDRESS", "URL", "CREDIT_CARD", "PHONE_NUMBER", "IP_ADDRESS"],
                "ignore_types": [],
                "min_score": 0.5
            }
        
        # Parse the output
        original_text, entities = SelectiveAnonymizer.parse_presidio_output(output_text)
        
        # Filter entities based on rules
        filtered_entities = SelectiveAnonymizer.filter_entities_by_rules(entities, rules)
        
        # Anonymize selected entities
        result_text = SelectiveAnonymizer.anonymize_selected_entities(
            original_text, 
            filtered_entities,
            anonymization_format
        )
        
        return result_text
        
    @staticmethod
    def anonymize_original_text(
        original_text: str,
        entities: List[Dict[str, Any]],
        rules: Dict[str, Any] = None,
        anonymization_format: str = "<{entity_type}>"
    ) -> str:
        """
        Directly anonymize the original text using detected entities based on rules.
        
        Args:
            original_text: The original text (without any anonymization)
            entities: List of entity dictionaries from Presidio (with start, end, entity_type, etc.)
            rules: Dictionary with filtering rules
            anonymization_format: Format for anonymized text
            
        Returns:
            Text with selectively anonymized entities
        """
        # Default rules if none provided
        if rules is None:
            rules = {
                "first_occurrence_only": ["PERSON"],
                "all_occurrences": ["EMAIL_ADDRESS", "URL"],
                "ignore_types": [],  # Ignore all other entity types
            }
        
        # Only keep entities in first_occurrence_only or all_occurrences
        valid_entity_types = (
            rules.get("first_occurrence_only", []) + 
            rules.get("all_occurrences", [])
        )
        
        # Filter entities to only include the ones we care about
        relevant_entities = [
            entity for entity in entities 
            if entity["entity_type"] in valid_entity_types
        ]
        
        # Apply rules to the relevant entities
        filtered_entities = SelectiveAnonymizer.filter_entities_by_rules(relevant_entities, rules)
        
        # Anonymize selected entities
        result_text = SelectiveAnonymizer.anonymize_selected_entities(
            original_text, 
            filtered_entities,
            anonymization_format
        )
        
        return result_text