import React, { useEffect, useRef } from 'react';
import { Brain, Info, AlertTriangle, XCircle } from 'lucide-react';

interface Thought {
  module: string;
  message: string;
  timestamp: string;
  level: string;
}

interface ThoughtStreamProps {
  thoughts: Thought[];
}

const ThoughtStream: React.FC<ThoughtStreamProps> = ({ thoughts }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [thoughts]);

  const getIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <XCircle className="h-4 w-4 text-red-400" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-400" />;
      case 'info':
      default:
        return <Info className="h-4 w-4 text-blue-400" />;
    }
  };

  const getModuleColor = (module: string) => {
    const colors = {
      'm1_data_core': 'text-green-400',
      'm2_simulation': 'text-blue-400',
      'm3_game_theory': 'text-purple-400',
      'm4_optimizer': 'text-yellow-400',
      'm5_live_ops': 'text-red-400',
      'm6_learning': 'text-indigo-400',
      'm7_adaptive': 'text-pink-400'
    };
    return colors[module as keyof typeof colors] || 'text-gray-400';
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6 h-96">
      <div className="flex items-center mb-4">
        <Brain className="h-5 w-5 text-blue-400 mr-2" />
        <h3 className="text-lg font-semibold text-white">Thought Stream</h3>
      </div>
      
      <div 
        ref={scrollRef}
        className="h-80 overflow-y-auto space-y-3 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800"
      >
        {thoughts.length === 0 ? (
          <div className="text-center text-gray-400 mt-8">
            <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>Waiting for system activity...</p>
          </div>
        ) : (
          thoughts.map((thought, index) => (
            <div key={index} className="flex items-start space-x-3 p-3 bg-gray-700 rounded-lg">
              <div className="flex-shrink-0 mt-0.5">
                {getIcon(thought.level)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-1">
                  <span className={`text-xs font-medium ${getModuleColor(thought.module)}`}>
                    {thought.module.replace('m', 'M').replace('_', ' ')}
                  </span>
                  <span className="text-xs text-gray-500">
                    {new Date(thought.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-sm text-gray-300 leading-relaxed">
                  {thought.message}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ThoughtStream;
