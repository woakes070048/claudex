import { useCallback } from 'react';
import { useUIStore } from '@/store';
import type * as monaco from 'monaco-editor';

const LIGHT_THEME: monaco.editor.IStandaloneThemeData = {
  base: 'vs',
  inherit: true,
  rules: [
    { token: '', foreground: '333333', background: '#f9f9f9' },
    { token: 'comment', foreground: '6A737D', fontStyle: 'italic' },
    { token: 'keyword', foreground: 'D73A49' },
    { token: 'string', foreground: '032F62' },
    { token: 'number', foreground: '005CC5' },
    { token: 'type', foreground: '6F42C1' },
    { token: 'variable', foreground: '24292E' },
    { token: 'function', foreground: '6F42C1' },
  ],
  colors: {
    'editor.background': '#f9f9f9',
    'editor.foreground': '#333333',
    'editorLineNumber.foreground': '#6E7781',
    'editorLineNumber.activeForeground': '#24292E',
    'editor.selectionBackground': '#ADD6FF',
    'editor.inactiveSelectionBackground': '#E5EBF1',
    'editorCursor.foreground': '#24292E',
    'editor.findMatchBackground': '#FFDF5D',
    'editor.findMatchHighlightBackground': '#FFDF5D80',
    'editorSuggestWidget.background': '#FFFFFF',
    'editorSuggestWidget.foreground': '#333333',
    'editorSuggestWidget.selectedBackground': '#E8E8E8',
    'editorWidget.background': '#FFFFFF',
    'editorWidget.border': '#E1E4E8',
  },
};

const DARK_THEME: monaco.editor.IStandaloneThemeData = {
  base: 'vs-dark',
  inherit: true,
  rules: [
    { token: '', foreground: 'BDBDBD', background: '#141414' },
    { token: 'comment', foreground: '7E7E7E', fontStyle: 'italic' },
    { token: 'keyword', foreground: '7895C6' },
    { token: 'string', foreground: 'C49B66' },
    { token: 'number', foreground: 'A5C186' },
    { token: 'type', foreground: '7EB0B0' },
    { token: 'variable', foreground: '8EACC3' },
    { token: 'function', foreground: 'C0B18C' },
  ],
  colors: {
    'editor.background': '#141414',
    'editor.foreground': '#BDBDBD',
    'editorLineNumber.foreground': '#959595',
    'editorLineNumber.activeForeground': '#B0B0B0',
    'editor.selectionBackground': '#333333',
    'editor.inactiveSelectionBackground': '#282828',
    'editorCursor.foreground': '#AEAEAE',
    'editor.findMatchBackground': '#363636',
    'editor.findMatchHighlightBackground': '#464646',
    'editorSuggestWidget.background': '#1B1B1B',
    'editorSuggestWidget.foreground': '#AEAEAE',
    'editorSuggestWidget.selectedBackground': '#282828',
    'editorWidget.background': '#1B1B1B',
    'editorWidget.border': '#363636',
  },
};

export function useEditorTheme() {
  const theme = useUIStore((state) => state.theme);

  const setupEditorTheme = useCallback(
    (monaco: typeof import('monaco-editor')) => {
      if (!monaco || !monaco.editor) return;

      monaco.editor.defineTheme('custom-light', LIGHT_THEME);
      monaco.editor.defineTheme('custom-dark', DARK_THEME);

      monaco.languages.typescript.typescriptDefaults.setCompilerOptions({
        target: monaco.languages.typescript.ScriptTarget.ES2020,
        module: monaco.languages.typescript.ModuleKind.ESNext,
        jsx: monaco.languages.typescript.JsxEmit.React,
        lib: ['es2020', 'dom'],
        strict: true,
        esModuleInterop: true,
        allowSyntheticDefaultImports: true,
        moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
      });

      monaco.languages.typescript.javascriptDefaults.setCompilerOptions({
        target: monaco.languages.typescript.ScriptTarget.ES2020,
        module: monaco.languages.typescript.ModuleKind.ESNext,
        jsx: monaco.languages.typescript.JsxEmit.React,
        lib: ['es2020', 'dom'],
        allowJs: true,
        checkJs: true,
        esModuleInterop: true,
        allowSyntheticDefaultImports: true,
      });

      monaco.editor.setTheme(theme === 'dark' ? 'custom-dark' : 'custom-light');
    },
    [theme],
  );

  return {
    currentTheme: theme === 'light' ? 'custom-light' : 'custom-dark',
    setupEditorTheme,
  };
}
