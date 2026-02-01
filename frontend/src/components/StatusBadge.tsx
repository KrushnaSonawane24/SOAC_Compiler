/**
 * Status Badge Component
 */

import React from 'react';
import { type JobState } from '../api/jobs';

interface StatusBadgeProps {
    status: JobState;
}

const statusConfig: Record<JobState, { color: string; label: string }> = {
    created: { color: 'var(--soac-stage-created)', label: 'Created' },
    normalizing: { color: 'var(--soac-stage-normalizing)', label: 'Normalizing' },
    validating: { color: 'var(--soac-stage-validating)', label: 'Validating' },
    canonicalizing: { color: 'var(--soac-stage-canonicalizing)', label: 'Canonicalizing' },
    optimizing: { color: 'var(--soac-stage-optimizing)', label: 'Optimizing' },
    benchmarking: { color: 'var(--soac-stage-benchmarking)', label: 'Benchmarking' },
    selecting: { color: 'var(--soac-stage-selecting)', label: 'Selecting' },
    deploying: { color: 'var(--soac-stage-deploying)', label: 'Deploying' },
    completed: { color: 'var(--soac-stage-completed)', label: 'Completed' },
    failed: { color: 'var(--soac-stage-failed)', label: 'Failed' },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
    const config = statusConfig[status] || statusConfig.created;

    return (
        <span
            className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
            style={{
                border: `1px solid ${config.color}`,
                color: config.color,
                backgroundColor: 'transparent',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
            }}
        >
            {config.label}
        </span>
    );
};
