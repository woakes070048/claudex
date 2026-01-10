import { memo, useState, useCallback } from 'react';
import { Globe, RotateCcw, Play, Square } from 'lucide-react';
import { Button, Spinner } from '@/components/ui';
import { VNCClient } from '@/components/editor/vnc-browser/VNCClient';
import {
  useVNCUrlQuery,
  useBrowserStatusQuery,
  useStartBrowserMutation,
  useStopBrowserMutation,
} from '@/hooks/queries';

const DEFAULT_BROWSER_URL = 'https://www.google.com';

interface BrowserViewProps {
  sandboxId?: string;
  isActive?: boolean;
}

export const BrowserView = memo(function BrowserView({
  sandboxId,
  isActive = false,
}: BrowserViewProps) {
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [vncInstanceKey, setVncInstanceKey] = useState(0);
  const [browserUrl, setBrowserUrl] = useState(DEFAULT_BROWSER_URL);

  const {
    data: vncUrl,
    refetch: refetchVncUrl,
    isFetching: isFetchingUrl,
  } = useVNCUrlQuery(sandboxId || '', { enabled: !!sandboxId && isActive });

  const { data: browserStatus } = useBrowserStatusQuery(sandboxId || '', {
    enabled: !!sandboxId && isActive,
  });

  const startBrowserMutation = useStartBrowserMutation();
  const stopBrowserMutation = useStopBrowserMutation();

  const handleStartBrowser = useCallback(() => {
    if (sandboxId) {
      setIsConnecting(true);
      startBrowserMutation.mutate(
        {
          sandboxId,
          url: browserUrl,
        },
        {
          onSuccess: () => {
            setTimeout(() => refetchVncUrl(), 2000);
          },
          onError: () => {
            setIsConnecting(false);
          },
        },
      );
    }
  }, [sandboxId, startBrowserMutation, refetchVncUrl, browserUrl]);

  const handleStopBrowser = useCallback(() => {
    if (sandboxId) {
      stopBrowserMutation.mutate({ sandboxId });
    }
  }, [sandboxId, stopBrowserMutation]);

  const handleConnect = useCallback(() => {
    setIsConnecting(false);
    setConnectionError(null);
  }, []);

  const handleDisconnect = useCallback(() => {
    setIsConnecting(false);
  }, []);

  const handleError = useCallback((error: string) => {
    setConnectionError(error);
    setIsConnecting(false);
  }, []);

  const handleReconnect = useCallback(() => {
    setIsConnecting(true);
    setConnectionError(null);
    setVncInstanceKey((prev) => prev + 1);
    refetchVncUrl();
  }, [refetchVncUrl]);

  const isBrowserRunning = browserStatus?.running;

  if (!sandboxId) {
    return (
      <div className="flex h-full items-center justify-center text-xs text-text-tertiary dark:text-text-dark-tertiary">
        No sandbox connected
      </div>
    );
  }

  if (!isActive) {
    return null;
  }

  return (
    <div className="flex h-full min-h-0 w-full min-w-0 flex-col bg-surface-secondary dark:bg-surface-dark-secondary">
      <div className="flex items-center border-b border-border px-3 py-1.5 dark:border-white/10">
        <div className="flex flex-1 items-center gap-3">
          <Button
            onClick={handleReconnect}
            variant="unstyled"
            className="rounded-md bg-transparent p-1 text-text-tertiary transition-all hover:bg-surface-hover hover:text-text-primary dark:text-text-dark-tertiary dark:hover:bg-surface-dark-hover dark:hover:text-text-dark-primary"
            title="Reconnect"
          >
            <RotateCcw className={`h-3.5 w-3.5 ${isFetchingUrl ? 'animate-spin' : ''}`} />
          </Button>

          <Globe className="h-4 w-4 text-text-secondary dark:text-text-dark-secondary" />

          <span className="text-xs font-medium text-text-secondary dark:text-text-dark-secondary">
            Browser (VNC)
          </span>

          <div className="flex-1" />

          {isBrowserRunning && (
            <Button
              onClick={handleStopBrowser}
              variant="unstyled"
              disabled={stopBrowserMutation.isPending}
              className="flex items-center gap-1 rounded-md bg-red-500 px-2 py-1 text-xs text-white transition-all hover:bg-red-600 disabled:opacity-50"
              title="Stop browser"
            >
              <Square className="h-3 w-3" />
              Stop
            </Button>
          )}
        </div>
      </div>

      <div className="relative min-h-0 min-w-0 flex-1 overflow-hidden">
        {isConnecting && isBrowserRunning && !connectionError && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-white/50 dark:bg-black/50">
            <Spinner size="md" className="h-6 w-6 text-brand-500" />
            <span className="text-xs text-text-tertiary dark:text-text-dark-tertiary">
              Connecting to browser...
            </span>
          </div>
        )}

        {connectionError && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-white/50 dark:bg-black/50">
            <span className="text-xs text-red-500">{connectionError}</span>
            <Button
              onClick={handleReconnect}
              variant="unstyled"
              className="rounded-md bg-brand-500 px-3 py-1 text-xs text-white hover:bg-brand-600"
            >
              Retry
            </Button>
          </div>
        )}

        {!isBrowserRunning && !isConnecting && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 bg-surface-secondary dark:bg-surface-dark-secondary">
            <Globe className="h-12 w-12 text-text-tertiary dark:text-text-dark-tertiary" />
            <div className="flex flex-col items-center gap-1">
              <span className="text-sm font-medium text-text-secondary dark:text-text-dark-secondary">
                Start a browser session
              </span>
              <span className="text-xs text-text-tertiary dark:text-text-dark-tertiary">
                Enter a URL to browse
              </span>
            </div>
            <input
              type="text"
              value={browserUrl}
              onChange={(e) => setBrowserUrl(e.target.value)}
              placeholder="https://example.com"
              className="bg-surface-primary dark:bg-surface-dark-primary w-80 rounded-md border border-border px-3 py-2 text-sm text-text-primary outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-white/10 dark:text-text-dark-primary dark:focus:border-brand-400 dark:focus:ring-brand-400"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !startBrowserMutation.isPending) {
                  handleStartBrowser();
                }
              }}
            />
            <Button
              onClick={handleStartBrowser}
              variant="unstyled"
              disabled={startBrowserMutation.isPending}
              className="flex items-center gap-2 rounded-md bg-brand-500 px-4 py-2 text-sm text-white transition-all hover:bg-brand-600 disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              Start Browser
            </Button>
          </div>
        )}

        <VNCClient
          wsUrl={vncUrl ?? null}
          isActive={isActive && !!vncUrl && !!isBrowserRunning}
          instanceKey={vncInstanceKey}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          onError={handleError}
        />
      </div>
    </div>
  );
});
