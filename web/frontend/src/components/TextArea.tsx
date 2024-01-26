import classNames from "classnames";


interface Props extends React.ComponentProps<"textarea"> {
  label?: string;
  error?: string;
  hint?: string;
  disabled?: boolean
  inputClassName?: string;
}

export default function TextArea({
  className,
  inputClassName,
  id,
  disabled,
  label,
  error,
  hint,
  ...props
}: Props) {
  return (
    <div className={className}>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      <div className="relative rounded-md ">
        <textarea
          id={id}
          disabled={disabled}
          className={classNames(
            "block rounded border shadow-sm w-full focus:outline-none sm:text-sm rounded-md shadow p-2",
            {
              "border-gray-400": disabled
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
