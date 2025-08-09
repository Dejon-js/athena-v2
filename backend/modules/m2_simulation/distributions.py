import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from scipy import stats
import structlog

logger = structlog.get_logger()


class DistributionModeler:
    """
    Statistical distribution modeling for player fantasy points.
    Models TDs using Poisson, receptions using Negative Binomial.
    """
    
    def __init__(self):
        self.distribution_cache = {}
        
    def model_player_distribution(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Model statistical distribution for individual player.
        
        Args:
            player_data: Player statistics and projections
            
        Returns:
            Dict containing distribution parameters and samples
        """
        position = player_data.get('position', 'FLEX')
        
        if position == 'QB':
            return self._model_qb_distribution(player_data)
        elif position == 'RB':
            return self._model_rb_distribution(player_data)
        elif position in ['WR', 'TE']:
            return self._model_receiver_distribution(player_data)
        elif position == 'DST':
            return self._model_dst_distribution(player_data)
        else:
            return self._model_generic_distribution(player_data)
    
    def _model_qb_distribution(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Model QB distribution with passing and rushing components"""
        
        passing_yards_mean = player_data.get('passing_yards_proj', 250)
        passing_yards_std = passing_yards_mean * 0.2
        
        passing_tds_rate = player_data.get('passing_tds_proj', 1.5)
        
        rushing_yards_mean = player_data.get('rushing_yards_proj', 20)
        rushing_yards_std = rushing_yards_mean * 0.5
        
        rushing_tds_rate = player_data.get('rushing_tds_proj', 0.3)
        
        distribution = {
            'position': 'QB',
            'components': {
                'passing_yards': {
                    'distribution': 'normal',
                    'params': {'mean': passing_yards_mean, 'std': passing_yards_std},
                    'points_multiplier': 0.04
                },
                'passing_tds': {
                    'distribution': 'poisson',
                    'params': {'rate': passing_tds_rate},
                    'points_multiplier': 4.0
                },
                'rushing_yards': {
                    'distribution': 'normal',
                    'params': {'mean': rushing_yards_mean, 'std': rushing_yards_std},
                    'points_multiplier': 0.1
                },
                'rushing_tds': {
                    'distribution': 'poisson',
                    'params': {'rate': rushing_tds_rate},
                    'points_multiplier': 6.0
                }
            }
        }
        
        samples = self._generate_distribution_samples(distribution, 1000)
        distribution['samples'] = samples
        distribution['statistics'] = self._calculate_distribution_stats(samples)
        
        return distribution
    
    def _model_rb_distribution(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Model RB distribution with rushing and receiving components"""
        
        rushing_yards_mean = player_data.get('rushing_yards_proj', 80)
        rushing_yards_std = rushing_yards_mean * 0.3
        
        rushing_tds_rate = player_data.get('rushing_tds_proj', 0.8)
        
        receiving_yards_mean = player_data.get('receiving_yards_proj', 20)
        receiving_yards_std = receiving_yards_mean * 0.4
        
        receptions_n = 10
        receptions_p = player_data.get('receptions_proj', 2) / receptions_n
        
        receiving_tds_rate = player_data.get('receiving_tds_proj', 0.2)
        
        distribution = {
            'position': 'RB',
            'components': {
                'rushing_yards': {
                    'distribution': 'normal',
                    'params': {'mean': rushing_yards_mean, 'std': rushing_yards_std},
                    'points_multiplier': 0.1
                },
                'rushing_tds': {
                    'distribution': 'poisson',
                    'params': {'rate': rushing_tds_rate},
                    'points_multiplier': 6.0
                },
                'receiving_yards': {
                    'distribution': 'normal',
                    'params': {'mean': receiving_yards_mean, 'std': receiving_yards_std},
                    'points_multiplier': 0.1
                },
                'receptions': {
                    'distribution': 'negative_binomial',
                    'params': {'n': receptions_n, 'p': receptions_p},
                    'points_multiplier': 1.0
                },
                'receiving_tds': {
                    'distribution': 'poisson',
                    'params': {'rate': receiving_tds_rate},
                    'points_multiplier': 6.0
                }
            }
        }
        
        samples = self._generate_distribution_samples(distribution, 1000)
        distribution['samples'] = samples
        distribution['statistics'] = self._calculate_distribution_stats(samples)
        
        return distribution
    
    def _model_receiver_distribution(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Model WR/TE distribution with receiving focus"""
        
        receiving_yards_mean = player_data.get('receiving_yards_proj', 60)
        receiving_yards_std = receiving_yards_mean * 0.3
        
        receptions_n = 15
        receptions_p = player_data.get('receptions_proj', 5) / receptions_n
        
        receiving_tds_rate = player_data.get('receiving_tds_proj', 0.5)
        
        distribution = {
            'position': player_data.get('position'),
            'components': {
                'receiving_yards': {
                    'distribution': 'normal',
                    'params': {'mean': receiving_yards_mean, 'std': receiving_yards_std},
                    'points_multiplier': 0.1
                },
                'receptions': {
                    'distribution': 'negative_binomial',
                    'params': {'n': receptions_n, 'p': receptions_p},
                    'points_multiplier': 1.0
                },
                'receiving_tds': {
                    'distribution': 'poisson',
                    'params': {'rate': receiving_tds_rate},
                    'points_multiplier': 6.0
                }
            }
        }
        
        samples = self._generate_distribution_samples(distribution, 1000)
        distribution['samples'] = samples
        distribution['statistics'] = self._calculate_distribution_stats(samples)
        
        return distribution
    
    def _model_dst_distribution(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Model DST distribution with defensive components"""
        
        sacks_rate = player_data.get('sacks_proj', 2.0)
        interceptions_rate = player_data.get('interceptions_proj', 1.0)
        fumbles_rate = player_data.get('fumbles_proj', 0.5)
        tds_rate = player_data.get('defensive_tds_proj', 0.3)
        
        points_allowed_mean = player_data.get('points_allowed_proj', 20)
        points_allowed_std = points_allowed_mean * 0.3
        
        distribution = {
            'position': 'DST',
            'components': {
                'sacks': {
                    'distribution': 'poisson',
                    'params': {'rate': sacks_rate},
                    'points_multiplier': 1.0
                },
                'interceptions': {
                    'distribution': 'poisson',
                    'params': {'rate': interceptions_rate},
                    'points_multiplier': 2.0
                },
                'fumbles': {
                    'distribution': 'poisson',
                    'params': {'rate': fumbles_rate},
                    'points_multiplier': 2.0
                },
                'defensive_tds': {
                    'distribution': 'poisson',
                    'params': {'rate': tds_rate},
                    'points_multiplier': 6.0
                },
                'points_allowed': {
                    'distribution': 'normal',
                    'params': {'mean': points_allowed_mean, 'std': points_allowed_std},
                    'points_function': 'dst_points_allowed'
                }
            }
        }
        
        samples = self._generate_distribution_samples(distribution, 1000)
        distribution['samples'] = samples
        distribution['statistics'] = self._calculate_distribution_stats(samples)
        
        return distribution
    
    def _model_generic_distribution(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Model generic distribution for unknown positions"""
        
        projected_points = player_data.get('projected_points', 10)
        points_std = projected_points * 0.3
        
        distribution = {
            'position': 'GENERIC',
            'components': {
                'fantasy_points': {
                    'distribution': 'normal',
                    'params': {'mean': projected_points, 'std': points_std},
                    'points_multiplier': 1.0
                }
            }
        }
        
        samples = self._generate_distribution_samples(distribution, 1000)
        distribution['samples'] = samples
        distribution['statistics'] = self._calculate_distribution_stats(samples)
        
        return distribution
    
    def _generate_distribution_samples(self, distribution: Dict[str, Any], n_samples: int) -> List[float]:
        """Generate samples from the distribution"""
        
        samples = []
        
        for _ in range(n_samples):
            total_points = 0
            
            for component, config in distribution['components'].items():
                dist_type = config['distribution']
                params = config['params']
                
                if dist_type == 'normal':
                    value = max(0, np.random.normal(params['mean'], params['std']))
                elif dist_type == 'poisson':
                    value = np.random.poisson(params['rate'])
                elif dist_type == 'negative_binomial':
                    value = np.random.negative_binomial(params['n'], params['p'])
                else:
                    value = 0
                
                if 'points_function' in config:
                    if config['points_function'] == 'dst_points_allowed':
                        points = self._calculate_dst_points_allowed(value)
                    else:
                        points = value
                else:
                    points = value * config.get('points_multiplier', 1.0)
                
                total_points += points
            
            samples.append(max(0, total_points))
        
        return samples
    
    def _calculate_dst_points_allowed(self, points_allowed: float) -> float:
        """Calculate DST points based on points allowed"""
        
        if points_allowed == 0:
            return 10
        elif points_allowed <= 6:
            return 7
        elif points_allowed <= 13:
            return 4
        elif points_allowed <= 20:
            return 1
        elif points_allowed <= 27:
            return 0
        elif points_allowed <= 34:
            return -1
        else:
            return -4
    
    def _calculate_distribution_stats(self, samples: List[float]) -> Dict[str, float]:
        """Calculate statistics from distribution samples"""
        
        samples_array = np.array(samples)
        
        return {
            'mean': float(np.mean(samples_array)),
            'median': float(np.median(samples_array)),
            'std': float(np.std(samples_array)),
            'min': float(np.min(samples_array)),
            'max': float(np.max(samples_array)),
            'percentile_10': float(np.percentile(samples_array, 10)),
            'percentile_25': float(np.percentile(samples_array, 25)),
            'percentile_75': float(np.percentile(samples_array, 75)),
            'percentile_90': float(np.percentile(samples_array, 90)),
            'skewness': float(stats.skew(samples_array)),
            'kurtosis': float(stats.kurtosis(samples_array))
        }
    
    def fit_distribution_to_data(self, data: List[float]) -> Dict[str, Any]:
        """Fit best distribution to historical data"""
        
        data_array = np.array(data)
        
        distributions = [
            ('normal', stats.norm),
            ('gamma', stats.gamma),
            ('lognormal', stats.lognorm),
            ('beta', stats.beta)
        ]
        
        best_fit = None
        best_aic = float('inf')
        
        for name, distribution in distributions:
            try:
                params = distribution.fit(data_array)
                log_likelihood = np.sum(distribution.logpdf(data_array, *params))
                aic = 2 * len(params) - 2 * log_likelihood
                
                if aic < best_aic:
                    best_aic = aic
                    best_fit = {
                        'distribution': name,
                        'params': params,
                        'aic': aic,
                        'log_likelihood': log_likelihood
                    }
            except Exception:
                continue
        
        return best_fit or {
            'distribution': 'normal',
            'params': (np.mean(data_array), np.std(data_array)),
            'aic': float('inf'),
            'log_likelihood': float('-inf')
        }
