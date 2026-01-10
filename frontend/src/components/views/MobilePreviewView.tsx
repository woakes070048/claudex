import { MobilePreview } from '../sandbox/mobile-preview/MobilePreview';

interface MobilePreviewViewProps {
  sandboxId?: string;
}

export function MobilePreviewView({ sandboxId }: MobilePreviewViewProps) {
  return (
    <div className="h-full w-full">
      <MobilePreview sandboxId={sandboxId} />
    </div>
  );
}
