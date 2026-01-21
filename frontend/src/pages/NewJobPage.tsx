/**
 * New Job Page
 * 
 * Upload model and configure compilation.
 */

import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { jobsApi, type CreateJobRequest } from '../api/jobs';
import { Navbar } from '../components/Navbar';

type Policy = 'balanced' | 'accuracy_first' | 'latency_first' | 'mobile_first';

export const NewJobPage: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const [policy, setPolicy] = useState<Policy>('balanced');
    const [reproducible, setReproducible] = useState(false);
    const [showSimulation, setShowSimulation] = useState(false);
    const [simAccuracy, setSimAccuracy] = useState<number | ''>('');
    const [simLatency, setSimLatency] = useState<number | ''>('');
    const [simMemory, setSimMemory] = useState<number | ''>('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const navigate = useNavigate();

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!file) {
            setError('Please select a model file');
            return;
        }

        setIsSubmitting(true);

        try {
            const config: CreateJobRequest = {
                compilation_policy: policy,
                build_mode: reproducible ? 'reproducible' : 'normal',
            };

            if (simAccuracy !== '') {
                config.simulate_accuracy_drop = Number(simAccuracy) / 100;
            }
            if (simLatency !== '') {
                config.simulate_latency_spike = Number(simLatency);
            }
            if (simMemory !== '') {
                config.simulate_memory_exceed = Number(simMemory);
            }

            const job = await jobsApi.create(file, config);
            navigate(`/jobs/${job.job_id}`);
        } catch {
            setError('Failed to create job. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-900">
            <Navbar />

            <main className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <h1 className="text-3xl font-bold text-white mb-8">New Compilation Job</h1>

                <form onSubmit={handleSubmit} className="space-y-6">
                    {error && (
                        <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg">
                            {error}
                        </div>
                    )}

                    {/* File Upload */}
                    <div className="card">
                        <h2 className="text-lg font-semibold text-white mb-4">Model File</h2>

                        <div
                            onClick={() => fileInputRef.current?.click()}
                            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${file
                                ? 'border-green-500 bg-green-900/20'
                                : 'border-gray-600 hover:border-indigo-500'
                                }`}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".onnx,.pt,.pth,.h5,.pb,.tflite"
                                onChange={handleFileChange}
                                className="hidden"
                            />

                            {file ? (
                                <div>
                                    <div className="text-green-400 mb-2">✓ File selected</div>
                                    <div className="text-white font-medium">{file.name}</div>
                                    <div className="text-gray-400 text-sm">
                                        {(file.size / 1024 / 1024).toFixed(2)} MB
                                    </div>
                                </div>
                            ) : (
                                <div>
                                    <div className="text-gray-400 mb-2">
                                        Drag and drop or click to upload
                                    </div>
                                    <div className="text-gray-500 text-sm">
                                        Supports: .onnx, .pt, .pth, .h5, .pb, .tflite
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Compilation Policy */}
                    <div className="card">
                        <h2 className="text-lg font-semibold text-white mb-4">Compilation Policy</h2>

                        <div className="grid grid-cols-2 gap-3">
                            {[
                                { value: 'balanced', label: 'Balanced', desc: 'Best overall' },
                                { value: 'accuracy_first', label: 'Accuracy First', desc: 'Max accuracy' },
                                { value: 'latency_first', label: 'Latency First', desc: 'Fastest inference' },
                                { value: 'mobile_first', label: 'Mobile First', desc: 'Smallest size' },
                            ].map((option) => (
                                <button
                                    key={option.value}
                                    type="button"
                                    onClick={() => setPolicy(option.value as Policy)}
                                    className={`p-4 rounded-lg border-2 text-left transition-colors ${policy === option.value
                                        ? 'border-indigo-500 bg-indigo-900/30'
                                        : 'border-gray-600 hover:border-gray-500'
                                        }`}
                                >
                                    <div className="text-white font-medium">{option.label}</div>
                                    <div className="text-gray-400 text-sm">{option.desc}</div>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Options */}
                    <div className="card">
                        <h2 className="text-lg font-semibold text-white mb-4">Options</h2>

                        <label className="flex items-center gap-3 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={reproducible}
                                onChange={(e) => setReproducible(e.target.checked)}
                                className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-indigo-500 focus:ring-indigo-500"
                            />
                            <div>
                                <div className="text-white">Reproducible Build</div>
                                <div className="text-gray-400 text-sm">
                                    Deterministic compilation with fixed seeds
                                </div>
                            </div>
                        </label>
                    </div>

                    {/* Simulation (Demo Only) */}
                    <div className="card">
                        <button
                            type="button"
                            onClick={() => setShowSimulation(!showSimulation)}
                            className="flex items-center justify-between w-full text-left"
                        >
                            <div>
                                <div className="text-lg font-semibold text-white">Failure Simulation</div>
                                <div className="text-gray-400 text-sm">Demo only - inject test failures</div>
                            </div>
                            <span className="text-gray-400">{showSimulation ? '▼' : '▶'}</span>
                        </button>

                        {showSimulation && (
                            <div className="mt-4 space-y-4 pt-4 border-t border-gray-700">
                                <div>
                                    <label className="block text-sm text-gray-300 mb-1">
                                        Accuracy Drop (%)
                                    </label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="100"
                                        step="0.1"
                                        value={simAccuracy}
                                        onChange={(e) => setSimAccuracy(e.target.value ? Number(e.target.value) : '')}
                                        className="input w-full"
                                        placeholder="e.g., 5 for 5% drop"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-gray-300 mb-1">
                                        Latency Multiplier
                                    </label>
                                    <input
                                        type="number"
                                        min="1"
                                        step="0.1"
                                        value={simLatency}
                                        onChange={(e) => setSimLatency(e.target.value ? Number(e.target.value) : '')}
                                        className="input w-full"
                                        placeholder="e.g., 2 for 2x latency"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-gray-300 mb-1">
                                        Memory Override (MB)
                                    </label>
                                    <input
                                        type="number"
                                        min="0"
                                        value={simMemory}
                                        onChange={(e) => setSimMemory(e.target.value ? Number(e.target.value) : '')}
                                        className="input w-full"
                                        placeholder="e.g., 10000 for 10GB"
                                    />
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Submit */}
                    <button
                        type="submit"
                        disabled={isSubmitting || !file}
                        className="btn-primary w-full py-3 text-lg disabled:opacity-50"
                    >
                        {isSubmitting ? 'Creating Job...' : 'Start Compilation'}
                    </button>
                </form>
            </main>
        </div>
    );
};
