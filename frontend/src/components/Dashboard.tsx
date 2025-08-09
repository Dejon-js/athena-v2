import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Users, Target, Download } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { ApiService } from '../services/ApiService';

interface DashboardProps {
  systemStatus: {
    overall_status: string;
    active_module: string | null;
    modules: Record<string, { status: string; progress: number }>;
    timestamp: string;
  };
}

const Dashboard: React.FC<DashboardProps> = ({ systemStatus }) => {
  const [optimizationStatus, setOptimizationStatus] = useState<any>(null);
  const [projectionStatus, setProjectionStatus] = useState<any>(null);
  const [performanceData, setPerformanceData] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [optStatus, projStatus, perfData] = await Promise.all([
          ApiService.getOptimizationStatus(),
          ApiService.getProjectionStatus(),
          ApiService.getPerformanceMetrics()
        ]);
        
        setOptimizationStatus(optStatus);
        setProjectionStatus(projStatus);
        setPerformanceData(perfData.performance || []);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const moduleProgress = Object.entries(systemStatus.modules).map(([name, data]) => ({
    name: name.replace('m', 'M').replace('_', ' '),
    progress: data.progress,
    status: data.status
  }));

  const samplePerformanceData = [
    { week: 'Week 1', roi: 1.15, accuracy: 85 },
    { week: 'Week 2', roi: 1.08, accuracy: 88 },
    { week: 'Week 3', roi: 1.22, accuracy: 82 },
    { week: 'Week 4', roi: 1.05, accuracy: 90 },
    { week: 'Week 5', roi: 1.18, accuracy: 87 }
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center">
            <Target className="h-8 w-8 text-blue-400" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Lineups Generated</p>
              <p className="text-2xl font-bold text-white">
                {optimizationStatus?.lineups_generated || 0}/150
              </p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center">
            <TrendingUp className="h-8 w-8 text-green-400" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Avg Leverage Score</p>
              <p className="text-2xl font-bold text-white">2.3x</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center">
            <Users className="h-8 w-8 text-purple-400" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Ownership MAE</p>
              <p className="text-2xl font-bold text-white">2.8%</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center">
            <BarChart3 className="h-8 w-8 text-yellow-400" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Weekly ROI</p>
              <p className="text-2xl font-bold text-white">+15%</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Module Progress</h3>
          <div className="space-y-4">
            {moduleProgress.map((module) => (
              <div key={module.name}>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-300">{module.name}</span>
                  <span className="text-gray-400">{module.progress}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2 mt-1">
                  <div
                    className={`h-2 rounded-full ${
                      module.status === 'running' ? 'bg-blue-400' :
                      module.status === 'completed' ? 'bg-green-400' :
                      module.status === 'error' ? 'bg-red-400' : 'bg-gray-600'
                    }`}
                    style={{ width: `${module.progress}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Performance Trend</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={samplePerformanceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="week" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1F2937', 
                  border: '1px solid #374151',
                  borderRadius: '6px'
                }}
              />
              <Line type="monotone" dataKey="roi" stroke="#3B82F6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-white">Current Optimization Run</h3>
          <button className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            <Download className="h-4 w-4 mr-2" />
            Export Lineups
          </button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-sm text-gray-400">Execution Time</p>
            <p className="text-xl font-bold text-white">
              {optimizationStatus?.execution_time || '0'} min
            </p>
            <p className="text-xs text-gray-500">Target: 20 min</p>
          </div>
          
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-sm text-gray-400">Avg Projected Points</p>
            <p className="text-xl font-bold text-white">142.5</p>
            <p className="text-xs text-gray-500">Per lineup</p>
          </div>
          
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-sm text-gray-400">Unique Players</p>
            <p className="text-xl font-bold text-white">85</p>
            <p className="text-xs text-gray-500">Across portfolio</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
