import { SecretsView as SecretsComponent } from '../sandbox/secrets/SecretsView';

interface SecretsViewProps {
  chatId?: string;
  sandboxId?: string;
}

export function SecretsView({ chatId, sandboxId }: SecretsViewProps) {
  return (
    <div className="h-full w-full">
      <SecretsComponent chatId={chatId} sandboxId={sandboxId} />
    </div>
  );
}
