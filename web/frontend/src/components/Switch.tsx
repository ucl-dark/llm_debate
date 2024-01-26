import classNames from "classnames";
import { Switch } from "@headlessui/react";

const SwitchComponent = ({
  isChecked,
  onChange,
  children,
  className = "",
  isDisabled = false,
  ...props
}) => {
  return (
    <Switch.Group as="div" className="py-2 flex items-center">
      <Switch
        checked={isChecked}
        disabled={isDisabled}
        onChange={onChange}
        className={classNames(
          isChecked ? "bg-blue-600" : "bg-gray-200",
          "relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2",
        )}
      >
        <span
          aria-hidden="true"
          className={classNames(
            isChecked ? "translate-x-5" : "translate-x-0",
            "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
          )}
        />
      </Switch>
      <Switch.Label as="span" className="ml-3 text-sm">
        {children}
      </Switch.Label>
    </Switch.Group>
  );
};
export default SwitchComponent;
