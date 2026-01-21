/**
 * Status Badge Component
 */

import React from 'react';
import { type JobState } from '../api/jobs';

interface StatusBadgeProps {
    status: JobState;
}

const statusConfig: Record<JobState, { color: string; label: string }> = {
    pending: { color: 'bg-gray-500', label: 'Pending' },
    validating: { color: 'bg-blue-500', label: 'Validating' },
    canonicalizing: { color: 'bg-blue-500', label: 'Canonicalizing' },
    optimizing: { color: 'bg-purple-500', label: 'Optimizing' },
    benchmarking: { color: 'bg-orange-500', label: 'Benchmarking' },
    selecting: { color: 'bg-yellow-500', label: 'Selecting' },
    deploying: { color: 'bg-cyan-500', label: 'Deploying' },
    completed: { color: 'bg-green-500', label: 'Completed' },
    failed: { color: 'bg-red-500', label: 'Failed' },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
    const config = statusConfig[status] || statusConfig.pending;

    return (
        <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium text-white ${config.color}`}
        >
            {config.label}
        </span>
    );
};
