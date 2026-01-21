/**
 * Log Viewer Component
 */

import React, { useRef, useEffect } from 'react';
import { type LogEntry } from '../api/jobs';

interface LogViewerProps {
    logs: LogEntry[];
}

export const LogViewer: React.FC<LogViewerProps> = ({ logs }) => {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
    }, [logs]);

    const getLevelColor = (level: string) => {
        switch (level.toLowerCase()) {
            case 'error':
                return 'text-red-400';
            case 'warning':
                return 'text-yellow-400';
            case 'info':
                return 'text-blue-400';
            default:
                return 'text-gray-400';
        }
    };

    return (
        <div
            ref={containerRef}
            className="bg-gray-900 rounded-lg p-4 font-mono text-sm h-64 overflow-y-auto"
        >
            {logs.length === 0 ? (
                <div className="text-gray-500">No logs yet...</div>
            ) : (
                logs.map((log, index) => (
                    <div key={index} className="flex gap-2 hover:bg-gray-800 px-1 rounded">
                        <span className="text-gray-500 shrink-0">
                            {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                        <span className={`shrink-0 uppercase ${getLevelColor(log.level)}`}>
                            [{log.level}]
                        </span>
                        <span className="text-gray-300">{log.message}</span>
                    </div>
                ))
            )}
        </div>
    );
};
