import { Container } from './Container';
import type { Chat } from '@/types';

interface TerminalPanelProps {
  currentChat?: Chat | null;
  isVisible: boolean;
}

export function TerminalPanel({ currentChat, isVisible }: TerminalPanelProps) {
  return (
    <Container sandboxId={currentChat?.sandbox_id} chatId={currentChat?.id} isVisible={isVisible} />
  );
}
