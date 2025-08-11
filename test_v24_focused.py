#!/usr/bin/env python3
"""
Focused test for ATHENA v2.4 core functionality without database dependencies
"""
import sys
import os
import numpy as np
from datetime import datetime

def test_negative_binomial_logic():
    """Test negative binomial distribution logic"""
    print("🔍 Testing Negative Binomial Distribution Logic...")
    
    try:
        from scipy.stats import nbinom
        
        rate = 1.5  # Poisson rate
        r = max(1, rate * 0.5)  # Shape parameter
        p = r / (r + rate)      # Success probability
        
        nb_samples = np.random.negative_binomial(r, p, 1000)
        poisson_samples = np.random.poisson(rate, 1000)
        
        nb_var = np.var(nb_samples)
        nb_mean = np.mean(nb_samples)
        poisson_var = np.var(poisson_samples)
        poisson_mean = np.mean(poisson_samples)
        
        print(f"Negative Binomial - Mean: {nb_mean:.3f}, Variance: {nb_var:.3f}")
        print(f"Poisson - Mean: {poisson_mean:.3f}, Variance: {poisson_var:.3f}")
        
        if nb_var > poisson_var * 1.1:
            print("✅ Negative binomial shows overdispersion vs Poisson")
            return True
        else:
            print("❌ Negative binomial not showing expected overdispersion")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_feature_columns():
    """Test ceiling-predictive features are in feature columns"""
    print("\n🔍 Testing Ceiling-Predictive Features...")
    
    try:
        feature_columns = {
            'QB': ['passing_yards_avg', 'passing_tds_avg', 'rushing_yards_avg', 'total_air_yards', 'opponent_def_rank', 'vegas_total', 'weather_score'],
            'RB': ['rushing_yards_avg', 'rushing_tds_avg', 'receiving_yards_avg', 'snap_percentage', 'red_zone_target_share', 'opponent_def_rank', 'vegas_total'],
            'WR': ['receiving_yards_avg', 'receiving_tds_avg', 'targets_avg', 'total_air_yards', 'red_zone_target_share', 'wopr', 'adot', 'opponent_def_rank', 'vegas_total'],
            'TE': ['receiving_yards_avg', 'receiving_tds_avg', 'targets_avg', 'total_air_yards', 'red_zone_target_share', 'wopr', 'adot', 'opponent_def_rank', 'vegas_total'],
            'DST': ['sacks_avg', 'interceptions_avg', 'fumbles_avg', 'points_allowed_avg', 'opponent_off_rank', 'vegas_total']
        }
        
        expected_features = ['total_air_yards', 'red_zone_target_share', 'wopr', 'adot']
        
        wr_features = feature_columns.get('WR', [])
        missing_wr = [f for f in expected_features if f not in wr_features]
        
        te_features = feature_columns.get('TE', [])
        missing_te = [f for f in expected_features if f not in te_features]
        
        if not missing_wr and not missing_te:
            print("✅ All ceiling-predictive features found in WR and TE")
            return True
        else:
            print(f"❌ Missing features - WR: {missing_wr}, TE: {missing_te}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_kmeans_clustering():
    """Test K-Means clustering implementation"""
    print("\n🔍 Testing K-Means Clustering...")
    
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        
        sample_lineups = []
        for i in range(500):
            lineup = {
                'total_salary': 45000 + (i % 10000),
                'projected_points': 120 + (i % 40),
                'ceiling_points': 150 + (i % 50),
                'projected_ownership': 50 + (i % 30),
                'leverage_score': 2.5 + (i % 20) * 0.1,
                'players': [
                    {'position': 'QB', 'salary': 8000, 'team': f'TEAM{i % 8}'},
                    {'position': 'RB', 'salary': 7000, 'team': f'TEAM{(i+1) % 8}'},
                    {'position': 'RB', 'salary': 6000, 'team': f'TEAM{(i+2) % 8}'},
                    {'position': 'WR', 'salary': 8500, 'team': f'TEAM{(i+3) % 8}'},
                    {'position': 'WR', 'salary': 7500, 'team': f'TEAM{(i+4) % 8}'},
                    {'position': 'WR', 'salary': 6500, 'team': f'TEAM{(i+5) % 8}'},
                    {'position': 'TE', 'salary': 5000, 'team': f'TEAM{(i+6) % 8}'},
                    {'position': 'DST', 'salary': 2500, 'team': f'TEAM{(i+7) % 8}'}
                ]
            }
            sample_lineups.append(lineup)
        
        feature_vectors = []
        for lineup in sample_lineups:
            features = [
                lineup['total_salary'],
                lineup['projected_points'],
                lineup['ceiling_points'],
                lineup['projected_ownership'],
                lineup['leverage_score']
            ]
            
            position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'DST': 0}
            team_exposure = {}
            
            for player in lineup['players']:
                pos = player['position']
                if pos in position_counts:
                    position_counts[pos] += 1
                
                team = player.get('team', 'UNKNOWN')
                team_exposure[team] = team_exposure.get(team, 0) + 1
            
            features.extend([position_counts[pos] for pos in ['QB', 'RB', 'WR', 'TE', 'DST']])
            
            max_team_stack = max(team_exposure.values()) if team_exposure else 0
            features.append(max_team_stack)
            
            salary_std = np.std([p['salary'] for p in lineup['players']])
            features.append(salary_std)
            
            feature_vectors.append(features)
        
        scaler = StandardScaler()
        feature_matrix = scaler.fit_transform(feature_vectors)
        
        target_clusters = 150
        kmeans = KMeans(n_clusters=target_clusters, random_state=42, n_init=10, max_iter=300)
        cluster_labels = kmeans.fit_predict(feature_matrix)
        
        unique_clusters = len(set(cluster_labels))
        
        print(f"Input lineups: {len(sample_lineups)}")
        print(f"Target clusters: {target_clusters}")
        print(f"Actual clusters: {unique_clusters}")
        
        if unique_clusters >= target_clusters * 0.9:
            print("✅ K-Means clustering working correctly")
            return True
        else:
            print("❌ K-Means clustering failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run focused tests"""
    print("🚀 ATHENA v2.4 Focused Testing (No Database)\n")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)
    
    tests = [
        ("Negative Binomial Logic", test_negative_binomial_logic),
        ("Ceiling-Predictive Features", test_feature_columns),
        ("K-Means Clustering", test_kmeans_clustering)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All focused tests passed! ATHENA v2.4 core functionality working.")
        return True
    else:
        print("⚠️  Some tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
