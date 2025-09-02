# Temporal Processor for ATHENA v2.2
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import structlog

logger = structlog.get_logger()


class TemporalVectorProcessor:
    """
    Handles temporal relevance and freshness scoring for vector search results.
    Ensures more recent and relevant content gets higher priority in search results.
    """

    def __init__(self):
        # Temporal decay factors
        self.decay_factors = {
            'podcast_transcript': {
                'half_life_days': 7,  # Podcasts stay relevant for about a week
                'max_age_days': 90    # Discard after 90 days
            },
            'news_article': {
                'half_life_days': 3,  # News relevance drops quickly
                'max_age_days': 30    # Discard after 30 days
            }
        }

    def apply_temporal_scoring(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply temporal relevance scoring to search results.
        More recent content gets higher temporal scores.
        """
        current_time = datetime.now(timezone.utc)

        for result in search_results:
            content_type = result.get('content_type', 'unknown')
            publish_date_str = result.get('publish_date', '')

            # Parse publish date
            publish_date = self._parse_date(publish_date_str)
            if not publish_date:
                result['temporal_score'] = 0.5  # Default neutral score
                continue

            # Calculate age in days
            age_days = (current_time - publish_date).days

            # Calculate temporal relevance score
            temporal_score = self._calculate_temporal_relevance(
                age_days, content_type
            )

            result['temporal_score'] = temporal_score
            result['age_days'] = age_days

        return search_results

    def _calculate_temporal_relevance(self, age_days: float, content_type: str) -> float:
        """
        Calculate temporal relevance score using exponential decay.
        """
        if content_type not in self.decay_factors:
            return 0.5  # Neutral score for unknown types

        config = self.decay_factors[content_type]

        # Check if content is too old
        if age_days > config['max_age_days']:
            return 0.1  # Very low score for stale content

        # Exponential decay formula
        half_life = config['half_life_days']
        decay_rate = -0.693 / half_life  # Natural log of 0.5 divided by half-life

        # Calculate decay factor
        decay_factor = 2 ** (-age_days / half_life)

        # Scale to 0.1-1.0 range for better control
        temporal_score = 0.1 + (decay_factor * 0.9)

        return temporal_score

    def combine_relevance_scores(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Combine semantic similarity with temporal relevance for final ranking.
        """
        for result in search_results:
            semantic_score = result.get('relevance_score', 0.5)
            temporal_score = result.get('temporal_score', 0.5)

            # Weighted combination (60% semantic, 40% temporal)
            combined_score = (semantic_score * 0.6) + (temporal_score * 0.4)

            result['combined_score'] = combined_score

        # Sort by combined score
        search_results.sort(key=lambda x: x.get('combined_score', 0), reverse=True)

        return search_results

    def filter_by_freshness(self, search_results: List[Dict[str, Any]], max_age_days: int = 30) -> List[Dict[str, Any]]:
        """
        Filter out results that are too old.
        """
        filtered_results = []

        for result in search_results:
            age_days = result.get('age_days', 0)
            if age_days <= max_age_days:
                filtered_results.append(result)

        return filtered_results

    def boost_recent_highlights(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply additional boost to very recent content and high-impact insights.
        """
        current_time = datetime.now(timezone.utc)

        for result in search_results:
            boost_multiplier = 1.0

            # Boost for very recent content (last 24 hours)
            age_days = result.get('age_days', 0)
            if age_days < 1:
                boost_multiplier *= 1.3

            # Boost for health-related insights
            if result.get('content_type') == 'podcast_transcript':
                categories = result.get('categories', [])
                if 'health' in categories:
                    boost_multiplier *= 1.2

            # Boost for high sentiment impact
            sentiment = result.get('sentiment', 'neutral')
            if sentiment in ['positive', 'negative']:
                boost_multiplier *= 1.1

            # Apply boost to combined score
            if 'combined_score' in result:
                result['combined_score'] *= boost_multiplier

        return search_results

    def get_content_freshness_distribution(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the age distribution of search results.
        """
        age_ranges = {
            'very_recent': 0,  # < 1 day
            'recent': 0,       # 1-3 days
            'this_week': 0,    # 4-7 days
            'this_month': 0,   # 8-30 days
            'older': 0         # > 30 days
        }

        for result in search_results:
            age_days = result.get('age_days', 0)

            if age_days < 1:
                age_ranges['very_recent'] += 1
            elif age_days < 4:
                age_ranges['recent'] += 1
            elif age_days < 8:
                age_ranges['this_week'] += 1
            elif age_days < 31:
                age_ranges['this_month'] += 1
            else:
                age_ranges['older'] += 1

        return age_ranges

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string into datetime object.
        """
        if not date_str:
            return None

        try:
            # Try ISO format first
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))

            # Try common date formats
            formats = [
                '%Y-%m-%d',
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d',
                '%m/%d/%Y',
                '%B %d, %Y'
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

            logger.warning("Could not parse date string", date_str=date_str)
            return None

        except Exception as e:
            logger.error("Error parsing date", date_str=date_str, error=str(e))
            return None

    def calculate_content_velocity(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate how quickly new content is being produced for different sources.
        """
        # Group by content type and team
        content_groups = {}

        for result in search_results:
            content_type = result.get('content_type', 'unknown')
            team = result.get('team_name', 'unknown')

            key = f"{content_type}_{team}"
            if key not in content_groups:
                content_groups[key] = []

            content_groups[key].append(result)

        # Calculate velocity metrics
        velocity_stats = {}

        for group_key, results in content_groups.items():
            if len(results) < 2:
                velocity_stats[group_key] = {'velocity': 0, 'avg_gap_days': None}
                continue

            # Sort by date (most recent first)
            sorted_results = sorted(results, key=lambda x: x.get('age_days', 0))

            # Calculate average gap between content pieces
            gaps = []
            for i in range(1, len(sorted_results)):
                gap = sorted_results[i-1]['age_days'] - sorted_results[i]['age_days']
                if gap > 0:  # Only count forward gaps
                    gaps.append(gap)

            avg_gap = sum(gaps) / len(gaps) if gaps else None
            velocity = len(results) / max(sorted_results[0]['age_days'], 1)  # Items per day

            velocity_stats[group_key] = {
                'velocity': round(velocity, 3),
                'avg_gap_days': round(avg_gap, 1) if avg_gap else None,
                'total_items': len(results)
            }

        return velocity_stats

    def predict_relevance_trend(self, search_results: List[Dict[str, Any]], days_ahead: int = 7) -> Dict[str, Any]:
        """
        Predict how relevance scores might trend in the future.
        """
        current_time = datetime.now(timezone.utc)

        # Group by content type
        trends = {}

        for result in search_results:
            content_type = result.get('content_type', 'unknown')
            publish_date = self._parse_date(result.get('publish_date', ''))

            if not publish_date:
                continue

            if content_type not in trends:
                trends[content_type] = []

            age_days = (current_time - publish_date).days
            relevance = result.get('relevance_score', 0.5)

            trends[content_type].append({
                'age_days': age_days,
                'relevance': relevance
            })

        # Calculate trend predictions
        predictions = {}

        for content_type, data_points in trends.items():
            if len(data_points) < 3:  # Need minimum data points
                predictions[content_type] = {'trend': 'insufficient_data'}
                continue

            # Simple linear trend calculation
            x_values = [point['age_days'] for point in data_points]
            y_values = [point['relevance'] for point in data_points]

            # Calculate slope (trend)
            n = len(x_values)
            slope = sum((x - sum(x_values)/n) * (y - sum(y_values)/n) for x, y in zip(x_values, y_values))
            slope /= sum((x - sum(x_values)/n) ** 2 for x in x_values) if x_values else 0

            # Predict future relevance
            future_relevance = y_values[-1] + (slope * days_ahead)

            predictions[content_type] = {
                'current_avg_relevance': sum(y_values) / len(y_values),
                'trend_slope': slope,
                'predicted_relevance': max(0, min(1, future_relevance)),
                'trend_direction': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
            }

        return predictions
