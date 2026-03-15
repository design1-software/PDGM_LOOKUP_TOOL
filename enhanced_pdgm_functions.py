"""
Enhanced PDGM Functions with Medical Synonym Mapping and Improved Follow-up Logic
"""

import re
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Set

# Medical synonym mapping for common abbreviations and terms
MEDICAL_SYNONYMS = {
    'CHF': ['heart failure', 'congestive heart failure', 'cardiac failure'],
    'DM': ['diabetes mellitus', 'diabetes'],
    'COPD': ['chronic obstructive pulmonary disease', 'chronic obstructive lung disease'],
    'MI': ['myocardial infarction', 'heart attack'],
    'CVA': ['cerebrovascular accident', 'stroke'],
    'UTI': ['urinary tract infection', 'bladder infection'],
    'DVT': ['deep vein thrombosis', 'deep venous thrombosis'],
    'PE': ['pulmonary embolism', 'pulmonary embolus'],
    'GERD': ['gastroesophageal reflux disease', 'acid reflux'],
    'HTN': ['hypertension', 'high blood pressure'],
    'CAD': ['coronary artery disease', 'coronary heart disease'],
    'CKD': ['chronic kidney disease', 'chronic renal disease'],
    'ESRD': ['end stage renal disease', 'end stage kidney disease'],
    'AFIB': ['atrial fibrillation'],
    'PVD': ['peripheral vascular disease', 'peripheral artery disease'],
    'TIA': ['transient ischemic attack', 'mini stroke'],
    'PTSD': ['post traumatic stress disorder'],
    'OCD': ['obsessive compulsive disorder'],
    'ADHD': ['attention deficit hyperactivity disorder'],
    'HIV': ['human immunodeficiency virus'],
    'AIDS': ['acquired immunodeficiency syndrome'],
    'MRSA': ['methicillin resistant staphylococcus aureus'],
    'C DIFF': ['clostridium difficile', 'clostridioides difficile'],
    'PNEUMONIA': ['lung infection', 'respiratory infection'],
    'SEPSIS': ['blood infection', 'systemic infection'],
    'CELLULITIS': ['skin infection', 'soft tissue infection']
}

# Context keywords that suggest specific variants
CONTEXT_KEYWORDS = {
    'exacerbation': ['acute', 'acute on chronic', 'with exacerbation'],
    'acute': ['acute', 'sudden onset'],
    'chronic': ['chronic', 'long term', 'persistent'],
    'with complications': ['with complications', 'complicated'],
    'unspecified': ['unspecified', 'not otherwise specified', 'NOS'],
    'type 1': ['type 1', 'type I', 'insulin dependent'],
    'type 2': ['type 2', 'type II', 'non insulin dependent'],
    'systolic': ['systolic', 'left ventricular'],
    'diastolic': ['diastolic', 'right ventricular'],
    'bilateral': ['bilateral', 'both sides'],
    'unilateral': ['unilateral', 'one side'],
    'primary': ['primary', 'essential'],
    'secondary': ['secondary', 'due to']
}

# Predefined follow-up suggestions for common conditions
PREDEFINED_FOLLOWUPS = {
    'heart failure': "Would you like to specify: acute exacerbation, chronic systolic, chronic diastolic, or combined systolic/diastolic?",
    'diabetes': "Please specify: Type 1, Type 2, with complications (neuropathy, nephropathy, retinopathy), or gestational?",
    'COPD': "Is this: acute exacerbation, with acute bronchitis, or chronic obstructive asthma?",
    'hypertension': "Please specify: essential hypertension, hypertensive heart disease, or hypertensive kidney disease?",
    'pneumonia': "Would you like to specify: bacterial, viral, aspiration, or organism-specific pneumonia?",
    'diabetes mellitus': "Please specify: Type 1, Type 2, with complications (neuropathy, nephropathy, retinopathy), or gestational?",
    'stroke': "Please specify: ischemic stroke, hemorrhagic stroke, or transient ischemic attack (TIA)?",
    'kidney disease': "Would you like to specify: acute kidney injury, chronic kidney disease stage, or end-stage renal disease?",
    'infection': "Please specify the site: urinary tract, respiratory, skin/soft tissue, or bloodstream infection?",
    'fracture': "Please specify: location (hip, wrist, spine), type (closed, open), or healing status?",
    'wound': "Please specify: pressure ulcer with stage, diabetic ulcer, or surgical wound complication?",
    'pain': "Please specify: location (back, joint, neuropathic), chronic vs acute, or pain syndrome type?"
}

def expand_with_medical_synonyms(phrase: str) -> List[str]:
    """Expand a medical phrase with known synonyms and abbreviations."""
    expanded_terms = [phrase.lower()]
    phrase_lower = phrase.lower()
    
    # Check for exact abbreviation matches
    for abbrev, synonyms in MEDICAL_SYNONYMS.items():
        if abbrev.lower() in phrase_lower:
            for synonym in synonyms:
                # Replace abbreviation with synonym
                expanded_phrase = phrase_lower.replace(abbrev.lower(), synonym)
                expanded_terms.append(expanded_phrase)
                expanded_terms.extend(synonyms)
    
    # Check for partial matches in synonyms
    for abbrev, synonyms in MEDICAL_SYNONYMS.items():
        for synonym in synonyms:
            if any(word in phrase_lower for word in synonym.split()):
                expanded_terms.extend(synonyms)
                expanded_terms.append(abbrev.lower())
                break
    
    return list(set(expanded_terms))  # Remove duplicates

