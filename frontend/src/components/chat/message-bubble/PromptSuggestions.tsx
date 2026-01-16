import { memo } from 'react';
import { Lightbulb } from 'lucide-react';

interface PromptSuggestionsProps {
  suggestions: string[];
  onSelect: (suggestion: string) => void;
}

const PromptSuggestionsInner: React.FC<PromptSuggestionsProps> = ({ suggestions, onSelect }) => {
  if (!suggestions || suggestions.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 flex flex-col gap-2.5">
      <div className="flex items-center gap-1.5 text-xs font-medium text-text-tertiary dark:text-text-dark-tertiary">
        <Lightbulb className="h-3.5 w-3.5 text-brand-500 dark:text-brand-400" />
        <span>Suggested follow-ups</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            type="button"
            onClick={() => onSelect(suggestion)}
            className="rounded-lg border border-border bg-surface-secondary px-3 py-2 text-left text-sm text-text-secondary transition-all duration-200 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:ring-offset-1 dark:border-border-dark dark:bg-surface-dark-secondary dark:text-text-dark-secondary dark:hover:border-brand-500/50 dark:hover:bg-brand-500/10 dark:hover:text-brand-300 dark:focus:ring-offset-surface-dark"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
};

export const PromptSuggestions = memo(PromptSuggestionsInner);
