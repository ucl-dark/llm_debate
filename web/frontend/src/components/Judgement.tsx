import { Disclosure } from "@headlessui/react";
import { ChevronDownIcon } from "@heroicons/react/24/outline";
import { TranscriptConfig, Judgement as IJudgement } from "../utils/types";

export default function Judgement({ transcript, judgement }: { transcript?: TranscriptConfig, judgement: IJudgement }) {
  let header: React.ReactNode;

  let judge_name = judgement.judge_name

  if (judge_name === "Unknown Model" && transcript) {
    if ("judge_name" in transcript.extra) {
      judge_name = transcript.extra["judge_name"]
    }
  }
  if (judgement.is_correct === true) {
    header = (
      <span className="text-green-700">✅ {`${judge_name}`}</span>
    );
  } else if (judgement.is_correct === false) {
    header = (
      <span className="text-red-700">❌ {`${judge_name}`}</span>
    );
  } else {
    header = <span className="text-bold">?? {`${judge_name}`}</span>;
  }

  return (
    <div>
      <Disclosure>
        {({ open }) => (
          <div className="">
            <Disclosure.Button className="flex justify-between w-full px-2 py-2 text-sm font-medium text-left text-black bg-blue-100 hover:bg-blue-200 focus:outline-none focus-visible:ring focus-visible:ring-blue-500 focus-visible:ring-opacity-75">
              <div>{header}</div>
              <ChevronDownIcon
                className={`${
                  open ? "transform rotate-180" : ""
                } w-5 h-5 text-black`}
              />
            </Disclosure.Button>
            <Disclosure.Panel className="px-2 whitespace-pre-wrap py-2 text-gray-800 ">
              <div className="">{judgement.judgement_text}</div>
            </Disclosure.Panel>
          </div>
        )}
      </Disclosure>
    </div>
  );
}
