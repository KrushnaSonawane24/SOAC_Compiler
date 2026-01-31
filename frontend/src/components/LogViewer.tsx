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
                return 'text-[color:var(--soac-error)]';
            case 'warning':
                return 'text-[color:var(--soac-primary)]';
            case 'info':
                return 'text-[color:var(--soac-secondary)]';
            default:
                return 'text-[color:var(--soac-muted)]';
        }
    };

    return (
        <div
            ref={containerRef}
            className="rounded-lg p-4 font-mono text-sm h-64 overflow-y-auto bg-[color:var(--soac-card)] border border-[color:var(--soac-border)] backdrop-blur-[var(--soac-blur)]"
        >
            {logs.length === 0 ? (
                <div className="text-[color:var(--soac-muted)]">No logs yet…</div>
            ) : (
                logs.map((log, index) => (
                    <div key={index} className="flex gap-2 px-1 rounded hover:bg-[color:var(--soac-card-hover)]">
                        <span className="text-[color:var(--soac-muted)] shrink-0">
                            {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                        <span className={`shrink-0 uppercase ${getLevelColor(log.level)}`}>
                            [{log.level}]
                        </span>
                        <span className="text-[color:var(--soac-text)]">{log.message}</span>
                    </div>
                ))
            )}
        </div>
    );
};
