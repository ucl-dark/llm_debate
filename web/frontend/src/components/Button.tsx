import React from "react";
import classNames from "classnames";

interface Props extends React.ComponentPropsWithRef<"button"> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "small" | "medium";
}
export type Ref = HTMLButtonElement;

const Button = React.forwardRef<Ref, Props>(
  (
    {
      children,
      size = "medium",
      variant = "primary",
      className = "",
      disabled = false,
      ...props
    }: Props,
    ref,
  ) => {
    const commonClasses =
      "inline-flex justify-center font-semibold border items-center rounded-md shadow-sm";

    const variantClasses = {
      primary: "text-white bg-blue-600 border-transparent",
      secondary: "text-gray-700 bg-white border-gray-300",
      danger: "text-white bg-red-600 border-transparent",
    };

    const hoverClasses = {
      primary: "hover:bg-blue-500",
      secondary: "hover:bg-gray-100",
      danger: "hover:bg-red-700",
    };

    const disabledClasses = {
      primary: "text-white bg-blue-400 border-transparent",
      secondary: "text-gray-500 bg-gray-200 border-gray-300",
      danger: "text-white bg-red-400 border-transparent",
    };

    const sizeClasses = {
      small: "px-3 py-1 text-sm leading-4 h-8",
      medium: "px-4 py-2 text-sm",
    };

    return (
      <button
        ref={ref}
        type="button"
        className={classNames(
          commonClasses,
          variantClasses[variant],
          disabled ? disabledClasses[variant] : hoverClasses[variant],
          sizeClasses[size],
          disabled ? "" : "cursor-pointer",
          className,
        )}
        disabled={disabled}
        {...props}
      >
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";
export default Button;
