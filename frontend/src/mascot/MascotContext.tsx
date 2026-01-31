import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

export type MascotMode = 'idle' | 'thinking' | 'benchmarking' | 'success' | 'failure';

type MascotState = {
    mode: MascotMode;
    message?: string;
};

type MascotContextValue = {
    state: MascotState;
    setState: (next: MascotState) => void;
    muted: boolean;
    toggleMuted: () => void;
};

const MascotContext = createContext<MascotContextValue | null>(null);

const STORAGE_KEY = 'soac-mascot-muted';

export const MascotProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
    const [state, setStateInner] = useState<MascotState>({ mode: 'idle' });
    const [muted, setMuted] = useState<boolean>(() => localStorage.getItem(STORAGE_KEY) === '1');
    const timerRef = useRef<number | null>(null);

    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, muted ? '1' : '0');
    }, [muted]);

    const setState = useCallback((next: MascotState) => {
        if (timerRef.current) window.clearTimeout(timerRef.current);
        timerRef.current = window.setTimeout(() => {
            setStateInner(next);
        }, 240);
    }, []);

    const toggleMuted = useCallback(() => {
        setMuted((m) => !m);
    }, []);

    const value = useMemo<MascotContextValue>(() => ({ state, setState, muted, toggleMuted }), [state, setState, muted, toggleMuted]);

    return <MascotContext.Provider value={value}>{children}</MascotContext.Provider>;
};

export function useMascot(): MascotContextValue {
    const value = useContext(MascotContext);
    if (!value) throw new Error('useMascot must be used within MascotProvider');
    return value;
}
