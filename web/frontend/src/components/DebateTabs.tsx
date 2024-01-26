import { Debate } from "../utils/types";
import { Tab } from "@headlessui/react";
import { useState, useRef } from "react";
import StyledTab from "./StyledTab";
import Transcript from "./Transcript";
import JSONViewer from "./JSONViewer";
import CreateNewTurn from "./CreateNewTurn";
import { isDebateComplete } from "../utils/utils";
import { useUser } from "../hooks/userProvider";

interface DebateTabsProps {
  debate: Debate;
  setDebate: () => void;
  hideAnswers: boolean;
  rawTranscriptEnabled?: boolean;
  responsesEnabled?: boolean;
  storyEnabled?: boolean;
  maxTurns?: number;
  minTurns?: number;
  judgeMessagesAllowed: boolean;
}

export default function DebateTabs({
  debate,
  setDebate,
  hideAnswers,
  responsesEnabled = true,
  rawTranscriptEnabled = true,
  storyEnabled = true,
  maxTurns,
  minTurns,
  judgeMessagesAllowed = true,
}: DebateTabsProps) {
  const { user } = useUser();
  const panelsRef = useRef(null); // Create a ref for the scrollable div
  const [currentTranscriptScroll, setCurrentTranscriptScroll] = useState(null);
  const scrollPanels = () => {
    // timeout ensures the scroll happens after rendering (needed when switching back to the tab)
    setTimeout(() => {
      if (panelsRef.current) {
        if (currentTranscriptScroll === null) {
          panelsRef.current.scrollTop = panelsRef.current.scrollHeight;
        } else {
          panelsRef.current.scrollTop = currentTranscriptScroll;
        }
      }
    }, 0);
  };

  const debateOwner = user && user.id === debate.user.id;

  const onChangeTab = (tabIndex: number) => {
    // Save the transcript scroll pos when navigating away, and restore it when navigating back
    if (tabIndex === 0) {
      // scrollPanels();
    } else {
      setCurrentTranscriptScroll(panelsRef.current.scrollTop);
    }
  };
  return (
    <Tab.Group onChange={onChangeTab}>
      <Tab.List className="flex border-b border-gray-200 w-full">
        <StyledTab className="flex-grow">Debate</StyledTab>
        {responsesEnabled && (
          <StyledTab className="flex-grow">Responses</StyledTab>
        )}
        {rawTranscriptEnabled && debate.transcript.responses && (
          <StyledTab className="flex-grow">Raw Transcript</StyledTab>
        )}
        {storyEnabled && debate.transcript.story && (
          <StyledTab className="flex-grow">Story</StyledTab>
        )}
      </Tab.List>
      <Tab.Panels
        className="flex flex-col flex-grow overflow-y-auto"
        ref={panelsRef}
      >
        <Tab.Panel unmount={false} className="flex flex-col flex-grow">
          <div className="flex flex-col flex-grow justify-between">
            <Transcript
              rounds={debate.transcript.rounds}
              names={debate.transcript.names}
              swap={debate.transcript.swap}
              hideAnswers={hideAnswers}
            />
            {!isDebateComplete(debate) && debateOwner && (
              <CreateNewTurn
                debate={debate}
                setDebate={setDebate}
                onNewTurn={scrollPanels}
                maxTurns={maxTurns}
                minTurns={minTurns}
                judgeMessagesAllowed={judgeMessagesAllowed}
              />
            )}
          </div>
        </Tab.Panel>
        {responsesEnabled && debate.transcript.responses && (
          <Tab.Panel>
            <Transcript
              rounds={debate.transcript.responses}
              names={debate.transcript.names}
              swap={debate.transcript.swap}
              hideAnswers={hideAnswers}
            />
          </Tab.Panel>
        )}
        {rawTranscriptEnabled && (
          <Tab.Panel>
            <JSONViewer content={debate.raw_transcript} truncate={["story"]} />
          </Tab.Panel>
        )}
        {storyEnabled && debate.transcript.story && (
          <Tab.Panel>
            <JSONViewer content={debate.transcript.story} />
          </Tab.Panel>
        )}
      </Tab.Panels>
    </Tab.Group>
  );
}
