import classNames from "classnames";


interface Props extends React.ComponentProps<"input"> {
  label?: string;
  error?: string;
  hint?: string;
  inputClassName?: string;
}

const Input = ({
  className,
  inputClassName,
  id,
  label,
  error,
  hint,
  type = "text",
  ...props
}: Props) => {
  return (
    <div className={className}>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      <div className="relative rounded-md ">
        <input
          type={type}
          id={id}
          className={classNames(
            "block w-full focus:outline-none sm:text-sm rounded-md shadow py-2",
            {
              "pr-10 border-red-300 text-red-900 placeholder-red-300 focus:ring-red-500 focus:border-red-500": error,
              "shadow-sm focus:ring-blue-500 focus:border-blue-500 border-gray-300": !error,
            },
            inputClassName
          )}
          {...props}
        />
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {!error && hint && <p className="mt-2 text-sm text-gray-500">{hint}</p>}
    </div>
  );
};

export default Input;
