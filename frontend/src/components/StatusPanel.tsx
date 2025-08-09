import React from 'react';
import { CheckCircle, AlertCircle, Clock, XCircle } from 'lucide-react';

interface StatusPanelProps {
  systemStatus: {
    overall_status: string;
    active_module: string | null;
    modules: Record<string, { status: string; progress: number }>;
    timestamp: string;
  };
}

const StatusPanel: React.FC<StatusPanelProps> = ({ systemStatus }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'operational':
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-400" />;
      case 'running':
        return <Clock className="h-5 w-5 text-blue-400" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-yellow-400" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-400" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'operational':
      case 'completed':
        return 'text-green-400';
      case 'running':
        return 'text-blue-400';
      case 'warning':
        return 'text-yellow-400';
      case 'error':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  const moduleDescriptions = {
    'm1_data_core': 'Ingests data from multiple sources including player stats, Vegas odds, and news sentiment',
    'm2_simulation': 'Runs Monte Carlo simulations to generate player projections and distributions',
    'm3_game_theory': 'Predicts player ownership percentages using XGBoost models',
    'm4_optimizer': 'Optimizes lineup portfolios using linear programming with PuLP',
    'm5_live_ops': 'Monitors live games and provides real-time adjustment suggestions',
    'm6_learning': 'Analyzes performance and retrains models for continuous improvement',
    'm7_adaptive': 'Handles early-season low-data mode operations for weeks 1-3'
  };

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">System Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-400">Overall Status</p>
            <div className="flex items-center mt-1">
              {getStatusIcon(systemStatus.overall_status)}
              <span className={`ml-2 font-medium ${getStatusColor(systemStatus.overall_status)}`}>
                {systemStatus.overall_status}
              </span>
            </div>
          </div>
          <div>
            <p className="text-sm text-gray-400">Active Module</p>
            <p className="text-white font-medium mt-1">
              {systemStatus.active_module || 'None'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Last Update</p>
            <p className="text-white font-medium mt-1">
              {new Date(systemStatus.timestamp).toLocaleTimeString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Version</p>
            <p className="text-white font-medium mt-1">v2.2.0</p>
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Module Status</h2>
        <div className="space-y-4">
          {Object.entries(systemStatus.modules).map(([moduleId, moduleData]) => (
            <div key={moduleId} className="border border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  {getStatusIcon(moduleData.status)}
                  <h3 className="ml-3 text-lg font-medium text-white">
                    {moduleId.replace('m', 'Module ').replace('_', ' - ')}
                  </h3>
                </div>
                <span className={`text-sm font-medium ${getStatusColor(moduleData.status)}`}>
                  {moduleData.status}
                </span>
              </div>
              
              <p className="text-sm text-gray-400 mb-3">
                {moduleDescriptions[moduleId as keyof typeof moduleDescriptions]}
              </p>
              
              {moduleData.progress > 0 && (
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-400">Progress</span>
                    <span className="text-gray-400">{moduleData.progress}%</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        moduleData.status === 'running' ? 'bg-blue-400' :
                        moduleData.status === 'completed' ? 'bg-green-400' :
                        'bg-gray-600'
                      }`}
                      style={{ width: `${moduleData.progress}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Performance Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-sm text-gray-400">Data Consistency</p>
            <p className="text-2xl font-bold text-green-400">95.2%</p>
            <p className="text-xs text-gray-500">Target: 95%</p>
          </div>
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-sm text-gray-400">Simulation Speed</p>
            <p className="text-2xl font-bold text-blue-400">42 min</p>
            <p className="text-xs text-gray-500">Target: 45 min</p>
          </div>
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-sm text-gray-400">Optimization Speed</p>
            <p className="text-2xl font-bold text-blue-400">18 min</p>
            <p className="text-xs text-gray-500">Target: 20 min</p>
          </div>
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-sm text-gray-400">Query Response</p>
            <p className="text-2xl font-bold text-green-400">3.2s</p>
            <p className="text-xs text-gray-500">Target: 5s</p>
          </div>
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-sm text-gray-400">Uptime</p>
            <p className="text-2xl font-bold text-green-400">99.98%</p>
            <p className="text-xs text-gray-500">Target: 99.95%</p>
          </div>
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-sm text-gray-400">Ownership MAE</p>
            <p className="text-2xl font-bold text-green-400">2.8%</p>
            <p className="text-xs text-gray-500">Target: 3.0%</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatusPanel;
