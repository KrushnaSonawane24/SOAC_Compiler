/**
 * Progress Timeline Component
 */

import React from 'react';
import { type JobState } from '../api/jobs';

const STAGES: JobState[] = [
    'created',
    'normalizing',
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
    const labelFor = (stage: JobState) => {
        if (stage === 'normalizing') return 'normalize';
        return stage.replace('ing', '');
    };

    return (
        <div className="flex items-center justify-between overflow-x-auto gap-4">
            {STAGES.map((stage, index) => {
                const isCompleted = currentIndex > index;
                const isCurrent = currentState === stage;

                let dotColor = 'var(--soac-card-border)';
                let labelColor = 'var(--soac-muted)';

                if (isFailed && isCurrent) {
                    dotColor = 'var(--soac-stage-failed)';
                    labelColor = 'var(--soac-stage-failed)';
                } else if (isCompleted) {
                    dotColor = 'var(--soac-stage-completed)';
                    labelColor = 'var(--soac-stage-completed)';
                } else if (isCurrent) {
                    dotColor = `var(--soac-stage-${stage})`;
                    labelColor = `var(--soac-stage-${stage})`;
                }

                return (
                    <React.Fragment key={stage}>
                        <div className="flex flex-col items-center min-w-16">
                            <div
                                className={`w-8 h-8 rounded-full flex items-center justify-center ${isCurrent && !isFailed ? 'animate-pulse' : ''}`}
                                style={{ backgroundColor: dotColor }}
                            >
                                {isCompleted ? (
                                    <svg className="w-5 h-5 text-black" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                    </svg>
                                ) : (
                                    <span className="text-black text-xs">{index + 1}</span>
                                )}
                            </div>
                            <span className="mt-2 text-xs capitalize" style={{ color: labelColor }}>
                                {labelFor(stage)}
                            </span>
                        </div>
                        {index < STAGES.length - 1 && (
                            <div
                                className="flex-1 h-1 mx-2"
                                style={{
                                    backgroundColor: isCompleted ? 'var(--soac-stage-completed)' : 'var(--soac-card-border)',
                                }}
                            />
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
};
