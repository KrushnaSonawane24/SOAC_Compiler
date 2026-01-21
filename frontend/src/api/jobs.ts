/**
 * Jobs API
 */

import api from './client';

export type JobState =
    | 'pending'
    | 'validating'
    | 'canonicalizing'
    | 'optimizing'
    | 'benchmarking'
    | 'selecting'
    | 'deploying'
    | 'completed'
    | 'failed';

export interface Job {
    job_id: string;
    user_id: string;
    state: JobState;
    created_at: string;
    updated_at: string;
    input_filename: string;
    stages?: StageInfo[];
    metadata?: Record<string, string | number | boolean | null>;
}

export interface StageInfo {
    stage: string;
    success: boolean;
    duration_ms: number;
    message: string;
}

export interface LogEntry {
    timestamp: string;
    level: string;
    message: string;
}

export interface Artifact {
    artifact_id: string;
    name: string;
    path: string;
    type: string;
    size_bytes: number;
}

export interface CreateJobRequest {
    compilation_policy?: string;
    build_mode?: string;
    reproducible_seed?: number;
    simulate_accuracy_drop?: number;
    simulate_latency_spike?: number;
    simulate_memory_exceed?: number;
}

export const jobsApi = {
    list: async (): Promise<Job[]> => {
        const response = await api.get<{ jobs: Job[] }>('/jobs');
        return response.data.jobs;
    },

    get: async (jobId: string): Promise<Job> => {
        const response = await api.get<Job>(`/jobs/${jobId}`);
        return response.data;
    },

    create: async (file: File, config: CreateJobRequest): Promise<Job> => {
        const formData = new FormData();
        formData.append('file', file);

        // Add config as JSON
        Object.entries(config).forEach(([key, value]) => {
            if (value !== undefined) {
                formData.append(key, String(value));
            }
        });

        const response = await api.post<Job>('/jobs', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    },

    getLogs: async (jobId: string): Promise<LogEntry[]> => {
        const response = await api.get<{ logs: LogEntry[] }>(`/jobs/${jobId}/logs`);
        return response.data.logs;
    },

    getArtifacts: async (jobId: string): Promise<Artifact[]> => {
        const response = await api.get<{ artifacts: Artifact[] }>(`/jobs/${jobId}/artifacts`);
        return response.data.artifacts;
    },

    downloadArtifact: async (jobId: string, artifactId: string): Promise<Blob> => {
        const response = await api.get(`/jobs/${jobId}/artifacts/${artifactId}`, {
            responseType: 'blob',
        });
        return response.data;
    },
};
