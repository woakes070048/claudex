import { WebPreview } from '../sandbox/web-preview/Preview';

interface WebPreviewViewProps {
  sandboxId?: string;
  isActive?: boolean;
}

export function WebPreviewView({ sandboxId, isActive = false }: WebPreviewViewProps) {
  return (
    <div className="h-full w-full">
      <WebPreview sandboxId={sandboxId} isActive={isActive} />
    </div>
  );
}
