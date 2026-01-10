import { useContext } from 'react';
import { ChatContext } from '@/contexts/ChatContextDefinition';

export function useChatContext() {
  const context = useContext(ChatContext);
  return (
    context ?? {
      chatId: undefined,
      sandboxId: undefined,
      fileStructure: [],
      customAgents: [],
      customSlashCommands: [],
    }
  );
}
