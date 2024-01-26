import {
  TranscriptNames,
  TranscriptRound,
} from "../utils/types";

const processContent = (content) => {
  const segments = [];
  const quoteTypes = { "u_quote": "</u_quote>", "v_quote": "</v_quote>" };
  let lastIndex = 0;
  let currentTag = null;
  let currentTagStartIndex = -1;

  for (let i = 0; i < content.length; i++) {
    if (content[i] === '<') {
      // Check for end tag
      if (currentTag && content.substring(i, i + currentTag.length + 3) === quoteTypes[currentTag]) {
        // Add the quote segment
        segments.push({ type: currentTag, content: content.substring(currentTagStartIndex, i) });
        i += currentTag.length + 2; // Move past the end tag
        currentTag = null;
        lastIndex = i + 1;
        continue;
      }

      // Check for start tag
      for (const [type, endTag] of Object.entries(quoteTypes)) {
        if (content.substring(i, i + type.length + 2) === `<${type}>`) {
          if (lastIndex < i) {
            segments.push({ type: "text", content: content.substring(lastIndex, i) });
          }
          currentTag = type;
          currentTagStartIndex = i + type.length + 2;
          i += type.length + 1; // Move past the start tag
          break;
        }
      }
    }
  }

  // Add the remaining content as a text segment if there's any
  if (lastIndex < content.length) {
    segments.push({ type: "text", content: content.substring(lastIndex) });
  }

  return segments;
};

function HighlightedContent({ content }: { content: string }) {
  const processedContent = processContent(content);

  return (
    <div>
      {processedContent.map((part, index) => {
        let className = '';
        if (part.type === 'u_quote') {
          className = 'bg-yellow-300'; // yellow for u_quote
        } else if (part.type === 'v_quote') {
          className = 'bg-green-300'; // green for v_quote
        }
        return (
          <span key={index} className={className}>
            {part.content}
          </span>
        );
      })}
    </div>
  );
}

function ChatRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex w-full  items-stretch justify-between gap-2">
      {children}
    </div>
  );
}

interface ChatBubbleProps {
  name: string;
  content: string;
  accent?: string;
}
function ChatBubble({ name, content, accent = "" }: ChatBubbleProps) {
  return (
    <div
      className={`flex flex-col flex-grow bg-white rounded-lg ${accent}`}
      style={{ flexBasis: 0 }}
    >
      <div className="flex flex-col flex-grow py-3 px-4 whitespace-pre-wrap border border-gray-300 rounded-lg shadow-sm text-base">
        <div className="text-gray-600 mb-2 font-medium">{name}</div>
        <HighlightedContent content={content.trim()} />
      </div>
    </div>
  );
}

interface RoundProps {
  round: TranscriptRound;
  names: TranscriptNames;
  swap: boolean;
  hideAnswers: boolean;
}

function Round({ round, names, swap, hideAnswers }: RoundProps) {
  const errorMessage =
    round.error ? (
      <ChatBubble
        content={round.error}
        name="Error"
        accent={"border-l-4 border-red-500"}
      />
    ) : null;

  const correctMessage =
    round.correct && names.correct ? (
      <ChatBubble
        content={round.correct}
        name={names.correct}
        accent={hideAnswers ? undefined : "border-l-4 border-green-500"}
      />
    ) : null;

  const incorrectMessage =
    round.incorrect && names.incorrect ? (
      <ChatBubble
        content={round.incorrect}
        name={names.incorrect}
        accent={hideAnswers ? undefined : "border-l-4 border-red-500"}
      />
    ) : null;

  const judgeMessage =
    round.judge ? (
      <ChatBubble
        content={round.judge}
        name={names.judge ? `${names.judge} (Judge)` : 'Judge'}
        accent="border-l-4 border-blue-500"
      />
    ) : null;

  const crossExaminerMessage =
    round.cross_examiner && names.cross_examiner ? (
      <ChatBubble
        content={round.cross_examiner}
        name={names.cross_examiner}
        accent="border-l-4 border-blue-500"
      />
    ) : null;

  let debaterMessages;
  if (round.type === "seq") {
    debaterMessages = (
      <>
        <ChatRow>{swap ? incorrectMessage : correctMessage}</ChatRow>
        <ChatRow>{swap ? correctMessage : incorrectMessage}</ChatRow>
      </>
    );
  } else {
    debaterMessages = (
      <ChatRow>
        {swap ? incorrectMessage : correctMessage}
        {swap ? correctMessage : incorrectMessage}
      </ChatRow>
    );
  }
  return (
    <div className="flex flex-col p-2 gap-2 justify-between">
      {errorMessage && <ChatRow>{errorMessage}</ChatRow>}
      {judgeMessage && <ChatRow>{judgeMessage}</ChatRow>}
      {crossExaminerMessage && <ChatRow>{crossExaminerMessage}</ChatRow>}
      {debaterMessages}
    </div>
  );
}

interface TranscriptProps {
  rounds: TranscriptRound[]
  names: TranscriptNames
  swap: boolean
  hideAnswers: boolean;
}

export default function Transcript({
  rounds,
  names,
  swap,
  hideAnswers,
}: TranscriptProps) {
  if (rounds.length === 0) {
    return <div className="p-2">No rounds in transcript</div>;
  }
  return (
    <div className="flex flex-col flex-grow bg-gray-100">
      {rounds.map((round, i) => (
        <Round
          key={i}
          round={round}
          names={names}
          swap={swap}
          hideAnswers={hideAnswers}
        />
      ))}
    </div>
  );
}
