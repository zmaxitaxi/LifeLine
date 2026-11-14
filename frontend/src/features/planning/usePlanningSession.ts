import { useCallback, useEffect, useRef, useState } from "react";
import type {
  PlanningState,
  CreatePlanningSession,
} from "../../../../contracts/planning";
import type { SolarForecast } from "../../../../contracts/forecast";
import { api } from "@/lib/clinic";
import { planningApi, PlanningApiError, currentPlan } from "./planning-api";
const storageKey = "lifeline.planning-session.v1";
const reviewedKey = "lifeline.reviewed-session.v1";
function reviewedSession() {try{return localStorage.getItem(reviewedKey);}catch{return null;}}
function markReviewed(id:string) {try{localStorage.setItem(reviewedKey,id);}catch{/* The server remains authoritative. */}}
function storedSession() {
  try {
    return localStorage.getItem(storageKey);
  } catch {
    return null;
  }
}
function remember(id: string) {
  try {
    localStorage.setItem(storageKey, id);
  } catch {
    /* Server snapshot remains authoritative without storage. */
  }
}
export function usePlanningSession() {
  const [state, setState] = useState<PlanningState | null>(null);
  const stateRef = useRef<PlanningState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [missingSession, setMissingSession] = useState(false);
  const [resumeCandidate,setResumeCandidate]=useState<PlanningState|null>(null);
  const [busy, setBusy] = useState("");
  const locked = useRef(false);
  const [invalidating, setInvalidating] = useState(false);
  const [verificationRequired, setVerificationRequired] = useState(false);
  const [weather, setWeather] = useState<SolarForecast | null>(null);
  const [weatherError, setWeatherError] = useState("");
  const [weatherLoading, setWeatherLoading] = useState(false);
  const initialization = useRef<AbortController | null>(null);
  const accept = useCallback((next: PlanningState) => {
    if (
      stateRef.current?.id === next.id &&
      next.revision < stateRef.current.revision
    )
      return;
    stateRef.current = next;
    setState(next);
    remember(next.id);
  }, []);
  const refreshWeather = useCallback(async (snapshot = stateRef.current) => {
    if (!snapshot) return;
    setWeatherLoading(true);
    setWeatherError("");
    try {
      setWeather(
        await api<SolarForecast>(
          `forecast?latitude=${snapshot.location.latitude}&longitude=${snapshot.location.longitude}`,
        ),
      );
    } catch (e) {
      setWeather(null);
      setWeatherError(
        e instanceof Error
          ? e.message
          : "The live forecast could not be retrieved.",
      );
    } finally {
      setWeatherLoading(false);
    }
  }, []);
  const initialize = useCallback(
    async (startNew = false) => {
      initialization.current?.abort();
      const controller = new AbortController();
      initialization.current = controller;
      setLoading(true);
      setError("");
      setMissingSession(false);
      try {
        const id = startNew ? null : storedSession();
        if(!id)return;
        const snapshot=await planningApi.read(id,controller.signal);
        if (controller.signal.aborted) return;
        if(reviewedSession()===id){accept(snapshot);void refreshWeather(snapshot);}
        else setResumeCandidate(snapshot);
      } catch (e) {
        if (controller.signal.aborted) return;
        if (e instanceof PlanningApiError && e.code === "NOT_FOUND") {
          setMissingSession(true);
          setError(
            "The previous local planning session is no longer available. The server may have restarted. Start a new session to continue; earlier activities have not been silently copied.",
          );
        } else
          setError(
            e instanceof Error
              ? e.message
              : "The local planning service is unavailable.",
          );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    },
    [accept, refreshWeather],
  );
  useEffect(() => {
    void initialize();
    return () => initialization.current?.abort();
  }, [initialize]);
  function beginSetup(){if(stateRef.current)setResumeCandidate(stateRef.current);stateRef.current=null;setState(null);setWeather(null);setError("");setNotice("");}
  async function resume(){if(!resumeCandidate || locked.current)return;markReviewed(resumeCandidate.id);accept(resumeCandidate);setResumeCandidate(null);setError("");void refreshWeather(resumeCandidate);}
  async function create(body:CreatePlanningSession){
    if(locked.current)return false;locked.current=true;setBusy("Saving your clinic setup…");setError("");
    try{const snapshot=await planningApi.create(body);markReviewed(snapshot.id);accept(snapshot);setResumeCandidate(null);setNotice("");void refreshWeather(snapshot);return true;}
    catch(e){setError(e instanceof Error ? e.message : "The clinic setup could not be saved. Please retry.");return false;}
    finally{locked.current=false;setBusy("");}
  }
  const reload = useCallback(async () => {
    const snapshot = stateRef.current;
    if (!snapshot) return;
    try {
      accept(await planningApi.read(snapshot.id));
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "The shared plan could not be reloaded.",
      );
    }
  }, [accept]);
  useEffect(() => {
    const focus = () => {
      if (!locked.current) void reload();
    };
    window.addEventListener("focus", focus);
    return () => window.removeEventListener("focus", focus);
  }, [reload]);
  useEffect(() => {
    if (state?.plan_status !== "pending") return;
    let attempts = 0,
      active = false;
    const timer = setInterval(async () => {
      if (active || locked.current) return;
      if (++attempts > 24) {
        clearInterval(timer);
        setError(
          "The plan is still pending. Reload the shared state to check its status.",
        );
        return;
      }
      active = true;
      await reload();
      active = false;
    }, 2500);
    return () => clearInterval(timer);
  }, [state?.plan_status, reload]);
  async function run<T>(
    label: string,
    action: (snapshot: PlanningState) => Promise<T>,
    extract: (result: T) => PlanningState,
    hidePlan = false,
  ): Promise<T | null> {
    if (!stateRef.current || locked.current) return null;
    locked.current = true;
    setBusy(label);
    setError("");
    setNotice("");
    if (hidePlan) setInvalidating(true);
    try {
      const result = await action(stateRef.current);
      const snapshot = extract(result);
      accept(snapshot);
      if (snapshot.plan_status === "current") setVerificationRequired(false);
      if (snapshot.forecast_reference) {
        setWeather(snapshot.forecast_reference);
        setWeatherError("");
      } else if (snapshot.plan_status === "failed") {
        setWeather(null);
        void refreshWeather(snapshot);
      }
      return result;
    } catch (e) {
      if (hidePlan) setVerificationRequired(true);
      if (e instanceof PlanningApiError && e.status === 409)
        setError(
          "The shared plan changed elsewhere. The latest state has been reloaded. Review the proposal again before retrying; no changes were automatically replayed.",
        );
      else
        setError(
          e instanceof Error
            ? e.message
            : "The change could not be verified. Reload the shared state and try again.",
        );
      await reload();
      return null;
    } finally {
      locked.current = false;
      setBusy("");
      setInvalidating(false);
    }
  }
  return {
    state,
    stateRef,
    loading,
    error,
    notice,
    busy,
    missingSession,
    resumeCandidate,
    resume,
    create,
    beginSetup,
    initialize,
    reload,
    run,
    weather,
    weatherError,
    weatherLoading,
    refreshWeather,
    computed: currentPlan(state, invalidating || verificationRequired),
    invalidating,
  };
}
