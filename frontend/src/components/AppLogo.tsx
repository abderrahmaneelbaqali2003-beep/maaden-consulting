import { cn } from "@/lib/utils";

interface AppLogoProps {
  className?: string;
}

export function AppLogo({ className }: AppLogoProps) {
  return (
    <img
      src="/branding/maaden-consulting-logo.png"
      alt="MAADEN Consulting"
      className={cn("h-auto w-[clamp(145px,90%,175px)] object-contain", className)}
    />
  );
}
