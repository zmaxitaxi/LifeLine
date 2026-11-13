import { Children, type ReactNode } from "react";
import { Field, FieldGroup } from "@/components/ui/field";
/** Preserve the existing controls while providing consistent shadcn field groups. */
export function FormFields({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <FieldGroup className={className}>
      {Children.map(children, (child) =>
        child ? <Field>{child}</Field> : null,
      )}
    </FieldGroup>
  );
}
