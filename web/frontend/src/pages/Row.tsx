import { Tab } from "@headlessui/react";
import { useState, useEffect } from "react";
import { useNavigate, useLocation, LoaderFunction } from "react-router-dom";
import useHideAnswers from "../hooks/useHideAnswers";
import { classNames, reverseTranscript } from "../utils/utils";
import Judgement from "../components/Judgement";
import { GetRowResponse, useTypedLoaderData } from "../utils/types";
import JSONViewer from "../components/JSONViewer";
import StyledTab from "../components/StyledTab";
import Transcript from "../components/Transcript";
import DebateHeader from "../components/DebateHeader";

export const rowLoader: LoaderFunction = async ({ params }) => {
  try {
    const { path_hash, row_number } = params;
    if (!path_hash || !row_number) throw `param missing from ${params}`;
    const response = await fetch(`/api/files/${path_hash}/row/${row_number}`);
    const row: GetRowResponse = await response.json();
    return { row };
  } catch (error) {
    console.error("Error:", error);
  }
};

interface FileNavButtonsProps {
  path_hash: string;
  row_number: number;
  next_available: boolean;
}

function FileNavButtons({
  path_hash,
  row_number,
  next_available,
}: FileNavButtonsProps) {
  const navigate = useNavigate();
  return (
    <div className="px-2 py-2 flex justify-center">
      <button
        type="button"
        disabled={row_number < 2}
        onClick={() =>
          navigate(
            `/files/${path_hash.slice(0, 8)}/row/${row_number - 1}${location.search
            }`,
          )
        }
        className={classNames(
          row_number >= 2 ? "text-gray-900 hover:bg-gray-50" : "text-gray-500",
          "rounded-md mr-4 bg-white px-2.5 py-1.5 text-sm font-semibold shadow-sm ring-1 ring-inset ring-gray-300 ",
        )}
      >
        Previous
      </button>
      <button
        type="button"
        disabled={!next_available}
        onClick={() =>
          navigate(
            `/files/${path_hash.slice(0, 8)}/row/${row_number + 1}${location.search
            }`,
          )
        }
        className={classNames(
          next_available ? "text-gray-900 hover:bg-gray-50" : "text-gray-500",
          "rounded-md mr-4 bg-white px-2.5 py-1.5 text-sm font-semibold shadow-sm ring-1 ring-inset ring-gray-300 ",
        )}
      >
        Next
      </button>
    </div>
  );
}

function Row() {
  const location = useLocation();
  const { row } = useTypedLoaderData();
  if (!row) return "Unable to load row.";

  const [getHideAnswers] = useHideAnswers();
  const hideAnswers = getHideAnswers();
  const [reverseIfHidden, setReverseIfHidden] = useState<boolean>(false);

  // If answers are hidden, we want to to randomize whether we show swapped or unswapped version of debate
  useEffect(() => {
    setReverseIfHidden(Math.random() < 0.5);
  }, [location]);

  let structuredTranscript = row.transcript;

  if (hideAnswers && reverseIfHidden && row.transcript) {
    // If answers are hidden, we don't want to give it away with position, so we randomly reverse the transcript
    // "Reverse" just means inverting the swap status. So swapped becomes unswapped and vice versa.
    // We use the structuredTranscript for header and messages, but show the original in the Raw Transcript
    structuredTranscript = reverseTranscript(row.transcript);
  }
  const answers = structuredTranscript?.answers || {
    correct: row.question.correct_answer,
    incorrect: row.question.incorrect_answer,
  };

  const names = structuredTranscript?.names || {};

  return (
    <div className="flex flex-col ">
      <DebateHeader
        question={row.question.question_text}
        answers={answers}
        names={names}
        swap={Boolean(structuredTranscript?.swap)}
        hideAnswers={hideAnswers}
      />
      <div className="flex ">
        <div className="flex-col w-3/4  ">
          <Tab.Group>
            <Tab.List className="flex border-b border-gray-200 w-full">
              {structuredTranscript && (
                <StyledTab className="flex-grow">Arguments</StyledTab>
              )}
              {structuredTranscript?.responses && (
                <StyledTab className="flex-grow">Responses</StyledTab>
              )}
              <StyledTab className="flex-grow">Raw Transcript</StyledTab>
              {structuredTranscript?.story && (
                <StyledTab className="flex-grow">Story</StyledTab>
              )}
            </Tab.List>
            <Tab.Panels className="flex-grow overflow-y-auto">
              {structuredTranscript && (
                <Tab.Panel>
                  <Transcript
                    rounds={structuredTranscript.rounds}
                    names={structuredTranscript.names}
                    swap={structuredTranscript.swap}
                    hideAnswers={hideAnswers}
                  />
                </Tab.Panel>
              )}
              {structuredTranscript?.responses && (
                <Tab.Panel>
                  <Transcript
                    rounds={structuredTranscript.responses}
                    names={structuredTranscript.names}
                    swap={structuredTranscript.swap}
                    hideAnswers={hideAnswers}
                  />
                </Tab.Panel>
              )}
              <Tab.Panel>
                <JSONViewer content={row.raw_transcript} truncate={["story"]} />
              </Tab.Panel>
              {structuredTranscript?.story && (
                <Tab.Panel>
                  <JSONViewer content={structuredTranscript.story} />
                </Tab.Panel>
              )}
            </Tab.Panels>
          </Tab.Group>
        </div>
        <div className="w-1/4 ">
          {row.file.path_hash && (
            <FileNavButtons
              path_hash={row.file.path_hash}
              row_number={row.row_number}
              next_available={Boolean(row.next_available)}
            />
          )}
          <div className="pb-2">
            <div className="underline justify-center w-full flex mb-4 bg-gray-100 py-4">
              Row {row.row_number}
            </div>
            <div className="px-2">
              <span className="break-all">
                {!hideAnswers && (
                  <>File: {row.file.path.split("/").slice(-5).join("/")}</>
                )}
              </span>
            </div>
          </div>
          {!hideAnswers && (
            <>
              <div className="justify-center w-full flex bg-gray-100 py-4">
                ⚖️ Judgements
              </div>
              {row.judgement ? (
                structuredTranscript ? (
                  <Judgement
                    transcript={structuredTranscript}
                    judgement={row.judgement}
                  />
                ) : (
                  <Judgement judgement={row.judgement} />
                )
              ) : (
                <p className="m-2">No judgements.</p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Row;
