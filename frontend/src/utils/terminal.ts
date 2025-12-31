import type { ITerminalOptions } from 'xterm';

export const buildTerminalTheme = (mode: 'light' | 'dark'): ITerminalOptions['theme'] => ({
  background: mode === 'dark' ? '#141414' : '#f9f9f9',
  foreground: mode === 'dark' ? '#e4e4e7' : '#27272a',
  cursor: mode === 'dark' ? '#e4e4e7' : '#27272a',
  cursorAccent: mode === 'dark' ? '#0a0a0a' : '#ffffff',
  selectionBackground: mode === 'dark' ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.15)',
  selectionInactiveBackground: mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.08)',
});

export const createTerminalOptions = (theme: ITerminalOptions['theme']): ITerminalOptions => ({
  scrollback: 1000,
  fontSize: 12,
  fontFamily: 'monospace',
  convertEol: true,
  theme,
});

export const getTerminalBackgroundClass = (mode: 'light' | 'dark'): string =>
  mode === 'dark' ? 'bg-surface-dark-secondary' : 'bg-surface-secondary';
