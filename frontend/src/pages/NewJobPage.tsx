/**
 * New Job Page
 * 
 * Upload model and configure compilation.
 */

import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { jobsApi, type CreateJobRequest } from '../api/jobs';
import { useMascot } from '../mascot/MascotContext';
import { BrutalNav } from '../brutal/BrutalNav';

type Policy = 'balanced' | 'accuracy_first' | 'latency_first' | 'mobile_first';

export const NewJobPage: React.FC = () => {
    const navigate = useNavigate();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const { setState: setMascotState } = useMascot();

    const [file, setFile] = useState<File | null>(null);
    const [policy, setPolicy] = useState<Policy>('balanced');
    const [target, setTarget] = useState<string>('android');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError(null);
            setMascotState({ mode: 'thinking', message: 'ready when you are' });
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) {
            setError('Please select a model file');
            return;
        }

        if (!target) return;

        setIsSubmitting(true);
        setError(null);
        setMascotState({ mode: 'thinking', message: 'starting a new job…' });

        try {
            const config: CreateJobRequest = {
                policy,
                targets: [target],
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
        <div className="min-h-screen selection:bg-[color:var(--soac-primary)] selection:text-black">
            <BrutalNav variant="app" />

            <main className="brutal-scroll max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 pt-32">
                <div className="text-center mb-12">
                    <h1 className="text-4xl font-semibold tracking-tight text-[color:var(--soac-text)] sm:text-5xl mb-3">
                        new job
                    </h1>
                    <p className="text-base text-[color:var(--soac-muted)] max-w-2xl mx-auto">
                        upload a model, choose targets and a policy, then start a pipeline run
                    </p>
                </div>

                <div className="brutal-panel rounded-2xl overflow-hidden p-0">
                    <form onSubmit={handleSubmit} className="p-8 md:p-12 space-y-10">
                        
                        {/* 1. Model Upload */}
                        <section>
                            <h2 className="text-2xl font-semibold text-[color:var(--soac-text)] mb-6 flex items-center">
                                <span className="step-badge mr-3">1</span>
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
                                        <div className="mx-auto w-12 h-12 bg-[color:var(--soac-primary)] rounded-full flex items-center justify-center text-black">
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
                                <span className="step-badge mr-3">2</span>
                                Deployment Targets
                            </h2>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div 
                                    className={`relative rounded-xl p-4 border-2 cursor-pointer transition-all duration-200 flex items-start space-x-4
                                        ${target === 'android' ? 'border-[color:var(--soac-primary)] bg-[color:var(--soac-card-hover)]' : 'border-[color:var(--soac-border)] bg-[color:var(--soac-card)] hover:border-[color:var(--soac-card-border)]'}`}
                                    onClick={() => setTarget('android')}
                                >
                                    <div className={`flex-shrink-0 w-6 h-6 rounded border flex items-center justify-center mt-1
                                        ${target === 'android' ? 'bg-[color:var(--soac-primary)] border-[color:var(--soac-primary)]' : 'border-[color:var(--soac-border)]'}`}>
                                        {target === 'android' && <svg className="w-4 h-4 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>}
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
                                        ${target === 'gpu' ? 'border-[color:var(--soac-primary)] bg-[color:var(--soac-card-hover)]' : 'border-[color:var(--soac-border)] bg-[color:var(--soac-card)] hover:border-[color:var(--soac-card-border)]'}`}
                                    onClick={() => setTarget('gpu')}
                                >
                                    <div className={`flex-shrink-0 w-6 h-6 rounded border flex items-center justify-center mt-1
                                        ${target === 'gpu' ? 'bg-[color:var(--soac-primary)] border-[color:var(--soac-primary)]' : 'border-[color:var(--soac-border)]'}`}>
                                        {target === 'gpu' && <svg className="w-4 h-4 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>}
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-medium text-[color:var(--soac-text)]">NVIDIA GPU (TensorRT)</h3>
                                        <p className="text-sm text-[color:var(--soac-muted)] mt-1">
                                            Engine builds for GPU inference. FP16/INT8 where supported.
                                        </p>
                                    </div>
                                </div>

                                <div 
                                    className={`relative rounded-xl p-4 border-2 cursor-pointer transition-all duration-200 flex items-start space-x-4
                                        ${target === 'onnx' ? 'border-[color:var(--soac-primary)] bg-[color:var(--soac-card-hover)]' : 'border-[color:var(--soac-border)] bg-[color:var(--soac-card)] hover:border-[color:var(--soac-card-border)]'}`}
                                    onClick={() => setTarget('onnx')}
                                >
                                    <div className={`flex-shrink-0 w-6 h-6 rounded border flex items-center justify-center mt-1
                                        ${target === 'onnx' ? 'bg-[color:var(--soac-primary)] border-[color:var(--soac-primary)]' : 'border-[color:var(--soac-border)]'}`}>
                                        {target === 'onnx' && <svg className="w-4 h-4 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>}
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-medium text-[color:var(--soac-text)]">ONNX</h3>
                                        <p className="text-sm text-[color:var(--soac-muted)] mt-1">
                                            Keep the optimized ONNX model for server/runtime deployment.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <div className="border-t border-[color:var(--soac-border)]"></div>

                        {/* 3. Optimization Policy */}
                        <section>
                            <h2 className="text-2xl font-semibold text-[color:var(--soac-text)] mb-6 flex items-center">
                                <span className="step-badge mr-3">3</span>
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
                                className={`cta-btn magnetic w-full justify-center ${(isSubmitting || !file) ? 'opacity-50 cursor-not-allowed grayscale' : ''}`}
                            >
                                <span>{isSubmitting ? 'starting…' : 'Start Job'}</span>
                            </button>
                        </div>

                    </form>
                </div>
            </main>
        </div>
    );
};
