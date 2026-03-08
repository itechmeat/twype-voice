type InterimTranscriptProps = {
  text: string | null;
};

export function InterimTranscript({ text }: InterimTranscriptProps) {
  if (text === null || text.trim().length === 0) {
    return null;
  }

  return (
    <p className="chat-feed__interim" role="status">
      Listening: {text}
    </p>
  );
}
