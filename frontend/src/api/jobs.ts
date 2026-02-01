/**
 * Jobs API
 */

import api from './client';

export type JobState =
    | 'created'
    | 'normalizing'
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
    state: JobState;
    created_at: string;
    updated_at: string;
    original_filename: string;
    file_size_bytes: number;
    progress: number;
    current_stage?: string | null;
    selected_variant?: string | null;
    selection_reason?: string | null;
    stages?: StageInfo[];
    artifacts?: Artifact[];
    metadata?: Record<string, unknown>;
}

export interface StageInfo {
    name: string;
    success: boolean;
    duration_ms?: number | null;
    message?: string | null;
}

export interface LogEntry {
    timestamp: string;
    level: string;
    message: string;
    stage?: string;
}

export interface Artifact {
    artifact_id: string;
    name: string;
    platform: string;
    format: string;
    size_bytes: number;
    status: string;
}

export interface CreateJobRequest {
    compilation_policy?: string;
    targets?: string[];  // Added targets
    policy?: string;     // Added policy (redundant with compilation_policy, but aligning with backend Form params)
    build_mode?: string;
    reproducible_seed?: number;
    simulate_accuracy_drop?: number;
    simulate_latency_spike?: number;
    simulate_memory_exceed?: number;
}

export interface JobCreated {
    job_id: string;
    state: JobState;
}

export const jobsApi = {
    list: async (): Promise<Job[]> => {
        const response = await api.get<{ jobs: Job[] }>('/api/jobs');
        return response.data.jobs;
    },

    get: async (jobId: string): Promise<Job> => {
        const response = await api.get<Job>(`/api/jobs/${jobId}`);
        return response.data;
    },

    create: async (file: File, config: CreateJobRequest): Promise<JobCreated> => {
        const formData = new FormData();
        formData.append('file', file);

        // Add config params
        if (config.targets) {
            // Backend expects comma-separated string or multiple values. 
            // Sending as comma-separated string is safer for FormData handling in some backends,
            // but FastAPI handles list of strings well too.
            // Let's send as multiple entries for 'targets' to match List[str] = Form(...)
            config.targets.forEach(t => formData.append('targets', t));
        }
        
        if (config.policy) {
            formData.append('policy', config.policy);
        }

        // Add other config params as JSON/String
        Object.entries(config).forEach(([key, value]) => {
            if (key !== 'targets' && key !== 'policy' && value !== undefined) {
                formData.append(key, String(value));
            }
        });

        const response = await api.post<JobCreated>('/api/jobs', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    },

    retry: async (jobId: string): Promise<JobCreated> => {
        const response = await api.post<JobCreated>(`/api/jobs/${jobId}/retry`);
        return response.data;
    },

    getLogs: async (jobId: string): Promise<LogEntry[]> => {
        const response = await api.get<{ logs: LogEntry[] }>(`/api/jobs/${jobId}/logs`);
        return response.data.logs;
    },

    downloadArtifact: async (jobId: string, artifactId: string): Promise<Blob> => {
        const response = await api.get(`/api/jobs/${jobId}/artifacts/${artifactId}`, {
            responseType: 'blob',
        });
        return response.data;
    },
};
