import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground placeholder:text-[#9a9fa1] transition-colors focus-visible:border-secondary focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_rgba(201,154,50,0.15)] disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
