/**
 * Latency Chart Component
 */

import React from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';

interface LatencyChartProps {
    data: { name: string; latency: number; selected?: boolean }[];
}

export const LatencyChart: React.FC<LatencyChartProps> = ({ data }) => {
    return (
        <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(224, 224, 224, 0.14)" />
                    <XAxis dataKey="name" stroke="rgba(224, 224, 224, 0.62)" />
                    <YAxis stroke="rgba(224, 224, 224, 0.62)" label={{ value: 'ms', position: 'insideLeft', fill: 'rgba(224, 224, 224, 0.62)' }} />
                    <Tooltip
                        contentStyle={{ backgroundColor: 'rgba(5, 5, 5, 0.92)', border: '1px solid rgba(224, 224, 224, 0.18)' }}
                        labelStyle={{ color: 'rgba(224, 224, 224, 0.96)' }}
                    />
                    <Line
                        type="monotone"
                        dataKey="latency"
                        stroke="var(--soac-primary)"
                        strokeWidth={2.5}
                        dot={(props) => {
                            const payload = props.payload as { selected?: boolean } | undefined;
                            const isSelected = Boolean(payload?.selected);
                            return (
                                <circle
                                    cx={props.cx}
                                    cy={props.cy}
                                    r={isSelected ? 4.5 : 3}
                                    fill={isSelected ? 'var(--soac-primary)' : 'rgba(224, 224, 224, 0.38)'}
                                    stroke="rgba(0, 0, 0, 0.65)"
                                    strokeWidth={isSelected ? 1.25 : 1}
                                />
                            );
                        }}
                        activeDot={{ r: 5, fill: 'var(--soac-primary)', stroke: 'rgba(0, 0, 0, 0.65)', strokeWidth: 1.25 }}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
};
