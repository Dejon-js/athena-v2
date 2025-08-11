import asyncio
import json
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import structlog

from shared.database import neo4j_conn
from shared.config import settings

logger = structlog.get_logger()


class KnowledgeGraphBuilder:
    """
    LLM-based entity and relationship extraction for Neo4j knowledge graph.
    Extracts Players, Teams, Injuries and their relationships from news content.
    """
    
    def __init__(self):
        self.llm_provider = self._determine_llm_provider()
        self.extraction_prompt = self._build_extraction_prompt()
    
    def _determine_llm_provider(self) -> str:
        """Determine which LLM provider to use based on available API keys"""
        if settings.gemini_api_key:
            return "gemini"
        elif settings.openai_api_key:
            return "openai"
        else:
            logger.warning("No LLM API key found, knowledge graph extraction will be limited")
            return None
    
    def _build_extraction_prompt(self) -> str:
        """Build structured prompt for entity and relationship extraction"""
        return """
You are an expert NFL data analyst. Extract structured information from the following news article.

Extract entities and relationships in this exact JSON format:
{
  "entities": [
    {"name": "Player Name", "type": "Player", "team": "TEAM_CODE"},
    {"name": "Team Name", "type": "Team", "code": "TEAM_CODE"},
    {"name": "Injury Type", "type": "Injury", "severity": "minor|moderate|severe"}
  ],
  "relationships": [
    {"source": "Player Name", "target": "Team Name", "type": "PLAYS_FOR"},
    {"source": "Player Name", "target": "Injury Type", "type": "SUFFERED_INJURY", "date": "YYYY-MM-DD"},
    {"source": "Player Name", "target": "Player Name", "type": "COMPETES_WITH"}
  ]
}

Entity Types:
- Player: NFL players (first and last name)
- Team: NFL teams (use standard 3-letter codes like KC, BUF, etc.)
- Injury: Specific injury types (hamstring, concussion, knee, etc.)

Relationship Types:
- PLAYS_FOR: Player to Team
- SUFFERED_INJURY: Player to Injury
- COMPETES_WITH: Player to Player (same position)
- TEAMMATES: Player to Player (same team)

Only extract entities and relationships that are explicitly mentioned in the article.
Return only valid JSON, no additional text.

Article:
"""
    
    async def extract_entities_and_relationships(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract entities and relationships from news article using LLM.
        
        Args:
            article: Article data with title and content
            
        Returns:
            Dict containing extracted entities and relationships
        """
        logger.info("Starting entity extraction", title=article.get('title', '')[:50])
        
        try:
            content = f"{article.get('title', '')} {article.get('content', '')}"
            
            if not content.strip():
                return {'entities': [], 'relationships': []}
            
            if not self.llm_provider:
                logger.warning("No LLM provider available, using fallback extraction")
                return await self._fallback_extraction(content)
            
            extraction_result = await self._call_llm_for_extraction(content)
            
            if extraction_result:
                await self._store_in_neo4j(extraction_result, article)
                
                logger.info("Entity extraction completed", 
                          entities=len(extraction_result.get('entities', [])),
                          relationships=len(extraction_result.get('relationships', [])))
                
                return extraction_result
            else:
                return {'entities': [], 'relationships': []}
                
        except Exception as e:
            logger.error("Error during entity extraction", error=str(e))
            return {'entities': [], 'relationships': []}
    
    async def _call_llm_for_extraction(self, content: str) -> Optional[Dict[str, Any]]:
        """Call LLM API for entity and relationship extraction"""
        try:
            if self.llm_provider == "gemini":
                return await self._call_gemini_api(content)
            elif self.llm_provider == "openai":
                return await self._call_openai_api(content)
            else:
                return None
                
        except Exception as e:
            logger.error("Error calling LLM API", provider=self.llm_provider, error=str(e))
            return None
    
    async def _call_gemini_api(self, content: str) -> Optional[Dict[str, Any]]:
        """Call Gemini API for extraction"""
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
            
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": settings.gemini_api_key
            }
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"{self.extraction_prompt}\n{content}"
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 2048
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if 'candidates' in result and result['candidates']:
                            text_response = result['candidates'][0]['content']['parts'][0]['text']
                            return self._parse_llm_response(text_response)
                    else:
                        logger.error("Gemini API error", status=response.status)
                        return None
                        
        except Exception as e:
            logger.error("Error calling Gemini API", error=str(e))
            return None
    
    async def _call_openai_api(self, content: str) -> Optional[Dict[str, Any]]:
        """Call OpenAI API for extraction"""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.openai_api_key}"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": self.extraction_prompt},
                    {"role": "user", "content": content}
                ],
                "temperature": 0.1,
                "max_tokens": 2048
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if 'choices' in result and result['choices']:
                            text_response = result['choices'][0]['message']['content']
                            return self._parse_llm_response(text_response)
                    else:
                        logger.error("OpenAI API error", status=response.status)
                        return None
                        
        except Exception as e:
            logger.error("Error calling OpenAI API", error=str(e))
            return None
    
    def _parse_llm_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response to extract JSON"""
        try:
            response_text = response_text.strip()
            
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            parsed_response = json.loads(response_text)
            
            if 'entities' in parsed_response and 'relationships' in parsed_response:
                return parsed_response
            else:
                logger.warning("Invalid LLM response format", response=response_text[:100])
                return None
                
        except json.JSONDecodeError as e:
            logger.error("Error parsing LLM JSON response", error=str(e), response=response_text[:100])
            return None
    
    async def _fallback_extraction(self, content: str) -> Dict[str, Any]:
        """Fallback extraction using simple keyword matching"""
        entities = []
        relationships = []
        
        common_players = [
            "Patrick Mahomes", "Josh Allen", "Lamar Jackson", "Joe Burrow",
            "Christian McCaffrey", "Derrick Henry", "Alvin Kamara", "Nick Chubb",
            "Cooper Kupp", "Davante Adams", "Tyreek Hill", "Stefon Diggs",
            "Travis Kelce", "Mark Andrews", "George Kittle", "Darren Waller"
        ]
        
        common_injuries = [
            "hamstring", "concussion", "knee", "ankle", "shoulder", "back",
            "groin", "quad", "calf", "wrist", "hand", "finger"
        ]
        
        content_lower = content.lower()
        
        for player in common_players:
            if player.lower() in content_lower:
                entities.append({
                    "name": player,
                    "type": "Player",
                    "team": "UNKNOWN"
                })
        
        for injury in common_injuries:
            if injury in content_lower:
                entities.append({
                    "name": injury.title(),
                    "type": "Injury",
                    "severity": "moderate"
                })
        
        return {'entities': entities, 'relationships': relationships}
    
    async def _store_in_neo4j(self, extraction_result: Dict[str, Any], article: Dict[str, Any]):
        """Store extracted entities and relationships in Neo4j"""
        try:
            entities = extraction_result.get('entities', [])
            relationships = extraction_result.get('relationships', [])
            
            for entity in entities:
                await self._create_entity_node(entity)
            
            for relationship in relationships:
                await self._create_relationship(relationship)
            
            await self._create_article_node(article, extraction_result)
            
            logger.info("Data stored in Neo4j", 
                       entities=len(entities),
                       relationships=len(relationships))
            
        except Exception as e:
            logger.error("Error storing data in Neo4j", error=str(e))
    
    async def _create_entity_node(self, entity: Dict[str, Any]):
        """Create entity node in Neo4j"""
        try:
            entity_type = entity.get('type')
            entity_name = entity.get('name')
            
            if entity_type == 'Player':
                query = """
                MERGE (p:Player {name: $name})
                SET p.team = $team,
                    p.updated_at = datetime()
                """
                parameters = {
                    'name': entity_name,
                    'team': entity.get('team', 'UNKNOWN')
                }
                
            elif entity_type == 'Team':
                query = """
                MERGE (t:Team {name: $name})
                SET t.code = $code,
                    t.updated_at = datetime()
                """
                parameters = {
                    'name': entity_name,
                    'code': entity.get('code', 'UNKNOWN')
                }
                
            elif entity_type == 'Injury':
                query = """
                MERGE (i:Injury {name: $name})
                SET i.severity = $severity,
                    i.updated_at = datetime()
                """
                parameters = {
                    'name': entity_name,
                    'severity': entity.get('severity', 'moderate')
                }
            else:
                return
            
            neo4j_conn.query(query, parameters)
            
        except Exception as e:
            logger.error("Error creating entity node", entity=entity, error=str(e))
    
    async def _create_relationship(self, relationship: Dict[str, Any]):
        """Create relationship in Neo4j"""
        try:
            source = relationship.get('source')
            target = relationship.get('target')
            rel_type = relationship.get('type')
            
            if not all([source, target, rel_type]):
                return
            
            if rel_type == 'PLAYS_FOR':
                query = """
                MATCH (p:Player {name: $source})
                MATCH (t:Team {name: $target})
                MERGE (p)-[r:PLAYS_FOR]->(t)
                SET r.updated_at = datetime()
                """
                
            elif rel_type == 'SUFFERED_INJURY':
                query = """
                MATCH (p:Player {name: $source})
                MATCH (i:Injury {name: $target})
                MERGE (p)-[r:SUFFERED_INJURY]->(i)
                SET r.date = $date,
                    r.updated_at = datetime()
                """
                
            elif rel_type in ['COMPETES_WITH', 'TEAMMATES']:
                query = f"""
                MATCH (p1:Player {{name: $source}})
                MATCH (p2:Player {{name: $target}})
                MERGE (p1)-[r:{rel_type}]->(p2)
                SET r.updated_at = datetime()
                """
            else:
                return
            
            parameters = {
                'source': source,
                'target': target,
                'date': relationship.get('date', datetime.now().strftime('%Y-%m-%d'))
            }
            
            neo4j_conn.query(query, parameters)
            
        except Exception as e:
            logger.error("Error creating relationship", relationship=relationship, error=str(e))
    
    async def _create_article_node(self, article: Dict[str, Any], extraction_result: Dict[str, Any]):
        """Create article node and link to extracted entities"""
        try:
            query = """
            CREATE (a:Article {
                title: $title,
                url: $url,
                source: $source,
                published_date: $published_date,
                ingested_at: $ingested_at,
                entities_count: $entities_count,
                relationships_count: $relationships_count
            })
            """
            
            parameters = {
                'title': article.get('title', ''),
                'url': article.get('url', ''),
                'source': article.get('source', ''),
                'published_date': article.get('published_date', ''),
                'ingested_at': article.get('ingested_at', datetime.now(timezone.utc).isoformat()),
                'entities_count': len(extraction_result.get('entities', [])),
                'relationships_count': len(extraction_result.get('relationships', []))
            }
            
            neo4j_conn.query(query, parameters)
            
        except Exception as e:
            logger.error("Error creating article node", error=str(e))
    
    async def get_neo4j_schema_index(self) -> Dict[str, Any]:
        """Get Neo4j schema index for LLM context"""
        try:
            node_labels_query = "CALL db.labels()"
            relationship_types_query = "CALL db.relationshipTypes()"
            
            node_labels = neo4j_conn.query(node_labels_query)
            relationship_types = neo4j_conn.query(relationship_types_query)
            
            schema_index = {
                'node_labels': [record['label'] for record in node_labels] if node_labels else [],
                'relationship_types': [record['relationshipType'] for record in relationship_types] if relationship_types else [],
                'sample_queries': [
                    "MATCH (p:Player)-[:SUFFERED_INJURY]->(i:Injury) RETURN p.name, i.name",
                    "MATCH (p:Player)-[:PLAYS_FOR]->(t:Team) RETURN p.name, t.name",
                    "MATCH (p1:Player)-[:TEAMMATES]->(p2:Player) RETURN p1.name, p2.name"
                ]
            }
            
            return schema_index
            
        except Exception as e:
            logger.error("Error getting Neo4j schema index", error=str(e))
            return {
                'node_labels': ['Player', 'Team', 'Injury', 'Article'],
                'relationship_types': ['PLAYS_FOR', 'SUFFERED_INJURY', 'TEAMMATES', 'COMPETES_WITH'],
                'sample_queries': []
            }
