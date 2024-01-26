import { Debate } from "../utils/types";
import { useRevalidator } from "react-router-dom";
import { useUser } from "../hooks/userProvider";
import Button from "./Button";
import Slider from "./Slider";
import { useState } from "react";
import { shouldShowFeedback } from "../utils/utils";
import { useDebateContext } from "../hooks/debateProvider";

interface JudgementFormProps {
  debate: Debate;
  confidenceCorrect: number;
  setConfidenceCorrect: (value: number) => void;
  isExplanationRequired: boolean;
  isCommitmentRequired: boolean;
}

function JudgementForm({
  debate,
  confidenceCorrect,
  setConfidenceCorrect,
  isExplanationRequired,
  isCommitmentRequired,
}: JudgementFormProps) {
  const { generatingTurn } = useDebateContext()
  const { swap } = debate.transcript;
  const revalidator = useRevalidator();
  const { user } = useUser();
  const [explanation, setExplanation] = useState("");
  const [error, setError] = useState<string | null>(null);

  const confidenceA = swap ? 100 - confidenceCorrect : confidenceCorrect;
  const confidenceB = swap ? confidenceCorrect : 100 - confidenceCorrect;

  const debateOwner = user && user.id === debate.user.id;

  const onChange = (e: number) => {
    if (swap) {
      setConfidenceCorrect(e);
    } else {
      setConfidenceCorrect(100 - e);
    }
  };

  const chooseWinner = async () => {
    if (isCommitmentRequired && confidenceCorrect === 50) {
      setError("50/50 splits are not allowed. Please choose which answer you think is more likely to be correct, even if you are uncertain.")
      return
    }
    if (isExplanationRequired && explanation.trim().length === 0) {
      setError("Please provide an explanation for your judgement.");
      return;
    }
    if (debate.transcript.rounds.length === 0) {
      setError("Must have at least one round to judge debate.");
      return;
    }
    if (generatingTurn) {
      setError("Cannot submit judgement while generating a new turn.")
      return
    }
    if (debate.min_turns && debate.transcript.rounds.length < debate.min_turns) {
      setError(`Please create another turn first. This debate requires that you use at least ${debate.min_turns} turns before submitting a judgement.`)
      return
    }
    try {
      const response = await fetch(`/api/debates/${debate.id}/judgements`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          confidence_correct: confidenceCorrect,
          user_name: user,
          explanation: explanation,
        }),
      });

      revalidator.revalidate();
      if (!response.ok) {
        throw new Error("An error occurred while choosing the winner.");
      }
    } catch (error) {
      console.error("Failed to choose the winner:", error);
    }
  };

  if (!debateOwner) {
    return (
      <div>
        <p> Waiting for {debate.user.full_name} to judge.</p>
      </div>
    );
  }
  return (
    <form className="flex flex-col">
      <Slider
        value={confidenceB}
        label="Confidence score:"
        onChange={onChange}
        min={5}
        max={95}
        step={5}
      />
      <div className="flex justify-between text-sm font-medium text-gray-700 mt-1">
        <span>{`A (${confidenceA}%)`}</span>
        <span>B ({confidenceB}%)</span>
      </div>
      <label
        htmlFor="textarea"
        className="block text-sm font-medium text-gray-600 mt-8"
      >
        Explanation:
      </label>
      <textarea
        id="textarea"
        value={explanation}
        onChange={(e) => setExplanation(e.target.value)}
        className="p-2 w-full h-32 rounded border shadow-sm"
      />
      {error && (
        <span className="block text-sm font-medium text-red-600">{error}</span>
      )}
      <Button
        onClick={chooseWinner}
        variant="secondary"
        className="w-full mt-4"
      >
        Submit judgement
      </Button>
    </form>
  );
}

interface JudgementConfidencesProps {
  debate: Debate;
  className?: string;
}

