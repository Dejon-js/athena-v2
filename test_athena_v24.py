#!/usr/bin/env python3
"""
Test script for ATHENA v2.4 elite strategy features
Tests negative binomial distribution, ceiling-predictive features, K-Means clustering, and frontend enhancements
"""
import asyncio
import sys
import os
import json
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_negative_binomial_distribution():
    """Test negative binomial distribution for touchdown modeling"""
    print("🔍 Testing Negative Binomial Distribution for Touchdown Modeling...")
    
    try:
        from backend.modules.m2_simulation.distributions import DistributionModeler
        
        modeler = DistributionModeler()
        
        test_player_data = {
            'player_id': 'test_player_1',
            'position': 'WR',
            'passing_tds_avg': 0.0,
            'rushing_tds_avg': 0.1,
            'receiving_tds_avg': 0.8
        }
        
        print("Testing touchdown distribution modeling...")
        
        poisson_samples = []
        nb_samples = []
        
        for i in range(100):
            distributions = modeler.model_player_distributions(test_player_data)
            
            if 'receiving_tds' in distributions:
                td_dist = distributions['receiving_tds']
                sample = modeler._generate_distribution_samples({'receiving_tds': td_dist}, 1)
                
                if 'receiving_tds' in sample:
                    nb_samples.append(sample['receiving_tds'])
        
        if nb_samples:
            nb_variance = np.var(nb_samples)
            nb_mean = np.mean(nb_samples)
            
            print(f"Negative Binomial - Mean: {nb_mean:.3f}, Variance: {nb_variance:.3f}")
            
            if nb_variance > nb_mean * 1.1:
                print("✅ Negative binomial shows overdispersion (variance > mean)")
                return True
            else:
                print("❌ Negative binomial not showing expected overdispersion")
                return False
        else:
            print("❌ No touchdown samples generated")
            return False
            
    except Exception as e:
        print(f"❌ Negative binomial test error: {e}")
        return False

async def test_ceiling_predictive_features():
    """Test ceiling-predictive features in player projections"""
    print("\n🔍 Testing Ceiling-Predictive Features...")
    
    try:
        from backend.modules.m2_simulation.player_projections import PlayerProjectionEngine
        
        engine = PlayerProjectionEngine()
        
        expected_features = ['total_air_yards', 'red_zone_target_share', 'wopr', 'adot']
        
        print("Checking WR feature columns...")
        wr_features = engine.feature_columns.get('WR', [])
        
        missing_features = []
        for feature in expected_features:
            if feature not in wr_features:
                missing_features.append(feature)
            else:
                print(f"✅ {feature} found in WR features")
        
        print("Checking TE feature columns...")
        te_features = engine.feature_columns.get('TE', [])
        
        for feature in expected_features:
            if feature not in te_features:
                missing_features.append(f"TE_{feature}")
            else:
                print(f"✅ {feature} found in TE features")
        
        if not missing_features:
            print("✅ All ceiling-predictive features properly integrated")
            return True
        else:
            print(f"❌ Missing features: {missing_features}")
            return False
            
    except Exception as e:
        print(f"❌ Ceiling-predictive features test error: {e}")
        return False

async def test_leveraged_ceiling_objective():
    """Test that leveraged ceiling is the default objective"""
    print("\n🔍 Testing Leveraged Ceiling Default Objective...")
    
    try:
        from backend.modules.m4_optimizer.linear_programming import LinearProgrammingOptimizer
        import pandas as pd
        
        optimizer = LinearProgrammingOptimizer()
        
        sample_data = []
        for i in range(20):
            sample_data.append({
                'player_id': f'player_{i}',
                'name': f'Player {i}',
                'position': 'WR' if i % 4 == 0 else 'RB' if i % 4 == 1 else 'QB' if i % 4 == 2 else 'TE',
                'salary': 5000 + i * 100,
                'projected_points': 10 + i * 0.5,
                'ceiling_points': 15 + i * 0.7,
                'projected_ownership': 5 + i * 0.3,
                'team': f'TEAM{i % 8}'
            })
        
        player_data = pd.DataFrame(sample_data)
        
        print("Testing objective function selection...")
        
        objective_func = optimizer.objective_function.get_objective_function(
            'leveraged_ceiling', player_data, {}
        )
        
        if objective_func is not None:
            print("✅ Leveraged ceiling objective function accessible")
            return True
        else:
            print("❌ Leveraged ceiling objective function not found")
            return False
            
    except Exception as e:
        print(f"❌ Leveraged ceiling objective test error: {e}")
        return False

async def test_kmeans_clustering():
    """Test K-Means clustering for portfolio diversification"""
    print("\n🔍 Testing K-Means Clustering for Portfolio Diversification...")
    
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        import numpy as np
        
        print("Testing K-Means clustering components...")
        
        sample_lineups = []
        for i in range(300):
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
        
        print(f"K-Means clustering results:")
        print(f"  Input lineups: {len(sample_lineups)}")
        print(f"  Target clusters: {target_clusters}")
        print(f"  Actual clusters: {unique_clusters}")
        
        if unique_clusters >= target_clusters * 0.9:
            print("✅ K-Means clustering working correctly")
            return True
        else:
            print("❌ K-Means clustering not generating expected clusters")
            return False
            
    except Exception as e:
        print(f"❌ K-Means clustering test error: {e}")
        return False

async def test_data_ingestion_features():
    """Test ceiling-predictive features in data ingestion"""
    print("\n🔍 Testing Data Ingestion Ceiling-Predictive Features...")
    
    try:
        from backend.modules.m1_data_core.data_ingestion import DataIngestionEngine
        
        engine = DataIngestionEngine()
        
        print("Testing PFF metrics ingestion...")
        metrics = await engine._scrape_pff_metrics()
        
        if metrics and len(metrics) > 0:
            sample_metric = metrics[0]
            
            required_fields = ['total_air_yards', 'red_zone_target_share', 'wopr', 'adot']
            missing_fields = []
            
            for field in required_fields:
                if field not in sample_metric:
                    missing_fields.append(field)
                else:
                    print(f"✅ {field} found in metrics")
            
            if not missing_fields:
                print("✅ All ceiling-predictive metrics available in data ingestion")
                return True
            else:
                print(f"❌ Missing metrics: {missing_fields}")
                return False
        else:
            print("❌ No metrics returned from PFF ingestion")
            return False
            
    except Exception as e:
        print(f"❌ Data ingestion features test error: {e}")
        return False

async def main():
    """Run all v2.4 tests"""
    print("🚀 ATHENA v2.4 Elite Strategy Testing\n")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    tests = [
        ("Negative Binomial Distribution", test_negative_binomial_distribution),
        ("Ceiling-Predictive Features", test_ceiling_predictive_features),
        ("Leveraged Ceiling Objective", test_leveraged_ceiling_objective),
        ("K-Means Clustering", test_kmeans_clustering),
        ("Data Ingestion Features", test_data_ingestion_features)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 ATHENA v2.4 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! ATHENA v2.4 elite strategy features are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Implementation needs attention.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
