import re
from typing import Dict, List
from dataclasses import dataclass
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

load_dotenv()

@dataclass
class PolicySection:
    title: str
    content: str
    level: int
    subsections: List['PolicySection'] = None
    
    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []

class CreditPolicyExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=PdfPipelineOptions(
                        do_ocr=False,
                        do_table_structure=True,
                        table_structure_options={
                            "do_cell_matching": True
                        }
                    )
                )
            }
        )
    
    def extract_document(self):
        result = self.converter.convert(self.pdf_path)
        return result
    
    def parse_structure(self, doc) -> List[PolicySection]:
        sections = []
        
        # Access the document object from ConversionResult
        document = doc.document
        
        # Iterate through all items in the document
        for item, level in document.iterate_items():
            text = ""
            if hasattr(item, 'text'):
                text = item.text
            elif hasattr(item, 'get_text'):
                text = item.get_text()
            
            if text and text.strip():
                text = text.strip()
                section = PolicySection(
                    title=text[:100] if len(text) > 100 else text,
                    content=text,
                    level=level
                )
                sections.append(section)
        
        return sections
    
    def extract_entities(self, doc) -> Dict[str, List[str]]:
        entities = {
            'credit_limits': [],
            'interest_rates': [],
            'requirements': [],
            'risk_categories': [],
            'loan_types': [],
            'tables': []
        }
        
        full_text = doc.document.export_to_markdown()
        
        credit_limit_pattern = re.compile(r'\$[\d,]+(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|dollars?)', re.IGNORECASE)
        interest_rate_pattern = re.compile(r'\d+(?:\.\d+)?%|(?:APR|interest rate)\s*:?\s*\d+(?:\.\d+)?%', re.IGNORECASE)
        
        entities['credit_limits'] = list(set(credit_limit_pattern.findall(full_text)))
        entities['interest_rates'] = list(set(interest_rate_pattern.findall(full_text)))
        
        risk_keywords = ['low risk', 'medium risk', 'high risk', 'risk assessment', 'risk category', 'risk tier']
        for keyword in risk_keywords:
            if keyword.lower() in full_text.lower():
                entities['risk_categories'].append(keyword)
        
        loan_types = ['personal loan', 'mortgage', 'auto loan', 'credit card', 'business loan', 'student loan', 'home equity']
        for loan_type in loan_types:
            if loan_type.lower() in full_text.lower():
                entities['loan_types'].append(loan_type)
        
        requirement_patterns = [
            r'must have\s+(.+?)(?:\.|,|;)',
            r'required\s+(.+?)(?:\.|,|;)',
            r'minimum\s+(.+?)(?:\.|,|;)',
            r'eligibility\s*:?\s*(.+?)(?:\.|,|;)'
        ]
        
        for pattern in requirement_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            entities['requirements'].extend([m.strip() for m in matches if len(m.strip()) < 200])
        
        # Access tables from the document
        document = doc.document
        if hasattr(document, 'tables'):
            for table in document.tables:
                table_data = {
                    'headers': [],
                    'rows': []
                }
                
                if hasattr(table, 'table_cells'):
                    for cell in table.table_cells:
                        if hasattr(cell, 'text'):
                            if cell.row_index == 0:
                                table_data['headers'].append(cell.text)
                            else:
                                if cell.row_index not in table_data['rows']:
                                    table_data['rows'][cell.row_index] = []
                                table_data['rows'][cell.row_index].append(cell.text)
                
                if table_data['headers'] or table_data['rows']:
                    entities['tables'].append(table_data)
                
        return entities

