# Content Processor for ATHENA v2.2
import re
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import structlog

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

from shared.config import settings

logger = structlog.get_logger()


class ContentVectorProcessor:
    """
    Processes podcast transcripts and news articles to extract
    fantasy-relevant insights and prepare content for vector storage.
    """

    def __init__(self):
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("Sentence transformers not available")

        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Fantasy-relevant keywords and patterns
        self.fantasy_keywords = {
            'performance': [
                'playing', 'performing', 'production', 'output', 'touchdowns',
                'yards', 'carries', 'targets', 'receptions', 'fantasy points'
            ],
            'health': [
                'injury', 'healthy', 'recovery', 'practice', 'IR', 'questionable',
                'doubtful', 'probable', 'out', 'return', 'concussion', 'hamstring'
            ],
            'situational': [
                'matchup', 'defense', 'opponent', 'weather', 'home', 'away',
                'travel', 'rest', 'bye week', 'schedule'
            ],
            'team_dynamics': [
                'chemistry', 'coaching', 'scheme', 'playbook', 'confidence',
                'leadership', 'rookie', 'veteran', 'depth', 'competition'
            ]
        }

        # DFS-specific patterns
        self.dfs_patterns = [
            r'(?:should|could|might|will) (?:be|have|get|see|play) (?:\w+ ){0,5}(?:points|fantasy|production)',
            r'(?:high|low|big|good|bad) (?:week|game|matchup|performance) (?:for|against)',
            r'(?:over|under) (?:performing|producing|expected)',
            r'(?:favorite|sleepers?|chalk|value) (?:play|player|pick)',
            r'(?:ownership|correlation|stack|leverage) (?:percentage|rate|score)'
        ]

    async def process_podcast_transcript(self, podcast_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process podcast transcript to extract fantasy-relevant insights.

        Args:
            podcast_data: Raw podcast data with transcript

        Returns:
            Processed data with extracted insights
        """
        try:
            transcript = podcast_data.get('transcript', '')
            if not transcript:
                return podcast_data

            # Extract fantasy insights from transcript
            insights = self._extract_fantasy_insights(transcript)

            # Categorize insights by type
            categorized_insights = self._categorize_insights(insights)

            # Calculate transcript metrics
            metrics = self._calculate_transcript_metrics(transcript, insights)

            # Prepare processed data
            processed_data = podcast_data.copy()
            processed_data.update({
                'insights': categorized_insights,
                'metrics': metrics,
                'processed_at': datetime.now(timezone.utc).isoformat(),
                'fantasy_relevance_score': self._calculate_relevance_score(insights, metrics)
            })

            logger.info("Podcast transcript processed",
                       team=podcast_data.get('team_name', ''),
                       insights_count=len(insights),
                       relevance_score=processed_data['fantasy_relevance_score'])

            return processed_data

        except Exception as e:
            logger.error("Error processing podcast transcript", error=str(e))
            return podcast_data

    def _extract_fantasy_insights(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Extract fantasy-relevant insights from podcast transcript.
        Focuses on qualitative statements that could impact DFS performance.
        """
        insights = []

        # Split transcript into sentences for analysis
        sentences = self._split_into_sentences(transcript)

        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower().strip()

            # Check for fantasy-relevant keywords
            relevance_score = self._calculate_sentence_relevance(sentence_lower)

            if relevance_score > 0.3:  # Threshold for inclusion
                insight = {
                    'content': sentence.strip(),
                    'sentence_index': i,
                    'relevance_score': relevance_score,
                    'categories': self._identify_categories(sentence_lower),
                    'mentioned_players': self._extract_player_mentions(sentence),
                    'mentioned_teams': self._extract_team_mentions(sentence),
                    'sentiment': self._analyze_sentiment(sentence),
                    'context_window': self._get_context_window(sentences, i)
                }
                insights.append(insight)

        # Filter and rank insights
        insights = [insight for insight in insights if insight['relevance_score'] > 0.4]
        insights.sort(key=lambda x: x['relevance_score'], reverse=True)

        return insights[:20]  # Top 20 most relevant insights

    def _calculate_sentence_relevance(self, sentence: str) -> float:
        """
        Calculate how relevant a sentence is to fantasy football.
        """
        score = 0.0

        # Check for fantasy keywords
        for category, keywords in self.fantasy_keywords.items():
            for keyword in keywords:
                if keyword in sentence:
                    if category == 'performance':
                        score += 0.4
                    elif category == 'health':
                        score += 0.5  # Health is very important for DFS
                    elif category == 'situational':
                        score += 0.3
                    elif category == 'team_dynamics':
                        score += 0.2

        # Check for DFS-specific patterns
        for pattern in self.dfs_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                score += 0.6

        # Boost score for player mentions
        if self._contains_player_indicators(sentence):
            score += 0.2

        # Length consideration (avoid very short or very long sentences)
        word_count = len(sentence.split())
        if 5 <= word_count <= 50:
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0

    def _identify_categories(self, sentence: str) -> List[str]:
        """
        Identify which fantasy categories this sentence relates to.
        """
        categories = []

        for category, keywords in self.fantasy_keywords.items():
            if any(keyword in sentence for keyword in keywords):
                categories.append(category)

        return list(set(categories))

    def _extract_player_mentions(self, sentence: str) -> List[str]:
        """
        Extract mentioned NFL player names from sentence.
        This is a simplified version - in production you'd use NER.
        """
        # Common NFL player name patterns (simplified)
        players = []

        # Look for capitalized names that might be players
        words = sentence.split()
        for i, word in enumerate(words):
            if word.istitle() and len(word) > 2:
                # Check if next word is also capitalized (first + last name)
                if i + 1 < len(words) and words[i + 1].istitle():
                    player_name = f"{word} {words[i + 1]}"
                    # Filter out common non-player words
                    if not any(skip in player_name.lower() for skip in
                              ['the', 'and', 'but', 'for', 'with', 'this', 'that']):
                        players.append(player_name)

        return list(set(players))

    def _extract_team_mentions(self, sentence: str) -> List[str]:
        """
        Extract mentioned NFL team names from sentence.
        """
        # NFL team name patterns
        team_keywords = [
            'chiefs', 'chargers', 'raiders', 'broncos',
            'patriots', 'jets', 'bills', 'dolphins',
            'packers', 'vikings', 'bears', 'lions',
            'cowboys', 'eagles', 'giants', 'commanders',
            'buccaneers', 'falcons', 'panthers', 'saints',
            'steelers', 'ravens', 'bengals', 'browns',
            'titans', 'colts', 'jaguars', 'texans',
            'seahawks', 'rams', 'cardinals', '49ers'
        ]

        teams = []
        sentence_lower = sentence.lower()

        for team in team_keywords:
            if team in sentence_lower:
                teams.append(team.title())

        return list(set(teams))

    def _analyze_sentiment(self, sentence: str) -> str:
        """
        Simple sentiment analysis for fantasy context.
        """
        positive_words = ['great', 'excellent', 'outstanding', 'fantastic', 'amazing',
                         'impressive', 'strong', 'dominant', 'explosive', 'elite']
        negative_words = ['worried', 'concerned', 'struggling', 'poor', 'weak',
                         'disappointing', 'injured', 'questionable', 'doubtful']

        sentence_lower = sentence.lower()

        positive_count = sum(1 for word in positive_words if word in sentence_lower)
        negative_count = sum(1 for word in negative_words if word in sentence_lower)

        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'

    def _get_context_window(self, sentences: List[str], index: int, window: int = 2) -> str:
        """
        Get surrounding context for a sentence.
        """
        start = max(0, index - window)
        end = min(len(sentences), index + window + 1)

        context_sentences = sentences[start:end]
        return ' '.join(context_sentences)

    def _categorize_insights(self, insights: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group insights by category for better organization.
        """
        categories = {
            'performance': [],
            'health': [],
            'situational': [],
            'team_dynamics': []
        }

        for insight in insights:
            insight_categories = insight.get('categories', [])
            for category in insight_categories:
                if category in categories:
                    categories[category].append(insight)

        return categories

    def _calculate_transcript_metrics(self, transcript: str, insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate metrics about the transcript's fantasy relevance.
        """
        total_words = len(transcript.split())
        total_sentences = len(self._split_into_sentences(transcript))

        return {
            'total_words': total_words,
            'total_sentences': total_sentences,
            'insights_extracted': len(insights),
            'insights_per_sentence': len(insights) / max(total_sentences, 1),
            'insights_per_word': len(insights) / max(total_words, 1),
            'avg_relevance_score': sum(i['relevance_score'] for i in insights) / max(len(insights), 1)
        }

    def _calculate_relevance_score(self, insights: List[Dict[str, Any]], metrics: Dict[str, Any]) -> float:
        """
        Calculate overall fantasy relevance score for the transcript.
        """
        if not insights:
            return 0.0

        # Base score from insights
        base_score = sum(insight['relevance_score'] for insight in insights) / len(insights)

        # Boost for health-related insights (very important for DFS)
        health_insights = sum(1 for i in insights if 'health' in i.get('categories', []))
        health_boost = min(health_insights * 0.1, 0.3)

        # Boost for high insight density
        density_boost = min(metrics['insights_per_sentence'] * 0.2, 0.2)

        total_score = base_score + health_boost + density_boost

        return min(total_score, 1.0)

    def _contains_player_indicators(self, sentence: str) -> bool:
        """
        Check if sentence likely contains player references.
        """
        indicators = [
            'quarterback', 'qb', 'running back', 'rb', 'wide receiver', 'wr',
            'tight end', 'te', 'offensive line', 'ol', 'defensive line', 'dl',
            'linebacker', 'lb', 'defensive back', 'db', 'safety', 'cornerback'
        ]

        sentence_lower = sentence.lower()
        return any(indicator in sentence_lower for indicator in indicators)

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences for analysis.
        """
        # Simple sentence splitting (could be improved with NLTK)
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    async def process_news_article(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process news article for sentiment and fantasy relevance.
        """
        try:
            content = article_data.get('content', '')
            title = article_data.get('title', '')

            # Analyze sentiment
            sentiment = self._analyze_news_sentiment(content)

            # Check fantasy relevance
            fantasy_relevance = self._calculate_news_relevance(content, title)

            processed_data = article_data.copy()
            processed_data.update({
                'sentiment': sentiment,
                'fantasy_relevance': fantasy_relevance,
                'processed_at': datetime.now(timezone.utc).isoformat()
            })

            return processed_data

        except Exception as e:
            logger.error("Error processing news article", error=str(e))
            return article_data

    def _analyze_news_sentiment(self, content: str) -> Dict[str, Any]:
        """
        Analyze sentiment of news content.
        """
        # Simple sentiment analysis (could be enhanced with better models)
        positive_indicators = ['upgrade', 'healthy', 'returning', 'expected', 'confident']
        negative_indicators = ['downgrade', 'injury', 'concerned', 'doubtful', 'questionable']

        content_lower = content.lower()

        positive_score = sum(1 for word in positive_indicators if word in content_lower)
        negative_score = sum(1 for word in negative_indicators if word in content_lower)

        if positive_score > negative_score:
            return {'label': 'positive', 'score': 0.7}
        elif negative_score > positive_score:
            return {'label': 'negative', 'score': -0.7}
        else:
            return {'label': 'neutral', 'score': 0.0}

    def _calculate_news_relevance(self, content: str, title: str) -> float:
        """
        Calculate how relevant news is to fantasy football.
        """
        combined_text = f"{title} {content}".lower()

        relevance_score = 0.0

        # Fantasy keywords
        fantasy_terms = ['fantasy', 'dfs', 'ownership', 'projection', 'points']
        for term in fantasy_terms:
            if term in combined_text:
                relevance_score += 0.3

        # Player/team mentions
        if self._contains_player_indicators(combined_text):
            relevance_score += 0.2

        # Injury/health mentions
        if any(word in combined_text for word in ['injury', 'healthy', 'practice', 'ir']):
            relevance_score += 0.4

        return min(relevance_score, 1.0)
