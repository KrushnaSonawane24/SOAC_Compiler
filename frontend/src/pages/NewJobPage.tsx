/**
 * New Job Page
 * 
 * Upload model and configure compilation.
 */

import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { jobsApi, type CreateJobRequest } from '../api/jobs';
import { Navbar } from '../components/Navbar';
import { useMascot } from '../mascot/MascotContext';

type Policy = 'balanced' | 'accuracy_first' | 'latency_first' | 'mobile_first';

export const NewJobPage: React.FC = () => {
    const navigate = useNavigate();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const { setState: setMascotState } = useMascot();

    const [file, setFile] = useState<File | null>(null);
    const [policy, setPolicy] = useState<Policy>('balanced');
    const [targets, setTargets] = useState<string[]>(['android', 'gpu']);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError(null);
            setMascotState({ mode: 'thinking', message: 'ready when you are' });
        }
    };

    const toggleTarget = (target: string) => {
        setTargets(prev => 
            prev.includes(target) 
                ? prev.filter(t => t !== target)
                : [...prev, target]
        );
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) {
            setError('Please select a model file');
            return;
        }

        if (targets.length === 0) {
            setError('Please select at least one deployment target');
            return;
        }

        setIsSubmitting(true);
        setError(null);
        setMascotState({ mode: 'thinking', message: 'starting a new job…' });

        try {
            const config: CreateJobRequest = {
                policy,
                targets,
                compilation_policy: policy // For backward compatibility if needed
            };

            const job = await jobsApi.create(file, config);
            navigate(`/jobs/${job.job_id}`);
        } catch (err: unknown) {
            type ApiErrorBody = { detail?: string };
            type AxiosLikeError = { response?: { data?: ApiErrorBody } };
            const maybeAxiosError = err as AxiosLikeError;
            const detail = maybeAxiosError.response?.data?.detail;
            setError(typeof detail === 'string' ? detail : 'Failed to create job');
            setIsSubmitting(false);
            setMascotState({ mode: 'failure', message: 'could not start the job' });
        }
    };

    return (
        <div className="min-h-screen selection:bg-[color:var(--soac-primary)] selection:text-white">
            <Navbar />

            <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <div className="text-center mb-12">
                    <h1 className="text-4xl font-semibold tracking-tight text-[color:var(--soac-text)] sm:text-5xl mb-3">
                        new job
                    </h1>
                    <p className="text-base text-[color:var(--soac-muted)] max-w-2xl mx-auto">
                        upload a model, choose targets and a policy, then start a pipeline run
                    </p>
                </div>

                <div className="card rounded-2xl overflow-hidden p-0">
                    <form onSubmit={handleSubmit} className="p-8 md:p-12 space-y-10">
                        
                        {/* 1. Model Upload */}
                        <section>
                            <h2 className="text-2xl font-semibold text-[color:var(--soac-text)] mb-6 flex items-center">
                                <span className="bg-[color:var(--soac-primary)] text-white rounded-full w-8 h-8 flex items-center justify-center text-sm mr-3">1</span>
                                Upload Model
                            </h2>
                            <div 
                                className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200 ease-in-out cursor-pointer group
                                    ${file ? 'border-[color:var(--soac-primary)] bg-[color:var(--soac-card-hover)]' : 'border-[color:var(--soac-border)] hover:border-[color:var(--soac-card-border)] hover:bg-[color:var(--soac-card-hover)]'}`}
                                onClick={() => fileInputRef.current?.click()}
                            >
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    onChange={handleFileChange}
                                    className="hidden"
                                    accept=".onnx,.h5,.keras,.pb,.tflite"
                                />
                                
                                {file ? (
                                    <div className="space-y-2">
                                        <div className="mx-auto w-12 h-12 bg-[color:var(--soac-primary)] rounded-full flex items-center justify-center text-white">
                                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" /></svg>
                                        </div>
                                        <p className="text-lg font-medium text-[color:var(--soac-text)]">{file.name}</p>
                                        <p className="text-sm text-[color:var(--soac-secondary)]">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                        <p className="text-xs text-[color:var(--soac-muted)] mt-2">click to change file</p>
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        <div className="mx-auto w-12 h-12 rounded-full flex items-center justify-center transition-colors bg-[color:var(--soac-card-hover)] text-[color:var(--soac-muted)] group-hover:text-[color:var(--soac-text)]">
                                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
                                        </div>
                                        <p className="text-lg font-medium text-[color:var(--soac-text)]">click to upload</p>
                                        <p className="text-sm text-[color:var(--soac-muted)]">ONNX, TensorFlow, Keras (max 500MB)</p>
                                    </div>
                                )}
                            </div>
                        </section>

                        <div className="border-t border-[color:var(--soac-border)]"></div>

                        {/* 2. Deployment Targets */}
                        <section>
                            <h2 className="text-2xl font-semibold text-[color:var(--soac-text)] mb-6 flex items-center">
                                <span className="bg-[color:var(--soac-primary)] text-white rounded-full w-8 h-8 flex items-center justify-center text-sm mr-3">2</span>
                                Deployment Targets
                            </h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div 
                                    className={`relative rounded-xl p-4 border-2 cursor-pointer transition-all duration-200 flex items-start space-x-4
                                        ${targets.includes('android') ? 'border-[color:var(--soac-primary)] bg-[color:var(--soac-card-hover)]' : 'border-[color:var(--soac-border)] bg-[color:var(--soac-card)] hover:border-[color:var(--soac-card-border)]'}`}
                                    onClick={() => toggleTarget('android')}
                                >
                                    <div className={`flex-shrink-0 w-6 h-6 rounded border flex items-center justify-center mt-1
                                        ${targets.includes('android') ? 'bg-[color:var(--soac-primary)] border-[color:var(--soac-primary)]' : 'border-[color:var(--soac-border)]'}`}>
                                        {targets.includes('android') && <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>}
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-medium text-[color:var(--soac-text)]">Android (TFLite)</h3>
                                        <p className="text-sm text-[color:var(--soac-muted)] mt-1">
                                            Optimized for edge devices. INT8 with stability fallback.
                                        </p>
                                    </div>
                                </div>

                                <div 
                                    className={`relative rounded-xl p-4 border-2 cursor-pointer transition-all duration-200 flex items-start space-x-4
                                        ${targets.includes('gpu') ? 'border-[color:var(--soac-primary)] bg-[color:var(--soac-card-hover)]' : 'border-[color:var(--soac-border)] bg-[color:var(--soac-card)] hover:border-[color:var(--soac-card-border)]'}`}
                                    onClick={() => toggleTarget('gpu')}
                                >
                                    <div className={`flex-shrink-0 w-6 h-6 rounded border flex items-center justify-center mt-1
                                        ${targets.includes('gpu') ? 'bg-[color:var(--soac-primary)] border-[color:var(--soac-primary)]' : 'border-[color:var(--soac-border)]'}`}>
                                        {targets.includes('gpu') && <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>}
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-medium text-[color:var(--soac-text)]">NVIDIA GPU (TensorRT)</h3>
                                        <p className="text-sm text-[color:var(--soac-muted)] mt-1">
                                            Engine builds for GPU inference. FP16/INT8 where supported.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <div className="border-t border-[color:var(--soac-border)]"></div>

                        {/* 3. Optimization Policy */}
                        <section>
                            <h2 className="text-2xl font-semibold text-[color:var(--soac-text)] mb-6 flex items-center">
                                <span className="bg-[color:var(--soac-primary)] text-white rounded-full w-8 h-8 flex items-center justify-center text-sm mr-3">3</span>
                                Optimization Policy
                            </h2>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {[
                                    { id: 'balanced', label: 'Balanced', desc: 'Best trade-off between speed and accuracy.' },
                                    { id: 'accuracy_first', label: 'Accuracy First', desc: 'Minimal quantization, max precision (FP16/FP32).' },
                                    { id: 'latency_first', label: 'Latency First', desc: 'Aggressive optimization (INT8) for max speed.' },
                                ].map((option) => (
                                    <div 
                                        key={option.id}
                                        className={`relative rounded-xl p-5 border-2 cursor-pointer transition-all duration-200
                                            ${policy === option.id ? 'border-[color:var(--soac-primary)] bg-[color:var(--soac-card-hover)]' : 'border-[color:var(--soac-border)] bg-[color:var(--soac-card)] hover:border-[color:var(--soac-card-border)]'}`}
                                        onClick={() => setPolicy(option.id as Policy)}
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <h3 className="text-lg font-medium text-[color:var(--soac-text)]">{option.label}</h3>
                                            <div className={`w-5 h-5 rounded-full border flex items-center justify-center
                                                ${policy === option.id ? 'border-[color:var(--soac-primary)]' : 'border-[color:var(--soac-border)]'}`}>
                                                {policy === option.id && <div className="w-3 h-3 rounded-full bg-[color:var(--soac-primary)]" />}
                                            </div>
                                        </div>
                                        <p className="text-sm text-[color:var(--soac-muted)]">{option.desc}</p>
                                    </div>
                                ))}
                            </div>
                        </section>

                        {/* Error Message */}
                        {error && (
                            <div className="rounded-lg p-4 flex items-start border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] text-[color:var(--soac-text)]">
                                <svg className="w-5 h-5 mr-3 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                <span>{error}</span>
                            </div>
                        )}

                        {/* Submit Button */}
                        <div className="pt-4">
                            <button
                                type="submit"
                                disabled={isSubmitting || !file}
                                className={`btn-primary w-full py-4 text-lg font-semibold rounded-xl ${(isSubmitting || !file) ? 'opacity-50 cursor-not-allowed grayscale' : ''}`}
                            >
                                {isSubmitting ? (
                                    <>
                                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                                        starting…
                                    </>
                                ) : (
                                    'Start Job'
                                )}
                            </button>
                        </div>

                    </form>
                </div>
            </main>
        </div>
    );
};
