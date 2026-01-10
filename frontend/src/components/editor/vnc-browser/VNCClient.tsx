import { memo, useRef, useCallback } from 'react';
import { VncScreen, VncScreenHandle } from 'react-vnc';

interface VNCClientProps {
  wsUrl: string | null;
  isActive: boolean;
  instanceKey?: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: string) => void;
}

export const VNCClient = memo(function VNCClient({
  wsUrl,
  isActive,
  instanceKey,
  onConnect,
  onDisconnect,
  onError,
}: VNCClientProps) {
  const vncRef = useRef<VncScreenHandle>(null);

  const handleConnect = useCallback(() => {
    onConnect?.();
  }, [onConnect]);

  const handleDisconnect = useCallback(() => {
    onDisconnect?.();
  }, [onDisconnect]);

  const handleSecurityFailure = useCallback(() => {
    onError?.('Security failure');
  }, [onError]);

  if (!isActive || !wsUrl) {
    return <div className="h-full w-full bg-surface-secondary dark:bg-surface-dark-secondary" />;
  }

  return (
    <div className="flex h-full min-h-0 w-full min-w-0 items-center justify-center">
      <VncScreen
        key={`${instanceKey ?? 0}-${wsUrl}`}
        ref={vncRef}
        url={wsUrl}
        scaleViewport
        clipViewport
        resizeSession
        className="vnc-screen h-full w-full"
        style={{ width: '100%', height: '100%' }}
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
        onSecurityFailure={handleSecurityFailure}
      />
    </div>
  );
});
