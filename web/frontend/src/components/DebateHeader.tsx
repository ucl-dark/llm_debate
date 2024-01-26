import {
  Question,
  TranscriptAnswers,
  TranscriptConfig,
  TranscriptNames,
} from "../utils/types";

interface AnswerLineProps {
  name?: string;
  answer: string;
  isCorrect: boolean;
  hideAnswers: boolean;
  label: string;
}

function AnswerLine({
  name,
  answer,
  isCorrect,
  hideAnswers,
  label,
}: AnswerLineProps) {
  const icon = isCorrect ? "✅ " : "❌ ";

  return (
    <div>
      {!hideAnswers && <span className="mr-2">{icon} </span>}
      <span className="font-bold">{`${label}: `}</span>
      {`${answer} `}
      <span className="font-bold italic">{name ? <>({name})</> : null}</span>
    </div>
  );
}

interface DebateHeaderProps {
  question: string;
  answers: TranscriptAnswers;
  names: TranscriptNames;
  swap: boolean;
  hideAnswers: boolean;
}

export default function DebateHeader({
  question,
  answers,
  names,
  swap,
  hideAnswers,
}: DebateHeaderProps) {
  const correct = (
    <AnswerLine
      name={names.correct}
      answer={answers.correct}
      isCorrect={true}
      hideAnswers={hideAnswers}
      label={swap ? "B" : "A"}
    />
  );
  const incorrect = (
    <AnswerLine
      name={names.incorrect}
      answer={answers.incorrect}
      isCorrect={false}
      hideAnswers={hideAnswers}
      label={swap ? "A" : "B"}
    />
  );
  return (
    <div className="w-full p-4 flex-col justify-start ">
      <div className="font-bold">
        <span className="">Question: </span>
        {question}
      </div>
      {swap ? incorrect : correct}
      {swap ? correct : incorrect}
    </div>
  );
}
