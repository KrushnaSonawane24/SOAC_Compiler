/**
 * Job Detail Page
 * 
 * Shows job progress, logs, explainability, and artifacts.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { jobsApi, type Job, type LogEntry, type Artifact } from '../api/jobs';
import { Navbar } from '../components/Navbar';
import { StatusBadge } from '../components/StatusBadge';
import { ProgressTimeline } from '../components/ProgressTimeline';
import { LogViewer } from '../components/LogViewer';
import { LatencyChart } from '../charts/LatencyChart';

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

    const fetchData = useCallback(async () => {
        if (!jobId) return;

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

            setError(null);
        } catch {
            setError('Failed to load job details');
            setIsLive(false);
        } finally {
            setIsLoading(false);
        }
    }, [jobId]);

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
            <div className="min-h-screen bg-gray-900">
                <Navbar />
                <div className="flex justify-center py-24">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
                </div>
            </div>
        );
    }

    if (error || !job) {
        return (
            <div className="min-h-screen bg-gray-900">
                <Navbar />
                <div className="max-w-4xl mx-auto px-4 py-8">
                    <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg">
                        {error || 'Job not found'}
                    </div>
                    <Link to="/" className="text-indigo-400 hover:text-indigo-300 mt-4 inline-block">
                        ← Back to Dashboard
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

    return (
        <div className="min-h-screen bg-gray-900">
            <Navbar />

            <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <Link to="/" className="text-indigo-400 hover:text-indigo-300 text-sm mb-2 inline-block">
                            ← Back to Dashboard
                        </Link>
                        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                            <code className="text-indigo-400">{job.job_id}</code>
                            <StatusBadge status={job.state} />
                            {isLive && (
                                <span className="flex h-3 w-3 relative">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                                </span>
                            )}
                        </h1>
                    </div>
                </div>

                {/* Progress Timeline */}
                <div className="card mb-6">
                    <h2 className="text-lg font-semibold text-white mb-4">Pipeline Progress</h2>
                    <ProgressTimeline currentState={job.state} />
                </div>

                {/* Tabs */}
                <div className="flex gap-1 mb-6 bg-gray-800 p-1 rounded-lg w-fit">
                    {(['overview', 'logs', 'artifacts'] as const).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-4 py-2 rounded-md text-sm font-medium capitalize transition-colors ${activeTab === tab
                                ? 'bg-indigo-600 text-white'
                                : 'text-gray-400 hover:text-white'
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
                            <div className="card lg:col-span-2 bg-gradient-to-r from-gray-800 to-gray-900 border border-gray-700">
                                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                                    <span className="text-green-400">⚡</span> Optimization Results
                                </h3>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    {/* Speedup */}
                                    <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700">
                                        <div className="text-gray-400 text-sm mb-1">Speedup</div>
                                        <div className="text-3xl font-bold text-green-400">
                                            {summary.speedup ? `${summary.speedup}x` : '-'}
                                        </div>
                                        <div className="text-xs text-gray-500 mt-2 flex justify-between">
                                            <span>
                                                Original: {typeof summary?.baseline_latency === 'number' ? `${summary.baseline_latency.toFixed(2)}ms` : '-'}
                                            </span>
                                            <span className="text-white">
                                                Now: {typeof summary?.selected_latency === 'number' ? `${summary.selected_latency.toFixed(2)}ms` : '-'}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Size Reduction */}
                                    <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700">
                                        <div className="text-gray-400 text-sm mb-1">Size Reduction</div>
                                        <div className="text-3xl font-bold text-blue-400">
                                            {summary.size_reduction ? `${summary.size_reduction}%` : '-'}
                                        </div>
                                        <div className="text-xs text-gray-500 mt-2 flex justify-between">
                                            <span>
                                                Original: {typeof summary?.baseline_size === 'number' ? `${(summary.baseline_size / 1024 / 1024).toFixed(1)}MB` : '-'}
                                            </span>
                                            <span className="text-white">
                                                Now: {typeof summary?.selected_size === 'number' ? `${(summary.selected_size / 1024 / 1024).toFixed(1)}MB` : '-'}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Quality/Accuracy */}
                                    <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700">
                                        <div className="text-gray-400 text-sm mb-1">Quality Check</div>
                                        <div className={`text-3xl font-bold ${(summary.accuracy_drop ?? 0) > 0.02 ? 'text-red-400' : 'text-indigo-400'}`}>
                                            {summary.accuracy_drop !== undefined && summary.accuracy_drop !== null 
                                                ? (summary.accuracy_drop <= 0.001 ? 'Lossless' : `-${(summary.accuracy_drop * 100).toFixed(2)}%`) 
                                                : 'Verified'}
                                        </div>
                                        <div className="text-xs text-gray-500 mt-2">
                                            {(summary.accuracy_drop ?? 0) > 0.02 ? 'Exceeds threshold' : 'Within 2% threshold'}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : null}

                        {/* Job Info */}
                        <div className="card">
                            <h3 className="text-lg font-semibold text-white mb-4">Job Information</h3>
                            <dl className="space-y-3">
                                <div className="flex justify-between">
                                    <dt className="text-gray-400">Created</dt>
                                    <dd className="text-white">{new Date(job.created_at).toLocaleString()}</dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-gray-400">Model</dt>
                                    <dd className="text-white">{job.original_filename || 'model.onnx'}</dd>
                                </div>
                                {selectedVariant && (
                                    <div className="flex justify-between">
                                        <dt className="text-gray-400">Selected Variant</dt>
                                        <dd className="text-green-400 font-mono">{selectedVariant}</dd>
                                    </div>
                                )}
                            </dl>
                        </div>

                        {/* Build Fingerprint */}
                        {fingerprint ? (
                            <div className="card">
                                <h3 className="text-lg font-semibold text-white mb-4">Build Fingerprint</h3>
                                <div className="bg-gray-900 rounded-lg p-4">
                                    <code className="text-green-400 text-sm break-all">{fingerprint}</code>
                                </div>
                                <p className="text-gray-400 text-sm mt-2">
                                    Unique hash for reproducibility verification
                                </p>
                            </div>
                        ) : null}

                        {/* Stage Timing */}
                        {job.stages?.length ? (
                            <div className="card lg:col-span-2">
                                <h3 className="text-lg font-semibold text-white mb-4">Stage Timing</h3>
                                <LatencyChart
                                    data={job.stages.map((s) => ({
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
                                <h3 className="text-lg font-semibold text-white mb-4">Selection Rationale</h3>
                                <div className="bg-indigo-900/30 border border-indigo-700 rounded-lg p-4">
                                    <p className="text-indigo-300">{selectionReason}</p>
                                </div>
                            </div>
                        ) : null}
                    </div>
                )}

                {activeTab === 'logs' && (
                    <div className="card">
                        <h3 className="text-lg font-semibold text-white mb-4">Execution Logs</h3>
                        <LogViewer logs={logs} />
                    </div>
                )}

                {activeTab === 'artifacts' && (
                    <div className="card">
                        <h3 className="text-lg font-semibold text-white mb-4">Deployment Artifacts</h3>

                        {job.state !== 'completed' ? (
                            <div className="text-gray-400 text-center py-8">
                                Artifacts will be available after job completion
                            </div>
                        ) : artifacts.length === 0 ? (
                            <div className="text-gray-400 text-center py-8">
                                No artifacts found
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {artifacts.map((artifact) => (
                                    <div
                                        key={artifact.artifact_id}
                                        className="flex items-center justify-between bg-gray-700/50 rounded-lg p-4"
                                    >
                                        <div>
                                            <div className="text-white font-medium">{artifact.name}</div>
                                            <div className="text-gray-400 text-sm">
                                                {artifact.platform} • {artifact.format} • {(artifact.size_bytes / 1024).toFixed(1)} KB • {artifact.status}
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => handleDownload(artifact)}
                                            className="btn-primary text-sm"
                                        >
                                            Download
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
