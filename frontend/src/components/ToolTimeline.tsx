/**
 * Interactive timeline displaying autonomous agent tool executions.
 * Displays step-by-step reasoning, tool inputs, outputs, and status badges.
 */

import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Terminal,
  Search,
  FileCode,
  GitBranch,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
} from 'lucide-react';
import type { ToolCall } from '../types';

interface ToolTimelineProps {
  toolCalls?: ToolCall[];
  title?: string;
}

export default function ToolTimeline({ toolCalls = [], title = "Agent Reasoning & Execution Steps" }: ToolTimelineProps) {
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});

  if (!toolCalls || toolCalls.length === 0) {
    return null;
  }

  const toggleStep = (idx: number) => {
    setExpandedSteps(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const getToolIcon = (name: string) => {
    switch (name) {
      case 'semantic_search':
      case 'grep_search':
      case 'find_symbol':
        return <Search className="w-4 h-4 text-blue-400" />;
      case 'read_file':
      case 'list_files':
        return <FileCode className="w-4 h-4 text-emerald-400" />;
      case 'git_status':
      case 'git_diff':
      case 'git_log':
        return <GitBranch className="w-4 h-4 text-purple-400" />;
      default:
        return <Terminal className="w-4 h-4 text-amber-400" />;
    }
  };

  return (
    <div className="my-4 bg-gray-900/90 border border-gray-800 rounded-xl overflow-hidden shadow-lg">
      <div className="px-4 py-3 bg-gray-800/60 border-b border-gray-850 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-300">
            {title}
          </span>
          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-primary-950/60 text-primary-300 border border-primary-800/40">
            {toolCalls.length} {toolCalls.length === 1 ? 'step' : 'steps'}
          </span>
        </div>
      </div>

      <div className="divide-y divide-gray-800/60">
        {toolCalls.map((call, idx) => {
          const isExpanded = expandedSteps[idx] ?? false;
          const status = call.status || 'completed';
          const isError = status === 'error';

          return (
            <div key={idx} className="transition-colors hover:bg-gray-850/30">
              <button
                type="button"
                onClick={() => toggleStep(idx)}
                className="w-full px-4 py-3 flex items-center justify-between text-left gap-3 focus:outline-none"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-1.5 rounded-lg bg-gray-800 border border-gray-700/60 shrink-0">
                    {getToolIcon(call.tool)}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-gray-200">
                        Step {idx + 1}:
                      </span>
                      <span className="text-xs font-mono text-primary-400 font-medium">
                        {call.tool}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {isError ? (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-red-950/60 text-red-400 border border-red-800/50">
                      <AlertCircle className="w-3 h-3" /> Error
                    </span>
                  ) : status === 'running' ? (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-950/60 text-amber-400 border border-amber-800/50">
                      <Clock className="w-3 h-3 animate-spin" /> Running
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-950/50 text-emerald-400 border border-emerald-800/40">
                      <CheckCircle2 className="w-3 h-3" /> Done
                    </span>
                  )}
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  )}
                </div>
              </button>

              {isExpanded && (
                <div className="px-4 pb-4 pt-1 space-y-3 bg-gray-950/50 border-t border-gray-800/40">
                  {call.arguments && Object.keys(call.arguments).length > 0 && (
                    <div>
                      <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
                        Parameters:
                      </div>
                      <pre className="p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-xs font-mono text-gray-300 overflow-x-auto">
                        {JSON.stringify(call.arguments, null, 2)}
                      </pre>
                    </div>
                  )}

                  {call.result && (
                    <div>
                      <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
                        Output / Observation:
                      </div>
                      <pre className="p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-xs font-mono text-gray-300 max-h-60 overflow-y-auto whitespace-pre-wrap">
                        {typeof call.result === 'string'
                          ? call.result
                          : JSON.stringify(call.result, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
