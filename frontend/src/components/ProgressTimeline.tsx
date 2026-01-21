/**
 * Progress Timeline Component
 */

import React from 'react';
import { type JobState } from '../api/jobs';

const STAGES: JobState[] = [
    'validating',
    'canonicalizing',
    'optimizing',
    'benchmarking',
    'selecting',
    'deploying',
    'completed',
];

interface ProgressTimelineProps {
    currentState: JobState;
}

export const ProgressTimeline: React.FC<ProgressTimelineProps> = ({ currentState }) => {
    const currentIndex = STAGES.indexOf(currentState);
    const isFailed = currentState === 'failed';

    return (
        <div className="flex items-center justify-between">
            {STAGES.map((stage, index) => {
                const isCompleted = currentIndex > index;
                const isCurrent = currentState === stage;

                let bgColor = 'bg-gray-600';
                let textColor = 'text-gray-400';

                if (isFailed && isCurrent) {
                    bgColor = 'bg-red-500';
                    textColor = 'text-red-400';
                } else if (isCompleted) {
                    bgColor = 'bg-green-500';
                    textColor = 'text-green-400';
                } else if (isCurrent) {
                    bgColor = 'bg-indigo-500 animate-pulse';
                    textColor = 'text-indigo-400';
                }

                return (
                    <React.Fragment key={stage}>
                        <div className="flex flex-col items-center">
                            <div
                                className={`w-8 h-8 rounded-full flex items-center justify-center ${bgColor}`}
                            >
                                {isCompleted ? (
                                    <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                    </svg>
                                ) : (
                                    <span className="text-white text-xs">{index + 1}</span>
                                )}
                            </div>
                            <span className={`mt-2 text-xs capitalize ${textColor}`}>
                                {stage.replace('ing', '')}
                            </span>
                        </div>
                        {index < STAGES.length - 1 && (
                            <div
                                className={`flex-1 h-1 mx-2 ${isCompleted ? 'bg-green-500' : 'bg-gray-600'
                                    }`}
                            />
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
};
