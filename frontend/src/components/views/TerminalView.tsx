import { TerminalPanel } from '../sandbox/terminal/TerminalPanel';
import type { Chat } from '@/types';

interface TerminalViewProps {
  currentChat?: Chat | null;
  isVisible: boolean;
}

export function TerminalView({ currentChat, isVisible }: TerminalViewProps) {
  return (
    <div className="h-full w-full">
      <TerminalPanel currentChat={currentChat} isVisible={isVisible} />
    </div>
  );
}