class Neo4jPipeline:
    def __init__(self):
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'password')
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    
    def create_policy_graph(self, sections: List[PolicySection], entities: Dict[str, List[str]]):
        with self.driver.session() as session:
            policy_result = session.run(
                "CREATE (p:Policy {name: 'Consumer Bank Credit Policy', version: 'v2'}) RETURN id(p) as policy_id"
            ).single()
            policy_id = policy_result['policy_id']
            
            section_stack = []
            for section in sections:
                parent_id = None
                
                while section_stack and section_stack[-1][1] >= section.level:
                    section_stack.pop()
                
                if section_stack:
                    parent_id = section_stack[-1][0]
                
                result = session.run(
                    """
                    CREATE (s:Section {title: $title, content: $content, level: $level})
                    RETURN id(s) as section_id
                    """,
                    title=section.title,
                    content=section.content[:1000],
                    level=section.level
                ).single()
                
                section_id = result['section_id']
                
                if parent_id:
                    session.run(
                        """
                        MATCH (parent:Section), (child:Section)
                        WHERE id(parent) = $parent_id AND id(child) = $child_id
                        CREATE (parent)-[:HAS_SUBSECTION]->(child)
                        """,
                        parent_id=parent_id,
                        child_id=section_id
                    )
                else:
                    session.run(
                        """
                        MATCH (p:Policy), (s:Section)
                        WHERE id(p) = $policy_id AND id(s) = $section_id
                        CREATE (p)-[:HAS_SECTION]->(s)
                        """,
                        policy_id=policy_id,
                        section_id=section_id
                    )
                
                section_stack.append((section_id, section.level))
            
            for limit in entities['credit_limits']:
                session.run(
                    """
                    MATCH (p:Policy {name: 'Consumer Bank Credit Policy'})
                    MERGE (l:CreditLimit {amount: $amount})
                    CREATE (p)-[:DEFINES_LIMIT]->(l)
                    """,
                    amount=limit
                )
            
            for rate in entities['interest_rates']:
                session.run(
                    """
                    MATCH (p:Policy {name: 'Consumer Bank Credit Policy'})
                    MERGE (r:InterestRate {rate: $rate})
                    CREATE (p)-[:SPECIFIES_RATE]->(r)
                    """,
                    rate=rate
                )
            
            for risk in set(entities['risk_categories']):
                session.run(
                    """
                    MATCH (p:Policy {name: 'Consumer Bank Credit Policy'})
                    MERGE (rc:RiskCategory {name: $name})
                    CREATE (p)-[:CATEGORIZES_RISK]->(rc)
                    """,
                    name=risk
                )
            
            for loan_type in set(entities['loan_types']):
                session.run(
                    """
                    MATCH (p:Policy {name: 'Consumer Bank Credit Policy'})
                    MERGE (lt:LoanType {name: $name})
                    CREATE (p)-[:COVERS_LOAN_TYPE]->(lt)
                    """,
                    name=loan_type
                )
            
            for req in entities['requirements'][:20]:
                session.run(
                    """
                    MATCH (p:Policy {name: 'Consumer Bank Credit Policy'})
                    CREATE (r:Requirement {description: $description})
                    CREATE (p)-[:HAS_REQUIREMENT]->(r)
                    """,
                    description=req
                )
            
            for i, table in enumerate(entities['tables']):
                headers_str = ', '.join(table.get('headers', []))
                session.run(
                    """
                    MATCH (p:Policy {name: 'Consumer Bank Credit Policy'})
                    CREATE (t:Table {index: $index, headers: $headers})
                    CREATE (p)-[:CONTAINS_TABLE]->(t)
                    """,
                    index=i,
                    headers=headers_str
                )
    
    def query_policy_info(self):
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Policy)-[r]->(n)
                RETURN type(r) as relationship, labels(n) as node_type, count(n) as count
                ORDER BY count DESC
                """
            )
            print("\nPolicy Graph Summary:")
            for record in result:
                print(f"- {record['relationship']}: {record['count']} {record['node_type'][0]}")
            
            section_result = session.run(
                """
                MATCH (s:Section)
                RETURN count(s) as total_sections, collect(DISTINCT s.level) as levels
                """
            ).single()
            print(f"\nDocument Structure:")
            print(f"- Total sections: {section_result['total_sections']}")
            print(f"- Section levels: {sorted(section_result['levels'])}")

def main():
    print("Starting Credit Policy Extraction Pipeline with Docling...")
    
    extractor = CreditPolicyExtractor("consumer-bank-credit-policy-v2.pdf")
    
    print("Converting PDF document...")
    doc = extractor.extract_document()
    
    print("Parsing document structure...")
    sections = extractor.parse_structure(doc)
    print(f"Found {len(sections)} sections")
    
    print("Extracting entities...")
    entities = extractor.extract_entities(doc)
    for entity_type, values in entities.items():
        if values:
            print(f"- {entity_type}: {len(values)} found")
    
    print("\nConnecting to Neo4j...")
    pipeline = Neo4jPipeline()
    
    print("Clearing existing data...")
    pipeline.clear_database()
    
    print("Creating policy graph...")
    pipeline.create_policy_graph(sections, entities)
    
    print("\nQuerying policy information...")
    pipeline.query_policy_info()
    
    pipeline.close()
    print("\nPipeline completed successfully!")

if __name__ == "__main__":
    main()