def extract_context_keywords(phrase: str) -> List[str]:
    """Extract context keywords that suggest specific code variants."""
    phrase_lower = phrase.lower()
    found_contexts = []
    
    for keyword, variants in CONTEXT_KEYWORDS.items():
        if keyword in phrase_lower:
            found_contexts.extend(variants)
    
    return found_contexts

def get_candidate_codes_enhanced(phrase: str, icd10_data: Dict, limit: int = 15) -> List[Dict]:
    """Enhanced candidate code matching with medical synonyms and context awareness."""
    
    # Expand phrase with medical synonyms
    expanded_terms = expand_with_medical_synonyms(phrase)
    context_keywords = extract_context_keywords(phrase)
    
    # Combine all search terms
    all_search_terms = expanded_terms + context_keywords
    
    # Score all codes against all search terms
    code_scores = {}
    
    for row in icd10_data.values():
        desc = row.get('description', '')
        if not desc:
            continue
            
        desc_lower = desc.lower()
        max_score = 0
        
        # Test against all expanded terms
        for term in all_search_terms:
            # Exact phrase match gets highest score
            if term in desc_lower:
                score = 1.0
            else:
                # Fuzzy matching for partial matches
                score = SequenceMatcher(None, term, desc_lower).ratio()
            
            # Boost score for context matches
            if any(ctx in desc_lower for ctx in context_keywords):
                score *= 1.5
            
            max_score = max(max_score, score)
        
        # Only include codes with reasonable similarity
        if max_score > 0.3:
            code_scores[row['icd10_code']] = (max_score, row)
    
    # Sort by score and return top candidates
    sorted_codes = sorted(code_scores.values(), key=lambda x: x[0], reverse=True)
    return [row for _, row in sorted_codes[:limit]]

def get_fallback_followup(phrase: str) -> str:
    """Generate fallback follow-up suggestions when AI returns None."""
    phrase_lower = phrase.lower()
    
    # Check for predefined follow-ups
    for condition, followup in PREDEFINED_FOLLOWUPS.items():
        if condition in phrase_lower:
            return followup
    
    # Check for common medical terms that need specification
    if any(term in phrase_lower for term in ['diabetes', 'dm']):
        return PREDEFINED_FOLLOWUPS['diabetes']
    elif any(term in phrase_lower for term in ['heart failure', 'chf']):
        return PREDEFINED_FOLLOWUPS['heart failure']
    elif any(term in phrase_lower for term in ['copd', 'chronic obstructive']):
        return PREDEFINED_FOLLOWUPS['COPD']
    elif any(term in phrase_lower for term in ['hypertension', 'htn', 'high blood pressure']):
        return PREDEFINED_FOLLOWUPS['hypertension']
    elif any(term in phrase_lower for term in ['pneumonia', 'lung infection']):
        return PREDEFINED_FOLLOWUPS['pneumonia']
    elif any(term in phrase_lower for term in ['stroke', 'cva']):
        return PREDEFINED_FOLLOWUPS['stroke']
    elif any(term in phrase_lower for term in ['kidney', 'renal']):
        return PREDEFINED_FOLLOWUPS['kidney disease']
    elif any(term in phrase_lower for term in ['infection', 'uti', 'sepsis']):
        return PREDEFINED_FOLLOWUPS['infection']
    elif any(term in phrase_lower for term in ['fracture', 'break', 'broken']):
        return PREDEFINED_FOLLOWUPS['fracture']
    elif any(term in phrase_lower for term in ['wound', 'ulcer', 'sore']):
        return PREDEFINED_FOLLOWUPS['wound']
    elif any(term in phrase_lower for term in ['pain', 'ache']):
        return PREDEFINED_FOLLOWUPS['pain']
    
    # Generic fallback for broad terms
    return "Could you provide more specific details about the condition, such as: acute vs chronic, location, severity, or any complications?"

def ai_followup_question_enhanced(phrase: str, pdgm_response: str = "") -> str:
    """Enhanced follow-up question generation with fallback logic."""
    
    # If PDGM response is empty or indicates no match, use fallback
    if not pdgm_response or any(indicator in pdgm_response.lower() for indicator in 
                               ['no matching codes', 'error', 'not found', 'openai error']):
        return get_fallback_followup(phrase)
    
    # Check for predefined follow-ups first (faster and more reliable)
    fallback = get_fallback_followup(phrase)
    if fallback != "Could you provide more specific details about the condition, such as: acute vs chronic, location, severity, or any complications?":
        return fallback
    
    # If we have a good PDGM response, we can still try AI for more specific follow-ups
    # But we'll return the fallback if AI fails or returns "None"
    return fallback

def validate_pdgm_response(response: str) -> bool:
    """Validate that a PDGM response contains proper structure."""
    if not response:
        return False
    
    # Check for required PDGM response elements
    required_elements = ['Focus of Care:', 'ICD-10:', 'PDGM Group:']
    return any(element in response for element in required_elements)

# Test function to verify the enhancements work
def test_enhanced_functions():
    """Test the enhanced functions with CHF exacerbation."""
    
    # Test synonym expansion
    expanded = expand_with_medical_synonyms("CHF exacerbation")
    print("Expanded terms for 'CHF exacerbation':")
    for term in expanded:
        print(f"  - {term}")
    
    # Test context extraction
    contexts = extract_context_keywords("CHF exacerbation")
    print(f"\nContext keywords: {contexts}")
    
    # Test fallback follow-up
    followup = get_fallback_followup("CHF exacerbation")
    print(f"\nFallback follow-up: {followup}")

if __name__ == "__main__":
    test_enhanced_functions()

