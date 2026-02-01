/**
 * Job Detail Page
 * 
 * Shows job progress, logs, explainability, and artifacts.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { jobsApi, type Job, type LogEntry, type Artifact } from '../api/jobs';
import { StatusBadge } from '../components/StatusBadge';
import { ProgressTimeline } from '../components/ProgressTimeline';
import { LogViewer } from '../components/LogViewer';
import { LatencyChart } from '../charts/LatencyChart';
import { useMascot } from '../mascot/MascotContext';
import { BrutalNav } from '../brutal/BrutalNav';

type BenchmarkSummary = {
    baseline_latency?: number | null;
    selected_latency?: number | null;
    speedup?: number | null;
    baseline_size?: number | null;
    selected_size?: number | null;
    size_reduction?: number | null;
    baseline_accuracy?: number | null;
    selected_accuracy?: number | null;
    accuracy_drop?: number | null;
};

const STAGE_ORDER = ['created', 'validating', 'canonicalizing', 'optimizing', 'benchmarking', 'selecting', 'deploying', 'completed'] as const;
const stageIndex = (name: unknown) => {
    if (typeof name !== 'string') return Number.MAX_SAFE_INTEGER;
    const idx = STAGE_ORDER.indexOf(name as (typeof STAGE_ORDER)[number]);
    return idx === -1 ? Number.MAX_SAFE_INTEGER : idx;
};

const pickPrimaryArtifact = (params: {
    state: Job['state'];
    artifacts: Artifact[];
    selectedVariant?: string;
}): Artifact | null => {
    if (params.state !== 'completed') return null;
    if (!params.artifacts.length) return null;

    if (params.selectedVariant) {
        const match = params.artifacts.find(a => a.name.toLowerCase().includes(params.selectedVariant!.toLowerCase()));
        if (match) return match;
    }

    const preferNames = ['final', 'selected', 'best', 'optimized'];
    const byName = params.artifacts.find(a => preferNames.some(k => a.name.toLowerCase().includes(k)));
    if (byName) return byName;

    return params.artifacts[0] ?? null;
};

export const JobDetailPage: React.FC = () => {
    const { jobId } = useParams<{ jobId: string }>();
    const [job, setJob] = useState<Job | null>(null);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [artifacts, setArtifacts] = useState<Artifact[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'overview' | 'logs' | 'artifacts'>('overview');
    const [isLive, setIsLive] = useState(false);
    const lastKnownStateRef = useRef<Job['state'] | null>(null);
    const firstLoadRef = useRef(true);
    const { setState: setMascotState } = useMascot();

    const fetchData = useCallback(async () => {
        if (!jobId) return;
        const start = performance.now();

        try {
            const [jobData, logsData] = await Promise.all([
                jobsApi.get(jobId),
                jobsApi.getLogs(jobId),
            ]);
            setJob(jobData);
            setLogs(logsData);
            lastKnownStateRef.current = jobData.state;

            if ('artifacts' in jobData && Array.isArray(jobData.artifacts)) setArtifacts(jobData.artifacts);
            setIsLive(!['completed', 'failed'].includes(jobData.state));
            if (jobData.state === 'completed') setMascotState({ mode: 'success' });
            else if (jobData.state === 'failed') setMascotState({ mode: 'failure' });
            else if (jobData.state === 'benchmarking') setMascotState({ mode: 'benchmarking' });
            else setMascotState({ mode: 'thinking' });

            setError(null);
        } catch {
            setError('Failed to load job details');
            setIsLive(false);
            setMascotState({ mode: 'failure', message: 'could not load job details' });
        } finally {
            if (firstLoadRef.current) {
                const elapsed = performance.now() - start;
                const wait = Math.max(0, 240 - elapsed);
                window.setTimeout(() => {
                    firstLoadRef.current = false;
                    setIsLoading(false);
                }, wait);
            }
        }
    }, [jobId, setMascotState]);

    useEffect(() => {
        fetchData();

        const interval = setInterval(() => {
            const state = lastKnownStateRef.current;
            if (state && ['completed', 'failed'].includes(state)) return;
            fetchData();
        }, 1000);

        return () => clearInterval(interval);
    }, [fetchData]);

    const handleDownload = async (artifact: Artifact) => {
        if (!jobId) return;

        try {
            const blob = await jobsApi.downloadArtifact(jobId, artifact.artifact_id);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = artifact.name;
            a.click();
            URL.revokeObjectURL(url);
        } catch {
            alert('Failed to download artifact');
        }
    };

    if (isLoading) {
        return (
            <div className="min-h-screen">
                <BrutalNav variant="app" />
                <main className="brutal-scroll max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pt-32">
                    <div className="space-y-6">
                        <div className="soac-skeleton h-8 w-72" />
                        <div className="soac-skeleton h-24 w-full" />
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div className="soac-skeleton h-56 w-full" />
                            <div className="soac-skeleton h-56 w-full" />
                        </div>
                        <div className="soac-skeleton h-72 w-full" />
                    </div>
                </main>
            </div>
        );
    }

    if (error || !job) {
        return (
            <div className="min-h-screen">
                <BrutalNav variant="app" />
                <div className="brutal-scroll max-w-4xl mx-auto px-4 py-8 pt-32">
                    <div className="px-4 py-3 rounded-lg border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] text-[color:var(--soac-text)]">
                        {error || 'Job not found'}
                    </div>
                    <Link to="/dashboard" className="nav-link magnetic" data-text="DASHBOARD">
                        ← DASHBOARD
                    </Link>
                </div>
            </div>
        );
    }

    const metadata = job.metadata || {};
    const summary = (metadata as Record<string, unknown>)?.benchmark_summary as BenchmarkSummary | undefined;
    const fingerprintValue: unknown = metadata.fingerprint;
    const fingerprint: string | undefined = typeof fingerprintValue === 'string' ? fingerprintValue : undefined;
    const selectedVariantValue: unknown = metadata.selected_variant_id;
    const selectedVariant: string | undefined = typeof selectedVariantValue === 'string' ? selectedVariantValue : undefined;
    const selectionReasonValue: unknown = metadata.selection_reason;
    const selectionReason: string | undefined = typeof selectionReasonValue === 'string' ? selectionReasonValue : undefined;
    const policyValue: unknown = metadata.policy ?? metadata.compilation_policy;
    const policy: string | undefined = typeof policyValue === 'string' ? policyValue : undefined;
    const targetsValue: unknown = metadata.targets;
    const targets: string[] | undefined = Array.isArray(targetsValue) ? targetsValue.filter((t): t is string => typeof t === 'string') : undefined;

    const primaryArtifact = pickPrimaryArtifact({ state: job.state, artifacts, selectedVariant });
    const convertedModelLabel =
        primaryArtifact ? `${primaryArtifact.platform} • ${primaryArtifact.format}` : selectedVariant ? selectedVariant : undefined;
    const sortedStages = (job.stages ?? []).slice().sort((a, b) => stageIndex(a?.name) - stageIndex(b?.name));

    return (
        <div className="min-h-screen">
            <BrutalNav variant="app" />

            <main className="brutal-scroll max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pt-32">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <Link to="/dashboard" className="nav-link magnetic" data-text="DASHBOARD">
                            ← DASHBOARD
                        </Link>
                        <h1 className="text-2xl font-semibold tracking-tight text-[color:var(--soac-text)] flex items-center gap-3">
                            <span className="job-id">{job.job_id}</span>
                            <StatusBadge status={job.state} />
                            {isLive && (
                                <span className="flex h-3 w-3 relative">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ backgroundColor: 'var(--soac-primary)' }}></span>
                                    <span className="relative inline-flex rounded-full h-3 w-3" style={{ backgroundColor: 'var(--soac-primary)' }}></span>
                                </span>
                            )}
                        </h1>
                    </div>
                </div>

                {/* Progress Timeline */}
                <div className="card mb-6">
                    <h2 className="text-lg font-semibold text-[color:var(--soac-text)] mb-4">Pipeline Progress</h2>
                    <ProgressTimeline currentState={job.state} />
                </div>

                {/* Tabs */}
                <div className="flex gap-1 mb-6 p-1 rounded-lg w-fit bg-[color:var(--soac-card)] border border-[color:var(--soac-card-border)] backdrop-blur-[var(--soac-blur)]">
                    {(['overview', 'logs', 'artifacts'] as const).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-4 py-2 rounded-md text-sm font-medium capitalize transition-colors ${activeTab === tab
                                ? 'bg-[color:var(--soac-primary)] text-black'
                                : 'text-[color:var(--soac-muted)] hover:text-[color:var(--soac-text)]'
                                }`}
                        >
                            {tab}
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                {activeTab === 'overview' && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        
                        {/* Optimization Summary - NEW SECTION */}
                        {summary ? (
                            <div className="card lg:col-span-2">
                                <h3 className="text-lg font-semibold text-[color:var(--soac-text)] mb-4 flex items-center gap-2">
                                    <span className="text-[color:var(--soac-primary)]">⚡</span> Optimization Results
                                </h3>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    {/* Speedup */}
                                    <div className="p-4 rounded-lg border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)]">
                                        <div className="text-[color:var(--soac-muted)] text-sm mb-1">Speedup</div>
                                        <div className="text-3xl font-bold text-[color:var(--soac-success)]">
                                            {summary.speedup ? `${summary.speedup}x` : '-'}
                                        </div>
                                        <div className="text-xs text-[color:var(--soac-muted)] mt-2 flex justify-between">
                                            <span>
                                                Original: {typeof summary?.baseline_latency === 'number' ? `${summary.baseline_latency.toFixed(2)}ms` : '-'}
                                            </span>
                                            <span className="text-[color:var(--soac-text)]">
                                                Now: {typeof summary?.selected_latency === 'number' ? `${summary.selected_latency.toFixed(2)}ms` : '-'}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Size Reduction */}
                                    <div className="p-4 rounded-lg border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)]">
                                        <div className="text-[color:var(--soac-muted)] text-sm mb-1">Size Reduction</div>
                                        <div className="text-3xl font-bold text-[color:var(--soac-success)]">
                                            {summary.size_reduction ? `${summary.size_reduction}%` : '-'}
                                        </div>
                                        <div className="text-xs text-[color:var(--soac-muted)] mt-2 flex justify-between">
                                            <span>
                                                Original: {typeof summary?.baseline_size === 'number' ? `${(summary.baseline_size / 1024 / 1024).toFixed(1)}MB` : '-'}
                                            </span>
                                            <span className="text-[color:var(--soac-text)]">
                                                Now: {typeof summary?.selected_size === 'number' ? `${(summary.selected_size / 1024 / 1024).toFixed(1)}MB` : '-'}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Quality/Accuracy */}
                                    <div className="p-4 rounded-lg border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)]">
                                        <div className="text-[color:var(--soac-muted)] text-sm mb-1">Quality Check</div>
                                        <div className={`text-3xl font-bold ${(summary.accuracy_drop ?? 0) > 0.02 ? 'text-[color:var(--soac-error)]' : 'text-[color:var(--soac-success)]'}`}>
                                            {summary.accuracy_drop !== undefined && summary.accuracy_drop !== null 
                                                ? (summary.accuracy_drop <= 0.001 ? 'Lossless' : `-${(summary.accuracy_drop * 100).toFixed(2)}%`) 
                                                : 'Verified'}
                                        </div>
                                        <div className="text-xs text-[color:var(--soac-muted)] mt-2">
                                            {(summary.accuracy_drop ?? 0) > 0.02 ? 'Exceeds threshold' : 'Within 2% threshold'}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : null}

                        {/* Final Model Download */}
                        {job.state === 'completed' ? (
                            <div className="card lg:col-span-2">
                                <h3 className="text-lg font-semibold text-[color:var(--soac-text)] mb-4">Final Model Download</h3>
                                {primaryArtifact ? (
                                    <div className="flex items-center justify-between gap-4 border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)] p-4">
                                        <div className="min-w-0">
                                            <div className="text-[color:var(--soac-text)] font-medium truncate">{primaryArtifact.name}</div>
                                            <div className="text-[color:var(--soac-muted)] text-sm">
                                                {primaryArtifact.platform} • {primaryArtifact.format} • {(primaryArtifact.size_bytes / 1024).toFixed(1)} KB
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => handleDownload(primaryArtifact)}
                                            className="cta-btn cta-btn--sm magnetic"
                                            type="button"
                                        >
                                            <span>Download Final</span>
                                        </button>
                                    </div>
                                ) : (
                                    <div className="text-[color:var(--soac-muted)]">
                                        Final model will appear here after job completion.
                                    </div>
                                )}
                                {artifacts.length > 1 ? (
                                    <div className="mt-4">
                                        <button
                                            type="button"
                                            onClick={() => setActiveTab('artifacts')}
                                            className="cta-btn cta-btn--sm magnetic"
                                        >
                                            <span>View All Artifacts</span>
                                        </button>
                                    </div>
                                ) : null}
                            </div>
                        ) : null}

                        {/* Model Changes */}
                        {job.state === 'completed' ? (
                            <div className="card lg:col-span-2">
                                <h3 className="text-lg font-semibold text-[color:var(--soac-text)] mb-4">Model Changes</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {convertedModelLabel ? (
                                        <div className="border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)] p-4">
                                            <div className="text-[color:var(--soac-muted)] text-sm mb-1">Converted Model</div>
                                            <div className="text-[color:var(--soac-text)] font-medium">{convertedModelLabel}</div>
                                        </div>
                                    ) : null}
                                    {policy ? (
                                        <div className="border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)] p-4">
                                            <div className="text-[color:var(--soac-muted)] text-sm mb-1">Policy</div>
                                            <div className="text-[color:var(--soac-text)] font-medium">{policy}</div>
                                        </div>
                                    ) : null}
                                    {targets?.length ? (
                                        <div className="border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)] p-4">
                                            <div className="text-[color:var(--soac-muted)] text-sm mb-1">Targets</div>
                                            <div className="text-[color:var(--soac-text)] font-medium">{targets.join(', ')}</div>
                                        </div>
                                    ) : null}
                                    {selectedVariant ? (
                                        <div className="border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)] p-4">
                                            <div className="text-[color:var(--soac-muted)] text-sm mb-1">Selected Variant</div>
                                            <div className="text-[color:var(--soac-primary)] font-medium">{selectedVariant}</div>
                                        </div>
                                    ) : null}
                                    {summary ? (
                                        <div className="border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)] p-4">
                                            <div className="text-[color:var(--soac-muted)] text-sm mb-1">Performance</div>
                                            <div className="text-[color:var(--soac-text)] font-medium">
                                                {typeof summary.baseline_latency === 'number' && typeof summary.selected_latency === 'number'
                                                    ? `${summary.baseline_latency.toFixed(2)}ms → ${summary.selected_latency.toFixed(2)}ms`
                                                    : 'Verified'}
                                            </div>
                                            <div className="text-[color:var(--soac-muted)] text-sm mt-1">
                                                {summary.speedup ? `Speedup: ${summary.speedup}x` : null}
                                            </div>
                                        </div>
                                    ) : null}
                                    {summary ? (
                                        <div className="border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)] p-4">
                                            <div className="text-[color:var(--soac-muted)] text-sm mb-1">Model Size</div>
                                            <div className="text-[color:var(--soac-text)] font-medium">
                                                {typeof summary.baseline_size === 'number' && typeof summary.selected_size === 'number'
                                                    ? `${(summary.baseline_size / 1024 / 1024).toFixed(1)}MB → ${(summary.selected_size / 1024 / 1024).toFixed(1)}MB`
                                                    : 'Measured'}
                                            </div>
                                            <div className="text-[color:var(--soac-muted)] text-sm mt-1">
                                                {summary.size_reduction ? `Reduction: ${summary.size_reduction}%` : null}
                                            </div>
                                        </div>
                                    ) : null}
                                    {summary ? (
                                        <div className="border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)] p-4">
                                            <div className="text-[color:var(--soac-muted)] text-sm mb-1">Accuracy</div>
                                            <div className="text-[color:var(--soac-text)] font-medium">
                                                {summary.accuracy_drop !== undefined && summary.accuracy_drop !== null
                                                    ? (summary.accuracy_drop <= 0.001 ? 'Lossless' : `Drop: ${(summary.accuracy_drop * 100).toFixed(2)}%`)
                                                    : 'Verified'}
                                            </div>
                                        </div>
                                    ) : null}
                                </div>
                            </div>
                        ) : null}

                        {/* Job Info */}
                        <div className="card">
                            <h3 className="text-lg font-semibold text-[color:var(--soac-text)] mb-4">Job Information</h3>
                            <dl className="space-y-3">
                                <div className="flex justify-between">
                                    <dt className="text-[color:var(--soac-muted)]">Created</dt>
                                    <dd className="text-[color:var(--soac-text)]">{new Date(job.created_at).toLocaleString()}</dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-[color:var(--soac-muted)]">Model</dt>
                                    <dd className="text-[color:var(--soac-text)]">{job.original_filename || 'model.onnx'}</dd>
                                </div>
                                {selectedVariant && (
                                    <div className="flex justify-between">
                                        <dt className="text-[color:var(--soac-muted)]">Selected Variant</dt>
                                        <dd className="text-[color:var(--soac-primary)]">{selectedVariant}</dd>
                                    </div>
                                )}
                            </dl>
                        </div>

                        {/* Build Fingerprint */}
                        {fingerprint ? (
                            <div className="card">
                                <h3 className="text-lg font-semibold text-[color:var(--soac-text)] mb-4">Build Fingerprint</h3>
                                <div className="rounded-lg p-4 bg-[color:var(--soac-card-hover)] border border-[color:var(--soac-border)]">
                                    <span className="job-id">{fingerprint}</span>
                                </div>
                                <p className="text-[color:var(--soac-muted)] text-sm mt-2">
                                    Unique hash for reproducibility verification
                                </p>
                            </div>
                        ) : null}

                        {/* Stage Timing */}
                        {job.stages?.length ? (
                            <div className="card lg:col-span-2">
                                <h3 className="text-lg font-semibold text-[color:var(--soac-text)] mb-4">Stage Timing</h3>
                                <LatencyChart
                                    data={sortedStages.map((s) => ({
                                        name: ((s && s.name) || 'unknown').replace('ing', ''),
                                        latency: typeof s.duration_ms === 'number' ? s.duration_ms : 0,
                                        selected: s.name === 'completed',
                                    }))}
                                />
                            </div>
                        ) : null}

                        {/* Explainability (if available) */}
                        {selectionReason ? (
                            <div className="card lg:col-span-2">
                                <h3 className="text-lg font-semibold text-[color:var(--soac-text)] mb-4">Selection Rationale</h3>
                                <div className="rounded-lg p-4 bg-[color:var(--soac-card-hover)] border border-[color:var(--soac-border)]">
                                    <p className="text-[color:var(--soac-text)]">{selectionReason}</p>
                                </div>
                            </div>
                        ) : null}
                    </div>
                )}

                {activeTab === 'logs' && (
                    <div className="card">
                        <h3 className="text-lg font-semibold text-[color:var(--soac-text)] mb-4">Execution Logs</h3>
                        <LogViewer logs={logs} />
                    </div>
                )}

                {activeTab === 'artifacts' && (
                    <div className="card">
                        <h3 className="text-lg font-semibold text-[color:var(--soac-text)] mb-4">Deployment Artifacts</h3>

                        {job.state !== 'completed' ? (
                            <div className="text-[color:var(--soac-muted)] text-center py-8">
                                Artifacts will be available after job completion
                            </div>
                        ) : artifacts.length === 0 ? (
                            <div className="text-[color:var(--soac-muted)] text-center py-8">
                                No artifacts found
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {artifacts.map((artifact) => (
                                    <div
                                        key={artifact.artifact_id}
                                        className="flex items-center justify-between rounded-lg p-4 brutal-panel"
                                    >
                                        <div>
                                            <div className="text-[color:var(--soac-text)] font-medium">{artifact.name}</div>
                                            <div className="text-[color:var(--soac-muted)] text-sm">
                                                {artifact.platform} • {artifact.format} • {(artifact.size_bytes / 1024).toFixed(1)} KB • {artifact.status}
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => handleDownload(artifact)}
                                            className="cta-btn cta-btn--sm magnetic"
                                        >
                                            <span>Download</span>
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Error Message */}
                {job.state === 'failed' && (
                    <div className="card mt-6 bg-red-900/30 border-red-700">
                        <h3 className="text-lg font-semibold text-red-400 mb-2">Job Failed</h3>
                        <p className="text-red-300">
                            {(metadata.error as string) || 'An error occurred during compilation'}
                        </p>
                    </div>
                )}
            </main>
        </div>
    );
};
