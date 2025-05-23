from typing import List, Dict
from agents.base_agent import GeneralAgent
import json
import re
import concurrent.futures
import hashlib
from functools import lru_cache

class PolicyAnalyzer:
    """Universal policy analyzer for any type of compliance or assessment requirement"""
    
    def extract_checks(self, policy_text: str, domain_hint: str = None) -> List[Dict]:
        """Extract individual checks from any type of policy text using optimized chunking"""
        # First, extract thresholds using regex as a safety net
        regex_checks = self._extract_thresholds_with_regex(policy_text, domain_hint)
        
        # Fast path for short documents
        if len(policy_text) < 3000:  # Short enough for single pass
            llm_checks = self._extract_checks_single_pass(policy_text, domain_hint)
        else:
            # Smart chunking for longer documents
            chunks = self._smart_chunk_policy_text(policy_text)
            
            # If still only one chunk, use single pass
            if len(chunks) == 1:
                llm_checks = self._extract_checks_single_pass(chunks[0], domain_hint)
            else:
                llm_checks = []
                
                # Process chunks in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    # Submit all chunks for processing
                    future_to_chunk = {
                        executor.submit(
                            self._extract_checks_from_chunk_cached,
                            chunk,
                            domain_hint,
                            i+1,
                            len(chunks)
                        ): i for i, chunk in enumerate(chunks)
                    }
                    
                    # Collect results as they complete
                    for future in concurrent.futures.as_completed(future_to_chunk):
                        try:
                            chunk_checks = future.result()
                            llm_checks.extend(chunk_checks)
                        except Exception as e:
                            print(f"Error processing chunk: {e}")
        
        # Combine LLM and regex-extracted checks
        all_checks = llm_checks + regex_checks
        
        # Fast deduplication
        unique_checks = self._fast_deduplicate_checks(all_checks)
        
        # Light enhancement (skip if too many checks to avoid slowdown)
        if len(unique_checks) < 50:
            enhanced_checks = self._enhance_checks(unique_checks, policy_text)
        else:
            enhanced_checks = self._light_enhance_checks(unique_checks)
        
        return enhanced_checks
    
    def _extract_checks_single_pass(self, text: str, domain_hint: str = None) -> List[Dict]:
        """Extract all checks in a single LLM call for short documents"""
        agent = GeneralAgent("universal_policy_extraction")
        
        prompt = f"""
        You are a universal policy analysis expert. Analyze this policy document and extract ALL compliance checks, assessments, and requirements.
        
        Policy Text:
        {text}
        
        Domain Context: {domain_hint or "Auto-detect from content"}
        
        CRITICAL: Extract EVERY SINGLE requirement, threshold, condition, and criterion.
        
        MUST EXTRACT:
        1. EVERY number mentioned (percentages, amounts, ratios, scores, days, etc.)
        2. EVERY comparison (greater than, less than, equal to, between, minimum, maximum)
        3. EVERY condition (if/then, when, unless, provided that, subject to)
        4. EVERY requirement (must, shall, should, required, needs to, has to, will)
        5. EVERY qualification (eligible, qualified, acceptable, satisfactory)
        6. EVERY restriction (prohibited, not allowed, excluded, limited to)
        7. EVERY time constraint (within X days, annually, quarterly, by date)
        8. EVERY documentation requirement (provide, submit, evidence, proof)
        
        For credit policies specifically, look for:
        - Loan-to-value (LTV) ratios
        - Debt service coverage ratios (DSCR)
        - Credit score requirements
        - Income requirements
        - Employment history requirements
        - Down payment requirements
        - Interest rate criteria
        - Loan term limits
        - Maximum/minimum loan amounts
        - Geographic restrictions
        - Property type restrictions
        - Occupancy requirements
        - Insurance requirements
        - Appraisal requirements
        - Title requirements
        
        IMPORTANT: Create a separate check for EACH threshold, even if they're in the same sentence.
        Example: "LTV must be below 80% and credit score above 700" = 2 separate checks
        
        For each requirement found, return JSON array:
        [{{
            "check_type": "descriptive name for this type of check (e.g., 'debt_to_equity_ratio', 'minimum_revenue_requirement')",
            "description": "clear description of what needs to be checked",
            "criteria": "specific criteria, threshold, standard, or requirement that must be met",
            "formula": "for ratios/calculations: the exact formula (e.g., 'total_debt / total_equity')",
            "threshold": "for quantitative checks: the specific threshold (e.g., '< 2.5', '> $1M', '>= 80%')",
            "data_fields": ["list", "of", "data", "fields", "needed"],
            "priority": "critical/high/medium/low",
            "complexity": "simple/quantitative/comparative/multi_step",
            "domain": "financial/esg/regulatory/risk/operational/market/strategic/hr/technology/supply_chain/general"
        }}]
        
        Return only JSON array, no other text.
        """
        
        try:
            response = agent.process(prompt)
            checks = json.loads(response)
            if isinstance(checks, list):
                # Add missing fields and ensure check_type exists
                for check in checks:
                    if 'check_type' not in check:
                        # Generate check_type from description
                        desc = check.get('description', 'unknown_check')
                        check['check_type'] = self._generate_check_type(desc)
                    if 'priority' not in check:
                        check['priority'] = self._determine_priority(check)
                    if 'complexity' not in check:
                        check['complexity'] = self._determine_complexity(check)
                    if 'domain' not in check:
                        check['domain'] = self._determine_domain(check)
                    if 'data_fields' not in check:
                        check['data_fields'] = []
                return checks
            return []
        except json.JSONDecodeError:
            return []
    
    def _smart_chunk_policy_text(self, text: str, target_chunk_size: int = 3000) -> List[str]:
        """Smart chunking that minimizes splits and respects document structure"""
        # Clean text
        text = text.strip()
        
        # If already small enough, return as is
        if len(text) <= target_chunk_size:
            return [text]
        
        # Try to split by major sections first
        major_sections = self._split_by_major_sections(text)
        
        # If we got reasonable sections, use them
        if len(major_sections) > 1 and all(len(s) < target_chunk_size * 1.5 for s in major_sections):
            return major_sections
        
        # Otherwise, fall back to intelligent chunking
        return self._intelligent_chunk(text, target_chunk_size)
    
    def _split_by_major_sections(self, text: str) -> List[str]:
        """Split text by major section headers"""
        # Look for major section patterns
        section_patterns = [
            r'\n\s*(?:Section|SECTION|Chapter|CHAPTER)\s+\d+[:\.\s]',
            r'\n\s*\d+\.\s+[A-Z][A-Za-z\s]+(?:\n|:)',
            r'\n\s*[A-Z][A-Z\s]+(?:\n|:)'
        ]
        
        sections = []
        remaining_text = text
        
        for pattern in section_patterns:
            matches = list(re.finditer(pattern, remaining_text))
            if len(matches) > 1:  # Found multiple sections
                for i in range(len(matches)):
                    start = matches[i].start()
                    end = matches[i+1].start() if i+1 < len(matches) else len(remaining_text)
                    section = remaining_text[start:end].strip()
                    if section:
                        sections.append(section)
                
                if sections:
                    return sections
        
        return [text]  # No clear sections found
    
    def _intelligent_chunk(self, text: str, target_size: int) -> List[str]:
        """Intelligent chunking that minimizes splits"""
        chunks = []
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= target_size:
                current_chunk += ("\n\n" + para) if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If paragraph itself is too large, split it
                if len(para) > target_size:
                    sentences = para.split('. ')
                    temp_chunk = ""
                    for sent in sentences:
                        if len(temp_chunk) + len(sent) + 2 <= target_size:
                            temp_chunk += ('. ' + sent) if temp_chunk else sent
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk + '.')
                            temp_chunk = sent
                    if temp_chunk:
                        current_chunk = temp_chunk
                else:
                    current_chunk = para
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _chunk_policy_text(self, text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
        """Split policy text into overlapping chunks for better extraction"""
        # Clean text
        text = text.strip()
        
        # If text is short, return as single chunk
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        
        # Try to split by sections first
        section_patterns = [
            r'\n\s*\d+\.\s+',  # Numbered sections
            r'\n\s*[A-Z][a-z]*\.\s+',  # Lettered sections
            r'\n\s*(?:Section|Article|Chapter)\s+\d+',  # Formal sections
            r'\n\s*[•●▪▫■□◆◇]\s+',  # Bullet points
            r'\n\s*[-–—]\s+',  # Dashes
            r'\n{2,}',  # Double line breaks
        ]
        
        # Find all section boundaries
        boundaries = [0]
        for pattern in section_patterns:
            matches = list(re.finditer(pattern, text))
            boundaries.extend([m.start() for m in matches])
        
        boundaries.append(len(text))
        boundaries = sorted(set(boundaries))
        
        # Create chunks based on boundaries
        current_chunk = ""
        
        for i in range(len(boundaries) - 1):
            section = text[boundaries[i]:boundaries[i+1]].strip()
            
            if len(current_chunk) + len(section) <= chunk_size:
                current_chunk += "\n" + section if current_chunk else section
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = section
                
                # If section itself is too large, split it
                if len(section) > chunk_size:
                    words = section.split()
                    temp_chunk = ""
                    
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 <= chunk_size:
                            temp_chunk += " " + word if temp_chunk else word
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk)
                            temp_chunk = word
                    
                    current_chunk = temp_chunk
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # Add overlap between chunks
        if len(chunks) > 1 and overlap > 0:
            overlapped_chunks = []
            for i in range(len(chunks)):
                if i == 0:
                    # First chunk: add beginning of next chunk
                    chunk = chunks[i]
                    if i + 1 < len(chunks):
                        next_words = chunks[i + 1].split()[:overlap//10]
                        chunk += "\n...\n" + " ".join(next_words)
                    overlapped_chunks.append(chunk)
                elif i == len(chunks) - 1:
                    # Last chunk: add end of previous chunk
                    prev_words = chunks[i - 1].split()[-overlap//10:]
                    chunk = " ".join(prev_words) + "\n...\n" + chunks[i]
                    overlapped_chunks.append(chunk)
                else:
                    # Middle chunks: add both overlaps
                    prev_words = chunks[i - 1].split()[-overlap//20:]
                    next_words = chunks[i + 1].split()[:overlap//20]
                    chunk = " ".join(prev_words) + "\n...\n" + chunks[i] + "\n...\n" + " ".join(next_words)
                    overlapped_chunks.append(chunk)
            
            return overlapped_chunks
        
        return chunks
    
    @lru_cache(maxsize=32)
    def _extract_checks_from_chunk_cached(self, chunk: str, domain_hint: str, chunk_number: int, total_chunks: int) -> List[Dict]:
        """Cached version of chunk extraction to avoid reprocessing identical content"""
        return self._extract_checks_from_chunk(chunk, domain_hint, chunk_number, total_chunks)
    
    def _extract_checks_from_chunk(self, chunk: str, domain_hint: str, chunk_number: int, total_chunks: int) -> List[Dict]:
        """Extract checks from a single chunk of text"""
        agent = GeneralAgent("universal_policy_extraction")
        
        prompt = f"""
        You are a universal policy analysis expert. Analyze this policy document and extract ALL compliance checks, assessments, and requirements.
        
        Policy Text:
        {chunk}
        
        Domain Context: {domain_hint or "Auto-detect from content"}
        
        Processing chunk {chunk_number} of {total_chunks}
        
        CRITICAL INSTRUCTION: Extract EVERY SINGLE numeric value, comparison, or requirement as a separate check.
        
        SCAN FOR THESE PATTERNS:
        1. ANY NUMBER + ANY UNIT (e.g., "80%", "$100,000", "30 days", "5 years", "700 score")
        2. ANY COMPARISON WORD (must be, should be, cannot exceed, at least, no more than, minimum, maximum)
        3. ANY RATIO (X to Y, X/Y, X:Y, X per Y)
        4. ANY RANGE (between X and Y, from X to Y, X-Y)
        5. ANY LIST OF REQUIREMENTS (even if comma-separated in one sentence)
        6. ANY CONDITIONAL (if, when, unless, provided that, subject to, in case of)
        7. ANY ELIGIBILITY CRITERIA (eligible, qualified, acceptable, approved)
        8. ANY PROHIBITION (not allowed, prohibited, excluded, restricted)
        9. ANY DOCUMENTATION (must provide, submit, evidence of, proof of, certification)
        10. ANY TIME LIMIT (within, by, before, after, no later than)
        
        FOR CREDIT POLICIES, SPECIFICALLY EXTRACT:
        - LTV/CLTV requirements (e.g., "LTV not to exceed 80%")
        - DSCR requirements (e.g., "minimum DSCR of 1.25")
        - Credit score thresholds (e.g., "minimum FICO 700")
        - Income requirements (e.g., "minimum income $50,000")
        - Employment duration (e.g., "2 years employment history")
        - Down payment percentages (e.g., "20% down payment required")
        - Interest rate caps/floors (e.g., "maximum rate 7%")
        - Loan term limits (e.g., "maximum 30 years")
        - Loan amount limits (e.g., "minimum $50,000, maximum $1,000,000")
        - Property requirements (e.g., "owner-occupied only")
        - Geographic restrictions (e.g., "properties in state only")
        - Insurance requirements (e.g., "hazard insurance required")
        - Reserve requirements (e.g., "6 months reserves")
        - Debt-to-income ratios (e.g., "DTI not to exceed 43%")
        - Appraisal requirements (e.g., "appraisal within 90 days")
        
        RULE: If you see a number, create a check. If you see a requirement word, create a check.
        
        For each check/requirement you identify:
        1. Create a descriptive check_type that captures the specific nature of the check
        2. Be flexible - this could be anything: ESG assessment, financial ratio, regulatory compliance, risk evaluation, operational metric, etc.
        3. Extract the EXACT criteria, formula, or standard that must be met
        4. For ratios: include the formula (e.g., "debt/equity") and threshold (e.g., "< 2.5")
        5. For quantitative: include the metric, operator, and value (e.g., "revenue > $1M")
        6. For qualitative: include evaluation criteria and what constitutes "satisfactory"
        
        Return a JSON array where each check has:
        {{
            "check_type": "descriptive name for this type of check (e.g., 'debt_to_equity_ratio', 'minimum_revenue_requirement', 'management_quality_assessment')",
            "description": "clear description of what needs to be checked or assessed",
            "criteria": "specific criteria, threshold, standard, or requirement that must be met",
            "formula": "for ratios/calculations: the exact formula (e.g., 'total_debt / total_equity')",
            "threshold": "for quantitative checks: the specific threshold (e.g., '< 2.5', '> $1M', '>= 80%')",
            "data_fields": ["list", "of", "data", "fields", "needed"],
            "priority": "critical/high/medium/low",
            "complexity": "simple/quantitative/comparative/multi_step",
            "domain": "financial/esg/regulatory/risk/operational/market/strategic/hr/technology/supply_chain/general",
            "agent_instructions": "detailed instructions for how to perform this specific check",
            "success_criteria": "what constitutes passing this check",
            "failure_impact": "consequences if this check fails",
            "benchmarks": "relevant industry standards or benchmarks if applicable"
        }}
        
        Be EXTREMELY comprehensive - extract EVERY requirement, including:
        - All financial ratios mentioned
        - All numeric thresholds or limits
        - All qualitative requirements
        - All comparative benchmarks
        - All conditional or multi-step requirements
        - All time-based constraints
        - All documentation needs
        - All implicit requirements (things that are implied but not directly stated)
        
        EXTRACTION RULES:
        1. EVERY sentence with a number = at least one check
        2. EVERY sentence with "must", "shall", "should", "required" = at least one check  
        3. EVERY bullet point or list item = separate check
        4. EVERY table row with a threshold = separate check
        5. EVERY parenthetical with a requirement = separate check
        6. Split compound requirements (sentences with "and", "or") into multiple checks
        7. Extract implicit requirements (e.g., "standard terms" implies specific requirements)
        8. Extract negative requirements (e.g., "may not", "shall not", "prohibited")
        
        TARGET: Extract 10-20 checks per page of text. More is better than less.
        
        If the text mentions any of these words, it MUST generate a check:
        - Numbers (any digit)
        - Percent/percentage (%) 
        - Dollar amounts ($)
        - Ratios (X:Y, X/Y)
        - Scores (FICO, credit score)
        - Time periods (days, months, years)
        - Must/shall/should/required/needs
        - Minimum/maximum/at least/no more than
        - Eligible/qualified/acceptable
        - Prohibited/restricted/not allowed
        
        Return only the JSON array, no other text.
        """
        
        try:
            response = agent.process(prompt)
            checks = json.loads(response)
            if isinstance(checks, list):
                # Ensure all required fields exist
                for check in checks:
                    if 'check_type' not in check:
                        desc = check.get('description', 'unknown_check')
                        check['check_type'] = self._generate_check_type(desc)
                    if 'priority' not in check:
                        check['priority'] = self._determine_priority(check)
                    if 'complexity' not in check:
                        check['complexity'] = self._determine_complexity(check)
                    if 'domain' not in check:
                        check['domain'] = self._determine_domain(check)
                    if 'data_fields' not in check:
                        check['data_fields'] = []
                    if 'description' not in check:
                        check['description'] = check.get('check_type', 'Unknown requirement')
                    if 'criteria' not in check:
                        check['criteria'] = 'Not specified'
                return checks
            return []
        except json.JSONDecodeError:
            # Fallback: return empty list if JSON parsing fails
            return []
    
    def _fast_deduplicate_checks(self, checks: List[Dict]) -> List[Dict]:
        """Fast deduplication using hashing"""
        seen_hashes = set()
        unique_checks = []
        
        for check in checks:
            # Create a hash of the normalized description
            normalized = self._normalize_check_description(check.get('description', ''))
            check_hash = hashlib.md5(normalized.encode()).hexdigest()
            
            if check_hash not in seen_hashes:
                seen_hashes.add(check_hash)
                unique_checks.append(check)
        
        return unique_checks
    
    def _deduplicate_checks(self, checks: List[Dict]) -> List[Dict]:
        """Remove duplicate checks based on similarity"""
        unique_checks = []
        seen_descriptions = set()
        
        for check in checks:
            # Create a normalized version for comparison
            normalized = self._normalize_check_description(check.get('description', ''))
            
            # Check if we've seen a very similar check
            is_duplicate = False
            for seen in seen_descriptions:
                if self._calculate_similarity(normalized, seen) > 0.85:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_checks.append(check)
                seen_descriptions.add(normalized)
        
        return unique_checks
    
    def _normalize_check_description(self, description: str) -> str:
        """Normalize description for comparison"""
        # Convert to lowercase
        normalized = description.lower()
        
        # Remove common variations
        replacements = {
            'must be': 'should be',
            'shall be': 'should be',
            'needs to be': 'should be',
            'required to be': 'should be',
            'greater than': '>',
            'less than': '<',
            'at least': '>=',
            'at most': '<=',
            'no more than': '<=',
            'no less than': '>=',
            'minimum': 'min',
            'maximum': 'max'
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        # Simple word-based similarity
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _light_enhance_checks(self, checks: List[Dict]) -> List[Dict]:
        """Light enhancement without full text search for performance"""
        enhanced_checks = []
        
        for check in checks:
            enhanced = check.copy()
            
            # Ensure all required fields are present
            if 'priority' not in enhanced:
                enhanced['priority'] = self._determine_priority(enhanced)
            
            if 'complexity' not in enhanced:
                enhanced['complexity'] = self._determine_complexity(enhanced)
            
            if 'domain' not in enhanced:
                enhanced['domain'] = self._determine_domain(enhanced)
            
            enhanced_checks.append(enhanced)
        
        return enhanced_checks
    
    def _enhance_checks(self, checks: List[Dict], full_text: str) -> List[Dict]:
        """Enhance checks with additional context from the full document"""
        enhanced_checks = []
        
        for check in checks:
            enhanced = check.copy()
            
            # Try to find related context in the full text
            description = check.get('description', '')
            keywords = self._extract_keywords(description)
            
            # Search for additional context
            context_snippets = []
            for keyword in keywords:
                # Find sentences containing the keyword
                sentences = full_text.split('.')
                for sentence in sentences:
                    if keyword.lower() in sentence.lower() and len(sentence) < 300:
                        context_snippets.append(sentence.strip())
            
            # Add context if found
            if context_snippets:
                enhanced['additional_context'] = list(set(context_snippets))[:3]
            
            # Ensure all required fields are present
            if 'priority' not in enhanced:
                enhanced['priority'] = self._determine_priority(enhanced)
            
            if 'complexity' not in enhanced:
                enhanced['complexity'] = self._determine_complexity(enhanced)
            
            if 'domain' not in enhanced:
                enhanced['domain'] = self._determine_domain(enhanced)
            
            enhanced_checks.append(enhanced)
        
        return enhanced_checks
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        # Remove common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 
                     'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall'}
        
        words = text.lower().split()
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        
        return keywords[:5]  # Return top 5 keywords
    
    def _determine_priority(self, check: Dict) -> str:
        """Determine priority based on check content"""
        description = check.get('description', '').lower()
        criteria = check.get('criteria', '').lower()
        
        critical_indicators = ['must', 'shall', 'required', 'mandatory', 'critical', 'essential']
        high_indicators = ['should', 'important', 'significant', 'key', 'primary']
        
        for indicator in critical_indicators:
            if indicator in description or indicator in criteria:
                return 'critical'
        
        for indicator in high_indicators:
            if indicator in description or indicator in criteria:
                return 'high'
        
        return 'medium'
    
    def _determine_complexity(self, check: Dict) -> str:
        """Determine complexity based on check content"""
        description = check.get('description', '').lower()
        
        if any(word in description for word in ['calculate', 'ratio', 'formula', 'percentage']):
            return 'quantitative'
        elif any(word in description for word in ['compare', 'benchmark', 'relative', 'versus']):
            return 'comparative'
        elif any(word in description for word in ['if', 'then', 'when', 'after', 'before']):
            return 'multi_step'
        
        return 'simple'
    
    def _determine_domain(self, check: Dict) -> str:
        """Determine domain based on check content"""
        description = check.get('description', '').lower()
        check_type = check.get('check_type', '').lower()
        
        domain_keywords = {
            'financial': ['financial', 'revenue', 'profit', 'cash', 'debt', 'equity'],
            'esg': ['environmental', 'social', 'governance', 'sustainability', 'carbon'],
            'regulatory': ['compliance', 'regulation', 'legal', 'requirement', 'standard'],
            'risk': ['risk', 'exposure', 'volatility', 'uncertainty'],
            'operational': ['operational', 'process', 'efficiency', 'performance']
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in description or keyword in check_type for keyword in keywords):
                return domain
        
        return 'general'
    
    def _extract_thresholds_with_regex(self, text: str, domain_hint: str = None) -> List[Dict]:
        """Extract thresholds using regex patterns as a safety net"""
        checks = []
        
        # Common threshold patterns
        patterns = [
            # Percentages
            (r'(\w+(?:\s+\w+)*?)\s*(?:must be|should be|cannot exceed|not to exceed|maximum of|minimum of|at least|no more than|greater than|less than)\s*(\d+(?:\.\d+)?%)\s*', 'percentage_threshold'),
            # Dollar amounts
            (r'(\w+(?:\s+\w+)*?)\s*(?:must be|should be|cannot exceed|not to exceed|maximum of|minimum of|at least|no more than)\s*\$([\d,]+(?:\.\d+)?(?:M|K|million|thousand)?)', 'dollar_threshold'),
            # Ratios (X:Y or X to Y)
            (r'(\w+(?:\s+\w+)*?)\s*(?:ratio|must be|should be)\s*(?:of\s+)?(\d+(?:\.\d+)?)[\s:-]to[\s:-](\d+(?:\.\d+)?)', 'ratio_threshold'),
            # Numeric scores
            (r'(?:minimum|maximum)\s+(FICO|credit score|score)\s*(?:of\s+)?(\d+)', 'score_threshold'),
            # Time periods
            (r'(?:within|in|after|before)\s+(\d+)\s+(days?|months?|years?)', 'time_threshold'),
            # General numbers with context
            (r'(\w+(?:\s+\w+)*?)\s*(?:equal to|equals|=|≥|≤|>=|<=|>|<)\s*(\d+(?:\.\d+)?)', 'numeric_threshold'),
            # LTV/CLTV specific
            (r'(?:LTV|CLTV|loan[- ]to[- ]value)\s*(?:ratio)?\s*(?:must be|should be|cannot exceed|maximum of|≤|<=|<)\s*(\d+(?:\.\d+)?%?)', 'ltv_threshold'),
            # DSCR specific
            (r'(?:DSCR|debt service coverage ratio)\s*(?:must be|should be|minimum of|≥|>=|>)\s*(\d+(?:\.\d+)?)', 'dscr_threshold'),
            # DTI specific
            (r'(?:DTI|debt[- ]to[- ]income)\s*(?:ratio)?\s*(?:must be|should be|cannot exceed|maximum of|≤|<=|<)\s*(\d+(?:\.\d+)?%?)', 'dti_threshold'),
        ]
        
        # Extract using patterns
        for pattern, check_type_base in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    field_name = groups[0].strip()
                    value = groups[1] if len(groups) == 2 else f"{groups[1]}:{groups[2]}"
                    
                    # Create check
                    check = {
                        'check_type': f'{check_type_base}_{field_name.lower().replace(" ", "_")}',
                        'description': f'Check {field_name} against threshold',
                        'criteria': match.group(0).strip(),
                        'threshold': value,
                        'data_fields': [field_name.lower().replace(" ", "_")],
                        'priority': 'high',
                        'complexity': 'quantitative',
                        'domain': domain_hint or 'financial',
                        'source': 'regex_extraction'
                    }
                    checks.append(check)
        
        # Extract list items that might be requirements
        list_patterns = [
            r'^\s*[•·▪▫◦‣⁃]\s+(.+)$',  # Bullet points
            r'^\s*\d+\.\s+(.+)$',  # Numbered lists
            r'^\s*[a-z]\.\s+(.+)$',  # Lettered lists
        ]
        
        lines = text.split('\n')
        for line in lines:
            for pattern in list_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match and any(word in line.lower() for word in ['must', 'shall', 'required', 'minimum', 'maximum']):
                    check = {
                        'check_type': self._generate_check_type(line),
                        'description': match.group(1).strip(),
                        'criteria': match.group(1).strip(),
                        'data_fields': [],
                        'priority': 'medium',
                        'complexity': 'simple',
                        'domain': domain_hint or 'general',
                        'source': 'regex_extraction'
                    }
                    checks.append(check)
        
        return checks
    
    def _generate_check_type(self, description: str) -> str:
        """Generate a check_type from description if missing"""
        # Convert description to snake_case check type
        import re
        
        # Extract key words
        desc_lower = description.lower()
        
        # Common patterns
        if 'ratio' in desc_lower:
            if 'debt' in desc_lower and 'equity' in desc_lower:
                return 'debt_to_equity_ratio'
            elif 'current' in desc_lower:
                return 'current_ratio'
            elif 'quick' in desc_lower:
                return 'quick_ratio'
            else:
                return 'ratio_requirement'
        elif 'minimum' in desc_lower or 'at least' in desc_lower:
            if 'revenue' in desc_lower:
                return 'minimum_revenue_requirement'
            elif 'score' in desc_lower:
                return 'minimum_score_requirement'
            else:
                return 'minimum_requirement'
        elif 'maximum' in desc_lower or 'must not exceed' in desc_lower:
            return 'maximum_limit_requirement'
        elif 'compliance' in desc_lower:
            return 'compliance_requirement'
        elif 'assessment' in desc_lower:
            return 'assessment_requirement'
        else:
            # Create from first few words
            words = re.findall(r'\w+', description[:50].lower())
            return '_'.join(words[:3]) + '_check' if words else 'general_check'
    
    def rewrite_policy(self, policy_text: str, domain_hint: str = None) -> str:
        """Rewrite any policy in structured, machine-readable format"""
        agent = GeneralAgent("universal_policy_rewrite")
        
        prompt = f"""
        Rewrite this policy document in a clear, structured, machine-readable format.
        
        Original Policy:
        {policy_text}
        
        Domain: {domain_hint or "Auto-detect"}
        
        Structure the rewritten policy with:
        1. Executive Summary
        2. Scope and Applicability
        3. Detailed Requirements (numbered and categorized)
        4. Assessment Criteria for each requirement
        5. Compliance Standards and Thresholds
        6. Data Requirements for verification
        7. Priority Levels (Critical/High/Medium/Low)
        8. Reporting and Documentation Requirements
        
        Make it:
        - Clear and unambiguous
        - Machine-parseable while human-readable
        - Comprehensive and actionable
        - Suitable for automated compliance checking
        
        Use consistent formatting and terminology throughout.
        """
        
        return agent.process(prompt)
    
    def analyze_policy_complexity(self, policy_text: str) -> Dict:
        """Analyze the complexity and characteristics of a policy"""
        agent = GeneralAgent("policy_complexity_analyzer")
        
        prompt = f"""
        Analyze this policy document to understand its complexity and characteristics:
        
        {policy_text}
        
        Return a JSON analysis:
        {{
            "estimated_domain": "primary domain this policy belongs to",
            "complexity_level": "simple/moderate/complex/highly_complex",
            "estimated_checks": "number estimate of individual checks this policy contains",
            "data_requirements": ["types", "of", "data", "needed"],
            "analysis_types_needed": ["quantitative", "qualitative", "comparative", "etc"],
            "potential_challenges": ["list", "of", "challenges", "in", "implementation"],
            "automation_feasibility": "high/medium/low",
            "recommended_approach": "strategy for implementing compliance checking"
        }}
        
        Return only JSON, no other text.
        """
        
        try:
            response = agent.process(prompt)
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "estimated_domain": "unknown",
                "complexity_level": "unknown",
                "estimated_checks": 0,
                "automation_feasibility": "medium"
            }