from typing import Dict, List
from app.parsers.document_parser import DocumentParser
from app.services.policy_analyzer import PolicyAnalyzer
from agents.base_agent import GeneralAgent
import json
import concurrent.futures

class DocumentProcessor:
    """Processes parsed documents to extract policy information from any content type"""
    
    def __init__(self):
        self.parser = DocumentParser()
    
    def process_document(self, file_path: str, domain_hint: str = None) -> Dict:
        """Process a document file and extract policy information"""
        # Parse the document
        parsed_doc = self.parser.parse_document(file_path)
        
        if 'error' in parsed_doc:
            return parsed_doc
        
        # Generate document summary
        doc_summary = self.parser.get_document_summary(parsed_doc)
        
        # Extract policy information from all content types
        policy_info = self._extract_policy_from_parsed_content(parsed_doc, domain_hint)
        
        return {
            'document_summary': doc_summary,
            'parsed_content': parsed_doc,
            'policy_extraction': policy_info,
            'processing_status': 'success'
        }
    
    def _extract_policy_from_parsed_content(self, parsed_doc: Dict, domain_hint: str = None) -> Dict:
        """Extract policy information from all types of parsed content with parallel processing"""
        analyzer = PolicyAnalyzer()
        all_checks = []
        text_checks = []
        table_checks = []
        visual_checks = []
        
        # Process different content types in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}
            
            # Submit text extraction
            if parsed_doc.get('text_content'):
                future = executor.submit(analyzer.extract_checks, parsed_doc['text_content'], domain_hint)
                futures[future] = 'text'
            
            # Submit table extraction if tables exist
            if parsed_doc.get('tables'):
                future = executor.submit(self._extract_checks_from_tables, parsed_doc['tables'], domain_hint)
                futures[future] = 'table'
            
            # Submit visual extraction if visuals exist
            visuals = parsed_doc.get('charts', []) + parsed_doc.get('images', [])
            if visuals:
                future = executor.submit(self._extract_checks_from_visuals, visuals, domain_hint)
                futures[future] = 'visual'
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                try:
                    checks = future.result()
                    check_type = futures[future]
                    
                    if check_type == 'text':
                        text_checks = checks
                    elif check_type == 'table':
                        table_checks = checks
                    elif check_type == 'visual':
                        visual_checks = checks
                    
                    all_checks.extend(checks)
                except Exception as e:
                    print(f"Error extracting checks: {e}")
        
        # Fast deduplication
        unique_checks = analyzer._fast_deduplicate_checks(all_checks)
        
        # Prepare document insights
        agent = GeneralAgent("document_insights_analyzer")
        content_summary = self._prepare_content_for_analysis(parsed_doc)
        
        prompt = f"""
        You are a multimodal policy analysis expert. Extract policy information from this document that contains multiple content types.
        
        Domain Context: {domain_hint or "Auto-detect from content"}
        
        Document Content Summary:
        {json.dumps(content_summary, indent=2)}
        
        Analyze this document summary to provide insights about the policy content.
        
        Return JSON with document insights:
        {{
            "document_insights": {{
                "primary_domain": "detected domain",
                "content_richness": "text_only/tables_included/charts_included/multimedia",
                "policy_complexity": "simple/moderate/complex",
                "visual_compliance_elements": ["list of visual elements found"],
                "data_requirements": ["comprehensive list of data needed"],
                "estimated_check_count": "estimated number of compliance checks in document",
                "key_themes": ["main themes identified in the document"]
            }}
        }}
        
        Return only JSON, no other text.
        """
        
        try:
            response = agent.process(prompt)
            insights = json.loads(response)
            
            return {
                "extracted_policies": unique_checks,
                "document_insights": insights.get('document_insights', {}),
                "extraction_summary": {
                    "text_checks": len(text_checks),
                    "table_checks": len(table_checks),
                    "visual_checks": len(visual_checks),
                    "total_unique_checks": len(unique_checks)
                }
            }
        except json.JSONDecodeError:
            return {
                "extracted_policies": unique_checks,
                "document_insights": {
                    "primary_domain": "unknown",
                    "error": "Failed to parse AI response"
                }
            }
    
    def _prepare_content_for_analysis(self, parsed_doc: Dict) -> Dict:
        """Prepare parsed document content for AI analysis"""
        content_summary = {
            "text_content": parsed_doc.get('text_content', '')[:5000],  # Truncate for token limits
            "metadata": parsed_doc.get('metadata', {}),
            "content_types_found": []
        }
        
        # Summarize tables
        if parsed_doc.get('tables'):
            content_summary["content_types_found"].append("tables")
            content_summary["tables_summary"] = []
            
            for table in parsed_doc['tables'][:5]:  # Limit to first 5 tables
                table_summary = {
                    "location": table.get('page', table.get('sheet_name', 'unknown')),
                    "headers": table.get('analysis', {}).get('headers', []),
                    "row_count": table.get('analysis', {}).get('row_count', 0),
                    "compliance_indicators": table.get('analysis', {}).get('compliance_indicators', []),
                    "potential_metrics": table.get('analysis', {}).get('potential_metrics', []),
                    "sample_data": table.get('data', [])[:3] if table.get('data') else []  # First 3 rows
                }
                content_summary["tables_summary"].append(table_summary)
        
        # Summarize charts
        if parsed_doc.get('charts'):
            content_summary["content_types_found"].append("charts")
            content_summary["charts_summary"] = []
            
            for chart in parsed_doc['charts']:
                chart_summary = {
                    "location": f"Page {chart.get('page', 'unknown')}",
                    "type": chart.get('type', 'unknown'),
                    "data_points": chart.get('extracted_data', [])[:10],  # First 10 data points
                    "analysis": chart.get('analysis', {})
                }
                content_summary["charts_summary"].append(chart_summary)
        
        # Summarize images
        if parsed_doc.get('images'):
            content_summary["content_types_found"].append("images")
            content_summary["images_summary"] = []
            
            for img in parsed_doc['images'][:3]:  # First 3 images
                img_summary = {
                    "location": f"Page {img.get('page', 'unknown')}",
                    "ocr_text": img.get('analysis', {}).get('ocr_text', '')[:500],  # Truncate OCR text
                    "contains_text": img.get('analysis', {}).get('contains_text', False),
                    "is_chart": img.get('analysis', {}).get('is_chart', False)
                }
                content_summary["images_summary"].append(img_summary)
        
        return content_summary
    
    def _extract_checks_from_tables(self, tables: List[Dict], domain_hint: str = None) -> List[Dict]:
        """Extract policy checks from table data"""
        if not tables:
            return []
        
        checks = []
        agent = GeneralAgent("table_policy_extractor")
        
        # Process only significant tables
        for i, table in enumerate(tables[:5]):  # Limit to first 5 tables
            if not table.get('data') or len(table.get('data', [])) < 2:
                continue
            
            # Prepare table summary
            table_summary = {
                "headers": table.get('analysis', {}).get('headers', []),
                "row_count": table.get('analysis', {}).get('row_count', 0),
                "sample_data": table.get('data', [])[:10],  # First 10 rows
                "potential_metrics": table.get('analysis', {}).get('potential_metrics', [])
            }
            
            prompt = f"""
            Extract policy requirements from this table data:
            
            Table Location: {table.get('page', table.get('sheet_name', f'Table {i+1}'))}
            Table Data: {json.dumps(table_summary, indent=2)}
            Domain: {domain_hint or "Auto-detect"}
            
            CRITICAL: Extract EVERY row that contains a number, percentage, or threshold.
            
            Look for:
            1. ANY row with a number (create a separate check for each)
            2. ANY row with min/max/threshold/limit/requirement
            3. ANY row with a percentage (%)
            4. ANY row with a ratio or score
            5. ANY row with eligible/qualified/acceptable/required
            6. Column headers that indicate requirements (e.g., "Minimum", "Maximum", "Required", "Threshold")
            
            Common credit policy table patterns:
            - Product | Min LTV | Max LTV | Min FICO | Max DTI
            - Loan Type | Minimum Amount | Maximum Amount | Rate
            - Risk Grade | Required DSCR | Maximum LTV | Pricing
            
            RULE: Every cell with a number should generate a check
            
            Extract one check for EACH numeric value in the table.
            
            For each requirement found, return JSON array:
            [{{
                "source_type": "table",
                "source_location": "Table at {table.get('page', table.get('sheet_name', f'Table {i+1}'))}",
                "check_type": "descriptive name based on row/column",
                "description": "what needs to be checked (be specific about which product/category)",
                "criteria": "exact requirement from the table",
                "threshold": "the specific number/percentage from the table",
                "formula": "if applicable",
                "data_fields": ["fields needed"],
                "priority": "high",
                "complexity": "quantitative",
                "domain": "{domain_hint or 'financial'}"
            }}]
            
            IMPORTANT: If a table has 5 rows and 3 numeric columns, extract 15 checks (one per cell).
            
            Return only JSON array, no other text.
            """
            
            try:
                response = agent.process(prompt)
                table_checks = json.loads(response)
                if isinstance(table_checks, list):
                    checks.extend(table_checks)
            except json.JSONDecodeError:
                pass
        
        return checks
    
    def _extract_checks_from_visuals(self, visuals: List[Dict], domain_hint: str = None) -> List[Dict]:
        """Extract policy checks from charts and images"""
        if not visuals:
            return []
        
        checks = []
        agent = GeneralAgent("visual_policy_extractor")
        
        # Process only the most relevant visuals
        for i, visual in enumerate(visuals[:3]):  # Limit to first 3 visuals
            visual_type = "chart" if visual.get('type') else "image"
            
            # Prepare visual summary
            visual_summary = {
                "type": visual.get('type', visual_type),
                "location": f"Page {visual.get('page', i+1)}",
                "extracted_data": visual.get('extracted_data', [])[:20] if visual.get('extracted_data') else None,
                "ocr_text": visual.get('analysis', {}).get('ocr_text', '')[:500] if visual.get('analysis') else None,
                "analysis": visual.get('analysis', {})
            }
            
            prompt = f"""
            Extract policy requirements from this {visual_type}:
            
            Visual Data: {json.dumps(visual_summary, indent=2)}
            Domain: {domain_hint or "Auto-detect"}
            
            Look for:
            1. Trend lines indicating thresholds
            2. Target zones or acceptable ranges
            3. Benchmark lines or reference values
            4. Warning/danger zones
            5. Performance indicators
            6. Compliance boundaries
            
            For each requirement found, return JSON array:
            [{{
                "source_type": "{visual_type}",
                "source_location": "specific location",
                "check_type": "descriptive name",
                "description": "what needs to be checked",
                "criteria": "specific requirement",
                "visual_elements": "description of visual indicators",
                "data_fields": ["fields needed"],
                "priority": "critical/high/medium/low",
                "complexity": "simple/quantitative/comparative/multi_step",
                "domain": "detected domain"
            }}]
            
            Return only JSON array, no other text.
            """
            
            try:
                response = agent.process(prompt)
                visual_checks = json.loads(response)
                if isinstance(visual_checks, list):
                    checks.extend(visual_checks)
            except json.JSONDecodeError:
                pass
        
        return checks
    
    def extract_visual_metrics(self, parsed_doc: Dict) -> List[Dict]:
        """Extract metrics specifically from visual elements (charts, graphs)"""
        visual_metrics = []
        
        # Process charts
        for chart in parsed_doc.get('charts', []):
            if chart.get('extracted_data'):
                metric = {
                    'source': 'chart',
                    'type': chart.get('type', 'unknown'),
                    'location': f"Page {chart.get('page', 'unknown')}",
                    'data_points': chart.get('extracted_data', []),
                    'potential_thresholds': self._identify_thresholds(chart.get('extracted_data', [])),
                    'analysis': chart.get('analysis', {})
                }
                visual_metrics.append(metric)
        
        # Process tables with numeric data
        for table in parsed_doc.get('tables', []):
            metrics = table.get('analysis', {}).get('potential_metrics', [])
            for metric in metrics:
                if metric.get('type') == 'numeric':
                    visual_metric = {
                        'source': 'table',
                        'type': 'tabular_data',
                        'location': table.get('page', table.get('sheet_name', 'unknown')),
                        'column': metric.get('column'),
                        'sample_values': metric.get('sample_values', []),
                        'potential_thresholds': self._identify_thresholds(metric.get('sample_values', []))
                    }
                    visual_metrics.append(visual_metric)
        
        return visual_metrics
    
    def _identify_thresholds(self, data_points: List) -> List[Dict]:
        """Identify potential thresholds from numeric data"""
        if not data_points:
            return []
        
        numeric_values = []
        for point in data_points:
            try:
                numeric_values.append(float(point))
            except (ValueError, TypeError):
                continue
        
        if not numeric_values:
            return []
        
        thresholds = []
        
        # Statistical thresholds
        import statistics
        if len(numeric_values) > 1:
            mean_val = statistics.mean(numeric_values)
            try:
                std_val = statistics.stdev(numeric_values)
                thresholds.extend([
                    {'type': 'mean', 'value': mean_val},
                    {'type': 'upper_control', 'value': mean_val + 2*std_val},
                    {'type': 'lower_control', 'value': mean_val - 2*std_val}
                ])
            except statistics.StatisticsError:
                thresholds.append({'type': 'mean', 'value': mean_val})
        
        # Percentile thresholds
        if len(numeric_values) >= 5:
            sorted_values = sorted(numeric_values)
            n = len(sorted_values)
            thresholds.extend([
                {'type': '95th_percentile', 'value': sorted_values[int(0.95 * n)]},
                {'type': '5th_percentile', 'value': sorted_values[int(0.05 * n)]},
                {'type': 'median', 'value': statistics.median(numeric_values)}
            ])
        
        return thresholds
    
    def validate_document_completeness(self, parsed_doc: Dict) -> Dict:
        """Validate if document contains sufficient information for policy extraction"""
        validation = {
            'is_complete': True,
            'missing_elements': [],
            'recommendations': [],
            'confidence_score': 1.0
        }
        
        # Check for text content
        if not parsed_doc.get('text_content') or len(parsed_doc['text_content'].strip()) < 100:
            validation['missing_elements'].append('substantial_text_content')
            validation['confidence_score'] -= 0.3
        
        # Check for structured data
        has_tables = len(parsed_doc.get('tables', [])) > 0
        has_charts = len(parsed_doc.get('charts', [])) > 0
        
        if not has_tables and not has_charts:
            validation['missing_elements'].append('structured_data')
            validation['confidence_score'] -= 0.2
        
        # Check for policy indicators
        text = parsed_doc.get('text_content', '').lower()
        policy_keywords = ['policy', 'requirement', 'compliance', 'standard', 'threshold']
        policy_indicators = sum(1 for keyword in policy_keywords if keyword in text)
        
        if policy_indicators < 2:
            validation['missing_elements'].append('policy_indicators')
            validation['confidence_score'] -= 0.2
        
        # Generate recommendations
        if 'substantial_text_content' in validation['missing_elements']:
            validation['recommendations'].append("Document may need additional text content for comprehensive policy extraction")
        
        if 'structured_data' in validation['missing_elements']:
            validation['recommendations'].append("Consider adding tables or charts with specific metrics and thresholds")
        
        if 'policy_indicators' in validation['missing_elements']:
            validation['recommendations'].append("Document may benefit from clearer policy language and requirements")
        
        validation['is_complete'] = validation['confidence_score'] >= 0.6
        
        return validation