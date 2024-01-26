import classNames from "classnames";

interface Props extends React.ComponentProps<"select"> {
  label?: string;
  hint?: string;
  inputClassName?: string;
  sizing?: "small" | "medium"; // select already has a size prop
}

const Select = ({
  className,
  sizing = "medium",
  inputClassName,
  id,
  label,
  hint,
  children,
  ...props
}: Props) => {
  return (
    <div className={className}>
      {label && (
        <label
          htmlFor={id}
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          {label}
        </label>
      )}
      <div className="relative rounded-md shadow-sm">
        <select
          id={id}
          className={classNames(
            "block w-full pl-3 pr-10 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md cursor-pointer",
            { "py-2": sizing === "medium", "py-1": sizing === "small" },
            inputClassName,
          )}
          {...props}
        >
          {children}
        </select>
      </div>
      {hint && <p className="mt-2 text-sm text-gray-500">{hint}</p>}
    </div>
  );
};

export default Select;
