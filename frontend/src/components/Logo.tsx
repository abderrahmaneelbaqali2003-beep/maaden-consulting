import { cn } from "@/lib/utils";
import maadenMark from "@/assets/maaden-mark.png";

interface LogoProps {
  className?: string;
  markClassName?: string;
  showWordmark?: boolean;
  theme?: "dark" | "light";
}

export function Logo({ className, markClassName, showWordmark = true, theme = "dark" }: LogoProps) {
  const titleColor = theme === "dark" ? "text-white" : "text-foreground";
  const subtitleColor = theme === "dark" ? "text-primary" : "text-primary";

  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <img src={maadenMark} alt="" className={cn("h-8 w-8 shrink-0", markClassName)} />
      {showWordmark && (
        <div className="flex flex-col leading-none">
          <span className={cn("text-[15px] font-bold tracking-tight", titleColor)}>MAADEN</span>
          <span className={cn("text-[9px] font-semibold tracking-[0.25em]", subtitleColor)}>
            CONSULTING
          </span>
        </div>
      )}
    </div>
  );
}
