import { useEffect, useRef, type RefObject } from "react";
/** Keep keyboard focus inside a review dialog and return to a usable control. */
export function useReviewedDialog(ref:RefObject<HTMLDialogElement|null>,editing:boolean) {
  const trigger=useRef(document.activeElement instanceof HTMLElement ? document.activeElement : null);
  useEffect(()=>{
    const dialog=ref.current;if(!dialog)return;
    if(!dialog.open)dialog.showModal();
    return ()=>{
      if(dialog.open)dialog.close();
      const target=trigger.current;
      if(target?.isConnected && !target.closest('[hidden],dialog:not([open])'))target.focus();
      else document.querySelector<HTMLElement>(location.hash.startsWith('#overview') ? '.panel-actions button' : '#chat-input')?.focus();
    };
  },[ref]);
  useEffect(()=>{
    const dialog=ref.current;
    if(editing)dialog?.querySelector<HTMLInputElement>('input:not([disabled])')?.focus();
    else dialog?.querySelector<HTMLElement>('h2')?.focus();
  },[ref,editing]);
}
