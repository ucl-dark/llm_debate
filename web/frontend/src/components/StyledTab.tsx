import { Tab, TabProps } from "@headlessui/react";
import classNames from "classnames";
import { ReactElement, ReactNode } from "react";

interface TabRenderPropArg {
  selected: boolean;
}

export default function StyledTab({ children, ...props }: TabProps<"button">) {
  return (
    <Tab {...props}>
      {({ selected }: TabRenderPropArg) => {
        let content: ReactNode;

        if (typeof children === "function") {
          content = (children as (bag: TabRenderPropArg) => ReactElement)({
            selected,
          });
        } else {
          content = children;
        }

        return (
          <div
            className={classNames(
              selected
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300",
              "py-2 px-4 text-center w-full border-b-2 font-medium text-sm -mb-px",
            )}
          >
            {content}
          </div>
        );
      }}
    </Tab>
  );
}
