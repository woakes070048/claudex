import { memo, useState, useEffect, useCallback } from 'react';
import { logger } from '@/utils/logger';
import { PlusCircle, Trash2, SaveAll, EyeOff, Eye, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  useSecretsQuery,
  useAddSecretMutation,
  useUpdateSecretMutation,
  useDeleteSecretMutation,
} from '@/hooks/queries';
import { Button, Input, Spinner } from '@/components/ui';
import type { Secret } from '@/types';
import toast from 'react-hot-toast';

export interface SecretsViewProps {
  chatId?: string;
  sandboxId?: string;
}

const baseButtonClasses = 'flex items-center gap-1 px-2.5 py-1 text-xs rounded-md';
const disabledButtonClasses =
  'opacity-50 cursor-not-allowed bg-surface-secondary dark:bg-surface-dark-secondary text-text-quaternary';
const enabledButtonClasses =
  'bg-surface-secondary dark:bg-surface-dark-secondary hover:bg-surface-hover dark:hover:bg-surface-dark-hover text-text-secondary dark:text-text-dark-secondary';
const inputClasses =
  'w-full px-2 py-1 text-xs bg-surface-tertiary dark:bg-surface-dark-tertiary border border-border dark:border-border-dark rounded-md';

export const SecretsView = memo(function SecretsView({ sandboxId }: SecretsViewProps) {
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [showValues, setShowValues] = useState<Record<string, boolean>>({});

  const {
    data: secretsData = [],
    isLoading,
    refetch: refetchSecrets,
  } = useSecretsQuery(sandboxId || '');
  const addSecretMutation = useAddSecretMutation();
  const updateSecretMutation = useUpdateSecretMutation();
  const deleteSecretMutation = useDeleteSecretMutation();

  const hasChanges = secrets.some(
    (secret) => secret.isNew || secret.isModified || secret.isDeleted,
  );

  const hasEmptyKeys = secrets.some((secret) => !secret.isDeleted && secret.key.trim() === '');

  useEffect(() => {
    const secretsWithOriginals = secretsData.map((secret) => ({
      ...secret,
      originalKey: secret.key,
      originalValue: secret.value,
      isNew: false,
      isModified: false,
      isDeleted: false,
    }));
    setSecrets(secretsWithOriginals);
  }, [secretsData]);

  const loadEnvironmentVariables = useCallback(() => {
    refetchSecrets();
  }, [refetchSecrets]);

  const handleAddSecret = () => {
    if (hasEmptyKeys) {
      toast.error('Please fill in all empty keys before adding a new variable');
      return;
    }

    setSecrets((current) => [...current, { key: '', value: '', isNew: true }]);
  };

  const handleRemoveSecret = async (index: number) => {
    const targetSecret = secrets[index];

    if (!targetSecret) {
      return;
    }

    if (targetSecret.isNew) {
      setSecrets((current) => current.filter((_, itemIndex) => itemIndex !== index));
      return;
    }

    if (!sandboxId || !targetSecret.originalKey) {
      return;
    }

    try {
      await deleteSecretMutation.mutateAsync({ sandboxId, key: targetSecret.originalKey });
      setSecrets((current) =>
        current.filter((secret) => secret.originalKey !== targetSecret.originalKey),
      );
      toast.success('Environment variable deleted successfully');
    } catch (error) {
      logger.error('Environment variable delete failed', 'SecretsView', error);
      toast.error('Failed to delete environment variable');
    }
  };

  const handleUpdateSecret = (index: number, field: 'key' | 'value', value: string) => {
    setSecrets((currentSecrets) => {
      if (index < 0 || index >= currentSecrets.length) {
        return currentSecrets;
      }

      const existingSecret = currentSecrets[index];
      const updatedSecret = { ...existingSecret, [field]: value };

      if (!existingSecret.isNew && !existingSecret.isDeleted) {
        const updatedKey = field === 'key' ? value : updatedSecret.key;
        const updatedValue = field === 'value' ? value : updatedSecret.value;
        const keyChanged = updatedKey !== existingSecret.originalKey;
        const valueChanged = updatedValue !== existingSecret.originalValue;
        updatedSecret.isModified = keyChanged || valueChanged;
      }

      const nextSecrets = [...currentSecrets];
      nextSecrets[index] = updatedSecret;
      return nextSecrets;
    });
  };

  const toggleShowValue = (index: number) => {
    setShowValues((current) => ({
      ...current,
      [index]: !current[index],
    }));
  };

  const handleSaveSecrets = async () => {
    if (!sandboxId) {
      toast.error('No sandbox available');
      return;
    }

    setIsSaving(true);

    try {
      const activeSecrets = secrets.filter(
        (secret) => !secret.isDeleted && secret.key.trim() !== '',
      );

      if (activeSecrets.length === 0) {
        setIsSaving(false);
        return;
      }

      for (const secret of activeSecrets) {
        if (secret.isNew) {
          await addSecretMutation.mutateAsync({ sandboxId, key: secret.key, value: secret.value });
        } else if (secret.isModified && secret.originalKey) {
          if (secret.key !== secret.originalKey) {
            await deleteSecretMutation.mutateAsync({ sandboxId, key: secret.originalKey });
            await addSecretMutation.mutateAsync({
              sandboxId,
              key: secret.key,
              value: secret.value,
            });
          } else {
            await updateSecretMutation.mutateAsync({
              sandboxId,
              key: secret.originalKey,
              value: secret.value,
            });
          }
        }
      }

      toast.success('Environment variables saved successfully');
    } catch (error) {
      logger.error('Environment variables save failed', 'SecretsView', error);
      toast.error('Failed to save environment variables');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex h-full flex-col p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium">Environment Variables</h2>
        <div className="flex items-center gap-2">
          <Button
            onClick={loadEnvironmentVariables}
            disabled={isLoading || !sandboxId}
            title="Refresh environment variables"
            variant="unstyled"
            className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs transition-colors ${
              !sandboxId || isLoading ? disabledButtonClasses : enabledButtonClasses
            }`}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
          <Button
            onClick={handleSaveSecrets}
            disabled={isSaving || !sandboxId || !hasChanges}
            variant="unstyled"
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs transition-colors ${
              !sandboxId || !hasChanges
                ? disabledButtonClasses
                : 'bg-brand-500 text-white hover:bg-brand-600'
            }`}
          >
            <SaveAll className="h-3.5 w-3.5" />
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>

      {!sandboxId && (
        <div className="mb-3 flex items-center gap-2 rounded-md bg-warning-50 p-3 text-xs text-warning-600 dark:bg-warning-500/10 dark:text-warning-400">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <p>No sandbox is connected. You need an active sandbox to use environment variables.</p>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex h-40 items-center justify-center">
            <Spinner size="md" className="text-brand-500" />
          </div>
        )}

        {!isLoading && secrets.length === 0 ? (
          <div className="flex h-40 flex-col items-center justify-center text-text-tertiary dark:text-text-dark-tertiary">
            <p className="mb-3 text-sm">No environment variables added yet</p>
            <Button
              onClick={handleAddSecret}
              disabled={!sandboxId}
              variant="unstyled"
              className={`${baseButtonClasses} ${
                !sandboxId ? disabledButtonClasses : enabledButtonClasses
              }`}
            >
              <PlusCircle className="h-3.5 w-3.5" />
              Add Variable
            </Button>
          </div>
        ) : (
          !isLoading && (
            <div className="space-y-2">
              {secrets.map(
                (secret, index) =>
                  !secret.isDeleted && (
                    <div
                      key={index}
                      className={`flex items-center gap-2 rounded-md border p-2 ${
                        secret.isNew
                          ? 'border-brand-200 bg-brand-50/50 dark:border-brand-800 dark:bg-brand-500/5'
                          : secret.isModified
                            ? 'border-warning-200 bg-warning-50/50 dark:border-warning-800 dark:bg-warning-500/5'
                            : 'border-border dark:border-border-dark'
                      }`}
                    >
                      <div className="grid flex-1 grid-cols-2 gap-2">
                        <Input
                          type="text"
                          value={secret.key}
                          onChange={(e) => handleUpdateSecret(index, 'key', e.target.value)}
                          placeholder="KEY"
                          className={inputClasses}
                          variant="unstyled"
                        />
                        <div className="relative">
                          <Input
                            type={showValues[index] ? 'text' : 'password'}
                            value={secret.value}
                            onChange={(e) => handleUpdateSecret(index, 'value', e.target.value)}
                            placeholder="VALUE"
                            className={`${inputClasses} pr-7`}
                            variant="unstyled"
                          />
                          <Button
                            onClick={() => toggleShowValue(index)}
                            variant="unstyled"
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-text-quaternary hover:text-text-secondary dark:hover:text-text-dark-secondary"
                          >
                            {showValues[index] ? (
                              <EyeOff className="h-3.5 w-3.5" />
                            ) : (
                              <Eye className="h-3.5 w-3.5" />
                            )}
                          </Button>
                        </div>
                      </div>
                      <Button
                        onClick={() => handleRemoveSecret(index)}
                        variant="unstyled"
                        className="rounded-md p-1 text-text-quaternary transition-colors hover:bg-surface-hover hover:text-error-600 dark:hover:bg-surface-dark-hover dark:hover:text-error-400"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ),
              )}

              <div className="pt-2">
                <Button
                  onClick={handleAddSecret}
                  disabled={!sandboxId}
                  variant="unstyled"
                  className={`${baseButtonClasses} ${
                    !sandboxId ? disabledButtonClasses : enabledButtonClasses
                  }`}
                >
                  <PlusCircle className="h-3.5 w-3.5" />
                  Add Variable
                </Button>
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
});
