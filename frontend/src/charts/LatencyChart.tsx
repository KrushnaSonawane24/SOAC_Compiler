/**
 * Latency Chart Component
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
} from 'recharts';

interface LatencyChartProps {
    data: { name: string; latency: number; selected?: boolean }[];
}

export const LatencyChart: React.FC<LatencyChartProps> = ({ data }) => {
    return (
        <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="name" stroke="#9CA3AF" />
                    <YAxis stroke="#9CA3AF" label={{ value: 'ms', position: 'insideLeft', fill: '#9CA3AF' }} />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                        labelStyle={{ color: '#F9FAFB' }}
                    />
                    <Bar dataKey="latency" radius={[4, 4, 0, 0]}>
                        {data.map((entry, index) => (
                            <Cell
                                key={`cell-${index}`}
                                fill={entry.selected ? '#10B981' : '#6366F1'}
                            />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
};
