import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost";

export function Button({
  variant = "primary",
  className,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const cls = [
    "btn",
    variant === "secondary" ? "btn-secondary" : "",
    variant === "ghost" ? "btn-ghost" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");
  return <button className={cls} {...rest} />;
}
