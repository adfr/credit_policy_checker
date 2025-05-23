from agents.universal_agent import UniversalAgent
from typing import Dict

class AgentFactory:
    """Factory to create agents for any type of policy checking"""
    
    def __init__(self):
        # Keep track of agent instances for reuse if needed
        self.agent_cache = {}
    
    def create_agent(self, check_type: str, check_definition: Dict = None):
        """Create a universal agent that can handle any type of check"""
        if not check_definition:
            check_definition = {'check_type': check_type}
        
        # Determine domain and complexity from check definition
        domain = self._determine_domain(check_definition)
        complexity = self._determine_complexity(check_definition)
        
        # Add domain and complexity to check definition
        check_definition.update({
            'domain': domain,
            'complexity': complexity
        })
        
        # Create universal agent
        return UniversalAgent(check_definition)
    
    def _determine_domain(self, check_definition: Dict) -> str:
        """Determine the domain/expertise area for the check"""
        check_type = check_definition.get('check_type', '').lower()
        description = check_definition.get('description', '').lower()
        criteria = check_definition.get('criteria', '').lower()
        
        # Combine all text for domain detection
        full_text = f"{check_type} {description} {criteria}"
        
        # Domain mapping based on keywords
        domain_keywords = {
            'financial': ['financial', 'ratio', 'revenue', 'profit', 'cash', 'debt', 'equity', 'balance', 'income', 'credit', 'loan'],
            'esg': ['esg', 'environmental', 'social', 'governance', 'sustainability', 'carbon', 'emission', 'diversity', 'ethics'],
            'regulatory': ['regulatory', 'compliance', 'legal', 'law', 'regulation', 'audit', 'requirement', 'standard'],
            'risk': ['risk', 'volatility', 'exposure', 'hedge', 'var', 'stress', 'scenario', 'probability'],
            'operational': ['operational', 'process', 'efficiency', 'productivity', 'quality', 'performance', 'kpi'],
            'market': ['market', 'competitive', 'industry', 'peer', 'benchmark', 'analysis', 'comparison'],
            'strategic': ['strategic', 'business', 'growth', 'investment', 'merger', 'acquisition', 'partnership'],
            'hr': ['hr', 'human', 'employee', 'staff', 'training', 'talent', 'compensation', 'benefits'],
            'technology': ['technology', 'tech', 'it', 'digital', 'cyber', 'security', 'data', 'system'],
            'supply_chain': ['supply', 'chain', 'vendor', 'supplier', 'procurement', 'logistics', 'inventory']
        }
        
        # Find best matching domain
        best_domain = 'general'
        max_matches = 0
        
        for domain, keywords in domain_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in full_text)
            if matches > max_matches:
                max_matches = matches
                best_domain = domain
        
        return best_domain
    
    def _determine_complexity(self, check_definition: Dict) -> str:
        """Determine the complexity level of the check"""
        description = check_definition.get('description', '').lower()
        criteria = check_definition.get('criteria', '').lower()
        agent_instructions = check_definition.get('agent_instructions', '').lower()
        check_type = check_definition.get('check_type', '').lower()
        
        # Check for formula or threshold fields
        has_formula = bool(check_definition.get('formula'))
        has_threshold = bool(check_definition.get('threshold'))
        
        full_text = f"{check_type} {description} {criteria} {agent_instructions}"
        
        # Complexity indicators
        multi_step_indicators = ['analyze and then', 'first check', 'step by step', 'multiple criteria', 'workflow', 'process', 'sequential', 'if then']
        comparative_indicators = ['compare', 'benchmark', 'peer', 'industry average', 'relative to', 'versus', 'quartile', 'percentile', 'above average', 'below average']
        quantitative_indicators = ['calculate', 'ratio', 'percentage', 'statistical', 'variance', 'correlation', 'regression', 'formula', 'equation']
        
        # If it has a formula or numeric threshold, it's likely quantitative
        if has_formula or has_threshold:
            # But check if it's also comparative
            if any(indicator in full_text for indicator in comparative_indicators):
                return 'comparative'
            return 'quantitative'
        
        # Check text-based indicators
        if any(indicator in full_text for indicator in multi_step_indicators):
            return 'multi_step'
        elif any(indicator in full_text for indicator in comparative_indicators):
            return 'comparative'
        elif any(indicator in full_text for indicator in quantitative_indicators):
            return 'quantitative'
        else:
            return 'simple'
    
    def get_domain_capabilities(self) -> Dict:
        """Return information about supported domains"""
        return {
            'financial': 'Financial analysis, ratios, credit assessment, valuation',
            'esg': 'Environmental, Social, Governance compliance and assessment',
            'regulatory': 'Legal compliance, regulatory requirements, audit checks',
            'risk': 'Risk assessment, exposure analysis, stress testing',
            'operational': 'Process efficiency, performance metrics, operational KPIs',
            'market': 'Market analysis, competitive positioning, benchmarking',
            'strategic': 'Strategic planning, business analysis, investment assessment',
            'hr': 'Human resources, talent management, compensation analysis',
            'technology': 'Technology assessment, cybersecurity, digital transformation',
            'supply_chain': 'Supply chain analysis, vendor assessment, procurement',
            'general': 'General purpose analysis for any domain'
        }