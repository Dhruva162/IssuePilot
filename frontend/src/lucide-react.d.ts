declare module "lucide-react" {
  import type { ForwardRefExoticComponent, RefAttributes, SVGProps } from "react";

  type Icon = ForwardRefExoticComponent<
    Omit<SVGProps<SVGSVGElement>, "ref"> & RefAttributes<SVGSVGElement> & { size?: number | string }
  >;

  export const Archive: Icon;
  export const CheckCircle2: Icon;
  export const Clock3: Icon;
  export const ExternalLink: Icon;
  export const Github: Icon;
  export const Heart: Icon;
  export const LoaderCircle: Icon;
  export const Play: Icon;
  export const RefreshCw: Icon;
  export const SkipForward: Icon;
  export const Star: Icon;
  export const TerminalSquare: Icon;
}
