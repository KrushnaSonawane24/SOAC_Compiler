/**
 * Dashboard Page
 * 
 * Shows user's jobs with auto-refresh.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { jobsApi, type Job } from '../api/jobs';
import { StatusBadge } from '../components/StatusBadge';
import { Navbar } from '../components/Navbar';

export const DashboardPage: React.FC = () => {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchJobs = useCallback(async () => {
        try {
            const data = await jobsApi.list();
            setJobs(data);
            setError(null);
        } catch {
            setError('Failed to load jobs');
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchJobs();

        // Auto-refresh every 5 seconds
        const interval = setInterval(fetchJobs, 5000);
        return () => clearInterval(interval);
    }, [fetchJobs]);

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleString();
    };

    return (
        <div className="min-h-screen bg-gray-900">
            <Navbar />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="flex items-center justify-between mb-8">
                    <h1 className="text-3xl font-bold text-white">Your Jobs</h1>
                    <Link to="/new" className="btn-primary">
                        + New Job
                    </Link>
                </div>

                {error && (
                    <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4">
                        {error}
                    </div>
                )}

                {isLoading ? (
                    <div className="flex justify-center py-12">
                        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
                    </div>
                ) : jobs.length === 0 ? (
                    <div className="card text-center py-12">
                        <div className="text-gray-400 text-lg mb-4">No jobs yet</div>
                        <Link to="/new" className="btn-primary">
                            Create your first job
                        </Link>
                    </div>
                ) : (
                    <div className="card overflow-hidden">
                        <table className="min-w-full divide-y divide-gray-700">
                            <thead className="bg-gray-700/50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                        Job ID
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                        Model
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                        Status
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                        Created
                                    </th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-700">
                                {jobs.map((job) => (
                                    <tr key={job.job_id} className="hover:bg-gray-700/30 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <code className="text-indigo-400 text-sm">{job.job_id}</code>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-gray-300">
                                            {job.original_filename || 'model.onnx'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <StatusBadge status={job.state} />
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-gray-400 text-sm">
                                            {formatDate(job.created_at)}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <Link
                                                to={`/jobs/${job.job_id}`}
                                                className="text-indigo-400 hover:text-indigo-300"
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
