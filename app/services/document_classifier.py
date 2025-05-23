from typing import Dict, List, Tuple
from agents.base_agent import GeneralAgent
import json
import re

class DocumentClassifier:
    """Classifies documents and determines which policy checks are applicable"""
    
    def __init__(self):
        self.loan_type_keywords = {
            'mortgage': [
                'mortgage', 'home loan', 'property', 'real estate', 'house', 
                'dwelling', 'residence', 'ltv', 'loan-to-value', 'appraisal',
                'title', 'deed', 'escrow', 'homeowner', 'property tax'
            ],
            'auto_loan': [
                'auto loan', 'vehicle', 'car', 'automobile', 'truck', 'motorcycle',
                'vin', 'make', 'model', 'mileage', 'vehicle identification',
                'dealer', 'trade-in', 'vehicle value'
            ],
            'credit_card': [
                'credit card', 'revolving', 'credit limit', 'apr', 'cash advance',
                'balance transfer', 'minimum payment', 'grace period', 'annual fee',
                'rewards', 'cashback', 'credit line'
            ],
            'personal_loan': [
                'personal loan', 'unsecured', 'signature loan', 'installment',
                'consolidation', 'fixed rate', 'term loan'
            ],
            'business_loan': [
                'business loan', 'commercial', 'sba', 'working capital', 'equipment finance',
                'business credit', 'revenue', 'cash flow', 'dscr', 'business plan',
                'financial statements', 'tax returns'
            ],
            'student_loan': [
                'student loan', 'education', 'tuition', 'school', 'university',
                'college', 'degree', 'enrollment', 'cosigner', 'deferment'
            ]
        }
    
    def classify_document(self, document_content: Dict) -> Dict:
        """Classify document type and extract key characteristics"""
        # Extract all text content
        text_content = self._extract_all_text(document_content)
        
        # Use AI to classify
        classification = self._ai_classify(text_content)
        
        # Verify with keyword matching
        keyword_scores = self._keyword_analysis(text_content)
        
        # Combine results
        final_classification = self._combine_classifications(classification, keyword_scores)
        
        return final_classification
    
    def _extract_all_text(self, document_content: Dict) -> str:
        """Extract all text from document including tables"""
        text_parts = []
        
        # Main text content
        if document_content.get('text_content'):
            text_parts.append(document_content['text_content'])
        
        # Text from parsed document
        if document_content.get('parsed_content', {}).get('text_content'):
            text_parts.append(document_content['parsed_content']['text_content'])
        
        # Table content
        for table in document_content.get('parsed_content', {}).get('tables', []):
            if table.get('data'):
                for row in table['data']:
                    text_parts.extend([str(cell) for cell in row if cell])
        
        return ' '.join(text_parts)
    
    def _ai_classify(self, text: str) -> Dict:
        """Use AI to classify document type"""
        agent = GeneralAgent("document_classifier")
        
        prompt = f"""
        Analyze this document and determine its type and characteristics.
        
        Document text (first 3000 chars):
        {text[:3000]}
        
        Classify the document and extract key information:
        
        Return JSON:
        {{
            "primary_loan_type": "mortgage/auto_loan/credit_card/personal_loan/business_loan/student_loan/other",
            "confidence": 0.0-1.0,
            "loan_purpose": "purchase/refinance/cash_out/consolidation/other",
            "applicant_type": "individual/joint/business",
            "property_type": "if mortgage: single_family/condo/multi_family/commercial/land",
            "loan_amount_mentioned": "amount if found",
            "key_identifiers": ["list of key identifying phrases found"],
            "detected_sections": ["application info", "financial info", "property info", etc],
            "is_application": true/false,
            "is_approval": true/false,
            "is_disclosure": true/false
        }}
        
        Return only JSON.
        """
        
        try:
            response = agent.process(prompt)
            return json.loads(response)
        except:
            return {
                "primary_loan_type": "unknown",
                "confidence": 0.0,
                "error": "Classification failed"
            }
    
    def _keyword_analysis(self, text: str) -> Dict[str, float]:
        """Analyze keyword presence for each loan type"""
        text_lower = text.lower()
        scores = {}
        
        for loan_type, keywords in self.loan_type_keywords.items():
            # Count keyword matches
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            # Weight by keyword length (longer phrases are more specific)
            weighted_matches = sum(
                len(keyword.split()) for keyword in keywords 
                if keyword in text_lower
            )
            # Normalize score
            scores[loan_type] = weighted_matches / len(keywords) if keywords else 0
        
        return scores
    
    def _combine_classifications(self, ai_result: Dict, keyword_scores: Dict) -> Dict:
        """Combine AI and keyword analysis results"""
        # Start with AI classification
        result = ai_result.copy()
        
        # Add keyword analysis
        result['keyword_scores'] = keyword_scores
        
        # Determine final loan type with confidence adjustment
        ai_type = ai_result.get('primary_loan_type', 'unknown')
        ai_confidence = ai_result.get('confidence', 0.5)
        
        # If AI confidence is low, check keyword scores
        if ai_confidence < 0.7 and keyword_scores:
            best_keyword_type = max(keyword_scores.items(), key=lambda x: x[1])
            if best_keyword_type[1] > 0.3:  # Significant keyword presence
                result['primary_loan_type'] = best_keyword_type[0]
                result['confidence'] = (ai_confidence + best_keyword_type[1]) / 2
                result['classification_method'] = 'combined'
            else:
                result['classification_method'] = 'ai_primary'
        else:
            result['classification_method'] = 'ai_primary'
        
        return result
    
    def determine_applicable_agents(self, document_classification: Dict, 
                                  policy_checks: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Determine which agents are applicable based on document type"""
        loan_type = document_classification.get('primary_loan_type', 'unknown')
        applicable_checks = []
        skipped_checks = []
        
        for check in policy_checks:
            relevance = self._calculate_check_relevance(check, document_classification)
            
            if relevance >= 0.6:  # Raised threshold for better filtering
                check['relevance_score'] = relevance
                applicable_checks.append(check)
            else:
                check['relevance_score'] = relevance
                check['skip_reason'] = self._get_skip_reason(check, loan_type)
                skipped_checks.append(check)
        
        return applicable_checks, skipped_checks
    
    def _calculate_check_relevance(self, check: Dict, classification: Dict) -> float:
        """Calculate relevance score for a check based on document type"""
        loan_type = classification.get('primary_loan_type', 'unknown')
        check_desc = check.get('description', '').lower()
        check_type = check.get('check_type', '').lower()
        criteria = check.get('criteria', '').lower()
        
        # Universal checks that apply to all loan types
        universal_keywords = [
            'credit score', 'fico', 'income', 'employment', 'debt', 'dti',
            'identification', 'fraud', 'compliance', 'eligibility', 'age',
            'citizenship', 'residence', 'bankruptcy', 'default'
        ]
        
        # Type-specific keywords
        type_specific = {
            'mortgage': ['ltv', 'property', 'appraisal', 'title', 'home', 'dwelling',
                        'escrow', 'pmi', 'hazard insurance', 'flood', 'hoa'],
            'auto_loan': ['vehicle', 'car', 'auto', 'vin', 'mileage', 'make', 'model',
                         'dealer', 'trade-in', 'gap insurance', 'vehicle value'],
            'credit_card': ['credit limit', 'apr', 'revolving', 'minimum payment',
                           'cash advance', 'balance transfer', 'annual fee'],
            'business_loan': ['business', 'commercial', 'revenue', 'cash flow', 'dscr',
                             'business credit', 'financial statements', 'sba'],
            'personal_loan': ['personal', 'unsecured', 'signature', 'installment'],
            'student_loan': ['student', 'education', 'school', 'enrollment', 'degree']
        }
        
        # Check if it's a universal check
        check_text = f"{check_desc} {check_type} {criteria}"
        universal_match_count = sum(1 for keyword in universal_keywords if keyword in check_text)
        
        if universal_match_count > 0:  # Has universal keywords
            return 0.9  # High relevance for universal checks
        
        # Check type-specific relevance
        if loan_type in type_specific:
            specific_keywords = type_specific[loan_type]
            specific_score = sum(1 for keyword in specific_keywords if keyword in check_text) / len(specific_keywords)
            
            # Check for exclusion keywords from other types
            other_types_score = 0
            for other_type, other_keywords in type_specific.items():
                if other_type != loan_type:
                    other_score = sum(1 for keyword in other_keywords if keyword in check_text) / len(other_keywords)
                    other_types_score = max(other_types_score, other_score)
            
            # High specific score and low other types score = relevant
            if specific_score > 0.1 and other_types_score < 0.1:
                return 0.7 + (0.3 * specific_score)
            # Has keywords from other loan types = not relevant
            elif other_types_score > 0.2:
                return 0.2 - (0.2 * other_types_score)
            # Neutral
            else:
                return 0.5
        
        # Unknown loan type - include most checks
        return 0.6
    
    def _get_skip_reason(self, check: Dict, loan_type: str) -> str:
        """Generate explanation for why check is skipped"""
        check_desc = check.get('description', '').lower()
        
        # Common skip reasons
        if 'property' in check_desc or 'ltv' in check_desc or 'appraisal' in check_desc:
            if loan_type != 'mortgage':
                return f"Property-related check not applicable to {loan_type}"
        
        elif 'vehicle' in check_desc or 'car' in check_desc or 'auto' in check_desc:
            if loan_type != 'auto_loan':
                return f"Vehicle-related check not applicable to {loan_type}"
        
        elif 'revolving' in check_desc or 'credit limit' in check_desc:
            if loan_type != 'credit_card':
                return f"Credit card-specific check not applicable to {loan_type}"
        
        elif 'business' in check_desc or 'commercial' in check_desc or 'dscr' in check_desc:
            if loan_type != 'business_loan':
                return f"Business loan check not applicable to {loan_type}"
        
        elif 'education' in check_desc or 'enrollment' in check_desc:
            if loan_type != 'student_loan':
                return f"Student loan check not applicable to {loan_type}"
        
        return f"Check not relevant for {loan_type} application"