export function JudgementConfidencesCorrectFirst({
  debate,
  className = "",
}: JudgementConfidencesProps) {
  if (!debate.judgement) {
    return;
  }

  const { confidence_correct: confidenceCorrect } = debate.judgement;
  const confidenceA = confidenceCorrect;
  const confidenceB = 100 - confidenceCorrect;
  const red = "bg-red-600";
  const green = "bg-green-600";
  return (
    <div className={`flex ${className}`}>
      <div
        style={{ flex: confidenceA }}
        className={`${green} rounded-l px-2 text-white text-center`}
      >
        {confidenceA}%
      </div>
      <div
        style={{ flex: confidenceB }}
        className={`${red} rounded-r px-2 text-white text-center`}
      >
        {confidenceB}%
      </div>
    </div>
  );
}

// In this version we order the bars by A and B, rather than correct and incorrect. Unsure which is better.
// TODO: Test both of these out and pick the best
export function JudgementConfidences({
  debate,
  className = "",
}: JudgementConfidencesProps) {
  if (!debate.judgement) {
    return;
  }

  const { confidence_correct: confidenceCorrect } = debate.judgement;
  const { swap } = debate.transcript;
  const confidenceA = swap ? 100 - confidenceCorrect : confidenceCorrect;
  const confidenceB = swap ? confidenceCorrect : 100 - confidenceCorrect;
  const red = "bg-red-600";
  const green = "bg-green-600";
  const bgA = shouldShowFeedback(debate) ? (swap ? red : green) : "bg-gray-200";
  const bgB = shouldShowFeedback(debate) ? (swap ? green : red) : "bg-gray-300";
  const textColor = shouldShowFeedback(debate) ? "text-white" : "text-gray-900"
  return (
    <div className={`flex ${className}`}>
      <div
        style={{ flex: Math.min(Math.max(confidenceA, 15), 85) }}
        className={`${bgA} rounded-l  px-2 ${textColor} text-center`}
      >
        A: {confidenceA}%
      </div>
      <div
        style={{ flex: Math.min(Math.max(confidenceB, 15), 85) }}
        className={`${bgB} rounded-r px-2 ${textColor} text-center`}
      >
        B: {confidenceB}%
      </div>
    </div>
  );
}

interface JudgementResultsProps {
  debate: Debate;
  hideAnswers?: boolean;
}

function JudgementResults({ debate, hideAnswers }: JudgementResultsProps) {
  if (!debate.judgement) {
    return;
  }

  const { confidence_correct: confidenceCorrect } = debate.judgement;
  const isCorrect = confidenceCorrect > 50;
  return (
    <div className="mb-8 space-y-4">
      <JudgementConfidences debate={debate} />
      <p className="">
        <span className="text-sm font-medium text-gray-700">Judge:</span>{" "}
        {debate.user.full_name}
      </p>
      {debate.judgement.explanation && (
        <div className="mt-2">
          <span className="text-sm font-medium text-gray-700">
            Explanation:
          </span>{" "}
          {debate.judgement.explanation}
        </div>
      )}
      {!hideAnswers && shouldShowFeedback(debate) && (
        <p>
          Judgement was
          {isCorrect ? (
            <span> correct! ✅ </span>
          ) : (
            <span> incorrect! ❌ </span>
          )}
        </p>
      )}
    </div>
  );
}
interface JudgementPanelProps {
  debate: Debate;
  hideAnswers: boolean;
  isExplanationRequired?: boolean;
  isCommitmentRequired?: boolean;
}

export default function JudgementPanel({
  debate,
  hideAnswers,
  isExplanationRequired = false,
  isCommitmentRequired = false,
}: JudgementPanelProps) {
  const [confidenceCorrect, setConfidenceCorrect] = useState(50);
  return (
    <div>
      <div className="border-b border-gray-200 pb-2 mb-4">
        <h3 className="text-base font-semibold leading-6 text-gray-900">
          Judgement
        </h3>
      </div>
      {debate.judgement ? (
        <JudgementResults debate={debate} hideAnswers={hideAnswers} />
      ) : (
        <JudgementForm
          debate={debate}
          confidenceCorrect={confidenceCorrect}
          setConfidenceCorrect={setConfidenceCorrect}
          isExplanationRequired={isExplanationRequired}
          isCommitmentRequired={isCommitmentRequired}
        />
      )}
    </div>
  );
}
