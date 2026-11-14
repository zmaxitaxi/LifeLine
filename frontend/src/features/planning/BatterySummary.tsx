import type { RecoveryOption } from "../../../../contracts/recovery";
import type { ComputedPlan } from "../../../../contracts/planning";
import { BatteryEvidence } from "./BatteryEvidence";

export function BatterySummary({ computed, date, selected }: { computed: ComputedPlan; date: string; selected?: RecoveryOption }) {
  return <BatteryEvidence key={`${computed.input_revision}-${computed.generation}`} result={computed.simulation} date={date} intervention={selected ?? computed.recovery?.existing} showIndicators={false} />;
}
