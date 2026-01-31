/**
 * Dashboard Page
 * 
 * Shows user's jobs with auto-refresh.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { jobsApi, type Job } from '../api/jobs';
import { StatusBadge } from '../components/StatusBadge';
import { Navbar } from '../components/Navbar';
import { useMascot } from '../mascot/MascotContext';

export const DashboardPage: React.FC = () => {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const { setState } = useMascot();
    const firstLoadRef = useRef(true);

    const fetchJobs = useCallback(async () => {
        const start = performance.now();
        try {
            const data = await jobsApi.list();
            setJobs(data);
            setError(null);
        } catch {
            setError('Failed to load jobs');
        } finally {
            if (firstLoadRef.current) {
                const elapsed = performance.now() - start;
                const wait = Math.max(0, 220 - elapsed);
                window.setTimeout(() => {
                    firstLoadRef.current = false;
                    setIsLoading(false);
                }, wait);
            }
        }
    }, []);

    useEffect(() => {
        setState({ mode: 'idle' });
        fetchJobs();

        // Auto-refresh every 5 seconds
        const interval = setInterval(fetchJobs, 5000);
        return () => clearInterval(interval);
    }, [fetchJobs, setState]);

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleString();
    };

    return (
        <div className="min-h-screen">
            <Navbar />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-semibold tracking-tight text-[color:var(--soac-text)]">Jobs</h1>
                        <p className="mt-1 text-sm text-[color:var(--soac-muted)]">recent runs and active work</p>
                    </div>
                    <Link to="/new" className="btn-primary">
                        + New Job
                    </Link>
                </div>

                {error && (
                    <div className="px-4 py-3 rounded-lg mb-4 border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] text-[color:var(--soac-text)]">
                        {error}
                    </div>
                )}

                {isLoading ? (
                    <div className="flex justify-center py-12">
                        <div className="w-full max-w-3xl space-y-3">
                            <div className="soac-skeleton h-10 w-48" />
                            <div className="soac-skeleton h-56 w-full" />
                        </div>
                    </div>
                ) : jobs.length === 0 ? (
                    <div className="card text-center py-12">
                        <div className="text-[color:var(--soac-muted)] text-lg mb-2">no jobs yet</div>
                        <div className="text-[color:var(--soac-muted)] text-sm mb-4">upload a model to start a run</div>
                        <Link to="/new" className="btn-primary">
                            Create your first job
                        </Link>
                    </div>
                ) : (
                    <div className="card overflow-hidden">
                        <table className="min-w-full divide-y divide-[color:var(--soac-border)]">
                            <thead className="bg-[color:var(--soac-card-hover)]">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-[color:var(--soac-muted)] uppercase tracking-wider">
                                        Job ID
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-[color:var(--soac-muted)] uppercase tracking-wider">
                                        Model
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-[color:var(--soac-muted)] uppercase tracking-wider">
                                        Status
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-[color:var(--soac-muted)] uppercase tracking-wider">
                                        Created
                                    </th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-[color:var(--soac-muted)] uppercase tracking-wider">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[color:var(--soac-border)]">
                                {jobs.map((job) => (
                                    <tr key={job.job_id} className="transition-colors hover:bg-[color:var(--soac-card-hover)]">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <code className="text-[color:var(--soac-secondary)] text-sm">{job.job_id}</code>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-[color:var(--soac-text)]">
                                            {job.original_filename || 'model.onnx'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <StatusBadge status={job.state} />
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-[color:var(--soac-muted)] text-sm">
                                            {formatDate(job.created_at)}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <Link
                                                to={`/jobs/${job.job_id}`}
                                                className="text-[color:var(--soac-secondary)] hover:text-[color:var(--soac-text)]"
                                            >
                                                View Details →
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </main>
        </div>
    );
};
