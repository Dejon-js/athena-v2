import React, { useState, useEffect } from 'react';
import { Activity, Brain, BarChart3, Settings } from 'lucide-react';
import Dashboard from './components/Dashboard';
import StatusPanel from './components/StatusPanel';
import ThoughtStream from './components/ThoughtStream';
import ChatInterface from './components/ChatInterface';
import { WebSocketService } from './services/WebSocketService';
import { ApiService } from './services/ApiService';

interface SystemStatus {
  overall_status: string;
  active_module: string | null;
  modules: Record<string, { status: string; progress: number }>;
  timestamp: string;
}

function App() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    overall_status: 'initializing',
    active_module: null,
    modules: {},
    timestamp: new Date().toISOString()
  });
  const [thoughtStream, setThoughtStream] = useState<Array<{
    module: string;
    message: string;
    timestamp: string;
    level: string;
  }>>([]);
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    const wsService = new WebSocketService();
    
    wsService.onStatusUpdate = (status) => {
      setSystemStatus(status);
    };
    
    wsService.onThoughtStream = (thought) => {
      setThoughtStream(prev => [...prev.slice(-49), thought]);
    };
    
    wsService.connect();
    
    return () => {
      wsService.disconnect();
    };
  }, []);

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'status', label: 'System Status', icon: Activity },
    { id: 'chat', label: 'Ask ATHENA', icon: Brain },
    { id: 'settings', label: 'Settings', icon: Settings }
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <Brain className="h-8 w-8 text-blue-400 mr-3" />
              <h1 className="text-2xl font-bold text-white">ATHENA v2.4</h1>
              <span className="ml-3 px-2 py-1 text-xs bg-blue-600 rounded-full">
                NFL DFS Optimizer
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <div className={`flex items-center px-3 py-1 rounded-full text-sm ${
                systemStatus.overall_status === 'operational' 
                  ? 'bg-green-600' 
                  : systemStatus.overall_status === 'error'
                  ? 'bg-red-600'
                  : 'bg-yellow-600'
              }`}>
                <div className="w-2 h-2 bg-white rounded-full mr-2 animate-pulse"></div>
                {systemStatus.overall_status}
              </div>
            </div>
          </div>
        </div>
      </header>

      <nav className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center px-3 py-4 text-sm font-medium border-b-2 ${
                    activeTab === tab.id
                      ? 'border-blue-400 text-blue-400'
                      : 'border-transparent text-gray-300 hover:text-white hover:border-gray-300'
                  }`}
                >
                  <Icon className="h-4 w-4 mr-2" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <div className="lg:col-span-3">
            {activeTab === 'dashboard' && <Dashboard systemStatus={systemStatus} />}
            {activeTab === 'status' && <StatusPanel systemStatus={systemStatus} />}
            {activeTab === 'chat' && <ChatInterface />}
            {activeTab === 'settings' && (
              <div className="bg-gray-800 rounded-lg p-6">
                <h2 className="text-xl font-semibold mb-6">Optimization Settings</h2>
                
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-medium mb-4">Objective Function Weights</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Leveraged Ceiling Weight: <span className="text-blue-400">50%</span>
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          defaultValue="50"
                          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Projected Points Weight: <span className="text-green-400">30%</span>
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          defaultValue="30"
                          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Value Score Weight: <span className="text-yellow-400">20%</span>
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          defaultValue="20"
                          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                        />
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="text-lg font-medium mb-4">Portfolio Settings</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Target Lineups
                        </label>
                        <input
                          type="number"
                          defaultValue="150"
                          min="1"
                          max="500"
                          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Initial Pool Size
                        </label>
                        <input
                          type="number"
                          defaultValue="3000"
                          min="150"
                          max="10000"
                          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t border-gray-700">
                    <button className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors">
                      Save Settings
                    </button>
                    <button className="ml-3 bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-md transition-colors">
                      Reset to Defaults
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
          
          <div className="lg:col-span-1">
            <ThoughtStream thoughts={thoughtStream} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
