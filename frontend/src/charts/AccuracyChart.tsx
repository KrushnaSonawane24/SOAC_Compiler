/**
 * Accuracy Chart Component
 */

import React from 'react';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
    ReferenceLine,
} from 'recharts';

interface AccuracyChartProps {
    data: { name: string; accuracy: number; threshold?: number }[];
    threshold?: number;
}

export const AccuracyChart: React.FC<AccuracyChartProps> = ({ data, threshold = 0.98 }) => {
    return (
        <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="name" stroke="#9CA3AF" />
                    <YAxis
                        stroke="#9CA3AF"
                        domain={[0.9, 1]}
                        tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                        labelStyle={{ color: '#F9FAFB' }}
                        formatter={(value) => [`${((value as number) * 100).toFixed(2)}%`, 'Accuracy']}
                    />
                    <ReferenceLine
                        y={threshold}
                        stroke="#EF4444"
                        strokeDasharray="5 5"
                        label={{ value: 'Threshold', fill: '#EF4444', fontSize: 12 }}
                    />
                    <Bar dataKey="accuracy" radius={[4, 4, 0, 0]}>
                        {data.map((entry, index) => (
                            <Cell
                                key={`cell-${index}`}
                                fill={entry.accuracy >= threshold ? '#10B981' : '#EF4444'}
                            />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
};
