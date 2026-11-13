import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

export function Disclosure({
  title,
  children,
  className = "",
  keepMounted = true,
  open,
  onOpenChange,
}: {
  title: ReactNode;
  children: ReactNode;
  className?: string;
  keepMounted?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}) {
  return (
    <Collapsible
      className={`disclosure ${className}`}
      open={open}
      onOpenChange={onOpenChange}
    >
      <CollapsibleTrigger
        render={
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="w-full justify-between"
          />
        }
      >
        <span>{title}</span>
        <ChevronDown data-icon="inline-end" />
      </CollapsibleTrigger>
      <CollapsibleContent keepMounted={keepMounted}>
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}
