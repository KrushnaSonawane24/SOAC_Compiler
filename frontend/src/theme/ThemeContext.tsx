import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export type Theme = 'night' | 'day';

type ThemeContextValue = {
    theme: Theme;
    setTheme: (theme: Theme) => void;
    toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

const STORAGE_KEY = 'soac-theme';

function applyThemeToRoot(theme: Theme) {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme === 'day' ? 'light' : 'dark';
}

export const ThemeProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
    const [theme, setThemeState] = useState<Theme>(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved === 'day' || saved === 'night' ? saved : 'night';
    });

    useEffect(() => {
        applyThemeToRoot(theme);
        localStorage.setItem(STORAGE_KEY, theme);
    }, [theme]);

    const setTheme = useCallback((next: Theme) => {
        setThemeState(next);
    }, []);

    const toggleTheme = useCallback(() => {
        setThemeState((t) => (t === 'night' ? 'day' : 'night'));
    }, []);

    const value = useMemo<ThemeContextValue>(() => ({ theme, setTheme, toggleTheme }), [theme, setTheme, toggleTheme]);

    return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export function useTheme(): ThemeContextValue {
    const value = useContext(ThemeContext);
    if (!value) throw new Error('useTheme must be used within ThemeProvider');
    return value;
}
