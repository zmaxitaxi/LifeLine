import { useEffect, useState, type ReactNode } from "react";
import { ChevronDown, Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

export function ClinicConfiguration({ children }: { children: ReactNode }) {
  const [wide, setWide] = useState(
    () => window.matchMedia("(min-width: 761px)").matches,
  );
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(min-width: 761px)");
    const changed = () => setWide(query.matches);
    query.addEventListener("change", changed);
    return () => query.removeEventListener("change", changed);
  }, []);
  return (
    <Collapsible
      className="inspector"
      render={<aside />}
      open={wide || open}
      onOpenChange={setOpen}
    >
      <CollapsibleTrigger
        className="mobile-config-trigger"
        render={
          <Button
            type="button"
            variant="outline"
            className="w-full justify-between"
          />
        }
      >
        <span className="flex items-center gap-2">
          <Settings2 />
          Configure clinic
        </span>
        <ChevronDown />
      </CollapsibleTrigger>
      <CollapsibleContent keepMounted>{children}</CollapsibleContent>
    </Collapsible>
  );
}
