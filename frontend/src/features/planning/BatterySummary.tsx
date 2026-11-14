import type { RecoveryOption } from "../../../../contracts/recovery";
import type { ComputedPlan } from "../../../../contracts/planning";
import { BatteryEvidence } from "./BatteryEvidence";

export function BatterySummary({ computed, date, selected }: { computed: ComputedPlan; date: string; selected?: RecoveryOption }) {
  return <BatteryEvidence key={`${computed.input_revision}-${computed.generation}`} resetKey={`${computed.input_revision}-${computed.generation}-${computed.computed_at}-${selected?.id ?? "current"}`} result={computed.simulation} date={date} intervention={selected ?? computed.recovery?.existing} showIndicators={false} />;
}
