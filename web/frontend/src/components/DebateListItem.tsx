import Link from "./Link";
import { Debate } from "../utils/types";
import { JudgementConfidences } from "./JudgementPanel";
import { getDebateType, hasInteractiveJudge, shouldShowFeedback } from "../utils/utils";

function calculateColorFromCorrectness(correctness: number) {
  const colorMappings = [
    { max: 50, className: "bg-red-200" },
    { max: 100, className: "bg-green-200" },
  ];

  for (const mapping of colorMappings) {
    if (correctness <= mapping.max) {
      return mapping.className;
    }
  }
}

function getBackgroundColor(debate: Debate, hideAnswers: boolean) {
  const { judgement } = debate;
  let backgroundColor = "bg-white";
  if (judgement) {
    if (shouldShowFeedback(debate) && !hideAnswers) {
      backgroundColor = calculateColorFromCorrectness(
        judgement?.confidence_correct,
      );
    } else {
      backgroundColor = "bg-gray-100";
    }
  }
  return backgroundColor;
}

interface DebateListItemProps {
  debate: Debate;
  hideAnswers: boolean;
  urlPrefix: string;
}

export default function DebateListItem({
  debate,
  hideAnswers,
  urlPrefix,
}: DebateListItemProps) {
  const { transcript } = debate;
  const backgroundColor = getBackgroundColor(debate, hideAnswers);
  const debateType = getDebateType(debate, hideAnswers)


  // TODO: Bars are too wide, but if shorter 5% confidences go to 2 lines. This also may happen on smaller screens now
  return (
    <Link
      to={`${urlPrefix}/${debate.id}`}
      className={`flex flex-col flex-grow w-full py-3 px-4 whitespace-pre-wrap border border-gray-300 rounded-lg shadow text-base hover:brightness-90 hover:cursor-pointer justify-between ${backgroundColor}`}
    >
      <div className="flex flex-row">
        <div className="flex flex-col flex-grow">
          <span className="font-bold">{debate.name}</span>
          <span>{transcript.question}</span>
          <div className="flex flex-row text-sm font-medium mt-2 gap-4">
            <span className="">{debateType}</span>
            {hasInteractiveJudge(debate) && <span className="">Interactive</span>}
          </div>
        </div>
        {debate.judgement && (
          <div className="w-2/5 flex flex-col justify-center">
            {shouldShowFeedback(debate) && !hideAnswers ? (
              <>
                <span> </span>
                <JudgementConfidences debate={debate} className="" />
              </>
            ) : (
              <span className="w-full text-right text-sm font-medium ">
                Complete
              </span>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}
